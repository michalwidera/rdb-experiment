#!/bin/bash
# Regresja definicji `slot`, wprowadzonej w K6c (predeklaracja v3).
#
# Predeklaracje v1 i v2 wyliczaly `slot(phi) = 1/(15*s)` arytmetycznie -- czyli
# interwal przeplotu DWOCH strumieni. Dla rodzin, ktorych strumien wyjsciowy jest
# glebszym zagniezdzeniem, to nieprawda: przeplot SUMUJE czestotliwosci, wiec
# kazdy kolejny poziom zageszcza slot. Silnik zapytany o `W3_d3` przy s=24
# odpowiada 1/810, nie 1/360.
#
# Skutek w K6b: `W3_d3` przeszla regule 50 % (p99 1122 us wobec budzetu 1389 us),
# choc wobec prawdziwego slotu 1235 us pracowala na 91 % -- czyli w nasyceniu,
# ktorego ta regula zakazuje. Drugi skutek: przebiegi trwaly ~3,5 s zamiast 8 s.
#
# Ten plik pilnuje trzech rzeczy naraz:
#   1. parsowania odpowiedzi silnika i przeliczenia budzetu slotow;
#   2. tego, ze wartosc nominalna zostala WYLACZNIE do raportowania rozjazdu
#      i nie wraca zadnym bokiem do reguly 50 %;
#   3. kontraktu macierzy i `rate.json`, na ktorych stoi harness workera.
#
# Regula zliczania (K5h/K5i): kontrola, ktora nic nie porownala, milczy --
# a milczenie wyglada jak sukces. Liczba kontroli jest wypisywana na koncu.
set -uo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$TEST_DIR/.." && pwd)"
CAMPAIGN_DIR="$REPO_ROOT/results_20260730_K6c"
CALIBRATE="$CAMPAIGN_DIR/calibrate.py"
SATURATION="$CAMPAIGN_DIR/saturation.py"
ANALYZE="$CAMPAIGN_DIR/analyze.py"
MATRIX="$CAMPAIGN_DIR/matrix.tsv"
WORKER="$REPO_ROOT/worker/run_ablation_study.sh"

export PYTHONDONTWRITEBYTECODE=1

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

for required in "$CALIBRATE" "$SATURATION" "$ANALYZE" "$MATRIX" "$WORKER" \
                "$CAMPAIGN_DIR/stream_interval.py"; do
  [ -f "$required" ] || { printf 'BLAD: brak pliku %s\n' "$required" >&2; exit 1; }
done

# --- 1. parsowanie odpowiedzi silnika i budzet slotow -----------------------
if python3 - "$CAMPAIGN_DIR" <<'PY'
import importlib.util, sys
from fractions import Fraction
from pathlib import Path

