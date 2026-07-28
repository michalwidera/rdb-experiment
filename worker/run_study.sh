#!/bin/bash
# Pojedyncze badanie kampanii wydajnosciowej na workerze.
#
# Twardy invariant:
#   - CODE_REPO jest tylko do odczytu i pozostaje czyste;
#   - wszystkie wyniki, JOURNAL.md i commity trafiaja wylacznie do
#     EXPERIMENT_REPO na branch EXPERIMENT_BRANCH.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_EXPERIMENT_REPO="$(cd "$SCRIPT_DIR/.." && pwd)"

CODE_REPO="/home/michal/retractordb"
EXPERIMENT_REPO="$DEFAULT_EXPERIMENT_REPO"
CODE_COMMIT=""
EXPERIMENT_BRANCH=""
RESULTS_ROOT=""
CAMPAIGN=""
STUDY_ID=""
RATE_HZ=""
CLIENTS=""
SAMPLES=""
SINK="null"

while [ $# -gt 0 ]; do
  case "$1" in
    --code-repo) CODE_REPO="$2"; shift 2 ;;
    --experiment-repo) EXPERIMENT_REPO="$2"; shift 2 ;;
    --code-commit) CODE_COMMIT="$2"; shift 2 ;;
    --experiment-branch) EXPERIMENT_BRANCH="$2"; shift 2 ;;
    --results-root) RESULTS_ROOT="$2"; shift 2 ;;
    --campaign) CAMPAIGN="$2"; shift 2 ;;
    --study-id) STUDY_ID="$2"; shift 2 ;;
    --rate-hz) RATE_HZ="$2"; shift 2 ;;
    --clients) CLIENTS="$2"; shift 2 ;;
    --samples) SAMPLES="$2"; shift 2 ;;
    --sink) SINK="$2"; shift 2 ;;
    *) printf 'Nieznana opcja: %s\n' "$1" >&2; exit 1 ;;
  esac
done

# shellcheck source=../lib/common.sh
source "$EXPERIMENT_REPO/lib/common.sh"

[ -n "$CODE_COMMIT" ] || die "Brak --code-commit"
[ -n "$EXPERIMENT_BRANCH" ] || die "Brak --experiment-branch"
[ -n "$RESULTS_ROOT" ] || die "Brak --results-root"
[ -n "$CAMPAIGN" ] || die "Brak --campaign"
[ -n "$STUDY_ID" ] || die "Brak --study-id"
[ -n "$RATE_HZ" ] || die "Brak --rate-hz"
[ -n "$CLIENTS" ] || die "Brak --clients"
[ -n "$SAMPLES" ] || die "Brak --samples"
validate_results_root "$RESULTS_ROOT" || exit 1
validate_campaign_name "$CAMPAIGN" || exit 1
validate_git_branch "$EXPERIMENT_BRANCH" "brancha wynikow" || exit 1
validate_safe_absolute_path "$CODE_REPO" "repozytorium kodu" || exit 1
validate_safe_absolute_path "$EXPERIMENT_REPO" "repozytorium wynikow" || exit 1
[[ "$CODE_COMMIT" =~ ^[0-9a-f]{40}$ ]] || die "code-commit musi byc pelnym SHA-1"
[[ "$STUDY_ID" =~ ^[0-9]+$ ]] || die "study-id musi byc liczba"
[[ "$RATE_HZ" =~ ^[0-9]+$ ]] && [ "$RATE_HZ" -gt 0 ] || die "rate-hz musi byc dodatnie"
[[ "$CLIENTS" =~ ^[0-9]+$ ]] && [ "$CLIENTS" -gt 0 ] || die "clients musi byc dodatnie"
[[ "$SAMPLES" =~ ^[0-9]+$ ]] && [ "$SAMPLES" -gt 1 ] || die "samples musi byc wieksze od 1"
[ "$SINK" = "null" ] || [ "$SINK" = "nc" ] || die "sink musi byc null albo nc"

