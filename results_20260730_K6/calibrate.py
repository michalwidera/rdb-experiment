#!/usr/bin/env python3
"""K6.0 — kalibracja rate'u pomiarowego. Uruchamiane na workerze.

Reguła jest zamrożona w README i przepisana tu dosłownie: kampania używa
**największego** `s` z drabiny `{36, 24, 12, 6}`, dla którego **każda** komórka
kalibracyjna spełnia

    p99(compute_ns) <= 0,5 * slot(phi)

gdzie `slot(phi)` jest nominalnym interwałem strumienia przeplotu. Porównanie
profili musi zachodzić w reżimie nienasyconym; w saturacji `compute_ns`
przestaje mierzyć koszt planu, a zaczyna mierzyć backlog.

**Wyniki kalibracji nie są wynikami kampanii.** Służą wyłącznie ustaleniu `s`
i zostają w `results/calibration.md`. Skrypt nie mierzy niczego, co trafia do
tabel artykułu, i nie wolno go użyć jako źródła metryki głównej.
"""
import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

LADDER = [36, 24, 12, 6]
CELLS = ["W2_Q32", "W3_d3", "W4_Q32", "W9_Q32"]
PROFILES = ["OFF", "STRUCT"]
REPS = 3
SLOTS = 1200
BUDGET_FRACTION = 0.5
WARMUP_FRACTION = 0.05
XR_CPU = "3"


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


def run_once(binary: Path, case_dir: Path, slots: int) -> dict[str, float]:
    with tempfile.TemporaryDirectory(prefix="rdb-k6-cal-", dir="/dev/shm") as root:
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
        completed = subprocess.run(
            ["taskset", "-c", XR_CPU, str(binary), "query.rql", "-r", "-k", "-m", str(slots), "-t", "-g", "study.toml"],
            cwd=work,
            env=environment,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=slots // 20 + 180,
            check=False,
        )
        if completed.returncode != 0:
            raise SystemExit(f"kalibracja: xretractor zakończył się kodem {completed.returncode}\n{completed.stderr[-800:]}")
        compute: list[int] = []
        with probe.open(encoding="utf-8") as handle:
            handle.readline()
            for line in handle:
                parts = line.strip().split(",")
                if len(parts) == 4:
                    compute.append(int(parts[1]))
        if not compute:
            raise SystemExit("kalibracja: sonda nie zawiera żadnego slotu")
        skip = int(len(compute) * WARMUP_FRACTION)
        compute = compute[skip:]
        return {
            "slots": len(compute),
            "median_ns": statistics.median(compute),
            "p99_ns": percentile(compute, 0.99),
            "max_ns": max(compute),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    code_repo = args.code_repo.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    lines = [
        "# K6.0 — kalibracja rate'u pomiarowego",
        "",
        "Reguła zamrożona w README: największe `s`, dla którego **każda** komórka",
        f"kalibracyjna spełnia `p99(compute_ns) <= {BUDGET_FRACTION} * slot(phi)`.",
        "",
        f"- komórki: {', '.join(CELLS)} × {', '.join(PROFILES)}",
        f"- powtórzeń na komórkę: {REPS}, slotów na przebieg: {SLOTS}",
        "",
        "| `s` | slot `phi` | budżet | przypadek | profil | p99 `compute_ns` | mieści się |",
        "|---:|---:|---:|---|---|---:|:--:|",
    ]
    chosen: int | None = None
    observations: list[dict[str, object]] = []
    checked = 0

    for scale in LADDER:
        slot_ns = float(Fraction(1, 15 * scale) * 1_000_000_000)
        budget_ns = BUDGET_FRACTION * slot_ns
        workloads = Path("/dev/shm/k6-calibration") / f"scale{scale}"
        if workloads.exists():
            shutil.rmtree(workloads)
        subprocess.run(
            [sys.executable, str(here / "generate.py"), "--output", str(workloads), "--scale", str(scale)],
            check=True,
            capture_output=True,
        )
        scale_ok = True
        for case in CELLS:
            for profile in PROFILES:
                binary = code_repo / f"build/K6-{profile}/src/retractor/xretractor"
                if not binary.is_file():
                    raise SystemExit(f"brak binarki profilu {profile}: {binary}")
                worst = 0.0
                for _ in range(REPS):
                    result = run_once(binary, workloads / case, SLOTS)
                    worst = max(worst, float(result["p99_ns"]))
                    checked += 1
                fits = worst <= budget_ns
                scale_ok = scale_ok and fits
                observations.append(
                    {"scale": scale, "case": case, "profile": profile, "p99_ns": worst, "budget_ns": budget_ns, "fits": fits}
                )
                lines.append(
                    f"| {scale} | {slot_ns / 1000:.2f} µs | {budget_ns / 1000:.2f} µs | `{case}` | "
                    f"{profile} | {worst / 1000:.2f} µs | {'tak' if fits else '**nie**'} |"
                )
        if scale_ok:
            chosen = scale
            break

    # Reguła zliczania: zero wykonanych przebiegów nie jest zgodnością.
    if checked == 0:
        raise SystemExit("kalibracja nie wykonała ani jednego przebiegu")

    if chosen is None:
        lines += ["", "## Wynik", "", "**Żadne `s` z drabiny nie spełnia reguły.** Kampania nie może wystartować:", ""]
        lines.append("drabina jest zamrożona, więc nie wolno dopisać do niej wolniejszego rate'u bez")
        lines.append("nowego katalogu wyników (R3). Decyzja należy do człowieka.")
        (output / "calibration.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (output / "rate.json").write_text(
            json.dumps({"scale": None, "checked_runs": checked, "observations": observations}, indent=2) + "\n",
            encoding="utf-8",
        )
        print("BLAD: żadne s z drabiny nie spełnia reguły", file=sys.stderr)
        return 1

    slot_ns = float(Fraction(1, 15 * chosen) * 1_000_000_000)
    lines += [
        "",
        "## Wynik",
        "",
        f"**Wybrane `s = {chosen}`** — `f_phi = {15 * chosen} Hz`, slot `phi = {slot_ns / 1000:.2f} µs`.",
        f"Przebiegów kalibracyjnych: {checked}. Wartości powyżej są maksimum z {REPS} powtórzeń.",
        "",
        "Wyniki kalibracji nie są wynikami kampanii i nie wchodzą do żadnej tabeli artykułu.",
    ]
    (output / "calibration.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "rate.json").write_text(
        json.dumps(
            {"scale": chosen, "f_phi_hz": 15 * chosen, "slot_phi_ns": slot_ns, "checked_runs": checked, "observations": observations},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wybrane scale={chosen} (f_phi={15 * chosen} Hz), przebiegów kalibracyjnych: {checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
