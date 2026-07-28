#!/usr/bin/env bash
# Buduje trzy drzewa Debug uzywane przez badania coverage_gap i artifact_diff:
#
#   FIXED      — commit z poprawka pojemnosci AGSE (domyslnie 3db7817),
#   MUTANT     — ten sam commit z ODWROCONA wylacznie czescia silnikowa poprawki
#                (src/retractor/lib/compiler.cpp). Zestaw testow pozostaje ten sam,
#                wiec mutacja dotyczy wylacznie kodu produkcyjnego,
#   HISTORICAL — commit-rodzic bez zadnych zmian, czyli stan z epoki K19:
#                wadliwy silnik ORAZ owczesny zestaw testow.
#
# MUTANT i HISTORICAL maja identyczny kod silnika i roznia sie wylacznie zestawem
# testow. Ta para mierzy moc detekcyjna testow, nie wersje silnika.
#
# Mutacja nie jest przepisywana recznie: powstaje przez odwrotne nalozenie
# roznicy commita poprawki ograniczonej do pliku silnika. Dzieki temu jest
# dokladnie tym, co wprowadzil commit, i nie da sie jej rozjechac z historia.
#
# Wszystkie trzy drzewa powstaja z KLONU repozytorium kodu, poza nim samym:
# repozytorium robocze kodu nie jest modyfikowane ani odczytywane inaczej niz
# przez git clone (R2). Katalog roboczy lezy na dysku, nie w /dev/shm — trzy
# drzewa Debug to ~10 GB, wiecej niz tmpfs workera i nadzorcy. Badanie nie mierzy
# czasu, wiec wymog /dev/shm z R7 go nie dotyczy.
set -euo pipefail

FIXED_COMMIT="${FIXED_COMMIT:-3db781711a84c08ce794c3924aab533dba6fcbd1}"
ENGINE_FILE="src/retractor/lib/compiler.cpp"
ROOT="${BUILD_TREES_ROOT:-${TMPDIR:-/tmp}/rdb-extend}"
CODE_REPO="${CODE_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../retractordb" && pwd)}"

die() { printf 'BLAD: %s\n' "$*" >&2; exit 1; }
log() { printf '[build_pair] %s\n' "$*"; }

[ -d "$CODE_REPO/.git" ] || die "brak repozytorium kodu: $CODE_REPO"
git -C "$CODE_REPO" cat-file -e "$FIXED_COMMIT^{commit}" 2>/dev/null ||
  die "brak commita $FIXED_COMMIT w $CODE_REPO"
PARENT_COMMIT="$(git -C "$CODE_REPO" rev-parse "$FIXED_COMMIT^")"

mkdir -p "$ROOT"

build_one() {
  local label="$1"
  local dir="$ROOT/$label"
  if [ -x "$dir/build/Debug/src/retractor/xretractor" ]; then
    log "$label: binarka juz istnieje, pomijam build"
    return 0
  fi
  rm -rf "$dir"
  log "$label: klonowanie"
  git clone --quiet --no-hardlinks "$CODE_REPO" "$dir"

  local commit="$FIXED_COMMIT"
  [ "$label" = "historical" ] && commit="$PARENT_COMMIT"
  git -C "$dir" checkout --quiet --detach "$commit"

  if [ "$label" = "mutant" ]; then
    log "mutant: odwracam silnikowa czesc poprawki ($ENGINE_FILE)"
    git -C "$CODE_REPO" diff "$PARENT_COMMIT" "$FIXED_COMMIT" -- "$ENGINE_FILE" |
      git -C "$dir" apply --reverse - ||
      die "nie udalo sie odwrocic poprawki — historia lub sciezka sie zmienily"
    [ -n "$(git -C "$dir" status --short)" ] || die "mutacja nie zmienila drzewa"
  fi

  # buildrdb.sh rozpoznaje katalog roboczy po nazwie (retractordb/scripts/build/...),
  # a klon lezy pod wlasna nazwa — dlatego wolamy go z podkatalogu scripts/.
  log "$label: build Debug"
  ( cd "$dir/scripts" && ./buildrdb.sh debug ) >"$ROOT/build_$label.log" 2>&1 ||
    die "build $label nie powiodl sie; log: $ROOT/build_$label.log"
  [ -x "$dir/build/Debug/src/retractor/xretractor" ] ||
    die "build $label nie utworzyl binarki"
}

build_one fixed
build_one mutant
build_one historical

# Kontrola pozytywna: binarki musza sie roznic dokladnie w tej jednej decyzji.
grep -c 'floorR(retained) + (source.isDeclaration() ? 2 : 1)' "$ROOT/fixed/$ENGINE_FILE" >/dev/null ||
  die "drzewo fixed nie zawiera poprawki"
grep -c 'ceilR(retained)' "$ROOT/mutant/$ENGINE_FILE" >/dev/null ||
  die "drzewo mutant nie zawiera cofnietej poprawki"
diff <(git -C "$ROOT/fixed" rev-parse HEAD) <(git -C "$ROOT/mutant" rev-parse HEAD) >/dev/null ||
  die "fixed i mutant stoja na roznych commitach"
[ "$(git -C "$ROOT/historical" rev-parse HEAD)" = "$PARENT_COMMIT" ] ||
  die "historical nie stoi na commicie-rodzicu"
# Mutant i historical musza miec BAJTOWO ten sam silnik — inaczej porownanie
# mierzyloby roznice wersji, a nie roznice zestawu testow.
cmp -s "$ROOT/mutant/$ENGINE_FILE" "$ROOT/historical/$ENGINE_FILE" ||
  die "silnik mutanta rozni sie od silnika historycznego"

log "gotowe: $ROOT/{fixed,mutant,historical}"