[ -d "$CODE_REPO/.git" ] || die "Brak repozytorium kodu: $CODE_REPO"
[ -d "$EXPERIMENT_REPO/.git" ] || die "Brak repozytorium wynikow: $EXPERIMENT_REPO"
require_disjoint_repositories "$CODE_REPO" "$EXPERIMENT_REPO" || exit 1
[ -z "$(git -C "$CODE_REPO" status --short)" ] || die "Repozytorium kodu workera nie jest czyste"
[ "$(git -C "$CODE_REPO" rev-parse HEAD)" = "$CODE_COMMIT" ] ||
  die "Repozytorium kodu nie wskazuje wymaganego commita $CODE_COMMIT"

git -C "$EXPERIMENT_REPO" fetch origin "$EXPERIMENT_BRANCH" --quiet
[ -z "$(git -C "$EXPERIMENT_REPO" status --short)" ] || die "Repozytorium wynikow workera nie jest czyste"
git -C "$EXPERIMENT_REPO" checkout -B "$EXPERIMENT_BRANCH" "origin/$EXPERIMENT_BRANCH" >/dev/null

ECG_SRC="$CODE_REPO/examples/ecg/rec205"
ANALYZER="$CODE_REPO/examples/ecg/e1_stats.py"
[ -f "$ECG_SRC/rec205" ] || die "Brak $ECG_SRC/rec205; uruchom examples/ecg/build.sh"
[ -f "$ECG_SRC/rec205.desc" ] || die "Brak $ECG_SRC/rec205.desc"
[ -f "$ANALYZER" ] || die "Brak analizatora $ANALYZER"

command -v xretractor >/dev/null || die "xretractor nie jest na PATH"
command -v xqry >/dev/null || die "xqry nie jest na PATH"
command -v taskset >/dev/null || die "Brak taskset"
command -v setcap >/dev/null || die "Brak setcap"
command -v getcap >/dev/null || die "Brak getcap"
command -v findmnt >/dev/null || die "Brak findmnt"
command -v pgrep >/dev/null || die "Brak pgrep"
sudo -n true 2>/dev/null || die "Badanie RT wymaga bezhaslowego sudo"
require_tmpfs /dev/shm || exit 1
uname -v | grep -q PREEMPT_RT || die "Kernel workera nie jest buildem PREEMPT_RT"

XR_BIN="$(command -v xretractor)"
verify_probe_binary "$XR_BIN" || exit 1
sudo -n setcap cap_sys_nice,cap_ipc_lock+ep "$XR_BIN" ||
  die "Nie mozna nadac capabilities RT na $XR_BIN"
getcap "$XR_BIN" | grep -q "cap_ipc_lock,cap_sys_nice=ep\\|cap_sys_nice,cap_ipc_lock=ep" ||
  die "Binarka nie ma wymaganych capabilities RT"

XR_CPU=3
BG_CPUS="0-2"
[ -d "/sys/devices/system/cpu/cpu$XR_CPU" ] || die "Brak wymaganego rdzenia CPU $XR_CPU"

WORKDIR="/dev/shm/rdb-experiment/${RESULTS_ROOT}_${CAMPAIGN}_study_${STUDY_ID}"
RESULTS_DIR="$EXPERIMENT_REPO/$RESULTS_ROOT/$CAMPAIGN/study_$(printf '%02d' "$STUDY_ID")"
[ ! -e "$RESULTS_DIR" ] ||
  die "$RESULTS_DIR juz istnieje; wyniki sa niemutowalne i nie wolno ich nadpisac"
rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"

STREAM_NAME="detect_out"
NC_PORT=$((20000 + STUDY_ID))
CLIENT_PIDS=()
METRICS_PID=""
XRETRACTOR_PID=""
ENGINE_PID=""
NC_PID=""
MONITOR_PID=""
ORIG_GOVERNOR=""

restore_governor() {
  local c
  if [ -n "$ORIG_GOVERNOR" ]; then
    echo "$ORIG_GOVERNOR" |
      sudo -n tee /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor >/dev/null 2>&1 ||
      return 1
    for c in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
      [ "$(cat "$c")" = "$ORIG_GOVERNOR" ] || return 1
    done
    ORIG_GOVERNOR=""
  fi
}

cleanup() {
  local pid
  for pid in "${CLIENT_PIDS[@]:-}"; do
    terminate_process "$pid" || true
  done
  terminate_process "$METRICS_PID" || true
  terminate_process "$XRETRACTOR_PID" || true
  terminate_process "$ENGINE_PID" || true
  terminate_process "$NC_PID" || true
  terminate_process "$MONITOR_PID" || true
  restore_governor || true
  wait 2>/dev/null || true
}
trap cleanup EXIT

