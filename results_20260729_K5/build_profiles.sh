#!/usr/bin/env bash
# Buduje pięć profili ablacyjnych z profiles.tsv w izolowanych katalogach
# build/K5-<slug> repozytorium kodu i weryfikuje --build-info bajtowo.
set -euo pipefail

cd "$(dirname "$0")"
here=$(pwd)
experiment_repo=$(realpath ..)
code_repo=${RDB_CODE_REPO:-"$experiment_repo/../retractordb"}
code_repo=$(realpath "$code_repo")
jobs=${K5_BUILD_JOBS:-4}

raw_dir="$here/results/raw/profiles"
conan_dir="$code_repo/build/Conan-K5-Profiles"
toolchain="$conan_dir/build/Release/generators/conan_toolchain.cmake"
mkdir -p "$raw_dir"

if [ ! -f "$toolchain" ]; then
  conan install "$code_repo" \
    -s build_type=Release \
    --build missing \
    -of "$conan_dir" >"$raw_dir/conan-install.log" 2>&1
fi

while IFS=$'\t' read -r profile slug dedup share commutative factor; do
  [ "$profile" = "profile" ] && continue

  build_dir="$code_repo/build/K5-$slug"
  cmake -S "$code_repo" -B "$build_dir" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_TOOLCHAIN_FILE="$toolchain" \
    -DRDB_OPT_DEDUP_SUBSTRATES="$dedup" \
    -DRDB_OPT_SHARE_EQUIVALENT_SELECTS="$share" \
    -DRDB_OPT_COMMUTATIVE_ADD="$commutative" \
    -DRDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES="$factor" \
    -DRDB_BENCH_PROBE=ON >"$raw_dir/cmake-$slug.log" 2>&1

  cmake --build "$build_dir" --target xretractor \
    --parallel "$jobs" >"$raw_dir/build-$slug.log" 2>&1

  binary="$build_dir/src/retractor/xretractor"
  actual=$("$binary" --build-info)
  expected=$(printf '%s\n' \
    "RDB_OPT_DEDUP_SUBSTRATES=$dedup" \
    "RDB_OPT_SHARE_EQUIVALENT_SELECTS=$share" \
    "RDB_OPT_COMMUTATIVE_ADD=$commutative" \
    "RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=$factor" \
    "RDB_BENCH_PROBE=ON")
  if [ "$actual" != "$expected" ]; then
    printf 'Niepoprawne --build-info dla profilu %s\n' "$profile" >&2
    diff -u <(printf '%s\n' "$expected") <(printf '%s\n' "$actual") >&2 || true
    exit 1
  fi
  printf '%s\n' "$actual" >"$raw_dir/build-info-$slug.txt"

  # Macierz ablacyjna testów integracyjnych musi przechodzić w każdym profilu.
  ctest --test-dir "$build_dir" \
    -R '^it_optimizer_ablation-' \
    --output-on-failure >"$raw_dir/ctest-$slug.log" 2>&1
done < profiles.tsv

echo "Profile zbudowane i zweryfikowane."
