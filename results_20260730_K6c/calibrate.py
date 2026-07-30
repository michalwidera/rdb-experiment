#!/usr/bin/env python3
"""K6c.0 — kalibracja rate'u pomiarowego, **per rodzina**. Uruchamiane na workerze.

Reguła jest zamrożona w README v3 i przepisana tu dosłownie:

    rate(rodzina) = największe `s` z drabiny {36, 24, 12, 6, 3, 1}, przy którym
                    KAŻDA niewykluczona komórka tej rodziny spełnia
                    p99(compute_ns) <= 0,5 * slot(komórki, wg silnika)
                    w najgorszym zmierzonym profilu

    komórka, która nie spełnia tego warunku nawet przy s = 1, jest WYKLUCZONA
    z Tier B, nie ogranicza rate'u swojej rodziny i jest raportowana wraz
    z p99, budżetem i wymaganą częstotliwością strumienia

Dlaczego per rodzina, a nie globalnie: kalibracja v1 (`results_20260730_K6`)
odrzuciła całą drabinę, bo jedna komórka — `W4_Q32` — ma koszt STAŁY co-slot
(okno `@(1,30)` liczy 30 próbek w każdym slocie, niezależnie od jego długości).
Rate globalny wiązał ze sobą rodziny, między którymi nie zachodzi żadne
porównanie.

Dlaczego nie per komórka: przy różnych rate'ach dla `Q08` i `Q32` porównanie
skalowania w `Q` wewnątrz rodziny byłoby skażone rate'em.

ZMIANA v3 wobec v2: `slot(phi)` NIE jest już wyliczany arytmetycznie jako
`1/(15·s)`. Jest odczytywany z silnika dla **strumienia, który kampania faktycznie
mierzy** (kolumna `client_stream` w macierzy). Powód jest ustaleniem K6b: dla
rodzin z zagnieżdżonym przepłotem wyliczenie było fałszywe — `W3_d3` miała slot
1/810, nie 1/360, a `W8` 1/720, nie 1/360. Reguła 50 % przepuszczała przez to
komórkę pracującą na 91 % swojego slotu. Szczegóły w `stream_interval.py`.

Konsekwencja, której v2 nie mogła zobaczyć: **slot jest własnością komórki, nie
rodziny.** `W3_d1` i `W3_d3` należą do jednej rodziny i mają różne sloty (1/360
i 1/810 przy tym samym `s = 24`). Dlatego budżet przebiegu — zamrożone
`clamp(round(8 s / slot), 400, 6000)` — liczymy per komórka. Wzór jest ten sam,
zmienia się tylko to, że wstawiamy do niego prawdziwą wartość. Rate rodziny
(szczebel `s`) pozostaje wspólny, bo to on decyduje o porównywalności `Q`
wewnątrz rodziny.

Rodziny „ze źródła" (`rate = source` w macierzy, dziś tylko W8) nie schodzą po
drabinie — ich generacja jest zamrożona przez deklarację źródła (`rec205`,
1/360). Kolumna `source_hz` opisuje **źródło danych**, a nie strumień mierzony:
`mon_000` powstaje z przeplotu i biegnie 1/720. To były w v2 dwie różne
wielkości pod jedną nazwą. Slot takiej rodziny mierzymy z silnika tak samo jak
każdy inny; przynależność do budżetu 50 % jest dla niej RAPORTOWANA, ale nie
zmienia jej rate'u — ten należy do źródła, nie do nas.

**Wyniki kalibracji nie są wynikami kampanii.** Służą wyłącznie ustaleniu
rate'ów i zostają w `results/calibration.md` oraz `results/rate.json`.

Przebieg kalibracyjny ma włączone te same trzy instrumenty co przebieg Tier B
(`RDB_BENCH_CSV`, `RDB_BENCH_PLAN`, `RDB_BENCH_MATERIALIZE`), z dwóch powodów.
Po pierwsze, kalibracja ma mierzyć ten sam przebieg, który potem będzie mierzony
— v1 kalibrowała bez dwóch z nich. Po drugie, liczniki planu i materializacji
z tych przebiegów są wejściem modelu kosztu slotu (K20 etap 1); bez nich komórka
wykluczona z Tier B nie miałaby żadnego wektora cech, a to właśnie ona łamie
model liczący same tokeny.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_counters import stage  # noqa: E402
from stream_interval import measure_interval  # noqa: E402
from stream_interval import slots_for as slots_for_interval  # noqa: E402
from summarize_run import read_log  # noqa: E402

LADDER = [36, 24, 12, 6, 3, 1]
PROFILES = ["OFF", "STRUCT"]
REPS = 3
BUDGET_FRACTION = 0.5
WARMUP_FRACTION = 0.05
XR_CPU = "3"

# Budżet przebiegu, zamrożony w README v2: 8 sekund pracy, ale nie mniej niż 400
# i nie więcej niż 6000 slotów. Podłoga zeszła z 1500 na 400, bo przy 15 Hz
# 1500 slotów to 100 s na przebieg.
RUN_SECONDS = 8
SLOTS_MIN = 400
SLOTS_MAX = 6000

# Mnożnik generatora dla rodzin „ze źródła". Generator go dla nich ignoruje
# (`generate.py`: W8 nie podlega skalowaniu), ale musi dostać jakąś wartość
# z drabiny — zamrażamy ją tutaj, żeby kalibracja i przebieg Tier B generowały
# te same pliki. Worker czyta tę samą liczbę z `rate.json`, nie zgaduje jej.
SOURCE_FAMILY_SCALE = 6


def nominal_slot_ns(scale: int) -> float:
    """Slot wyliczony jak w v1/v2 — zachowany WYŁĄCZNIE po to, żeby raport mógł
    pokazać rozjazd wobec wartości z silnika. Nie wolno go użyć do reguły 50 %."""
    return float(Fraction(1, 15 * scale) * 1_000_000_000)


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


def read_matrix(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as handle:
        header = handle.readline().rstrip("\n").split("\t")
        for line in handle:
            line = line.rstrip("\n")
            if not line:
                continue
            rows.append(dict(zip(header, line.split("\t"))))
    if not rows:
        raise SystemExit("macierz Tier B jest pusta")
    return rows


def resolve_rates(
    laddered: dict[str, list[str]],
    resolved: dict[str, int],
    fits_at: dict[tuple[str, int], bool],
    worst_at: dict[tuple[str, int], float],
    measured_scales: list[int],
    slot_ns_at: dict[tuple[str, int], float],
) -> tuple[dict[str, int], list[dict[str, object]], list[str]]:
    """Domknięcie reguły dla rodzin, które nie zmieściły się na żadnym szczeblu.

    `resolved` to rodziny rozstrzygnięte w trakcie zejścia po drabinie (pierwszy,
    czyli największy `s`, przy którym zmieściły się wszystkie ich komórki).
    Dla pozostałych: komórki niemieszczące się przy najniższym zmierzonym
    szczeblu są **wykluczane**, po czym rate wyznaczamy na tym, co zostało.

    Funkcja jest czysta — nic nie mierzy — żeby regresja mogła sprawdzić samą
    regułę bez uruchamiania silnika.
    """
    rates = dict(resolved)
    excluded_cases: list[dict[str, object]] = []
    excluded_families: list[str] = []
    bottom = measured_scales[-1] if measured_scales else LADDER[-1]
    for family in sorted(set(laddered) - set(resolved)):
        survivors = [case for case in laddered[family] if fits_at.get((case, bottom), False)]
        for case in laddered[family]:
            if case in survivors:
                continue
            p99 = worst_at[(case, bottom)]
            excluded_cases.append(
                {
                    "family": family,
                    "case": case,
                    "p99_ns": p99,
                    "budget_ns": BUDGET_FRACTION * slot_ns_at[(case, bottom)],
                    "slot_ns": slot_ns_at[(case, bottom)],
                    "stream_hz": 1_000_000_000 / slot_ns_at[(case, bottom)],
                    "scale": bottom,
                    # Wymagana czestotliwosc strumienia MIERZONEGO, nie wyliczonego
                    # przepłotu dwóch źródeł — to dwie różne wielkości (K6b).
                    "required_stream_hz": BUDGET_FRACTION * 1_000_000_000 / p99,
                }
            )
        if not survivors:
            excluded_families.append(family)
            continue
        candidates = [s for s in measured_scales if all(fits_at.get((c, s), False) for c in survivors)]
        if not candidates:
            raise SystemExit(f"{family}: komórki przeszły przy s={bottom}, a nie ma szczebla — sprzeczność danych")
        rates[family] = max(candidates)
    return rates, excluded_cases, excluded_families


def run_once(binary: Path, case_dir: Path, code_repo: Path, slots: int) -> tuple[int, dict[str, int]]:
    """Jeden przebieg kalibracyjny.

    Zwraca `p99(compute_ns)` po odrzuceniu transjentu oraz liczniki planu
    i materializacji z tego samego przebiegu.
    """
    with tempfile.TemporaryDirectory(prefix="rdb-k6b-cal-", dir="/dev/shm") as root:
        work = Path(root) / "case"
        stage(case_dir, code_repo, work)
        (work / "study.toml").write_text("[scheduling]\nrt_priority = 50\n", encoding="utf-8")
        probe = work / "e1_probe.csv"
        environment = os.environ.copy()
        environment["RDB_BENCH_CSV"] = str(probe)
        environment["RDB_BENCH_PLAN"] = "1"
        environment["RDB_BENCH_MATERIALIZE"] = "1"
        completed = subprocess.run(
            ["taskset", "-c", XR_CPU, str(binary), "query.rql", "-r", "-k", "-m", str(slots), "-t", "-g", "study.toml"],
            cwd=work,
            env=environment,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=slots // 10 + 300,
            check=False,
        )
        if completed.returncode != 0:
            raise SystemExit(f"kalibracja: xretractor zakończył się kodem {completed.returncode}\n{completed.stderr[-800:]}")
        engine_log = work / "xretractor.log"
        engine_log.write_text(completed.stdout + completed.stderr, encoding="utf-8")
        counters = read_log(engine_log)
        compute: list[int] = []
        with probe.open(encoding="utf-8") as handle:
            handle.readline()
            for line in handle:
                parts = line.strip().split(",")
                if len(parts) == 4:
                    compute.append(int(parts[1]))
        if not compute:
            raise SystemExit("kalibracja: sonda nie zawiera żadnego slotu")
        compute = compute[int(len(compute) * WARMUP_FRACTION) :]
        if not compute:
            raise SystemExit("kalibracja: po odrzuceniu transjentu nie został żaden slot")
        return percentile(compute, 0.99), counters


def generate_workloads(here: Path, scale: int) -> Path:
    workloads = Path("/dev/shm/k6c-calibration") / f"scale{scale}"
    if workloads.exists():
        shutil.rmtree(workloads)
    subprocess.run(
        [sys.executable, str(here / "generate.py"), "--output", str(workloads), "--scale", str(scale)],
        check=True,
        capture_output=True,
    )
    return workloads


def measure_cell(
    binaries: dict[str, Path], workloads: Path, code_repo: Path, case: str, stream: str
) -> tuple[Fraction, int, float, dict[str, int]]:
    """Pomiar jednej komórki: slot z silnika, budżet slotów, najgorszy `p99`.

    Slot pochodzi z SILNIKA, dla strumienia, który kampania faktycznie mierzy.
    Wyliczenie `1/(15·s)` opisywało przeplot dwóch źródeł i dla rodzin
    z zagnieżdżonym przeplotem było fałszywe (`W3_d3`: 1/810, nie 1/360).
    Reguły 50 % i budżetu slotów stosujemy do wartości zmierzonej.

    Cechy dla modelu kosztu slotu zbieramy z profilu OFF: jest bez przepisywania,
    więc liczniki opisują plan wejściowy, a nie jego zoptymalizowaną postać.
    """
    # `generate.py` zostawia w katalogu komórki same wejścia, a silnik potrzebuje
    # GOTOWEGO katalogu przebiegu: `temp/`, bo nagłówek RQL to `STORAGE 'temp'`,
    # oraz plików wskazanych przez `external_data.txt`. Pytanie o slot dostawało
    # katalog surowy — W2 kończyło się `FATAL: storage: path 'temp/' is not
    # a directory`, a W8 (w kalibracji nowa w v3) pracowałaby bez wejścia ECG.
    # Ten sam `stage()`, którego używa `run_once` i `check_counters.py`.
    with tempfile.TemporaryDirectory(prefix="rdb-k6c-slot-", dir="/dev/shm") as root:
        probe = Path(root) / "case"
        stage(workloads / case, code_repo, probe)
        interval = measure_interval(binaries[PROFILES[0]], probe, stream)
    slots = slots_for_interval(interval, RUN_SECONDS, SLOTS_MIN, SLOTS_MAX)
    worst = 0.0
    features: dict[str, int] = {}
    for profile in PROFILES:
        for _ in range(REPS):
            p99, counters = run_once(binaries[profile], workloads / case, code_repo, slots)
            worst = max(worst, float(p99))
            if profile == PROFILES[0] and not features:
                features = counters
    return interval, slots, worst, features


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--build-prefix", default="K6")
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    code_repo = args.code_repo.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    matrix = read_matrix(here / "matrix.tsv")
    for column in ("rate", "client_stream", "source_hz"):
        if column not in matrix[0]:
            raise SystemExit(f"macierz nie ma kolumny `{column}`; K6c wymaga macierzy v3")

    # Strumień, który kampania faktycznie mierzy. To o JEGO slot pytamy silnik —
    # nie o wyliczony przeplot dwóch źródeł i nie o rate źródła danych.
    client_stream = {row["case"]: row["client_stream"] for row in matrix}

    # Rodziny podlegające drabinie i rodziny o rate'cie z deklaracji źródła (W8).
    laddered: dict[str, list[str]] = {}
    sourced: dict[str, list[str]] = {}
    source_hz: dict[str, float] = {}
    for row in matrix:
        if row["rate"] == "calibration":
            laddered.setdefault(row["family"], []).append(row["case"])
        elif row["rate"] == "source":
            sourced.setdefault(row["family"], []).append(row["case"])
            declared = float(row["source_hz"])
            if source_hz.setdefault(row["family"], declared) != declared:
                raise SystemExit(f"{row['family']}: niejednolita deklaracja `source_hz` w macierzy")
        else:
            raise SystemExit(f"nieznana wartość kolumny `rate`: {row['rate']}")
    if not laddered:
        raise SystemExit("żadna rodzina Tier B nie podlega drabinie — nie ma czego kalibrować")

    binaries: dict[str, Path] = {}
    for profile in PROFILES:
        binary = code_repo / f"build/{args.build_prefix}-{profile}/src/retractor/xretractor"
        if not binary.is_file():
            raise SystemExit(f"brak binarki profilu {profile}: {binary}")
        binaries[profile] = binary

    observations: list[dict[str, object]] = []
    fits_at: dict[tuple[str, int], bool] = {}
    worst_at: dict[tuple[str, int], float] = {}
    rates: dict[str, int] = {}
    pending = set(laddered)
    checked = 0
    measured_scales: list[int] = []

    intervals: dict[tuple[str, int], Fraction] = {}
    slots_at: dict[tuple[str, int], int] = {}
    features_at: dict[tuple[str, int], dict[str, int]] = {}

    for scale in LADDER:
        if not pending:
            break
        measured_scales.append(scale)
        workloads = generate_workloads(here, scale)
        for family in sorted(pending):
            family_fits = True
            for case in laddered[family]:
                interval, slots, worst, features = measure_cell(binaries, workloads, code_repo, case, client_stream[case])
                checked += len(PROFILES) * REPS
                intervals[(case, scale)] = interval
                slots_at[(case, scale)] = slots
                features_at[(case, scale)] = features
                duration_ns = float(interval) * 1_000_000_000
                budget_ns = BUDGET_FRACTION * duration_ns
                fits = worst <= budget_ns
                fits_at[(case, scale)] = fits
                worst_at[(case, scale)] = worst
                family_fits = family_fits and fits
                observations.append(
                    {
                        "scale": scale,
                        "family": family,
                        "case": case,
                        "slots": slots,
                        "p99_ns": worst,
                        "budget_ns": budget_ns,
                        "slot_ns": duration_ns,
                        "slot_nominal_ns": nominal_slot_ns(scale),
                        "slot_from": "silnik",
                        "fits": fits,
                        "counters": features,
                    }
                )
                print(
                    f"s={scale} {case}: p99={worst / 1000:.2f} µs budżet={budget_ns / 1000:.2f} µs "
                    f"{'OK' if fits else 'NIE'}",
                    flush=True,
                )
            if family_fits:
                rates[family] = scale
        pending -= set(rates)
        shutil.rmtree(workloads, ignore_errors=True)

    # Rodziny „ze źródła" nie schodzą po drabinie — ich rate należy do deklaracji
    # źródła. Slot mierzymy im mimo to, bo jest własnością strumienia, nie naszą:
    # `mon_000` biegnie 1/720, choć `rec205` deklaruje 1/360. Wynik reguły 50 %
    # jest dla nich RAPORTOWANY (żeby ewentualne nasycenie było widoczne przed
    # kampanią, nie po niej), ale rate'u nie zmienia.
    if sourced:
        workloads = generate_workloads(here, SOURCE_FAMILY_SCALE)
        for family in sorted(sourced):
            for case in sourced[family]:
                interval, slots, worst, features = measure_cell(binaries, workloads, code_repo, case, client_stream[case])
                checked += len(PROFILES) * REPS
                key = (case, SOURCE_FAMILY_SCALE)
                intervals[key] = interval
                slots_at[key] = slots
                features_at[key] = features
                duration_ns = float(interval) * 1_000_000_000
                budget_ns = BUDGET_FRACTION * duration_ns
                fits = worst <= budget_ns
                fits_at[key] = fits
                worst_at[key] = worst
                observations.append(
                    {
                        "scale": SOURCE_FAMILY_SCALE,
                        "family": family,
                        "case": case,
                        "slots": slots,
                        "p99_ns": worst,
                        "budget_ns": budget_ns,
                        "slot_ns": duration_ns,
                        "slot_nominal_ns": 1_000_000_000 / source_hz[family],
                        "slot_from": "silnik",
                        "fits": fits,
                        "counters": features,
                    }
                )
                print(
                    f"źródło {case}: p99={worst / 1000:.2f} µs budżet={budget_ns / 1000:.2f} µs "
                    f"{'OK' if fits else 'NIE (raportowane, rate nie zmieniony)'}",
                    flush=True,
                )
        shutil.rmtree(workloads, ignore_errors=True)

    # Reguła zliczania: zero wykonanych przebiegów nie jest zgodnością.
    if checked == 0:
        raise SystemExit("kalibracja nie wykonała ani jednego przebiegu")

    # Rodziny, które nie zmieściły się na żadnym szczeblu: wykluczamy komórki
    # niemieszczące się przy najniższym szczeblu, po czym wyznaczamy rate
    # na tym, co zostało.
    slot_ns_at = {key: float(value) * 1_000_000_000 for key, value in intervals.items()}
    rates, excluded_cases, excluded_families = resolve_rates(
        laddered, rates, fits_at, worst_at, measured_scales, slot_ns_at
    )

    # Rodzina niesie już tylko to, co jest jej własnością: szczebel drabiny,
    # czyli mnożnik przekazywany generatorowi. Slot NIE jest własnością rodziny —
    # `W3_d1` i `W3_d3` mają go różny przy tym samym `s`. Dlatego `f_phi_hz`
    # nazywa się tu `generator_f_phi_hz`: to rate przeplotu dwóch źródeł, który
    # generator wytwarza, a nie częstotliwość strumienia mierzonego.
    families: dict[str, dict[str, object]] = {}
    for family, scale in sorted(rates.items()):
        families[family] = {
            "scale": scale,
            "generator_f_phi_hz": 15.0 * scale,
            "source": "kalibracja",
        }
    for family in sorted(sourced):
        families[family] = {
            "scale": SOURCE_FAMILY_SCALE,
            "generator_f_phi_hz": 15.0 * SOURCE_FAMILY_SCALE,
            "source_hz": source_hz[family],
            "source": "deklaracja zrodla",
        }

    # Slot i budżet slotów są własnością KOMÓRKI. Worker czyta te wartości stąd
    # i nie wolno mu ich wyliczać.
    excluded_names = {entry["case"] for entry in excluded_cases}
    cells: dict[str, dict[str, object]] = {}
    for case, stream in sorted(client_stream.items()):
        if case in excluded_names:
            continue
        family = next(row["family"] for row in matrix if row["case"] == case)
        if family not in families:
            continue
        scale = int(families[family]["scale"])
        key = (case, scale)
        if key not in intervals:
            raise SystemExit(f"{case}: brak zmierzonego slotu przy s={scale} — kalibracja niespójna")
        duration_ns = float(intervals[key]) * 1_000_000_000
        # Wartość, którą wstawiłaby v2 — trzymana wyłącznie po to, żeby raport
        # pokazał rozjazd. Dla rodzin ze źródła v2 wstawiała rate źródła danych.
        nominal_ns = 1_000_000_000 / source_hz[family] if family in sourced else nominal_slot_ns(scale)
        cells[case] = {
            "family": family,
            "client_stream": stream,
            "scale": scale,
            "slot_ns": duration_ns,
            "slot_nominal_ns": nominal_ns,
            "stream_hz": 1_000_000_000 / duration_ns,
            "slots": slots_at[key],
            "p99_ns": worst_at[key],
            "budget_ns": BUDGET_FRACTION * duration_ns,
            "fits": fits_at[key],
            "slot_from": "silnik",
            "counters": features_at[key],
        }
    if not cells:
        raise SystemExit("żadna komórka Tier B nie ma zmierzonego slotu — nie ma czego mierzyć")

    rate_json = {
        "version": 3,
        "ladder": LADDER,
        "budget_fraction": BUDGET_FRACTION,
        "profiles": PROFILES,
        "reps": REPS,
        "run_seconds": RUN_SECONDS,
        "slots_min": SLOTS_MIN,
        "slots_max": SLOTS_MAX,
        "families": families,
        "cells": cells,
        "excluded_cases": excluded_cases,
        "excluded_families": excluded_families,
        "checked_runs": checked,
        "calibrated_cases": sum(len(cases) for cases in laddered.values()),
        "observations": observations,
    }

    lines = [
        "# K6c.0 — kalibracja rate'u pomiarowego (per rodzina)",
        "",
        "Reguła zamrożona w README v3: dla każdej rodziny największe `s`, przy którym",
        f"**każda niewykluczona** komórka spełnia `p99(compute_ns) <= {BUDGET_FRACTION} * slot`",
        "w najgorszym zmierzonym profilu. Komórka niemieszcząca się przy `s = 1` wypada",
        "z Tier B i nie ogranicza rate'u swojej rodziny.",
        "",
        "`slot` pochodzi z **silnika** (`xqry -t`), dla strumienia, który kampania",
        "faktycznie mierzy. To jest zmiana v3 wobec v2 i jedyny powód istnienia K6c.",
        "",
        f"- drabina: {LADDER}",
        f"- profile kalibracyjne: {', '.join(PROFILES)} — bez przepisywania algebraicznego, więc górne oszacowanie kosztu",
        f"- powtórzeń na komórkę i profil: {REPS}",
        f"- komórek kalibrowanych: {rate_json['calibrated_cases']}, przebiegów: {checked}",
        "",
        "## Przemiecenie drabiny",
        "",
        "Rodzina nieobecna na niższym szczeblu jest rodziną **rozstrzygniętą** wyżej —",
        "kalibracja nie mierzy jej dalej. Rodziny „ze źródła” mają w kolumnie `s`",
        "mnożnik generatora, którego dla nich nie używa; ich rate jest deklaracją źródła.",
        "",
        "| `s` | slot (silnik) | budżet | slotów | rodzina | przypadek | `p99` (najgorszy profil) | mieści się |",
        "|---:|---:|---:|---:|---|---|---:|:--:|",
    ]
    for record in observations:
        lines.append(
            f"| {record['scale']} | {float(record['slot_ns']) / 1000:.2f} µs | "
            f"{float(record['budget_ns']) / 1000:.2f} µs | {record['slots']} | {record['family']} | "
            f"`{record['case']}` | {float(record['p99_ns']) / 1000:.2f} µs | "
            f"{'tak' if record['fits'] else '**nie**'} |"
        )

    lines += [
        "",
        "## Rate wybrany per rodzina",
        "",
        "`f_phi` generatora to rate przeplotu **dwóch źródeł**, który generator wytwarza.",
        "Nie jest częstotliwością strumienia mierzonego — ta jest w tabeli niżej, per komórka.",
        "Pomylenie tych dwóch wielkości było błędem v2.",
        "",
        "| Rodzina | `s` | `f_phi` generatora | źródło rate'u |",
        "|---|---:|---:|---|",
    ]
    for family, entry in sorted(families.items()):
        lines.append(
            f"| {family} | {entry['scale']} | {float(entry['generator_f_phi_hz']):.1f} Hz | {entry['source']} |"
        )

    lines += [
        "",
        "## Slot per komórka — wartość z silnika wobec wyliczenia v2",
        "",
        "Slot jest własnością **komórki**, nie rodziny: `W3_d1` i `W3_d3` mają go różny",
        "przy tym samym `s`, bo przeplot sumuje częstotliwości. Kolumna „v2” pokazuje,",
        "co wstawiłaby poprzednia predeklaracja; kolumna „rozjazd” jest miarą jej błędu.",
        "Budżet slotów liczony jest z wartości zmierzonej.",
        "",
        "| Przypadek | strumień | `s` | slot (silnik) | slot wg v2 | rozjazd | częstotliwość | slotów | `p99` | wykorzystanie |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for case, entry in sorted(cells.items()):
        measured = float(entry["slot_ns"])
        nominal = float(entry["slot_nominal_ns"])
        utilisation = float(entry["p99_ns"]) / measured
        lines.append(
            f"| `{case}` | `{entry['client_stream']}` | {entry['scale']} | {measured / 1000:.2f} µs | "
            f"{nominal / 1000:.2f} µs | {nominal / measured:.2f}× | {float(entry['stream_hz']):.1f} Hz | "
            f"{entry['slots']} | {float(entry['p99_ns']) / 1000:.2f} µs | "
            f"{'**' if utilisation > BUDGET_FRACTION else ''}{utilisation * 100:.0f} %"
            f"{'**' if utilisation > BUDGET_FRACTION else ''} |"
        )

    lines += ["", "## Komórki wykluczone z Tier B", ""]
    if excluded_cases:
        lines += [
            "Komórka nie mieści się w budżecie nawet przy `s = 1`. Wykluczenie jest",
            "**wynikiem**, nie zamiataniem: wymagana częstotliwość strumienia jest podana.",
            "",
            "| Przypadek | `p99` przy `s=1` | slot (silnik) | budżet | wymagana częstotliwość |",
            "|---|---:|---:|---:|---:|",
        ]
        for entry in excluded_cases:
            lines.append(
                f"| `{entry['case']}` | {float(entry['p99_ns']) / 1000:.2f} µs | "
                f"{float(entry['slot_ns']) / 1000:.2f} µs | {float(entry['budget_ns']) / 1000:.2f} µs | "
                f"{float(entry['required_stream_hz']):.2f} Hz |"
            )
        if excluded_families:
            lines += ["", f"Rodziny wykluczone w całości: {', '.join(excluded_families)}."]
    else:
        lines.append("Brak — każda komórka Tier B zmieściła się w budżecie na którymś szczeblu drabiny.")

    # Rodzina „ze źródła" nie może zejść niżej po drabinie, więc jej nasycenie
    # nie jest wykluczeniem, tylko faktem do zaraportowania przed kampanią.
    saturated_sourced = [case for case, entry in sorted(cells.items()) if entry["family"] in sourced and not entry["fits"]]
    if saturated_sourced:
        lines += [
            "",
            "## Rodziny ze źródła poza budżetem 50 %",
            "",
            f"Komórki: {', '.join(f'`{case}`' for case in saturated_sourced)}.",
            "Ich rate należy do deklaracji źródła, więc kalibracja go nie zmienia i nie",
            "wyklucza tych komórek. Fakt jest raportowany **przed** kampanią; decyzja,",
            "czy mierzyć rodzinę w tym reżimie, należy do człowieka.",
        ]

    lines += [
        "",
        "## Uwaga o statusie tych liczb",
        "",
        "Wyniki kalibracji **nie są wynikami kampanii** i nie wchodzą do żadnej tabeli",
        "artykułu. Wchodzą natomiast — jako pary (komórka, rate, `p99`) — do modelu",
        "kosztu slotu (`cost_model.md`, K20 etap 1), który jest produktem ubocznym",
        "i nie zmienia reguły wyboru rate'u.",
    ]

    (output / "calibration.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "rate.json").write_text(json.dumps(rate_json, indent=2) + "\n", encoding="utf-8")

    if not rates:
        print("BLAD: żadna rodzina Tier B nie ma dopuszczalnego rate'u", file=sys.stderr)
        return 1
    summary = ", ".join(f"{family}=s{families[family]['scale']}" for family in sorted(rates))
    print(
        f"rate per rodzina: {summary}; wykluczone komórki: {len(excluded_cases)}; "
        f"przebiegów kalibracyjnych: {checked}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
