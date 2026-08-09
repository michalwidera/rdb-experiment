#!/usr/bin/env python3
"""Korpus ksztaltow: oracle zdarzeniowy wobec silnika (compile-only).

Sprawdza dwie rzeczy naraz:
  1. gdzie silnik rozjezdza sie z granica zdarzeniowa i W KTORA STRONE,
  2. czy KANDYDACKA REGULA NAPRAWY  W' = max(0, W_silnika - O_silnika)
     odtwarza oracle na CALYM korpusie, a nie na kilku przypadkach.

Silnik uruchamiany jest w budowie R1 OFF, zeby ogladac ksztalt NAPISANY, a nie
przepisany przez regule czynnikowania.
"""
import re, subprocess, sys
from fractions import Fraction as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from oracle_boundary import Decl, Shift, Hash, Sum, boundary  # noqa: E402

BIN = sys.argv[1]
WORK = Path(sys.argv[2]); WORK.mkdir(parents=True, exist_ok=True)
HDR = re.compile(r"^m\((\d+/\d+)\)(.*)$")

RATES = [(F(1,100), F(1,50)), (F(1,60), F(1,30)), (F(1,3), F(1,7)),
         (F(1,5), F(1,2)), (F(1,4), F(1,6)), (F(1,2), F(1,2)), (F(2,7), F(3,5))]


def engine(expr, da, db, tag):
    f = WORK / f"{tag}.rql"
    f.write_text(f"DECLARE v INTEGER STREAM A, {da} FILE 'a.txt'\n"
                 f"DECLARE v INTEGER STREAM B, {db} FILE 'b.txt'\n"
                 f"SELECT * STREAM m FROM {expr}\n", encoding="utf-8")
    r = subprocess.run([BIN, "-c", f.name], cwd=WORK, capture_output=True, text=True)
    if r.returncode != 0:
        return None
    for line in (r.stdout + r.stderr).splitlines():
        mm = HDR.match(line.strip())
        if mm:
            rest = mm.group(2)
            t = int(re.search(r"tail=(\d+)", rest).group(1)) if "tail=" in rest else 0
            o = int(re.search(r"origin=(\d+)", rest).group(1)) if "origin=" in rest else 0
            return o, t
    return None


rows, skipped = [], 0
for da, db in RATES:
    for i in range(0, 4):
        for k in range(0, 4):
            a = Shift(Decl(da), i) if i else Decl(da)
            b = Shift(Decl(db), k) if k else Decl(db)
            sa = f"(A>{i})" if i else "A"
            sb = f"(B>{k})" if k else "B"
            for opname, node, expr in (("#", Hash(a, b), f"{sa}#{sb}"),
                                       ("+", Sum(a, b), f"{sa}+{sb}")):
                tag = f"{opname}_{da.denominator}_{db.denominator}_{i}_{k}".replace("/", "-")
                eng = engine(expr, da, db, tag)
                if eng is None:
                    skipped += 1
                    continue
                try:
                    orc = boundary(node)
                except Exception:
                    skipped += 1
                    continue
                rows.append((expr, f"{da},{db}", opname, orc, eng))
    for m in range(1, 4):
        for opname, node, expr in (("#", Shift(Hash(Decl(da), Decl(db)), m), f"(A#B)>{m}"),
                                   ("+", Shift(Sum(Decl(da), Decl(db)), m), f"(A+B)>{m}")):
            tag = f"post{opname}_{da.denominator}_{db.denominator}_{m}".replace("/", "-")
            eng = engine(expr, da, db, tag)
            if eng is None:
                skipped += 1
                continue
            rows.append((expr, f"{da},{db}", opname, boundary(node), eng))

agree = under = over = 0
rule_ok = rule_bad = 0
bad_examples, under_examples = [], []
for expr, rates, op, (oo, ow), (eo, et) in rows:
    if (oo, ow) == (eo, et):
        agree += 1
    elif (eo + et) > (oo + ow):
        over += 1
    else:
        under += 1
        under_examples.append((expr, rates, (oo, ow), (eo, et)))
    if eo != oo:
        bad_examples.append(("ORIGIN", expr, rates, (oo, ow), (eo, et)))
    cand = max(0, et - eo)
    if (eo, cand) == (oo, ow):
        rule_ok += 1
    else:
        rule_bad += 1
        if len(bad_examples) < 12:
            bad_examples.append(("REGULA", expr, rates, (oo, ow), (eo, et), cand))

print(f"korpus: {len(rows)} ksztaltow, pominietych (plan odrzucony/niemodelowany): {skipped}")
print(f"  silnik zgodny z oracle : {agree}")
print(f"  silnik ZAWYZA          : {over}")
print(f"  silnik ZANIZA          : {under}   <-- kierunek niebezpieczny")
print(f"\nkandydacka regula W' = max(0, W - O):  odtwarza oracle {rule_ok}/{len(rows)}, chybia {rule_bad}")
if under_examples:
    print("\nPRZYPADKI ZANIZANIA:")
    for e in under_examples[:10]:
        print("   ", e)
if bad_examples:
    print("\nCHYBIENIA REGULY / ORIGINU (do 12):")
    for e in bad_examples[:12]:
        print("   ", e)
