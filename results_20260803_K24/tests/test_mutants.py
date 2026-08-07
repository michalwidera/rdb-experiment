#!/usr/bin/env python3
"""Bramka niezależności oracle'a — wykrycie 100% zamrożonych mutantów.

Mutant jest wykryty, gdy istnieje węzeł korpusu bramkowego, na którym
oracle == replika != mutant. Warunek zgodności oracle'a z repliką jest
istotny: bez niego „wykryciem” byłaby dowolna stała różnica.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "oracle"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import closedform as C  # noqa: E402
import model as M  # noqa: E402
from mutants import MUTANTS  # noqa: E402
from plan import SOURCE  # noqa: E402
from hand_cases import hand_cases  # noqa: E402


def main():
    corpus = hand_cases()
    detected = {}
    for name, mutation in MUTANTS.items():
        witnesses = []
        for label, plan, _, _ in corpus:
            oracle = M.tails_by_name(plan, convention=M.C1)
            replica = C.evaluate(plan)
            mutant = C.evaluate(plan, mutation=mutation)
            for node in plan.nodes:
                if node.kind == SOURCE:
                    continue
                key = node.name
                if oracle[key] == replica[key] and mutant[key] != replica[key]:
                    witnesses.append(f"{label}:{key} (oracle={oracle[key]}, mutant={mutant[key]})")
        detected[name] = witnesses

    missing = [name for name, hits in detected.items() if not hits]
    for name, hits in detected.items():
        state = f"wykryty ({len(hits)} świadków, np. {hits[0]})" if hits else "NIEWYKRYTY"
        print(f"{name:24s} {state}")
    print("BRAMKA MUTANTÓW: " + ("PRZESZŁA (100%)" if not missing
                                 else f"NIE PRZESZŁA — niewykryte: {', '.join(missing)}"))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
