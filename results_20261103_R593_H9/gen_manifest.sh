#!/usr/bin/env bash
# Explicit manifest of the R593 H9 replication apparatus and premeasurement evidence.
# KOPIA results_20260814_K26v3/gen_manifest.sh dla zawartosci tego katalogu: bez Flinka,
# pilota, generatora blokow i kalibracji; z migracja, ANEKS-1 i analyze_r593.py.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

mapfile -t FILES < <(
  printf '%s\n' \
    .gitignore \
    README.md \
    ANEKS-1_rate.tsv \
    profiles.tsv \
    blocks.tsv \
    analyze_r593.py \
    bind_campaign.py \
    build_profiles.sh \
    capture_worker.py \
    collect_p8_archives.sh \
    freeze_check.sh \
    gen_corpus.py \
    gen_manifest.sh \
    install_worker_service.sh \
    mechanism_table.py \
    oracle_values.py \
    reduce_results.py \
    run_gates.py \
    run_main_rdb.sh \
    run_matrix_chain.sh \
    run_matrix_family.sh \
    run_matrix_worker.py \
    start_matrix_p8.sh \
    test_apparatus.py \
    test_pipeline.py \
    validate_corpus.py \
    verdict.py
  find data rql migration -type f | sort
  find corpus_validation -type f | sort
  find calib -maxdepth 1 -type f -name '*.py' | sort
  [[ -f ANEKS-2_worker_binaria.tsv ]] && printf '%s\n' ANEKS-2_worker_binaria.tsv
  [[ -f ANEKS-3_worker_srodowisko.tsv ]] && printf '%s\n' ANEKS-3_worker_srodowisko.tsv
)

for file in "${FILES[@]}"; do
  [[ -f "$file" ]] || { echo "BLAD: manifest wymienia brakujacy plik $file" >&2; exit 2; }
done

sha256sum "${FILES[@]}" > manifest.sha256
echo "OK: manifest.sha256 - ${#FILES[@]} artefaktow"
