#!/usr/bin/env python3
"""Faza 2b K24/H10 — kontrola zasiegu zmiany, bez tautologii.

Pytanie: czy poza trzema naprawianymi klasami cokolwiek sie rusza z INNEGO
powodu niz dziedziczenie po naprawionym dziecku?

Test: wezel klasy innej niz {SUB, THETA, NTHETA}, w ktorego PODDRZEWIE nie ma
ani jednego wezla tych klas, musi miec ogon propagowany co do jednego slota
rowny zamrozonej kolumnie `replica_tail` kampanii K24d (pelna propagacja starej
repliki). Wezly z takim potomkiem moga sie zmienic — i wtedy sprawdzamy, czy
zmiana idzie w strone oracle'a, a nie od niego.
"""

import csv
from collections import defaultdict
from pathlib import Path
import sys

K24D = Path(__file__).resolve().parent.parent / "results_20260807_K24d"
sys.path.insert(0, str(K24D / "oracle"))
sys.path.insert(0, str(K24D))

from generator import generate                       # noqa: E402
from phase2_form import NEW, propagated              # noqa: E402
from plan import SOURCE                              # noqa: E402

COUNT = 10_010


def touched(plan):
    """Nazwy wezlow, w ktorych poddrzewie jest choc jeden wezel naprawianej klasy."""
    mark = {}
    for node in plan.nodes:                          # porzadek topologiczny
        mark[node.name] = node.kind in NEW or any(mark[c] for c in node.children)
    return mark


def main():
    for seed in (20260804, 20260807):
        ref = {}
        with (K24D / "raw" / f"campaign_seed{seed}.csv").open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                ref[(int(row["plan"]), row["node"])] = row

        clean = defaultdict(lambda: [0, 0])      # kind -> [identycznych z replica_tail, n]
        inherited = defaultdict(lambda: [0, 0, 0, 0])  # kind -> [n, zmienionych, ku oracle, od oracle]

        for index, (_stratum, plan) in enumerate(generate(seed, COUNT)):
            tails = propagated(plan)
            mark = touched(plan)
            for node in plan.nodes:
                if node.kind == SOURCE or node.kind in NEW:
                    continue
                row = ref[(index, node.name)]
                old = int(row["replica_tail"])
                new = tails[node.name]
                target = int(row["oracle_c1"])
                if not mark[node.name]:
                    clean[node.kind][0] += int(new == old)
                    clean[node.kind][1] += 1
                else:
                    stat = inherited[node.kind]
                    stat[0] += 1
                    if new != old:
                        stat[1] += 1
                        stat[2] += int(new == target and old != target)
                        stat[3] += int(old == target and new != target)

        print(f"\n===== ziarno {seed}")
        print("A. wezly BEZ naprawianej klasy w poddrzewie — musi byc identycznie:")
        for kind in sorted(clean):
            good, n = clean[kind]
            flag = "OK" if good == n else "ROZJAZD"
            print(f"   {kind:8} {good:6d}/{n:<6d}  {flag}")
        print("B. wezly z naprawiona klasa w poddrzewie — zmiana wolno tylko ku oracle'owi:")
        for kind in sorted(inherited):
            n, changed, to_oracle, from_oracle = inherited[kind]
            print(f"   {kind:8} n={n:6d}  zmienionych {changed:6d}  ku oracle {to_oracle:6d}  "
                  f"OD oracle {from_oracle:6d}")


if __name__ == "__main__":
    main()
