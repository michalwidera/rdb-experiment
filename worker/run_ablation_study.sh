#!/bin/bash
# Pojedyncze badanie kampanii ablacyjnej K6 na workerze: jedna RODZINA
# workloadów, wszystkie jej przypadki × profile × powtórzenia w kolejności
# losowej.
#
# Rate NIE jest parametrem wywołania. Od K6b jest wybierany per rodzina przez
# kalibrację i odczytywany z `results/rate.json`. Powód jest metodologiczny —
# rate globalny (`--scale` z v1) wiązał ze sobą rodziny, między którymi nie
# zachodzi żadne porównanie, i jedna komórka potrafiła zablokować całą kampanię.
# Komórki wykluczone przez kalibrację są pomijane w planie i raportowane imiennie.
#
# Od K6c budżet slotów i częstotliwość strumienia są własnością KOMÓRKI, nie
# rodziny: `W3_d1` i `W3_d3` biegną przy tym samym `scale` z różnym slotem, bo
# przeplot sumuje częstotliwości. Skrypt tych wielkości nie wylicza — czyta je
# z sekcji `cells` w `rate.json`, gdzie zapisała je kalibracja po zapytaniu
# silnika. Wyliczanie ich obok silnika było błędem v2 i przyczyną K6c.
#
# Jeden przebieg `xretractor` daje komplet metryk, bo trzy instrumenty sondy
# działają równocześnie:
#   RDB_BENCH_CSV         -> compute_ns, wake_lag_ns, e2e_ns (sonda E1)
#   RDB_BENCH_PLAN        -> PLAN bench, REWRITE_APPLIED, COMPILE_NS, PLAN capacity
#   RDB_BENCH_MATERIALIZE -> MATERIALIZED trwale/pamieciowe
# Peak RSS i CPU time zbiera próbnik z /proc/PID; checksum artefaktów liczy
# sha256sum po zakończeniu pętli.
#
# Twardy invariant (R2): CODE_REPO jest tylko do odczytu i pozostaje bez zmian,
# również w plikach ignorowanych. Wyniki trafiają wyłącznie do EXPERIMENT_REPO.
set -euo pipefail

# Skrypty kampanii importuja sie nawzajem w katalogu wynikow, wiec bez tego
# kazdy przebieg zostawia __pycache__ w repozytorium wynikow i nastepne
# badanie odmawia startu na kontroli czystosci.
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_EXPERIMENT_REPO="$(cd "$SCRIPT_DIR/.." && pwd)"

CODE_REPO="/home/michal/retractordb"
EXPERIMENT_REPO="$DEFAULT_EXPERIMENT_REPO"
CODE_COMMIT=""
EXPERIMENT_BRANCH=""
RESULTS_ROOT=""
CAMPAIGN="ablation"
STUDY_ID=""
FAMILY=""
REPS=""

while [ $# -gt 0 ]; do
  case "$1" in
    --code-repo) CODE_REPO="$2"; shift 2 ;;
    --experiment-repo) EXPERIMENT_REPO="$2"; shift 2 ;;
    --code-commit) CODE_COMMIT="$2"; shift 2 ;;
    --experiment-branch) EXPERIMENT_BRANCH="$2"; shift 2 ;;
    --results-root) RESULTS_ROOT="$2"; shift 2 ;;
    --campaign) CAMPAIGN="$2"; shift 2 ;;
    --study-id) STUDY_ID="$2"; shift 2 ;;
    --family) FAMILY="$2"; shift 2 ;;
    --reps) REPS="$2"; shift 2 ;;
    *) printf 'Nieznana opcja: %s\n' "$1" >&2; exit 1 ;;
  esac
done

# shellcheck source=../lib/common.sh
source "$EXPERIMENT_REPO/lib/common.sh"

[ -n "$CODE_COMMIT" ] || die "Brak --code-commit"
[ -n "$EXPERIMENT_BRANCH" ] || die "Brak --experiment-branch"
[ -n "$RESULTS_ROOT" ] || die "Brak --results-root"
[ -n "$STUDY_ID" ] || die "Brak --study-id"
[ -n "$FAMILY" ] || die "Brak --family"
[ -n "$REPS" ] || die "Brak --reps"
validate_results_root "$RESULTS_ROOT" || exit 1
validate_campaign_name "$CAMPAIGN" || exit 1
validate_git_branch "$EXPERIMENT_BRANCH" "brancha wynikow" || exit 1
validate_safe_absolute_path "$CODE_REPO" "repozytorium kodu" || exit 1
validate_safe_absolute_path "$EXPERIMENT_REPO" "repozytorium wynikow" || exit 1
[[ "$CODE_COMMIT" =~ ^[0-9a-f]{40}$ ]] || die "code-commit musi byc pelnym SHA-1"
[[ "$STUDY_ID" =~ ^[0-9]+$ ]] || die "study-id musi byc liczba"
[[ "$FAMILY" =~ ^W[0-9]+$ ]] || die "family musi miec postac W<liczba>"
[[ "$REPS" =~ ^[0-9]+$ ]] && [ "$REPS" -ge 2 ] || die "reps musi byc >= 2"

