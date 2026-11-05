#!/usr/bin/env python3
"""R603D: rozdzielczosc i moc miar K2 (README R603D, *Ustalenia*, punkt 4) na surowych danych R603C.

Uzycie: k2_resolution.py --raw SUROWE_R603C --r603c KATALOG_results_20261105_R603C [--seed 6034]

Dla kazdej rodziny i strony R603C (B: okna R_B, C: okna R_C) oraz dla syntetycznych serii porcji na tle strony C
(hipoteza zerowa: brak drenazu, faza i dlugosc jak w C') liczy miary K2a i K2b R603D:
- slot narazony: przedzial [pobudka, pobudka + mediana compute klasy] przecina okno (klasa = iter mod H),
- odchylenie slotu = compute - mediana compute slotow kontrolnych tej klasy,
- K2a: mediana odchylen slotow narazonych serii prawdziwych minus to samo dla kopii placebo,
- K2b: odsetek slotow narazonych z e2e > takt wsrod obudzonych na czas (wake_lag < takt/2), prawdziwe minus placebo,
- placebo: 20 kopii kazdej serii przesunietych o m * H * takt (m losowe), w calosci w slotach kontrolnych,
- przedzial 95 % bootstrap po seriach (porzuceniach) razem z ich kopiami placebo.
Wydruk to liczby wyprowadzone; zadnej tresci korpusu.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

H = {"uc03": 8, "uc05": 40, "uc06": 5, "uc07": 10, "uc08": 12}
PORTIONS = {"uc03": 7, "uc05": 31, "uc06": 19, "uc07": 1, "uc08": 0}  # obroty po pierwszej porcji, N z dlugosci mmap
W_NS, TURN_NS = 75_000, 1_070_000
PLACEBO, TRIES, BOOT = 20, 400, 2000


def load(A, run):
    s = A.load_slots(run / "slots.csv")
    conns = A.load_conns(run / "conns.tsv")
    return s, conns


def control_mask(A, s, conns, excl):
    dl = s["deadline"]
    ctl = (dl >= conns[0]["start"] - A.SERIES_PAD_NS) & (dl <= conns[-1]["end"] + A.SERIES_PAD_NS)
    for c in conns:
        ctl &= ~((dl >= c["start"] - A.GUARD_NS) & (dl <= c["end"] + A.GUARD_NS))
    for a, b in excl:
        ctl &= ~((dl >= a - A.GUARD_NS) & (dl <= b + A.GUARD_NS))
    return ctl


def real_series(A, run, side):
    events = A.parse_trace(run / "trace.txt")
    rt = A.rt_tids(run / "rt.txt")
    conns = A.load_conns(run / "conns.tsv")
    kills = A.kill_windows(events, conns, rt)
    series, excl = [], []
    if side == "B":
        for m in A.queue_mappings(events, conns, rt):
            if m is not None:
                rel = A.find_release(events, m["addr"], m["len"], m["w1"])
                if rel is not None:
                    series.append([(rel[0], rel[1])])
    else:
        for w in kills:
            if w is not None and w["t0"] is not None and w["t1"] is not None and not w["overflow"]:
                series.append([(w["t0"], w["t1"])])
    for w in kills:
        if w is not None:
            excl.append((w["t_kill"], w["t1"] if w["t1"] is not None else (w["t0"] or w["t_kill"])))
    pairs, _, _ = A.queue_pairs(events, A.queue_mappings(events, conns, rt))
    excl += [(p[0], p[1]) for p in pairs]
    excl += [(cl[0][0], cl[-1][1]) for cl in series]
    return series, excl


class Run:
    def __init__(self, s, ctl, h):
        self.dl, self.comp, self.wake, self.e2e = s["deadline"], s["compute"], s["wake"], s["e2e"]
        self.period = int(np.median(np.diff(self.dl)))
        self.h, self.ctl = h, ctl
        self.cls = np.arange(len(self.dl)) % h
        self.base = np.array([np.median(self.comp[ctl & (self.cls == c)]) for c in range(h)])
        self.ontime = self.wake < self.period // 2
        self.t_on = self.dl + self.wake
        self.t_off = self.t_on + self.base[self.cls].astype(np.int64)

    def exposed(self, windows):
        idx = set()
        for t0, t1 in windows:
            lo = int(np.searchsorted(self.dl, t0 - 200_000_000))
            hi = int(np.searchsorted(self.dl, t1, side="right"))
            k = np.arange(lo, hi)
            idx.update(int(x) for x in k[(self.t_on[k] <= t1) & (self.t_off[k] >= t0)])
        return np.array(sorted(idx), dtype=np.int64)

    def values(self, idx):
        dev = (self.comp[idx] - self.base[self.cls[idx]]).astype(float)
        miss = np.where(self.ontime[idx], (self.e2e[idx] > self.period).astype(float), np.nan)
        return np.column_stack([dev, miss]) if len(idx) else np.zeros((0, 2))

    def placebo(self, windows, rng):
        """Kopie serii przesuniete o m * H * takt, wszystkie sloty narazone kontrolne."""
        step = self.h * self.period
        span = (self.dl[0] - windows[0][0], self.dl[-1] - windows[-1][1])
        lo_m, hi_m = int(np.ceil(span[0] / step)), int(np.floor(span[1] / step))
        out = []
        for _ in range(TRIES):
            if len(out) == PLACEBO or hi_m <= lo_m:
                break
            m = int(rng.integers(lo_m, hi_m + 1))
            if m == 0:
                continue
            shifted = [(a + m * step, b + m * step) for a, b in windows]
            idx = self.exposed(shifted)
            if len(idx) == 0 or self.ctl[idx].all():
                out.append(self.values(idx))
        return out


def stat(clusters):
    real = np.concatenate([c[0] for c in clusters]) if clusters else np.zeros((0, 2))
    pl = np.concatenate([p for c in clusters for p in c[1]]) if clusters else np.zeros((0, 2))
    if len(real) == 0 or len(pl) == 0:
        return np.nan, np.nan, len(real)
    dc = np.median(real[:, 0]) - np.median(pl[:, 0])
    dm = np.nanmean(real[:, 1]) - np.nanmean(pl[:, 1])
    return dc, dm, len(real)


def report(tag, clusters, rng):
    dc, dm, n = stat(clusters)
    nclu = sum(1 for c in clusters if len(c[0]))
    if n == 0:
        print(f"  {tag}: 0 slotow narazonych ({len(clusters)} serii)")
        return
    b = np.array([stat([clusters[i] for i in rng.integers(0, len(clusters), len(clusters))])[:2] for _ in range(BOOT)])
    lo, hi = np.nanpercentile(b, [2.5, 97.5], axis=0)
    print(f"  {tag}: serie {len(clusters)} (z narazeniem {nclu}), sloty narazone {n}"
          f" | K2a dcompute {dc / 1e3:+.2f} us [{lo[0] / 1e3:+.2f}, {hi[0] / 1e3:+.2f}]"
          f" | K2b d(e2e>takt, na czas) {100 * dm:+.2f} pp [{100 * lo[1]:+.2f}, {100 * hi[1]:+.2f}]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--r603c", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=6034)
    args = ap.parse_args()
    sys.path.insert(0, str(args.r603c))
    import analyze as A  # noqa: E402  parser okien R603C bez zmian

    rng = np.random.default_rng(args.seed)
    for fam, h in H.items():
        print(f"{fam} (H = {h}, obroty po pierwszej porcji = {PORTIONS[fam]})")
        for side in ("B", "C"):
            real_cl, null_cl = [], []
            for run in sorted((args.raw / fam).glob(f"{side}_*")):
                s, conns = load(A, run)
                series, excl = real_series(A, run, side)
                r = Run(s, control_mask(A, s, conns, excl), h)
                for cl in series:
                    real_cl.append((r.values(r.exposed(cl)), r.placebo(cl, rng)))
                if side == "C":
                    end = r.dl + r.e2e
                    cidx = np.flatnonzero(r.ctl)
                    for _ in range(len(series)):
                        k0 = int(rng.choice(cidx))
                        t0 = int(end[k0]) + int(rng.integers(40_000, 1_100_000))
                        st = [t0 + j * TURN_NS + int(rng.integers(0, 60_000)) for j in range(PORTIONS[fam] + 1)]
                        cl = [(a, a + W_NS) for a in st]
                        idx = r.exposed(cl)
                        if len(idx) and not r.ctl[idx].all():
                            continue
                        null_cl.append((r.values(idx), r.placebo(cl, rng)))
            report(f"{side}, prawdziwe okna", real_cl, rng)
            if side == "C":
                report("H0, syntetyczne serie porcji na tle C", null_cl, rng)


if __name__ == "__main__":
    main()
