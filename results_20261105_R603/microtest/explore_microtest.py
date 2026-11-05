#!/usr/bin/env python3
"""R603 - EKSPLORACJA mikrotestu po odczytaniu wyniku kryteriow M1-M3 (nie jest czescia kryteriow).

Pytanie po wyniku: w ktorej fazie zwolnienia (munmap czy shm_unlink) i w ktorym odcinku slotu
(pobudka czy praca) powstaje nadwyzka czasu i licznikow, wspolna dla trybow whole i chunk.
Jednostka: pojedynczy slot (nie max po oknie). Slot nalezy do fazy, gdy jego [deadline, end]
przecina [t_begin, t_munmap_end] (munmap) albo [t_munmap_end, t_end] (unlink); slot przecinajacy
obie fazy trafia do "obie". Kontrola: sloty kontrolne z analyze_microtest.py (> 50 ms od [t_create, t_end]).
Raport: mediana miary w grupie minus mediana w slotach kontrolnych, n slotow.

Uzycie: explore_microtest.py PREFIKS [PREFIKS ...]
"""

import sys

import numpy as np

from analyze_microtest import COUNTERS, GUARD_NS, load

MEASURES = ["wake_lag_ns", "work_ns"] + [f"wake_{c}" for c in COUNTERS[:5]] + [f"work_{c}" for c in COUNTERS[:5]]


def main():
    for prefix in sys.argv[1:]:
        s, ev, m = load(prefix)
        dl, end = s["deadline_ns"], s["end_ns"]
        vals = {"wake_lag_ns": m["wake_lag_ns"], "work_ns": m["work_ns"]}
        for c in COUNTERS[:5]:
            vals[f"wake_{c}"] = s[f"wake_{c}"]
            vals[f"work_{c}"] = s[f"work_{c}"]
        control = np.ones(len(dl), dtype=bool)
        control[0] = False
        for r in ev:
            control &= ~((dl <= r["t_end_ns"] + GUARD_NS) & (end >= r["t_create_ns"] - GUARD_NS))
        print(f"== {prefix}: nadwyzka mediany wobec slotow kontrolnych (n kontrolnych {int(control.sum())})")
        for mode in ("whole", "chunk"):
            groups = {"munmap": np.zeros(len(dl), bool), "unlink": np.zeros(len(dl), bool), "obie": np.zeros(len(dl), bool)}
            for r in ev[ev["mode"] == mode]:
                a = (dl <= r["t_munmap_end_ns"]) & (end >= r["t_begin_ns"])
                b = (dl <= r["t_end_ns"]) & (end >= r["t_munmap_end_ns"])
                groups["munmap"] |= a & ~b
                groups["unlink"] |= b & ~a
                groups["obie"] |= a & b
            sel = ev[ev["mode"] == mode]
            um = np.median((sel["t_munmap_end_ns"] - sel["t_begin_ns"]) / 1e6)
            ul = np.median((sel["t_end_ns"] - sel["t_munmap_end_ns"]) / 1e6)
            print(f"-- {mode}: faza munmap p50 {um:.2f} ms, faza unlink p50 {ul:.2f} ms")
            print("   " + f"{'miara':24s}" + "".join(f"{g:>16s}" for g in groups))
            print("   " + f"{'n slotow':24s}" + "".join(f"{int(g.sum()):16d}" for g in groups.values()))
            for k in MEASURES:
                base = np.median(vals[k][control])
                row = "".join(f"{np.median(vals[k][g]) - base:16.0f}" if g.any() else f"{'-':>16s}" for g in groups.values())
                print(f"   {k:24s}{row}")


if __name__ == "__main__":
    main()
