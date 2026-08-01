#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONDONTWRITEBYTECODE=1

python3 "$ROOT/tests/test_instrument.py"
python3 "$ROOT/tests/test_generator.py"

# Kontrole regresyjne semantyki i komparatora z pilota pozostają obowiązujące.
python3 "$ROOT/../results_20260801_K22/oracle/test_refsem.py"
python3 "$ROOT/../results_20260801_K22/oracle/test_compare.py"

echo "OK: aparatura K22v5"
