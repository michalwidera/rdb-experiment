#!/usr/bin/env bash
# Pilot compile-only K23 (P4). Macierz: cztery profile x sześć planów.
# NIE MIERZY KOSZTU: wyłącznie `xretractor -c` z RDB_BENCH_PLAN, bez -r, bez -m,
# na danych miniaturowych. Wynik: out/<profil>_<plan>.{plan,probe}.
set -euo pipefail

cd "$(dirname "$0")"
CODE_REPO="${CODE_REPO:-/home/michal/github/retractordb}"
profiles=(DEFAULT NO_R2_CANON NO_R1_FACTOR NO_R1_NO_R2)
plans=(F9_R2_Q8 F9_R1_Q8 F9_X_Q8 F9_R2_controls F9_R1_controls F9_X_controls)

rm -rf out temp
mkdir -p out temp

for profile in "${profiles[@]}"; do
  binary="$CODE_REPO/build/K23-$profile/src/retractor/xretractor"
  [ -x "$binary" ] || { echo "BLAD: brak binarki profilu $profile" >&2; exit 2; }
  for plan in "${plans[@]}"; do
    RDB_BENCH_PLAN=1 "$binary" "$plan.rql" -c \
      > "out/${profile}_${plan}.plan" 2> "out/${profile}_${plan}.probe" ||
      { echo "BLAD: kompilacja $plan w profilu $profile nie powiodla sie" >&2; exit 3; }
  done
done

rm -rf temp ./*.desc
echo "OK: $(( ${#profiles[@]} * ${#plans[@]} )) kompilacji"
