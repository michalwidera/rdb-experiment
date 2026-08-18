#!/usr/bin/env python3
"""Faza 0 planu K24/H10 — falsyfikacja hipotezy scalajacej H-scal.

Bez silnika, bez workera, bez generowania danych. Korpus odtwarzany
deterministycznie z ziarna (generator.py z K24d, bajtowo bez zmian),
odniesieniem jest zamrozona kolumna `oracle_c1` z kampanii K24d.

H-scal: dla klas SUB, THETA i NTHETA ogon dokladny daje przeglad JEDNEGO
okresu fazowego warunku dostepnosci

    W = max(0, max_{n in [O, O+P)} [ ceil((idx(n)+1+W_src)*d_src/d_out) - 1 - n ])

gdzie idx(n) jest odwzorowaniem indeksu klasy (model.dependencies), O poczatkiem
logicznym wezla, a P = p+q okresem fazowym (plan.period_hint). Ogony skladowych
brane z oracle'a — atrybucja izolowana, jak kolumna `step_c1` kampanii.

Kandydat NIE jest jeszcze postacia zamknieta: sprawdzamy tu wylacznie, czy jeden
okres wystarcza. Postac zamknieta wyprowadza faza 1.
"""

import argparse
import csv
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
import sys

K24D = Path(__file__).resolve().parent.parent / "results_20260807_K24d"
sys.path.insert(0, str(K24D / "oracle"))
sys.path.insert(0, str(K24D))

import model as M           # noqa: E402
from generator import generate   # noqa: E402
from plan import NTHETA, SOURCE, SUB, THETA, period_hint  # noqa: E402

CLASSES = (SUB, THETA, NTHETA)
COUNT = 10_010


def _ceil(value):
    return -((-Fraction(value).numerator) // Fraction(value).denominator)


def candidate_tail(node, child, source_tail, origin, window):
    """Kandydat H-scal dla jednego wezla, przy zadanym oknie przegladu."""
    best = 0
    for n in range(origin, origin + window):
        deps = M.dependencies(node, [child], n)
        required = None
        for _name, index, _delay in deps:
            if index < 0:
                return None          # slot przed poczatkiem logicznym — nie nasz przypadek
            moment = (Fraction(index) + 1 + source_tail) * child.delta
            if required is None or moment > required:
                required = moment
        value = _ceil(required / node.delta) - (n + 1)
        if value > best:
            best = value
    return best


def load_reference(path):
    """(plan, node) -> wiersz kampanii; tylko kolumny, ktorych uzywamy."""
    ref = {}
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            ref[(int(row["plan"]), row["node"])] = {
                "kind": row["kind"],
                "oracle_c1": int(row["oracle_c1"]),
                "oracle_origin": int(row["oracle_origin"]),
                "engine_tail": int(row["engine_tail"]),
                "agree_c1": int(row["agree_c1"]),
                "step_c1": int(row["step_c1"]),
            }
    return ref


def run(seed, reference, out_rows):
    ref = load_reference(reference)
    corpus = generate(seed, COUNT)
    stats = defaultdict(lambda: defaultdict(int))
    for index, (_stratum, plan) in enumerate(corpus):
        for node in plan.nodes:
            if node.kind not in CLASSES:
                continue
            key = (index, node.name)
            row = ref.get(key)
            if row is None:
                stats[node.kind]["brak_w_kampanii"] += 1
                continue
            child = plan.by_name(node.children[0])
            source_tail = 0 if child.kind == SOURCE else ref[(index, child.name)]["oracle_c1"]
            origin = row["oracle_origin"]
            period = period_hint(node, [child])
            got = candidate_tail(node, child, source_tail, origin, period)
            got4 = candidate_tail(node, child, source_tail, origin, 4 * period)
            target = row["oracle_c1"]
            kind = stats[node.kind]
            kind["wezlow"] += 1
            kind["okres_stabilny"] += int(got == got4)
            kind["zgodnych"] += int(got == target)
            if got < target:
                kind["zanizen"] += 1
            elif got > target:
                kind["zawyzen"] += 1
            if row["agree_c1"] == 1:
                kind["silnik_zgodny"] += 1
                kind["silnik_zgodny_zachowany"] += int(got == target)
            if got != target or got != got4:
                out_rows.append({
                    "seed": seed, "plan": index, "node": node.name, "kind": node.kind,
                    "period": period, "origin": origin, "source_tail": source_tail,
                    "candidate_P": got, "candidate_4P": got4,
                    "oracle_c1": target, "engine_tail": row["engine_tail"],
                    "step_c1": row["step_c1"],
                })
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, action="append", required=True)
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent / "raw"))
    args = parser.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    misses = []
    report = {}
    for seed in args.seed:
        reference = K24D / "raw" / f"campaign_seed{seed}.csv"
        report[seed] = run(seed, reference, misses)

    if misses:
        fields = list(misses[0].keys())
        with (outdir / "phase0_misses.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(misses)

    for seed, stats in report.items():
        print(f"\n== ziarno {seed}")
        print(f"{'klasa':8} {'wezlow':>7} {'zgodnych':>10} {'zanizen':>8} "
              f"{'zawyzen':>8} {'okres OK':>9} {'silnik zgodny -> zachowany':>28}")
        for kind in CLASSES:
            s = stats[kind]
            n = s["wezlow"]
            if not n:
                continue
            pct = 100.0 * s["zgodnych"] / n
            print(f"{kind:8} {n:7d} {s['zgodnych']:7d} ({pct:5.1f}%) {s['zanizen']:8d} "
                  f"{s['zawyzen']:8d} {s['okres_stabilny']:9d} "
                  f"{s['silnik_zgodny_zachowany']:12d} / {s['silnik_zgodny']:<12d}")
    print(f"\nwierszy rozjazdu: {len(misses)}")


if __name__ == "__main__":
    main()
