#!/usr/bin/env python3
"""Zamrożona kolejność wykonania macierzy K26 — 20 sparowanych bloków.

§10: „wykonać je w 20 sparowanych blokach obejmujących wszystkie profile,
z kolejnością losowaną z zamrożonego ziarna, rebootem między rodzinami".

Blok = jedno przejście przez WSZYSTKIE profile danej komórki `(rodzina, Q)`.
Sparowanie jest istotne dla bramki ceny czasowej: bootstrap losuje bloki, więc
`DEFAULT` i ablacja muszą leżeć w tym samym bloku, na tej samej maszynie i w tym
samym stanie termicznym. Losowana jest KOLEJNOŚĆ PROFILI wewnątrz bloku — żeby
pozycja w bloku nie skorelowała się z profilem.

Czego ten plik NIE losuje: kolejności rodzin (jest stała, bo między rodzinami
idzie reboot) ani kolejności `Q` (rosnąca, żeby najcięższe komórki `Q=32` nie
rozgrzewały maszyny przed lekkimi).

Uruchomienie:
    ./gen_blocks.py            # zapisuje blocks.tsv
    ./gen_blocks.py --check    # porównuje z dyskiem (kod 1 przy rozbieżności)
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

#: Ziarno kolejności bloków. Rozdzielone od ziarna danych i od ziarna bootstrapu.
SEED_BLOCKS = 20260809_2604

FAMILIES = ["F9-R2", "F9-R1", "F9-X"]
PROFILES = ["DEFAULT", "NO_R2_CANON", "NO_R1_FACTOR", "NO_R1_NO_R2"]
Q_GRID = [1, 2, 4, 8, 16, 32]
BLOCKS = 20

COLUMNS = ["family", "block", "q", "order", "profile"]


def splitmix64(state):
    state = (state + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    z = state
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return state, z ^ (z >> 31)


def render():
    state = SEED_BLOCKS
    lines = ["\t".join(COLUMNS)]
    for family in FAMILIES:
        for block in range(1, BLOCKS + 1):
            for q in Q_GRID:
                pool = list(PROFILES)
                order = []
                # Tasowanie Fishera-Yatesa na tym samym PRNG, ktorego uzywa
                # generator korpusu i bootstrap — jeden algorytm, trzy ziarna.
                while pool:
                    state, value = splitmix64(state)
                    order.append(pool.pop(value % len(pool)))
                for position, profile in enumerate(order, start=1):
                    lines.append(f"{family}\t{block}\t{q}\t{position}\t{profile}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    content = render()
    path = HERE / "blocks.tsv"
    runs = content.count("\n") - 1

    if args.check:
        if not path.exists():
            print("BLAD: brak blocks.tsv", file=sys.stderr)
            return 1
        if path.read_text() != content:
            print("BLAD: blocks.tsv rozjechany z generatorem", file=sys.stderr)
            return 1
        print(f"OK: blocks.tsv zgodny z generatorem ({runs} przebiegow)")
        return 0

    path.write_text(content)
    print(f"OK: blocks.tsv — {runs} przebiegow "
          f"({len(FAMILIES)} rodziny x {BLOCKS} blokow x {len(Q_GRID)} Q x {len(PROFILES)} profile)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
