#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
RDB_BUILD=${RDB_BUILD:-../../retractordb/build/Debug}
RDB_BUILD=$(realpath "$RDB_BUILD")

mkdir -p results
python3 test_boundaries.py --json results/oracle.json | tee results/oracle.txt

env PATH="$RDB_BUILD/src/retractor:$RDB_BUILD/src/qry:$RDB_BUILD/src/rdb:$PATH" \
  ctest --test-dir "$RDB_BUILD" \
  -R '^(ut_soperations|ut_compiler|ut_dataModel|it_k19_boundaries|it_agse1|it_agse2|it_agse3|it_deinterleave_roundtrip-run)$' \
  --output-on-failure | tee results/engine.txt
