#!/usr/bin/env bash
# Jednorazowy start macierzy P8 K26v3: bramki hosta, instalacja uslugi systemd
# workera i uruchomienie lancucha rodzin.
#
# Po tym skrypcie host nie ma zadnej roli w pomiarze i moze byc wylaczony:
# lancuch trzech rodzin prowadzi worker pod systemd, sam restartuje sie miedzy
# rodzinami i sam wstaje po zaniku zasilania. Archiwa odbiera pozniej
# `collect_p8_archives.sh`, kiedykolwiek — takze po calym pomiarze.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKER_SSH="${WORKER_SSH:-michal@192.168.88.13}"
SSH_CONFIG="${RDB_SSH_CONFIG:-/dev/null}"
REMOTE_CAMPAIGN_DIR="${REMOTE_CAMPAIGN_DIR:-/home/michal/rdb-experiment/results_20260814_K26v3}"
REMOTE_CODE_REPO="${REMOTE_CODE_REPO:-/home/michal/K26v3}"
REMOTE_P6_RDB="${REMOTE_P6_RDB:-/home/michal/k26v3_gates_rdb}"
REMOTE_P8_OUT="${REMOTE_P8_OUT:-/home/michal/k26v3_p8}"
REMOTE_ARCHIVES="${REMOTE_ARCHIVES:-/home/michal/k26v3_archives}"
REMOTE_CONTROL="${REMOTE_CONTROL:-/home/michal/k26v3_control}"
UNIT_NAME="${UNIT_NAME:-k26v3-p8.service}"
CPU="${CPU:-3}"

SSH_OPTIONS=(-F "$SSH_CONFIG" -o BatchMode=yes -o ConnectTimeout=8 \
  -o ServerAliveInterval=15 -o ServerAliveCountMax=3)

fail() { echo "BLAD STARTU P8: $*" >&2; exit 2; }
ssh_run() { ssh "${SSH_OPTIONS[@]}" "$WORKER_SSH" "$@"; }

# Ta sama konfiguracja musi trafic do generatora unitu po OBU stronach, inaczej
# porownanie sum kontrolnych bylby porownaniem dwoch roznych plikow.
unit_env=(
  "CAMPAIGN_DIR=$REMOTE_CAMPAIGN_DIR"
  "CODE_REPO=$REMOTE_CODE_REPO"
  "P6_RDB=$REMOTE_P6_RDB"
  "P8_OUT=$REMOTE_P8_OUT"
  "ARCHIVES=$REMOTE_ARCHIVES"
  "CONTROL=$REMOTE_CONTROL"
  "UNIT_NAME=$UNIT_NAME"
  "CPU=$CPU"
)
remote_env=""
for entry in "${unit_env[@]}"; do
  remote_env+=" $(printf '%q' "$entry")"
done

"$HERE/freeze_check.sh" macierz

# Start jest od zera. Wznowienie przerwanego pomiaru nalezy do samej uslugi
# (`systemctl start k26v3-p8`), nie do tego skryptu — inaczej nie odroznilby
# swiezej kampanii od nadpisania cudzego stanu.
ssh_run "for path in '$REMOTE_P8_OUT' '$REMOTE_ARCHIVES' '$REMOTE_CONTROL'; do
  if [ -e \"\$path\" ]; then echo \"artefakt juz istnieje: \$path\" >&2; exit 2; fi
done" || fail "worker ma zastane artefakty P8; wznowienie idzie przez systemctl start, nie przez ten skrypt"

ssh_run "env$remote_env $(printf '%q' "$REMOTE_CAMPAIGN_DIR/install_worker_service.sh")" \
  || fail "instalacja uslugi $UNIT_NAME na workerze nie powiodla sie"

# Bramka po stronie konsumenta (D3): liczy sie plik, ktory faktycznie wykona
# systemd workera, a nie kopia hosta.
worker_sum="$(ssh_run "sha256sum '/etc/systemd/system/$UNIT_NAME'" | awk '{print $1}')" \
  || fail "nie mozna odczytac unitu na workerze"
host_sum="$(env "${unit_env[@]}" "$HERE/install_worker_service.sh" --print | sha256sum | awk '{print $1}')"
[[ "$worker_sum" == "$host_sum" ]] \
  || fail "unit na workerze rozni sie od generowanego na hoscie ($worker_sum != $host_sum)"

enabled="$(ssh_run "systemctl is-enabled '$UNIT_NAME'" || true)"
[[ "$enabled" == enabled ]] || fail "$UNIT_NAME nie jest wlaczony na boot (jest: $enabled)"

ssh_run "sudo -n systemctl start --no-block '$UNIT_NAME'" || fail "start $UNIT_NAME odrzucony"
sleep 3
active="$(ssh_run "systemctl is-active '$UNIT_NAME'" || true)"
[[ "$active" == active ]] || fail "$UNIT_NAME nie jest aktywny po starcie (jest: $active)"

echo "OK: lancuch P8 rusza na workerze jako $UNIT_NAME"
echo "unit sha256: $host_sum (host i worker zgodne)"
echo "log lancucha: $WORKER_SSH:$REMOTE_CONTROL/chain.log"
echo "stan i archiwa: $HERE/collect_p8_archives.sh (mozna uruchamiac kiedykolwiek)"
echo "host nie jest juz potrzebny do pomiaru i moze zostac wylaczony"
