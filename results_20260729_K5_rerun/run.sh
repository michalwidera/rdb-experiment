#!/usr/bin/env bash
# Pełny przebieg kampanii K5. Compile-only; nie rejestruje metryk czasowych
# i nie korzysta z workera pomiarowego.
set -euo pipefail

cd "$(dirname "$0")"
here=$(pwd)
experiment_repo=$(realpath ..)
code_repo=${RDB_CODE_REPO:-"$experiment_repo/../retractordb"}
code_repo=$(realpath "$code_repo")
expected_code_commit=2a5aa86148cc4e76ccc0adb8f3e2fa9f450b9123

# --- R5: warunki wejściowe -------------------------------------------------
if [ -n "$(git -C "$code_repo" status --porcelain=v1 --untracked-files=all)" ]; then
  echo "Repozytorium kodu musi być czyste przed przebiegiem." >&2
  exit 1
fi
if [ "$(git -C "$code_repo" rev-parse HEAD)" != "$expected_code_commit" ]; then
  echo "Niepoprawny commit kodu; oczekiwano $expected_code_commit." >&2
  exit 1
fi
if [ "$(stat -f -c %T /dev/shm)" != "tmpfs" ]; then
  echo "/dev/shm nie jest tmpfs." >&2
  exit 1
fi

mkdir -p results
{
  echo "# Stan przed K5"
  echo
  echo "- czas: $(date --iso-8601=seconds)"
  echo "- kod: $(git -C "$code_repo" rev-parse HEAD)"
  echo "- branch kodu: $(git -C "$code_repo" branch --show-current)"
  echo "- eksperyment: $(git -C "$experiment_repo" rev-parse HEAD)"
  echo "- branch wyników: $(git -C "$experiment_repo" branch --show-current)"
  echo "- system: $(uname -a)"
  echo "- kompilator: $(c++ --version | head -n 1)"
  echo "- Conan: $(conan --version)"
  echo "- CMake: $(cmake --version | head -n 1)"
  echo "- Python: $(python3 --version)"
} > results/state_before.md

# --- K5.3: profile ---------------------------------------------------------
./build_profiles.sh

# --- K5.1/K5.2: workloady --------------------------------------------------
python3 generate.py --output results/workloads

# --- K5.4: macierz kompilacji ----------------------------------------------
python3 collect.py --code-repo "$code_repo" --workloads results/workloads --output results

# --- K5.5: kontrola semantyczna --------------------------------------------
semantic_status=0
python3 semantic.py --code-repo "$code_repo" --workloads results/workloads --output results || semantic_status=$?

# --- K5.6: werdykt ---------------------------------------------------------
python3 verdict.py --output results

# --- R2/R11: repozytorium kodu nietknięte ----------------------------------
if [ -n "$(git -C "$code_repo" status --porcelain=v1 --untracked-files=all)" ]; then
  echo "Przebieg zmienił repozytorium kodu." >&2
  exit 1
fi
if [ "$(git -C "$code_repo" rev-parse HEAD)" != "$expected_code_commit" ]; then
  echo "Commit kodu zmienił się podczas przebiegu." >&2
  exit 1
fi

{
  echo "# Stan po K5"
  echo
  echo "- czas: $(date --iso-8601=seconds)"
  echo "- kod: $(git -C "$code_repo" rev-parse HEAD)"
  echo "- status kodu: czysty"
  echo "- profile: $(($(wc -l < profiles.tsv) - 1))"
  echo "- przypadki: $(python3 -c 'import json;print(len(json.load(open("results/workloads/index.json"))))')"
  echo "- kontrola semantyczna: $([ $semantic_status -eq 0 ] && echo 'wszystkie identyczne' || echo 'ROZBIEŻNOŚĆ')"
  echo "- SHA-256 comparison.csv: $(sha256sum results/comparison.csv | cut -d' ' -f1)"
  echo "- SHA-256 counts.csv: $(sha256sum results/counts.csv | cut -d' ' -f1)"
} > results/state_after.md

echo "K5 zakończone; werdykt: $here/results/summary.md"
exit $semantic_status
