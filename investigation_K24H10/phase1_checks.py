#!/usr/bin/env python3
"""Faza 1 K24/H10 — kontrole wyprowadzenia na korpusie K24d.

Bez silnika, bez workera. Trzy pytania, na ktore faza 1 musi odpowiedziec, zanim
postac trafi do C++:

  K1. Czy okres TESNY T = q (mianownik zredukowanego d_out/d_src) wystarcza,
      zamiast P = p+q uzytego w fazie 0?
  K2. Czy przeglad moze startowac od ZERA zamiast od poczatku logicznego O?
      Silnik liczy ogon w `computeStartupLatency()` i nie ma prawa zalezec od
      kolejnosci wobec `computeLogicalOrigin()` — tak samo jak `#`.
  K3. Czy galaz `sourceDeclared` w `SubtractStartupLatency()` jest po przejsciu
      na przeglad jeszcze do czegokolwiek potrzebna? Podpopulacja: wezly `-`
      o skladowej bedacej DEKLARACJA; zestawienie z obiema konwencjami
      dostepnosci (C1 i C2) oraz z faktycznym ogonem silnika.
"""

import csv
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import sys

K24D = Path(__file__).resolve().parent.parent / "results_20260807_K24d"
sys.path.insert(0, str(K24D / "oracle"))
sys.path.insert(0, str(K24D))

import model as M                          # noqa: E402
from generator import generate             # noqa: E402
from plan import NTHETA, SOURCE, SUB, THETA, period_hint, reduced_ratio  # noqa: E402

CLASSES = (SUB, THETA, NTHETA)
COUNT = 10_010


def _ceil(value):
    value = Fraction(value)
    return -((-value.numerator) // value.denominator)


def scan(node, child, w_src, start, window):
    best = 0
    for n in range(start, start + window):
        required = None
        for _name, index, _delay in M.dependencies(node, [child], n):
            moment = (Fraction(index) + 1 + w_src) * child.delta
            if required is None or moment > required:
                required = moment
        best = max(best, _ceil(required / node.delta) - (n + 1))
    return best


def main():
    for seed in (20260804, 20260807):
        ref = {}
        with (K24D / "raw" / f"campaign_seed{seed}.csv").open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                ref[(int(row["plan"]), row["node"])] = row

        k1 = defaultdict(lambda: [0, 0])      # klasa -> [zgodnych T=q z P=p+q, wszystkich]
        k2 = defaultdict(lambda: [0, 0])      # klasa -> [start 0 == start O, wszystkich]
        k3 = Counter()
        k3_detail = defaultdict(Counter)

        for index, (_stratum, plan) in enumerate(generate(seed, COUNT)):
            for node in plan.nodes:
                if node.kind not in CLASSES:
                    continue
                row = ref[(index, node.name)]
                child = plan.by_name(node.children[0])
                w_src = 0 if child.kind == SOURCE else int(ref[(index, child.name)]["oracle_c1"])
                origin = int(row["oracle_origin"])
                p, q = reduced_ratio(node.delta, child.delta)
                big = period_hint(node, [child])

                tight_at_origin = scan(node, child, w_src, origin, q)
                broad_at_origin = scan(node, child, w_src, origin, big)
                tight_at_zero = scan(node, child, w_src, 0, q)

                k1[node.kind][1] += 1
                k1[node.kind][0] += int(tight_at_origin == broad_at_origin)
                k2[node.kind][1] += 1
                k2[node.kind][0] += int(tight_at_zero == tight_at_origin)

                if node.kind == SUB and child.kind == SOURCE:
                    c1, c2 = int(row["oracle_c1"]), int(row["oracle_c2"])
                    k3["wezlow"] += 1
                    k3["kandydat==C1"] += int(tight_at_zero == c1)
                    k3["kandydat==C2"] += int(tight_at_zero == c2)
                    k3["C1==C2"] += int(c1 == c2)
                    k3["silnik==C1"] += int(int(row["engine_tail"]) == c1)
                    k3["silnik==C2"] += int(int(row["engine_tail"]) == c2)
                    k3_detail["silnik-kandydat"][int(row["engine_tail"]) - tight_at_zero] += 1
                    k3_detail["C2-C1"][c2 - c1] += 1

        print(f"\n===== ziarno {seed}")
        print("K1 (okres tesny T=q wobec P=p+q) i K2 (start od zera wobec startu od origin):")
        for kind in CLASSES:
            print(f"  {kind:7} K1 {k1[kind][0]}/{k1[kind][1]}    K2 {k2[kind][0]}/{k2[kind][1]}")
        print(f"K3 (wezly `-` o skladowej-deklaracji): {dict(k3)}")
        print(f"   rozklad (silnik - kandydat): {dict(sorted(k3_detail['silnik-kandydat'].items()))}")
        print(f"   rozklad (C2 - C1):           {dict(sorted(k3_detail['C2-C1'].items()))}")


if __name__ == "__main__":
    main()
