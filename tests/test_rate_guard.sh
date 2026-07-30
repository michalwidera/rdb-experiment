#!/bin/bash
# Regresja kontroli rate'u wprowadzonej w K6b (predeklaracja v2).
#
# Rate przestał być stałą kampanii: jest wybierany per rodzina przez kalibrację.
# Dwie rzeczy muszą być więc pilnowane przez kod, a nie przez uwagę operatora:
#
#   1. warunek unieważniający nr 6 — w obrębie jednego przypadku (a więc i każdej
#      jego komórki) wolno wystąpić dokładnie jednej wartości `scale`/`f_phi_hz`;
#      porównanie profili przy różnych rate'ach nie mierzy optymalizacji;
#   2. reguła wyboru rate'u per rodzina wraz z wykluczaniem komórek, które nie
#      mieszczą się w budżecie nawet na najniższym szczeblu drabiny.
#
# Reguła zliczania (K5h/K5i): kontrola, która nic nie porównała, milczy —
# a milczenie wygląda jak sukces. Dlatego zero sprawdzonych przypadków jest
# błędem i ma tu własną regresję.
set -uo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$TEST_DIR/.." && pwd)"
CAMPAIGN_DIR="$REPO_ROOT/results_20260730_K6c"
ANALYZE="$CAMPAIGN_DIR/analyze.py"
CALIBRATE="$CAMPAIGN_DIR/calibrate.py"

failures=0
checks=0

report() {
  local outcome="$1" name="$2"
  checks=$((checks + 1))
  if [ "$outcome" != "ok" ]; then
    printf 'FAIL: %s\n' "$name" >&2
    failures=$((failures + 1))
  fi
}

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

HEADER="case,profile,rep,scale,f_phi_hz,stream_hz,samples,exit_code,compute_median_ns,compute_p99_ns,compute_max_ns,compute_sum_ns,wake_p999_ns,e2e_p50_ns,e2e_p99_ns,e2e_p999_ns,e2e_max_ns,vmhwm_kb,cpu_ticks,compile_ns,probe_ns,r1,r2,nodes_public,nodes_substrates,tokens_from,tokens_fields,capacity_streams,capacity_sum,capacity_max,mat_bytes,mat_mem_bytes,artifacts_sha256,artifact_count,wall_ms"

# Jeden wiersz runs.csv. Wartosci metryk sa nieistotne dla tej kontroli, wazne
# sa kolumny `case`, `profile`, `scale`, `f_phi_hz` i `stream_hz`.
# Siodmy argument (`stream_hz`) jest opcjonalny i domyslnie rowny `f_phi`;
# ich rozjazd jest przedmiotem kontroli nr 10.
emit_rows() {
  local case="$1" profile="$2" scale="$3" f_phi="$4" median="$5" reps="$6" stream="${7:-$4}" rep
  for ((rep = 1; rep <= reps; rep++)); do
    printf '%s,%s,%d,%s,%s,%s,720,0,%d,%d,%d,%d,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,deadbeef,1,0\n' \
      "$case" "$profile" "$rep" "$scale" "$f_phi" "$stream" \
      "$median" "$((median * 2))" "$((median * 3))" "$((median * 100))"
  done
}

# --- 1. rate identyczny w obrebie komorki: kampania wazna --------------------
GOOD="$WORK/good"
mkdir -p "$GOOD"
{
  echo "$HEADER"
  emit_rows W2_Q32 OFF 6 90 1000000 15
  emit_rows W2_Q32 STRUCT 6 90 1000000 15
  emit_rows W2_Q32 ALGSTRUCT 6 90 1000000 15
  emit_rows W5_Q32 OFF 6 90 900000 15
  emit_rows W5_Q32 STRUCT 6 90 900000 15
  emit_rows W5_Q32 ALGSTRUCT 6 90 900000 15
} > "$GOOD/runs.csv"
if python3 "$ANALYZE" --runs "$GOOD/runs.csv" --output "$GOOD/out" >/dev/null 2>&1; then
  report ok "rate identyczny w obrebie komorki nie unieważnia kampanii"
else
  report bad "rate identyczny w obrebie komorki nie unieważnia kampanii"
fi
if grep -q "sprawdzonych" "$GOOD/out/summary.md" 2>/dev/null ||
   grep -q "przypadków sprawdzonych" "$GOOD/out/summary.md" 2>/dev/null; then
  report ok "raport podaje LICZBE sprawdzonych przypadkow"
else
  report bad "raport podaje LICZBE sprawdzonych przypadkow"
fi
if python3 -c "
import json,sys
d=json.load(open('$GOOD/out/analysis.json'))
sys.exit(0 if d['rate_checked_cases']==2 and not d['rate_problems'] else 1)
"; then
  report ok "analysis.json: 2 przypadki sprawdzone, zero niezgodnosci"