[ -d "$CODE_REPO/.git" ] || die "Brak repozytorium kodu: $CODE_REPO"
[ -d "$EXPERIMENT_REPO/.git" ] || die "Brak repozytorium wynikow: $EXPERIMENT_REPO"
require_disjoint_repositories "$CODE_REPO" "$EXPERIMENT_REPO" || exit 1
[ "$(git -C "$CODE_REPO" rev-parse HEAD)" = "$CODE_COMMIT" ] ||
  die "Repozytorium kodu nie wskazuje wymaganego commita $CODE_COMMIT"
# R2 utwardzone: kontrola obejmuje pliki ignorowane, bo `git status --short`
# jest na nie slepy (defekt wykryty 2026-07-30).
require_input_dirs_pristine "$CODE_REPO" examples/ecg || exit 1
CODE_FINGERPRINT=$(mktemp)
code_tree_fingerprint "$CODE_REPO" "$CODE_FINGERPRINT" || exit 1

git -C "$EXPERIMENT_REPO" fetch origin "$EXPERIMENT_BRANCH" --quiet
[ -z "$(git -C "$EXPERIMENT_REPO" status --short)" ] || die "Repozytorium wynikow workera nie jest czyste"
git -C "$EXPERIMENT_REPO" checkout -B "$EXPERIMENT_BRANCH" "origin/$EXPERIMENT_BRANCH" >/dev/null

CAMPAIGN_DIR="$EXPERIMENT_REPO/$RESULTS_ROOT"
MATRIX="$CAMPAIGN_DIR/matrix.tsv"
PROFILES="$CAMPAIGN_DIR/profiles.tsv"
RATE_JSON="$CAMPAIGN_DIR/results/rate.json"
[ -f "$MATRIX" ] || die "Brak macierzy: $MATRIX"
[ -f "$PROFILES" ] || die "Brak profili: $PROFILES"
[ -f "$RATE_JSON" ] || die "Brak $RATE_JSON; Tier B wymaga wykonanej kalibracji K6c.0"

# Rate rodziny pochodzi wylacznie z kalibracji. GEN_SCALE jest mnoznikiem
# przekazywanym generatorowi; dla rodzin o rate'cie z deklaracji zrodla (W8)
# generator go ignoruje, ale mnoznik i tak pochodzi z rate.json, zeby kalibracja
# i Tier B generowaly te same pliki.
#
# ZMIANA v3: budzet slotow i czestotliwosc strumienia sa wlasnoscia KOMORKI,
# nie rodziny -- W3_d1 i W3_d3 maja rozny slot przy tym samym scale. Czytamy je
# z sekcji `cells`. Skrypt nie wylicza slotu; wylicza go silnik, a kalibracja
# tylko zapisuje.
declare -A CELL_SLOTS CELL_STREAM_HZ
eval "$(python3 - "$RATE_JSON" "$FAMILY" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
if int(data.get("version", 0)) < 3:
    sys.exit("rate.json jest w wersji starszej niz 3 -- brak slotu per komorka")
family = sys.argv[2]
entry = data.get("families", {}).get(family)
if entry is None:
    sys.exit(f"rate.json nie zawiera rodziny {family}")
cells = {name: cell for name, cell in data.get("cells", {}).items() if cell["family"] == family}
if not cells:
    sys.exit(f"rate.json nie zawiera ani jednej komorki rodziny {family}")
