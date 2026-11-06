#!/usr/bin/env python3
"""R603D: analiza przebiegow run_one.py wedlug kryteriow K1', K2a, K2b, K3 i obserwacji O1-O5 z README.md.

Uzycie: analyze.py --raw KATALOG [--out RAPORT.md] [--seed 6034]
        analyze.py --raw KATALOG_SUCHY --gates               (bramki G1-G5 i H suchego przebiegu)
        analyze.py --raw SUROWE_R603C --parser-check          (test parsera na danych R603C, README, Kolejnosc, punkt 2)
KATALOG ma uklad <rodzina>/<strona>_<para>/ ze stronami C i Cp (slots.csv z kolumna P1, trace.txt, conns.tsv, rt.txt,
meta.json). Kod wyjscia: 0 - raport zapisany / test zdany, 2 - blad danych albo test niezdany.
Wymaga NumPy (np. retractordb/.venv-python).

Parser R603C (okna R_C, pary munmap + unlinkat, oddania z puli, O1, O2) jest importowany BEZ ZMIAN z
../results_20261105_R603C/analyze.py. Dochodzi (README R603D, Aparatura, punkt 5):
- obroty watku komunikacyjnego: [wyjscie z clock_nanosleep/nanosleep, nastepne wejscie] watku spoza RT,
- serie drenazu C': P0 = okno R_C, P1..Pk = k kolejnych obrotow po obrocie z P0 (k z PORTIONS, sprawdzane wobec
  pojemnosci kolejki z dlugosci mmap), seria przepelnienia i seria zaklocona osobno,
- K2 klasowe z placebo (klasa slotu iter mod H, narazenie [pobudka, pobudka + mediana klasy], placebo = seria
  przesunieta o m * H * takt, bootstrap po seriach) - ta sama miara co k2_resolution.py,
- model stanu puli (K1', gotowosc), O3 (dlugosci porcji i obrotow), O4 (koszt na porzucenie), O5 (zaklocenia).
Ziarna: placebo --seed, bootstrap --seed+1, syntetyczne serie H0 --seed+2, pseudo-zdarzenia opisowe --seed+3,
pseudo-zdarzenia wewnatrz parsera R603C --seed+4 (ich wynik nie jest uzywany). W --parser-check jedno ziarno 6034
w kolejnosci losowan k2_resolution.py (tabela README, Ustalenia, punkt 4) i 6031 dla wydruku R603C.
Wydruk to liczby wyprowadzone; zadnej tresci korpusu.
"""

import argparse
import functools
import gzip
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def _load_r603c():
    spec = importlib.util.spec_from_file_location("analyze_r603c", HERE.parent / "results_20261105_R603C" / "analyze.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


A = _load_r603c()
# Ten sam slad czyta parser R603C i czesc R603D: jedno parsowanie na przebieg (wynik bez zmian).
A.parse_trace = functools.lru_cache(maxsize=2)(A.parse_trace)

H = {"uc03": 8, "uc05": 40, "uc06": 5, "uc07": 10, "uc08": 12}
PORTIONS = {"uc03": 7, "uc05": 31, "uc06": 19, "uc07": 1, "uc08": 0}  # README, Ustalenia, punkt 1
DRAIN_BATCH = 256  # kResponseQueueDrainBatch w C'
MQ_HDR, MQ_MSG = 216, 1048  # dlugosc mmap kolejki = MQ_HDR + MQ_MSG * N (README, Ustalenia, punkt 1)
SLEEP = ("clock_nanosleep", "nanosleep")
DELTA_C_NS = 5_000  # D2
DELTA_M = 0.02
MIN_SLOTS, MIN_SERIES = 100, 50
H0_BOUND_NS = 1_000  # delta_c / 5
PLACEBO, TRIES, BOOT = 20, 400, 2000
LOOKBACK_NS = 200_000_000
# Parametry syntetycznych serii H0 z k2_resolution.py (tylko --parser-check); w kampanii z danych C'.
H0_DEFAULT = {"p0_ns": 75_000, "w_ns": 75_000, "turn_ns": 1_070_000, "phase": (40_000, 1_100_000), "jitter_ns": 60_000}
H_TOL = 0.05  # bramka H (aneks 1): mediana przy H najwyzej 5 % nad mediana przy argminie


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def pct(a, q):
    return A.pct(a, q)


def fmt_us(ns, digits=1):
    return "-" if ns is None or (isinstance(ns, float) and math.isnan(ns)) else f"{ns / 1e3:.{digits}f}"


def all_tids(path):
    out = {}
    for line in path.read_text().splitlines():
        m = re.search(r"tid=(\d+)\tpolicy=(\S+)", line)
        if m:
            out[int(m[1])] = m[2]
    return out


def capacity_portions(n):
    """Liczba obrotow po pierwszej porcji dla pelnej kolejki n komunikatow."""
    return max(0, math.ceil((n - DRAIN_BATCH) / DRAIN_BATCH))


# ---------------------------------------------------------------- miara K2 (jak k2_resolution.py)

class SlotModel:
    def __init__(self, s, ctl, h):
        self.dl, self.comp, self.wake, self.e2e = s["deadline"], s["compute"], s["wake"], s["e2e"]
        self.period = int(np.median(np.diff(self.dl)))
        self.h, self.ctl = h, ctl
        self.cls = np.arange(len(self.dl)) % h
        self.base = np.array([np.median(self.comp[ctl & (self.cls == c)]) for c in range(h)])
        self.ontime = self.wake < self.period // 2
        self.t_on = self.dl + self.wake
        self.t_off = self.t_on + self.base[self.cls].astype(np.int64)
        self.end = self.dl + self.e2e

    def exposed(self, windows):
        idx = set()
        for t0, t1 in windows:
            lo = int(np.searchsorted(self.dl, t0 - LOOKBACK_NS))
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

    def cluster(self, windows, rng):
        real = self.values(self.exposed(windows))
        pl = self.placebo(windows, rng)
        return {"real": real, "pl": np.concatenate(pl) if pl else np.zeros((0, 2)), "pl_copies": len(pl),
                "pl_sum": [float(p[:, 0].sum()) for p in pl], "pl_n": [len(p) for p in pl]}

    def h0_windows(self, rng, k, par):
        """Syntetyczna seria porcji na tle bez drenazu (k2_resolution.py; parametry z C' w kampanii)."""
        cidx = np.flatnonzero(self.ctl)
        k0 = int(rng.choice(cidx))
        t0 = int(self.end[k0]) + int(rng.integers(par["phase"][0], par["phase"][1]))
        st = [t0 + j * par["turn_ns"] + int(rng.integers(0, par["jitter_ns"])) for j in range(k + 1)]
        return [(a, a + (par["p0_ns"] if j == 0 else par["w_ns"])) for j, a in enumerate(st)]


def k2_stat(clusters):
    real = [c["real"] for c in clusters]
    pl = [c["pl"] for c in clusters]
    real = np.concatenate(real) if real else np.zeros((0, 2))
    pl = np.concatenate(pl) if pl else np.zeros((0, 2))
    if len(real) == 0 or len(pl) == 0:
        return np.nan, np.nan, len(real)
    dc = np.median(real[:, 0]) - np.median(pl[:, 0])
    with np.errstate(invalid="ignore"):
        dm = np.nanmean(real[:, 1]) - np.nanmean(pl[:, 1]) if (~np.isnan(real[:, 1])).any() else np.nan
    return dc, dm, len(real)


def k2_summary(clusters, rng):
    dc, dm, n = k2_stat(clusters)
    out = {"dc": dc, "dm": dm, "n": n, "series": len(clusters), "series_exposed": sum(1 for c in clusters if len(c["real"])),
           "lo": (np.nan, np.nan), "hi": (np.nan, np.nan)}
    if n == 0:
        return out
    b = np.array([k2_stat([clusters[i] for i in rng.integers(0, len(clusters), len(clusters))])[:2] for _ in range(BOOT)])
    with np.errstate(invalid="ignore"):
        lo, hi = np.nanpercentile(b, [2.5, 97.5], axis=0)
    out["lo"], out["hi"] = (lo[0], lo[1]), (hi[0], hi[1])
    return out


def ratio_boot(cp, c, rng):
    """u' = Delta_c(C') / Delta_c(C), losowanie serii obu stron niezaleznie."""
    if not cp or not c:
        return np.nan, np.nan, np.nan
    point = k2_stat(cp)[0] / k2_stat(c)[0]
    out = []
    for _ in range(BOOT):
        a = k2_stat([cp[i] for i in rng.integers(0, len(cp), len(cp))])[0]
        b = k2_stat([c[i] for i in rng.integers(0, len(c), len(c))])[0]
        if b > 0:
            out.append(a / b)
    if len(out) < BOOT * 0.9:
        return point, np.nan, np.nan
    return point, float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def o4_cost(clusters):
    """Na serie: (sloty narazone, suma odchylen) minus srednia tego samego w kopiach placebo."""
    n, d = [], []
    for c in clusters:
        pn = np.mean(c["pl_n"]) if c["pl_n"] else 0.0
        ps = np.mean(c["pl_sum"]) if c["pl_sum"] else 0.0
        n.append(len(c["real"]) - pn)
        d.append(float(c["real"][:, 0].sum()) - ps)
    return np.array(n), np.array(d)


def o4_boot(cp, c, rng):
    """Roznica srednich kosztow na porzucenie C' - C (95 % bootstrap po seriach)."""
    if len(cp) == 0 or len(c) == 0:
        return np.nan, np.nan, np.nan
    point = cp.mean() - c.mean()
    b = [cp[rng.integers(0, len(cp), len(cp))].mean() - c[rng.integers(0, len(c), len(c))].mean() for _ in range(BOOT)]
    return point, float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


# ---------------------------------------------------------------- przebieg

def comm_turns(events, tids, rt):
    """Obroty watku komunikacyjnego: tablice (poczatek = wyjscie ze snu, koniec = nastepne wejscie), tid."""
    by_tid = {}
    for e in events:
        if e[2] in SLEEP and e[1] not in rt:
            by_tid.setdefault(e[1], []).append(e)
    if not by_tid:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64), None, 0
    tid = max(by_tid, key=lambda t: len(by_tid[t]))
    starts, ends, pending = [], [], None
    for t, _, call, kind, _, _ in by_tid[tid]:
        if kind == "exit":
            pending = t
        elif pending is not None:
            starts.append(pending)
            ends.append(t)
            pending = None
    others = sum(len(v) for t, v in by_tid.items() if t != tid)
    return np.array(starts, dtype=np.int64), np.array(ends, dtype=np.int64), tid, others


