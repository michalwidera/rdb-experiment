#!/usr/bin/env bash
# Pilot z PRZEBIEGIEM RUNTIME — K23 iteracja 2 (P4'), aparatura NOWA w tej iteracji.
#
# Po co ten skrypt istnieje
# -------------------------
# Iteracja 1 padła, bo pilot był compile-only: `xretractor -c` NIE WOŁA EWALUATORA,
# więc zamrożony korpus przeszedł bramkę, mimo że żaden z 14 planów z `Sqrt` nie
# dawał się wykonać. `run_pilot.sh` (compile-only) zostaje bez zmian — mierzy liczby
# mechanizmu z planu. Ten skrypt dokłada to, czego tamtemu brakowało: KAŻDA rodzina
# musi wykonać pełny przebieg i pokazać liczniki LOGICAL i WORK.
#
# Bramka jest pokazana NAJPIERW na wersji obalonej
# ------------------------------------------------
# Reguła tego łuku: bramka musi umieć odróżnić wersję obaloną, inaczej nie jest
# bramką. Wersją obaloną jest tu korpus, który KOMPILUJE SIĘ, ale NIE WYKONUJE —
# dokładnie stan, w którym iteracja 1 dotarła do P6. Odtwarzamy go legalnie:
# `Abs` jest w gramatyce (RQL.g4) i nie ma implementacji w ewaluatorze, więc plan
# z `Abs` kompiluje się z rc=0 i wywraca w wykonaniu z rc=4 — tą samą ścieżką, co
# `Sqrt` przed naprawą `ebd8aab`. Skrypt przepuszcza ten przypadek przez TĘ SAMĄ
# funkcję asercji co komórki macierzy i wymaga, żeby została ODRZUCONA. Jeżeli
# przypadek negatywny przejdzie, skrypt kończy się błędem, zanim policzy cokolwiek
# innego.
#
# Wynik: out_rt/<profil>_<plan>.{out,counters}, out/DEFAULT_diag_X_named.{plan,probe}.
set -euo pipefail

cd "$(dirname "$0")"
CODE_REPO="${CODE_REPO:-/home/michal/github/retractordb}"
SLOTS="${SLOTS:-100}"
profiles=(DEFAULT NO_R2_CANON NO_R1_FACTOR NO_R1_NO_R2)
plans=(F9_R2_Q8 F9_R1_Q8 F9_X_Q8 F9_R2_controls F9_R1_controls F9_X_controls)
#: Plany rodzin — tylko one muszą materializować substrat. Plany kontrolne z założenia
#: mogą go nie mieć (kontrola „ten sam program bez etapu materializowanego").
main_plans=" F9_R2_Q8 F9_R1_Q8 F9_X_Q8 "

# Wyciekły `xretractor -x` z poprzedniego przebiegu wywraca kolejne uruchomienia
# i każde z nich diagnozuje się osobno. Sprawdzamy to raz, na wejściu.
if pgrep -af '[x]retractor' >/dev/null; then
  echo "BLAD: w systemie biegnie xretractor — najpierw sprzatnij, potem mierz" >&2
  pgrep -af '[x]retractor' >&2
  exit 2
fi

fail_reason=""

# ─── Asercja jednej komórki ──────────────────────────────────────────────────
# Zwraca 0, gdy przebieg jest dowodem WYKONYWALNOŚCI planu. Cztery warunki:
#   1. kod wyjścia 0 — samo to odróżnia wersję obaloną (`Abs` daje 4);
#   2. wiersz LOGICAL jest obecny — inaczej mierzylibyśmy binarkę bez sondy;
#   3. mianownik niezerowy (publiczne dopisania > 0) — plan, który nie wypisał ani
#      jednego rekordu publicznego, nie policzył się, choćby wrócił z zerem;
#   4. wiersz WORK jest obecny.
# Warunek na substrat jest osobny (`want_substrate`), bo kontrole negatywne mają
# prawo nie materializować niczego i to jest ich oczekiwany wynik.
assert_cell() {
  local label="$1" rc="$2" counters="$3" want_substrate="$4"
  local logical work pub sub
  fail_reason=""

  if [ "$rc" != "0" ]; then
    fail_reason="kod wyjscia $rc — plan sie NIE WYKONAL (compile-only by tego nie zobaczyl)"
    return 1
  fi
  logical="$(grep -m1 '^LOGICAL ' "$counters" || true)"
  work="$(grep -m1 '^WORK ' "$counters" || true)"
  if [ -z "$logical" ]; then
    fail_reason="brak wiersza LOGICAL — sonda nie jest wkompilowana albo przebieg nie doszedl do raportu"
    return 1
  fi
  if [ -z "$work" ]; then
    fail_reason="brak wiersza WORK"
    return 1
  fi
  pub="$(sed -n 's/.*publiczne: dopisania=\([0-9]*\).*/\1/p' <<<"$logical")"
  sub="$(sed -n 's/^LOGICAL substrat: dopisania=\([0-9]*\).*/\1/p' <<<"$logical")"
  if [ "${pub:-0}" -le 0 ]; then
    fail_reason="mianownik pusty — zero publicznych rekordow wyjsciowych"
    return 1
  fi
  if [ "$want_substrate" = "1" ] && [ "${sub:-0}" -le 0 ]; then
    fail_reason="rodzina nie zapisala ani jednego rekordu substratu"
    return 1
  fi
  printf '  ok  %-34s substrat=%-6s publiczne=%-6s\n' "$label" "${sub}" "${pub}"
  return 0
}