# Dwa rodzaje wykluczen o roznej semantyce, raportowane osobno:
#   excluded_cases          -- kalibracja: komorka nie miesci sie w budzecie 0,5*slot
#   decision_excluded_cases -- decyzja czlowieka (np. W8_Q32: przeciazenie rodziny
#                              ze zrodla, gdzie "budzet przy s=1" nie ma sensu)
# Do skipu w planie licza sie oba (suma); do raportu -- kazdy pod wlasna etykieta,
# zeby results.md/JOURNAL nie opisaly decyzji jako wykluczenia kalibracyjnego.
excluded_calib = sorted(e["case"] for e in data.get("excluded_cases", []) if e["family"] == family)
excluded_decision = sorted(e["case"] for e in data.get("decision_excluded_cases", []) if e["family"] == family)
excluded = sorted(set(excluded_calib) | set(excluded_decision))
print(f"SCALE_TEXT={entry['scale']}")
print(f"GEN_SCALE={entry['scale']}")
print(f"F_PHI_HZ={entry['generator_f_phi_hz']:.6g}")
print(f"EXCLUDED='{','.join(excluded)}'")
print(f"EXCLUDED_CALIB='{','.join(excluded_calib)}'")
print(f"EXCLUDED_DECISION='{','.join(excluded_decision)}'")
for name, cell in sorted(cells.items()):
    print(f"CELL_SLOTS[{name}]={int(cell['slots'])}")
    print(f"CELL_STREAM_HZ[{name}]={cell['stream_hz']:.6g}")
PY
)" || die "Nie udalo sie odczytac rate'u rodziny $FAMILY z $RATE_JSON"
[[ "$GEN_SCALE" =~ ^(36|24|12|6|3|1)$ ]] || die "scale $GEN_SCALE spoza zamrozonej drabiny"
[ "${#CELL_SLOTS[@]}" -gt 0 ] || die "rate.json nie dal ani jednej komorki rodziny $FAMILY"
for cell in "${!CELL_SLOTS[@]}"; do
  [[ "${CELL_SLOTS[$cell]}" =~ ^[0-9]+$ ]] &&
    [ "${CELL_SLOTS[$cell]}" -ge 400 ] && [ "${CELL_SLOTS[$cell]}" -le 6000 ] ||
    die "$cell: slots=${CELL_SLOTS[$cell]} poza zamrozonym zakresem [400, 6000]"
done
log "rodzina $FAMILY: scale=$SCALE_TEXT f_phi generatora=$F_PHI_HZ Hz komorek=${#CELL_SLOTS[@]} wykluczone_kalibracja='${EXCLUDED_CALIB:-}' wykluczone_decyzja='${EXCLUDED_DECISION:-}'"
CELL_BUDGETS=""
for cell in $(printf '%s\n' "${!CELL_SLOTS[@]}" | sort); do
  log "  $cell: slotow=${CELL_SLOTS[$cell]} strumien=${CELL_STREAM_HZ[$cell]} Hz"
  CELL_BUDGETS="${CELL_BUDGETS:+$CELL_BUDGETS; }$cell=${CELL_SLOTS[$cell]} slotow@${CELL_STREAM_HZ[$cell]} Hz"
done

command -v xqry >/dev/null || die "xqry nie jest na PATH"
# `xqry` na PATH jest czescia aparatury pomiarowej: kampania czyta z niego
# interwal strumienia (`-t`, pole `delta`), a w Tier B podlacza go jako klienta.
# Staly klient z innego commita przeszedlby kontrole `command -v` i po cichu
# wrocilby z defektem, dla ktorego naprawy zatrzymano K6b. `--help` wypisuje
# `Branch: <branch>:<short-sha>` ustalone przy KONFIGURACJI cmake, wiec kontrola
# wykrywa podmieniona binarke, a nie przebudowe bez rekonfiguracji -- i to jest
# jej zadeklarowany zakres.
XQRY_COMMIT=$(xqry --help 2>&1 | sed -n 's/.*Branch: [^:]*:\([0-9a-f]\{7,\}\).*/\1/p' | head -1)
[ -n "$XQRY_COMMIT" ] || die "nie udalo sie ustalic commita klienta xqry"
case "$CODE_COMMIT" in
  "$XQRY_COMMIT"*) ;;
  *) die "xqry pochodzi z commita $XQRY_COMMIT, a kampania z $CODE_COMMIT" ;;
esac
log "klient xqry: $XQRY_COMMIT (zgodny z przypieciem)"

command -v taskset >/dev/null || die "Brak taskset"
command -v getcap >/dev/null || die "Brak getcap"
command -v sha256sum >/dev/null || die "Brak sha256sum"
sudo -n true 2>/dev/null || die "Badanie RT wymaga bezhaslowego sudo"
require_tmpfs /dev/shm || exit 1
uname -v | grep -q PREEMPT_RT || die "Kernel workera nie jest buildem PREEMPT_RT"

XR_CPU=3
BG_CPUS="0-2"
[ -d "/sys/devices/system/cpu/cpu$XR_CPU" ] || die "Brak wymaganego rdzenia CPU $XR_CPU"

