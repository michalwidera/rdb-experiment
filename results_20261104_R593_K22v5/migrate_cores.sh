#!/bin/bash
# Migracja 15 rdzeni RQL K22v5 (M1, S1, S2) przez paper-arXiv/measurment-tool/migrate_corpus.py,
# z dowodem w config/migration.tsv. Oryginaly sa zamrozonymi plikami K22 / K22v5 i nie sa zmieniane.
#
# Wywolanie: migrate_cores.sh <binarka pinu 40c28dbe> <xretractor dfcc42d2>
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP="$(cd "$HERE/.." && pwd)"
MIG="${MIGRATE_CORPUS:-/home/michal/github/paper-arXiv/measurment-tool/migrate_corpus.py}"
PIN="$1"
ENG="$2"
OUT="$HERE/config/cores"
TSV="$HERE/config/migration.tsv"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fail() { echo "BLAD MIGRACJI: $*" >&2; exit 2; }
sha() { sha256sum "$1" | awk '{print $1}'; }

# Wydruk -c w katalogu tymczasowym; sciezka binarki nie trafia do wydruku (argv[0] = nazwa).
compile_c() {
  local bin="$1" plan="$2" out="$3" dir
  dir="$(mktemp -d "$WORK/c.XXXX")"
  cp "$plan" "$dir/q.rql"
  (cd "$dir" && PATH="$(dirname "$bin"):$PATH" "$(basename "$bin")" q.rql -c "${@:4}" >"$out" 2>&1) \
    || fail "-c nie przeszlo: $bin $plan"
}

mkdir -p "$OUT"
printf 'cell\tsource\torig_sha256\tmigrated_sha256\tm1\tm1_wrapped\ts\ts1\ts2\tm1_proof\tc_eng_m1_sha256\tc_eng_migrated_sha256\tdeprecated_orig\tdeprecated_migrated\tpostfix_migrated\n' >"$TSV"

for cell in base_F1 base_F2 base_F3 M1_F1 M1_F2 M1_F3 M2_F1 M2_F2 M2_F3 M3_F1 M3_F2 M3_F3 M4_F1 M4_F2 M4_F3; do
  task="${cell%_*}"
  case "${cell#*_}" in F1) dir=F1_fir ;; F2) dir=F2_ecg ;; F3) dir=F3_multirate ;; esac
  if [[ "$task" == base ]]; then
    rel="results_20260801_K22/corpus/$dir/rql/core.rql"
  else
    rel="results_20260801_K22v5/tasks/$task/$dir/rql/core.rql"
  fi
  src="$EXP/$rel"
  pin_plan="$WORK/$cell.pin.rql"
  dst="$OUT/$cell.rql"
  IFS=$'\t' read -r m1 m1n m1d s s1 s2 _sd < <(python3 -I "$MIG" "$PIN" "$ENG" "$src" "$pin_plan" "$dst")
  [[ "$m1" == MIGRATED && "$s" == MIGRATED ]] || fail "$cell: M1=$m1 S=$s"

  # M1: wydruk pinu na planie po M1 = wydruk pinu na oryginale + dokladnie m1n wierszy CALL(to_integer).
  compile_c "$PIN" "$src" "$WORK/$cell.pin_orig.txt"
  compile_c "$PIN" "$pin_plan" "$WORK/$cell.pin_m1.txt"
  added="$(diff "$WORK/$cell.pin_orig.txt" "$WORK/$cell.pin_m1.txt" | grep -c '^>' || true)"
  other="$(diff "$WORK/$cell.pin_orig.txt" "$WORK/$cell.pin_m1.txt" | grep '^[<>]' | grep -vcP '^> \t\tCALL\(to_integer\)$' || true)"
  [[ "$added" == "$m1n" && "$other" == 0 ]] || fail "$cell: dowod M1 (dodane=$added, inne=$other, oczekiwano $m1n)"

  # S1/S2: ten sam wydruk -c silnika na planie po M1 i po S1+S2; --verbose bez `is deprecated`.
  compile_c "$ENG" "$pin_plan" "$WORK/$cell.eng_m1.txt"
  compile_c "$ENG" "$dst" "$WORK/$cell.eng_mig.txt"
  cmp -s "$WORK/$cell.eng_m1.txt" "$WORK/$cell.eng_mig.txt" || fail "$cell: wydruk -c rozni sie po S1/S2"
  compile_c "$ENG" "$src" "$WORK/$cell.v_orig.txt" --verbose
  compile_c "$ENG" "$dst" "$WORK/$cell.v_mig.txt" --verbose
  dep_orig="$(grep -c 'is deprecated' "$WORK/$cell.v_orig.txt" || true)"
  dep_mig="$(grep -c 'is deprecated' "$WORK/$cell.v_mig.txt" || true)"
  postfix="$(grep -v '^\s*#' "$dst" | grep -cE '\.(sumc|avg|min|max)\b' || true)"
  [[ "$dep_mig" == 0 && "$postfix" == 0 ]] || fail "$cell: forma przestarzala po migracji ($dep_mig, $postfix)"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$cell" "$rel" "$(sha "$src")" "$(sha "$dst")" \
    "$m1" "$m1d" "$s" "$s1" "$s2" "+${added} CALL(to_integer)" "$(sha "$WORK/$cell.eng_m1.txt")" \
    "$(sha "$WORK/$cell.eng_mig.txt")" "$dep_orig" "$dep_mig" "$postfix" >>"$TSV"
done
echo "OK: 15 rdzeni zmigrowanych z dowodem -> $TSV"
