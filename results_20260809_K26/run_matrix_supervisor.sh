#!/usr/bin/env bash
# Nadzorca P8: trzy rodziny, kopia archiwow na host i reboot miedzy rodzinami.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKER_SSH="${WORKER_SSH:-michal@192.168.88.13}"
SSH_CONFIG="${RDB_SSH_CONFIG:-/dev/null}"
REMOTE_K26_DIR="${REMOTE_K26_DIR:-/home/michal/rdb-experiment/results_20260809_K26}"
REMOTE_CODE_REPO="${REMOTE_CODE_REPO:-/home/michal/K26}"
REMOTE_P6_RDB="${REMOTE_P6_RDB:-/home/michal/k26_gates_rdb}"
REMOTE_P8_OUT="${REMOTE_P8_OUT:-/home/michal/k26_p8}"
REMOTE_ARCHIVES="${REMOTE_ARCHIVES:-/home/michal/k26_archives}"
HOST_ARCHIVES="${HOST_ARCHIVES:-$HOME/k26_archives}"
CPU="${CPU:-3}"

wait_worker() {
  local deadline=$((SECONDS + 600))
  until ssh -F "$SSH_CONFIG" -o BatchMode=yes -o ConnectTimeout=5 "$WORKER_SSH" true 2>/dev/null; do
    (( SECONDS < deadline )) || { echo "BLAD: worker nie wrocil po restarcie" >&2; exit 2; }
    sleep 10
  done
  sleep 15
}

set_governor() {
  ssh -F "$SSH_CONFIG" "$WORKER_SSH" "sudo -n sh -c 'for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance >\"\$f\"; done'"
}

set_governor
"$HERE/freeze_check.sh" macierz

[[ "$HOST_ARCHIVES" = /* && "$HOST_ARCHIVES" != "$HERE"* ]] || {
  echo "BLAD: HOST_ARCHIVES musi byc bezwzglednym katalogiem poza aparatura K26" >&2; exit 2; }
mkdir -p "$HOST_ARCHIVES"
[[ ! -e "$HOST_ARCHIVES/archive-index.tsv" ]] || {
  echo "BLAD: $HOST_ARCHIVES/archive-index.tsv juz istnieje; odmowa dopisywania do innej kampanii" >&2; exit 2; }
printf 'family\tsha256\tarchive\n' >"$HOST_ARCHIVES/archive-index.tsv"

families=(F9-R2 F9-R1 F9-X)
for index in "${!families[@]}"; do
  family="${families[$index]}"
  if (( index > 0 )); then
    set_governor
  fi
  ssh -F "$SSH_CONFIG" "$WORKER_SSH" \
    "cd '$REMOTE_K26_DIR' && ./run_matrix_worker.py --family '$family' --cpu '$CPU' --code-repo '$REMOTE_CODE_REPO' --p6-rdb '$REMOTE_P6_RDB' --out '$REMOTE_P8_OUT/$family' --archive-dir '$REMOTE_ARCHIVES'"
  remote_archive="$REMOTE_ARCHIVES/K26-P8-$family.tar.gz"
  remote_sum="$(ssh -F "$SSH_CONFIG" "$WORKER_SSH" "sha256sum '$remote_archive'" | awk '{print $1}')"
  scp -F "$SSH_CONFIG" "$WORKER_SSH:$remote_archive" "$HOST_ARCHIVES/"
  local_archive="$HOST_ARCHIVES/K26-P8-$family.tar.gz"
  local_sum="$(sha256sum "$local_archive" | awk '{print $1}')"
  [[ "$remote_sum" == "$local_sum" ]] || { echo "BLAD: suma archiwum $family po scp jest inna" >&2; exit 2; }
  printf '%s\t%s\t%s\n' "$family" "$local_sum" "$(basename "$local_archive")" >>"$HOST_ARCHIVES/archive-index.tsv"
  if (( index + 1 < ${#families[@]} )); then
    ssh -F "$SSH_CONFIG" "$WORKER_SSH" 'sync; sudo -n reboot' || true
    wait_worker
  fi
done

echo "OK: P8 1440/1440; archiwa i indeks: $HOST_ARCHIVES"