else
  report bad "analysis.json: 2 przypadki sprawdzone, zero niezgodnosci"
fi

# --- 2. rate rozny miedzy profilami tej samej komorki: kampania niewazna -----
BAD="$WORK/bad"
mkdir -p "$BAD"
{
  echo "$HEADER"
  emit_rows W2_Q32 OFF 6 90 1000000 15
  emit_rows W2_Q32 STRUCT 12 180 1000000 15
  emit_rows W2_Q32 ALGSTRUCT 6 90 1000000 15
} > "$BAD/runs.csv"
if python3 "$ANALYZE" --runs "$BAD/runs.csv" --output "$BAD/out" >/dev/null 2>&1; then
  report bad "rozny rate w obrebie komorki uniewaznia kampanie"
else
  report ok "rozny rate w obrebie komorki uniewaznia kampanie"
fi
if grep -q "warunek nr 6" "$BAD/out/summary.md" 2>/dev/null; then
  report ok "werdykt nazywa warunek uniewazniajacy nr 6"
else
  report bad "werdykt nazywa warunek uniewazniajacy nr 6"
fi

# --- 3. rate rozny miedzy powtorzeniami jednej komorki -----------------------
DRIFT="$WORK/drift"
mkdir -p "$DRIFT"
{
  echo "$HEADER"
  emit_rows W2_Q32 OFF 6 90 1000000 15
  emit_rows W2_Q32 STRUCT 6 90 1000000 14
  emit_rows W2_Q32 STRUCT 3 45 1000000 1
  emit_rows W2_Q32 ALGSTRUCT 6 90 1000000 15
} > "$DRIFT/runs.csv"
if python3 "$ANALYZE" --runs "$DRIFT/runs.csv" --output "$DRIFT/out" >/dev/null 2>&1; then
  report bad "jeden przebieg z innym rate'em uniewaznia kampanie"
else
  report ok "jeden przebieg z innym rate'em uniewaznia kampanie"
fi

# --- 4. brak kolumn rate'u: kontrola nie moze milczec ------------------------
LEGACY="$WORK/legacy"
mkdir -p "$LEGACY"
{
  echo "${HEADER/,scale,f_phi_hz,stream_hz/}"
  emit_rows W2_Q32 OFF 6 90 1000000 15 | sed 's/,6,90,90,/,/'
  emit_rows W2_Q32 STRUCT 6 90 1000000 15 | sed 's/,6,90,90,/,/'
  emit_rows W2_Q32 ALGSTRUCT 6 90 1000000 15 | sed 's/,6,90,90,/,/'
} > "$LEGACY/runs.csv"
if python3 "$ANALYZE" --runs "$LEGACY/runs.csv" --output "$LEGACY/out" >/dev/null 2>&1; then
  report bad "runs.csv bez kolumn rate'u nie przechodzi jako zgodny"
else
  report ok "runs.csv bez kolumn rate'u nie przechodzi jako zgodny"
fi

# --- 5. regula wyboru rate'u per rodzina (funkcja czysta) --------------------
# Odwzorowanie sytuacji zmierzonej w K6.0: W2 mieści się dopiero przy s=6,
# W3 już przy s=24, a W4_Q32 nie mieści się nawet przy s=1 i musi wypaść.
if python3 - "$CALIBRATE" <<'PY'
import importlib.util, sys

spec = importlib.util.spec_from_file_location("calibrate", sys.argv[1])
calibrate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calibrate)

laddered = {"W2": ["W2_Q08", "W2_Q32"], "W3": ["W3_d3"], "W4": ["W4_Q08", "W4_Q32"]}
measured = [36, 24, 12, 6, 3, 1]
fits = {}
for scale in measured:
    fits[("W2_Q08", scale)] = scale <= 12
    fits[("W2_Q32", scale)] = scale <= 6
    fits[("W3_d3", scale)] = scale <= 24
    fits[("W4_Q08", scale)] = scale <= 3
    fits[("W4_Q32", scale)] = False
worst = {key: 35_500_000.0 for key in fits}
# Slot ZMIERZONY, per komorka -- nie `1/(15*s)`. Budzet w raporcie wykluczenia
# musi pochodzic z tej mapy, a nie z arytmetyki drabiny (zmiana v3).
slot_ns_at = {(case, scale): 1e9 / (15 * scale) for case, scale in fits}
slot_ns_at[("W4_Q32", 1)] = 1e9 / 22.5  # 1/22,5 s -- glebsze zagniezdzenie

# W3 rozstrzygnięta w trakcie zejścia (pierwszy szczebel, na którym pasuje).
resolved = {"W3": 24}
rates, excluded, excluded_families = calibrate.resolve_rates(
    laddered, resolved, fits, worst, measured, slot_ns_at
)

