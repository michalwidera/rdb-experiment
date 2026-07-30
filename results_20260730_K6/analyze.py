#!/usr/bin/env python3
"""K6.6 — analiza i werdykt kampanii. Uruchamiane na nadzorcy.

Reguła decyzyjna jest przepisana z predeklaracji README i **nie jest tu
wyznaczana**:

    r(c)  = mediana15(ALGSTRUCT) / mediana15(STRUCT)     dla metryki głównej
    CI(c) = bootstrap 95% ilorazu, 10 000 replikacji, ziarno 20260730

    (A) poprawa   : r <= 0,90 oraz górna granica CI < 1,00
    (B) neutralna : CI zawiera 1,00 albo |1 - r| < 0,10
    (C) regresja  : r >= 1,10 oraz dolna granica CI > 1,00

Metryka główna: mediana `compute_ns` na slot. Metryki drugorzędne przechodzą
przez ten sam aparat i są raportowane obok, nigdy zamiast.

Raportowane są **wszystkie** komórki — reguła §9.5 planu badawczego zabrania
wybierania workloadu, na którym optymalizacja wygrywa.
"""
import argparse
import csv
import json
import random
import statistics
from pathlib import Path

BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20260730
THRESHOLD = 0.10
BASELINE = "STRUCT"
TREATMENT = "ALGSTRUCT"

# Kontrole negatywne: komórka klasy (A) lub (C) unieważnia kampanię.
NEGATIVE_CONTROLS = {"W5_Q32", "W7_Q32"}

PRIMARY = "compute_median_ns"
SECONDARY = [
    "compute_p99_ns",
    "compute_sum_ns",
    "e2e_p50_ns",
    "e2e_p999_ns",
    "vmhwm_kb",
    "cpu_ticks",
    "capacity_sum",
    "mat_bytes",
    "mat_mem_bytes",
]


def bootstrap_ratio_ci(treatment: list[float], baseline: list[float]) -> tuple[float, float, float]:
    """Iloraz median i jego przedział bootstrapowy 95%.

    Resamplowane są niezależnie obie próbki median z przebiegów; statystyką jest
    iloraz median replikacji. Ziarno jest stałe, więc wynik jest odtwarzalny.
    """
    ratio = statistics.median(treatment) / statistics.median(baseline)
    rng = random.Random(BOOTSTRAP_SEED)
    ratios = []
    n_t, n_b = len(treatment), len(baseline)
    for _ in range(BOOTSTRAP_REPLICATES):
        sample_t = statistics.median([treatment[rng.randrange(n_t)] for _ in range(n_t)])
        sample_b = statistics.median([baseline[rng.randrange(n_b)] for _ in range(n_b)])
        ratios.append(sample_t / sample_b)
    ratios.sort()
    low = ratios[int(0.025 * (len(ratios) - 1))]
    high = ratios[int(0.975 * (len(ratios) - 1))]
    return ratio, low, high


def classify(ratio: float, low: float, high: float) -> str:
    if ratio <= 1 - THRESHOLD and high < 1.0:
        return "A"
    if ratio >= 1 + THRESHOLD and low > 1.0:
        return "C"
    return "B"


