#!/usr/bin/env bash
# Buduje nienadzorowanie trzy profile optymalizatora (K4) i uruchamia sondę
# w każdym z nich. Odpowiednik `buildrdb.sh release-ablation`, ale bez menu.
#
# Profile:
#   OFF        wszystkie przebiegi wyłączone
#   STRUCT     tylko zgodność strukturalna (dedup + współdzielenie SELECT)
#   ALGSTRUCT  strukturalna + algebraiczna (R1 + R2)  [= konfiguracja domyślna]
#
# Ograniczenie z CMakeLists.txt: COMMUTATIVE_ADD=ON wymaga SHARE=ON.
#
# Użycie: ./build_profiles.sh [profil ...]      (domyślnie wszystkie trzy)
set -euo pipefail

cd "$(dirname "$0")"
here=$(pwd)
repo=$(cd ../../.. && pwd)

toolchain="$repo/build/Release/generators/conan_toolchain.cmake"
if [ ! -f "$toolchain" ]; then
  echo "brak $toolchain — uruchom najpierw: scripts/buildrdb.sh release" >&2
  exit 1
fi

profile_flags() {
  case "$1" in
    OFF)       echo "OFF OFF OFF OFF" ;;
    STRUCT)    echo "ON ON OFF OFF" ;;
    ALGSTRUCT) echo "ON ON ON ON" ;;
    *) echo "nieznany profil: $1" >&2; exit 1 ;;
  esac
}

for profile in "${@:-OFF STRUCT ALGSTRUCT}"; do
  read -r dedup share commutative factor <<<"$(profile_flags "$profile")"
  builddir="$repo/build/Release-Ablation/G1-$profile"

  echo "== profil $profile =="
  cmake -S "$repo" -B "$builddir" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_TOOLCHAIN_FILE="$toolchain" \
    -DRDB_OPT_DEDUP_SUBSTRATES="$dedup" \
    -DRDB_OPT_SHARE_EQUIVALENT_SELECTS="$share" \
    -DRDB_OPT_COMMUTATIVE_ADD="$commutative" \
    -DRDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES="$factor" \
    -DRDB_BENCH_PROBE=OFF >"$here/results/raw/cmake-$profile.log"
  cmake --build "$builddir" --target xretractor >"$here/results/raw/build-$profile.log"

  python3 probe.py \
    --xretractor "$builddir/src/retractor/xretractor" \
    --workdir "work-$profile" \
    --profile "$profile" \
    --json "results/probe-$profile.json" | tee "results/raw/probe-$profile.txt"
done

python3 make_summary.py
