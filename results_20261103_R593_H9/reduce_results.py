#!/usr/bin/env python3
"""Deterministyczny eksport wejsc `mechanism.tsv` i `timing.tsv` dla K26.

Eksporter nie wykonuje pomiarow i nie interpretuje H9. Laczy zamrozone zrzuty
planu z licznikami P6 oraz redukuje surowe sondy P8 do dokladnych schematow,
ktorych wymaga ``verdict.py``. Kazdy brak, duplikat albo dodatkowa komorka jest
bledem -- nie wolno po cichu uzupelniac niepelnej macierzy.
"""

import argparse
import csv
import re
import statistics
import sys
from pathlib import Path

import mechanism_table
from verdict import MECHANISM_COLUMNS, TIMING_COLUMNS

HERE = Path(__file__).resolve().parent
FAMILIES = ["F9-R2", "F9-R1", "F9-X"]
FAMILY_FILE = {family: family.replace("-", "_") for family in FAMILIES}
PROFILES = ["DEFAULT", "NO_R2_CANON", "NO_R1_FACTOR", "NO_R1_NO_R2"]
Q_GRID = [1, 2, 4, 8, 16, 32]

SUMMARY_COLUMNS = [
    "family", "profile", "q", "block", "order", "compute_median_ns",
    "compute_p99_ns", "slot_ns", "lost_records", "probe_rows",
    "public_appends", "temp_before_millic", "temp_after_millic",
]

RDB_LOGICAL = re.compile(
    r"^LOGICAL substrat: dopisania=(\d+) nadpisania=(\d+) bajty=(\d+)\s+"
    r"publiczne: dopisania=(\d+) nadpisania=(\d+) bajty=(\d+)", re.M
)
RDB_WORK = re.compile(
    r"^WORK .*?eval: wywolania=(\d+) tokeny=(\d+)\s+hash: wybory=(\d+)\s+"
    r"add: scalenia=(\d+)", re.M
)
FLINK_LOGICAL = re.compile(
    r"^LOGICAL substrat: zapisy=(\d+) bajty=(\d+)\s+publiczne: rekordy=(\d+)", re.M
)
FLINK_WORK = re.compile(
    r"^WORK eval: wywolania=(\d+) tokeny=(\d+)\s+hash: wybory=(\d+)\s+"
    r"add: scalenia=(\d+)", re.M
)


class ReductionError(RuntimeError):
    pass


def read_single_match(path, pattern, label):
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = pattern.findall(text)
    if len(matches) != 1:
        raise ReductionError(f"{path}: oczekiwano jednego wiersza {label}, znaleziono {len(matches)}")
    return tuple(int(value) for value in matches[0])


def read_tsv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in columns})


def indexed_rows(path, key_columns):
    rows, out = read_tsv(path), {}
    for row in rows:
        key = tuple(row[column] for column in key_columns)
        if key in out:
            raise ReductionError(f"{path}: zdublowany klucz {key}")
        out[key] = row
    return out


def rdb_instances(cell):
    """Liczba instancji badanego podplanu, ktore plan MATERIALIZUJE (§7.2).

    Jedna definicja dla wszystkich rodzin: liczba substratow wewnetrznych,
    niezalezna od nazwy wezla. Mniej = wiecej wspoldzielenia, wiec straznik
    `instances(DEFAULT) <= instances(ablacja)` czyta ja w te sama strone, co
    predeklaracja.

    K26v2/D7: wersja poprzednia liczyla w F9-R1 wylacznie substraty nazwane
    `STREAM_HASH_*`. Taki wezel powstaje z konstrukcji dopiero przy R1 ON, wiec
    ablacja raportowala 0 zamiast swoich 2-3 substratow i straznik odwracal sie,
    uniewazniajac iteracje mimo poprawnego planu.
    """
    return len(cell["substrates"])


def costly_evals(family, public_appends, add_merges):
    """Licznik operatora, na ktorym rodzina wykonuje kosztowny program pola."""
    return public_appends if family == "F9-R1" else add_merges


