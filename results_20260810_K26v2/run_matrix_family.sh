#!/usr/bin/env bash
# Trwaly wrapper jednej rodziny P8, uruchamiany w odlaczonej sesji screen workera.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if (( $# != 7 )); then
  echo "uzycie: $(basename "$0") FAMILY CPU CODE_REPO P6_RDB OUT ARCHIVE_DIR CONTROL_DIR" >&2
  exit 2
fi

family="$1"
cpu="$2"
code_repo="$3"
p6_rdb="$4"
out="$5"
archive_dir="$6"
control="$7"

[[ -d "$control" ]] || { echo "BLAD: brak katalogu kontrolnego $control" >&2; exit 2; }
for marker in started.tsv runner.log runner.rc; do
  [[ ! -e "$control/$marker" ]] || {
    echo "BLAD: $control/$marker juz istnieje; odmowa nadpisania" >&2
    exit 2
  }
done

printf 'key\tvalue\nfamily\t%s\npid\t%s\nstarted_epoch\t%s\n' \
  "$family" "$$" "$(date +%s)" >"$control/started.tsv"

set +e
"$HERE/run_matrix_worker.py" \
  --family "$family" \
  --cpu "$cpu" \
  --code-repo "$code_repo" \
  --p6-rdb "$p6_rdb" \
  --out "$out" \
  --archive-dir "$archive_dir" \
  >"$control/runner.log" 2>&1
rc=$?
set -e

tmp="$control/.runner.rc.$$"
printf '%s\n' "$rc" >"$tmp"
mv "$tmp" "$control/runner.rc"
exit "$rc"
