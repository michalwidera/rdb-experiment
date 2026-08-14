#!/usr/bin/env bash
# Instalacja uslugi systemd, ktora prowadzi lancuch P8 po stronie workera.
#
# Ten skrypt jest JEDYNYM zrodlem tresci unitu: `--print` wypisuje dokladnie to,
# co instalacja zapisuje do /etc/systemd/system. Dzieki temu host moze porownac
# swoja kopie z kopia workera tak samo, jak robi to bramka ANEKS-1 (D3) —
# sprawdzamy plik po stronie, ktora go konsumuje, a nie po swojej.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

UNIT_NAME="${UNIT_NAME:-k26v3-p8.service}"
UNIT_PATH="${UNIT_PATH:-/etc/systemd/system/$UNIT_NAME}"
RUN_USER="${RUN_USER:-michal}"
CAMPAIGN_DIR="${CAMPAIGN_DIR:-$HERE}"
CPU="${CPU:-3}"
CODE_REPO="${CODE_REPO:-/home/michal/K26v3}"
P6_RDB="${P6_RDB:-/home/michal/k26v3_gates_rdb}"
P8_OUT="${P8_OUT:-/home/michal/k26v3_p8}"
ARCHIVES="${ARCHIVES:-/home/michal/k26v3_archives}"
CONTROL="${CONTROL:-/home/michal/k26v3_control}"
SETTLE_SECONDS="${SETTLE_SECONDS:-60}"
SUDO="${SUDO:-sudo -n}"

unit_text() {
  cat <<UNIT
[Unit]
Description=K26v3 P8: lancuch rodzin macierzy (jedna rodzina na uruchomienie)
Documentation=file://$CAMPAIGN_DIR/PREDEKLARACJA.md
After=local-fs.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$CAMPAIGN_DIR
Environment=CPU=$CPU
Environment=CODE_REPO=$CODE_REPO
Environment=P6_RDB=$P6_RDB
Environment=P8_OUT=$P8_OUT
Environment=ARCHIVES=$ARCHIVES
Environment=CONTROL=$CONTROL
Environment=UNIT=$UNIT_NAME
Environment=SETTLE_SECONDS=$SETTLE_SECONDS
ExecStart=$CAMPAIGN_DIR/run_matrix_chain.sh
Restart=no
TimeoutStopSec=120
StandardOutput=append:$CONTROL/chain.log
StandardError=append:$CONTROL/chain.log

[Install]
WantedBy=multi-user.target
UNIT
}

if [[ "${1:-}" == "--print" ]]; then
  unit_text
  exit 0
fi
if (( $# > 1 )) || [[ -n "${1:-}" && "${1:-}" != "--force" ]]; then
  echo "uzycie: $(basename "$0") [--print|--force]" >&2
  exit 2
fi

[[ -x "$CAMPAIGN_DIR/run_matrix_chain.sh" ]] \
  || { echo "BLAD: brak wykonywalnego $CAMPAIGN_DIR/run_matrix_chain.sh" >&2; exit 2; }
mkdir -p "$CONTROL"

# Odmowa cichego nadpisania: instalacja jest bezpieczna do powtorzenia tylko
# wtedy, gdy zastany unit jest CO DO BAJTU tym samym plikiem.
if [[ -e "$UNIT_PATH" && "${1:-}" != "--force" ]]; then
  if ! diff -q <(unit_text) "$UNIT_PATH" >/dev/null; then
    echo "BLAD: $UNIT_PATH istnieje i rozni sie od generowanego; uzyj --force" >&2
    diff -u "$UNIT_PATH" <(unit_text) >&2 || true
    exit 2
  fi
fi

unit_text | $SUDO tee "$UNIT_PATH" >/dev/null
$SUDO systemctl daemon-reload
$SUDO systemctl enable "$UNIT_NAME" >/dev/null

state="$(systemctl is-enabled "$UNIT_NAME" 2>&1 || true)"
[[ "$state" == enabled ]] || { echo "BLAD: $UNIT_NAME nie jest enabled (jest: $state)" >&2; exit 2; }

printf 'OK: %s zainstalowany i wlaczony na boot\n' "$UNIT_PATH"
printf 'sha256\t%s\n' "$(sha256sum "$UNIT_PATH" | awk '{print $1}')"