run_cell() {  # profil plan katalog_wyjsciowy -> ustawia CELL_RC, CELL_COUNTERS
  local binary="$1" plan="$2" outdir="$3" tag="$4"
  rm -rf temp && mkdir -p temp "$outdir"
  CELL_COUNTERS="$outdir/$tag.counters"
  set +e
  RDB_BENCH_LOGICAL=1 RDB_BENCH_WORK=1 timeout 300 \
    "$binary" "$plan" -m "$SLOTS" -r -k >"$outdir/$tag.out" 2>"$CELL_COUNTERS"
  CELL_RC=$?
  set -e
}

# ─── 1. Wersja obalona — POKAZANA PRZED CZYMKOLWIEK INNYM ────────────────────
echo "== bramka na wersji obalonej: korpus, ktory sie KOMPILUJE, ale NIE WYKONUJE =="
binary="$CODE_REPO/build/K23-DEFAULT/src/retractor/xretractor"
[ -x "$binary" ] || { echo "BLAD: brak binarki profilu DEFAULT" >&2; exit 2; }

rm -rf neg && mkdir -p neg
sed 's/Sqrt(/Abs(/' F9_R2_Q8.rql >neg/F9_R2_Q8_abs.rql
cp src_a.txt src_b.txt neg/
(
  cd neg
  mkdir -p temp
  "$binary" F9_R2_Q8_abs.rql -c >compile.out 2>compile.err
) || { echo "BLAD: przypadek negatywny nie kompiluje sie — nie odtwarza stanu iteracji 1" >&2; exit 2; }
echo "  ok  wersja obalona KOMPILUJE sie z rc=0 (tyle widzial pilot iteracji 1)"

(
  cd neg
  run_cell "$binary" F9_R2_Q8_abs.rql . negatyw
  echo "$CELL_RC" >negatyw.rc
)
neg_rc="$(cat neg/negatyw.rc)"
if assert_cell "wersja obalona" "$neg_rc" neg/negatyw.counters 1; then
  echo "BLAD BRAMKI: przypadek, ktory ma byc ODRZUCONY, przeszedl. Bramka nie odroznia" >&2
  echo "             wersji obalonej i jest bezwartosciowa — to szosta odslona tej klasy." >&2
  exit 1
fi
echo "  ok  wersja obalona ODRZUCONA przez te sama asercje: $fail_reason"
echo "      (komunikat silnika: $(head -c 120 neg/negatyw.counters | tr '\n' ' '))"
printf '%s\n' "$fail_reason" >neg/odrzucenie.txt
rm -rf neg/temp neg/*.desc
echo

# ─── 2. Macierz runtime: 4 profile × 6 planow ────────────────────────────────
echo "== przebiegi runtime: $((${#profiles[@]} * ${#plans[@]})) komorek, $SLOTS slotow kazda =="
rm -rf out_rt && mkdir -p out_rt
cells=0
for profile in "${profiles[@]}"; do
  binary="$CODE_REPO/build/K23-$profile/src/retractor/xretractor"
  [ -x "$binary" ] || { echo "BLAD: brak binarki profilu $profile" >&2; exit 2; }
  echo "-- $profile"
  for plan in "${plans[@]}"; do
    want_substrate=0
    [[ "$main_plans" == *" $plan "* ]] && want_substrate=1
    run_cell "$binary" "$plan.rql" out_rt "${profile}_${plan}"
    if ! assert_cell "$plan" "$CELL_RC" "$CELL_COUNTERS" "$want_substrate"; then
      echo "BLAD: ${profile}/${plan}: $fail_reason" >&2
      sed -n '1,5p' "$CELL_COUNTERS" >&2
      exit 3
    fi
    cells=$((cells + 1))
  done
done

# ─── 3. Zrzut diagnostyczny poza macierza (compile-only, DEFAULT) ────────────
# `diag_X_named` nie nalezy do rodziny ani do macierzy; jest dowodem dla §3.4
# predeklaracji (nazwanie posrednich kasuje warstwe R2). Iteracja 1 zrobila ten
# zrzut recznie — tutaj robi go skrypt, zeby out/ bylo odtwarzalne w calosci.
rm -rf temp && mkdir -p temp out
RDB_BENCH_PLAN=1 "$CODE_REPO/build/K23-DEFAULT/src/retractor/xretractor" diag_X_named.rql -c \
  >out/DEFAULT_diag_X_named.plan 2>out/DEFAULT_diag_X_named.probe

rm -rf temp ./*.desc
echo
echo "OK: $cells komorek runtime wykonanych, kazda z licznikami LOGICAL i WORK"
echo "OK: wersja obalona odrzucona przed pomiarem"
