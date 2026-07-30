#!/usr/bin/env python3
"""K6b.0 — kalibracja rate'u pomiarowego, **per rodzina**. Uruchamiane na workerze.

Reguła jest zamrożona w README v2 i przepisana tu dosłownie:

    rate(rodzina) = największe `s` z drabiny {36, 24, 12, 6, 3, 1}, przy którym
                    KAŻDA niewykluczona komórka tej rodziny spełnia
                    p99(compute_ns) <= 0,5 * slot(phi)
                    w najgorszym zmierzonym profilu

    komórka, która nie spełnia tego warunku nawet przy s = 1, jest WYKLUCZONA
    z Tier B, nie ogranicza rate'u swojej rodziny i jest raportowana wraz
    z p99, budżetem i wymaganym f_phi

Dlaczego per rodzina, a nie globalnie: kalibracja v1 (`results_20260730_K6`)
odrzuciła całą drabinę, bo jedna komórka — `W4_Q32` — ma koszt STAŁY co-slot
(okno `@(1,30)` liczy 30 próbek w każdym slocie, niezależnie od jego długości).
Rate globalny wiązał ze sobą rodziny, między którymi nie zachodzi żadne
porównanie.

Dlaczego nie per komórka: przy różnych rate'ach dla `Q08` i `Q32` porównanie
skalowania w `Q` wewnątrz rodziny byłoby skażone rate'em.

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


def slot_ns(scale: int) -> float:
    return float(Fraction(1, 15 * scale) * 1_000_000_000)


def slots_for(slot_duration_ns: float) -> int:
    return max(SLOTS_MIN, min(SLOTS_MAX, round(RUN_SECONDS * 1_000_000_000 / slot_duration_ns)))


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
                    "budget_ns": BUDGET_FRACTION * slot_ns(bottom),
                    "scale": bottom,
                    "required_f_phi_hz": BUDGET_FRACTION * 1_000_000_000 / p99,
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


def run_once(binary: Path, case_dir: Path, slots: int) -> tuple[int, dict[str, int]]:
    """Jeden przebieg kalibracyjny.

    Zwraca `p99(compute_ns)` po odrzuceniu transjentu oraz liczniki planu
    i materializacji z tego samego przebiegu.
    """
    with tempfile.TemporaryDirectory(prefix="rdb-k6b-cal-", dir="/dev/shm") as root:
        work = Path(root) / "case"
        work.mkdir()
        (work / "temp").mkdir()
        shutil.copy(case_dir / "query.rql", work / "query.rql")
        for extra in sorted(case_dir.glob("*.txt")):
            if extra.name != "external_data.txt":
                shutil.copy(extra, work / extra.name)
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
    if "rate" not in matrix[0]:
        raise SystemExit("macierz nie ma kolumny `rate`; K6b wymaga macierzy v2")

    # Rodziny podlegające drabinie i rodziny o rate'cie z deklaracji źródła (W8).
    laddered: dict[str, list[str]] = {}
    fixed: dict[str, float] = {}
    for row in matrix:
        if row["rate"] == "calibration":
            laddered.setdefault(row["family"], []).append(row["case"])
        elif row["rate"].startswith("fixed:"):
            fixed[row["family"]] = float(row["rate"].split(":", 1)[1])
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

    for scale in LADDER:
        if not pending:
            break
        measured_scales.append(scale)
        duration_ns = slot_ns(scale)
        budget_ns = BUDGET_FRACTION * duration_ns
        slots = slots_for(duration_ns)
        workloads = Path("/dev/shm/k6b-calibration") / f"scale{scale}"
        if workloads.exists():
            shutil.rmtree(workloads)
        subprocess.run(
            [sys.executable, str(here / "generate.py"), "--output", str(workloads), "--scale", str(scale)],
            check=True,
            capture_output=True,
        )
        for family in sorted(pending):
            family_fits = True
            for case in laddered[family]:
                worst = 0.0
                # Cechy dla modelu kosztu slotu zbieramy z profilu OFF: jest bez
                # przepisywania, więc liczniki opisują plan wejściowy, a nie
                # jego zoptymalizowaną postać.
                features: dict[str, int] = {}
                for profile in PROFILES:
                    for _ in range(REPS):
                        p99, counters = run_once(binaries[profile], workloads / case, slots)
                        worst = max(worst, float(p99))
                        if profile == PROFILES[0] and not features:
                            features = counters
                        checked += 1
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

    # Reguła zliczania: zero wykonanych przebiegów nie jest zgodnością.
    if checked == 0:
        raise SystemExit("kalibracja nie wykonała ani jednego przebiegu")

    # Rodziny, które nie zmieściły się na żadnym szczeblu: wykluczamy komórki
    # niemieszczące się przy najniższym szczeblu, po czym wyznaczamy rate
    # na tym, co zostało.
    rates, excluded_cases, excluded_families = resolve_rates(
        laddered, rates, fits_at, worst_at, measured_scales
    )

    families: dict[str, dict[str, object]] = {}
    for family, scale in sorted(rates.items()):
        duration_ns = slot_ns(scale)
        families[family] = {
            "scale": scale,
            "f_phi_hz": 15.0 * scale,
            "slot_phi_ns": duration_ns,
            "slots": slots_for(duration_ns),
            "source": "kalibracja",
        }
    for family, f_phi in sorted(fixed.items()):
        duration_ns = 1_000_000_000 / f_phi
        families[family] = {
            "scale": None,
            "f_phi_hz": f_phi,
            "slot_phi_ns": duration_ns,
            "slots": slots_for(duration_ns),
            "source": "deklaracja zrodla",
        }

    rate_json = {
        "version": 2,
        "ladder": LADDER,
        "budget_fraction": BUDGET_FRACTION,
        "profiles": PROFILES,
        "reps": REPS,
        "families": families,
        "excluded_cases": excluded_cases,
        "excluded_families": excluded_families,
        "checked_runs": checked,
        "calibrated_cases": sum(len(cases) for cases in laddered.values()),
        "observations": observations,
    }

    lines = [
        "# K6b.0 — kalibracja rate'u pomiarowego (per rodzina)",
        "",
        "Reguła zamrożona w README v2: dla każdej rodziny największe `s`, przy którym",
        f"**każda niewykluczona** komórka spełnia `p99(compute_ns) <= {BUDGET_FRACTION} * slot(phi)`",
        "w najgorszym zmierzonym profilu. Komórka niemieszcząca się przy `s = 1` wypada",
        "z Tier B i nie ogranicza rate'u swojej rodziny.",
        "",
        f"- drabina: {LADDER}",
        f"- profile kalibracyjne: {', '.join(PROFILES)} — bez przepisywania algebraicznego, więc górne oszacowanie kosztu",
        f"- powtórzeń na komórkę i profil: {REPS}",
        f"- komórek kalibrowanych: {rate_json['calibrated_cases']}, przebiegów: {checked}",
        "",
        "## Przemiecenie drabiny",
        "",
        "Rodzina nieobecna na niższym szczeblu jest rodziną **rozstrzygniętą** wyżej —",
        "kalibracja nie mierzy jej dalej.",
        "",
        "| `s` | slot `phi` | budżet | slotów | rodzina | przypadek | `p99` (najgorszy profil) | mieści się |",
        "|---:|---:|---:|---:|---|---|---:|:--:|",
    ]
    for record in observations:
        lines.append(
            f"| {record['scale']} | {float(record['budget_ns']) / BUDGET_FRACTION / 1000:.2f} µs | "
            f"{float(record['budget_ns']) / 1000:.2f} µs | {record['slots']} | {record['family']} | "
            f"`{record['case']}` | {float(record['p99_ns']) / 1000:.2f} µs | "
            f"{'tak' if record['fits'] else '**nie**'} |"
        )

    lines += [
        "",
        "## Rate wybrany per rodzina",
        "",
        "| Rodzina | `s` | `f_phi` | slot | slotów | źródło |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for family, entry in sorted(families.items()):
        scale_text = str(entry["scale"]) if entry["scale"] is not None else "—"
        lines.append(
            f"| {family} | {scale_text} | {float(entry['f_phi_hz']):.1f} Hz | "
            f"{float(entry['slot_phi_ns']) / 1000:.2f} µs | {entry['slots']} | {entry['source']} |"
        )

    lines += ["", "## Komórki wykluczone z Tier B", ""]
    if excluded_cases:
        lines += [
            "Komórka nie mieści się w budżecie nawet przy `s = 1` (`f_phi = 15 Hz`).",
            "Wykluczenie jest **wynikiem**, nie zamiataniem: wymagany rate jest podany.",
            "",
            "| Przypadek | `p99` przy `s=1` | budżet | wymagane `f_phi` |",
            "|---|---:|---:|---:|",
        ]
        for entry in excluded_cases:
            lines.append(
                f"| `{entry['case']}` | {float(entry['p99_ns']) / 1000:.2f} µs | "
                f"{float(entry['budget_ns']) / 1000:.2f} µs | {float(entry['required_f_phi_hz']):.2f} Hz |"
            )
        if excluded_families:
            lines += ["", f"Rodziny wykluczone w całości: {', '.join(excluded_families)}."]
    else:
        lines.append("Brak — każda komórka Tier B zmieściła się w budżecie na którymś szczeblu drabiny.")

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