spec = importlib.util.spec_from_file_location("stream_interval", Path(sys.argv[1]) / "stream_interval.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

problems = []

# Odpowiedz `xqry -t` dla W3_d3 przy s=24 -- fragment prawdziwego wyjscia.
answer = "stream: w3_out_000\n  delta: 1/810\n  rows: 12\n"
if module.parse_delta(answer) != Fraction(1, 810):
    problems.append(f"delta 1/810 sparsowana jako {module.parse_delta(answer)}")
if module.parse_delta("stream: w3_out_000\n  rows: 12\n") is not None:
    problems.append("brak pola delta ma dawac None, a nie wartosc zastepcza")
if module.parse_delta("delta: 1/0.5\n") is not None:
    problems.append("delta niecalkowita nie moze byc uznana za poprawna")

# Budzet 8 sekund pracy liczony wobec slotu ZMIERZONEGO. Rozjazd jest sednem K6c:
# ten sam szczebel drabiny daje 2880 slotow przy wyliczeniu i 6000 przy pomiarze.
measured = module.slots_for(Fraction(1, 810), 8, 400, 6000)
nominal = module.slots_for(Fraction(1, 360), 8, 400, 6000)
if measured != 6000:
    problems.append(f"slot 1/810 przez 8 s to 6480 slotow -> 6000 po obcieciu, policzono {measured}")
if nominal != 2880:
    problems.append(f"slot 1/360 przez 8 s to 2880 slotow, policzono {nominal}")
if measured == nominal:
    problems.append("budzet slotow nie odroznia slotu zmierzonego od wyliczonego")

# Podloga i sufit sa zamrozone i musza dzialac w obie strony.
if module.slots_for(Fraction(1, 15), 8, 400, 6000) != 400:
    problems.append("podloga 400 slotow nie dziala przy 15 Hz")
if module.slots_for(Fraction(1, 100000), 8, 400, 6000) != 6000:
    problems.append("sufit 6000 slotow nie dziala")

if problems:
    print("; ".join(problems), file=sys.stderr)
    sys.exit(1)
PY
then
  report ok "parse_delta i budzet slotow licza z wartosci zmierzonej"
else
  report bad "parse_delta i budzet slotow licza z wartosci zmierzonej"
fi

# --- 2. slot nominalny nie wraca do reguly 50 % -----------------------------
# `nominal_slot_ns` istnieje wylacznie po to, zeby raport pokazal rozjazd.
# Kazde jego uzycie musi konczyc sie w polu raportowym, nigdy w budzecie.
if bad_use=$(grep -n 'nominal_slot_ns(' "$CALIBRATE" |
             grep -v 'def nominal_slot_ns' |
             grep -v 'slot_nominal_ns\|nominal_ns ='); then
  printf '  uzycie slotu nominalnego poza raportem:\n%s\n' "$bad_use" >&2
  report bad "slot nominalny nie wchodzi do reguly 50 %"
else
  report ok "slot nominalny nie wchodzi do reguly 50 %"
fi
if grep -q 'budget_ns = BUDGET_FRACTION \* duration_ns' "$CALIBRATE" &&
   grep -q 'duration_ns = float(interval) \* 1_000_000_000' "$CALIBRATE"; then
  report ok "budzet 50 % liczony z interwalu zmierzonego"
else
  report bad "budzet 50 % liczony z interwalu zmierzonego"
fi

# --- 3. slot pochodzi z silnika, dla strumienia z macierzy ------------------
if grep -q 'measure_interval(binaries\[PROFILES\[0\]\], probe, stream)' "$CALIBRATE" &&
   grep -q 'stage(workloads / case, code_repo, probe)' "$CALIBRATE" &&
   grep -q 'client_stream = {row\["case"\]: row\["client_stream"\] for row in matrix}' "$CALIBRATE"; then
  report ok "kalibracja pyta silnik o strumien z kolumny client_stream"
else
  report bad "kalibracja pyta silnik o strumien z kolumny client_stream"
fi

# --- 4. kryterium saturacji tez liczy wobec slotu z silnika -----------------
# Trzecie miejsce tego samego bledu: krok saturacji liczyl przekroczenia wobec
# `1/rate` ZRODLA rec205, podczas gdy mierzony `mon_000` biegnie 2x gesciej.
if grep -q 'slot_ns = probe_slot_ns(binary, query, code_repo)' "$SATURATION" &&
   grep -q 'measure_interval' "$SATURATION"; then
  report ok "saturacja mierzy slot strumienia, nie liczy go z rate'u zrodla"
else
  report bad "saturacja mierzy slot strumienia, nie liczy go z rate'u zrodla"
fi
if grep -n '1_000_000_000 / rate' "$SATURATION" | grep -qv 'slot_nominal_ns'; then
  report bad "rate zrodla nie sluzy juz za slot w kryterium przekroczen"
else
  report ok "rate zrodla nie sluzy juz za slot w kryterium przekroczen"
fi

# --- 5. kontrola nasycenia porownuje komorke z jej wlasnym slotem ----------
# W K6b ta kontrola brala budzet RODZINY i przez to milczala o W3_d3.
if grep -q 'cells_json = rate_json.get("cells")' "$ANALYZE" &&
   grep -q 'entry = cells_json.get(case)' "$ANALYZE"; then
  report ok "kontrola nasycenia bierze slot per komorka"
else
  report bad "kontrola nasycenia bierze slot per komorka"
fi
if grep -q 'slot_phi_ns' "$ANALYZE"; then
  report bad "analyze.py nie uzywa juz slotu rodziny"
else
  report ok "analyze.py nie uzywa juz slotu rodziny"
fi

# --- 6. kontrakt macierzy v3 ------------------------------------------------
if python3 - "$MATRIX" <<'PY'
import sys

rows = []
with open(sys.argv[1], encoding="utf-8") as handle:
    header = handle.readline().rstrip("\n").split("\t")
    for line in handle:
        line = line.rstrip("\n")
        if line:
            rows.append(dict(zip(header, line.split("\t"))))

problems = []
for column in ("family", "case", "profiles", "client_stream", "rate", "source_hz"):
    if column not in header:
        problems.append(f"brak kolumny `{column}`")
if problems:
    print("; ".join(problems), file=sys.stderr)
    sys.exit(1)

# Zero porownanych wierszy jest bledem, nie zgodnoscia.
if not rows:
    print("macierz nie ma ani jednego wiersza", file=sys.stderr)
    sys.exit(1)

for row in rows:
    if row["rate"] not in ("calibration", "source"):
        problems.append(f"{row['case']}: nieznana wartosc rate `{row['rate']}`")
    if not row["client_stream"]:
        problems.append(f"{row['case']}: pusty client_stream -- nie ma czego zapytac silnika")
    if row["rate"] == "source":
        try:
            float(row["source_hz"])
        except ValueError:
            problems.append(f"{row['case']}: rodzina ze zrodla musi podac source_hz")
    elif row["source_hz"] != "-":
        problems.append(f"{row['case']}: rodzina z drabiny nie ma rate'u zrodla, ma byc `-`")
    # Rate zrodla nie moze udawac czestotliwosci strumienia mierzonego -- to byl
    # blad v2, gdzie `fixed:360` opisywalo naraz rec205 (1/360) i mon_000 (1/720).
    if "fixed:" in row["rate"]:
        problems.append(f"{row['case']}: `fixed:N` mylilo rate zrodla ze slotem strumienia")

if problems:
    print("; ".join(problems), file=sys.stderr)
    sys.exit(1)
print(f"sprawdzono {len(rows)} wierszy macierzy")
PY
then
  report ok "macierz v3 rozdziela rate zrodla od strumienia mierzonego"
else
  report bad "macierz v3 rozdziela rate zrodla od strumienia mierzonego"
fi

# --- 7. harness workera czyta budzet per komorka, nie per rodzine -----------
if grep -q 'if int(data.get("version", 0)) < 3:' "$WORKER"; then
  report ok "worker odrzuca rate.json starszy niz v3"
else
  report bad "worker odrzuca rate.json starszy niz v3"
fi
if grep -q 'CELL_SLOTS\[' "$WORKER" && grep -q 'SAMPLES="\${CELL_SLOTS\[\$case\]:-}"' "$WORKER"; then
  report ok "budzet slotow brany z sekcji cells, per komorka"
else
  report bad "budzet slotow brany z sekcji cells, per komorka"
fi
if grep -q "entry\['slots'\]" "$WORKER"; then
  report bad "worker nie bierze juz budzetu slotow z poziomu rodziny"
else
  report ok "worker nie bierze juz budzetu slotow z poziomu rodziny"
fi
if grep -q -- '--stream-hz "\$STREAM_HZ"' "$WORKER" &&
   grep -q 'stream_hz' "$CAMPAIGN_DIR/summarize_run.py"; then
  report ok "czestotliwosc strumienia trafia do runs.csv przy kazdym przebiegu"
else
  report bad "czestotliwosc strumienia trafia do runs.csv przy kazdym przebiegu"
fi

# --- 8. predeklaracja v3 nazywa blad v2 wprost ------------------------------
# Tak samo, jak v2 nazwala blad v1. Predeklaracja, ktora milczy o powodzie
# swojego istnienia, nie jest predeklaracja, tylko kolejnym podejsciem.
README="$CAMPAIGN_DIR/README.md"
if grep -q 'Predeklaracja v3' "$README" &&
   grep -q '1/810' "$README" &&
   grep -q 'e1e5181' "$README" &&
   grep -q 'e1c13bb' "$README"; then
  report ok "README v3 nazywa blad v2, rozjazd slotu i oba przypiecia silnika"
else
  report bad "README v3 nazywa blad v2, rozjazd slotu i oba przypiecia silnika"
fi

# --- 9. klient jest czescia aparatury pomiarowej ----------------------------
# Harness sprawdzal wylacznie `command -v xqry`. Od K6c kampania czyta przez
# klienta interwal strumienia, wiec staly klient z innego commita przeszedlby te
# kontrole i po cichu wrocilby z defektem, dla ktorego naprawy zatrzymano K6b.
for script in worker/run_ablation_study.sh worker/run_k6_step.sh; do
  if grep -q 'XQRY_COMMIT=' "$REPO_ROOT/$script" &&
     grep -q 'xqry pochodzi z commita' "$REPO_ROOT/$script"; then
    report ok "$script: sprawdza commit klienta xqry, nie tylko obecnosc"
  else
    report bad "$script: sprawdza commit klienta xqry, nie tylko obecnosc"
  fi
done
# Sam parser tez ma regresje: `--help` wypisuje `Branch: <branch>:<short-sha>`.
if python3 - <<'PY'
import re, sys

# Ten sam wzorzec, ktory harness uruchamia przez sed.
pattern = re.compile(r".*Branch: [^:]*:([0-9a-f]{7,}).*")
sample = "Branch: master:e1e5181, Code compiler: GNU Ver. 15.2.0, Build time: 2607310710, Type: Release"
match = pattern.match(sample)
problems = []
if not match or match.group(1) != "e1e5181":
    problems.append(f"nie wyluskano skroconego commita z `{sample}`")
else:
    short = match.group(1)
    if not "e1e5181141f96965da4a092f7e7191f8cb0b2748".startswith(short):
        problems.append("klient z przypietego commita zostal odrzucony")
    if "bb3a5216b952432818b23a26365001fe4f7627f5".startswith(short):
        problems.append("klient z obcego commita zostal przyjety")
if pattern.match("Branch: Deatached:none, Type: Release"):
    problems.append("`none` (build spoza repozytorium git) nie moze udawac commita")
if problems:
    print("; ".join(problems), file=sys.stderr)
    sys.exit(1)
PY
then
  report ok "wzorzec commita klienta przyjmuje przypiety i odrzuca obcy"
else
  report bad "wzorzec commita klienta przyjmuje przypiety i odrzuca obcy"
fi

# --- 10. proba na sucho calej kalibracji ------------------------------------
# Kalibracja K6b wywracala sie NIE na pomiarze, tylko na skladaniu raportu --
# po tym, jak worker przemierzyl juz caly material. Tu przechodzimy te sama
# sciezke z podstawionym pomiarem: rate.json i calibration.md musza powstac,
# a harness workera musi umiec je odczytac.
if python3 - "$CAMPAIGN_DIR" "$WORKER" <<'PY'
import contextlib, importlib.util, io, json, subprocess, sys, tempfile
from fractions import Fraction
from pathlib import Path

campaign = Path(sys.argv[1])
worker = Path(sys.argv[2])

spec = importlib.util.spec_from_file_location("calibrate", campaign / "calibrate.py")
calibrate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calibrate)