WORKDIR="/dev/shm/rdb-k6/${RESULTS_ROOT}_${CAMPAIGN}_${FAMILY}"
RESULTS_DIR="$CAMPAIGN_DIR/$CAMPAIGN/study_$(printf '%02d' "$STUDY_ID")_$FAMILY"
[ ! -e "$RESULTS_DIR" ] ||
  die "$RESULTS_DIR juz istnieje; wyniki sa niemutowalne i nie wolno ich nadpisac"
rm -rf "$WORKDIR"
mkdir -p "$WORKDIR/runs"

WORKLOADS="$WORKDIR/workloads"
ORIG_GOVERNOR=""
METRICS_PID=""
CLIENT_PID=""
ENGINE_WRAPPER_PID=""
SAMPLER_PID=""

restore_governor() {
  local c
  if [ -n "$ORIG_GOVERNOR" ]; then
    echo "$ORIG_GOVERNOR" |
      sudo -n tee /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor >/dev/null 2>&1 || return 1
    for c in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
      [ "$(cat "$c")" = "$ORIG_GOVERNOR" ] || return 1
    done
    ORIG_GOVERNOR=""
  fi
}

STUDY_OK=0

# R14: dowod porazki nie moze byc zachowany w gorszej formie niz dowod sukcesu.
# Przy przerwanym badaniu surowe przebiegi trafiaja do results/evidence/ i sa
# pakowane tak samo jak przy sukcesie.
preserve_evidence() {
  [ -d "$WORKDIR/runs" ] || return 0
  local evidence="$CAMPAIGN_DIR/results/evidence/${CAMPAIGN}_study_$(printf '%02d' "$STUDY_ID")_$FAMILY"
  mkdir -p "$(dirname "$evidence")" || return 0
  rm -rf "$evidence"
  cp -r "$WORKDIR/runs" "$evidence" 2>/dev/null || return 0
  [ -f "$WORKDIR/runs.csv" ] && cp "$WORKDIR/runs.csv" "$evidence/" 2>/dev/null
  python3 "$EXPERIMENT_REPO/lib/artifacts.py" pack "$evidence" >&2 2>/dev/null || true
  log "dowod porazki zachowany w $evidence"
}

cleanup() {
  local status=$?
  terminate_process "$CLIENT_PID" || true
  terminate_process "$ENGINE_WRAPPER_PID" || true
  terminate_process "$SAMPLER_PID" || true
  terminate_process "$METRICS_PID" || true
  restore_governor || true
  wait 2>/dev/null || true
  [ "$STUDY_OK" -eq 1 ] || preserve_evidence
  return "$status"
}
trap cleanup EXIT

set_performance_governor() {
  local gov_file=/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
  local c
  [ -r "$gov_file" ] || die "Brak cpufreq w sysfs"
  ORIG_GOVERNOR=$(cat "$gov_file")
  echo performance | sudo -n tee /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor >/dev/null
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
    echo "- badanie: experiment=$RESULTS_ROOT campaign=$CAMPAIGN study_id=$STUDY_ID rodzina=$FAMILY"
    echo "- parametry: reps=$REPS scale=$SCALE_TEXT f_phi generatora=$F_PHI_HZ Hz"
    echo "- budzet slotow per komorka: $CELL_BUDGETS"
    echo "- commit kodu: $CODE_COMMIT"
    echo "- branch wynikow: $EXPERIMENT_BRANCH"
    echo
    echo '## uname'
    echo '```'; uname -a; echo '```'
    echo '## CPU'
    echo '```'; lscpu 2>/dev/null || cat /proc/cpuinfo; echo '```'
    echo '## Pamiec'
    echo '```'; free -h; echo '```'
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
      printf '%s: governor=%s cur=%s kHz\n' "$(basename "$(dirname "$c")")" \
        "$(cat "$c/scaling_governor")" "$(cat "$c/scaling_cur_freq")"
    done
    echo '```'
  } > "$out"
}

sample_metrics() {
  local out="$1"
  echo "ts_epoch,load1,mem_used_kb,temp_mC" > "$out"
  while true; do
    local ts load1 mem_used temp=""
    ts=$(date +%s)
    load1=$(cut -d' ' -f1 /proc/loadavg)
    mem_used=$(awk '/MemTotal/{t=$2} /MemAvailable/{a=$2} END{print t-a}' /proc/meminfo)
    for z in /sys/class/thermal/thermal_zone*/temp; do
      [ -r "$z" ] && { temp=$(cat "$z"); break; }
    done
    echo "${ts},${load1},${mem_used},${temp:-NA}" >> "$out"
    sleep 1
  done
}

