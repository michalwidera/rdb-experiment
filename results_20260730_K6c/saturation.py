#!/usr/bin/env python3
"""K6c.5 — punkt saturacji. Uruchamiane na workerze.

`W8` nie podlega drabinie rate'u (jej rate wynika z deklaracji źródła `rec205`),
więc przejście na rate wybierany per rodzina tego kroku nie dotknęło. Dotknęła
go natomiast druga zmiana v3: slot, wobec którego liczymy przekroczenia, jest
odczytywany z silnika, a nie wyliczany z rate'u źródła.

Pytanie: **czy `ALGSTRUCT` utrzymuje rate, którego `STRUCT` nie utrzymuje.**
To jest odpowiedź na „czy jest szybszy?" w idiomie §7.4 artykułu — sufit
wyznaczony przez kryterium co-slot, nie przez percentyl.

Zamrożone w README: `W8_Q32` (rodzina umotywowana zewnętrznie) × `{STRUCT,
ALGSTRUCT}` × `{360, 480, 540} Hz` × 5 powtórzeń. Metryka: udział slotów
z `compute_ns > slot`, gdzie `slot` jest interwałem strumienia MIERZONEGO
wg silnika — nie `1/rate` źródła (zmiana v3, patrz `probe_slot_ns`).

Rate zmienia się przez podstawienie w deklaracji źródła `rec205`, tak samo jak
w kampanii wydajnościowej §7 (`worker/run_study.sh`). Dane EKG są **kopiowane**
do `/dev/shm`, nie symlinkowane do repozytorium kodu (R2).
"""
import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stream_interval import measure_interval  # noqa: E402

CASE = "W8_Q32"
CLIENT_STREAM = "mon_000"
PROFILES = ["STRUCT", "ALGSTRUCT"]
RATES_HZ = [360, 480, 540]
REPS = 5
SLOTS = 3000
WARMUP_FRACTION = 0.05
XR_CPU = "3"
ECG_INPUTS = ["examples/ecg/rec205/rec205", "examples/ecg/rec205/bp_coef.txt", "examples/ecg/rec205/d_coef.txt"]


def run_once(binary: Path, query: str, code_repo: Path, slots: int) -> list[int]:
    with tempfile.TemporaryDirectory(prefix="rdb-k6-sat-", dir="/dev/shm") as root:
        work = Path(root) / "case"
        work.mkdir()
        (work / "temp").mkdir()
        (work / "query.rql").write_text(query, encoding="utf-8")
        for relative in ECG_INPUTS:
            shutil.copy(code_repo / relative, work / Path(relative).name)
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
            timeout=slots // 20 + 240,
            check=False,
        )
        if completed.returncode != 0:
            raise SystemExit(f"saturacja: xretractor kod {completed.returncode}\n{completed.stderr[-800:]}")
        compute: list[int] = []
        with probe.open(encoding="utf-8") as handle:
            handle.readline()
            for line in handle:
                parts = line.strip().split(",")
                if len(parts) == 4:
                    compute.append(int(parts[1]))
        if not compute:
            raise SystemExit("saturacja: sonda nie zawiera żadnego slotu")
        return compute[int(len(compute) * WARMUP_FRACTION) :]