# Slot per komorka, taki jak odpowiada silnik: W3_d3 jest 2,25x gestsza od
# W3_d1 przy tym samym szczeblu, a mon_000 dwa razy gestszy od zrodla.
def slot_of(case: str, scale: int) -> Fraction:
    if case == "W3_d3":
        return Fraction(1, 45 * scale)
    if case.startswith("W8"):
        return Fraction(1, 720)
    return Fraction(1, 15 * scale)

def fake_measure_cell(binaries, workloads, code_repo, case, stream):
    interval = slot_of(case, fake_measure_cell.scale)
    slots = calibrate.slots_for_interval(interval, calibrate.RUN_SECONDS, calibrate.SLOTS_MIN, calibrate.SLOTS_MAX)
    # W4_Q32 ma koszt STALY co-slot -- nie zmiesci sie na zadnym szczeblu.
    worst = 35_500_000.0 if case == "W4_Q32" else 0.2 * float(interval) * 1e9
    return interval, slots, worst, {"tokens_from": 7}

def fake_generate(here, scale):
    fake_measure_cell.scale = scale
    return Path(tempfile.mkdtemp(prefix="k6c-dry-"))

calibrate.measure_cell = fake_measure_cell
calibrate.generate_workloads = fake_generate

root = Path(tempfile.mkdtemp(prefix="k6c-dryrun-"))
code_repo = root / "code"
for profile in calibrate.PROFILES:
    binary = code_repo / f"build/K6-{profile}/src/retractor/xretractor"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text("")
