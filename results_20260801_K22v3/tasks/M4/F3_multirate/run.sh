#!/bin/bash
# F3 -- przebieg trzech modeli i wspólny oracle (etap K22b).
set -euo pipefail

CAMPAIGN="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FLINK_HOME="${FLINK_HOME:-$HOME/opt/flink-2.3.0}"
WORK="${WORK:-/dev/shm/k22_f3}"
SPAN=2000

# Relacja cykli do rekordow jest ZALEZNA OD PLANU, nie uniwersalna
# (PREDECLARATION.md §11.1 E2): dla F1 bylo N-1-tail, tu floor(3N/4)-tail,
# bo strumien wyjsciowy biegnie wolniej niz globalna siatka. Dlatego zamawiamy
# z zapasem, a emiter ZATRZYMUJE sie, jesli rekordow zabraknie.
CYCLES=2800

rm -rf "$WORK"
mkdir -p "$WORK/temp" "$WORK/classes"
cd "$WORK"

echo "== dane"
python3 "$CAMPAIGN/corpus/gen_data.py" --family F3

echo "== RQL: odczyt ogona z silnika"
cp "$CAMPAIGN/corpus/F3_multirate/rql/core.rql" q.rql
TAIL=$(xretractor q.rql -c 2>/dev/null | sed -n 's/^f3_out(.*)\ttail=\([0-9]*\).*/\1/p')
[[ -n "$TAIL" ]] || { echo "BLAD: nie odczytano tail z silnika" >&2; exit 2; }
echo "   tail=$TAIL (zrodlo: xretractor q.rql -c; 2 przeplot + 3 przesuniecie + 30 okno)"

echo "== RQL: przebieg ($CYCLES cykli)"
xretractor q.rql -m "$CYCLES" -k -r >/dev/null 2>&1
python3 "$CAMPAIGN/corpus/emit_rql.py" --stream temp/f3_out --family F3 \
  --tail "$TAIL" --limit "$SPAN" --out rql.csv

echo "== Python: przebieg"
python3 "$CAMPAIGN/corpus/F3_multirate/python/run.py" --a f3_a.txt --b f3_b.txt \
  --slots $((SPAN + 30)) --out py.csv

echo "== Flink: kompilacja i przebieg"
javac -nowarn -cp "$FLINK_HOME/lib/flink-dist-2.3.0.jar" -d classes \
  "$CAMPAIGN/corpus/F3_multirate/flink/F3Multirate.java"
java -cp "classes:$FLINK_HOME/lib/*" F3Multirate --a f3_a.txt --b f3_b.txt \
  --slots $((SPAN + 30)) --out flink.csv 2>/dev/null

echo "== oracle"
python3 "$CAMPAIGN/oracle/compare.py" --span "$SPAN" \
  --tail rql="$TAIL" --tail python="$TAIL" --tail flink="$TAIL" \
  rql=rql.csv python=py.csv flink=flink.csv
