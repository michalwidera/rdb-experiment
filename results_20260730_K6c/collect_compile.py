#!/usr/bin/env python3
"""K6b.3 — Tier A: metryki kompilacji. Uruchamiane na workerze.

Czas kompilacji jest metryką czasową, więc mierzy go worker pod governorem
`performance`, na izolowanym rdzeniu 3, a nie nadzorca. Reżim RT nie jest
potrzebny — kompilacja nie ma pętli slotowej.

Zbierane w jednym przebiegu `xretractor <w>.rql -c` z `RDB_BENCH_PLAN`:
`COMPILE_NS` (z odjętym narzutem sondy), `PLAN bench`, `PLAN capacity`,
`REWRITE_APPLIED`.

Kolejność wszystkich trójek (przypadek, profil, powtórzenie) jest losowana
w obrębie powtórzenia, ziarnem zapisanym w kodzie — dryf termiczny nie może
sprzęgnąć się z profilem.

Tier A jest **niezależny od rate'u**: mierzy kompilację, nie pętlę slotową.
Dlatego w K6b nie podlega wyborowi rate'u per rodzina i jest generowany przy
jednym, zamrożonym `s = 6` (README v2). Użyty mnożnik trafia do kolumny `scale`
w `compile_runs.csv`, żeby ta niezależność była udokumentowana, a nie
domniemana.
"""
import argparse
import csv
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_counters import compile_case, parse_tsv  # noqa: E402

SEED = "20260730-tierA"
XR_CPU = 3

TIER_A_SCALE = 6

COLUMNS = [
    "case",
    "profile",
    "rep",
    "scale",
    "compile_ns",
    "probe_ns",
    "r1",
    "r2",
    "nodes_public",
    "nodes_substrates",
    "tokens_from",
    "tokens_fields",
    "capacity_streams",
    "capacity_sum",
    "capacity_max",
    "node_count",
    "nodes_sha256",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-repo", type=Path, required=True)
    parser.add_argument("--workloads", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reps", type=int, default=15)
    parser.add_argument("--build-prefix", default="K6")
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    code_repo = args.code_repo.resolve()
    workloads = args.workloads.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    profiles = parse_tsv(here / "profiles.tsv")
    index = json.loads((workloads / "index.json").read_text(encoding="utf-8"))
    scale = int(json.loads((workloads / "rates.json").read_text(encoding="utf-8"))["scale"])
    if scale != TIER_A_SCALE:
        raise SystemExit(f"Tier A jest zamrożony na s={TIER_A_SCALE}, a workloady mają s={scale}")

    binaries: dict[str, Path] = {}
    for profile in profiles:
        binary = code_repo / f"build/{args.build_prefix}-{profile['slug']}/src/retractor/xretractor"
        if not binary.is_file():
            raise SystemExit(f"brak binarki profilu {profile['profile']}: {binary}")
        binaries[str(profile["slug"])] = binary

    # `compile_case` uruchamia binarkę bez `taskset`, więc przypięcie robimy przez
    # własną afinność — potomkowie ją dziedziczą. Rdzeń 3 jest izolowany
    # (`isolcpus=3`), co nie blokuje jawnego ustawienia afinności.
    os.sched_setaffinity(0, {XR_CPU})
    if os.sched_getaffinity(0) != {XR_CPU}:
        raise SystemExit(f"nie udało się przypiąć do rdzenia {XR_CPU}")

    target = output / "compile_runs.csv"
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        executed = 0
        planned = 0
        for rep in range(1, args.reps + 1):
            runs = [(str(entry["case"]), str(profile["slug"])) for entry in index for profile in profiles]
            random.Random(f"{SEED}-{rep}").shuffle(runs)
            planned += len(runs)
            for case, slug in runs:
                record = compile_case(binaries[slug], workloads / case, code_repo)
                if record["status"] != "compiled":
                    raise SystemExit(f"{case}/{slug}: {record['status']} rc={record['returncode']}")
                writer.writerow(
                    [
                        case,
                        slug,
                        rep,
                        scale,
                        record["compile_ns"],
                        record["probe_ns"],
                        record["r1"],
                        record["r2"],
                        record["wyjscie_publiczne"],
                        record["wyjscie_substraty"],
                        record["wyjscie_tokeny_from"],
                        record["wyjscie_tokeny_pol"],
                        record["capacity_streams"],
                        record["capacity_sum"],
                        record["capacity_max"],
                        record["node_count"],
                        record["nodes_sha256"],
                    ]
                )
                executed += 1
            handle.flush()
            print(f"powtórzenie {rep}/{args.reps}: {executed} kompilacji", flush=True)

    # Reguła zliczania: liczba wykonanych kompilacji musi zgadzać się z planem.
    if executed != planned:
        raise SystemExit(f"wykonano {executed} kompilacji z {planned} zaplanowanych")
    if executed == 0:
        raise SystemExit("Tier A nie wykonał ani jednej kompilacji")
    print(f"Tier A: {executed} kompilacji w {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
