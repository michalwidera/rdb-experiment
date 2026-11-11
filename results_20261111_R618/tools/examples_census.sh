#!/usr/bin/env bash
# Kontrola przykladow R618 (metoda #612): kazdy plik .rql z examples/ rewizji R kompilowany z wlasnego katalogu
# przez `-c -m -q` i `-c -q` binarka all-on i all-off; stdout porownany bajtowo, stderr zachowany.
# Trzy kontrole pozytywne musza dac rozne zwykle listingi. Kopia drzewa z git archive, HOME pusty.
# Uzycie: examples_census.sh <R> <xretractor-on> <xretractor-off> <katalog-wyjscia>
set -euo pipefail
R=$1 ON=$(realpath "$2") OFF=$(realpath "$3") OUT=$4
SRC=/home/michal/github/retractordb
[ ! -e "$OUT" ] || { echo "$OUT istnieje"; exit 2; }
mkdir -p "$OUT"/{tree,home,tmp,dumps}
OUT=$(realpath "$OUT")
POS=(test/IntegrationTest/issue167_dedup_positive/query.rql
     test/IntegrationTest/issue202_hash_shift_factorization/matched.rql
     test/IntegrationTest/select_cse_commutative_add/query.rql)
git -C $SRC archive "$R" -- examples "${POS[@]%/*}" | tar -x -C "$OUT/tree"
for v in ON OFF; do b=${!v}; { echo "$v $b"; "$b" --help 2>&1 | head -3; "$b" --build-info; sha256sum "$b"; } > "$OUT/binary-$v.txt"; done
git -C $SRC ls-tree -r "$R" --name-only -- examples | grep '\.rql$' > "$OUT/programs.txt"
printf '%s\n' "${POS[@]}" > "$OUT/positive.txt"
run() { # lista wariant-pliku -> wiersze TSV
  local list=$1 kind=$2 f d n mode v rc
  while read -r f; do
    d=$(dirname "$f"); n=$(basename "$f")
    for mode in cmq cq; do
      for v in ON OFF; do
        local args=(-c -q); [ $mode = cmq ] && args=(-c -m -q)
        local stem="$OUT/dumps/${f//\//__}.$mode.$v"
        set +e
        (cd "$OUT/tree/$d" && HOME="$OUT/home" TMPDIR="$OUT/tmp" "${!v}" "${args[@]}" "$n" >"$stem.out" 2>"$stem.err")
        rc=$?; set -e
        echo "$rc" > "$stem.rc"
      done
      local same=DIFF; cmp -s "$OUT/dumps/${f//\//__}.$mode.ON.out" "$OUT/dumps/${f//\//__}.$mode.OFF.out" && same=SAME
      printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$kind" "$f" "$mode" "$(cat "$OUT/dumps/${f//\//__}.$mode.ON.rc")" \
        "$(cat "$OUT/dumps/${f//\//__}.$mode.OFF.rc")" "$same" "$(sha256sum "$OUT/dumps/${f//\//__}.$mode.ON.out" | cut -c1-12)"
    done
  done < "$list"
}
{ printf 'rodzaj\tplik\ttryb\trc_on\trc_off\ton_vs_off\tsha_on\n'; run "$OUT/programs.txt" example; run "$OUT/positive.txt" positive; } > "$OUT/census.tsv"
( cd "$OUT/tree" && sha256sum $(cat "$OUT/programs.txt" "$OUT/positive.txt") ) > "$OUT/sources.sha256"
rm -rf "$OUT/tree" "$OUT/home"
awk -F'\t' 'NR>1 && $1=="example" { n++; if ($4!=0||$5!=0) rej++; if ($6!="SAME") d++ }
            NR>1 && $1=="positive" && $3=="cq" { p++; if ($6=="DIFF") pd++ }
            END { printf "przyklady: %d wierszy (%d programow x 2 tryby), odrzucone %d, rozne ON/OFF %d; kontrole pozytywne cq: %d, rozne %d\n", n, n/2, rej+0, d+0, p, pd+0 }' "$OUT/census.tsv"
