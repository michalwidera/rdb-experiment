#!/usr/bin/env python3
"""K6b.6 — analiza i werdykt kampanii. Uruchamiane na nadzorcy.

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

**Nowe w v2 (warunek unieważniający nr 6).** Rate jest w K6b wybierany per
rodzina, więc przestał być stałą kampanii i stał się zmienną, którą trzeba
kontrolować. Porównanie profili ma sens wyłącznie przy identycznym rate'cie,
dlatego `runs.csv` niesie kolumny `scale` i `f_phi_hz` przy każdym przebiegu,
a tutaj sprawdzamy, że w obrębie jednego przypadku — a więc i w obrębie każdej
jego komórki — jest dokładnie jedna wartość. Zero sprawdzonych przypadków jest
błędem, nie zgodnością.
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


def rate_consistency(rows: list[dict[str, str]]) -> tuple[list[str], int, dict[str, str]]:
    """Warunek unieważniający nr 6: rate identyczny w obrębie przypadku.

    Zwraca listę problemów, liczbę sprawdzonych przypadków i mapę przypadek →
    rate. Zero sprawdzonych przypadków jest błędem — instrument, który nic nie
    porównał, milczy, a milczenie wygląda jak sukces (K5h, K5i).
    """
    # ZMIANA v3: sprawdzamy też `stream_hz`, czyli częstotliwość strumienia
    # MIERZONEGO. Sam `scale` jej nie wyznacza — `W3_d1` i `W3_d3` biegną przy
    # tym samym `s` z różnym slotem — więc kontrola oparta na `scale` i `f_phi_hz`
    # generatora przepuściłaby porównanie profili przy różnym slocie.
    required = ("scale", "f_phi_hz", "stream_hz")
    missing = [column for column in required if column not in rows[0]]
    if missing:
        return [f"runs.csv lacks columns {', '.join(f'`{c}`' for c in missing)} — the rate control cannot be performed"], 0, {}
    seen: dict[str, set[tuple[str, str, str]]] = {}
    for row in rows:
        seen.setdefault(row["case"], set()).add((row["scale"], row["f_phi_hz"], row["stream_hz"]))
    problems: list[str] = []
    rates: dict[str, str] = {}
    for case, values in sorted(seen.items()):
        if len(values) != 1:
            listed = ", ".join(f"s={scale} f_phi={f_phi} stream={stream} Hz" for scale, f_phi, stream in sorted(values))
            problems.append(f"{case}: {len(values)} different rates ({listed})")
            continue
        scale, f_phi, stream = next(iter(values))
        rates[case] = f"s={scale}, generator f_phi={f_phi} Hz, stream={stream} Hz"
    return problems, len(seen), rates


def saturation_control(rows: list[dict[str, str]], rate_json: dict[str, object]) -> list[str]:
    """Kontrola RAPORTOWANA, nie unieważniająca.

    Kalibracja mierzy `OFF` i `STRUCT` — profile bez przepisywania
    algebraicznego, a więc górne oszacowanie kosztu. Tutaj sprawdzamy to
    założenie na danych właściwych: czy któryś profil przekroczył
    `budget_fraction * slot` w `p99`. Reguła wyboru rate'u jest zamrożona
    i nie podlega korekcie po zobaczeniu danych, więc przekroczenie jest
    ostrzeżeniem dla interpretacji, nie unieważnieniem.

    ZMIANA v3: budżet bierzemy z sekcji `cells`, bo slot jest własnością komórki,
    nie rodziny. W K6b ta kontrola porównywała `p99` komórki z budżetem rodziny
    i przez to milczała o `W3_d3`, która pracowała na 91 % swojego slotu.
    """
    cells_json = rate_json.get("cells")
    if not isinstance(cells_json, dict):
        return []
    fraction = float(rate_json.get("budget_fraction", 0.5))
    warnings: list[str] = []
    worst: dict[tuple[str, str], float] = {}
    for row in rows:
        key = (row["case"], row["profile"])
        worst[key] = max(worst.get(key, 0.0), float(row["compute_p99_ns"]))
    for (case, profile), p99 in sorted(worst.items()):
        entry = cells_json.get(case)
        if not isinstance(entry, dict):
            continue
        slot = float(entry["slot_ns"])
        budget = fraction * slot
        if p99 > budget:
            warnings.append(
                f"{case}/{profile}: p99 = {p99 / 1000:.2f} µs > budget {budget / 1000:.2f} µs "
                f"({p99 / slot * 100:.0f} % of slot {slot / 1000:.2f} µs)"
            )
    return warnings


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
    parser.add_argument("--rate-json", type=Path, help="rate.json z kalibracji K6b.0")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows = load_runs([p.resolve() for p in args.runs])
    if not rows:
        raise SystemExit("ERROR: zero runs to analyse")

    rate_json: dict[str, object] = {}
    if args.rate_json and args.rate_json.is_file():
        rate_json = json.loads(args.rate_json.resolve().read_text(encoding="utf-8"))

    # Warunek unieważniający nr 6 (nowy w v2): rate identyczny w obrębie komórki.
    rate_problems, rate_checked, rates_by_case = rate_consistency(rows)
    if rate_checked == 0:
        rate_problems.append("zero cases checked — the rate control compared nothing")
    saturation_warnings = saturation_control(rows, rate_json)
    excluded_cases = rate_json.get("excluded_cases", []) if rate_json else []
    excluded_families = rate_json.get("excluded_families", []) if rate_json else []
    # Wykluczenia decyzja czlowieka sa rozdzielne od kalibracyjnych i nie wchodza do
    # tabeli kalibracyjnej. Raportowane osobno, zeby regula zliczania komorek nie
    # potknela sie o milczace pominiecie.
    decision_excluded_cases = rate_json.get("decision_excluded_cases", []) if rate_json else []

    # Warunek unieważniający nr 2: wynik musi być identyczny w obrębie komórki
    # i między profilami tego samego przypadku.
    checksum_problems: list[str] = []
    by_case: dict[str, set[str]] = {}
    for row in rows:
        by_case.setdefault(row["case"], set()).add(row["artifacts_sha256"])
    for case, digests in sorted(by_case.items()):
        if len(digests) != 1:
            checksum_problems.append(f"{case}: {len(digests)} different artifact checksums")

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
        "rate_problems": rate_problems,
        "rate_checked_cases": rate_checked,
        "rates_by_case": rates_by_case,
        "saturation_warnings": saturation_warnings,
        "excluded_cases": excluded_cases,
        "decision_excluded_cases": decision_excluded_cases,
        "excluded_families": excluded_families,
        "records": records,
        "secondary": secondary,
        "compile": compile_records,
    }
    (output / "analysis.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# K6b — ablation campaign result",
        "",
        f"- runs: {len(rows)}",
        f"- cases: {len(cases)}, profiles: {len(profiles)}",
        f"- primary metric: `{PRIMARY}`, practical significance threshold: {int(THRESHOLD * 100)}%",
        f"- bootstrap: {BOOTSTRAP_REPLICATES} replicates, seed {BOOTSTRAP_SEED}",
        f"- rate control: {rate_checked} cases checked, {len(rate_problems)} mismatches",
        f"- cells excluded by calibration: {len(excluded_cases)}",
        f"- cells excluded by human decision: {len(decision_excluded_cases)}",
        "",
        "## Primary metric — all cells",
        "",
        "| Case | rate | `STRUCT` [µs] | `ALGSTRUCT` [µs] | ratio | 95% CI | class | control |",
        "|---|---|---:|---:|---:|---|:--:|:--:|",
    ]
    for record in records:
        lines.append(
            f"| `{record['case']}` | {rates_by_case.get(str(record['case']), '—')} | "
            f"{float(record['median_baseline_ns']) / 1000:.2f} | "
            f"{float(record['median_treatment_ns']) / 1000:.2f} | {float(record['ratio']):.3f} | "
            f"[{float(record['ci_low']):.3f}; {float(record['ci_high']):.3f}] | **{record['class']}** | "
            f"{'neg' if record['negative_control'] else ''} |"
        )

    lines += ["", "## Cells excluded from Tier B by calibration", ""]
    if excluded_cases:
        lines += [
            "The cell does not fit the `0.5 · slot` budget even at `s = 1`. It is not",
            "dropped silently — the required rate is given, and its absence from the table",
            "above is part of the result.",
            "",
            "| Case | `p99` at `s=1` | slot (engine) | budget | required frequency |",
            "|---|---:|---:|---:|---:|",
        ]
        for entry in excluded_cases:
            lines.append(
                f"| `{entry['case']}` | {float(entry['p99_ns']) / 1000:.2f} µs | "
                f"{float(entry['slot_ns']) / 1000:.2f} µs | {float(entry['budget_ns']) / 1000:.2f} µs | "
                f"{float(entry['required_stream_hz']):.2f} Hz |"
            )
        if excluded_families:
            lines += ["", f"Families excluded in full: {', '.join(str(f) for f in excluded_families)}."]
    else:
        lines.append("None.")

    lines += ["", "## Cells excluded from Tier B by human decision", ""]
    if decision_excluded_cases:
        lines += [
            "Exclusion by decision is disjoint from calibration exclusion: the cell did",
            "fit the calibration budget but was taken out of Tier B by a separate",
            "decision. Its absence from the table above is part of the result, not an",
            "omission.",
            "",
            "| Case | family | reason |",
            "|---|---|---|",
        ]
        for entry in decision_excluded_cases:
            lines.append(f"| `{entry['case']}` | {entry['family']} | {entry['reason']} |")
    else:
        lines.append("None.")

    lines += ["", "## Saturation control (reported, not invalidating)", ""]
    if saturation_warnings:
        lines += [
            f"**{len(saturation_warnings)} cells** exceeded the `0.5 · slot` budget in `p99` despite",
            "a rate chosen on the `OFF`/`STRUCT` profiles. Calibration assumed that profiles",
            "with algebraic rewriting can only remove work; the cells below contradict that,",
            "and their interpretation must take it into account.",
            "",
        ]
        lines += [f"- {warning}" for warning in saturation_warnings]
    else:
        lines.append(
            "No cell exceeded the `0.5 · slot` budget in `p99` — the calibration assumption "
            "(profiles without rewriting are the most expensive) is confirmed on the real data."
        )

    lines += [
        "",
        "## Per-profile attribution (G14)",
        "",
        "| Case | " + " | ".join(f"`{p}` [µs]" for p in profiles) + " |",
        "|---|" + "---:|" * len(profiles),
    ]
    for record in records:
        values = []
        for profile in profiles:
            key = f"median_{profile}_ns"
            values.append(f"{float(record[key]) / 1000:.2f}" if key in record else "—")
        lines.append(f"| `{record['case']}` | " + " | ".join(values) + " |")

    lines += ["", "## Verdict", ""]
    lines.append(f"- cells (A) improvement: **{counts['A']}**" + (f" — {', '.join(improvements)}" if improvements else ""))
    lines.append(f"- cells (B) neutral: **{counts['B']}**")
    lines.append(f"- cells (C) regression: **{counts['C']}**" + (f" — {', '.join(regressions)}" if regressions else ""))
    lines.append("")
    if rate_problems:
        lines.append(
            "**CAMPAIGN INVALID (condition no. 6).** The rate is not identical within a cell: "
            + "; ".join(rate_problems)
            + ". Comparing profiles at different rates does not measure optimization, only rate."
        )
    elif control_violations:
        lines.append(
            f"**CAMPAIGN INVALID.** The negative control produced an effect: {', '.join(control_violations)}. "
            "The instrument measures something other than optimization; the remaining cells must not be reported as a result."
        )
    elif checksum_problems:
        lines.append(
            "**CAMPAIGN INVALID.** The result is not preserved across profiles: "
            + "; ".join(checksum_problems)
            + ". A speed-up with a different result is not a speed-up."
        )
    elif counts["A"] == 0:
        lines.append(
            "**No class (A) cell.** The benefit of R1/R2 is not visible in compute time at the "
            f"{int(THRESHOLD * 100)}% threshold. This is a result, not a failure of the campaign: the "
            "benefit remains structural (plan, tokens, buffers, materializations), and the paper is "
            "to describe it that way. The sentence 'the plan is smaller, but not faster' is publishable."
        )
    else:
        lines.append(f"**Improvement demonstrated in {counts['A']} cells.**")
        if external_improvement:
            lines.append(
                f"At least one belongs to an externally motivated family (W8): {', '.join(external_improvement)}."
            )
        else:
            lines.append(
                "**None belongs to an externally motivated family (W8)** — gap G7 remains open for "
                "the cost claim, and that is how it must be reported."
            )
        if regressions:
            lines.append(
                f"Regressions were also recorded: {', '.join(regressions)}. H4 requires checking whether "
                "they cancel the benefit."
            )

    if compile_records:
        lines += [
            "",
            "## Cost of normalization — compile time (Tier A)",
            "",
            "| Case | `STRUCT` [µs] | `ALGSTRUCT` [µs] | ratio | 95% CI | class |",
            "|---|---:|---:|---:|---|:--:|",
        ]
        for record in compile_records:
            lines.append(
                f"| `{record['case']}` | {float(record['median_baseline_ns']) / 1000:.2f} | "
                f"{float(record['median_treatment_ns']) / 1000:.2f} | {float(record['ratio']):.3f} | "
                f"[{float(record['ci_low']):.3f}; {float(record['ci_high']):.3f}] | {record['class']} |"
            )
        lines.append("")
        lines.append("Class (C) in this table is the **cost** of normalization, not a benefit.")

    lines += ["", "## Secondary metrics", ""]
    for metric, metric_records in secondary.items():
        classes = {"A": 0, "B": 0, "C": 0}
        for record in metric_records:
            if record.get("class"):
                classes[str(record["class"])] += 1
        lines.append(f"- `{metric}`: A={classes['A']}, B={classes['B']}, C={classes['C']}")

    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"cells: {len(records)}, A={counts['A']} B={counts['B']} C={counts['C']}; "
        f"rate checked on {rate_checked} cases, cells excluded: {len(excluded_cases)}"
    )
    if rate_problems or control_violations or checksum_problems:
        print("CAMPAIGN INVALID", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