def mechanism_rows(rdb_dir, flink_dir, plans_dir, rql_dir, flink_curve, flink_work_curve):
    rows = []
    for family in FAMILIES:
        plan_family = FAMILY_FILE[family]
        for q in Q_GRID:
            plan = f"{plan_family}_Q{q}"
            for profile in PROFILES:
                cell_dir = rdb_dir / profile / plan
                logical = read_single_match(cell_dir / "cell.counters", RDB_LOGICAL, "LOGICAL")
                work = read_single_match(cell_dir / "cell.counters", RDB_WORK, "WORK")
                shape = mechanism_table.cell(
                    plans_dir / profile / f"{plan}.plan",
                    plans_dir / profile / f"{plan}.stderr",
                    rql_dir / f"{plan}.rql",
                )
                rows.append({
                    "family": family,
                    "system": "RDB",
                    "profile": profile,
                    "q": q,
                    "instances": rdb_instances(shape),
                    "stream_selects": len(shape["selects"]),
                    "substrates": len(shape["substrates"]),
                    "r1": shape["r1"],
                    "r2": shape["r2"],
                    "substrate_bytes": logical[2],
                    "public_appends": logical[3],
                    # F9-R2/F9-X wykonuja program na wezle STREAM_ADD. W F9-R1
                    # kwadrat jest programem publicznego monitora; rodzine i tak
                    # rozstrzyga osobny licznik hashPicks.
                    "work_costly_evals": costly_evals(family, logical[3], work[3]),
                    "work_hash_picks": work[2],
                    "work_add_merges": work[3],
                })

    curves = indexed_rows(flink_curve, ("family", "variant", "q"))
    work_curves = indexed_rows(flink_work_curve, ("family", "variant", "q"))
    for family in FAMILIES:
        plan_family = FAMILY_FILE[family]
        for q in Q_GRID:
            for variant in ("natural", "manual"):
                key = (family, variant, str(q))
                if key not in curves or key not in work_curves:
                    raise ReductionError(f"brak krzywej Flinka {key}")
                curve = curves[key]
                run = flink_dir / f"{plan_family}_{variant}_q{q}" / "job.out"
                logical = read_single_match(run, FLINK_LOGICAL, "LOGICAL")
                work = read_single_match(run, FLINK_WORK, "WORK")
                rows.append({
                    "family": family,
                    "system": "FLINK",
                    "profile": variant.upper(),
                    "q": q,
                    "instances": int(curve["subplan_nodes"]),
                    "stream_selects": 0,
                    "substrates": int(curve["subplan_nodes"]),
                    "r1": 0,
                    "r2": 0,
                    "substrate_bytes": logical[1],
                    "public_appends": logical[2],
                    "work_costly_evals": costly_evals(family, logical[2], work[3]),
                    "work_hash_picks": work[2],
                    "work_add_merges": work[3],
                })

    expected = len(FAMILIES) * len(Q_GRID) * (len(PROFILES) + 2)
    if len(rows) != expected:
        raise ReductionError(f"mechanism: {len(rows)} wierszy, oczekiwano {expected}")
    return sorted(rows, key=lambda row: (
        FAMILIES.index(row["family"]), row["q"], row["system"], row["profile"]
    ))


def percentile99(values):
    """Ta sama regula co w analizatorze P7: indeks int(0.99*n), bez interpolacji."""
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(0.99 * len(ordered)))]


def summarize_probe(path):
    if path.suffix != ".csv":
        raise ReductionError(f"{path}: sonda musi byc CSV")
    compute, iterations = [], []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["iter", "compute_ns", "wake_lag_ns", "e2e_ns"]:
            raise ReductionError(f"{path}: nieprawidlowy naglowek sondy")
        for row in reader:
            try:
                iterations.append(int(row["iter"]))
                compute.append(int(row["compute_ns"]))
            except (TypeError, ValueError) as exc:
                raise ReductionError(f"{path}: nieprawidlowy wiersz sondy") from exc
    if not compute:
        raise ReductionError(f"{path}: pusta sonda")
    expected_iterations = list(range(len(iterations)))
    if iterations != expected_iterations:
        raise ReductionError(f"{path}: iter nie jest ciagly od zera")
    return {
        "compute_median_ns": int(statistics.median(compute)),
        "compute_p99_ns": percentile99(compute),
        "probe_rows": len(compute),
    }


