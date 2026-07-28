#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
here=$(pwd)
experiment_repo=$(realpath ..)
code_repo=${RDB_CODE_REPO:-"$experiment_repo/../retractordb"}
code_repo=$(realpath "$code_repo")
expected_code_commit=50e19b75d71ef42c842c7db6214e5c31d5dd86ab

if [ -n "$(git -C "$experiment_repo" status --porcelain=v1 --untracked-files=all)" ]; then
  echo "Repozytorium eksperymentu musi być czyste przed przebiegiem." >&2
  exit 1
fi
if [ -n "$(git -C "$code_repo" status --porcelain=v1 --untracked-files=all)" ]; then
  echo "Repozytorium kodu musi być czyste przed przebiegiem." >&2
  exit 1
fi
if [ "$(git -C "$code_repo" rev-parse HEAD)" != "$expected_code_commit" ]; then
  echo "Niepoprawny commit kodu; oczekiwano $expected_code_commit." >&2
  exit 1
fi

experiment_head=$(git -C "$experiment_repo" rev-parse HEAD)
mkdir -p results/raw
{
  echo "# Stan przed K4"
  echo
  echo "- czas: $(date --iso-8601=seconds)"
  echo "- kod: $(git -C "$code_repo" rev-parse HEAD)"
  echo "- branch kodu: $(git -C "$code_repo" branch --show-current)"
  echo "- eksperyment: $experiment_head"
  echo "- branch wyników: $(git -C "$experiment_repo" branch --show-current)"
  echo "- system: $(uname -a)"
  echo "- kompilator: $(c++ --version | head -n 1)"
  echo "- Conan: $(conan --version)"
  echo "- CMake: $(cmake --version | head -n 1)"
} > results/state_before.md

./build_profiles.sh
python3 collect.py --code-repo "$code_repo" --output results

if [ -n "$(git -C "$code_repo" status --porcelain=v1 --untracked-files=all)" ]; then
  echo "Przebieg zmienił repozytorium kodu." >&2
  exit 1
fi
if [ "$(git -C "$code_repo" rev-parse HEAD)" != "$expected_code_commit" ]; then
  echo "Commit kodu zmienił się podczas przebiegu." >&2
  exit 1
fi

{
  echo "# Stan po K4"
  echo
  echo "- czas: $(date --iso-8601=seconds)"
  echo "- kod: $(git -C "$code_repo" rev-parse HEAD)"
  echo "- status kodu: czysty"
  echo "- liczba profili: 5"
  echo "- liczba wierszy: $(($(wc -l < results/counts.csv) - 1))"
  echo "- SHA-256 counts.csv: $(sha256sum results/counts.csv | cut -d' ' -f1)"
  echo "- SHA-256 counts.json: $(sha256sum results/counts.json | cut -d' ' -f1)"
} > results/state_after.md

echo "K4 zakończone; wyniki: $here/results/summary.md"