def pool_out_events(events, conns, maps, kills, rt):
    """Oddania z puli: ta sama regula co w parserze R603C (analyze_run), z czasami."""
    rc_rename = {w["rename_idx"] for w in kills if w is not None and w["rename_idx"] is not None}
    out = []
    for i, e in enumerate(events):
        if e[2] in A.RENAME and e[3] == "enter" and e[1] not in rt:
            j = next((k for k in range(i + 1, len(events)) if events[k][1] == e[1] and events[k][2] == e[2]
                      and events[k][3] == "exit"), None)
            if j is None or j in rc_rename or events[j][4] != 0:
                continue
            ci = next((k for k, c in enumerate(conns) if c["start"] <= e[0] <= c["end"]), None)
            if ci is not None and maps[ci] is None:
                out.append((ci, e[0], events[j][0]))
    return out


def analyze_run(run_dir, rngs, h0_par=None, h0_n_from=None):
    """Jeden przebieg: parser R603C + serie, obroty, model puli, klastry K2.

    rngs: slownik generatorow 'placebo', 'base', 'pseudo'. Klastry H0 licza sie tylko na stronie C (gdy h0_par).
    """
    meta = json.loads((run_dir / "meta.json").read_text())
    base = A.analyze_run(run_dir, rngs["base"])  # sprawdza waznosc przebiegu (rt_ok, governor, binarka, overrun)
    side, fam = meta["side"], meta["family"]
    h = H[fam]
    k = PORTIONS[fam]
    events = A.parse_trace(run_dir / "trace.txt")
    rt = A.rt_tids(run_dir / "rt.txt")
    tids = all_tids(run_dir / "rt.txt")
    conns = A.load_conns(run_dir / "conns.tsv")
    s = A.load_slots(run_dir / "slots.csv")
    dl = s["deadline"]
    maps = A.queue_mappings(events, conns, rt)
    pairs, _, _ = A.queue_pairs(events, maps)
    kills = A.kill_windows(events, conns, rt) if conns[0]["pid"] is not None else [None] * len(conns)
    caps = sorted({(m["len"] - MQ_HDR) // MQ_MSG for m in maps if m is not None})
    k_mmap = [capacity_portions(n) for n in caps]
    ts, te, comm_tid, sleep_other = comm_turns(events, tids, rt)
    comm_ev = [e for e in events if e[1] == comm_tid and e[2] not in SLEEP and e[3] == "enter"] if comm_tid else []
    comm_t = np.array([e[0] for e in comm_ev], dtype=np.int64)

    # Serie: B (tylko --parser-check na danych R603C) = okna R_B; C = P0; Cp = P0 + P1..Pk.
    series = []
    if side == "B":
        for m in maps:
            if m is not None:
                rel = A.find_release(events, m["addr"], m["len"], m["w1"])
                if rel is not None:
                    series.append({"windows": [(rel[0], rel[1])], "t0": rel[0], "end": rel[1], "kind": "ok",
                                   "reason": "", "t_kill": rel[0]})
    else:
        for ci, w in enumerate(kills):
            if w is None or w["t0"] is None or w["t1"] is None:
                continue  # zwolnienie bez puli (martwy muteks, skasowanie) - nie seria drenazu
            sr = {"ci": ci, "t_kill": w["t_kill"], "t0": w["t0"], "p0": (w["t0"], w["t1"]), "windows": [(w["t0"], w["t1"])],
                  "end": w["t1"], "kind": "overflow" if w["overflow"] else "ok", "reason": "", "turns": []}
            if side == "Cp" and k > 0:
                j0 = int(np.searchsorted(ts, w["t0"], side="right")) - 1
                if j0 < 0 or te[j0] < w["t1"]:
                    if sr["kind"] == "ok":
                        sr["kind"], sr["reason"] = "disturbed", "P0 poza jednym obrotem"
                elif j0 + k + 1 >= len(ts):
                    sr["kind"], sr["reason"] = "disturbed", "koniec sladu przed Pk+1"
                else:
                    sr["turns"] = list(range(j0 + 1, j0 + k + 1))
                    sr["after"] = j0 + k + 1
                    sr["windows"] += [(int(ts[j]), int(te[j])) for j in sr["turns"]]
                    sr["end"] = int(te[j0 + k])
                    a, b = int(ts[j0 + 1]), int(te[j0 + k])
                    inside = comm_t[(comm_t >= a) & (comm_t <= b)]
                    if len(inside) and sr["kind"] == "ok":
                        names = sorted({e[2] for e in comm_ev if a <= e[0] <= b})
                        sr["kind"], sr["reason"] = "disturbed", "wywolanie w P1..Pk: " + ", ".join(names)
            series.append(sr)

    # Sloty kontrolne: jak R603C + cale serie (od kill do konca Pk).
    excl = [(w["t_kill"], w["t1"] if w["t1"] is not None else (w["t0"] or w["t_kill"])) for w in kills if w is not None]
    excl += [(p[0], p[1]) for p in pairs]
    excl += [(sr["windows"][0][0], sr["end"]) for sr in series]
    ctl = (dl >= conns[0]["start"] - A.SERIES_PAD_NS) & (dl <= conns[-1]["end"] + A.SERIES_PAD_NS)
    for c in conns:
        ctl &= ~((dl >= c["start"] - A.GUARD_NS) & (dl <= c["end"] + A.GUARD_NS))
    for a, b in excl:
        ctl &= ~((dl >= a - A.GUARD_NS) & (dl <= b + A.GUARD_NS))
    model = SlotModel(s, ctl, h)
    for sr in series:
        if sr["kind"] == "ok":
            sr["cluster"] = model.cluster(sr["windows"], rngs["placebo"])
    h0 = []
    if h0_par is not None and side == "C":
        n_h0 = len([sr for sr in series if sr["kind"] == "ok"]) if h0_n_from is None else h0_n_from
        for _ in range(n_h0):
            cl = model.h0_windows(rngs["h0"], h0_par["k"], h0_par)
            idx = model.exposed(cl)
            if len(idx) and not model.ctl[idx].all():
                continue
            h0.append({"real": model.values(idx), **{kk: v for kk, v in model.cluster(cl, rngs["h0"]).items() if kk != "real"}})

    # Obroty bezczynne: bez wywolan, poza seriami (od kill do konca Pk), poza podlaczeniami.
    busy = [(sr["t_kill"], sr["end"]) for sr in series] + [(c["start"], c["end"]) for c in conns]
    busy += [(w["t_kill"], w["t1"] or w["t0"] or w["t_kill"]) for w in kills if w is not None]
    idle = np.ones(len(ts), dtype=bool)
    for a, b in busy:
        idle &= ~((ts <= b) & (te >= a))
    if len(comm_t):
        j = np.searchsorted(ts, comm_t, side="right") - 1
        j = j[(j >= 0) & (comm_t <= te[np.clip(j, 0, max(0, len(te) - 1))])] if len(ts) else j[:0]
        idle[j] = False
    idle_len = (te - ts)[idle]

    # O3: dlugosci.
    end_slot = dl + s["e2e"]
    p0_len = [sr["p0"][1] - sr["p0"][0] for sr in series if "p0" in sr and sr["kind"] != "overflow"]
    phase = []
    for sr in series:
        if "p0" in sr and sr["kind"] != "overflow":
            i = int(np.searchsorted(dl, sr["t0"], side="right")) - 1
            if i >= 0:
                phase.append(sr["t0"] - int(end_slot[i]))
    full = [int(te[j] - ts[j]) for sr in series if sr["kind"] == "ok" for j in sr.get("turns", [])[:-1]]
    last = [int(te[sr["turns"][-1]] - ts[sr["turns"][-1]]) for sr in series if sr["kind"] == "ok" and sr.get("turns")]
    after = [int(te[sr["after"]] - ts[sr["after"]]) for sr in series if sr["kind"] == "ok" and "after" in sr]
    step = [int(ts[j + 1] - ts[j]) for sr in series if sr["kind"] == "ok" for j in sr.get("turns", [])]
    dur = [sr["end"] - sr["t0"] for sr in series if sr["kind"] == "ok"]

    # Model stanu puli (K1', gotowosc): wejscie = koniec P0 (niegotowy), gotowy = koniec serii, oddanie = renameat
    # z puli (pierwszy gotowy), przepelnienie = zwolnienie najstarszego przed wejsciem.
    pouts = pool_out_events(events, conns, maps, kills, rt)
    tl = []
    for n_, sr in enumerate(series):
        if side == "B":
            continue
        w = kills[sr["ci"]]
        if w["kill_ret"] != -A.ESRCH:
            continue
        if sr["kind"] == "overflow":
            tl.append((w["t_munmap"], 0, "evict", n_))
        tl.append((w["t1"], 1, "enter", n_))
        tl.append((sr["end"], 2, "ready", n_))
    tl += [(t0, 3, "out", ci) for ci, t0, _ in pouts]
    tl += [(m["w0"], 3, "create", ci) for ci, m in enumerate(maps) if m is not None]
    pool, viol = [], []
    for t, _, kind, ref in sorted(tl):
        if kind == "evict":
            if pool:
                pool.pop(0)
        elif kind == "enter":
            pool.append([ref, False])
        elif kind == "ready":
            for e in pool:
                if e[0] == ref:
                    e[1] = True
        elif kind == "out":
            r = next((e for e in pool if e[1]), None)
            if r is None:
                viol.append(f"oddanie z puli bez wpisu gotowego (podlaczenie {ref})")
            else:
                pool.remove(r)
        elif kind == "create" and any(e[1] for e in pool):
            viol.append(f"kolejka utworzona przy gotowym wpisie (podlaczenie {ref})")
    late = []
    for sr in series:
        if side == "B":
            continue
        nxt = next((c["start"] for c in conns if c["start"] > sr["t_kill"]), None)
        if nxt is not None and sr["end"] >= nxt:
            late.append(sr["ci"])
    tail_overflow = sum(1 for sr in series if sr["kind"] == "overflow" and sr["t_kill"] > conns[-1]["start"])

    # Opisowo: max e2e okna wobec pseudo-zdarzen R600/R603C (z kontrola R603D), osobno P0 i P1..Pk.
    series_span = (conns[0]["start"] - A.SERIES_PAD_NS, conns[-1]["end"] + A.SERIES_PAD_NS)
    desc = {}
    for part in ("P0", "Pk"):
        wins = [(sr["windows"][0] if part == "P0" else None) for sr in series if sr["kind"] == "ok"]
        if part == "Pk":
            wins = [w for sr in series if sr["kind"] == "ok" for w in sr["windows"][1:]]
        ev = []
        for a, b in wins:
            mask = (dl <= b) & (end_slot >= a)
            if mask.any():
                ev.append(int(s["e2e"][mask].max()))
        ps = A.pseudo_events(dl, end_slot, s["e2e"], ctl, [b - a for a, b in wins], series_span, rngs["pseudo"]) if wins else []
        desc[part] = {"ev": ev, "ps": ps, "n_win": len(wins)}

    in_series = (dl >= series_span[0]) & (dl <= series_span[1])
    return {"meta": meta, "side": side, "fam": fam, "base": base, "series": series, "h0": h0, "model": model,
            "ctl": {kk: s[kk][ctl] for kk in ("e2e", "compute", "wake")}, "n_conns": len(conns), "k": k, "k_mmap": k_mmap,
            "caps": caps, "turns": (ts, te), "comm_tid": comm_tid, "sleep_other": sleep_other, "idle_len": idle_len,
            "o3": {"p0": p0_len, "phase": phase, "full": full, "last": last, "after": after, "step": step, "dur": dur},
            "pool_viol": viol, "late": late, "pool_out_n": len(pouts), "tail_overflow": tail_overflow, "desc": desc,
            "comm_ev_n": len(comm_ev), "trace_span": (events[0][0], events[-1][0]) if events else (0, 0),
            "slots_in_series": int(in_series.sum()), "conns": conns}


# ---------------------------------------------------------------- raport

def dist(a, qs=(50, 99, 100)):
    return " / ".join(fmt_us(pct(a, q)) if len(a) else "-" for q in qs)


def k1_side(rs):
    """K1' jednej strony: (werdykt, opis)."""
    if not rs:
        return "brak strony", ""
    k1 = lambda key: sum(r["base"]["k1"][key] for r in rs)  # noqa: E731
    n = sum(r["n_conns"] for r in rs)
    excluded = k1("explained")
    unexplained = sum(r["base"]["k1"]["pairs_working_unexplained"] + r["base"]["k1"]["erased_other"]
                      + r["base"]["k1"]["no_kill_reaped"] for r in rs)
    pool_ok = k1("pool_in") == n - excluded
    tail_ok = all(r["base"]["k1"]["tail_outside_overflow"] == 0 and r["base"]["k1"]["overflow"]
                  == max(0, r["base"]["k1"]["created"] - r["base"]["k1"]["erased_total"] - A.POOL) for r in rs)
    pos_ok = all(r["tail_overflow"] >= 1 for r in rs)
    viol = sum(len(r["pool_viol"]) for r in rs)
    late = sum(len(r["late"]) for r in rs)
    if not pos_ok:
        v = "NIEROZSTRZYGNIĘTE (aparatura: kontrola dodatnia - przebieg bez przepełnienia w ogonie)"
    elif n and excluded / n > A.EXCLUDED_MAX:
        v = f"NIEROZSTRZYGNIĘTE (aparatura: wyłączenia {excluded} z {n})"
    elif unexplained == 0 and pool_ok and tail_ok and viol == 0 and late == 0:
        v = "ZDANE"
    else:
        v = "NIEZDANE"
    txt = (f"do puli {k1('pool_in')} z {n} (wyłączenia {excluded}: martwy muteks {k1('dead_mutex')}, niezebrany "
           f"{k1('not_reaped')}), pary w fazie pracy niewyjaśnione {k1('pairs_working_unexplained')}, zwolnienia bez puli "
           f"niewyjaśnione {k1('erased_other') + k1('no_kill_reaped')}, kolejki utworzone / z puli {k1('created')} / "
           f"{k1('pool_out')}, przepełnienia {k1('overflow')} (w ogonie: każdy przebieg ≥ 1 - {'tak' if pos_ok else 'NIE'}), "
           f"spójność ogona {'tak' if tail_ok else 'NIE'}, model puli: naruszeń {viol}, serii niegotowych przed "
           f"następnym podłączeniem {late}")
    return v, txt


def k2_verdict(x, thr, valid, power=True):
    if x["n"] < MIN_SLOTS or x["series_exposed"] < MIN_SERIES:
        return f"NIEROZSTRZYGNIĘTE (n = {x['n']} slotów, {x['series_exposed']} serii z narażeniem)"
    if valid is not True:
        return f"NIEROZSTRZYGNIĘTE (miara: {valid})"
    if not power:
        return "opisowo (kontrola dodatnia C bez mocy)"
    return x["_v"](thr)


def with_verdict(x, i):
    def v(thr):
        lo, hi = x["lo"][i], x["hi"][i]
        if hi < thr:
            return "ZDANE"
        if lo > thr:
            return "NIEZDANE"
        return "NIEROZSTRZYGNIĘTE (przedział zawiera próg)"
    return dict(x, _v=v)


def k2_fmt(x, i, scale, unit):
    if x["n"] == 0:
        return f"0 slotów ({x['series']} serii)"
    val = x["dc"] if i == 0 else x["dm"]
    return (f"{val * scale:+.2f} {unit} ({x['lo'][i] * scale:+.2f}..{x['hi'][i] * scale:+.2f}); n = {x['n']}, "
            f"serie {x['series_exposed']}/{x['series']}")


def k2_family(runs, rng):
    """Klastry i podsumowania K2 rodziny: C, C' i H0 (jedno losowanie bootstrapu na wielkosc)."""
    cl = {sd: [sr["cluster"] for r in runs if r["side"] == sd for sr in r["series"] if sr["kind"] == "ok"]
          for sd in ("C", "Cp")}
    k2 = {sd: k2_summary(v, rng) for sd, v in cl.items()}
    k2["H0"] = k2_summary([c for r in runs if r["side"] == "C" for c in r["h0"]], rng)
    return cl, k2


def family_report(fam, runs, rngs, cl, k2, ctx):
    C = [r for r in runs if r["side"] == "C"]
    P = [r for r in runs if r["side"] == "Cp"]
    period = int(np.median([r["model"].period for r in runs]))
    lines = [f"## {fam}", "", f"Takt slotu: {period / 1e6:.3f} ms, H = {H[fam]}, k = {PORTIONS[fam]} "
             f"(z pojemności mmap: {sorted({x for r in runs for x in r['k_mmap']})}, pojemność "
             f"{sorted({x for r in runs for x in r['caps']})}).", "", "| wielkość | C | C' |", "|---|---|---|"]

    def row(label, f):
        lines.append(f"| {label} | {f(C) if C else '-'} | {f(P) if P else '-'} |")

    def ser(rs, kind):
        return [sr for r in rs for sr in r["series"] if sr["kind"] == kind]

    row("przebiegi / podłączenia", lambda x: f"{len(x)} / {sum(r['n_conns'] for r in x)}")
    row("serie: niezakłócone / przepełnienia / zakłócone", lambda x: f"{len(ser(x, 'ok'))} / {len(ser(x, 'overflow'))} / "
        f"{len(ser(x, 'disturbed'))}")
    row("O5: powody zakłóceń", lambda x: "; ".join(sorted({sr['reason'] for sr in ser(x, 'disturbed')})) or "-")
    row("O3: P0 [µs] p50 / p99 / max", lambda x: dist([v for r in x for v in r["o3"]["p0"]]))
    row("O3: faza P0 po końcu slotu [µs] p5 / p50 / p95", lambda x: dist([v for r in x for v in r["o3"]["phase"]], (5, 50, 95)))
    row("O3: pełna porcja P1..Pk-1 [µs] p50 / p99 / max", lambda x: dist([v for r in x for v in r["o3"]["full"]]))
    row("O3: ostatnia porcja Pk [µs] p50 / p99 / max", lambda x: dist([v for r in x for v in r["o3"]["last"]]))
    row("O3: obrót Pk+1 [µs] p50 / p99 / max", lambda x: dist([v for r in x for v in r["o3"]["after"]]))
    row("O3: obrót bezczynny [µs] p50 / p99 / max", lambda x: dist(np.concatenate([r["idle_len"] for r in x])))
    row("O3: odstęp obrotów w serii [µs] p50 / p99 / max", lambda x: dist([v for r in x for v in r["o3"]["step"]]))
    row("O3: seria P0..Pk [ms] p50 / max", lambda x: (lambda v: f"{A.fmt_ms(pct(v, 50))} / {A.fmt_ms(pct(v, 100))}")(
        [v for r in x for v in r["o3"]["dur"]]))

    # K1'.
    kc, tc = k1_side(C)
    kp, tp = k1_side(P)
    # K2.
    h0 = k2["H0"]
    row("K2a Δ_c [µs] (95 % bootstrap); n slotów; serie z narażeniem", lambda x: k2_fmt(k2["C" if x is C else "Cp"], 0, 1e-3, "µs"))
    row("K2b Δ_m [pp] (95 % bootstrap)", lambda x: k2_fmt(k2["C" if x is C else "Cp"], 1, 100, "pp"))
    lines.append(f"| H0 (syntetyczne serie porcji na tle C) K2a / K2b | {k2_fmt(h0, 0, 1e-3, 'µs')} | "
                 f"{k2_fmt(h0, 1, 100, 'pp')} |")
    for part, label in (("P0", "P0"), ("Pk", "P1..Pk")):
        def d(x, part=part):
            ev = [v for r in x for v in r["desc"][part]["ev"]]
            ps = [v for r in x for v in r["desc"][part]["ps"]]
            nw = sum(r["desc"][part]["n_win"] for r in x)
            if not ev or not ps:
                return f"okna {nw}, trafione {len(ev)}"
            return (f"okna {nw}, trafione {len(ev)}, Δ_e2e {(pct(ev, 50) - pct(ps, 50)) / 1e3:.2f} µs, "
                    f"MW p = {A.mann_whitney_greater(ev, ps):.3g}")
        row(f"opisowo {label}: max e2e okna wobec pseudo-zdarzeń", d)
    no4 = {sd: o4_cost(v) for sd, v in cl.items()}
    row("O4: sloty narażone na serię ponad placebo (średnia)", lambda x: f"{no4['C' if x is C else 'Cp'][0].mean():.2f}"
        if len(no4["C" if x is C else "Cp"][0]) else "-")
    row("O4: suma odchyleń na serię ponad placebo [µs] (średnia)", lambda x: f"{no4['C' if x is C else 'Cp'][1].mean() / 1e3:.1f}"
        if len(no4["C" if x is C else "Cp"][1]) else "-")
    for k in ("e2e", "compute", "wake"):
        row(f"kontrola {k} [µs] p50 / p99 / max", lambda x, k=k: dist(np.concatenate([r["ctl"][k] for r in x])))
    o1 = lambda x, key: sum(r["base"]["o1"][key] for r in x)  # noqa: E731
    row("O1: futex wątku RT: sloty z futex / sloty w serii", lambda x: f"{o1(x, 'slots_with_futex')} / {o1(x, 'slots')} "
        f"({100.0 * o1(x, 'slots_with_futex') / max(1, o1(x, 'slots')):.3f} %)")
    row("O1: FUTEX_WAIT na muteksie kolejki: liczba / max [µs] / w oknie R_C / slot > takt", lambda x: (
        lambda v: f"{len(v)} / {fmt_us(pct(v, 100)) if v else '-'} / {o1(x, 'wait_in_window')} / {o1(x, 'wait_over_period')}")(
        [v for r in x for v in r["base"]["o1"]["wait_ns"]]))
    for kind, label in (("created", "kolejka utworzona"), ("pooled", "kolejka z puli")):
        row(f"O2: podłączenie, {label}: liczba / okno p50 [ms]", lambda x, kind=kind: (
            lambda ev: f"{len(ev)} / {A.fmt_ms(pct([e['len_ns'] for e in ev], 50))}")(
            [e for r in x for e in r["base"]["o2"] if e["kind"] == kind]))
    lines.append("")

    lines.append(f"- **K1'** C': {tp}. Werdykt C': **{kp}**.")
    lines.append(f"- K1' C (opisowo, powtórzenie R603C): {tc}. Werdykt C: {kc}.")
    h0_ok = (h0["n"] > 0 and not math.isnan(h0["lo"][0]) and -H0_BOUND_NS <= h0["lo"][0] and h0["hi"][0] <= H0_BOUND_NS)
    valid_a = True if ctx["pos_c_ok"] and h0_ok else (
        "kontrola dodatnia C w uc05/uc06 niespełniona" if not ctx["pos_c_ok"] else
        f"kontrola H0 poza ±{H0_BOUND_NS / 1e3:.0f} µs albo bez narażenia")
    power_b = k2["C"]["n"] > 0 and not math.isnan(k2["C"]["lo"][1]) and k2["C"]["lo"][1] > DELTA_M
    va = k2_verdict(with_verdict(k2["Cp"], 0), DELTA_C_NS, valid_a)
    vb = k2_verdict(with_verdict(k2["Cp"], 1), DELTA_M, True, power_b)
    vac = k2_verdict(with_verdict(k2["C"], 0), DELTA_C_NS, True)
    lines.append(f"- **K2a** (próg δ_c = {DELTA_C_NS / 1e3:.0f} µs): C' {k2_fmt(k2['Cp'], 0, 1e-3, 'µs')}. Kontrola H0: "
                 f"{k2_fmt(h0, 0, 1e-3, 'µs')} - {'w' if h0_ok else 'POZA'} ±{H0_BOUND_NS / 1e3:.0f} µs. Werdykt C': **{va}**. "
                 f"C (opisowo): {vac}.")
    lines.append(f"- **K2b** (próg δ_m = {100 * DELTA_M:.0f} pp, werdykt tylko przy mocy kontroli C): C' "
                 f"{k2_fmt(k2['Cp'], 1, 100, 'pp')}; kontrola C {k2_fmt(k2['C'], 1, 100, 'pp')} - moc "
                 f"{'jest' if power_b else 'brak'}. Werdykt C': **{vb}**.")
    u, ulo, uhi = ratio_boot(cl["Cp"], cl["C"], rngs["boot"])
    lines.append(f"- K2 opisowo: u' = Δ_c(C') / Δ_c(C) = {u:.2f} (95 % bootstrap {ulo:.2f}..{uhi:.2f}).")
    on = o4_boot(no4["Cp"][0], no4["C"][0], rngs["boot"])
    od = o4_boot(no4["Cp"][1], no4["C"][1], rngs["boot"])
    lines.append(f"- **O4** koszt na porzucenie C' - C: sloty narażone ponad placebo {on[0]:+.2f} ({on[1]:+.2f}..{on[2]:+.2f}), "
                 f"suma odchyleń ponad placebo {od[0] / 1e3:+.1f} µs ({od[1] / 1e3:+.1f}..{od[2] / 1e3:+.1f}).")
    for key, q, label in (("compute", 50, "compute_ns p50"), ("wake", 99, "wake_lag_ns p99"), ("e2e", 99, "e2e_ns p99")):
        c = [pct(r["ctl"][key], q) for r in C]
        p = [pct(r["ctl"][key], q) for r in P]
        c, p = [x for x in c if not math.isnan(x)], [x for x in p if not math.isnan(x)]
        if not (c and p):
            lines.append(f"- **K3**, {label}: brak danych obu stron.")
            continue
        diff = float(np.median(p) - np.median(c))
        spread = max(max(c) - min(c), max(p) - min(p))
        pv = A.permutation_mw_two_sided(c, p)
        state = "w szumie" if abs(diff) <= spread else ("REGRESJA C' - osobne znalezisko" if diff > 0 else "C' lepsze poza szumem")
        lines.append(f"- **K3**, {label} per przebieg: mediana C' - C = {diff / 1e3:.2f} µs, rozrzut wewnątrz strony do "
                     f"{spread / 1e3:.2f} µs, permutacyjny MW p = {pv:.3g} - {state}.")
    lines.append("")
    ctx["verdicts"][fam] = {"K1": kp, "K2a": va, "K2b": vb, "C_K2a": vac}
    return lines


def h0_params(runs_cp, k):
    """Parametry syntetycznych serii H0 z danych C' (README, K2, Waznosc miary)."""
    p0 = [v for r in runs_cp for v in r["o3"]["p0"]]
    full = [v for r in runs_cp for v in r["o3"]["full"]] or [v for r in runs_cp for v in r["o3"]["last"]]
    step = [v for r in runs_cp for v in r["o3"]["step"]]
    ph = [v for r in runs_cp for v in r["o3"]["phase"]]
    par = dict(H0_DEFAULT, k=k)
    if p0:
        par["p0_ns"] = int(pct(p0, 50))
    if full:
        par["w_ns"] = int(pct(full, 50))
    if step:
        par["turn_ns"] = int(pct(step, 50))
    if len(ph) >= 20:
        lo, hi = int(pct(ph, 5)), int(pct(ph, 95))
        if hi > lo:
            par["phase"] = (max(0, lo), hi)
    return par


def rng_set(seed):
    return {"placebo": np.random.default_rng(seed), "boot": np.random.default_rng(seed + 1),
            "h0": np.random.default_rng(seed + 2), "pseudo": np.random.default_rng(seed + 3),
            "base": np.random.default_rng(seed + 4)}


def run_dirs(fam_dir, side):
    return sorted(p for p in fam_dir.iterdir() if p.is_dir() and p.name.startswith(f"{side}_"))


def main_report(raw, seed, out):
    rngs = rng_set(seed)
    fams = {}
    for fam_dir in sorted(p for p in raw.iterdir() if p.is_dir()):
        fam = fam_dir.name
        cp = [analyze_run(d, rngs) for d in run_dirs(fam_dir, "Cp")]
        for r in cp:
            if any(x != PORTIONS[fam] for x in r["k_mmap"]):
                die(f"{fam}: k z pojemności mmap {r['k_mmap']} różne od {PORTIONS[fam]} - przesłanka protokołu nie zachodzi")
        par = h0_params(cp, PORTIONS[fam])
        c = [analyze_run(d, rngs, h0_par=par) for d in run_dirs(fam_dir, "C")]
        fams[fam] = (c + cp, par, *k2_family(c + cp, rngs["boot"]))
    # Kontrola dodatnia C (uc05 i uc06) potrzebna przed werdyktami K2a wszystkich rodzin.
    pos = {fam: fams[fam][3]["C"] for fam in ("uc05", "uc06") if fam in fams}
    ctx = {"pos_c_ok": all(fam in pos and pos[fam]["n"] and pos[fam]["lo"][0] > DELTA_C_NS for fam in ("uc05", "uc06")),
           "verdicts": {}}
    report = ["# R603D - wynik", "", f"Źródło: `{raw.name}`, ziarna: placebo {seed}, bootstrap {seed + 1}, H0 {seed + 2}, "
              f"pseudo-zdarzenia {seed + 3}.", "",
              "Kontrola dodatnia C dla ważności K2a (dolna granica Δ_c > δ_c): " + ", ".join(
                  f"{f} {fmt_us(pos[f]['lo'][0], 2)} µs" for f in pos) + f" - {'spełniona' if ctx['pos_c_ok'] else 'NIESPEŁNIONA'}.",
              ""]
    for fam, (runs, par, cl, k2) in fams.items():
        report += [f"Parametry H0 {fam}: P0 {par['p0_ns'] / 1e3:.1f} µs, porcja {par['w_ns'] / 1e3:.1f} µs, obrót "
                   f"{par['turn_ns'] / 1e3:.1f} µs, faza {par['phase'][0] / 1e3:.0f}..{par['phase'][1] / 1e3:.0f} µs, "
                   f"rozrzut {par['jitter_ns'] / 1e3:.0f} µs.", ""]
        report += family_report(fam, runs, rngs, cl, k2, ctx)
    report += ["## Werdykty", "", "| rodzina | K1' C' | K2a C' | K2b C' | K2a C (opisowo) |", "|---|---|---|---|---|"]
    for fam, v in ctx["verdicts"].items():
        report.append(f"| {fam} | {v['K1']} | {v['K2a']} | {v['K2b']} | {v['C_K2a']} |")
    text = "\n".join(report) + "\n"
    if out:
        out.write_text(text)
    print(text)


# ---------------------------------------------------------------- bramki suchego przebiegu

def gate_h(runs):
    """Bramka H (aneks 1): argmin h* mediany |compute(i) - compute(i - h)| po h = 1..2H, wszystkie sloty strony."""
    out = []
    for side in ("C", "Cp"):
        rs = [r for r in runs if r["side"] == side]
        if not rs:
            continue
        h = H[rs[0]["fam"]]
        med = {}
        for hh in range(1, 2 * h + 1):
            med[hh] = float(np.median(np.concatenate([np.abs(r["model"].comp[hh:] - r["model"].comp[:-hh]) for r in rs])))
        order = sorted(med, key=lambda x: (med[x], x))
        hs = order[0]
        ok = h % hs == 0 and med[h] <= med[hs] * (1 + H_TOL)
        out.append((side, h, order[:4], [round(med[x] / 1e3, 3) for x in order[:4]], ok, hs == h))
    return out


def gates(raw):
    rngs = rng_set(6034)
    ok_all = True
    for fam_dir in sorted(p for p in raw.iterdir() if p.is_dir()):
        fam = fam_dir.name
        runs = [analyze_run(d, rngs) for side in ("C", "Cp") for d in run_dirs(fam_dir, side)]
        print(f"## {fam} (k = {PORTIONS[fam]}, H = {H[fam]})")
        for r in runs:
            ts, te = r["turns"]
            span_ms = (r["trace_span"][1] - r["trace_span"][0]) / 1e6
            per = np.diff(ts)
            busy = [(c["start"], c["end"]) for c in r["conns"]] + [(sr["t_kill"], sr["end"]) for sr in r["series"]]
            free = np.ones(len(per), dtype=bool)
            for a, b in busy:
                free &= ~((ts[1:] >= a) & (ts[:-1] <= b))
            cover = (ts[-1] - ts[0]) / 1e6 if len(ts) else 0.0
            maxgap = int(per[free].max()) if free.any() else 0
            g1 = (r["meta"].get("trace_overrun", 0) == 0 and len(ts) > 0 and 1.0 <= np.median(per) / 1e6 <= 1.2
                  and cover >= 0.95 * span_ms and maxgap < 5_000_000 and r["sleep_other"] == 0)
            print(f"- {r['meta']['side']}_{r['meta']['run']:02d}: G1 {'OK' if g1 else 'NIE'}: overrun "
                  f"{r['meta'].get('trace_overrun')}, obrotów {len(ts)} na {span_ms:.0f} ms śladu (pokrycie {cover:.0f} ms, "
                  f"{len(ts) / max(1.0, cover):.3f}/ms), odstęp p50 {np.median(per) / 1e3:.1f} µs, max poza podłączeniami i "
                  f"seriami {maxgap / 1e3:.1f} µs, sen innych wątków spoza RT {r['sleep_other']}, wątek {r['comm_tid']}")
            ok_all &= g1
            idle = r["idle_len"]
            p999, p99 = (pct(idle, 99.9), pct(idle, 99)) if len(idle) else (np.nan, np.nan)
            if r["side"] == "Cp":
                good = 0
                ser = [sr for sr in r["series"] if sr["kind"] == "ok"]
                for sr in ser:
                    if not sr.get("turns"):
                        continue
                    lens = [int(te[j] - ts[j]) for j in sr["turns"]]
                    a = all(v > p999 for v in lens[:-1])
                    b = int(te[sr["after"]] - ts[sr["after"]]) <= p99
                    good += a and b
                need = [sr for sr in ser if sr.get("turns")]
                g2 = len(need) > 0 and good == len(need) if PORTIONS[fam] > 0 else True
                print(f"  G2 {'OK' if g2 else 'NIE'}: serii niezakłóconych {len(ser)} (z obrotami {len(need)}), spełnia oba "
                      f"warunki {good}; obrót bezczynny p99 / p99,9 / max {fmt_us(p99)} / {fmt_us(p999)} / "
                      f"{fmt_us(pct(idle, 100))} µs (n = {len(idle)}); pełna porcja p50 / min "
                      f"{fmt_us(pct(r['o3']['full'], 50))} / {fmt_us(pct(r['o3']['full'], 0))} µs; Pk p50 "
                      f"{fmt_us(pct(r['o3']['last'], 50))} µs; Pk+1 p50 / max {fmt_us(pct(r['o3']['after'], 50))} / "
                      f"{fmt_us(pct(r['o3']['after'], 100))} µs; zakłócone "
                      f"{sum(sr['kind'] == 'disturbed' for sr in r['series'])} "
                      f"({'; '.join(sorted({sr['reason'] for sr in r['series'] if sr['kind'] == 'disturbed'})) or '-'})")
                ok_all &= g2
            v, txt = k1_side([r])
            k1 = r["base"]["k1"]
            # Suchy przebieg: kontrola dodatnia (przepelnienie w ogonie) wymaga 3 porzucen po zapelnieniu puli; przy 10
            # podlaczeniach to tez zachodzi, ale G3 pyta o rozpoznawalnosc licznikow, nie o werdykt.
            g3 = k1["kill_client"] > 0 and k1["pool_in"] > 0 and k1["pool_out"] > 0 and not r["pool_viol"] and not r["late"]
            print(f"  G3 {'OK' if g3 else 'NIE'}: {txt}; kill klienta {k1['kill_client']}, wartości kill {k1['kill_ret']}; "
                  f"werdykt na tym przebiegu: {v}; k z mmap {r['k_mmap']} (pojemność {r['caps']})")
            ok_all &= g3 and all(x == PORTIONS[fam] for x in r["k_mmap"])
            o1 = r["base"]["o1"]
            frac = o1["slots_with_futex"] / max(1, o1["slots"])
            g4 = frac <= 0.01
            print(f"  G4 {'OK' if g4 else 'NIE'}: futex wątku slotu w {100 * frac:.3f} % slotów ({o1['slots_with_futex']} / "
                  f"{o1['slots']}); FUTEX_WAIT na muteksie kolejki {len(o1['wait_ns'])}")
            ok_all &= g4
            run_dir = fam_dir / f"{r['meta']['side']}_{r['meta']['run']:02d}"
            sizes = {p.name: (p.stat().st_size, len(gzip.compress(p.read_bytes(), 6))) for p in run_dir.iterdir() if p.is_file()}
            tot = sum(v[1] for v in sizes.values())
            print(f"  G5: trace.txt {sizes['trace.txt'][0] / 1e6:.1f} MB (gzip {sizes['trace.txt'][1] / 1e6:.1f} MB), "
                  f"przebieg po gzip {tot / 1e6:.1f} MB, skalowane na 30 podłączeń ×{30 / r['n_conns']:.1f}")
        for side, h, order, meds, ok, exact in gate_h(runs):
            print(f"- H {side}: {'OK' if ok else 'NIE'}: najmniejsze mediany |Δ compute| przy h = {order} ({meds} µs); "
                  f"argmin {'=' if exact else '≠'} H = {h}")
            ok_all &= ok
        print()
    print("BRAMKI: " + ("wszystkie spełnione" if ok_all else "CO NAJMNIEJ JEDNA NIESPEŁNIONA - decyzja człowieka"))
    return ok_all


# ---------------------------------------------------------------- test parsera na danych R603C

# Tabela README R603D, Ustalenia, punkt 4 (k2_resolution.py, ziarno 6034): (n, Δ_c, lo, hi) w µs.
EXPECTED_K2 = {("uc03", "B"): (34, 34.99, 29.77, 40.82), ("uc03", "C"): (0,), ("uc03", "H0"): (80, -0.17, -0.50, 0.16),
               ("uc05", "B"): (1760, 11.09, 10.39, 11.85), ("uc05", "C"): (599, 47.26, 39.72, 52.13),
               ("uc05", "H0"): (1440, 0.06, -0.06, 0.18), ("uc06", "B"): (716, 28.38, 25.61, 31.61),
               ("uc06", "C"): (330, 94.07, 77.74, 100.42), ("uc06", "H0"): (893, -0.26, -0.46, -0.11),
               ("uc07", "B"): (0,), ("uc07", "C"): (0,), ("uc07", "H0"): (0,), ("uc08", "B"): (0,), ("uc08", "C"): (0,),
               ("uc08", "H0"): (0,)}
EXPECTED_N = {"uc03": 2000, "uc05": 8000, "uc06": 5000, "uc07": 500, "uc08": 100}


def parser_check(raw):
    bad = 0
    # 1. Wydruk R603C (okna R_C, K1', O1, O2, K2 i K3 w postaci R603C) identyczny z wynik.md R603C.
    wynik = (HERE.parent / "results_20261105_R603C" / "wynik.md").read_text()
    ref = wynik.split("## Wydruk analizy", 1)[1].strip().splitlines()
    rng, rng_boot = np.random.default_rng(6031), np.random.default_rng(6032)
    got = []
    for fam_dir in sorted(p for p in raw.iterdir() if p.is_dir()):
        runs = [A.analyze_run(d, rng) for d in sorted(p for p in fam_dir.iterdir() if p.is_dir())]
        got += A.family_report(fam_dir.name, runs, rng_boot)
    got = [("### " + l[3:]) if l.startswith("## ") else l for l in got]
    got = "\n".join(got).strip().splitlines()
    nd = sum(1 for a, b in zip(ref, got) if a != b) + abs(len(ref) - len(got))
    print(f"1. wydruk parsera R603C wobec wynik.md R603C: {len(got)} wierszy, różnic {nd}")
    for a, b in [(a, b) for a, b in zip(ref, got) if a != b][:5]:
        print(f"   wynik.md: {a}\n   teraz:    {b}")
    bad += nd != 0

    # 2. Czesc R603D na stronie C R603C: serie = okna R_C, model puli bez naruszen, pojemnosci, oddania z puli.
    # 3. K2 klasowe = tabela Ustalen (kolejnosc losowan k2_resolution.py, jedno ziarno 6034).
    rng = np.random.default_rng(6034)
    rngs = {"placebo": rng, "h0": rng, "boot": rng, "pseudo": np.random.default_rng(1), "base": np.random.default_rng(2)}
    for fam_dir in sorted(p for p in raw.iterdir() if p.is_dir()):
        fam = fam_dir.name
        for side in ("B", "C"):
            runs, real, null = [], [], []
            for d in run_dirs(fam_dir, side):
                r = analyze_run(d, rngs, h0_par=dict(H0_DEFAULT, k=PORTIONS[fam]) if side == "C" else None)
                runs.append(r)
                real += [sr["cluster"] for sr in r["series"] if sr["kind"] == "ok"]
                null += r["h0"]
            res = [(side, k2_summary(real, rng))]
            if side == "C":
                res.append(("H0", k2_summary(null, rng)))
                nwin = sum(len(r["base"]["windows"]) for r in runs)
                nser = sum(1 for r in runs for sr in r["series"] if sr["kind"] == "ok")
                viol = sum(len(r["pool_viol"]) for r in runs)
                late = sum(len(r["late"]) for r in runs)
                pout = all(r["pool_out_n"] == r["base"]["k1"]["pool_out"] for r in runs)
                caps = sorted({x for r in runs for x in r["caps"]})
                kk = sorted({x for r in runs for x in r["k_mmap"]})
                ok2 = nwin == nser and viol == 0 and late == 0 and pout and caps == [EXPECTED_N[fam]] and kk == [PORTIONS[fam]]
                print(f"2. {fam} C: okna R_C parsera R603C {nwin}, serie R603D {nser}; model puli: naruszeń {viol}, "
                      f"niegotowych przed podłączeniem {late}; oddania z puli zgodne {pout}; pojemność {caps}, k {kk} - "
                      f"{'OK' if ok2 else 'RÓŻNICA'}")
                bad += not ok2
            for tag, x in res:
                exp = EXPECTED_K2[(fam, tag)]
                if exp[0] == 0:
                    ok3 = x["n"] == 0
                    shown = f"n = {x['n']}"
                else:
                    shown = (f"n = {x['n']}, Δ_c {x['dc'] / 1e3:+.2f} ({x['lo'][0] / 1e3:+.2f}..{x['hi'][0] / 1e3:+.2f}), "
                             f"Δ_m {100 * x['dm']:+.2f} pp")
                    ok3 = (x["n"] == exp[0] and round(x["dc"] / 1e3, 2) == exp[1] and round(x["lo"][0] / 1e3, 2) == exp[2]
                           and round(x["hi"][0] / 1e3, 2) == exp[3])
                print(f"3. {fam} {tag}: {shown} - {'OK' if ok3 else 'RÓŻNICA wobec tabeli ' + str(exp)}")
                bad += not ok3
    print(f"parser-check: {'ZDANY' if bad == 0 else f'NIEZDANY ({bad} różnic)'}")
    return bad == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--seed", type=int, default=6034)
    ap.add_argument("--parser-check", action="store_true", help="--raw wskazuje surowe dane R603C")
    ap.add_argument("--gates", action="store_true", help="--raw wskazuje suchy przebieg R603D")
    args = ap.parse_args()
    if args.parser_check:
        sys.exit(0 if parser_check(args.raw) else 2)
    if args.gates:
        sys.exit(0 if gates(args.raw) else 2)
    main_report(args.raw, args.seed, args.out)


if __name__ == "__main__":
    main()