problems = []
if rates.get("W3") != 24:
    problems.append(f"W3 powinno zostać na s=24, jest {rates.get('W3')}")
if rates.get("W4") != 3:
    problems.append(f"W4 po wykluczeniu W4_Q32 powinno mieć s=3, ma {rates.get('W4')}")
if [entry["case"] for entry in excluded] != ["W4_Q32"]:
    problems.append(f"wykluczona powinna być wyłącznie W4_Q32, jest {[e['case'] for e in excluded]}")
if excluded_families:
    problems.append(f"żadna rodzina nie powinna wypaść w całości, wypadły {excluded_families}")
required = excluded[0]["required_stream_hz"] if excluded else 0
if not 14.0 <= required <= 14.2:
    problems.append(f"wymagana czestotliwosc dla 35,5 ms to ~14,08 Hz, policzono {required}")
# Budzet wykluczenia liczony z SLOTU ZMIERZONEGO: 0,5 * (1/22,5 s) = 22,22 ms.
# Gdyby liczyc go z drabiny (`1/15` s przy s=1), wyszloby 33,33 ms.
budget = excluded[0]["budget_ns"] if excluded else 0
if not 22_000_000 <= budget <= 22_500_000:
    problems.append(f"budzet ma pochodzic ze zmierzonego slotu (22,22 ms), jest {budget}")

# Rodzina, której WSZYSTKIE komórki wypadają, ma wypaść w całości.
rates2, excluded2, families2 = calibrate.resolve_rates(
    {"W4": ["W4_Q32"]}, {}, {("W4_Q32", s): False for s in measured}, worst, measured, slot_ns_at
)
if families2 != ["W4"] or "W4" in rates2:
    problems.append(f"rodzina bez ocalałych komórek powinna wypaść w całości: {families2}, {rates2}")

if problems:
    print("; ".join(problems), file=sys.stderr)
    sys.exit(1)
PY
then
  report ok "regula rate'u per rodzina: wykluczenie W4_Q32 nie blokuje W4_Q08"
else
  report bad "regula rate'u per rodzina: wykluczenie W4_Q32 nie blokuje W4_Q08"
fi

# --- 6. orkiestracja nie przyjmuje juz globalnego --scale --------------------
if grep -q -- '--scale)' "$REPO_ROOT/worker/run_ablation_study.sh"; then
  report bad "run_ablation_study.sh nie przyjmuje globalnego --scale"
else
  report ok "run_ablation_study.sh nie przyjmuje globalnego --scale"
fi
if grep -q 'rate.json' "$REPO_ROOT/worker/run_ablation_study.sh"; then
  report ok "run_ablation_study.sh czyta rate z rate.json"
else
  report bad "run_ablation_study.sh czyta rate z rate.json"
fi

# --- 7. petla przebiegow nie oddaje stdin procesom potomnym -----------------
# Klient xqry uruchamiany w petli `while read ... done < plan.tsv` dziedziczyl
# plan jako stdin, czytal go do EOF i konczyl sie kodem 0 -- badanie padalo na
# "klient xqry nie uruchomil sie". Cichszy skutek byl gorszy: potomek KONSUMOWAL
# plan, wiec petla gubila przebiegi bez ani jednego komunikatu.
if grep -q 'read -r case profile rep stream <&9' "$REPO_ROOT/worker/run_ablation_study.sh" &&
   grep -q 'done 9< "\$PLAN_FILE"' "$REPO_ROOT/worker/run_ablation_study.sh"; then
  report ok "plan przebiegow czytany z deskryptora 9, nie ze stdin"
else
  report bad "plan przebiegow czytany z deskryptora 9, nie ze stdin"
fi
missing_stdin=0
while IFS= read -r line; do
  case "$line" in
    *"</dev/null"*) ;;
    *) missing_stdin=$((missing_stdin + 1)); printf '  bez </dev/null: %s\n' "$line" >&2 ;;
  esac
done < <(grep -n 'xqry -s\|sample_process "\$engine_pid"' "$REPO_ROOT/worker/run_ablation_study.sh" |
         grep -v '^[0-9]*:#')
if [ "$missing_stdin" -eq 0 ]; then
  report ok "procesy potomne w petli maja odciety stdin"
else
  report bad "procesy potomne w petli maja odciety stdin"
fi

