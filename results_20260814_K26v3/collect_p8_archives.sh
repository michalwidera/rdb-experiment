#!/usr/bin/env bash
# Odczyt stanu macierzy P8 i odbior gotowych archiwow rodzin.
#
# Skrypt jest krotki, bezstanowy i mozna go uruchamiac dowolna liczbe razy —
# takze dopiero po calym pomiarze. Nie trzyma niczego na workerze i nie jest
# warunkiem postepu lancucha: worker liczy dalej, nawet gdy host jest wylaczony.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKER_SSH="${WORKER_SSH:-michal@192.168.88.13}"
SSH_CONFIG="${RDB_SSH_CONFIG:-/dev/null}"
REMOTE_P8_OUT="${REMOTE_P8_OUT:-/home/michal/k26v3_p8}"
REMOTE_ARCHIVES="${REMOTE_ARCHIVES:-/home/michal/k26v3_archives}"
REMOTE_CONTROL="${REMOTE_CONTROL:-/home/michal/k26v3_control}"
HOST_ARCHIVES="${HOST_ARCHIVES:-$HOME/k26v3_archives}"
UNIT_NAME="${UNIT_NAME:-k26v3-p8.service}"

SSH_OPTIONS=(-F "$SSH_CONFIG" -o BatchMode=yes -o ConnectTimeout=8 \
  -o ServerAliveInterval=15 -o ServerAliveCountMax=3)
FAMILIES=(F9-R2 F9-R1 F9-X)

fail() { echo "BLAD ODBIORU: $*" >&2; exit 2; }
ssh_run() { ssh "${SSH_OPTIONS[@]}" "$WORKER_SSH" "$@"; }
field() { awk -F'\t' -v key="$1" '$1==key {print $2}' <<<"$2"; }

read_status() {
  ssh_run "
unit=\$(systemctl is-active '$UNIT_NAME' 2>/dev/null || true)
result=\$(systemctl show -p Result --value '$UNIT_NAME' 2>/dev/null || true)
if [ -e '$REMOTE_P8_OUT/HALT' ]; then halt=\$(awk -F'\t' '\$1==\"reason\"{print \$2}' '$REMOTE_P8_OUT/HALT'); else halt=no; fi
if [ -e '$REMOTE_P8_OUT/P8_COMPLETE' ]; then complete=1; else complete=0; fi
temp=unknown; for f in /sys/class/thermal/thermal_zone*/temp; do
  if [ -r \"\$f\" ]; then
    value=\$(cat \"\$f\")
    if [ \"\$temp\" = unknown ] || [ \"\$value\" -gt \"\$temp\" ]; then temp=\$value; fi
  fi
done
avail=unknown; [ -e '$REMOTE_P8_OUT' ] && avail=\$(df -Pk '$REMOTE_P8_OUT' | awk 'NR==2 {print \$4}')
printf 'unit\t%s\nresult\t%s\nhalt\t%s\ncomplete\t%s\ntemp_millic\t%s\ndisk_avail_kib\t%s\n' \
  \"\$unit\" \"\$result\" \"\$halt\" \"\$complete\" \"\$temp\" \"\$avail\"
for family in ${FAMILIES[*]}; do
  out='$REMOTE_P8_OUT'/\$family
  if [ -d \"\$out/raw\" ]; then cells=\$(find \"\$out/raw\" -type f -name summary.tsv | wc -l); else cells=0; fi
  if [ -r \"\$out/RUN_COMPLETE\" ]; then done_flag=1; else done_flag=0; fi
  if [ -r \"\$out/STOP-8\" ]; then stop8=1; else stop8=0; fi
  if [ -r '$REMOTE_ARCHIVES'/K26v3-P8-\$family.tar.gz ]; then archive=1; else archive=0; fi
  printf '%s\t%s/480\t%s\t%s\t%s\n' \"\$family\" \"\$cells\" \"\$done_flag\" \"\$stop8\" \"\$archive\"
done"
}

copy_archive() {
  local family="$1"
  local remote_archive="$REMOTE_ARCHIVES/K26v3-P8-$family.tar.gz"
  local local_archive="$HOST_ARCHIVES/K26v3-P8-$family.tar.gz"
  local remote_sum local_sum
  remote_sum="$(ssh_run "sha256sum '$remote_archive'" | awk '{print $1}')" \
    || fail "$family: nie mozna odczytac sumy archiwum workera"
  if [[ -e "$local_archive" ]]; then
    local_sum="$(sha256sum "$local_archive" | awk '{print $1}')"
    [[ "$local_sum" == "$remote_sum" ]] \
      || fail "$family: kopia hosta rozni sie od archiwum workera; odmowa nadpisania"
    echo "JUZ MAM: $family $local_sum"
    return 0
  fi
  scp "${SSH_OPTIONS[@]}" "$WORKER_SSH:$remote_archive" "$HOST_ARCHIVES/" \
    || fail "$family: kopiowanie archiwum nie powiodlo sie"
  local_sum="$(sha256sum "$local_archive" | awk '{print $1}')"
  [[ "$remote_sum" == "$local_sum" ]] || fail "$family: suma archiwum po scp jest inna"
  printf '%s\t%s\t%s\n' "$family" "$local_sum" "$(basename "$local_archive")" \
    >>"$HOST_ARCHIVES/archive-index.tsv"
  echo "ODEBRANE: $family $local_sum"
}

command -v scp >/dev/null || fail "brak programu scp na hoscie"
[[ "$HOST_ARCHIVES" = /* && "$HOST_ARCHIVES" != "$HERE"* ]] \
  || fail "HOST_ARCHIVES musi byc bezwzglednym katalogiem poza aparatura K26v3"
mkdir -p "$HOST_ARCHIVES"
[[ -e "$HOST_ARCHIVES/archive-index.tsv" ]] \
  || printf 'family\tsha256\tarchive\n' >"$HOST_ARCHIVES/archive-index.tsv"

status="$(read_status)" || fail "worker nieosiagalny; lancuch liczy dalej bez hosta"
unit="$(field unit "$status")"
result="$(field result "$status")"
halt="$(field halt "$status")"
complete="$(field complete "$status")"
echo "STAN: $(date '+%F %T %Z') unit=$unit result=$result HALT=$halt P8_COMPLETE=$complete" \
  "temp_millic=$(field temp_millic "$status") disk_avail_kib=$(field disk_avail_kib "$status")"

copied=0
for family in "${FAMILIES[@]}"; do
  row="$(awk -F'\t' -v key="$family" '$1==key' <<<"$status")"
  IFS=$'\t' read -r _ cells done_flag stop8 archive <<<"$row"
  echo "CHECK: family=$family cells=$cells RUN_COMPLETE=$done_flag STOP-8=$stop8 archiwum=$archive"
  if [[ "$archive" == 1 ]]; then
    copy_archive "$family"
    copied=$((copied + 1))
  fi
done

if [[ "$halt" == stop8 ]]; then
  fail "lancuch zatrzymany przez STOP-8; rodzina bez werdyktu"
elif [[ "$halt" != no ]]; then
  fail "lancuch zatrzymany jako apparatus ($halt); iteracja wymaga decyzji czlowieka"
fi

if [[ "$complete" == 1 && "$copied" == "${#FAMILIES[@]}" ]]; then
  printf '1440/1440\n' >"$HOST_ARCHIVES/COLLECT_COMPLETE"
  echo "OK: P8 1440/1440; ${#FAMILIES[@]} archiwa i indeks w $HOST_ARCHIVES"
else
  echo "POSTEP: odebrane archiwa $copied/${#FAMILIES[@]}; pomiar trwa niezaleznie od hosta"
fi