set_performance_governor() {
  local gov_file=/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
  local c
  [ -r "$gov_file" ] || die "Brak cpufreq w sysfs"
  ORIG_GOVERNOR=$(cat "$gov_file")
  echo performance |
    sudo -n tee /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor >/dev/null
  for c in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
    [ "$(cat "$c")" = "performance" ] || die "Nie ustawiono governora performance dla $c"
  done
}

snapshot_state() {
  local label="$1" out="$2"
  {
    echo "# Stan maszyny -- $label"
    echo
    echo "- data: $(date -Is)"
    echo "- badanie: experiment=$RESULTS_ROOT campaign=$CAMPAIGN study_id=$STUDY_ID rate_hz=$RATE_HZ clients=$CLIENTS samples=$SAMPLES"
    echo "- commit kodu: $CODE_COMMIT"
    echo "- branch wynikow: $EXPERIMENT_BRANCH"
    echo
    echo '## Build xretractor'
    echo '```'
    "$XR_BIN" --build-info
    echo '```'
    echo '## uname'
    echo '```'; uname -a; echo '```'
    echo '## dystrybucja'
    echo '```'; cat /etc/os-release 2>/dev/null || echo "brak /etc/os-release"; echo '```'
    echo '## CPU'
    echo '```'; lscpu 2>/dev/null || cat /proc/cpuinfo; echo '```'
    echo '## Pamiec'
    echo '```'; free -h; echo '```'
    echo '## Fragmentacja pamieci'
    echo '```'; cat /proc/buddyinfo 2>/dev/null || echo "niedostepne"; echo '```'
    echo '## Load average'
    echo '```'; cat /proc/loadavg; echo '```'
    echo '## Temperatura'
    echo '```'
    for z in /sys/class/thermal/thermal_zone*/temp; do
      [ -r "$z" ] && printf '%s: %d m°C\n' "$z" "$(cat "$z")"
    done
    command -v vcgencmd >/dev/null && echo "throttled: $(vcgencmd get_throttled)"
    echo '```'
    echo '## Kernel cmdline'
    echo '```'; cat /proc/cmdline; echo '```'
    echo '## Governor CPU'
    echo '```'
    for c in /sys/devices/system/cpu/cpu[0-9]*/cpufreq; do
      [ -r "$c/scaling_governor" ] || continue
      printf '%s: governor=%s cur=%s kHz min=%s max=%s kHz\n' \
        "$(basename "$(dirname "$c")")" "$(cat "$c/scaling_governor")" \
        "$(cat "$c/scaling_cur_freq")" "$(cat "$c/scaling_min_freq")" "$(cat "$c/scaling_max_freq")"
    done
    echo '```'
  } > "$out"
}

sample_metrics() {
  local out="$1"
  echo "ts_epoch,load1,mem_used_kb,mem_avail_kb,temp_mC" > "$out"
  while true; do
    local ts load1 mem_used mem_avail temp
    ts=$(date +%s)
    load1=$(cut -d' ' -f1 /proc/loadavg)
    mem_used=$(awk '/MemTotal/{t=$2} /MemAvailable/{a=$2} END{print t-a}' /proc/meminfo)
    mem_avail=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
    temp=""
    for z in /sys/class/thermal/thermal_zone*/temp; do
      [ -r "$z" ] && { temp=$(cat "$z"); break; }
    done
    echo "${ts},${load1},${mem_used},${mem_avail},${temp:-NA}" >> "$out"
    sleep 1
  done
}

log "=== Badanie $RESULTS_ROOT/$CAMPAIGN/$STUDY_ID ==="
cp "$ECG_SRC/rec205" "$ECG_SRC/rec205.desc" "$ECG_SRC/bp_coef.txt" "$ECG_SRC/d_coef.txt" "$WORKDIR/"
sed "s#1/360#1/${RATE_HZ}#" "$ECG_SRC/rec205-detect.rql" > "$WORKDIR/study.rql"
cat > "$WORKDIR/study.toml" <<'EOF'
[scheduling]
rt_priority = 50
EOF

