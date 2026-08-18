#!/usr/bin/env python3
"""Faza 2c K24/H10 — kontrola progu przegladu, POZA korpusem.

Powyzej progu postac docelowa wraca do dzisiejszej reguly silnika. Wariant
zapasowy jest dopuszczalny tylko wtedy, gdy NIGDY nie zanizna ogona: zanizenie
to rekord wyemitowany przed okresleniem zaleznosci, zawyzenie to slot
opoznienia. Korpus K24 ma q <= 5, wiec dla wiekszych q jest to na razie
ZALOZENIE — ten skrypt je sprawdza celowanym przemiataniem.

Dodatkowo kontrola wlasna przegladu: maksimum po oknie [0, q) musi rownac sie
maksimum po oknie [0, 20q) — jesli nie, lemat okresowosci jest zly.
"""

from fractions import Fraction
from math import gcd
from types import SimpleNamespace
from pathlib import Path
import sys

K24D = Path(__file__).resolve().parent.parent / "results_20260807_K24d"
sys.path.insert(0, str(K24D / "oracle"))
sys.path.insert(0, str(K24D))

from phase2_form import _ceil, index_map, legacy_tail, new_tail   # noqa: E402
from plan import NTHETA, SOURCE, SUB, THETA                        # noqa: E402

LIMIT_Q = 60
TAILS = (0, 1, 2, 3, 5, 8)


def node_of(kind, delta, param=None):
    return SimpleNamespace(kind=kind, delta=Fraction(delta), param=param and Fraction(param), name="n")


def long_scan(node, child, w_src, factor=20):
    idx = index_map(node, child)
    ratio = node.delta / child.delta
    q = ratio.denominator
    best = 0
    for n in range(factor * q + 1):
        best = max(best, _ceil((Fraction(idx(n)) + 1 + w_src) * child.delta / node.delta) - (n + 1))
    return best


def cases():
    """Trojki (opis, wezel, skladowa) o duzym q, poza zakresem korpusu."""
    for q in range(2, LIMIT_Q + 1):
        for p in range(q, 4 * q + 1):
            if gcd(p, q) != 1:
                continue
            # `-`: d_src = 1, d_out = p/q >= 1 (cel nie moze byc szybszy od zrodla)
            yield (f"SUB p/q={p}/{q}", node_of(SUB, Fraction(p, q)), node_of(SOURCE, 1))
    for a in range(1, LIMIT_Q + 1):
        for b in range(1, LIMIT_Q + 1):
            if gcd(a, b) != 1:
                continue
            src = Fraction(a * b, a + b)
            # `Theta`: skladowa lewa (interwal a), param = interwal prawej (b); q = b
            yield (f"THETA a/b={a}/{b}", node_of(THETA, a, b), node_of(SOURCE, src))
            # `~Theta`: skladowa prawa (interwal b), param = interwal lewej (a); q = a
            yield (f"NTHETA a/b={a}/{b}", node_of(NTHETA, b, a), node_of(SOURCE, src))


def main():
    stats = {SUB: [0, 0, 0], THETA: [0, 0, 0], NTHETA: [0, 0, 0]}   # [przypadkow, zanizen zapasowego, niestabilnych]
    worst = {SUB: None, THETA: None, NTHETA: None}
    qmax = {SUB: 0, THETA: 0, NTHETA: 0}
    for label, node, child in cases():
        ratio = node.delta / child.delta
        q = ratio.denominator
        qmax[node.kind] = max(qmax[node.kind], q)
        for w_src in TAILS:
            exact = new_tail(node, child, w_src, scan_limit=10**9)
            stable = long_scan(node, child, w_src)
            # Galaz deklaracyjna ma sens WYLACZNIE przy w_src == 0 — deklaracja
            # ma ogon zerowy z definicji. Sparowanie jej z w_src > 0 daje
            # rozjazdy, ktore w zadnym planie nie moga wystapic.
            variants = [False] if w_src else [False, True]
            for declared in variants:
                fallback = legacy_tail(node, child, w_src, declared=declared)
                s = stats[node.kind]
                s[0] += 1
                if exact != stable:
                    s[2] += 1
                if fallback < exact:
                    s[1] += 1
                    if worst[node.kind] is None:
                        worst[node.kind] = (f"{label} declared={declared}", w_src, exact, fallback)
    print(f"przemiatanie: q do {LIMIT_Q}, ogony skladowej {TAILS}")
    for kind in (SUB, THETA, NTHETA):
        n, under, unstable = stats[kind]
        print(f"  {kind:7} przypadkow {n:7d}  max q {qmax[kind]:3d}  "
              f"ZANIZEN wariantu zapasowego: {under:6d}  niestabilnosci okresu: {unstable}")
        if worst[kind]:
            label, w, exact, fallback = worst[kind]
            print(f"           pierwszy przypadek zanizenia: {label}, W_src={w}, "
                  f"dokladny {exact}, zapasowy {fallback}")


if __name__ == "__main__":
    main()
