#!/usr/bin/env bash
# Trwaly wrapper jednej rodziny P8, uruchamiany przez lancuch `run_matrix_chain.sh`.
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
resume="${RESUME:-0}"

[[ -d "$control" ]] || { echo "BLAD: brak katalogu kontrolnego $control" >&2; exit 2; }
# `runner.rc` jest nienadpisywalne: rodzina zakonczona ma dokladnie jeden status.
# `started.tsv` i `runner.log` przezywaja WIECEJ NIZ JEDNO podejscie, bo bieg
# przerwany w polowie (twarde wylaczenie) nie zostawia `runner.rc` i musi dac sie
# wznowic. Kazde podejscie dopisuje wlasny wiersz i wlasny kawalek logu.
[[ ! -e "$control/runner.rc" ]] || {
  echo "BLAD: $control/runner.rc juz istnieje; odmowa nadpisania" >&2
  exit 2
}

attempts_file="$control/started.tsv"
if [[ ! -e "$attempts_file" ]]; then
  printf 'attempt\tfamily\tpid\tstarted_epoch\tresume\n' >"$attempts_file"
fi
attempt="$(grep -c . "$attempts_file")"  # naglowek + wiersze poprzednich podejsc
printf '%s\t%s\t%s\t%s\t%s\n' "$attempt" "$family" "$$" "$(date +%s)" "$resume" >>"$attempts_file"

runner_args=(
  --family "$family"
  --cpu "$cpu"
  --code-repo "$code_repo"
  --p6-rdb "$p6_rdb"
  --out "$out"
  --archive-dir "$archive_dir"
)
if [[ "$resume" == 1 ]]; then
  runner_args+=(--resume)
fi

printf '=== podejscie %s, %s ===\n' "$attempt" "$(date '+%F %T %Z')" >>"$control/runner.log"

set +e
"$HERE/run_matrix_worker.py" "${runner_args[@]}" >>"$control/runner.log" 2>&1
rc=$?
set -e

tmp="$control/.runner.rc.$$"
printf '%s\n' "$rc" >"$tmp"
mv "$tmp" "$control/runner.rc"
exit "$rc"
