#!/usr/bin/env bash
# Jednorazowy start hostowego nadzorcy P8 w odlaczonej sesji screen.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION="${HOST_SCREEN_SESSION:-K26v2-P8-supervisor}"
LOG="${HOST_SUPERVISOR_LOG:-$HOME/k26v2_supervisor.log}"

command -v screen >/dev/null || { echo "BLAD: brak programu screen na hoscie" >&2; exit 2; }
[[ -z "${STY:-}" ]] || { echo "BLAD: start_matrix_screen.sh uruchom poza istniejacym screen" >&2; exit 2; }
screen -S "$SESSION" -Q select . >/dev/null 2>&1 && {
  echo "BLAD: sesja screen $SESSION juz istnieje" >&2
  exit 2
}
[[ ! -e "$LOG" ]] || { echo "BLAD: log $LOG juz istnieje; odmowa nadpisania" >&2; exit 2; }

screen -DmS "$SESSION" -L -Logfile "$LOG" "$HERE/run_matrix_supervisor.sh"
sleep 1
screen -S "$SESSION" -Q select . >/dev/null 2>&1 || {
  echo "BLAD: nadzorca zakonczyl sie podczas startu; sprawdz $LOG" >&2
  exit 2
}

echo "OK: P8 uruchomione w screen $SESSION"
echo "log: $LOG"
echo "podglad: screen -r $SESSION"
echo "odlaczenie: Ctrl-a d"
