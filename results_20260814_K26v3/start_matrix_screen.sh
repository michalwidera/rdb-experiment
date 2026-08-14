#!/usr/bin/env bash
# Jednorazowy start hostowego nadzorcy P8 w odlaczonej sesji screen.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION="${HOST_SCREEN_SESSION:-K26v3-P8-supervisor}"
LOG="${HOST_SUPERVISOR_LOG:-$HOME/k26v3_supervisor.log}"

# `screen -Q select .` wisi na nieistniejacej sesji (K26v2/D5). Gniazda czytamy
# z `screen -ls`, ktore nigdy nie blokuje.
session_live() {
  screen -ls "$1" 2>/dev/null | grep -qE "^[[:space:]]*[0-9]+\.$1[[:space:]]"
}

command -v screen >/dev/null || { echo "BLAD: brak programu screen na hoscie" >&2; exit 2; }
[[ -z "${STY:-}" ]] || { echo "BLAD: start_matrix_screen.sh uruchom poza istniejacym screen" >&2; exit 2; }
if session_live "$SESSION"; then
  echo "BLAD: sesja screen $SESSION juz istnieje" >&2
  exit 2
fi
[[ ! -e "$LOG" ]] || { echo "BLAD: log $LOG juz istnieje; odmowa nadpisania" >&2; exit 2; }

# `-dmS` FORKUJE; `-DmS` nie forkowal i trzymal nadzorce w jednym procesie z
# poleceniem startowym (K26v2/D4), przez co petla kontrolna nie chodzila.
screen -dmS "$SESSION" -L -Logfile "$LOG" "$HERE/run_matrix_supervisor.sh"
sleep 1
if ! session_live "$SESSION"; then
  echo "BLAD: nadzorca zakonczyl sie podczas startu; sprawdz $LOG" >&2
  exit 2
fi

echo "OK: P8 uruchomione w screen $SESSION"
echo "log: $LOG"
echo "podglad: screen -r $SESSION"
echo "odlaczenie: Ctrl-a d"