def probe_slot_ns(binary: Path, query: str, code_repo: Path) -> float:
    """Slot strumienia MIERZONEGO przy danym rate źródła — wg silnika.

    ZMIANA v3: v1 i v2 liczyły tu `1/rate`, czyli slot ŹRÓDŁA `rec205`. Strumień
    mierzony (`mon_000`) powstaje z przeplotu i biegnie dwa razy gęściej, więc
    kryterium „`compute_ns > slot`" stosowano do slotu dwukrotnie za długiego
    i udział przekroczeń był zaniżony. To ten sam błąd, dla którego powstało
    K6c — poprawiony w tym samym miejscu, bo dotyczy tej samej wielkości.
    """
    with tempfile.TemporaryDirectory(prefix="rdb-k6-sat-slot-", dir="/dev/shm") as root:
        work = Path(root) / "case"
        work.mkdir()
        (work / "temp").mkdir()
        (work / "query.rql").write_text(query, encoding="utf-8")
        for relative in ECG_INPUTS:
            shutil.copy(code_repo / relative, work / Path(relative).name)
        return float(measure_interval(binary, work, CLIENT_STREAM)) * 1_000_000_000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    code_repo = args.code_repo.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    workloads = Path("/dev/shm/k6-saturation/workloads")
    if workloads.exists():
        shutil.rmtree(workloads)
    # Skala nie dotyczy W8 (rate ze zrodla), wiec generujemy z dowolnym s z drabiny.
    subprocess.run(
        [sys.executable, str(here / "generate.py"), "--output", str(workloads), "--scale", "36"],
        check=True,
        capture_output=True,
    )
    base_query = (workloads / CASE / "query.rql").read_text(encoding="utf-8")

    observations: list[dict[str, object]] = []
    executed = 0
    for rate in RATES_HZ:
        query = base_query.replace("1/360", f"1/{rate}")
        if rate != 360 and query == base_query:
            raise SystemExit(f"nie udało się podstawić rate'u {rate} Hz w zapytaniu")
        slot_nominal_ns = 1_000_000_000 / rate
        slot_ns = None
        for profile in PROFILES:
            binary = code_repo / f"build/K6-{profile}/src/retractor/xretractor"
            if not binary.is_file():
                raise SystemExit(f"brak binarki profilu {profile}: {binary}")
            if slot_ns is None:
                slot_ns = probe_slot_ns(binary, query, code_repo)
            overruns: list[float] = []
            medians: list[float] = []
            for _ in range(REPS):
                compute = run_once(binary, query, code_repo, SLOTS)
                overruns.append(sum(1 for value in compute if value > slot_ns) / len(compute))
                medians.append(statistics.median(compute))
                executed += 1
            observations.append(
                {
                    "rate_hz": rate,
                    "profile": profile,
                    "slot_ns": slot_ns,
                    "slot_nominal_ns": slot_nominal_ns,
                    "client_stream": CLIENT_STREAM,
                    "slot_from": "silnik",
                    "overrun_median": statistics.median(overruns),
                    "overrun_max": max(overruns),
                    "overrun_min": min(overruns),
                    "compute_median_ns": statistics.median(medians),
                    "reps": REPS,
                }
            )

    if executed == 0:
        raise SystemExit("saturacja nie wykonała ani jednego przebiegu")

    lines = [
        "# K6.5 — punkt saturacji",
        "",
        f"Zamrożone: `{CASE}` × {', '.join(PROFILES)} × {RATES_HZ} Hz × {REPS} powtórzeń,",
        f"{SLOTS} slotów na przebieg. Metryka: udział slotów z `compute_ns > slot`.",
        "",
        f"Przebiegów: {executed}.",
    ]
    # Siatka rate'ow jest zamrozona; jesli cala lezy powyzej punktu, raport musi to
    # powiedziec wprost, zamiast obiecywac punkt, ktorego nie zlokalizowano.
    if all(float(record["overrun_median"]) > 0 for record in observations):
        scale = statistics.median(float(r["slot_ns"]) * float(r["rate_hz"]) for r in observations)
        worst = max(float(r["compute_median_ns"]) for r in observations)
        lines += [
            "",
            "**Punkt saturacji nie został zlokalizowany — leży poniżej całej siatki.** Każdy",
            "rate w siatce przekracza budżet w obu profilach, więc metryka stoi pod sufitem",
            "i nie różnicuje ani rate'u, ani profilu. Iloczyn `slot · rate` jest w siatce stały",
            f"({scale / 1e6:.0f}·10⁶ ns·Hz); zestawiony z największą medianą `compute_ns`",
            f"({worst / 1000:.2f} µs) daje punkt przy ok. {scale / worst:.0f} Hz źródła — to",
            "ekstrapolacja z pomiarów powyżej saturacji, nie pomiar punktu.",
        ]
    lines += [
        "",
        f"Slot dotyczy strumienia `{CLIENT_STREAM}` i pochodzi z silnika. Kolumna „wg rate'u”",
        "pokazuje wartość, którą wstawiała v2 — czyli slot źródła, dwukrotnie za długi.",
        "",
        "| rate źródła | slot (silnik) | slot wg rate'u | profil | `compute_ns` mediana | przekroczenia mediana | min–max |",
        "|---:|---:|---:|---|---:|---:|---|",
    ]
    for record in observations:
        lines.append(
            f"| {record['rate_hz']} Hz | {float(record['slot_ns']) / 1000:.2f} µs | "
            f"{float(record['slot_nominal_ns']) / 1000:.2f} µs | {record['profile']} | "
            f"{float(record['compute_median_ns']) / 1000:.2f} µs | {float(record['overrun_median']) * 100:.2f}% | "
            f"{float(record['overrun_min']) * 100:.2f}–{float(record['overrun_max']) * 100:.2f}% |"
        )

    lines += ["", "## Odczyt", ""]
    for rate in RATES_HZ:
        by_profile = {str(r["profile"]): float(r["overrun_median"]) for r in observations if r["rate_hz"] == rate}
        struct, alg = by_profile.get("STRUCT", 0.0), by_profile.get("ALGSTRUCT", 0.0)
        if struct > 0 and alg == 0:
            verdict = "**`ALGSTRUCT` utrzymuje ten rate, `STRUCT` nie.**"
        elif struct == 0 and alg == 0:
            verdict = "oba profile utrzymują ten rate — punkt poniżej saturacji"
        elif struct > 0 and alg > 0:
            verdict = "oba profile przekraczają budżet — punkt powyżej saturacji obu"
        else:
            verdict = "**`STRUCT` utrzymuje, `ALGSTRUCT` nie — regresja sufitu**"
        lines.append(f"- {rate} Hz: {verdict}")

    (output / "saturation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "saturation.json").write_text(
        json.dumps({"case": CASE, "reps": REPS, "slots": SLOTS, "runs": executed, "observations": observations}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"saturacja: {executed} przebiegów, {len(observations)} komórek")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
