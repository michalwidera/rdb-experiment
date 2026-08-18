#!/usr/bin/env python3
"""Faza 2 K24/H10 — postac DOCELOWA wobec oracle'a, na korpusie K24d.

Bez silnika, bez workera. Roznica wobec fazy 0: liczona jest juz postac w tej
formie, w jakiej trafi do C++ — przeglad okna [0, q) po odwzorowaniach
`Subtract` / `Div` / `Mod` z `SOperations.hpp`, z progiem przejscia na wariant
zapasowy. Sprawdzane sa dwie rzeczy naraz:

  2a. zgodnosc IZOLOWANA (regula wezla z ogonami skladowych z oracle'a) — musi
      byc 100% dla trzech klas naprawianych i pozostac 100% dla szesciu innych,
  2b. zasieg zmiany — wartosc wezla klasy INNEJ niz trzy naprawiane nie ma prawa
      roznic sie od zamrozonej kolumny `step_c1` kampanii K24d ani o jeden slot,
  ---- dodatkowo, jako przewidywanie dla fazy 4 ----
      zgodnosc PROPAGOWANA (ogon liczony przez caly plan, tak jak robi to
      silnik): jesli kazda regula jest dokladna przy dokladnych ogonach
      skladowych, to zlozenie tez musi byc dokladne — czyli 100%.
"""

import csv
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
import sys

K24D = Path(__file__).resolve().parent.parent / "results_20260807_K24d"
sys.path.insert(0, str(K24D / "oracle"))
sys.path.insert(0, str(K24D))

import closedform as C                     # noqa: E402
from generator import generate             # noqa: E402
from plan import NTHETA, SOURCE, SUB, THETA, reduced_ratio  # noqa: E402

NEW = (SUB, THETA, NTHETA)
COUNT = 10_010
SCAN_LIMIT = 100_000          # odpowiednik kHashPhaseScanLimit


def _ceil(value):
    value = Fraction(value)
    return -((-value.numerator) // value.denominator)


def _floor(value):
    value = Fraction(value)
    return value.numerator // value.denominator


def index_map(node, child):
    """Odwzorowanie indeksu — te same funkcje, ktore SOperations.hpp ma juz dzis."""
    if node.kind == SUB:                                    # Subtract(d_src, d_out, n)
        if child.delta == node.delta:
            return lambda n: n
        return lambda n: _ceil(Fraction(n) * node.delta / child.delta)
    if node.kind == THETA:                                  # Div(d_out, param, n)
        return lambda n: n + _ceil(Fraction(n + 1) * node.delta / node.param)
    if node.kind == NTHETA:                                 # Mod(param, d_out, n)
        return lambda n: n + _floor(Fraction(n) * node.delta / node.param)
    raise AssertionError(node.kind)


def legacy_tail(node, child, w_src, declared=None):
    """Wariant zapasowy = dzisiejsza regula silnika.

    `declared` rozdzielone od `child.kind`, bo w przemiataniu 2c trzeba umiec
    zapytac o obie galezie osobno. Domyslnie jak w silniku: galaz deklaracyjna
    dla skladowej bedacej DECLARE. Kombinacja `declared=True` z `w_src > 0` jest
    NIEMOZLIWA w planie (deklaracja ma ogon zerowy) i nie wolno jej testowac."""
    generic = 0 if w_src <= 0 else _ceil(Fraction(w_src) * child.delta / node.delta)
    if node.kind == THETA:
        return generic + 1
    if node.kind == NTHETA:
        return generic
    ratio = node.delta / child.delta
    q = ratio.denominator
    phase = Fraction(q - 1, q)
    if child.kind == SOURCE if declared is None else declared:
        return _floor(phase / ratio) + 1
    return _ceil((Fraction(w_src) + phase) / ratio)


def new_tail(node, child, w_src, scan_limit=SCAN_LIMIT):
    """Postac docelowa: przeglad jednego okresu fazowego q, z progiem."""
    _p, q = reduced_ratio(node.delta, child.delta)
    if q > scan_limit:
        return legacy_tail(node, child, w_src)
    idx = index_map(node, child)
    best = 0
    for n in range(q):
        best = max(best, _ceil((Fraction(idx(n)) + 1 + w_src) * child.delta / node.delta) - (n + 1))
    return best


def propagated(plan):
    """Ogon calego planu przy nowej regule trzech klas i starej regule pozostalych."""
    tails = {}
    for node in plan.nodes:
        if node.kind == SOURCE:
            tails[node.name] = 0
            continue
        if node.kind in NEW:
            child = plan.by_name(node.children[0])
            tails[node.name] = new_tail(node, child, tails[child.name])
        else:
            # Regula niezmieniona — liczona replika kampanii, z dotychczasowych ogonow.
            filler = defaultdict(int, tails)
            tails[node.name] = C.evaluate(plan, given_tails=filler)[node.name]
    return tails


def main():
    for seed in (20260804, 20260807):
        ref = {}
        with (K24D / "raw" / f"campaign_seed{seed}.csv").open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                ref[(int(row["plan"]), row["node"])] = row

        iso = defaultdict(lambda: [0, 0, 0])     # kind -> [zgodnych, zanizen, n]
        scope = defaultdict(lambda: [0, 0])      # kind -> [identycznych ze step_c1, n]
        prop = defaultdict(lambda: [0, 0, 0])

        for index, (_stratum, plan) in enumerate(generate(seed, COUNT)):
            prop_tails = propagated(plan)
            for node in plan.nodes:
                if node.kind == SOURCE:
                    continue
                row = ref[(index, node.name)]
                target = int(row["oracle_c1"])

                if node.kind in NEW:
                    child = plan.by_name(node.children[0])
                    w_src = 0 if child.kind == SOURCE else int(ref[(index, child.name)]["oracle_c1"])
                    value = new_tail(node, child, w_src)
                else:
                    value = int(row["step_c1"])
                    scope[node.kind][0] += int(value == int(row["step_c1"]))
                    scope[node.kind][1] += 1

                iso[node.kind][0] += int(value == target)
                iso[node.kind][1] += int(value < target)
                iso[node.kind][2] += 1

                got = prop_tails[node.name]
                prop[node.kind][0] += int(got == target)
                prop[node.kind][1] += int(got < target)
                prop[node.kind][2] += 1

        print(f"\n===== ziarno {seed}")
        print(f"{'klasa':8} {'izolowana':>22} {'zanizen':>8} {'propagowana':>22} {'zanizen':>8}")
        for kind in sorted(iso):
            g, u, n = iso[kind]
            pg, pu, pn = prop[kind]
            print(f"{kind:8} {g:6d}/{n:<6d} ({100*g/n:5.1f}%) {u:8d} "
                  f"{pg:6d}/{pn:<6d} ({100*pg/pn:5.1f}%) {pu:8d}")


if __name__ == "__main__":
    main()