output = root / "results"

sys.argv = ["calibrate.py", "--code-repo", str(code_repo), "--output", str(output)]
# Wlasne wypisy kalibracji nie sa wynikiem tej kontroli -- interesuje nas plik.
with contextlib.redirect_stdout(io.StringIO()):
    status = calibrate.main()
if status != 0:
    print("kalibracja na sucho zwrocila blad", file=sys.stderr)
    sys.exit(1)

data = json.loads((output / "rate.json").read_text(encoding="utf-8"))
problems = []
if data["version"] != 3:
    problems.append(f"rate.json ma wersje {data['version']}, oczekiwano 3")
if not (output / "calibration.md").is_file():
    problems.append("calibration.md nie powstal")

cells = data["cells"]
if not cells:
    problems.append("rate.json nie ma ani jednej komorki")
for name, cell in cells.items():
    for field in ("slot_ns", "slot_nominal_ns", "stream_hz", "slots", "scale", "family"):
        if field not in cell:
            problems.append(f"{name}: brak pola `{field}`")
    if not calibrate.SLOTS_MIN <= cell["slots"] <= calibrate.SLOTS_MAX:
        problems.append(f"{name}: slots={cell['slots']} poza zamrozonym zakresem")

# Sedno v3: komorki jednej rodziny maja rozny budzet, bo maja rozny slot.
if "W3_d1" in cells and "W3_d3" in cells:
    if cells["W3_d1"]["scale"] != cells["W3_d3"]["scale"]:
        problems.append("komorki jednej rodziny musza dzielic szczebel drabiny")
    if cells["W3_d1"]["slots"] == cells["W3_d3"]["slots"]:
        problems.append("W3_d1 i W3_d3 maja rozny slot, wiec musza miec rozny budzet slotow")
