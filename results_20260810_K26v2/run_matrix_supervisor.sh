#!/usr/bin/env bash
# Nadzorca P8 K26v2: screen na hoscie i workerze, krotkie polaczenia SSH.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKER_SSH="${WORKER_SSH:-michal@192.168.88.13}"
SSH_CONFIG="${RDB_SSH_CONFIG:-/dev/null}"
REMOTE_CAMPAIGN_DIR="${REMOTE_CAMPAIGN_DIR:-/home/michal/rdb-experiment/results_20260810_K26v2}"
REMOTE_CODE_REPO="${REMOTE_CODE_REPO:-/home/michal/K26v2}"
REMOTE_P6_RDB="${REMOTE_P6_RDB:-/home/michal/k26v2_gates_rdb}"
REMOTE_P8_OUT="${REMOTE_P8_OUT:-/home/michal/k26v2_p8}"
REMOTE_ARCHIVES="${REMOTE_ARCHIVES:-/home/michal/k26v2_archives}"
REMOTE_CONTROL="${REMOTE_CONTROL:-/home/michal/k26v2_control}"
HOST_ARCHIVES="${HOST_ARCHIVES:-$HOME/k26v2_archives}"
SCREEN_PREFIX="${WORKER_SCREEN_PREFIX:-K26v2-P8}"
POLL_SECONDS="${POLL_SECONDS:-60}"
CPU="${CPU:-3}"

SSH_OPTIONS=(-F "$SSH_CONFIG" -o BatchMode=yes -o ConnectTimeout=8 \
  -o ServerAliveInterval=15 -o ServerAliveCountMax=3)

fail() { echo "BLAD NADZORCY: $*" >&2; exit 2; }
ssh_run() { ssh "${SSH_OPTIONS[@]}" "$WORKER_SSH" "$@"; }

wait_worker() {
  local deadline=$((SECONDS + 600))
  until ssh_run true 2>/dev/null; do
    (( SECONDS < deadline )) || fail "worker nie wrocil po restarcie"
    sleep 10
  done
  sleep 15
}

set_governor() {
  ssh_run "sudo -n sh -c 'for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance >\"\$f\"; done'"
}

