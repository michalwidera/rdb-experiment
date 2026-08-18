#!/usr/bin/env python3
"""Faza 2 K24/H10 — czy oszacowanie O(1) jest DOKLADNE na calym korpusie?

Jesli tak, przeglad okresu fazowego jest wylacznie narzedziem dowodu, a do
silnika idzie postac zamknieta O(1):

    W = max(0, ceil( (c + 1 + W_src) * d_src/d_out ) - 1)

    `-`   c = (q-1)/q          (q = mianownik skroconego d_out/d_src)
    `Th`  c = (a+b-1)/b        (a/b = skrocone d_out/param)
    `~Th` c = 0

Dowod dokladnosci: idx(n) = n*r + e(n), wiec f(n) = ceil((e(n)+1+W_src)/r) - 1
(skladnik n*r/r = n wychodzi przed sufit i kasuje sie z -n). Maksimum f po n to
maksimum po e(n), a kres e(n) = c jest OSIAGANY, bo reszty przebiegaja wszystkie
klasy modulo mianownik (gcd = 1 po skroceniu).
"""

import csv
from pathlib import Path
import sys

K24D = Path(__file__).resolve().parent.parent / "results_20260807_K24d"
sys.path.insert(0, str(K24D / "oracle"))
sys.path.insert(0, str(K24D))

from generator import generate                        # noqa: E402
from phase2_bound import bound                        # noqa: E402
from phase2_form import new_tail                      # noqa: E402
from plan import NTHETA, SOURCE, SUB, THETA           # noqa: E402

CLASSES = (SUB, THETA, NTHETA)


def main():
    for seed in (20260804, 20260807):
        ref = {}
        with (K24D / "raw" / f"campaign_seed{seed}.csv").open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                ref[(int(row["plan"]), row["node"])] = row
        stat = {k: [0, 0, 0, 0] for k in CLASSES}     # [n, ==oracle, ==przeglad, zanizen]
        for index, (_s, plan) in enumerate(generate(seed, 10_010)):
            for node in plan.nodes:
                if node.kind not in CLASSES:
                    continue
                child = plan.by_name(node.children[0])
                w = 0 if child.kind == SOURCE else int(ref[(index, child.name)]["oracle_c1"])
                target = int(ref[(index, node.name)]["oracle_c1"])
                closed = bound(node, child, w)
                scan = new_tail(node, child, w, scan_limit=10**9)
                s = stat[node.kind]
                s[0] += 1
                s[1] += int(closed == target)
                s[2] += int(closed == scan)
                s[3] += int(closed < target)
        print(f"== ziarno {seed}")
        for kind in CLASSES:
            n, ok, same, under = stat[kind]
            print(f"   {kind:7} n={n:5d}  postac O(1) == oracle: {ok:5d} ({100*ok/n:5.1f}%)  "
                  f"== przeglad: {same:5d}  ZANIZEN: {under}")


if __name__ == "__main__":
    main()
