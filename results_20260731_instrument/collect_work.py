#!/usr/bin/env python3
"""Zbiera cechy sondy E4 (praca na slot) dla komorek kampanii K6c.

Cechy sa DETERMINISTYCZNE: liczba odwiedzin elementow okna wynika z planu
i geometrii okna, nie z zegara. Dlatego zbieranie nie wymaga rytualu kampanii
pomiarowej (reboot, governor, izolacja rdzenia) -- wymaga tylko, zeby plan byl
ten sam. Cele `p99` pochodza z K6c i nie sa tu mierzone ponownie (README,
sekcja "Odstepstwo").

POMIAR ROZNICOWY. Praca w pierwszych slotach jest mniejsza, bo strumienie sa
jeszcze w swoich ogonach (`query::startupLatency`). Zamiast zgadywac, ile
slotow odrzucic, kazda komorka jest uruchamiana DWA razy -- na `SLOTS_LOW`
i `SLOTS_HIGH` slotow -- a praca na slot liczona jako iloraz roznic:

    praca_na_slot = (W(SLOTS_HIGH) - W(SLOTS_LOW)) / (SLOTS_HIGH - SLOTS_LOW)

Ogon startowy wchodzi identycznie do obu przebiegow i skraca sie w odejmowaniu.
Roznica ujemna oznaczalaby niedeterminizm licznika i jest bledem, nie szumem.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

SLOTS_LOW = 200
SLOTS_HIGH = 400
XR_CPU = "3"
STAGE_ROOT = "/dev/shm"

WORK_PATTERN = re.compile(
    r"WORK agse: okna=(\d+) elementy=(\d+) odczyty=(\d+)\s+"
    r"eval: wywolania=(\d+) tokeny=(\d+)\s+hash: wybory=(\d+)\s+add: scalenia=(\d+)"
)
WORK_FIELDS = ["agse_windows", "agse_elements", "agse_reads", "eval_calls", "eval_tokens", "hash_picks", "add_merges"]


def stage(case_dir: Path, code_repo: Path, work: Path) -> None:
    """Ten sam uklad katalogu przebiegu, ktorego uzywa K6c (check_counters.stage).

    Skopiowany, a nie zaimportowany: `results_20260730_K6c` jest katalogiem
    ZAMKNIETYM i to badanie nie moze zalezec od tego, ze nikt go nie ruszy.
    """
    work.mkdir(parents=True)
    (work / "temp").mkdir()
    shutil.copy(case_dir / "query.rql", work / "query.rql")
    external = case_dir / "external_data.txt"
    if external.is_file():
        for relative in external.read_text(encoding="utf-8").split():
            shutil.copy(code_repo / relative, work / Path(relative).name)
    for extra in sorted(case_dir.glob("*.txt")):
        if extra.name != "external_data.txt":
            shutil.copy(extra, work / extra.name)


def run_once(binary: Path, case_dir: Path, code_repo: Path, slots: int) -> dict[str, int]:
    """Jeden przebieg instrumentowany; zwraca liczniki E4 (sumy procesowe)."""
    with tempfile.TemporaryDirectory(prefix="rdb-e4-", dir=STAGE_ROOT) as root:
        work = Path(root) / "case"
        stage(case_dir, code_repo, work)
        (work / "study.toml").write_text("[scheduling]\nrt_priority = 50\n", encoding="utf-8")
        environment = os.environ.copy()
        environment["RDB_BENCH_WORK"] = "1"
        environment["RDB_BENCH_PLAN"] = "1"
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
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
            raise SystemExit(f"E4: xretractor zakonczyl sie kodem {completed.returncode}\n{completed.stderr[-800:]}")
        match = WORK_PATTERN.search(completed.stderr)
        if not match:
            raise SystemExit(
                "E4: brak wiersza WORK w wyjsciu silnika -- binarka nie jest zbudowana z RDB_BENCH_PROBE "
                f"albo zmienna RDB_BENCH_WORK nie zadziałala.\nstderr:\n{completed.stderr[-800:]}"
            )
        return dict(zip(WORK_FIELDS, (int(g) for g in match.groups())))


def collect_cell(binary: Path, case_dir: Path, code_repo: Path) -> dict[str, float]:
    low = run_once(binary, case_dir, code_repo, SLOTS_LOW)
    high = run_once(binary, case_dir, code_repo, SLOTS_HIGH)
    span = SLOTS_HIGH - SLOTS_LOW
    per_slot: dict[str, float] = {}
    for field in WORK_FIELDS:
        delta = high[field] - low[field]
        if delta < 0:
            raise SystemExit(
                f"E4: licznik {field} zmalal miedzy przebiegami ({low[field]} -> {high[field]}). "
                "Licznik nie jest deterministyczny -- ZATRZYMANIE, nie korekta."
            )
        per_slot[field] = delta / span
    return per_slot


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True, help="xretractor z RDB_BENCH_PROBE=ON")
    parser.add_argument("--code-repo", type=Path, required=True)
    parser.add_argument("--k6c-root", type=Path, required=True, help="katalog kampanii K6c (tylko do odczytu)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    k6c = args.k6c_root.resolve()
    rate_json = json.loads((k6c / "results" / "rate.json").read_text(encoding="utf-8"))

    # Komorki i skale bierzemy DOKLADNIE takie, jakie ma cel -- zaden nowy przypadek
    # nie wchodzi do zbioru, bo dla niego nie byloby celu z K6c.
    wanted: dict[int, list[dict[str, str]]] = {}
    for observation in rate_json["observations"]:
        if not observation.get("counters"):
            continue
        wanted.setdefault(int(observation["scale"]), []).append(
            {"case": str(observation["case"]), "family": str(observation["family"])}
        )
    if not wanted:
        raise SystemExit("E4: zero obserwacji z licznikami w rate.json -- nie ma czego zbierac")

    records: list[dict[str, object]] = []
    for scale in sorted(wanted):
        workloads = Path("/dev/shm/e4-instrument") / f"scale{scale}"
        if workloads.exists():
            shutil.rmtree(workloads)
        subprocess.run(
            [sys.executable, str(k6c / "generate.py"), "--output", str(workloads), "--scale", str(scale)],
            check=True,
            capture_output=True,
        )
        for entry in wanted[scale]:
            case_dir = workloads / entry["case"]
            if not case_dir.is_dir():
                raise SystemExit(f"E4: brak wygenerowanej komorki {entry['case']} dla scale={scale}")
            per_slot = collect_cell(args.binary, case_dir, args.code_repo)
            records.append({"case": entry["case"], "family": entry["family"], "scale": scale, **per_slot})
            print(f"{entry['case']:10s} s={scale:<3d} elementy/slot={per_slot['agse_elements']:.2f}", flush=True)

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "work.json").write_text(
        json.dumps(
            {
                "slots_low": SLOTS_LOW,
                "slots_high": SLOTS_HIGH,
                "method": "roznicowy: (W(high)-W(low))/(high-low), ogon startowy skraca sie",
                "records": records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"E4: zebrano {len(records)} komorko-skal", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