set_performance_governor
snapshot_state "PRZED badaniem" "$WORKDIR/state_before.md"

(
  taskset -p -c "$BG_CPUS" "$BASHPID" >/dev/null 2>&1
  sample_metrics "$WORKDIR/metrics.csv"
) &
METRICS_PID=$!
process_is_running "$METRICS_PID" || die "Sampler metryk nie uruchomil sie"

if [ "$SINK" = "nc" ]; then
  command -v nc >/dev/null || die "Wybrano sink=nc, ale brak nc"
  nc -lk 127.0.0.1 "$NC_PORT" > "$WORKDIR/nc_sink.log" 2>&1 &
  NC_PID=$!
  sleep 0.3
  kill -0 "$NC_PID" 2>/dev/null || die "Nie udalo sie uruchomic nc"
fi

cd "$WORKDIR"
RUN_TIMEOUT=$(( SAMPLES * 30 / 1000 + 120 ))
RDB_BENCH_CSV="$WORKDIR/e1_probe.csv" \
  timeout --kill-after=10s "${RUN_TIMEOUT}s" taskset -c "$XR_CPU" \
  "$XR_BIN" study.rql -k -m "$SAMPLES" -t -g study.toml \
  >"$WORKDIR/xretractor.log" 2>&1 &
XRETRACTOR_PID=$!
sleep 2
kill -0 "$XRETRACTOR_PID" 2>/dev/null || {
  wait_for_required_process "$XRETRACTOR_PID" xretractor || true
  die "xretractor zakonczyl sie przed dolaczeniem klientow"
}
ENGINE_PID=$(pgrep -P "$XRETRACTOR_PID" -x xretractor | sed -n '1p')
[ -n "$ENGINE_PID" ] || die "Nie znaleziono procesu xretractor uruchomionego przez timeout"
ps -eLo pid=,cls=,rtprio= | awk -v pid="$ENGINE_PID" '$1 == pid && $2 == "FF" && $3 == 50 {found=1} END {exit !found}' ||
  die "xretractor nie uruchomil watku SCHED_FIFO 50"

for i in $(seq 1 "$CLIENTS"); do
  if [ "$SINK" = "nc" ]; then
    taskset -c "$BG_CPUS" xqry -s "$STREAM_NAME" -r 2>>"$WORKDIR/xqry_${i}.err" |
      nc -q1 127.0.0.1 "$NC_PORT" &
  else
    taskset -c "$BG_CPUS" xqry -s "$STREAM_NAME" -r >/dev/null 2>>"$WORKDIR/xqry_${i}.err" &
  fi
  CLIENT_PIDS+=("$!")
done

sleep 1
REQUIRED_PROCESSES=(metrics "$METRICS_PID")
if [ -n "$NC_PID" ]; then
  REQUIRED_PROCESSES+=(nc-sink "$NC_PID")
fi
for i in "${!CLIENT_PIDS[@]}"; do
  process_is_running "${CLIENT_PIDS[$i]}" ||
    die "Klient xqry $((i + 1)) nie uruchomil sie"
  REQUIRED_PROCESSES+=("xqry-$((i + 1))" "${CLIENT_PIDS[$i]}")
done
monitor_required_processes "$XRETRACTOR_PID" "${REQUIRED_PROCESSES[@]}" &
MONITOR_PID=$!

wait_for_required_process "$XRETRACTOR_PID" xretractor ||
  die "Badanie przerwane; nie zapisuje niepelnych wynikow"
XRETRACTOR_PID=""
ENGINE_PID=""
wait_for_required_process "$MONITOR_PID" "monitor procesow wymaganych" ||
  die "Proces pomocniczy zakonczyl sie przed xretractor; wynik nie zostanie zatwierdzony"
MONITOR_PID=""
validate_probe_csv "$WORKDIR/e1_probe.csv" "$SAMPLES" ||
  die "Nieprawidlowy plik sondy; wynik nie zostanie zatwierdzony"

for i in "${!CLIENT_PIDS[@]}"; do
  pid="${CLIENT_PIDS[$i]}"
  finalize_required_process "$pid" "xqry-$((i + 1))" ||
    die "Klient xqry $((i + 1)) zakonczyl sie bledem lub nie zostal zatrzymany"
