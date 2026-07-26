#!/usr/bin/env bash
# Odtwarza K2/G3: kwalifikacja mutacji -> oracle -> most do silnika -> raport.
set -euo pipefail

cd "$(dirname "$0")"

XRETRACTOR=${XRETRACTOR:-../../../build/Debug/src/retractor/xretractor}
QUICK=${QUICK:-}

mkdir -p results/raw

echo "== 1/3 niezależny oracle R1 =="
python3 test_equivalence.py ${QUICK:+--quick} --json results/equivalence.json \
  2>results/raw/equivalence.progress | tee results/raw/equivalence.txt

echo
echo "== 2/3 most oracle — RetractorDB =="
engine_status=0
python3 engine_check.py --xretractor "$XRETRACTOR" --json results/engine.json \
  | tee results/raw/engine.txt || engine_status=$?

echo
echo "== 3/3 raport =="
python3 make_summary.py

echo
echo "gotowe: results/summary.md"

exit "$engine_status"