# Próbnik zasobów procesu silnika. VmHWM jest monotoniczne, więc próbkowanie
# daje maksimum z dokładnością ostatniego odczytu; utime+stime bierzemy
# z ostatniego udanego odczytu, bo /proc/PID znika razem z procesem.
sample_process() {
  local pid="$1" out="$2"
  local hwm=0 utime=0 stime=0 value fields
  while [ -r "/proc/$pid/status" ]; do
    value=$(awk '/^VmHWM:/{print $2}' "/proc/$pid/status" 2>/dev/null || true)
    [ -n "$value" ] && [ "$value" -gt "$hwm" ] 2>/dev/null && hwm=$value
    # shellcheck disable=SC2207
    fields=($(awk '{print $14, $15}' "/proc/$pid/stat" 2>/dev/null || true))
    if [ "${#fields[@]}" -eq 2 ]; then
      utime=${fields[0]}
      stime=${fields[1]}
    fi
    printf 'vmhwm_kb=%s\nutime_ticks=%s\nstime_ticks=%s\n' "$hwm" "$utime" "$stime" > "$out"
    sleep 0.05
  done
  printf 'vmhwm_kb=%s\nutime_ticks=%s\nstime_ticks=%s\n' "$hwm" "$utime" "$stime" > "$out"
}

# --- przygotowanie workloadów ------------------------------------------------
log "generuje workloady rodziny $FAMILY (scale=$GEN_SCALE)"
python3 "$CAMPAIGN_DIR/generate.py" --output "$WORKLOADS" --scale "$GEN_SCALE" >/dev/null

# Komorki wykluczone przez kalibracje wypadaja z Tier B. Sa raportowane
# imiennie w results.md i w rate.json, nie pomijane po cichu.
readarray -t MATRIX_ROWS < <(
  awk -F'\t' -v fam="$FAMILY" -v skip=",${EXCLUDED:-}," \
    'NR>1 && $1==fam && index(skip, ","$2",")==0 {print}' "$MATRIX"
)
[ "${#MATRIX_ROWS[@]}" -gt 0 ] ||
  die "Macierz nie zawiera rodziny $FAMILY albo wszystkie jej komorki sa wykluczone"

# Lista przebiegów: (przypadek, profil, powtorzenie) w kolejności losowej.
# Ziarno pochodzi z rodziny, nie z zegara — kolejność jest odtwarzalna.
PLAN_FILE="$WORKDIR/plan.tsv"
python3 - "$FAMILY" "$REPS" "$PLAN_FILE" <<'PY' "${MATRIX_ROWS[@]}"
import random, sys
family, reps, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
rows = sys.argv[4:]
runs = []
for row in rows:
    case, profiles, stream = row.split("\t")[1], row.split("\t")[2], row.split("\t")[3]
    for profile in profiles.split(","):
        for rep in range(1, reps + 1):
            runs.append((case, profile, rep, stream))
random.Random(f"20260730-{family}").shuffle(runs)
with open(out, "w", encoding="utf-8") as handle:
    for case, profile, rep, stream in runs:
        handle.write(f"{case}\t{profile}\t{rep}\t{stream}\n")
print(len(runs))
PY
TOTAL_RUNS=$(wc -l < "$PLAN_FILE")
[ "$TOTAL_RUNS" -gt 0 ] || die "Plan przebiegow jest pusty"
log "rodzina $FAMILY: $TOTAL_RUNS przebiegow"

set_performance_governor
snapshot_state "PRZED badaniem" "$WORKDIR/state_before.md"

(
  taskset -p -c "$BG_CPUS" "$BASHPID" >/dev/null 2>&1
  sample_metrics "$WORKDIR/metrics.csv"
) &
METRICS_PID=$!
process_is_running "$METRICS_PID" || die "Sampler metryk nie uruchomil sie"

RUNS_CSV="$WORKDIR/runs.csv"
echo "case,profile,rep,scale,f_phi_hz,stream_hz,samples,exit_code,compute_median_ns,compute_p99_ns,compute_max_ns,compute_sum_ns,wake_p999_ns,e2e_p50_ns,e2e_p99_ns,e2e_p999_ns,e2e_max_ns,vmhwm_kb,cpu_ticks,compile_ns,probe_ns,r1,r2,nodes_public,nodes_substrates,tokens_from,tokens_fields,capacity_streams,capacity_sum,capacity_max,mat_bytes,mat_mem_bytes,artifacts_sha256,artifact_count,wall_ms" > "$RUNS_CSV"