else:
    problems.append("brak komorek W3 -- nie ma czego porownac")

# W4_Q32 ma koszt staly co-slot: musi wypasc, a jej powod byc podany liczbowo.
excluded = [entry["case"] for entry in data["excluded_cases"]]
if excluded != ["W4_Q32"]:
    problems.append(f"wykluczona powinna byc wylacznie W4_Q32, jest {excluded}")
if "W4_Q32" in cells:
    problems.append("komorka wykluczona nie moze trafic do planu Tier B")
if data["excluded_cases"] and "required_stream_hz" not in data["excluded_cases"][0]:
    problems.append("wykluczenie musi podac wymagana czestotliwosc strumienia")

# Rodzina ze zrodla: rate zostaje przy zrodle, ale slot pochodzi z pomiaru.
w8 = data["families"].get("W8")
if w8 is None or w8["source"] != "deklaracja zrodla":
    problems.append("W8 musi zachowac rate ze zrodla")
elif abs(cells["W8_Q01"]["stream_hz"] - 720) > 1:
    problems.append(f"slot W8 ma pochodzic z pomiaru (720 Hz), jest {cells['W8_Q01']['stream_hz']}")

# Harness workera musi ten plik odczytac -- inaczej kampania stanie na starcie.
reader = worker.read_text(encoding="utf-8").split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
for family in sorted({cell["family"] for cell in cells.values()}):
    done = subprocess.run(
        [sys.executable, "-c", reader, str(output / "rate.json"), family],
        capture_output=True, text=True,
    )
    if done.returncode != 0:
        problems.append(f"worker nie odczytal rodziny {family}: {done.stderr.strip()}")
        continue
    emitted = dict(
        line.split("=", 1) for line in done.stdout.splitlines() if line.startswith("CELL_SLOTS[")
    )
    expected = sum(1 for cell in cells.values() if cell["family"] == family)
    if len(emitted) != expected:
        problems.append(f"{family}: worker dostal {len(emitted)} budzetow zamiast {expected}")

if problems:
    print("; ".join(problems), file=sys.stderr)
    sys.exit(1)
print(f"proba na sucho: {len(cells)} komorek, {len(data['excluded_cases'])} wykluczonych")
PY
then
  report ok "kalibracja na sucho sklada rate.json v3, ktory worker umie odczytac"
else
  report bad "kalibracja na sucho sklada rate.json v3, ktory worker umie odczytac"
fi

