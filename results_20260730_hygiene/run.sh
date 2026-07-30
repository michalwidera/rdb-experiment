#!/usr/bin/env bash
# Badanie higieniczne: równoważność zachowania silnika przez Fix (#214).
set -euo pipefail

cd "$(dirname "$0")"
here=$(pwd)
experiment_repo=$(realpath ..)
code_repo=${RDB_CODE_REPO:-"$experiment_repo/../retractordb"}
code_repo=$(realpath "$code_repo")
fixed_commit=bb3a5216b952432818b23a26365001fe4f7627f5
trees_root=${HYG2_TREES:-"$code_repo/build/HYG2-trees"}

if [ -n "$(git -C "$code_repo" status --porcelain=v1 --untracked-files=all)" ]; then
  echo "Repozytorium kodu musi być czyste przed przebiegiem." >&2; exit 1
fi
if [ "$(git -C "$code_repo" rev-parse HEAD)" != "$fixed_commit" ]; then
  echo "Niepoprawny commit kodu; oczekiwano $fixed_commit." >&2; exit 1
fi
if [ "$(stat -f -c %T /dev/shm)" != "tmpfs" ]; then
  echo "/dev/shm nie jest tmpfs." >&2; exit 1
fi

mkdir -p results

# R14: surowe artefakty trafiaja do archiwum na koniec badania, TAKZE gdy
# badanie zawiodlo — dowod porazki nie moze byc zachowany w gorszej formie niz
# dowod sukcesu. Pulapka EXIT oddaje pierwotny kod wyjscia.
# shellcheck source=../lib/artifacts.sh
source "$experiment_repo/lib/artifacts.sh"
artifacts_pack_on_exit results/raw
{
  echo "# Stan przed badaniem higienicznym"; echo
  echo "- czas: $(date --iso-8601=seconds)"
  echo "- kod (FIXED): $(git -C "$code_repo" rev-parse HEAD)"
  echo "- branch kodu: $(git -C "$code_repo" branch --show-current)"
  echo "- eksperyment: $(git -C "$experiment_repo" rev-parse HEAD)"
  echo "- branch wyników: $(git -C "$experiment_repo" branch --show-current)"
  echo "- system: $(uname -a)"
  echo "- kompilator: $(c++ --version | head -n 1)"
} > results/state_before.md

./build_trees.sh

historical_bin="$trees_root/build-historical/src/retractor/xretractor"
fixed_bin="$code_repo/build/HYG2-FIXED/src/retractor/xretractor"

python3 corpus_diff.py --code-repo "$code_repo" \
  --historical-binary "$historical_bin" --fixed-binary "$fixed_bin" --output results

pipelines_status=0
python3 artifact_diff.py --code-repo "$code_repo" \
  --historical-binary "$historical_bin" --fixed-binary "$fixed_bin" --output results || pipelines_status=$?

python3 verdict.py --output results

# R14 reguła 1: dowody porażki wyjmowane z drzewa surowego PRZED spakowaniem.
if [ -s results/evidence_list.txt ]; then
  while IFS= read -r relative; do
    [ -f "results/$relative" ] || continue
    mkdir -p "results/evidence/$(dirname "${relative#raw/}")"
    cp "results/$relative" "results/evidence/${relative#raw/}"
  done < results/evidence_list.txt
  echo "dowody porazki: $(wc -l < results/evidence_list.txt) plikow w results/evidence/"
else
  echo "dowody porazki: brak (badanie bez roznic)"
fi

if [ -n "$(git -C "$code_repo" status --porcelain=v1 --untracked-files=all)" ]; then
  echo "Przebieg zmienił repozytorium kodu." >&2; exit 1
fi

{
  echo "# Stan po badaniu higienicznym"; echo
  echo "- czas: $(date --iso-8601=seconds)"
  echo "- kod: $(git -C "$code_repo" rev-parse HEAD)"
  echo "- status kodu: czysty"
  echo "- SHA-256 corpus.csv: $(sha256sum results/corpus.csv | cut -d' ' -f1)"
} > results/state_after.md

echo "Badanie zakończone; wynik: $here/results/summary.md"
exit $pipelines_status
