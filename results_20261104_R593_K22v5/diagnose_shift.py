#!/usr/bin/env python3
"""Diagnoza opisowa po pomiarze (nie kryterium): liczba roznych rekordow i stale przesuniecie kazdego pola osobno.

Wywolanie: diagnose_shift.py <katalog R593 K22v5> <komorka>...  (wynik w results/diagnosis.txt)
"""
import csv, sys
from pathlib import Path
base = Path(sys.argv[1])
first = {(r["task"], r["family"]): int(r["first_index"]) for r in csv.DictReader(open(base / "results/semantic.csv"))}
def load(p):
    d = {}
    for line in open(p):
        f = line.rstrip("\n").split(",")
        d.setdefault(int(f[2]), {})[f[3]] = f[4]
    return d
for cell in sys.argv[2:]:
    t, fam = cell.split("_")
    l0 = first[(t, fam)]
    ev = base / "evidence/raw" / cell
    r, p = load(ev / "rql.csv"), load(ev / "python.csv")
    fields = list(r[l0])
    rng = range(l0, l0 + 2000)
    bad = sum(1 for i in rng if r.get(i) != p.get(i))
    out = [f"{cell}: rekordy rozne {bad}/2000"]
    for fld in fields:
        badf = sum(1 for i in rng if r[i][fld] != p[i][fld])
        shift = next((k for k in sorted(range(-10, 11), key=abs)
                      if all(r.get(i + k, {}).get(fld) == p[i][fld] for i in range(l0 + 10, l0 + 1990))), None)
        out.append(f"{fld} rozne={badf} przesuniecie_pola={shift}")
    print("; ".join(out))
