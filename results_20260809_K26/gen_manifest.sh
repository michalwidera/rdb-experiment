#!/usr/bin/env bash
# Explicit manifest of K26 preregistration apparatus and premeasurement evidence.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

mapfile -t FILES < <(
  printf '%s\n' \
    .gitignore \
    PREDEKLARACJA.md \
    README.md \
    profiles.tsv \
    blocks.tsv \
    build_profiles.sh \
    dump_control_plans.sh \
    freeze_check.sh \
    gen_blocks.py \
    gen_corpus.py \
    gen_manifest.sh \
    mechanism_table.py \
    oracle_values.py \
    run_gates.py \
    run_main_flink.sh \
    run_main_rdb.sh \
    test_apparatus.py \
    validate_corpus.py \
    verdict.py
  find data rql -type f | sort
  find corpus_validation -type f | sort
  find pilot -type f ! -path '*/__pycache__/*' | sort
  find calib -maxdepth 1 -type f \( -name '*.py' -o -name '*.sh' -o -name '*.cpp' \) | sort
  find flink/java -type f -name '*.java' | sort
  find flink -maxdepth 1 -type f \( -name '*.sh' -o -name '*.tsv' \) | sort
  find flink/oracle -maxdepth 1 -type f \( -name '*.cc' -o -name '*.sh' -o -name '*.tsv' \) | sort
  find flink/plans -type f | sort
  find flink/results -type f | sort
)

for file in "${FILES[@]}"; do
  [[ -f "$file" ]] || { echo "BLAD: manifest wymienia brakujacy plik $file" >&2; exit 2; }
done

sha256sum "${FILES[@]}" > manifest.sha256
echo "OK: manifest.sha256 — ${#FILES[@]} artefaktow"
