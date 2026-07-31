#!/usr/bin/env python3
"""Pomiar badania higienicznego 1bb2d2c.

Dla każdej pary (komórka, profil) wykonuje `--reps` powtórzeń po obu stronach
(PRZED = e1c13bb, PO = 1bb2d2c), NAPRZEMIENNIE, i zapisuje wynik do
`results/runs.csv`.

Przeplot zamiast odstępu. Protokół R8 kampanii wymaga reboota między badaniami;
przy 240 przebiegach jest to niestosowalne, więc dryf termiczny kontrolujemy
kolejnością: w powtórzeniach parzystych pierwsza idzie strona PRZED, w
nieparzystych PO. Dzięki temu monotoniczny dryf maszyny rozkłada się równo na
obie strony zamiast obciążać tę mierzoną później. To świadome odstępstwo od R8
i jest zapisane w predeklaracji.

Klient `xqry` jest STAŁY po obu stronach — różni się wyłącznie binarka silnika.
Bez tego porównywalibyśmy dwie aparatury naraz.
"""

import argparse
import csv
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "results_20260730_K6c"))
from check_counters import stage  # noqa: E402

# Komórki z zamkniętych badań Tier B, obie o duty < 100 % (patrz README).
CELLS = {
    "W2_Q32": {"stream": "w2_out_000", "slots": 1440},
    "W3_d3": {"stream": "w3_out_000", "slots": 3240},
}
PROFILES = ("STRUCT", "ALGSTRUCT")  # mianownik i licznik ilorazu r(c)
SIDES = ("PRZED", "PO")
SCALE = 12
XR_CPU = "3"
BG_CPUS = "0-2"

STUDY_TOML = "[scheduling]\nrt_priority = 50\n"


def percentile(values: list[int], q: float) -> int:
    ordered = sorted(values)
    index = min(int(len(ordered) * q), len(ordered) - 1)
    return int(ordered[index])


def read_probe(path: Path) -> tuple[list[int], list[int]]:
    """Zwraca (compute_ns, e2e_ns) z pliku sondy."""
    compute, e2e = [], []
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            compute.append(int(row["compute_ns"]))
            e2e.append(int(row["e2e_ns"]))
    return compute, e2e


def measure(binary: Path, case_dir: Path, code_repo: Path, work: Path, cell: dict) -> dict:
    """Jeden przebieg: silnik na izolowanym rdzeniu + klient na pozostałych."""
    if work.exists():
        shutil.rmtree(work)
    # Staging przez wspólny `stage()`, nie własną kopią: pisanie staging'u od
    # nowa było źródłem defektu katalogu przebiegu w kampanii (4772eb4).
    stage(case_dir, code_repo, work)
    (work / "study.toml").write_text(STUDY_TOML, encoding="utf-8")

    probe = work / "probe.csv"
    env = dict(os.environ)
    env.update(RDB_BENCH_CSV=str(probe), RDB_BENCH_PLAN="1", RDB_BENCH_MATERIALIZE="1")

    engine_log = (work / "engine.log").open("w", encoding="utf-8")
    engine = subprocess.Popen(
        ["timeout", "--kill-after=10s", "300s", "taskset", "-c", XR_CPU, str(binary),
         "query.rql", "-r", "-k", "-m", str(cell["slots"]), "-t", "-g", "study.toml"],
        cwd=work, env=env, stdout=engine_log, stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL)

    time.sleep(2)  # ten sam protokół dołączania, co w kampanii
    client_err = (work / "client.err").open("w", encoding="utf-8")
    client = subprocess.Popen(
        ["taskset", "-c", BG_CPUS, "xqry", "-s", cell["stream"], "-r"],
        cwd=work, stdout=subprocess.DEVNULL, stderr=client_err, stdin=subprocess.DEVNULL)

    engine_rc = engine.wait()
    engine_log.close()
    try:
        client_rc = client.wait(timeout=30)
    except subprocess.TimeoutExpired:
        client.terminate()
        client_rc = client.wait(timeout=10)
    client_err.close()

    if engine_rc != 0:
        raise RuntimeError(f"silnik zakonczyl sie kodem {engine_rc}; log: {work / 'engine.log'}")
    if not probe.is_file():
        raise RuntimeError(f"brak pliku sondy: {probe}")

    compute, e2e = read_probe(probe)
    if len(compute) < cell["slots"] - 1:
        raise RuntimeError(f"sonda ma {len(compute)} slotow, oczekiwano >= {cell['slots'] - 1}")

    return {
        "compute_median_ns": int(statistics.median(compute)),
        "compute_p99_ns": percentile(compute, 0.99),
        "e2e_p50_ns": int(statistics.median(e2e)),
        "e2e_p99_ns": percentile(e2e, 0.99),
        "slots": len(compute),
        "client_rc": client_rc,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-repo", required=True)
    parser.add_argument("--work-root", default="/dev/shm/h217")
    parser.add_argument("--reps", type=int, default=30)
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent / "results" / "runs.csv"))
    args = parser.parse_args()

    code_repo = Path(args.code_repo).resolve()
    work_root = Path(args.work_root)
    here = Path(__file__).resolve().parent

    binaries = {
        (side, profile): code_repo / "build" / f"H217-{side}-{profile}" / "src" / "retractor" / "xretractor"
        for side in SIDES for profile in PROFILES
    }
    for key, path in binaries.items():
        if not path.is_file():
            print(f"BLAD: brak binarki {key}: {path}", file=sys.stderr)
            return 1

    workloads = work_root / "workloads"
    if work_root.exists():
        shutil.rmtree(work_root)
    work_root.mkdir(parents=True)
    subprocess.run([sys.executable, str(here.parent / "results_20260730_K6c" / "generate.py"),
                    "--output", str(workloads), "--scale", str(SCALE)],
                   check=True, stdout=subprocess.DEVNULL)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["cell", "profile", "side", "rep", "compute_median_ns", "compute_p99_ns",
              "e2e_p50_ns", "e2e_p99_ns", "slots", "client_rc"]

    done = 0
    total = len(CELLS) * len(PROFILES) * args.reps * len(SIDES)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for cell_name, cell in CELLS.items():
            case_dir = workloads / cell_name
            for profile in PROFILES:
                for rep in range(args.reps):
                    # Przeplot: kolejność stron zależy od parzystości powtórzenia.
                    order = SIDES if rep % 2 == 0 else tuple(reversed(SIDES))
                    for side in order:
                        result = measure(binaries[(side, profile)], case_dir, code_repo,
                                         work_root / "run", cell)
                        writer.writerow({"cell": cell_name, "profile": profile,
                                         "side": side, "rep": rep, **result})
                        handle.flush()
                        done += 1
                        print(f"[{done}/{total}] {cell_name} {profile} {side} r{rep} "
                              f"compute_med={result['compute_median_ns']} client_rc={result['client_rc']}",
                              flush=True)

    print(f"zapisano {done} przebiegow do {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
