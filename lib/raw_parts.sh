#!/usr/bin/env bash
# Dzielenie i skladanie surowych archiwow, ktore nie mieszcza sie w limicie
# 100 MB pojedynczego pliku na GitHubie.
#
# Polityka z 2026-07-31 trzymala wszystkie `*raw.tar.gz` poza git i zostawiala
# w repozytorium sam indeks SHA-256. Kosztem bylo to, ze **klon nie niesie
# danych**: obcy dostawal opis tresci zamiast tresci, a jedyna kopia archiwum
# zyla na jednej maszynie. Decyzja 2026-08-23 odwraca to dla trzech archiwow,
# ktore polityka zdazyla objac: wchodza do repozytorium, a to ponad limit
# wchodzi w czesciach.
#
# Podzial jest odwracalny co do bajtu i sprawdzalny bez zaufania: indeks
# `<archiwum>.parts.tsv` niesie SHA-256 calosci ORAZ kazdej czesci, wiec
# uszkodzenie pojedynczej czesci wskazuje sie, a nie tylko wykrywa.
set -euo pipefail

PART_BYTES="${PART_BYTES:-47185920}"   # 45 MiB, ponizej ostrzezenia 50 MB

usage() {
  cat <<'EOF'
uzycie:
  lib/raw_parts.sh split   <archiwum.tar.gz>   # tworzy .part-NN i .parts.tsv
  lib/raw_parts.sh join    <archiwum.tar.gz>   # sklada z .part-NN i weryfikuje
  lib/raw_parts.sh verify  <archiwum.tar.gz>   # sprawdza czesci bez skladania

Rozmiar czesci: PART_BYTES (domyslnie 47185920 = 45 MiB).
EOF
}

fail() { echo "BLAD: $*" >&2; exit 2; }
sha() { sha256sum "$1" | awk '{print $1}'; }

index_of() { printf '%s.parts.tsv' "$1"; }

do_split() {
  local f="$1"
  [[ -f "$f" ]] || fail "brak pliku: $f"
  rm -f "$f".part-* "$(index_of "$f")"
  split -b "$PART_BYTES" -d -a 2 "$f" "$f".part-
  {
    printf 'name\tbytes\tsha256\n'
    printf 'WHOLE\t%s\t%s\n' "$(stat -c %s "$f")" "$(sha "$f")"
    local p
    for p in "$f".part-*; do
      printf '%s\t%s\t%s\n' "$(basename "$p")" "$(stat -c %s "$p")" "$(sha "$p")"
    done
  } >"$(index_of "$f")"
  echo "podzielone na $(ls "$f".part-* | wc -l) czesci; indeks: $(index_of "$f")"
}

# Sprawdza czesci wobec indeksu. Nie sklada, wiec dziala takze tam, gdzie nie ma
# miejsca na kopie calosci.
do_verify() {
  local f="$1" idx errors=0
  idx="$(index_of "$f")"
  [[ -f "$idx" ]] || fail "brak indeksu: $idx"
  local dir; dir="$(dirname "$f")"
  local name bytes expected actual
  while IFS=$'\t' read -r name bytes expected; do
    [[ "$name" == "name" || "$name" == "WHOLE" ]] && continue
    if [[ ! -f "$dir/$name" ]]; then
      echo "BRAK   $name"; errors=$((errors + 1)); continue
    fi
    actual="$(sha "$dir/$name")"
    if [[ "$actual" == "$expected" && "$(stat -c %s "$dir/$name")" == "$bytes" ]]; then
      echo "OK     $name"
    else
      echo "NIEZGODNA $name"; errors=$((errors + 1))
    fi
  done <"$idx"
  (( errors == 0 )) || fail "$errors czesci niezgodnych lub brakujacych"
  echo "wszystkie czesci zgodne z $idx"
}

do_join() {
  local f="$1" idx
  idx="$(index_of "$f")"
  [[ -f "$idx" ]] || fail "brak indeksu: $idx"
  do_verify "$f"
  # Odmowa cichego nadpisania: jesli calosc juz lezy obok, ma sie zgadzac.
  local expected; expected="$(awk -F'\t' '$1=="WHOLE"{print $3}' "$idx")"
  if [[ -f "$f" ]]; then
    [[ "$(sha "$f")" == "$expected" ]] \
      && { echo "calosc juz jest i zgadza sie z indeksem: $f"; return 0; }
    fail "$f istnieje i rozni sie od indeksu; usun go swiadomie przed skladaniem"
  fi
  cat "$f".part-* >"$f"
  local actual; actual="$(sha "$f")"
  [[ "$actual" == "$expected" ]] \
    || { rm -f "$f"; fail "zlozony plik ma SHA-256 $actual, oczekiwano $expected"; }
  echo "zlozone i zweryfikowane: $f ($actual)"
}

case "${1:-}" in
  split)  [[ $# -eq 2 ]] || { usage >&2; exit 2; }; do_split  "$2" ;;
  join)   [[ $# -eq 2 ]] || { usage >&2; exit 2; }; do_join   "$2" ;;
  verify) [[ $# -eq 2 ]] || { usage >&2; exit 2; }; do_verify "$2" ;;
  -h|--help) usage ;;
  *) usage >&2; exit 2 ;;
esac
