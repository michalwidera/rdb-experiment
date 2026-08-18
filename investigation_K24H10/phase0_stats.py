#!/usr/bin/env python3
"""Faza 0 K24/H10 — diagnostyka do wyprowadzenia (faza 1).

Trzy wielkosci, ktorych faza 1 potrzebuje, a ktorych bramka zgodnosci nie pokazuje:
  1. kolumna IZOLOWANA kampanii (step_c1 vs oracle_c1) — punkt wyjscia, liczby
     19,1% / 59,7% / 99,2% z REPORT.md K24d,
  2. rozklad okresu fazowego P = p+q — koszt przegladu i sensownosc progu,
  3. czlon WLASNY operatora = oracle_c1 - ceil(W_src*d_src/d_out) — to, co
     rachunek silnika przyklada do generycznego przeliczenia; jego zaleznosc od
     (p, q) rozstrzyga, czy istnieje postac O(1).
"""

import csv
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import sys

K24D = Path(__file__).resolve().parent.parent / "results_20260807_K24d"
sys.path.insert(0, str(K24D / "oracle"))
sys.path.insert(0, str(K24D))

from generator import generate            # noqa: E402
from plan import NTHETA, SOURCE, SUB, THETA, period_hint, reduced_ratio  # noqa: E402

CLASSES = (SUB, THETA, NTHETA)
COUNT = 10_010


def _ceil(value):
    value = Fraction(value)
    return -((-value.numerator) // value.denominator)


def main():
    for seed in (20260804, 20260807):
        ref = {}
        with (K24D / "raw" / f"campaign_seed{seed}.csv").open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                ref[(int(row["plan"]), row["node"])] = row
        corpus = generate(seed, COUNT)

        isolated = defaultdict(lambda: [0, 0])          # klasa -> [zgodnych, wszystkich]
        delta_iso = defaultdict(Counter)                # klasa -> rozklad (step_c1 - oracle_c1)
        periods = defaultdict(list)
        own = defaultdict(Counter)                      # klasa -> rozklad czlonu wlasnego
        own_by_q = defaultdict(lambda: defaultdict(Counter))

        for index, (_stratum, plan) in enumerate(corpus):
            for node in plan.nodes:
                if node.kind not in CLASSES:
                    continue
                row = ref[(index, node.name)]
                child = plan.by_name(node.children[0])
                w_src = 0 if child.kind == SOURCE else int(ref[(index, child.name)]["oracle_c1"])
                target = int(row["oracle_c1"])
                step = int(row["step_c1"])
                isolated[node.kind][1] += 1
                isolated[node.kind][0] += int(step == target)
                delta_iso[node.kind][step - target] += 1
                p, q = reduced_ratio(node.delta, child.delta)
                periods[node.kind].append(period_hint(node, [child]))
                generic = 0 if w_src <= 0 else _ceil(Fraction(w_src) * child.delta / node.delta)
                own[node.kind][target - generic] += 1
                own_by_q[node.kind][(p, q) if p + q <= 12 else "duze"][target - generic] += 1

        print(f"\n===== ziarno {seed}")
        for kind in CLASSES:
            good, total = isolated[kind]
            pers = sorted(periods[kind])
            print(f"\n-- {kind}: izolowana zgodnosc {good}/{total} = {100.0*good/total:.1f}%")
            print(f"   rozjazd izolowany (step_c1 - oracle_c1): {dict(sorted(delta_iso[kind].items()))}")
            print(f"   okres P=p+q: min {pers[0]}, mediana {pers[len(pers)//2]}, "
                  f"p95 {pers[int(0.95*len(pers))]}, max {pers[-1]}")
            print(f"   czlon wlasny (oracle_c1 - ceil(W_src*d_src/d_out)): {dict(sorted(own[kind].items()))}")
            if kind in (THETA, NTHETA, SUB):
                sample = {k: dict(sorted(v.items())) for k, v in sorted(own_by_q[kind].items(), key=str)[:8]}
                print(f"   czlon wlasny wg (p,q): {sample}")


if __name__ == "__main__":
    main()