executed=0
# Plan czytamy z deskryptora 9, a nie ze stdin. Procesy potomne uruchamiane
# w tej petli dziedzicza stdin, wiec przy `done < plan.tsv` klient xqry dostawal
# plik planu jako wejscie, czytal go do konca i konczyl sie kodem 0 -- badanie
# padalo na "klient xqry nie uruchomil sie". Drugi, cichszy skutek byl gorszy:
# potomek KONSUMOWAL plan, wiec petla gubila przebiegi.
while IFS=$'\t' read -r case profile rep stream <&9; do
  binary="$CODE_REPO/build/K6-$profile/src/retractor/xretractor"
  [ -x "$binary" ] || die "Brak binarki profilu $profile: $binary"
  getcap "$binary" | grep -q "cap_ipc_lock,cap_sys_nice=ep\|cap_sys_nice,cap_ipc_lock=ep" ||
    die "Binarka $binary nie ma capabilities RT"

  # Budzet slotow tej komorki, nie rodziny. Brak wpisu jest bledem, nie
  # okazja do wyliczenia wartosci zastepczej.
  SAMPLES="${CELL_SLOTS[$case]:-}"
  STREAM_HZ="${CELL_STREAM_HZ[$case]:-}"
  [ -n "$SAMPLES" ] && [ -n "$STREAM_HZ" ] || die "$case: brak budzetu slotow w rate.json"

  run_tag="${case}_${profile}_r$(printf '%02d' "$rep")"
  run_dir="$WORKDIR/runs/$run_tag"
  rm -rf "$run_dir"
  mkdir -p "$run_dir/temp"
  cp "$WORKLOADS/$case/query.rql" "$run_dir/query.rql"
  # R2: dane wejsciowe KOPIOWANE, nie symlinkowane.
  if [ -f "$WORKLOADS/$case/external_data.txt" ]; then
    while read -r relative; do
      [ -n "$relative" ] || continue
      cp "$CODE_REPO/$relative" "$run_dir/$(basename "$relative")"
    done < "$WORKLOADS/$case/external_data.txt"
  fi
  for extra in "$WORKLOADS/$case"/*.txt; do
    [ -f "$extra" ] || continue
    [ "$(basename "$extra")" = "external_data.txt" ] && continue
    cp "$extra" "$run_dir/"
  done
  cat > "$run_dir/study.toml" <<'EOF'
[scheduling]
rt_priority = 50
EOF

  run_timeout=$(( SAMPLES / 20 + 180 ))
  started_ms=$(date +%s%3N)
  (
    cd "$run_dir"
    RDB_BENCH_CSV="$run_dir/e1_probe.csv" \
    RDB_BENCH_PLAN=1 \
    RDB_BENCH_MATERIALIZE=1 \
      exec timeout --kill-after=10s "${run_timeout}s" taskset -c "$XR_CPU" \
      "$binary" query.rql -r -k -m "$SAMPLES" -t -g study.toml \
      >"$run_dir/xretractor.log" 2>&1 </dev/null
  ) &
  ENGINE_WRAPPER_PID=$!

  sleep 2
  kill -0 "$ENGINE_WRAPPER_PID" 2>/dev/null || {
    cat "$run_dir/xretractor.log" >&2 || true
    die "$run_tag: xretractor zakonczyl sie przed dolaczeniem klienta"
  }
  # Podpowloka zostala zastapiona przez `exec timeout`, wiec ENGINE_WRAPPER_PID
  # jest procesem `timeout`, a silnik jest jego jedynym dzieckiem.
  engine_pid=$(pgrep -P "$ENGINE_WRAPPER_PID" -x xretractor | sed -n '1p')
  [ -n "$engine_pid" ] || die "$run_tag: nie znaleziono procesu xretractor"
  ps -eLo pid=,cls=,rtprio= | awk -v pid="$engine_pid" '$1 == pid && $2 == "FF" && $3 == 50 {f=1} END {exit !f}' ||
    die "$run_tag: xretractor nie uruchomil watku SCHED_FIFO 50"

  sample_process "$engine_pid" "$run_dir/process.txt" </dev/null &
  SAMPLER_PID=$!

  taskset -c "$BG_CPUS" xqry -s "$stream" -r >/dev/null 2>"$run_dir/xqry.err" </dev/null &
  CLIENT_PID=$!
  sleep 1
  # Protokol dolaczania klienta (sleep 2 -> start -> sleep 1 -> kontrola) trwa
  # ~3 s i milczaco zakladal, ze tyle najmniej trwa przebieg. `W3_d3` trwa
  # 3,05 s i przegrywal ten wyscig o 9 ms: silnik konczyl sie SAM, klient
  # konczyl sie za nim kodem 0, a kontrola zywotnosci czytala to jako "klient
  # nie uruchomil sie". Wyscig, wiec awaria byla losowa, nie powtarzalna.
  #
  # Rozroznienie, ktorego brakowalo: klient nieobecny przy DZIALAJACYM silniku
  # to awaria; klient nieobecny po ZAKONCZONYM silniku to normalny koniec
  # krotkiego przebiegu -- pod warunkiem, ze wyszedl zerem.
  if ! process_is_running "$CLIENT_PID"; then
    process_is_running "$ENGINE_WRAPPER_PID" && {
      cat "$run_dir/xqry.err" >&2 || true
      die "$run_tag: klient xqry zniknal, choc silnik nadal dziala"
    }
    client_status=0
    wait "$CLIENT_PID" || client_status=$?
    CLIENT_PID=""
    [ "$client_status" -eq 0 ] || {
      cat "$run_dir/xqry.err" >&2 || true
      die "$run_tag: klient xqry zakonczyl sie kodem $client_status"
    }
  fi

  exit_code=0
  wait "$ENGINE_WRAPPER_PID" || exit_code=$?
  ENGINE_WRAPPER_PID=""
  finished_ms=$(date +%s%3N)
  wait "$SAMPLER_PID" 2>/dev/null || true
  SAMPLER_PID=""
  if [ -n "$CLIENT_PID" ]; then
    finalize_required_process "$CLIENT_PID" "xqry" ||
      die "$run_tag: klient xqry zakonczyl sie bledem lub nie zostal zatrzymany"
    CLIENT_PID=""
  fi

  [ "$exit_code" -eq 0 ] || {
    tail -20 "$run_dir/xretractor.log" >&2 || true
    die "$run_tag: xretractor zakonczyl sie kodem $exit_code"
  }
  validate_probe_csv "$run_dir/e1_probe.csv" "$SAMPLES" ||
    die "$run_tag: nieprawidlowy plik sondy"

  python3 "$CAMPAIGN_DIR/summarize_run.py" \
    --run-dir "$run_dir" \
    --case "$case" --profile "$profile" --rep "$rep" \
    --scale "$SCALE_TEXT" --f-phi-hz "$F_PHI_HZ" --stream-hz "$STREAM_HZ" \
    --samples "$SAMPLES" --exit-code "$exit_code" \
    --wall-ms "$((finished_ms - started_ms))" \
    --append "$RUNS_CSV" ||
    die "$run_tag: podsumowanie przebiegu nie powiodlo sie"

  # R14 regula 2: sukces jest skrotem. Artefakty strumieni sa juz sprowadzone do
  # checksumu w runs.csv, wiec nie musza wchodzic do archiwum -- surowym dowodem
  # pomiaru jest sonda E1 i log silnika, nie 840 kopii tych samych danych.
  rm -rf "$run_dir/temp"

  executed=$((executed + 1))
  log "[$executed/$TOTAL_RUNS] $run_tag"
done 9< "$PLAN_FILE"

# Regula zliczania: liczba wykonanych przebiegow musi zgadzac sie z planem.
[ "$executed" -eq "$TOTAL_RUNS" ] ||
  die "Wykonano $executed przebiegow z $TOTAL_RUNS zaplanowanych"

terminate_process "$METRICS_PID" || true
METRICS_PID=""
restore_governor || die "Nie udalo sie przywrocic pierwotnego governora CPU"
snapshot_state "PO badaniu" "$WORKDIR/state_after.md"

# R2: repozytorium kodu bez zmian, rowniez w plikach ignorowanych.
require_code_tree_unchanged "$CODE_REPO" "$CODE_FINGERPRINT" ||
  die "Repozytorium kodu zmienilo sie podczas badania; wynik nie zostanie zatwierdzony"
require_input_dirs_pristine "$CODE_REPO" examples/ecg ||
  die "Badanie zostawilo artefakty w katalogu wejsciowym repozytorium kodu"
rm -f "$CODE_FINGERPRINT"

mkdir -p "$RESULTS_DIR"
cp "$WORKDIR/state_before.md" "$WORKDIR/state_after.md" "$WORKDIR/metrics.csv" \
  "$WORKDIR/runs.csv" "$WORKDIR/plan.tsv" "$RESULTS_DIR/"

# R14: surowe artefakty i sondy pojedynczych przebiegow do archiwum z indeksem.
# shellcheck source=../lib/artifacts.sh
source "$EXPERIMENT_REPO/lib/artifacts.sh"
cp -r "$WORKDIR/runs" "$RESULTS_DIR/raw"
artifacts_pack "$RESULTS_DIR/raw" || die "Nie udalo sie spakowac artefaktow surowych"

{
  echo "# Badanie $STUDY_ID -- rodzina $FAMILY"
  echo
  echo "- data: $(date -Is)"
  echo "- commit kodu: \`$CODE_COMMIT\`"
  echo "- przebiegow: $executed (plan: $TOTAL_RUNS)"
  echo "- powtorzen na komorke: $REPS, scale: $SCALE_TEXT, f_phi generatora: $F_PHI_HZ Hz"
  echo "- budzet slotow per komorka (slot z silnika): $CELL_BUDGETS"
  echo "- komorki wykluczone przez kalibracje: ${EXCLUDED_CALIB:-brak}"
  echo "- komorki wykluczone decyzja: ${EXCLUDED_DECISION:-brak}"
  echo
  echo "Metryka konczy sie na emisji do kolejki klienta. Nie jest pelnym application E2E."
  echo
  echo '## Mediany compute_ns na komorke'
  echo
  echo '```'
  python3 - "$RESULTS_DIR/runs.csv" <<'PY'
import csv, statistics, sys
rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
cells = {}
for row in rows:
    cells.setdefault((row["case"], row["profile"]), []).append(int(row["compute_median_ns"]))
for (case, profile), values in sorted(cells.items()):
    print(f"{case:12s} {profile:12s} n={len(values):2d} mediana={statistics.median(values):>10.0f} ns")
PY
  echo '```'
} > "$RESULTS_DIR/results.md"

# R4 trzyma JEDEN commit kampanii, wiec kazdy push wykonany gdziekolwiek indziej
# w trakcie badania przesuwa wierzcholek i `--force-with-lease` slusznie odmawia.
# Bez tego kroku 19 minut poprawnego pomiaru przepadalo na samym commicie.
# Wyniki sa NOWYMI sciezkami, wiec `checkout -B` ich nie rusza; wpis do JOURNAL.md
# powstaje dopiero PO odswiezeniu, na swiezej wersji pliku.
git -C "$EXPERIMENT_REPO" fetch origin "$EXPERIMENT_BRANCH" --quiet ||
  die "Nie udalo sie odswiezyc brancha wynikow przed commitem"
git -C "$EXPERIMENT_REPO" checkout -B "$EXPERIMENT_BRANCH" "origin/$EXPERIMENT_BRANCH" --quiet ||
  die "Nie udalo sie przeniesc wynikow na aktualny wierzcholek brancha"
[ -d "$RESULTS_DIR" ] ||
  die "Odswiezenie brancha usunelo katalog wynikow $RESULTS_DIR"

cat >> "$EXPERIMENT_REPO/JOURNAL.md" <<EOF

## $(date -Is) — $RESULTS_ROOT / $CAMPAIGN / study_$STUDY_ID ($FAMILY)

- wynik: sukces
- commit kodu: \`$CODE_COMMIT\`
- parametry: rodzina=$FAMILY, reps=$REPS, scale=$SCALE_TEXT, f_phi generatora=$F_PHI_HZ Hz
- budzet slotow per komorka: $CELL_BUDGETS
- komorki wykluczone przez kalibracje: ${EXCLUDED_CALIB:-brak}
- komorki wykluczone decyzja: ${EXCLUDED_DECISION:-brak}
- przebiegow: $executed
- dane: \`$RESULTS_ROOT/$CAMPAIGN/study_$(printf '%02d' "$STUDY_ID")_$FAMILY\`
EOF

git -C "$EXPERIMENT_REPO" add "$RESULTS_ROOT" JOURNAL.md
MARKER="Experiment-Branch: $EXPERIMENT_BRANCH"
git -C "$EXPERIMENT_REPO" log -1 --pretty=%B | grep -qF "$MARKER" ||
  die "Ostatni commit nie nalezy do eksperymentu $EXPERIMENT_BRANCH"
git -C "$EXPERIMENT_REPO" commit --amend --no-edit --quiet
git -C "$EXPERIMENT_REPO" push --force-with-lease origin "HEAD:$EXPERIMENT_BRANCH" ||
  die "Push wynikow odrzucony; pomiar jest w drzewie roboczym workera i nie zostal utracony"

STUDY_OK=1
rm -rf "$WORKDIR"
log "Badanie $STUDY_ID ($FAMILY) zakonczone; kod pozostal niezmieniony."