def timing_rows(raw_dir, blocks_path):
    expected = {}
    for row in read_tsv(blocks_path):
        key = (row["family"], row["profile"], int(row["q"]), int(row["block"]))
        if key in expected:
            raise ReductionError(f"blocks.tsv: zdublowana komorka {key}")
        expected[key] = int(row["order"])

    found = {}
    for path in sorted(raw_dir.rglob("summary.tsv")):
        if "warmup" in path.parts:
            continue
        rows = read_tsv(path)
        if len(rows) != 1 or list(rows[0]) != SUMMARY_COLUMNS:
            raise ReductionError(f"{path}: oczekiwano jednego wiersza o zamrozonym schemacie")
        row = rows[0]
        key = (row["family"], row["profile"], int(row["q"]), int(row["block"]))
        if key in found:
            raise ReductionError(f"surowe wyniki: zdublowana komorka {key}")
        if key not in expected:
            raise ReductionError(f"surowe wyniki: dodatkowa komorka {key}")
        if int(row["order"]) != expected[key]:
            raise ReductionError(f"surowe wyniki: zla kolejnosc {key}")
        recomputed = summarize_probe(path.parent / "slot.csv")
        for column in ("compute_median_ns", "compute_p99_ns", "probe_rows"):
            if int(row[column]) != recomputed[column]:
                raise ReductionError(f"{path}: {column} nie zgadza sie z surowa sonda")
        if int(row["slot_ns"]) <= 0 or int(row["lost_records"]) < 0:
            raise ReductionError(f"{path}: nieprawidlowy slot albo liczba zgubionych rekordow")
        found[key] = row

    missing = sorted(set(expected) - set(found))
    if missing:
        raise ReductionError(f"surowe wyniki: brak {len(missing)} komorek, pierwsza {missing[0]}")

    out = []
    for key in sorted(found, key=lambda item: (FAMILIES.index(item[0]), item[2], item[3], item[1])):
        row = found[key]
        out.append({
            "family": row["family"],
            "profile": row["profile"],
            "q": row["q"],
            "block": row["block"],
            "compute_median_ns": row["compute_median_ns"],
            "compute_p99_ns": row["compute_p99_ns"],
            "slot_ns": row["slot_ns"],
            "lost_records": row["lost_records"],
        })
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    mechanism = sub.add_parser("mechanism")
    mechanism.add_argument("--rdb", type=Path, required=True)
    mechanism.add_argument("--flink", type=Path, required=True)
    mechanism.add_argument("--plans", type=Path, default=HERE / "corpus_validation" / "plans")
    mechanism.add_argument("--rql", type=Path, default=HERE / "rql")
    mechanism.add_argument("--flink-curve", type=Path, default=HERE / "flink" / "results" / "flink_q_curve.tsv")
    mechanism.add_argument("--flink-work-curve", type=Path,
                           default=HERE / "flink" / "results" / "flink_work_q_curve.tsv")
    mechanism.add_argument("--out", type=Path, required=True)
    timing = sub.add_parser("timing")
    timing.add_argument("--raw", type=Path, required=True)
    timing.add_argument("--blocks", type=Path, default=HERE / "blocks.tsv")
    timing.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.out.exists():
            raise ReductionError(f"odmowa nadpisania istniejacego {args.out}")
        if args.command == "mechanism":
            rows = mechanism_rows(args.rdb, args.flink, args.plans, args.rql,
                                  args.flink_curve, args.flink_work_curve)
            write_tsv(args.out, MECHANISM_COLUMNS, rows)
        else:
            rows = timing_rows(args.raw, args.blocks)
            write_tsv(args.out, TIMING_COLUMNS, rows)
    except (OSError, KeyError, ValueError, ReductionError) as exc:
        print(f"BLAD: {exc}", file=sys.stderr)
        return 2
    print(f"OK: {args.out} — {len(rows)} wierszy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
