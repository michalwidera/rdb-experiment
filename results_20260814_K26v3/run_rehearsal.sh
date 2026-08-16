#!/usr/bin/env bash
# N9 / §7.5 — PROBA GENERALNA PROCEDURY DECYZYJNEJ NA DANYCH PILOTA.
#
# Po co to istnieje
# -----------------
# W K26v2 `reduce_results.py` i `verdict.py` po raz pierwszy zetknely sie z
# prawdziwymi danymi dopiero w P9, po 48 h macierzy. Wysypaly sie wtedy trzy
# defekty naraz: dzielenie przez zero na komorce bez substratu (D6), odwrocony
# straznik izolacji mechanizmu (D7) i scisle porownanie z zerem na wielkosci
# mierzonej (D8). Kazdy z nich jest widoczny juz na KROTKIM biegu prawdziwego
# korpusu — zaden nie wymagal pomiaru kosztowego.
#
# Czego ten skrypt NIE robi
# -------------------------
#   * NIE mierzy kosztu i nie wolno z niego czytac zadnej wielkosci progowej.
#     Progi policzone na danych pilota sa bez znaczenia (§7.5);
#   * NIE dotyka danych glownych — wylacznie `data/calib/`;
#   * NIE tworzy zadnego artefaktu kampanii i nie wchodzi do zadnej redukcji.
#
# Strona czasowa jest tu STALA I SZTUCZNA. To celowe: cena czasowa nie
# uczestniczy w zadnym z defektow, ktorych ta proba szuka, a pelna macierz
# 1440 komorek kosztowalaby 48 h — czyli dokladnie tyle, ile ta faza ma
# zaoszczedzic. Sztuczne wiersze sa oznaczone w naglowku pliku wyniku.
#
# Kryterium zaliczenia: `verdict.py` konczy sie KODEM 0, 1 albo 2, nigdy
# wyjatkiem, kazda rodzina zostaje oceniona, a wejscie celowo uszkodzone daje
# kod 2. Tresc orzeczenia jest bez znaczenia i nie jest wypisywana.
set -euo pipefail

cd "$(dirname "$0")"
HERE="$(pwd)"
OUT="${OUT:-$HOME/k26v3_rehearsal}"
CODE_REPO="${CODE_REPO:-/home/michal/github/retractordb}"

[[ "$OUT" = /* ]] || { echo "BLAD: OUT musi byc sciezka bezwzgledna" >&2; exit 2; }
[[ ! -e "$OUT" ]] || { echo "BLAD: $OUT juz istnieje; odmowa nadpisania proby" >&2; exit 2; }
mkdir -p "$OUT/matrix"

echo "== 1/5 RetractorDB: 84 komorki na danych pilota =="
OUT="$OUT/rdb" CODE_REPO="$CODE_REPO" DATA="$HERE/data/calib" SLOTS_DIVISOR=5 \
  "$HERE/run_main_rdb.sh" | tail -2

echo "== 2/5 Flink: 36 przebiegow na danych pilota =="
OUT="$OUT/flink" DATA="$HERE/data/calib" SLOTS="${REHEARSAL_SLOTS:-600}" \
  "$HERE/run_main_flink.sh" | tail -2

echo "== 3/5 redukcja mechanizmu z PRAWDZIWYCH licznikow i zrzutow planu =="
"$HERE/reduce_results.py" mechanism --rdb "$OUT/rdb" --flink "$OUT/flink" \
  --out "$OUT/matrix/mechanism.tsv"

echo "== 4/5 strona czasowa i bramki: STALE, SZTUCZNE, wylacznie na potrzeby proby =="
python3 - "$OUT/matrix" <<'PY'
import csv
import sys
from pathlib import Path

matrix = Path(sys.argv[1])
FAMILIES = ["F9-R2", "F9-R1", "F9-X"]
ABLATION = {"F9-R2": "NO_R2_CANON", "F9-R1": "NO_R1_FACTOR", "F9-X": "NO_R1_NO_R2"}
GATES = ["corpus_validity", "oracle_values", "oracle_mutants", "counter_known_answer",
         "public_identity", "near_miss_controls", "no_materialization"]

with (matrix / "timing.tsv").open("w", newline="") as handle:
    writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
    writer.writerow(["family", "profile", "q", "block", "compute_median_ns",
                     "compute_p99_ns", "slot_ns", "lost_records"])
    for family in FAMILIES:
        for profile in ("DEFAULT", ABLATION[family]):
            for q in (1, 2, 4, 8, 16, 32):
                for block in range(1, 21):
                    writer.writerow([family, profile, q, block, 1000, 2000, 10000, 0])

with (matrix / "gates.tsv").open("w", newline="") as handle:
    writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
    writer.writerow(["family", "gate", "status", "classification"])
    for family in FAMILIES:
        for gate in GATES:
            writer.writerow([family, gate, "PASS", "clean"])
print("  timing.tsv (stale 1000/2000/10000) i gates.tsv (PASS/clean) zapisane")
PY

echo "== 5/5 procedura decyzyjna =="
set +e
"$HERE/verdict.py" --matrix "$OUT/matrix" >"$OUT/verdict-proby.txt" 2>"$OUT/verdict-proby.err"
rc=$?
set -e
# Kodu NIE wypisujemy: sprawdzamy, ze procedura KONCZY SIE kodem, a nie co
# orzeka. Na danych pilota i sztucznej stronie czasowej orzeczenie nie ma
# zadnej wartosci dowodowej i nie wolno go czytac (§7.5).
case "$rc" in
  0|1|2) echo "  zakonczone kodem ze zbioru {0,1,2}, bez wyjatku" ;;
  *) echo "BLAD: werdykt zwrocil kod $rc spoza {0,1,2}" >&2; exit 3 ;;
esac
[ -s "$OUT/verdict-proby.err" ] && { echo "BLAD: werdykt pisal na stderr — awaria" >&2
  cat "$OUT/verdict-proby.err" >&2; exit 3; }
for family in F9-R2 F9-R1 F9-X; do
  grep -q -- "--- $family " "$OUT/verdict-proby.txt" \
    || { echo "BLAD: rodzina $family nie zostala oceniona" >&2; exit 3; }
done
echo "  wszystkie trzy rodziny ocenione, brak sladu awarii"

echo "== negatyw: uszkodzone wejscie musi dac kod 2 =="
cp -r "$OUT/matrix" "$OUT/matrix-uszkodzony"
rm "$OUT/matrix-uszkodzony/gates.tsv"
mkdir "$OUT/matrix-uszkodzony/gates.tsv"
set +e
"$HERE/verdict.py" --matrix "$OUT/matrix-uszkodzony" >/dev/null 2>"$OUT/negatyw.err"
neg=$?
set -e
[ "$neg" = 2 ] || { echo "BLAD: uszkodzone wejscie dalo kod $neg, oczekiwano 2" >&2; exit 3; }
grep -q "BRAK WERDYKTU" "$OUT/negatyw.err" \
  || { echo "BLAD: brak sladu odmowy na stderr" >&2; exit 3; }
echo "  uszkodzone wejscie -> kod 2, odmowa zapisana"

echo
echo "PROBA GENERALNA ZALICZONA. Tresci orzeczenia NIE WOLNO czytac (§7.5):"
echo "  $OUT/verdict-proby.txt"
