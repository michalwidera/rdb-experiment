#!/bin/bash
# Regresja aparatury K22a — testy o znanej odpowiedzi dla oracle'a i metryk.
#
# Ten zestaw NIE mierzy niczego z korpusu. Sprawdza wyłącznie, czy aparatura
# pomiarowa działa: czy semantyka referencyjna odtwarza arytmetykę silnika,
# czy komparator łapie każdą klasę rozjazdu i czy skrypt metryk liczy to,
# co deklaruje `coding_manual.md`.
#
# Uruchamiać przed każdym etapem K22b–K22d. Aparatura, która nie przechodzi
# własnych testów, nie może rozstrzygać hipotezy.
set -uo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAMPAIGN="$(cd "$TEST_DIR/.." && pwd)"

failures=0
checks=0

run_suite() {
  local name="$1"
  local dir="$2"
  local script="$3"
  checks=$((checks + 1))
  echo "=== $name"
  if (cd "$dir" && python3 "$script"); then
    echo "--- $name: OK"
  else
    echo "--- $name: PORAZKA"
    failures=$((failures + 1))
  fi
  echo
}

run_suite "semantyka referencyjna (arytmetyka silnika)" "$CAMPAIGN/oracle" "test_refsem.py"
run_suite "komparator strumieni kanonicznych" "$CAMPAIGN/oracle" "test_compare.py"
run_suite "skrypt metryk konstrukcji" "$CAMPAIGN/metrics" "test_metrics.py"

echo "==== $((checks - failures))/$checks zestawow OK"
exit $((failures > 0 ? 1 : 0))
