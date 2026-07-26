#!/usr/bin/env bash
# Odtwarza sondę obserwowalności planu na bieżącej binarce (domyślnie Debug).
# Pełna macierz profili optymalizatora: ./build_profiles.sh
set -euo pipefail

cd "$(dirname "$0")"

XRETRACTOR=${XRETRACTOR:-../../../build/Debug/src/retractor/xretractor}

mkdir -p results/raw

python3 probe.py --xretractor "$XRETRACTOR" --profile default \
  --json results/probe.json | tee results/raw/probe.txt

python3 make_summary.py

echo
echo "gotowe: results/summary.md"
