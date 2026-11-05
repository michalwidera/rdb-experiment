#!/usr/bin/env python3
"""R603 - analiza mikrotestu tlb_microtest.c (kryteria M1-M3 w ../README.md).

Zdarzenie zwolnienia = [t_begin, t_end] (munmap + shm_unlink watku R). Sloty dotkniete zdarzeniem:
sloty S, ktorych przedzial [deadline, end] ma czesc wspolna z oknem, oraz pierwszy slot o deadline
po t_end (unieważnienie TLB dzieje sie na koncu munmap, w tlb_finish_mmu, wiec jego koszt moze trafic
dopiero w nastepna pobudke). Wartosc zdarzenia dla miary = max tej miary po slotach dotknietych.

Sloty kontrolne: dalej niz GUARD_NS od kazdego przedzialu [t_create, t_end] (budowa i zapelnianie
segmentu tez obciaza L2, wiec nie moze trafic do kontroli). Pseudo-zdarzenia: na kazde zdarzenie
PSEUDO_PER_EVENT okien o tej samej dlugosci w losowym miejscu przebiegu, w calosci w slotach
kontrolnych, z ta sama regula "plus pierwszy slot po oknie"; ziarno 603.

Uzycie: analyze_microtest.py PREFIKS [PREFIKS ...]   (PREFIKS_slots.csv, PREFIKS_events.csv)
"""

import math
import sys

import numpy as np

GUARD_NS = 50_000_000
PSEUDO_PER_EVENT = 20
SEED = 603
COUNTERS = ["l1d_tlb_refill", "l1i_tlb_refill", "l2d_cache", "l2d_cache_refill", "l1d_cache_refill", "inst_retired"]


def mann_whitney_greater(x, y):
    """Jednostronny test Manna-Whitneya H1: x > y, przyblizenie normalne z poprawka na wiazania (jak R600)."""
    x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return float("nan")
    allv = np.concatenate([x, y])
    order = allv.argsort(kind="mergesort")
    ranks = np.empty(len(allv))
    sv = allv[order]
    _, first, counts = np.unique(sv, return_index=True, return_counts=True)
    ranks[order] = np.repeat(first + (counts + 1) / 2.0, counts)
    u = ranks[:n1].sum() - n1 * (n1 + 1) / 2.0
    n = n1 + n2
    tie = (counts**3 - counts).sum()
    sigma = math.sqrt(n1 * n2 / 12.0 * ((n + 1) - tie / (n * (n - 1))))
    if sigma == 0:
        return 1.0
    z = (u - n1 * n2 / 2.0 - 0.5) / sigma
    return 0.5 * math.erfc(z / math.sqrt(2))


def load(prefix):
    s = np.genfromtxt(f"{prefix}_slots.csv", delimiter=",", names=True, dtype=np.int64)
    e = np.genfromtxt(f"{prefix}_events.csv", delimiter=",", names=True, dtype=None, encoding="ascii")
    if not np.all(s["valid"][1:] == 1):
        sys.exit(f"{prefix}: {int((s['valid'][1:] != 1).sum())} slotow z licznikami multipleksowanymi - przebieg niewazny")
    m = {
        "work_ns": s["end_ns"] - s["wake_ns"],
        "wake_lag_ns": s["wake_ns"] - s["deadline_ns"],
        "e2e_ns": s["end_ns"] - s["deadline_ns"],
    }
    for c in COUNTERS:
        m[c] = s[f"wake_{c}"] + s[f"work_{c}"]
    return s, e, m


def affected(dl, end, lo, hi):
    """Indeksy slotow dotknietych oknem [lo, hi] plus pierwszy slot o deadline > hi."""
    idx = np.nonzero((dl <= hi) & (end >= lo))[0]
    nxt = np.searchsorted(dl, hi, side="right")
    if nxt < len(dl):
        idx = np.union1d(idx, [nxt])
    return idx


def analyze(prefix, rng):
    s, ev, m = load(prefix)
    dl, end = s["deadline_ns"], s["end_ns"]
    control = np.ones(len(dl), dtype=bool)
    control[0] = False
    for r in ev:
        control &= ~((dl <= r["t_end_ns"] + GUARD_NS) & (end >= r["t_create_ns"] - GUARD_NS))
    out = {"whole": {k: [] for k in m}, "chunk": {k: [] for k in m}}
    pseudo = {"whole": {k: [] for k in m}, "chunk": {k: [] for k in m}}
    width = {"whole": [], "chunk": []}
    for r in ev:
        mode, lo, hi = r["mode"], r["t_begin_ns"], r["t_end_ns"]
        width[mode].append(hi - lo)
        idx = affected(dl, end, lo, hi)
        for k in m:
            out[mode][k].append(m[k][idx].max())
        got, tries = 0, 0
        while got < PSEUDO_PER_EVENT and tries < 10000:
            tries += 1
            plo = int(rng.integers(dl[1], dl[-1] - (hi - lo)))
            pidx = affected(dl, end, plo, plo + (hi - lo))
            if len(pidx) == 0 or not control[pidx].all():
                continue
            for k in m:
                pseudo[mode][k].append(m[k][pidx].max())
            got += 1
        if got < PSEUDO_PER_EVENT:
            sys.exit(f"{prefix}: za malo slotow kontrolnych na pseudo-zdarzenia")
    return out, pseudo, width, int(control.sum()), len(dl)


def main():
    rng = np.random.default_rng(SEED)
    for prefix in sys.argv[1:]:
        out, pseudo, width, ncontrol, nslots = analyze(prefix, rng)
        print(f"== {prefix}: slotow {nslots}, kontrolnych {ncontrol}")
        for mode in ("whole", "chunk"):
            w = np.asarray(width[mode]) / 1e6
            print(f"-- {mode}: n zdarzen {len(w)}, dlugosc okna p50 {np.median(w):.2f} ms, max {w.max():.2f} ms")
            print(f"   {'miara':18s} {'zdarzenia p50':>14s} {'pseudo p50':>12s} {'nadwyzka p50':>13s} {'MW p':>9s}")
            for k in out[mode]:
                x, y = np.asarray(out[mode][k]), np.asarray(pseudo[mode][k])
                print(f"   {k:18s} {np.median(x):14.0f} {np.median(y):12.0f} {np.median(x) - np.median(y):13.0f} "
                      f"{mann_whitney_greater(x, y):9.2e}")


if __name__ == "__main__":
    main()
