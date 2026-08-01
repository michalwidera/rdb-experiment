#!/bin/bash
# Oracle semantyczny K22 — porównanie kanonicznych strumieni trzech modeli.
#
# W etapie K22a ten skrypt CELOWO nie liczy jeszcze niczego z korpusu: korpus
# nie istnieje, a predeklaracja nie jest utrwalona. Zamiast po cichu zwrócić
# pustą tabelę (co wyglądałoby na wynik), sprawdza warunki wejścia i zatrzymuje
# się z nazwaniem tego, czego brakuje.
#
# Kolejność wymuszona przez PREDECLARATION.md §11:
#   1. aparatura przechodzi własne testy         (tests/test_k22a.sh)
#   2. predeklaracja jest utrwalona              (commit człowieka)
#   3. korpus istnieje i ma znaczniki rdzenia    (K22b)
#   4. `tail` odczytany z silnika, nie wyliczony (results/tails.csv)
#   5. dopiero wtedy porównanie
set -uo pipefail

ORACLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAMPAIGN="$(cd "$ORACLE_DIR/.." && pwd)"

fail() {
  echo "ZATRZYMANIE: $*" >&2
  exit 2
}

echo "== 1. Testy aparatury"
"$CAMPAIGN/tests/test_k22a.sh" >/dev/null || fail "aparatura nie przechodzi wlasnych testow (tests/test_k22a.sh)"
echo "   OK"

echo "== 2. Korpus"
mapfile -t cores < <(find "$CAMPAIGN/corpus" -type f \( -name '*.rql' -o -name '*.py' -o -name '*.java' \) 2>/dev/null)
if [[ ${#cores[@]} -eq 0 ]]; then
  fail "korpus jest pusty — etap K22b nie zostal wykonany.
   Zero porownanych rdzeni jest BLEDEM, nie wynikiem (PREDECLARATION.md §7.5).
   Nie wolno przejsc do K22b przed akceptacja PREDECLARATION.md (bramka K22a)."
fi
echo "   znaleziono ${#cores[@]} plikow rdzenia"

echo "== 3. Ogony odczytane z silnika"
[[ -f "$CAMPAIGN/results/tails.csv" ]] || fail "brak results/tails.csv.
   'tail' MUSI pochodzic z 'xretractor <plan>.rql -c', nie z rachunku obok silnika
   (PREDECLARATION.md §5.2 — wniosek metodologiczny z K6c)."
echo "   OK"

echo "== 4. Porownanie"
fail "porownanie korpusu jest zadaniem etapu K22b; w K22a nie ma czego porownywac"
