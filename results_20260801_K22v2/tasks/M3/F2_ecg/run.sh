#!/bin/bash
# F2 -- przebieg trzech modeli i wspólny oracle (etap K22b).
set -euo pipefail

CAMPAIGN="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CODE_REPO="${CODE_REPO:-/home/michal/github/retractordb}"
FLINK_HOME="${FLINK_HOME:-$HOME/opt/flink-2.3.0}"
WORK="${WORK:-/dev/shm/k22_f2}"
SPAN=2000

rm -rf "$WORK"
mkdir -p "$WORK/temp" "$WORK/classes"
cd "$WORK"

echo "== dane (prowenienecja: retractordb/examples/ecg/rec205)"
cp "$CODE_REPO/examples/ecg/rec205/rec205" .
cp "$CODE_REPO/examples/ecg/rec205/bp_coef.txt" .
cp "$CODE_REPO/examples/ecg/rec205/d_coef.txt" .
sha256sum bp_coef.txt d_coef.txt

echo "== RQL: odczyt ogona z silnika"
cp "$CAMPAIGN/corpus/F2_ecg/rql/core.rql" q.rql
TAIL=$(xretractor q.rql -c 2>/dev/null | sed -n 's/^qrs_out(.*)\ttail=\([0-9]*\).*/\1/p')
[[ -n "$TAIL" ]] || { echo "BLAD: nie odczytano tail z silnika" >&2; exit 2; }
echo "   tail=$TAIL (zrodlo: xretractor q.rql -c; 25+5+30+180)"

# PREDECLARATION.md §11.1 E2: -m N daje N-1-tail rekordow.
CYCLES=$((SPAN + 1 + TAIL))
SLOTS=$((SPAN + TAIL))

echo "== RQL: przebieg ($CYCLES cykli)"
xretractor q.rql -m "$CYCLES" -k -r >/dev/null 2>&1
python3 "$CAMPAIGN/corpus/emit_rql.py" --stream temp/qrs_out --family F2 \
  --tail "$TAIL" --limit "$SPAN" --out rql.csv

echo "== Python: przebieg ($SLOTS slotow)"
python3 "$CAMPAIGN/corpus/F2_ecg/python/run.py" --rec rec205 --bp bp_coef.txt --d d_coef.txt \
  --slots "$SLOTS" --out py.csv

echo "== Flink: kompilacja i przebieg"
javac -nowarn -cp "$FLINK_HOME/lib/flink-dist-2.3.0.jar" -d classes \
  "$CAMPAIGN/corpus/F2_ecg/flink/F2Ecg.java"
java -cp "classes:$FLINK_HOME/lib/*" F2Ecg --rec rec205 --bp bp_coef.txt --d d_coef.txt \
  --slots "$SLOTS" --out flink.csv 2>/dev/null

echo "== oracle"
python3 "$CAMPAIGN/oracle/compare.py" --span "$SPAN" \
  --tail rql="$TAIL" --tail python="$TAIL" --tail flink="$TAIL" \
  rql=rql.csv python=py.csv flink=flink.csv