done
CLIENT_PIDS=()
finalize_required_process "$METRICS_PID" "sampler metryk" ||
  die "Sampler metryk zakonczyl sie bledem lub nie zostal zatrzymany"
METRICS_PID=""
finalize_required_process "$NC_PID" "ujscie nc" ||
  die "Ujscie nc zakonczylo sie bledem lub nie zostalo zatrzymane"
NC_PID=""
restore_governor || die "Nie udalo sie przywrocic pierwotnego governora CPU"
snapshot_state "PO badaniu" "$WORKDIR/state_after.md"

mkdir -p "$RESULTS_DIR"
{
  echo "# Wyniki badania $STUDY_ID -- kampania $CAMPAIGN"
  echo
  echo "- data: $(date -Is)"
  echo "- commit kodu: \`$CODE_COMMIT\`"
  echo "- częstosc naplywu: $RATE_HZ Hz"
  echo "- liczba klientow xqry: $CLIENTS (sink=$SINK)"
  echo "- liczba probek: $SAMPLES"
  echo
  echo "## Compute, wake-up i queue-emission latency"
  echo
  echo '```'
  python3 "$ANALYZER" "$WORKDIR/e1_probe.csv" --fs "$RATE_HZ"
  echo '```'
  echo
  echo "Metryka kończy się na emisji do kolejki klienta. Nie jest pełnym application E2E."
  echo
  echo "## Metryki systemowe"
  echo
  echo '```'
  awk -F, 'NR>1{load+=$2; mem+=$3; if($5!="NA"){temp+=$5; n++}; c++}
           END{if(c>0) printf "srednie load1=%.2f mem_used_kb=%.0f", load/c, mem/c;
               if(n>0) printf " temp_mC=%.0f", temp/n; print ""}' "$WORKDIR/metrics.csv"
  echo '```'
} > "$RESULTS_DIR/results.md"

cp "$WORKDIR/state_before.md" "$WORKDIR/state_after.md" \
  "$WORKDIR/e1_probe.csv" "$WORKDIR/metrics.csv" "$WORKDIR/xretractor.log" \
  "$RESULTS_DIR/"
cp "$WORKDIR"/xqry_*.err "$RESULTS_DIR/" 2>/dev/null || true

# Ochrona przed przypadkowym zapisem wyniku do brancha kodu.
[ -z "$(git -C "$CODE_REPO" status --short)" ] ||
  die "Repozytorium kodu zostalo zmienione podczas badania; wynik nie zostanie zatwierdzony"
[ "$(git -C "$CODE_REPO" rev-parse HEAD)" = "$CODE_COMMIT" ] ||
  die "Commit kodu zmienil sie podczas badania"

cat >> "$EXPERIMENT_REPO/JOURNAL.md" <<EOF

## $(date -Is) — $RESULTS_ROOT / $CAMPAIGN / study_$STUDY_ID

- wynik: sukces
- commit kodu: \`$CODE_COMMIT\`
- parametry: rate_hz=$RATE_HZ, clients=$CLIENTS, samples=$SAMPLES, sink=$SINK
- dane: \`$RESULTS_ROOT/$CAMPAIGN/study_$(printf '%02d' "$STUDY_ID")\`
EOF

git -C "$EXPERIMENT_REPO" add "$RESULTS_ROOT/$CAMPAIGN/study_$(printf '%02d' "$STUDY_ID")" JOURNAL.md
MARKER="Experiment-Branch: $EXPERIMENT_BRANCH"
COMMIT_MSG="eksperyment $RESULTS_ROOT: $CAMPAIGN, badanie $STUDY_ID

$MARKER"
git -C "$EXPERIMENT_REPO" log -1 --pretty=%B | grep -qF "$MARKER" ||
  die "Ostatni commit nie nalezy do eksperymentu $EXPERIMENT_BRANCH"
git -C "$EXPERIMENT_REPO" commit --amend -m "$COMMIT_MSG"
git -C "$EXPERIMENT_REPO" push --force-with-lease origin "HEAD:$EXPERIMENT_BRANCH"

rm -rf "$WORKDIR"
log "Badanie $STUDY_ID zakonczone; kod pozostal niezmieniony, wyniki zapisano w rdb-experiment."
