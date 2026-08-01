#!/usr/bin/env python3
"""Harness Pythona dla F2 — POZA rdzeniem, nieliczony przez metryki."""
import argparse
import struct
import sys
from pathlib import Path

from core import run

FIELDS = ["qrs_out_0", "qrs_out_1", "qrs_out_2"]


def load_rec(path):
    """rec205: pary int32 LE (MLII, V1) — ten sam format co load_inputs() baseline'u."""
    data = Path(path).read_bytes()
    n = len(data) // 8
    mlii = []
    for i in range(n):
        mlii.append(struct.unpack_from("<i", data, i * 8)[0])
    return mlii


def load_ints(path):
    return [int(tok) for tok in Path(path).read_text(encoding="utf-8").split()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rec", required=True)
    ap.add_argument("--bp", required=True)
    ap.add_argument("--d", required=True)
    ap.add_argument("--slots", type=int, required=True)
    ap.add_argument("--family", default="F2")
    ap.add_argument("--variant", default="base")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    mlii = load_rec(args.rec)
    bp_coef = load_ints(args.bp)
    d_coef = load_ints(args.d)
    if len(mlii) < args.slots:
        raise SystemExit(f"BLAD APARATURY: {len(mlii)} probek, zadano {args.slots} slotow")

    rows = run(mlii, bp_coef, d_coef, args.slots)
    if not rows:
        raise SystemExit("BLAD APARATURY: zero wierszy — to blad, nie wynik")

    with open(args.out, "w", encoding="utf-8") as fh:
        for idx, values in rows:
            for name, value in zip(FIELDS, values):
                fh.write(f"{args.family},{args.variant},{idx},{name},{value},0,0\n")
    print(f"{args.out}: {len(rows)} rekordow, logical_index {rows[0][0]}..{rows[-1][0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
