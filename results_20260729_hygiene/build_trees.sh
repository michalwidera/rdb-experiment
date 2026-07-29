#!/usr/bin/env bash
# Buduje dwa drzewa silnika: przed i po Fix (#214). Drzewo HISTORICAL powstaje
# z KLONU repozytorium kodu, żeby repozytorium źródłowe pozostało nietknięte
# (REQUIREMENTS.md R2). Drzewo FIXED buduje się w katalogu build/ repozytorium
# kodu — build/ jest ignorowany, więc `git status` pozostaje czysty.
set -euo pipefail

cd "$(dirname "$0")"
here=$(pwd)
experiment_repo=$(realpath ..)
code_repo=${RDB_CODE_REPO:-"$experiment_repo/../retractordb"}
code_repo=$(realpath "$code_repo")
jobs=${HYG_BUILD_JOBS:-4}

historical_commit=0e0f70161fd46ffd918dbdb457e6dbdcd4439b03
fixed_commit=2a5aa86148cc4e76ccc0adb8f3e2fa9f450b9123

trees_root=${HYG_TREES:-"$here/.trees"}
raw="$here/results/raw/build"
mkdir -p "$raw" "$trees_root"

# --- klon na commicie sprzed poprawki ---
historical="$trees_root/historical"
if [ ! -d "$historical/.git" ]; then
  git clone -q --no-hardlinks "$code_repo" "$historical" >"$raw/clone.log" 2>&1
fi
git -C "$historical" checkout -q "$historical_commit"
git -C "$historical" submodule update -q --init --recursive >>"$raw/clone.log" 2>&1 || true

conan_dir="$code_repo/build/Conan-HYG"
toolchain="$conan_dir/build/Release/generators/conan_toolchain.cmake"
if [ ! -f "$toolchain" ]; then
  conan install "$code_repo" -s build_type=Release --build missing \
    -of "$conan_dir" >"$raw/conan-install.log" 2>&1
fi

build_one() {
  local label=$1 source=$2 build_dir=$3
  cmake -S "$source" -B "$build_dir" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_TOOLCHAIN_FILE="$toolchain" \
    -DRDB_BENCH_PROBE=ON >"$raw/cmake-$label.log" 2>&1
  cmake --build "$build_dir" --target xretractor --parallel "$jobs" >"$raw/build-$label.log" 2>&1
  "$build_dir/src/retractor/xretractor" --build-info >"$raw/build-info-$label.txt"
}

build_one HISTORICAL "$historical"  "$trees_root/build-historical"
build_one FIXED      "$code_repo"   "$code_repo/build/HYG-FIXED"

# Oba drzewa muszą mieć IDENTYCZNE przełączniki optymalizatora — inaczej
# porównywałyby profile, a nie skutek poprawki.
if ! diff -u "$raw/build-info-HISTORICAL.txt" "$raw/build-info-FIXED.txt" >"$raw/build-info-diff.txt"; then
  echo "Drzewa różnią się konfiguracją optymalizatora." >&2
  cat "$raw/build-info-diff.txt" >&2
  exit 1
fi

# Kontrola pozytywna: drzewa MUSZĄ różnić się kodem, inaczej badanie jest puste.
if [ "$(git -C "$historical" rev-parse HEAD)" = "$fixed_commit" ]; then
  echo "Drzewo historyczne stoi na commicie z poprawką." >&2
  exit 1
fi

echo "Drzewa gotowe: HISTORICAL=$(git -C "$historical" rev-parse --short HEAD) FIXED=$(git -C "$code_repo" rev-parse --short HEAD)"