# --- 8. commit wynikow przezywa przesuniety wierzcholek brancha --------------
# R4 trzyma JEDEN commit kampanii, wiec push wykonany gdziekolwiek indziej
# w trakcie badania uniewaznia dzierzawe --force-with-lease. Bez odswiezenia
# tuz przed commitem 19 minut poprawnego pomiaru przepadalo na samym push'u.
for script in worker/run_ablation_study.sh worker/run_k6_step.sh; do
  # Odswiezenie musi lezec PRZED dopisaniem do JOURNAL.md: dopisanie do pliku
  # sledzonego zablokowaloby `checkout -B`, a wpis powstaly przed odswiezeniem
  # zostalby nadpisany wersja z origin.
  refresh=$(grep -n 'checkout -B "\$EXPERIMENT_BRANCH" "origin/\$EXPERIMENT_BRANCH" --quiet' \
            "$REPO_ROOT/$script" | tail -1 | cut -d: -f1)
  journal=$(grep -n 'cat >> "\$EXPERIMENT_REPO/JOURNAL.md"' "$REPO_ROOT/$script" | tail -1 | cut -d: -f1)
  if [ -n "$refresh" ] && [ -n "$journal" ] && [ "$refresh" -lt "$journal" ]; then
    report ok "$script: odswiezenie brancha przed wpisem do JOURNAL.md"
  else
    report bad "$script: odswiezenie brancha przed wpisem do JOURNAL.md"
  fi
  # Odrzucony push nie moze byc cichy -- to byl komunikat, ktorego zabraklo.
  if grep -A2 'push --force-with-lease' "$REPO_ROOT/$script" | grep -q 'die "Push wynikow odrzucony'; then
    report ok "$script: odrzucony push konczy badanie bledem, nie cisza"
  else
    report bad "$script: odrzucony push konczy badanie bledem, nie cisza"
  fi
done

# --- 9. znikniecie klienta rozroznia awarie od konca krotkiego przebiegu -----
# Protokol dolaczania klienta trwa ~3 s. `W3_d3` trwa 3,05 s, wiec kontrola
# zywotnosci klienta wypadala 9 ms PO tym, jak silnik skonczyl sam z siebie --
# i normalny koniec byl raportowany jako "klient nie uruchomil sie". Wyscig,
# a wiec awaria losowa, moglaca trafic dowolna rodzine w dowolnym momencie.
if grep -q 'zniknal, choc silnik nadal dziala' "$REPO_ROOT/worker/run_ablation_study.sh"; then
  report ok "brak klienta przy dzialajacym silniku jest awaria"
else
  report bad "brak klienta przy dzialajacym silniku jest awaria"
fi
if grep -q 'klient xqry zakonczyl sie kodem \$client_status' "$REPO_ROOT/worker/run_ablation_study.sh"; then
  report ok "klient zakonczony niezerowo jest awaria takze przy krotkim przebiegu"
else
  report bad "klient zakonczony niezerowo jest awaria takze przy krotkim przebiegu"
fi

# --- 10. rate identyczny, slot rozny: to takze uniewaznia kampanie ----------
# Dziura kontroli v2. `scale` i `f_phi` generatora sa wspolne dla calej rodziny,
# wiec porownanie profili przy roznych slotach przechodzilo przez nia bez sladu.
# Slot jest wlasnoscia komorki: `W3_d1` biegnie 1/360, `W3_d3` 1/810 przy tym
# samym s=24.
SLOTDRIFT="$WORK/slotdrift"
mkdir -p "$SLOTDRIFT"
{
  echo "$HEADER"
  emit_rows W3_d3 OFF 24 360 1000000 15 810
  emit_rows W3_d3 STRUCT 24 360 1000000 15 810
  emit_rows W3_d3 ALGSTRUCT 24 360 1000000 15 360
} > "$SLOTDRIFT/runs.csv"
if python3 "$ANALYZE" --runs "$SLOTDRIFT/runs.csv" --output "$SLOTDRIFT/out" >/dev/null 2>&1; then
  report bad "ten sam scale przy roznym slocie uniewaznia kampanie"
else
  report ok "ten sam scale przy roznym slocie uniewaznia kampanie"
fi

# runs.csv bez kolumny `stream_hz` nie moze przejsc jako zgodny -- to wlasnie
# ksztalt, ktory v2 uznawala za poprawny.
NOSTREAM="$WORK/nostream"
mkdir -p "$NOSTREAM"
{
  echo "${HEADER/,stream_hz/}"
  emit_rows W3_d3 OFF 24 360 1000000 15 | sed 's/,24,360,360,/,24,360,/'
  emit_rows W3_d3 STRUCT 24 360 1000000 15 | sed 's/,24,360,360,/,24,360,/'
  emit_rows W3_d3 ALGSTRUCT 24 360 1000000 15 | sed 's/,24,360,360,/,24,360,/'
} > "$NOSTREAM/runs.csv"
if python3 "$ANALYZE" --runs "$NOSTREAM/runs.csv" --output "$NOSTREAM/out" >/dev/null 2>&1; then
  report bad "runs.csv bez kolumny stream_hz nie przechodzi jako zgodny"
else
  report ok "runs.csv bez kolumny stream_hz nie przechodzi jako zgodny"
fi

printf '%d kontroli, %d bledow\n' "$checks" "$failures"
[ "$failures" -eq 0 ]