# --- 10b. wykluczenie decyzyjne (W8_Q32): union do skipu, osobne etykiety ----
# decision_excluded_cases ma INNA semantyke niz excluded_cases: to decyzja
# czlowieka o przeciazeniu rodziny ze zrodla (W8_Q32, duty 243 % p99 @720 Hz),
# gdzie "budzet przy s=1" ani required_stream_hz nie maja sensu. Worker musi je
# ZSUMOWAC do skipu w planie, ale RAPORTOWAC osobno, zeby results.md/JOURNAL nie
# opisaly decyzji jako wykluczenia kalibracyjnego, a analyze.py nie wlozyl jej do
# tabeli kalibracyjnej.
if python3 - "$CAMPAIGN_DIR" "$WORKER" <<'PY'
import json, subprocess, sys
from pathlib import Path

campaign, worker = Path(sys.argv[1]), Path(sys.argv[2])
problems = []

rate = json.loads((campaign / "results/rate.json").read_text(encoding="utf-8"))
decision = [e["case"] for e in rate.get("decision_excluded_cases", [])]
calib = [e["case"] for e in rate.get("excluded_cases", [])]
if "W8_Q32" not in decision:
    problems.append(f"W8_Q32 musi byc w decision_excluded_cases, jest {decision}")
if "W8_Q32" in calib:
    problems.append("W8_Q32 nie moze trafic do excluded_cases -- to nie wykluczenie kalibracyjne")
for entry in rate.get("decision_excluded_cases", []):
    if not entry.get("reason"):
        problems.append(f"wpis decyzyjny {entry.get('case')} musi podac reason")

# Reader workera odczytany z pliku jak w kontroli 10 -- musi dac union w EXCLUDED
# i rozdzial na EXCLUDED_CALIB / EXCLUDED_DECISION.
reader = worker.read_text(encoding="utf-8").split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
done = subprocess.run(
    [sys.executable, "-c", reader, str(campaign / "results/rate.json"), "W8"],
    capture_output=True, text=True,
)
if done.returncode != 0:
    problems.append(f"reader nie odczytal W8: {done.stderr.strip()}")
else:
    emitted = {}
    for line in done.stdout.splitlines():
        if line[:1].isalpha() and "=" in line and line.split("=", 1)[0].isupper():
            key, val = line.split("=", 1)
            emitted[key] = val.strip("'")
    if "W8_Q32" not in emitted.get("EXCLUDED", "").split(","):
        problems.append(f"EXCLUDED musi zawierac W8_Q32 (skip), jest {emitted.get('EXCLUDED')!r}")
    if emitted.get("EXCLUDED_DECISION") != "W8_Q32":
        problems.append(f"EXCLUDED_DECISION musi byc 'W8_Q32', jest {emitted.get('EXCLUDED_DECISION')!r}")
    if "W8_Q32" in emitted.get("EXCLUDED_CALIB", "").split(","):
        problems.append(f"EXCLUDED_CALIB nie moze zawierac W8_Q32, jest {emitted.get('EXCLUDED_CALIB')!r}")

if problems:
    print("; ".join(problems), file=sys.stderr)
    sys.exit(1)
print("wykluczenie decyzyjne: union do skipu, osobne etykiety, kontrakt rate.json OK")
PY
then
  report ok "W8_Q32 wykluczona decyzja: skip przez union, raport pod osobna etykieta"
else
  report bad "W8_Q32 wykluczona decyzja: skip przez union, raport pod osobna etykieta"
fi

# --- 11. katalog przebiegu podawany do pytania o slot -----------------------
# Kontrola 10 podstawia CALE `measure_cell`, wiec jego wlasne przygotowanie
# katalogu nigdy sie nie wykonuje -- i dlatego przepuscila defekt, na ktorym
# K6c.0 stanela po 8 sekundach: do `measure_interval` szedl SUROWY katalog
# z `generate.py`. `generate.py` zostawia same wejscia, wiec silnik konczyl sie
# `FATAL: storage: path 'temp/' is not a directory` (W2), a W8 -- w kalibracji
# nowa w v3 -- pracowalaby bez plikow ECG z `external_data.txt`.
# Tutaj `measure_cell` biegnie NAPRAWDE; podstawiony jest wylacznie silnik.
if python3 - "$CAMPAIGN_DIR" <<'PY'
import importlib.util, shutil, sys, tempfile
from fractions import Fraction
from pathlib import Path

campaign = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("calibrate", campaign / "calibrate.py")
calibrate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calibrate)

