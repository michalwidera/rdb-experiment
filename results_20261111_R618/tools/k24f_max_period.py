"""Punkt 7 #618: najwieksze p+q wezlow `#` korpusu K24e (generator.py z pinu rdb-experiment).

p/q = skrocone delta_A/delta_B skladowych, jak period w HashStartupLatency() pinu e389edd3
(kHashPhaseScanLimit = 100000). Delty skladowych sprawdzane z kolumna `delta` zapisanego raw/*.csv.
Uzycie: python3 -I k24e_max_period.py <katalog K24e> <ziarno> [csv]
"""
import csv
import sys
from fractions import Fraction

root, seed = sys.argv[1], int(sys.argv[2])
raw = sys.argv[3] if len(sys.argv) > 3 else None
sys.path[:0] = [root, root + "/oracle"]
from generator import generate  # noqa: E402
from plan import HASH, period_hint  # noqa: E402

deltas = {}
if raw:
    with open(raw, newline="") as f:
        for r in csv.DictReader(f):
            deltas[(int(r["plan"]), r["node"])] = Fraction(r["delta"])

import generator as G
corpus = generate(seed, 10_010, strata=G.STRATA_WITH_WINDOW)
hash_nodes, best, best_all, checked, mismatch = 0, (0, None), (0, None), 0, 0
over = 0
for index, (_, plan) in enumerate(corpus):
    names = {n.name: n for n in plan.nodes}
    for n in plan.nodes:
        kids = [names[c] for c in n.children]
        ph = period_hint(n, kids)
        if ph > best_all[0]:
            best_all = (ph, (index, n.name, n.kind))
        if n.kind != HASH:
            continue
        hash_nodes += 1
        a, b = Fraction(kids[0].delta), Fraction(kids[1].delta)
        if raw:
            for k in kids:
                key = (index, k.name)
                if key in deltas:
                    checked += 1
                    mismatch += deltas[key] != Fraction(k.delta)
        r = a / b
        period = r.numerator + r.denominator
        over += period > 100_000
        if period > best[0]:
            best = (period, (index, n.name, f"{a}", f"{b}"))
print(f"seed {seed}: plany {len(corpus)}, wezly # {hash_nodes}, max p+q (#) {best[0]} w {best[1]}, "
      f"p+q > 100000: {over}; max period_hint (wszystkie klasy) {best_all[0]} w {best_all[1]}; "
      f"delty skladowych wobec raw: sprawdzone {checked}, rozne {mismatch}")
