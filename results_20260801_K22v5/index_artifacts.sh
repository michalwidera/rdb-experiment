#!/bin/bash
# Końcowy indeks dowodów i wyników; nie uczestniczy w obliczeniu metryk.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/results/artifact_sha256.tsv"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

printf 'sha256\tbytes\tpath\n' >"$TMP"
while IFS= read -r -d '' path; do
  printf '%s\t%s\t%s\n' \
    "$(sha256sum "$path" | awk '{print $1}')" \
    "$(stat -c %s "$path")" \
    "${path#"$HERE/"}" >>"$TMP"
done < <(find "$HERE/evidence" "$HERE/results" -type f ! -path "$OUT" -print0 | sort -z)

for path in "$HERE/REPORT.md" "$HERE/manual_coding.csv" "$HERE/manual_hits_review.csv"; do
  printf '%s\t%s\t%s\n' \
    "$(sha256sum "$path" | awk '{print $1}')" \
    "$(stat -c %s "$path")" \
    "${path#"$HERE/"}" >>"$TMP"
done

mv "$TMP" "$OUT"
trap - EXIT
echo "OK: $(($(wc -l <"$OUT") - 1)) artefaktów w indeksie SHA-256"
