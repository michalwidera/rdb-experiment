#!/usr/bin/env python3
"""Generator zamrożonych danych wejściowych korpusu K22 (PREDECLARATION.md §3).

Dane są DETERMINISTYCZNE i identyczne dla wszystkich trzech modeli — to jest
warunek wejścia do tabeli równoważności. Żadna rodzina nie używa `/dev/urandom`
(`dsp-simple-fir.rql` czyta losowe bajty, co uniemożliwiłoby oracle).

Uruchamiać z katalogu roboczego kampanii; pliki powstają w bieżącym katalogu.
"""
import argparse
import hashlib
import sys
from pathlib import Path

# F1 — źródło o zamrożonym wzorze; zakres |x| <= 500 wyklucza przepełnienie
# przy 26 odczepach filtru (patrz f1_range_ok()).
F1_ROWS = 4096


def f1_source(i):
    return ((i * 37) % 1000) - 500


# F3 — dwa źródła o wymiernych interwałach 1/10 i 1/5 s; warunek reguły
# i*delta_A = k*delta_B zachodzi dla (i,k) = (2,1). Wzory z rodziny W2
# (results_20260730_K6c/generate.py), żeby F3 dziedziczyła prowenienecję.
F3_ROWS = 8000


def write(path, lines):
    text = "".join(f"{v}\n" for v in lines)
    Path(path).write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print(f"{digest}  {path}  ({len(lines)} wierszy)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", choices=["F1", "F3", "all"], default="all")
    args = ap.parse_args()

    if args.family in ("F1", "all"):
        write("f1_source.txt", [f1_source(i) for i in range(F1_ROWS)])
    if args.family in ("F3", "all"):
        write("f3_a.txt", [i + 1 for i in range(F3_ROWS)])
        write("f3_b.txt", [1001 + i for i in range(F3_ROWS)])
    return 0


if __name__ == "__main__":
    sys.exit(main())