root = Path(tempfile.mkdtemp(prefix="k6c-stage-"))
code_repo = root / "code"
ecg = code_repo / "examples/ecg/rec205"
ecg.mkdir(parents=True)
for name in ("rec205", "bp_coef.txt", "d_coef.txt"):
    (ecg / name).write_text(f"{name}\n", encoding="utf-8")

# Katalogi komorek dokladnie takie, jakie zostawia `generate.py`: same wejscia,
# bez `temp/`. W8 nie ma ZADNEGO pliku danych -- tylko manifest.
workloads = root / "workloads"
(workloads / "W2_Q01").mkdir(parents=True)
(workloads / "W2_Q01/query.rql").write_text("STORAGE 'temp'\n", encoding="utf-8")
(workloads / "W2_Q01/a.txt").write_text("1\n", encoding="utf-8")
(workloads / "W2_Q01/b.txt").write_text("2\n", encoding="utf-8")
(workloads / "W8_Q01").mkdir(parents=True)
(workloads / "W8_Q01/query.rql").write_text("STORAGE 'temp'\n", encoding="utf-8")
(workloads / "W8_Q01/external_data.txt").write_text(
    "examples/ecg/rec205/rec205\nexamples/ecg/rec205/bp_coef.txt\nexamples/ecg/rec205/d_coef.txt\n", encoding="utf-8"
)

seen = {}

def fake_measure_interval(engine, work_dir, stream):
    # Katalog musi byc zdatny do uruchomienia silnika W MOMENCIE pytania --
    # kopiujemy jego zawartosc, bo `measure_cell` sprzata po sobie.
    seen[stream] = sorted(p.name for p in Path(work_dir).iterdir())
    seen[stream + "/temp"] = Path(work_dir, "temp").is_dir()
    return Fraction(1, 360)

run_once_args = []

def fake_run_once(binary, case_dir, repo, slots):
    run_once_args.append(repo)
    return 1000, {"tokens_from": 7}

calibrate.measure_interval = fake_measure_interval
calibrate.run_once = fake_run_once

binaries = {profile: root / f"xretractor-{profile}" for profile in calibrate.PROFILES}
for case, stream in (("W2_Q01", "w2_out_000"), ("W8_Q01", "mon_000")):
    calibrate.measure_cell(binaries, workloads, code_repo, case, stream)

problems = []
compared = 0

# W2: `temp/` plus dane, bez samego manifestu.
compared += 1
if not seen.get("w2_out_000/temp"):
    problems.append("W2: katalog podany do pytania o slot nie ma temp/")
for name in ("a.txt", "b.txt", "query.rql"):
    compared += 1
    if name not in seen.get("w2_out_000", []):
        problems.append(f"W2: brak {name} w katalogu przebiegu")

# W8: `temp/` plus pliki ROZWIAZANE z manifestu, a nie sam manifest.
compared += 1
if not seen.get("mon_000/temp"):
    problems.append("W8: katalog podany do pytania o slot nie ma temp/")
for name in ("rec205", "bp_coef.txt", "d_coef.txt", "query.rql"):
    compared += 1
    if name not in seen.get("mon_000", []):
        problems.append(f"W8: brak {name} w katalogu przebiegu -- pipeline bez wejscia ECG")
compared += 1
if "external_data.txt" in seen.get("mon_000", []):
    problems.append("W8: manifest skopiowany do katalogu przebiegu zamiast rozwiazany")

# Plumbing: `run_once` te same pliki stawia sam, wiec musi dostac code_repo.
expected_runs = 2 * len(calibrate.PROFILES) * calibrate.REPS
compared += 1
if len(run_once_args) != expected_runs or any(r != code_repo for r in run_once_args):
    problems.append(f"run_once nie dostal code_repo we wszystkich {expected_runs} przebiegach")

shutil.rmtree(root, ignore_errors=True)
if compared == 0:
    print("kontrola nic nie porownala", file=sys.stderr)
    sys.exit(1)
if problems:
    print("; ".join(problems), file=sys.stderr)
    sys.exit(1)
print(f"katalog przebiegu: {compared} porownan")
PY
then
  report ok "measure_cell podaje do pytania o slot GOTOWY katalog (temp/ + dane + manifest)"
else
  report bad "measure_cell podaje do pytania o slot GOTOWY katalog (temp/ + dane + manifest)"
fi

printf '%d kontroli, %d bledow\n' "$checks" "$failures"
[ "$failures" -eq 0 ]