def load_runs(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        with path.open(encoding="utf-8", newline="") as handle:
            rows.extend(csv.DictReader(handle))
    return rows


def cells(rows: list[dict[str, str]], metric: str) -> dict[tuple[str, str], list[float]]:
    grouped: dict[tuple[str, str], list[float]] = {}
    for row in rows:
        grouped.setdefault((row["case"], row["profile"]), []).append(float(row[metric]))
    return grouped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, nargs="+", required=True, help="pliki runs.csv badań Tier B")
    parser.add_argument("--compile-runs", type=Path, help="compile_runs.csv z Tier A")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows = load_runs([p.resolve() for p in args.runs])
    if not rows:
        raise SystemExit("BLAD: zero przebiegów do analizy")

    # Warunek unieważniający nr 2: wynik musi być identyczny w obrębie komórki
    # i między profilami tego samego przypadku.
    checksum_problems: list[str] = []
    by_case: dict[str, set[str]] = {}
    for row in rows:
        by_case.setdefault(row["case"], set()).add(row["artifacts_sha256"])
    for case, digests in sorted(by_case.items()):
        if len(digests) != 1:
            checksum_problems.append(f"{case}: {len(digests)} różnych checksumów artefaktów")

    grouped = cells(rows, PRIMARY)
    cases = sorted({row["case"] for row in rows})
    profiles = sorted({row["profile"] for row in rows})

    records: list[dict[str, object]] = []
    for case in cases:
        baseline = grouped.get((case, BASELINE))
        treatment = grouped.get((case, TREATMENT))
        if not baseline or not treatment:
            raise SystemExit(f"BLAD: brak pary {BASELINE}/{TREATMENT} dla {case}")
        ratio, low, high = bootstrap_ratio_ci(treatment, baseline)
        record: dict[str, object] = {
            "case": case,
            "n_baseline": len(baseline),
            "n_treatment": len(treatment),
            "median_baseline_ns": statistics.median(baseline),
            "median_treatment_ns": statistics.median(treatment),
            "iqr_baseline_ns": (statistics.quantiles(baseline, n=4)[2] - statistics.quantiles(baseline, n=4)[0])
            if len(baseline) >= 4
            else 0.0,
            "ratio": ratio,
            "ci_low": low,
            "ci_high": high,
            "class": classify(ratio, low, high),
            "negative_control": case in NEGATIVE_CONTROLS,
        }
        # Atrybucja: który profil pośredni odpowiada za efekt (G14).
        for profile in profiles:
            values = grouped.get((case, profile))
            if values:
                record[f"median_{profile}_ns"] = statistics.median(values)
        records.append(record)

    secondary: dict[str, list[dict[str, object]]] = {}
    for metric in SECONDARY:
        metric_cells = cells(rows, metric)
        metric_records = []
        for case in cases:
            baseline = metric_cells.get((case, BASELINE))
            treatment = metric_cells.get((case, TREATMENT))
            if not baseline or not treatment:
                continue
            if statistics.median(baseline) == 0:
                metric_records.append({"case": case, "ratio": None, "note": "baseline = 0"})
                continue
            ratio, low, high = bootstrap_ratio_ci(treatment, baseline)
            metric_records.append(
                {
                    "case": case,
                    "median_baseline": statistics.median(baseline),
                    "median_treatment": statistics.median(treatment),
                    "ratio": ratio,
                    "ci_low": low,
                    "ci_high": high,
                    "class": classify(ratio, low, high),
                }
            )
        secondary[metric] = metric_records

    compile_records: list[dict[str, object]] = []
    if args.compile_runs and args.compile_runs.is_file():
        compile_rows = load_runs([args.compile_runs.resolve()])
        compile_cells = cells(compile_rows, "compile_ns")
        for case in sorted({row["case"] for row in compile_rows}):
            baseline = compile_cells.get((case, BASELINE))
            treatment = compile_cells.get((case, TREATMENT))
            if not baseline or not treatment:
                continue
            ratio, low, high = bootstrap_ratio_ci(treatment, baseline)
            compile_records.append(
                {
                    "case": case,
                    "median_baseline_ns": statistics.median(baseline),
                    "median_treatment_ns": statistics.median(treatment),
                    "ratio": ratio,
                    "ci_low": low,
                    "ci_high": high,
                    "class": classify(ratio, low, high),
                }
            )

    counts = {"A": 0, "B": 0, "C": 0}
    for record in records:
        counts[str(record["class"])] += 1
    control_violations = [
        str(record["case"]) for record in records if record["negative_control"] and record["class"] != "B"
    ]
    improvements = [str(record["case"]) for record in records if record["class"] == "A"]
    regressions = [str(record["case"]) for record in records if record["class"] == "C"]
    external_improvement = [case for case in improvements if case.startswith("W8")]

    report = {
        "runs": len(rows),
        "cases": len(cases),
        "profiles": profiles,
        "primary_metric": PRIMARY,
        "threshold": THRESHOLD,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "counts": counts,
        "improvements": improvements,
        "regressions": regressions,
        "external_improvement": external_improvement,
        "control_violations": control_violations,
        "checksum_problems": checksum_problems,
        "records": records,
        "secondary": secondary,
        "compile": compile_records,
    }
    (output / "analysis.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# K6 — wynik kampanii ablacyjnej",
        "",
        f"- przebiegów: {len(rows)}",
        f"- przypadków: {len(cases)}, profili: {len(profiles)}",
        f"- metryka główna: `{PRIMARY}`, próg istotności praktycznej: {int(THRESHOLD * 100)}%",
        f"- bootstrap: {BOOTSTRAP_REPLICATES} replikacji, ziarno {BOOTSTRAP_SEED}",
        "",
        "## Metryka główna — wszystkie komórki",
        "",
        "| Przypadek | `STRUCT` [µs] | `ALGSTRUCT` [µs] | iloraz | 95% CI | klasa | kontrola |",
        "|---|---:|---:|---:|---|:--:|:--:|",
    ]
    for record in records:
        lines.append(
            f"| `{record['case']}` | {float(record['median_baseline_ns']) / 1000:.2f} | "
            f"{float(record['median_treatment_ns']) / 1000:.2f} | {float(record['ratio']):.3f} | "
            f"[{float(record['ci_low']):.3f}; {float(record['ci_high']):.3f}] | **{record['class']}** | "
            f"{'neg' if record['negative_control'] else ''} |"
        )

    lines += [
        "",
        "## Atrybucja profilowa (G14)",
        "",
        "| Przypadek | " + " | ".join(f"`{p}` [µs]" for p in profiles) + " |",
        "|---|" + "---:|" * len(profiles),
    ]
    for record in records:
        values = []
        for profile in profiles:
            key = f"median_{profile}_ns"
            values.append(f"{float(record[key]) / 1000:.2f}" if key in record else "—")
        lines.append(f"| `{record['case']}` | " + " | ".join(values) + " |")

    lines += ["", "## Werdykt", ""]
    lines.append(f"- komórki (A) poprawa: **{counts['A']}**" + (f" — {', '.join(improvements)}" if improvements else ""))
    lines.append(f"- komórki (B) neutralne: **{counts['B']}**")
    lines.append(f"- komórki (C) regresja: **{counts['C']}**" + (f" — {', '.join(regressions)}" if regressions else ""))
    lines.append("")
    if control_violations:
        lines.append(
            f"**KAMPANIA NIEWAŻNA.** Kontrola negatywna dała efekt: {', '.join(control_violations)}. "
            "Instrument mierzy coś innego niż optymalizację; pozostałych komórek nie wolno raportować jako wyniku."
        )
    elif checksum_problems:
        lines.append(
            "**KAMPANIA NIEWAŻNA.** Wynik nie jest zachowany między profilami: "
            + "; ".join(checksum_problems)
            + ". Przyspieszenie z innym wynikiem nie jest przyspieszeniem."
        )
    elif counts["A"] == 0:
        lines.append(
            "**Brak komórki klasy (A).** Korzyść z R1/R2 nie jest widoczna w czasie obliczeń przy "
            f"progu {int(THRESHOLD * 100)}%. To jest wynik, nie porażka kampanii: korzyść pozostaje "
            "strukturalna (plan, tokeny, bufory, materializacje), a artykuł ma tak ją opisać. "
            "Zdanie „plan jest mniejszy, ale nie szybszy" + '" jest publikowalne.'
        )
    else:
        lines.append(f"**Wykazano poprawę w {counts['A']} komórkach.**")
        if external_improvement:
            lines.append(
                f"Co najmniej jedna należy do rodziny umotywowanej zewnętrznie (W8): {', '.join(external_improvement)}."
            )
        else:
            lines.append(
                "**Żadna nie należy do rodziny umotywowanej zewnętrznie (W8)** — luka G7 pozostaje "
                "otwarta dla twierdzenia kosztowego i tak trzeba to zaraportować."
            )
        if regressions:
            lines.append(
                f"Odnotowano też regresje: {', '.join(regressions)}. H4 wymaga sprawdzenia, czy nie "
                "przekreślają korzyści."
            )

    if compile_records:
        lines += [
            "",
            "## Koszt normalizacji — czas kompilacji (Tier A)",
            "",
            "| Przypadek | `STRUCT` [µs] | `ALGSTRUCT` [µs] | iloraz | 95% CI | klasa |",
            "|---|---:|---:|---:|---|:--:|",
        ]
        for record in compile_records:
            lines.append(
                f"| `{record['case']}` | {float(record['median_baseline_ns']) / 1000:.2f} | "
                f"{float(record['median_treatment_ns']) / 1000:.2f} | {float(record['ratio']):.3f} | "
                f"[{float(record['ci_low']):.3f}; {float(record['ci_high']):.3f}] | {record['class']} |"
            )
        lines.append("")
        lines.append("Klasa (C) w tej tabeli jest **ceną** normalizacji, nie korzyścią.")

    lines += ["", "## Metryki drugorzędne", ""]
    for metric, metric_records in secondary.items():
        classes = {"A": 0, "B": 0, "C": 0}
        for record in metric_records:
            if record.get("class"):
                classes[str(record["class"])] += 1
        lines.append(f"- `{metric}`: A={classes['A']}, B={classes['B']}, C={classes['C']}")

    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"komórek: {len(records)}, A={counts['A']} B={counts['B']} C={counts['C']}")
    if control_violations or checksum_problems:
        print("KAMPANIA NIEWAŻNA", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
