#!/usr/bin/env python3
"""Harness Pythona dla F3 — POZA rdzeniem, nieliczony przez metryki."""
import argparse
import sys
from pathlib import Path

from core import run


def load_ints(path):
    return [int(tok) for tok in Path(path).read_text(encoding="utf-8").split()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--slots", type=int, required=True)
    ap.add_argument("--family", default="F3")
    ap.add_argument("--variant", default="base")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = run(load_ints(args.a), load_ints(args.b), args.slots)
    if not rows:
        raise SystemExit("BLAD APARATURY: zero wierszy — to blad, nie wynik")
    with open(args.out, "w", encoding="utf-8") as fh:
        for idx, value in rows:
            fh.write(f"{args.family},{args.variant},{idx},f3_out_0,{value},0,0\n")
    print(f"{args.out}: {len(rows)} rekordow, logical_index {rows[0][0]}..{rows[-1][0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