launch_family() {
  local family="$1" session="$SCREEN_PREFIX-$1"
  local out="$REMOTE_P8_OUT/$family" control="$REMOTE_CONTROL/$family"
  local archive="$REMOTE_ARCHIVES/K26v2-P8-$family.tar.gz"
  local archive_sum="$REMOTE_ARCHIVES/K26v2-P8-$family.sha256"
  ssh_run "set -eu
command -v screen >/dev/null
if screen -S '$session' -Q select . >/dev/null 2>&1; then
  echo 'sesja screen $session juz istnieje' >&2; exit 2
fi
for path in '$out' '$control' '$archive' '$archive_sum'; do
  if [ -e \"\$path\" ]; then echo \"artefakt juz istnieje: \$path\" >&2; exit 2; fi
done
mkdir -p '$control'
screen -DmS '$session' '$REMOTE_CAMPAIGN_DIR/run_matrix_family.sh' \
  '$family' '$CPU' '$REMOTE_CODE_REPO' '$REMOTE_P6_RDB' '$out' '$REMOTE_ARCHIVES' '$control'
sleep 1
if ! screen -S '$session' -Q select . >/dev/null 2>&1 && [ ! -r '$control/runner.rc' ]; then
  echo 'sesja screen $session nie wystartowala' >&2; exit 2
fi"
  echo "START: $family w screen workera $session"
}

family_status() {
  local family="$1" session="$SCREEN_PREFIX-$1"
  local out="$REMOTE_P8_OUT/$family" control="$REMOTE_CONTROL/$family"
  ssh_run "if screen -S '$session' -Q select . >/dev/null 2>&1; then screen_live=1; else screen_live=0; fi
if [ -r '$control/runner.rc' ]; then rc=\$(cat '$control/runner.rc'); else rc=running; fi
if [ -r '$out/RUN_COMPLETE' ]; then complete=1; else complete=0; fi
if [ -r '$out/STOP-8' ]; then stop8=1; else stop8=0; fi
if [ -d '$out/raw' ]; then cells=\$(find '$out/raw' -type f -name summary.tsv | wc -l); else cells=0; fi
temp=unknown; for f in /sys/class/thermal/thermal_zone*/temp; do
  if [ -r \"\$f\" ]; then
    value=\$(cat \"\$f\")
    if [ \"\$temp\" = unknown ] || [ \"\$value\" -gt \"\$temp\" ]; then temp=\$value; fi
  fi
done
avail=unknown; [ -e '$REMOTE_P8_OUT' ] && avail=\$(df -Pk '$REMOTE_P8_OUT' | awk 'NR==2 {print \$4}')
printf 'screen\t%s\nrc\t%s\ncomplete\t%s\nstop8\t%s\ncells\t%s\ntemp_millic\t%s\ndisk_avail_kib\t%s\n' \
  \"\$screen_live\" \"\$rc\" \"\$complete\" \"\$stop8\" \"\$cells\" \"\$temp\" \"\$avail\""
}

wait_screen_closed() {
  local family="$1" session="$SCREEN_PREFIX-$1" deadline=$((SECONDS + 30)) state
  while true; do
    state="$(ssh_run "if screen -S '$session' -Q select . >/dev/null 2>&1; then echo alive; else echo closed; fi")" \
      || fail "$family: nie mozna potwierdzic zamkniecia sesji screen $session"
    [[ "$state" == closed ]] && break
    [[ "$state" == alive ]] || fail "$family: nieznany stan sesji screen '$state'"
    (( SECONDS < deadline )) \
      || fail "$family: runner.rc istnieje, ale sesja screen $session nie zamknela sie"
    sleep 1
  done
  echo "CLOSE: sesja screen workera $session zakonczona"
}

wait_family() {
  local family="$1" status screen_live rc complete stop8 cells temp avail
  while true; do
    if ! status="$(family_status "$family")"; then
      echo "OSTRZEZENIE: $(date '+%F %T %Z') brak krotkiego odczytu SSH; screen workera nie jest przerywany"
      sleep "$POLL_SECONDS"
      continue
    fi
    screen_live="$(awk -F'\t' '$1=="screen"{print $2}' <<<"$status")"
    rc="$(awk -F'\t' '$1=="rc"{print $2}' <<<"$status")"
    complete="$(awk -F'\t' '$1=="complete"{print $2}' <<<"$status")"
    stop8="$(awk -F'\t' '$1=="stop8"{print $2}' <<<"$status")"
    cells="$(awk -F'\t' '$1=="cells"{print $2}' <<<"$status")"
    temp="$(awk -F'\t' '$1=="temp_millic"{print $2}' <<<"$status")"
    avail="$(awk -F'\t' '$1=="disk_avail_kib"{print $2}' <<<"$status")"
    echo "CHECK: $(date '+%F %T %Z') family=$family cells=$cells/480 screen=$screen_live rc=$rc STOP-8=$stop8 temp_millic=$temp disk_avail_kib=$avail"
    if [[ "$rc" != running ]]; then
      [[ "$rc" =~ ^[0-9]+$ ]] || fail "$family: nieprawidlowy runner.rc '$rc'"
      wait_screen_closed "$family"
      if [[ "$rc" != 0 ]]; then
        [[ "$stop8" == 1 ]] && fail "$family: STOP-8, rc=$rc; rodzina zatrzymana"
        fail "$family: runner zakonczony rc=$rc bez STOP-8 — apparatus"
      fi
      [[ "$complete" == 1 && "$cells" == 480 ]] \
        || fail "$family: rc=0 bez kompletu RUN_COMPLETE i 480/480 — apparatus"
      return 0
    fi
    [[ "$screen_live" == 1 ]] \
      || fail "$family: screen zniknal bez runner.rc — apparatus"
    [[ "$stop8" == 0 ]] || fail "$family: STOP-8 pojawil sie przed runner.rc"
    sleep "$POLL_SECONDS"
  done
}

copy_archive() {
  local family="$1" remote_archive="$REMOTE_ARCHIVES/K26v2-P8-$1.tar.gz"
  local remote_sum local_archive local_sum
  remote_sum="$(ssh_run "sha256sum '$remote_archive'" | awk '{print $1}')"
  scp "${SSH_OPTIONS[@]}" "$WORKER_SSH:$remote_archive" "$HOST_ARCHIVES/"
  local_archive="$HOST_ARCHIVES/K26v2-P8-$family.tar.gz"
  local_sum="$(sha256sum "$local_archive" | awk '{print $1}')"
  [[ "$remote_sum" == "$local_sum" ]] || fail "suma archiwum $family po scp jest inna"
  printf '%s\t%s\t%s\n' "$family" "$local_sum" "$(basename "$local_archive")" \
    >>"$HOST_ARCHIVES/archive-index.tsv"
}

[[ -n "${STY:-}" ]] || fail "uruchom P8 wyłącznie przez start_matrix_screen.sh"
[[ "$POLL_SECONDS" =~ ^[1-9][0-9]*$ ]] || fail "POLL_SECONDS musi byc dodatnia liczba calkowita"
command -v screen >/dev/null || fail "brak programu screen na hoscie"
command -v scp >/dev/null || fail "brak programu scp na hoscie"

set_governor
"$HERE/freeze_check.sh" macierz

[[ "$HOST_ARCHIVES" = /* && "$HOST_ARCHIVES" != "$HERE"* ]] \
  || fail "HOST_ARCHIVES musi byc bezwzglednym katalogiem poza aparatura K26v2"
[[ ! -e "$HOST_ARCHIVES" ]] || fail "$HOST_ARCHIVES juz istnieje; odmowa nadpisania"
mkdir -p "$HOST_ARCHIVES"
printf 'family\tsha256\tarchive\n' >"$HOST_ARCHIVES/archive-index.tsv"

families=(F9-R2 F9-R1 F9-X)
for index in "${!families[@]}"; do
  family="${families[$index]}"
  (( index == 0 )) || set_governor
  launch_family "$family"
  wait_family "$family"
  copy_archive "$family"
  if (( index + 1 < ${#families[@]} )); then
    ssh_run 'sync; sudo -n reboot' || true
    wait_worker
  fi
done

printf '1440/1440\n' >"$HOST_ARCHIVES/SUPERVISOR_COMPLETE"
echo "OK: P8 1440/1440; archiwa i indeks: $HOST_ARCHIVES"
