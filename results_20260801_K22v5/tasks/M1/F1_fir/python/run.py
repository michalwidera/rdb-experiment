#!/usr/bin/env python3
"""Harness Pythona dla F1 — POZA rdzeniem, nieliczony przez metryki.

Wczytuje zamrożone wejścia, woła rdzeń i zapisuje strumień kanoniczny K22.
Nie ma tu znaczników CORE_BEGIN/CORE_END, więc `measure.py` tego nie policzy.
"""
import argparse
import sys
from pathlib import Path

from core import run


def load_ints(path):
    return [int(tok) for tok in Path(path).read_text(encoding="utf-8").split()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--source2", required=True)
    ap.add_argument("--coef", required=True)
    ap.add_argument("--slots", type=int, required=True)
    ap.add_argument("--family", default="F1")
    ap.add_argument("--variant", default="base")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    samples = load_ints(args.source)
    coef = load_ints(args.coef)
    if len(samples) < args.slots:
        raise SystemExit(f"BLAD APARATURY: {len(samples)} probek, zadano {args.slots} slotow")

    samples2 = load_ints(args.source2)
    rows = run(samples, samples2, coef, args.slots)
    if not rows:
        raise SystemExit("BLAD APARATURY: zero wierszy — to blad, nie wynik")

    with open(args.out, "w", encoding="utf-8") as fh:
        for idx, values in rows:
            for name, value in zip(("f1_out_0", "f1_out_1"), values):
                fh.write(f"{args.family},{args.variant},{idx},{name},{value},0,0\n")
    print(f"{args.out}: {len(rows)} rekordow, logical_index {rows[0][0]}..{rows[-1][0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
