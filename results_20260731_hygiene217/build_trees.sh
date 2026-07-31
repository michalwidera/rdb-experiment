#!/usr/bin/env bash
# Buduje CZTERY binarki silnika dla badania higienicznego 1bb2d2c:
# {PRZED=e1c13bb, PO=1bb2d2c} x {STRUCT, ALGSTRUCT}.
#
# Drzewo PRZED powstaje z KLONU repozytorium kodu, żeby repozytorium źródłowe
# pozostało nietknięte (R2). Drzewo PO buduje się w `build/` repozytorium kodu —
# `build/` jest ignorowany, więc `git status` pozostaje czysty. Ten sam układ,
# co w badaniu higienicznym e1e5181.
#
# Katalogi `build/H217-*` są rozłączne z `build/K6-*`, więc pięć profili
# kampanii K6c pozostaje nietkniętych.
set -euo pipefail

cd "$(dirname "$0")"
here=$(pwd)
experiment_repo=$(realpath ..)
code_repo=${RDB_CODE_REPO:-"$experiment_repo/../retractordb"}
code_repo=$(realpath "$code_repo")
jobs=${H217_BUILD_JOBS:-3}

before_commit=e1c13bb2490e8bfeab28a6de0958271dded57cb1
after_commit=1bb2d2ce8bec35cd0ab46d168249b706ccbaf303

trees_root=${H217_TREES:-"$code_repo/build/H217-trees"}
raw=${H217_RAW_DIR:-"$here/results/raw/build"}
mkdir -p "$raw" "$trees_root"

# shellcheck source=../lib/common.sh
source "$experiment_repo/lib/common.sh"

# --- Warunek ważności: wejścia silnika identyczne po obu stronach -----------
# Jeżeli między commitami zmienił się choć jeden `.rql` albo plik w `examples/`,
# to nie jest już porównanie samego kodu i badanie traci sens.
engine_inputs=$(git -C "$code_repo" diff --name-only "$before_commit" "$after_commit" \
  -- '*.rql' 'examples/' | wc -l)
if [ "$engine_inputs" -ne 0 ]; then
  echo "BLAD: wejscia silnika roznia sie miedzy commitami ($engine_inputs plikow)" >&2
  git -C "$code_repo" diff --name-only "$before_commit" "$after_commit" -- '*.rql' 'examples/' >&2
  exit 1
fi
log "wejscia silnika identyczne miedzy $before_commit a $after_commit (0 roznic)"

# --- klon na commicie PRZED -------------------------------------------------
before_tree="$trees_root/przed"
if [ ! -d "$before_tree/.git" ]; then
  git clone -q --no-hardlinks "$code_repo" "$before_tree" >"$raw/clone.log" 2>&1
fi
git -C "$before_tree" fetch -q origin
git -C "$before_tree" checkout -q "$before_commit"
[ "$(git -C "$before_tree" rev-parse HEAD)" = "$before_commit" ] || {
  echo "BLAD: klon nie wskazuje $before_commit" >&2
  exit 1
}

# Repozytorium kodu musi stać na commicie PO — z niego budujemy stronę PO.
[ "$(git -C "$code_repo" rev-parse HEAD)" = "$after_commit" ] || {
  echo "BLAD: repozytorium kodu nie wskazuje $after_commit" >&2
  exit 1
}

conan_dir="$code_repo/build/Conan-K6-Profiles"
toolchain="$conan_dir/build/Release/generators/conan_toolchain.cmake"
[ -f "$toolchain" ] || {
  log "conan install (toolchain dla H217)"
  conan install "$code_repo" -s build_type=Release --build missing \
    -of "$conan_dir" >"$raw/conan-install.log" 2>&1
}

# --- budowa jednej binarki --------------------------------------------------
# Flagi profili przepisane z profiles.tsv kampanii; STRUCT i ALGSTRUCT to
# dokładnie mianownik i licznik ilorazu r(c).
build_one() {
  local side="$1" source_tree="$2" profile="$3" commutative="$4" factor="$5"
  local build_dir="$code_repo/build/H217-$side-$profile"
  local tag="$side-$profile"

  log "buduje $tag z $source_tree"
  cmake -S "$source_tree" -B "$build_dir" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_TOOLCHAIN_FILE="$toolchain" \
    -DCMAKE_CXX_COMPILER_LAUNCHER=ccache -DCMAKE_C_COMPILER_LAUNCHER=ccache \
    -DRDB_OPT_DEDUP_SUBSTRATES=ON \
    -DRDB_OPT_SHARE_EQUIVALENT_SELECTS=ON \
    -DRDB_OPT_COMMUTATIVE_ADD="$commutative" \
    -DRDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES="$factor" \
    -DRDB_BENCH_PROBE=ON >"$raw/cmake-$tag.log" 2>&1

  cmake --build "$build_dir" --target xretractor --parallel "$jobs" >"$raw/build-$tag.log" 2>&1

  local binary="$build_dir/src/retractor/xretractor"
  verify_probe_binary_profile "$binary" ON ON "$commutative" "$factor" ||
    die "profil $tag nie potwierdza sie w --build-info"
  "$binary" --build-info >"$raw/build-info-$tag.txt"

  # R7: sonda mierzy pod SCHED_FIFO i mlockall — capabilities na KAŻDEJ binarce.
  sudo -n setcap cap_sys_nice,cap_ipc_lock+ep "$binary" ||
    die "nie mozna nadac capabilities RT na $binary"
  getcap "$binary" | grep -q "cap_ipc_lock,cap_sys_nice=ep\|cap_sys_nice,cap_ipc_lock=ep" ||
    die "binarka $binary nie ma wymaganych capabilities RT"
  built=$((built + 1))
}

built=0
build_one PRZED "$before_tree" STRUCT    OFF OFF
build_one PRZED "$before_tree" ALGSTRUCT ON  ON
build_one PO    "$code_repo"   STRUCT    OFF OFF
build_one PO    "$code_repo"   ALGSTRUCT ON  ON

# Reguła zliczania: zero zbudowanych binarek nie jest sukcesem.
[ "$built" -eq 4 ] || die "zbudowano $built binarek, oczekiwano 4"

# Kontrola rozłączności: strona PRZED i PO MUSZĄ się różnić bajtowo, inaczej
# porównujemy binarkę ze sobą i każdy werdykt byłby pusty.
for profile in STRUCT ALGSTRUCT; do
  a=$(sha256sum "$code_repo/build/H217-PRZED-$profile/src/retractor/xretractor" | cut -d' ' -f1)
  b=$(sha256sum "$code_repo/build/H217-PO-$profile/src/retractor/xretractor" | cut -d' ' -f1)
  [ "$a" != "$b" ] || die "binarki PRZED i PO profilu $profile sa identyczne — badanie byloby puste"
done

log "zbudowane i zweryfikowane: $built binarki, strony rozlaczne bajtowo"
