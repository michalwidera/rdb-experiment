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
jobs=${HYG220_BUILD_JOBS:-4}

historical_commit=1bb2d2ce8bec35cd0ab46d168249b706ccbaf303
fixed_commit=abe075ee26775a0e66aa405927561509afdec2dc

trees_root=${HYG220_TREES:-"$code_repo/build/HYG220-trees"}
raw="$here/results/raw/build"
mkdir -p "$raw" "$trees_root"

# Warunek ważności: WEJŚCIA SILNIKA muszą być identyczne po obu stronach.
# Wejściem jest plik `.rql` oraz dane czytane przez FILE — te ostatnie leżą
# w `examples/` i w katalogach testów integracyjnych, część bez rozszerzenia
# (np. `examples/ecg/rec205/rec205`). Zmiana któregokolwiek przestaje być
# różnicą kodu silnika i unieważnia badanie.
engine_inputs=$(git -C "$code_repo" diff --name-only "$historical_commit" "$fixed_commit" \
  -- '*.rql' 'examples/' | wc -l)
if [ "$engine_inputs" -ne 0 ]; then
  echo "Wejscia silnika roznia sie miedzy commitami ($engine_inputs plikow) — badanie nie jest wazne." >&2
  git -C "$code_repo" diff --name-only "$historical_commit" "$fixed_commit" -- '*.rql' 'examples/' >&2
  exit 1
fi

# Zmiany w harnessie testowym NIE unieważniają badania — to badanie nie
# uruchamia ctest — ale muszą być widoczne, żeby nikt nie wziął ich za zmianę
# wejść. Raportowane, nie blokujące.
harness_changed=$(git -C "$code_repo" diff --name-only "$historical_commit" "$fixed_commit" \
  -- 'test/' | grep -v '\.rql$' || true)
if [ -n "$harness_changed" ]; then
  echo "Uwaga: harness testowy zmieniony miedzy commitami (nie wplywa na to badanie):"
  printf '  %s\n' $harness_changed
fi

# --- klon na commicie sprzed poprawki ---
historical="$trees_root/historical"
if [ ! -d "$historical/.git" ]; then
  git clone -q --no-hardlinks "$code_repo" "$historical" >"$raw/clone.log" 2>&1
fi
git -C "$historical" checkout -q "$historical_commit"
git -C "$historical" submodule update -q --init --recursive >>"$raw/clone.log" 2>&1 || true

conan_dir="$code_repo/build/Conan-HYG220"
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
  # Poprawka badana tutaj siedzi w KLIENCIE, wiec `xqry` jest przedmiotem
  # badania na rowni z silnikiem i musi powstac po obu stronach porownania.
  cmake --build "$build_dir" --target xretractor xqry --parallel "$jobs" >"$raw/build-$label.log" 2>&1
  "$build_dir/src/retractor/xretractor" --build-info >"$raw/build-info-$label.txt"
  [ -x "$build_dir/src/qry/xqry" ] || { echo "Brak binarki xqry w $build_dir" >&2; exit 1; }
}

build_one HISTORICAL "$historical"  "$trees_root/build-historical"
build_one FIXED      "$code_repo"   "$code_repo/build/HYG220-FIXED"

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

# Raport czyta commity z tego pliku, zamiast mieć je zaszyte w kodzie. Wartości
# pochodzą z FAKTYCZNIE zbudowanych drzew, nie ze zmiennych na górze skryptu.
{
  printf 'tree\tcommit\n'
  printf 'HISTORICAL\t%s\n' "$(git -C "$historical" rev-parse HEAD)"
  printf 'FIXED\t%s\n' "$(git -C "$code_repo" rev-parse HEAD)"
} > "$here/results/commits.tsv"

echo "Drzewa gotowe: HISTORICAL=$(git -C "$historical" rev-parse --short HEAD) FIXED=$(git -C "$code_repo" rev-parse --short HEAD)"
