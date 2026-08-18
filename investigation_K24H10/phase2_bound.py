#!/usr/bin/env python3
"""Faza 2c K24/H10 — DOWODLIWY wariant zapasowy O(1) zamiast dzisiejszej reguly.

Lemat oszacowania. Jesli idx(n) <= n*r + c dla kazdego n, gdzie r = d_out/d_src,
to warunek dostepnosci spelnia

    f(n) = ceil((idx(n)+1+W_src)/r) - 1 - n  <=  ceil((c + 1 + W_src)/r) - 1,

bo skladnik n*r po podzieleniu przez r daje calkowite n, ktore wychodzi przed
sufit i kasuje sie z -n. Prawa strona nie zalezy od n — jest to oszacowanie O(1).

Stale c (z odwzorowan indeksu, d_out/d_src = p/q):
    `-`   idx(n) = ceil(n*p/q)                 -> c = (q-1)/q
    `Th`  idx(n) = n + ceil((n+1)*a/b)         -> c = (a+b-1)/b,  p/q = (a+b)/b
    `~Th` idx(n) = n + floor(n*a/b)            -> c = 0,          p/q = (a+b)/b

Ten skrypt sprawdza numerycznie, ze oszacowanie NIGDY nie zaniza (bramka) i jak
czesto jest ciasne — na przemiataniu poza korpusem i na calym korpusie K24.
"""

import csv
from fractions import Fraction
from math import gcd
from pathlib import Path
import sys

K24D = Path(__file__).resolve().parent.parent / "results_20260807_K24d"
sys.path.insert(0, str(K24D / "oracle"))
sys.path.insert(0, str(K24D))

from generator import generate                                   # noqa: E402
from phase2_form import _ceil, legacy_tail, new_tail             # noqa: E402
from phase2_threshold import cases, node_of                      # noqa: E402
from plan import NTHETA, SOURCE, SUB, THETA                       # noqa: E402

TAILS = (0, 1, 2, 3, 5, 8)


def bound(node, child, w_src):
    """Dowodliwe oszacowanie O(1) — wariant zapasowy powyzej progu przegladu."""
    ratio = node.delta / child.delta                 # r = p/q
    q = ratio.denominator
    if node.kind == SUB:
        c = Fraction(q - 1, q)
    elif node.kind == THETA:
        ab = node.delta / node.param                 # a/b
        a, b = ab.numerator, ab.denominator
        c = Fraction(a + b - 1, b)
    elif node.kind == NTHETA:
        c = Fraction(0)
    else:
        raise AssertionError(node.kind)
    return max(0, _ceil((c + 1 + w_src) / ratio) - 1)


def main():
    print("A. przemiatanie poza korpusem (q do 60)")
    stats = {SUB: [0, 0, 0], THETA: [0, 0, 0], NTHETA: [0, 0, 0]}   # [n, zanizen, ciasnych]
    for _label, node, child in cases():
        for w_src in TAILS:
            exact = new_tail(node, child, w_src, scan_limit=10**9)
            u = bound(node, child, w_src)
            s = stats[node.kind]
            s[0] += 1
            s[1] += int(u < exact)
            s[2] += int(u == exact)
    for kind in (SUB, THETA, NTHETA):
        n, under, tight = stats[kind]
        print(f"   {kind:7} n={n:7d}  ZANIZEN: {under:5d}  ciasnych: {tight:7d} ({100*tight/n:5.1f}%)")

    print("B. korpus K24d, ziarno 20260804 (oszacowanie wobec oracle'a)")
    ref = {}
    with (K24D / "raw" / "campaign_seed20260804.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            ref[(int(row["plan"]), row["node"])] = row
    corp = {SUB: [0, 0, 0], THETA: [0, 0, 0], NTHETA: [0, 0, 0]}
    for index, (_s, plan) in enumerate(generate(20260804, 10_010)):
        for node in plan.nodes:
            if node.kind not in corp:
                continue
            child = plan.by_name(node.children[0])
            w = 0 if child.kind == SOURCE else int(ref[(index, child.name)]["oracle_c1"])
            target = int(ref[(index, node.name)]["oracle_c1"])
            u = bound(node, child, w)
            legacy = legacy_tail(node, child, w)
            s = corp[node.kind]
            s[0] += 1
            s[1] += int(u < target)
            s[2] += int(u <= legacy)
    for kind in (SUB, THETA, NTHETA):
        n, under, better = corp[kind]
        print(f"   {kind:7} n={n:6d}  ZANIZEN wobec oracle'a: {under:5d}  "
              f"nie gorsze od dzisiejszej reguly: {better}/{n}")


if __name__ == "__main__":
    main()
