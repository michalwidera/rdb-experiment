#!/bin/bash
# Bramka niezmienności i proweniencji K23 — SZKIELET, jeszcze NIE bramka.
#
# Wzorzec: results_20260801_K22v5/freeze_check.sh. Różnica jest zamierzona:
# tamten skrypt powstał PO zamrożeniu i nosi prawdziwe sumy kontrolne, ten
# powstaje PRZED predeklaracją (STOP-5) i nosi w ich miejscu znaczniki @@…@@.
# Dopóki choć jeden znacznik zostaje, skrypt kończy się błędem — bramka, która
# przechodzi z niewypełnionymi polami, byłaby gorsza niż jej brak (dwa razy
# w łuku K24 bramka niezdolna odróżnić wersji błędnej przeszła i zmyliła).
#
# Wypełnić dopiero w P5, w tej samej sesji, w której zamraża się predeklarację:
#   - SHA silnika, artykułu i eksperymentu,
#   - SHA-256 czterech binariów profili i xqry,
#   - wersję JDK/Flinka (po decyzji D-2),
#   - liczbę rekordów przebiegu i ziarna.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_REPO="$(cd "$HERE/.." && pwd)"
CODE_REPO="${CODE_REPO:-/home/michal/github/retractordb}"
PAPER_REPO="${PAPER_REPO:-/home/michal/github/paper-arXiv}"

fail() { echo "BLAD BRAMKI: $*" >&2; exit 2; }
eq() { [[ "$1" == "$2" ]] || fail "$3: otrzymano '$1', oczekiwano '$2'"; }

# --- pola do wypełnienia w P5 ---------------------------------------------
EXPECTED_BRANCH="experiment/20260808_K23"
EXPECTED_CODE_SHA="@@CODE_SHA@@"          # ≥ 1cfccf9 (instrument + bramka 36 przypadków)
EXPECTED_PAPER_SHA="@@PAPER_SHA@@"
EXPECTED_RECORDS="@@RECORDS@@"            # zamrożona liczba rekordów przebiegu
# ---------------------------------------------------------------------------

for value in "$EXPECTED_CODE_SHA" "$EXPECTED_PAPER_SHA" "$EXPECTED_RECORDS"; do
  case "$value" in
    @@*@@) fail "predeklaracja niezamrożona — pole '$value' niewypełnione; do tego czasu ŻADEN pomiar kosztowy nie jest dozwolony (STOP-5)" ;;
  esac
done

eq "$(git -C "$EXP_REPO" branch --show-current)" "$EXPECTED_BRANCH" "branch"
eq "$(git -C "$CODE_REPO" rev-parse HEAD)" "$EXPECTED_CODE_SHA" "retractordb HEAD"
eq "$(git -C "$PAPER_REPO" rev-parse HEAD)" "$EXPECTED_PAPER_SHA" "paper-arXiv HEAD"
[[ -z "$(git -C "$CODE_REPO" status --short)" ]] || fail "drzewo retractordb brudne"
[[ -z "$(git -C "$EXP_REPO" status --short)" ]] || fail "drzewo rdb-experiment brudne"

# Profile: cztery binaria, każde potwierdzone przez --build-info wobec profiles.tsv.
# shellcheck source=../lib/common.sh
source "$EXP_REPO/lib/common.sh"
while IFS=$'\t' read -r profile slug dedup share commutative factor; do
  [ "$profile" = "profile" ] && continue
  [ -n "$profile" ] || continue
  binary="$CODE_REPO/build/K23-$slug/src/retractor/xretractor"
  verify_probe_binary_profile "$binary" "$dedup" "$share" "$commutative" "$factor" ||
    fail "profil $profile nie potwierdza sie w --build-info"
done < "$HERE/profiles.tsv"

echo "OK: zamrożenie K23 potwierdzone"
