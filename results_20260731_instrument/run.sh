#!/usr/bin/env bash
# E4 — zebranie cech pracy na slot i przeliczenie modelu kosztu (K20 etap 1b).
#
# Czego ten skrypt NIE robi, świadomie:
#
#  - NIE uruchamia badania higienicznego. Higiena `1bb2d2c` -> `issue_219-instrument`
#    jest WARUNKIEM WSTĘPNYM (README) i wykonuje ją osobna, istniejąca maszyneria
#    (wzorzec: results_20260731_hygiene217/build_trees.sh + run.py + verdict.py).
#    Skrypt tylko sprawdza, że wynik higieny leży na dysku i mówi „brak wpływu".
#  - NIE mierzy czasu. Cele `p99` pochodzą z K6c i nie są odtwarzane (README,
#    sekcja „Odstępstwo"). Dlatego NIE ma tu rytuału kampanii: ani rebootu, ani
#    przełączania governora — nie byłoby czego chronić, bo nic nie jest mierzone
#    zegarem. Gdyby kiedyś ten skrypt zaczął mierzyć czas, rytuał trzeba dodać.
set -euo pipefail

cd "$(dirname "$0")"
here=$(pwd)
experiment_repo=$(realpath ..)
code_repo=${RDB_CODE_REPO:-"$experiment_repo/../retractordb"}
code_repo=$(realpath "$code_repo")

k6c_root=${E4_K6C_ROOT:-"$experiment_repo/results_20260730_K6c"}
binary=${E4_BINARY:-"$code_repo/build/Release-Probe/src/retractor/xretractor"}
hygiene_verdict=${E4_HYGIENE_VERDICT:-"$here/results/hygiene_verdict.txt"}
out="$here/results"

export PYTHONDONTWRITEBYTECODE=1

die() {
  echo "E4: $*" >&2
  exit 1
}

# --- Warunek wstępny 1: higiena --------------------------------------------
# Reguła kampanii: zmiana w kodzie wspólnym unieważnia wcześniejsze wyniki,
# dopóki nie wykazano braku wpływu. Bez tego zestawianie cech z buildu
# instrumentowanego z celami z `1bb2d2c` nie ma podstawy.
[ -f "$hygiene_verdict" ] || die "brak werdyktu higieny: $hygiene_verdict — uruchom badanie higieniczne PRZED tym krokiem"
grep -qi 'brak wplywu\|brak wpływu' "$hygiene_verdict" ||
  die "werdykt higieny nie mówi 'brak wpływu' — ZATRZYMANIE, nie obejście"
echo "E4: higiena OK ($(head -1 "$hygiene_verdict"))"

# --- Warunek wstępny 2: binarka z sondą ------------------------------------
[ -x "$binary" ] || die "brak binarki z sondą: $binary (zbuduj: scripts/buildrdb.sh probe)"
"$binary" --build-info 2>&1 | grep -q 'RDB_BENCH_PROBE=ON' ||
  die "binarka nie ma sondy — --build-info nie raportuje RDB_BENCH_PROBE=ON"

# --- Warunek wstępny 3: kampania K6c dostępna do ODCZYTU --------------------
[ -f "$k6c_root/results/rate.json" ] || die "brak celów: $k6c_root/results/rate.json"
[ -x "$k6c_root/generate.py" ] || [ -f "$k6c_root/generate.py" ] || die "brak generatora workloadów w $k6c_root"

# --- Krok 1: cechy ----------------------------------------------------------
python3 "$here/collect_work.py" \
  --binary "$binary" \
  --code-repo "$code_repo" \
  --k6c-root "$k6c_root" \
  --output "$out"

# --- Krok 2: model ----------------------------------------------------------
python3 "$here/cost_model_v2.py" \
  --rate-json "$k6c_root/results/rate.json" \
  --work-json "$out/work.json" \
  --output "$out"

echo "E4: gotowe — $out/cost_model_v2.md"
