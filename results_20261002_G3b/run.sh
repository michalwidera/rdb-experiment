#!/usr/bin/env bash
# Poprawiony most G3 (retractordb #353): jeden przebieg na silnik, potem raport.
#
#   ./run.sh <xretractor> <pelne SHA silnika>
#
# Wynik: results/engine-<8 znakow SHA>.json i odswiezony results/summary.md.
# Kod wyjscia: 0 - 13/13, 1 - rozbieznosci, 2 - blad aparatury albo argumentow.
set -euo pipefail

cd "$(dirname "$0")"

if [ $# -ne 2 ] || ! [[ "$2" =~ ^[0-9a-f]{40}$ ]]; then
  echo "uzycie: $0 <xretractor> <pelne SHA silnika (40 znakow)>" >&2
  exit 2
fi

mkdir -p results
status=0
PYTHONDONTWRITEBYTECODE=1 python3 engine_check.py --xretractor "$1" --engine-commit "$2" \
  --json "results/engine-${2:0:8}.json" || status=$?
PYTHONDONTWRITEBYTECODE=1 python3 make_summary.py
exit "$status"
