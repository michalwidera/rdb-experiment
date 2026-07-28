#!/usr/bin/env bash
# S1 — moc detekcyjna mostu K19 wobec realnego mutanta historycznego.
#
# Pytanie: czy zestaw testow, ktorym K19 uzasadnil twierdzenie o pojemnosci
# historii, wykrywa blad pojemnosci, ktory faktycznie istnial w silniku?
#
# Trzy drzewa (patrz lib/build_trees.sh):
#
#   HISTORICAL — stan z epoki K19: wadliwy silnik + owczesny zestaw testow,
#   MUTANT     — ten sam wadliwy silnik, ale zestaw testow po rozszerzeniu,
#   FIXED      — poprawiony silnik i rozszerzony zestaw testow.
#
# HISTORICAL i MUTANT maja bajtowo identyczny silnik, wiec roznica ich wynikow
# jest roznica mocy detekcyjnej TESTOW, a nie wersji kodu.
#
# Selekcje ctest:
#   K19_ORIGINAL  — dokladnie ta z results_20260728_K19/run.sh,
#   K19_EXTENDED  — ta sama selekcja + it_agse_volatile (polityka MEMORY).
#
# Wynik rozstrzygajacy: mutant przezywajacy zestaw oznacza, ze zestaw nie
# uzasadnia twierdzenia o pojemnosci historii; mutant zabity oznacza, ze uzasadnia.
#
# Badanie nie mierzy czasu i nie korzysta z workera.
set -euo pipefail

cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"
ROOT="${BUILD_TREES_ROOT:-${TMPDIR:-/tmp}/rdb-extend}"

K19_ORIGINAL='^(ut_soperations|ut_compiler|ut_dataModel|it_k19_boundaries|it_agse1|it_agse2|it_agse3|it_deinterleave_roundtrip-run)$'
K19_EXTENDED='^(ut_soperations|ut_compiler|ut_dataModel|it_k19_boundaries|it_agse1|it_agse2|it_agse3|it_deinterleave_roundtrip-run|it_agse_volatile)$'

BUILD_TREES_ROOT="$ROOT" ../lib/build_trees.sh

mkdir -p raw

run_suite() {
  local binary_label="$1" suite_label="$2" filter="$3"
  local build="$ROOT/$binary_label/build/Debug"
  local out="raw/${binary_label}__${suite_label}.txt"
  local rc=0
  env PATH="$build/src/retractor:$build/src/qry:$build/src/rdb:$PATH" \
    ctest --test-dir "$build" -R "$filter" --output-on-failure >"$out" 2>&1 || rc=$?
  printf '%s\n' "$rc"
}

# historical/extended nie istnieje: it_agse_volatile pojawil sie dopiero
# z poprawka, wiec w drzewie z epoki K19 nie ma czego uruchomic.
declare -A RC
for cell in historical/original mutant/original mutant/extended fixed/original fixed/extended; do
  binary="${cell%%/*}"; suite="${cell##*/}"
  case "$suite" in
    original) filter="$K19_ORIGINAL" ;;
    extended) filter="$K19_EXTENDED" ;;
  esac
  echo "== $binary / $suite"
  RC["$cell"]="$(run_suite "$binary" "$suite" "$filter")"
  echo "   ctest rc=${RC["$cell"]}"
done

pass_label() { [ "$1" = "0" ] && printf 'zielony' || printf 'OBLAL'; }
kill_label() { [ "$1" = "0" ] && printf 'PRZEZYL' || printf 'zabity'; }
failed_tests() {
  grep -E '^[[:space:]]+[0-9]+ - ' "raw/$1__$2.txt" |
    sed 's/^[[:space:]]*[0-9]* - //; s/ (Failed)//' |
    tr '\n' ' ' | sed 's/[[:space:]]*$//'
}

{
  printf '# S1 — moc detekcyjna mostu K19 wobec mutanta pojemnosci\n\n'
  printf '%s\n' "- data: $(date -Is)"
  printf '%s\n' "- FIXED: commit \`$(git -C "$ROOT/fixed" rev-parse HEAD)\`"
  printf '%s\n' "- MUTANT: ten sam commit, odwrocona silnikowa czesc poprawki"
  printf '%s\n' "- HISTORICAL: commit \`$(git -C "$ROOT/historical" rev-parse HEAD)\` bez zmian"
  printf '%s\n' "- mutacja: \`compiler::computeRequiredCapacities\`, galaz \`STREAM_AGSE\`"
  printf '%s\n\n' "- typ builda: Debug (trzy drzewa w \`$ROOT\`, klony repozytorium kodu)"

  printf '## Wynik\n\n'
  printf '| Drzewo | Silnik | Zestaw testow | Selekcja | Wynik | Oblane testy |\n'
  printf '|---|---|---|---|---|---|\n'
  printf '| HISTORICAL | wadliwy | z epoki K19 | `K19_ORIGINAL` | %s | %s |\n' \
    "$(kill_label "${RC["historical/original"]}")" "$(failed_tests historical original)"
  printf '| MUTANT | wadliwy | rozszerzony | `K19_ORIGINAL` | %s | %s |\n' \
    "$(kill_label "${RC["mutant/original"]}")" "$(failed_tests mutant original)"
  printf '| MUTANT | wadliwy | rozszerzony | `K19_EXTENDED` | %s | %s |\n' \
    "$(kill_label "${RC["mutant/extended"]}")" "$(failed_tests mutant extended)"
  printf '| FIXED | poprawiony | rozszerzony | `K19_ORIGINAL` | %s | %s |\n' \
    "$(pass_label "${RC["fixed/original"]}")" "$(failed_tests fixed original)"
  printf '| FIXED | poprawiony | rozszerzony | `K19_EXTENDED` | %s | %s |\n' \
    "$(pass_label "${RC["fixed/extended"]}")" "$(failed_tests fixed extended)"
  printf '\n'
  printf 'HISTORICAL i MUTANT roznia sie wylacznie zestawem testow — kod silnika jest\n'
  printf 'w obu bajtowo identyczny (kontrola w `lib/build_trees.sh`).\n\n'
  printf 'Surowe wyjscia ctest: `raw/<drzewo>__<selekcja>.txt`.\n'
} >results.md

cat results.md
