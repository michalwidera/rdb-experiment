#!/bin/bash
# F1 -- przebieg trzech modeli i wspólny oracle (etap K22b).
#
# Odtwarza rodzinę od zera w /dev/shm: dane, RQL, Python, Flink, porównanie.
# Artefakty powstają poza repozytorium (REQUIREMENTS.md R14) — do repo trafia
# tylko wynik porównania.
set -euo pipefail

CAMPAIGN="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CODE_REPO="${CODE_REPO:-/home/michal/github/retractordb}"
FLINK_HOME="${FLINK_HOME:-$HOME/opt/flink-2.3.0}"
WORK="${WORK:-/dev/shm/k22_f1}"

# Ogon i liczba slotów. `tail` jest ODCZYTYWANY z silnika nizej, nie wpisany.
SPAN=2000

rm -rf "$WORK"
mkdir -p "$WORK/temp" "$WORK/classes"
cd "$WORK"

echo "== dane"
python3 "$CAMPAIGN/corpus/gen_data.py" --family F1
cp "$CODE_REPO/test/IntegrationTest_parallel/dsp/filterremez.txt" f1_coef.txt
sha256sum f1_coef.txt

echo "== RQL: odczyt ogona z silnika"
cp "$CAMPAIGN/corpus/F1_fir/rql/core.rql" q.rql
TAIL=$(xretractor q.rql -c 2>/dev/null | sed -n 's/^f1_out(.*)\ttail=\([0-9]*\).*/\1/p')
[[ -n "$TAIL" ]] || { echo "BLAD: nie odczytano tail z silnika" >&2; exit 2; }
echo "   tail=$TAIL (zrodlo: xretractor q.rql -c)"

# PREDECLARATION.md §11.1 E2: -m N daje N-1-tail rekordow (jeden slot to krok zerowy).
CYCLES=$((SPAN + 1 + TAIL))
SLOTS=$((SPAN + TAIL - 1))

echo "== RQL: przebieg ($CYCLES cykli)"
xretractor q.rql -m "$CYCLES" -k -r >/dev/null 2>&1
python3 "$CAMPAIGN/corpus/emit_rql.py" --stream temp/f1_out --family F1 \
  --tail "$TAIL" --limit "$SPAN" --out rql.csv

echo "== Python: przebieg ($SLOTS slotow)"
python3 "$CAMPAIGN/corpus/F1_fir/python/run.py" --source f1_source.txt --coef f1_coef.txt \
  --slots "$SLOTS" --out py.csv

echo "== Flink: kompilacja i przebieg"
javac -nowarn -cp "$FLINK_HOME/lib/flink-dist-2.3.0.jar" -d classes \
  "$CAMPAIGN/corpus/F1_fir/flink/F1Fir.java"
java -cp "classes:$FLINK_HOME/lib/*" F1Fir --source f1_source.txt --coef f1_coef.txt \
  --slots "$SLOTS" --out flink.csv 2>/dev/null

echo "== oracle"
python3 "$CAMPAIGN/oracle/compare.py" --span "$SPAN" \
  --tail rql="$TAIL" --tail python="$TAIL" --tail flink="$TAIL" \
  rql=rql.csv python=py.csv flink=flink.csv
