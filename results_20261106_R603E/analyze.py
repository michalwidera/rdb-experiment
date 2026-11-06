#!/usr/bin/env python3
"""R603E: analiza przebiegow run_one.py wedlug kryteriow K1'', K2e, K2s, K3 i obserwacji z README.md.

Uzycie: analyze.py --raw KATALOG [--out RAPORT.md] [--seed 6034]
        analyze.py --raw KATALOG_SUCHY --gates               (bramki G1, G2', G3-G5 i H suchego przebiegu)
        analyze.py --raw SUROWE_R603D --parser-check          (test parsera na danych R603D, README, Kolejnosc, punkt 3)
KATALOG ma uklad <rodzina>/<strona>_<para>/ ze stronami Cp i Cpp (slots.csv z kolumna P1, trace.txt, conns.tsv,
rt.txt, meta.json). Kod wyjscia: 0 - raport zapisany / test zdany, 2 - blad danych albo test niezdany.
Wymaga NumPy (np. retractordb/.venv-python).

Parser R603D (a przez niego R603C) jest importowany BEZ ZMIAN z ../results_20261105_R603D/analyze.py; strona C'
idzie przez jego analyze_run. Strona C'' idzie przez analyze_run_e - kopie D.analyze_run, w ktorej jedyna zmiana
to wybor obrotow P1..Pk: w C' k kolejnych obrotow po obrocie z P0, w C'' pierwsze k obrotow z otwarta bramka
modelu (albo po kDrainGateMaxDeferrals kolejnych odroczeniach). --parser-check sprawdza, ze kopia z wyborem C'
daje na danych R603D wydruk R603D bajt w bajt. Dochodzi (README R603E, Aparatura, punkt 4, Okna i zdarzenia):
- model bramki ze sladu i slots.csv, obroty graniczne, oczekiwanie P0, kroki wymuszone limitem,
- miara slotow dotknietych (sloty narazone R603D + slot nastepny po kazdym oknie) z placebo - ten sam kod co
  est_affected.py, ta sama kolejnosc losowan,
- K2e (sloty narazone na serie), K2s (koszt serii, T = S(C'') - 0,5 S(C')) z kontrola dodatnia i H0,
- K1'' z warunku (b) modelu stanu puli, warunek (a) i O6 opisowo, K3 C'' wobec C', bramka G2'.
Ziarna: placebo --seed, bootstrap --seed+1, syntetyczne serie H0 --seed+2, pseudo-zdarzenia opisowe --seed+3,
pseudo-zdarzenia wewnatrz parsera R603C --seed+4 (jak R603D). Wydruk to liczby wyprowadzone; zadnej tresci korpusu.
"""

import argparse
import contextlib
import gzip
import importlib.util
import io
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def _load_r603d():
    spec = importlib.util.spec_from_file_location("analyze_r603d", HERE.parent / "results_20261105_R603D" / "analyze.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = _load_r603d()
A = D.A

RES_PORTION_NS = 200_000  # kDrainBatchSlotReserve w C''
RES_P0_NS = 500_000  # kAbandonedQueueSlotReserve w C''
MAX_DEFERRALS = 100  # kDrainGateMaxDeferrals w C''
BOUNDARY_NS = 20_000  # obrot graniczny (README, Okna i zdarzenia)
AFF_TRIES = 200  # proby placebo miary slotow dotknietych (est_affected.py)
E_THR = 0.2  # K2e
E_POS = 1.0  # K2e: kontrola dodatnia C'
T_FACTOR = 0.5  # K2s (D1)
H0_HALF_MAX = 0.25  # K2s: polszerokosc przedzialu H0 wobec S(C')
G2_FRAC = 0.99  # G2'


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


pct = D.pct
fmt_us = D.fmt_us
dist = D.dist


# ---------------------------------------------------------------- model bramki C''

def gate_state(dl, end, t, reserve):
    """Bramka C'' w chwili t: (otwarta, margines do granicy w ns).

    Opublikowany termin = deadline pierwszego slotu j z dl > t, o ile slot j-1 skonczyl sie do t (end <= t); inaczej
    opublikowany termin jest w przeszlosci (slot liczy albo nadrabia) i bramka jest zamknieta. Otwarta, gdy
    t + reserve < dl[j]. Margines = odleglosc t od blizszej z granic: konca slotu j-1 i dl[j] - reserve.
    """
    j = int(np.searchsorted(dl, t, side="right"))
    if j >= len(dl):
        return False, math.inf
    margin = abs(int(dl[j]) - reserve - t)
    ended = True
    if j > 0:
        ended = int(end[j - 1]) <= t
        margin = min(margin, abs(t - int(end[j - 1])))
    return ended and t + reserve < int(dl[j]), margin


def gated_turns(dl, end, ts, j0, k, gated):
    """Obroty P1..Pk po obrocie j0 z P0: (wybrane, zamkniete, wymuszone, graniczne).

    gated=False - wybor C' (R603D): k kolejnych obrotow. gated=True - wybor C'': obrot idzie, gdy bramka modelu
    z rezerwa porcji jest otwarta albo gdy przed nim bylo MAX_DEFERRALS kolejnych odroczen (passDrainGate).
    """
    sel, closed, forced, boundary = [], [], [], []
    defer = 0
    j = j0 + 1
    while len(sel) < k and j < len(ts):
        if not gated:
            sel.append(j)
        else:
            ok, margin = gate_state(dl, end, int(ts[j]), RES_PORTION_NS)
            if margin <= BOUNDARY_NS:
                boundary.append(j)
            if ok or defer >= MAX_DEFERRALS:
                sel.append(j)
                if not ok:
                    forced.append(j)
                defer = 0
            else:
                closed.append(j)
                defer += 1
        j += 1
    return sel, closed, forced, boundary


def p0_wait(dl, end, ts, j0):
    """Gorna granica oczekiwania P0: kolejne obroty z zamknieta bramka P0 tuz przed obrotem z P0.

    Rozpoznanie porzucenia (watek slotu, broadcast) nie zostawia zdarzenia w sladzie; nastapilo po ostatnim
    obrocie z otwarta bramka P0 przed j0, bo inaczej P0 poszloby w nim.
    """
    n, j = 0, j0 - 1
    while j >= 0 and n <= MAX_DEFERRALS and not gate_state(dl, end, int(ts[j]), RES_P0_NS)[0]:
        n += 1
        j -= 1
    return n


# ---------------------------------------------------------------- przebieg

def run_inputs(run_dir):
    events = A.parse_trace(run_dir / "trace.txt")
    rt = A.rt_tids(run_dir / "rt.txt")
    conns = A.load_conns(run_dir / "conns.tsv")
    maps = A.queue_mappings(events, conns, rt)
    kills = A.kill_windows(events, conns, rt) if conns[0]["pid"] is not None else [None] * len(conns)
    pouts = D.pool_out_events(events, conns, maps, kills, rt)
    return events, rt, conns, maps, kills, pouts


def pool_model(series, kills, pouts, maps):
    """Model stanu puli R603D (wejscie = koniec P0, gotowy = koniec serii, oddanie, przepelnienie, tworzenie).

    Zwraca (naruszenia warunku (b), O6 = podlaczenia z kolejka utworzona, gdy pula miala wpisy, ale zaden gotowy).
    """
    tl = []
    for n_, sr in enumerate(series):
        w = kills[sr["ci"]]
        if w["kill_ret"] != -A.ESRCH:
            continue
        if sr["kind"] == "overflow":
            tl.append((w["t_munmap"], 0, "evict", n_))
        tl.append((w["t1"], 1, "enter", n_))
        tl.append((sr["end"], 2, "ready", n_))
    tl += [(t0, 3, "out", ci) for ci, t0, _ in pouts]
    tl += [(m["w0"], 3, "create", ci) for ci, m in enumerate(maps) if m is not None]
    pool, viol, o6 = [], [], []
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
        elif kind == "create":
            if any(e[1] for e in pool):
                viol.append(f"kolejka utworzona przy gotowym wpisie (podlaczenie {ref})")
            elif pool:
                o6.append(ref)
    return viol, o6


def analyze_run_e(run_dir, rngs, gated):
    """Kopia D.analyze_run (strony C' i C''); jedyna zmiana: wybor obrotow P1..Pk przez gated_turns.

    Kolejnosc losowan jak w D.analyze_run (base, placebo klastrow, pseudo-zdarzenia), bez klastrow H0 strony C.
    """
    meta = json.loads((run_dir / "meta.json").read_text())
    base = A.analyze_run(run_dir, rngs["base"])  # sprawdza waznosc przebiegu (rt_ok, governor, binarka, overrun)
    side, fam = meta["side"], meta["family"]
    h = D.H[fam]
    k = D.PORTIONS[fam]
    events = A.parse_trace(run_dir / "trace.txt")
    rt = A.rt_tids(run_dir / "rt.txt")
    tids = D.all_tids(run_dir / "rt.txt")
    conns = A.load_conns(run_dir / "conns.tsv")
    s = A.load_slots(run_dir / "slots.csv")
    dl = s["deadline"]
    end_slot = dl + s["e2e"]
    maps = A.queue_mappings(events, conns, rt)
    pairs, _, _ = A.queue_pairs(events, maps)
    kills = A.kill_windows(events, conns, rt) if conns[0]["pid"] is not None else [None] * len(conns)
    caps = sorted({(m["len"] - D.MQ_HDR) // D.MQ_MSG for m in maps if m is not None})
    k_mmap = [D.capacity_portions(n) for n in caps]
    ts, te, comm_tid, sleep_other = D.comm_turns(events, tids, rt)
    comm_ev = [e for e in events if e[1] == comm_tid and e[2] not in D.SLEEP and e[3] == "enter"] if comm_tid else []
    comm_t = np.array([e[0] for e in comm_ev], dtype=np.int64)

    series = []
    for ci, w in enumerate(kills):
        if w is None or w["t0"] is None or w["t1"] is None:
            continue  # zwolnienie bez puli (martwy muteks, skasowanie) - nie seria drenazu
        sr = {"ci": ci, "t_kill": w["t_kill"], "t0": w["t0"], "p0": (w["t0"], w["t1"]), "windows": [(w["t0"], w["t1"])],
              "end": w["t1"], "kind": "overflow" if w["overflow"] else "ok", "reason": "", "turns": []}
        if k > 0:
            j0 = int(np.searchsorted(ts, w["t0"], side="right")) - 1
            if j0 < 0 or te[j0] < w["t1"]:
                if sr["kind"] == "ok":
                    sr["kind"], sr["reason"] = "disturbed", "P0 poza jednym obrotem"
            else:
                sel, closed, forced, boundary = gated_turns(dl, end_slot, ts, j0, k, gated)
                if gated:
                    ok0, m0 = gate_state(dl, end_slot, int(ts[j0]), RES_P0_NS)
                    sr["gate"] = {"closed": closed, "forced": forced, "boundary": boundary, "p0_open": ok0,
                                  "p0_boundary": m0 <= BOUNDARY_NS, "p0_wait": p0_wait(dl, end_slot, ts, j0)}
                if len(sel) < k or sel[-1] + 1 >= len(ts):
                    sr["kind"], sr["reason"] = "disturbed", "koniec sladu przed Pk+1"
                else:
                    sr["turns"] = sel
                    sr["after"] = sel[-1] + 1
                    sr["windows"] += [(int(ts[j]), int(te[j])) for j in sr["turns"]]
                    sr["end"] = int(te[sel[-1]])
                    a, b = int(ts[sel[0]]), int(te[sel[-1]])
                    inside = comm_t[(comm_t >= a) & (comm_t <= b)]
                    if len(inside) and sr["kind"] == "ok":
                        names = sorted({e[2] for e in comm_ev if a <= e[0] <= b})
                        sr["kind"], sr["reason"] = "disturbed", "wywolanie w P1..Pk: " + ", ".join(names)
        series.append(sr)

    excl = [(w["t_kill"], w["t1"] if w["t1"] is not None else (w["t0"] or w["t_kill"])) for w in kills if w is not None]
    excl += [(p[0], p[1]) for p in pairs]
    excl += [(sr["windows"][0][0], sr["end"]) for sr in series]
    ctl = (dl >= conns[0]["start"] - A.SERIES_PAD_NS) & (dl <= conns[-1]["end"] + A.SERIES_PAD_NS)
    for c in conns:
        ctl &= ~((dl >= c["start"] - A.GUARD_NS) & (dl <= c["end"] + A.GUARD_NS))
    for a, b in excl:
        ctl &= ~((dl >= a - A.GUARD_NS) & (dl <= b + A.GUARD_NS))
    model = D.SlotModel(s, ctl, h)
    for sr in series:
        if sr["kind"] == "ok":
            sr["cluster"] = model.cluster(sr["windows"], rngs["placebo"])

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

    pouts = D.pool_out_events(events, conns, maps, kills, rt)
    viol, o6 = pool_model(series, kills, pouts, maps)
    late = []
    for sr in series:
        nxt = next((c["start"] for c in conns if c["start"] > sr["t_kill"]), None)
        if nxt is not None and sr["end"] >= nxt:
            late.append(sr["ci"])
    tail_overflow = sum(1 for sr in series if sr["kind"] == "overflow" and sr["t_kill"] > conns[-1]["start"])

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
    return {"meta": meta, "side": side, "fam": fam, "base": base, "series": series, "h0": [], "model": model,
            "ctl": {kk: s[kk][ctl] for kk in ("e2e", "compute", "wake")}, "n_conns": len(conns), "k": k, "k_mmap": k_mmap,
            "caps": caps, "turns": (ts, te), "comm_tid": comm_tid, "sleep_other": sleep_other, "idle_len": idle_len,
            "o3": {"p0": p0_len, "phase": phase, "full": full, "last": last, "after": after, "step": step, "dur": dur},
            "pool_viol": viol, "late": late, "pool_out_n": len(pouts), "tail_overflow": tail_overflow, "desc": desc,
            "comm_ev_n": len(comm_ev), "trace_span": (events[0][0], events[-1][0]) if events else (0, 0),
            "slots_in_series": int(in_series.sum()), "conns": conns, "o6": o6}


# ---------------------------------------------------------------- miara slotow dotknietych (est_affected.py)

def affected_idx(m, wins):
    """(sloty dotkniete, sloty nastepne): narazone (definicja R603D) + pierwszy slot z pobudka po koncu okna."""
    idx = set(int(x) for x in m.exposed(wins))
    nxt = set()
    for a, b in wins:
        j = int(np.searchsorted(m.t_on, b, side="right"))
        if j < len(m.dl):
            nxt.add(j)
    return np.array(sorted(idx | nxt), dtype=np.int64), np.array(sorted(nxt), dtype=np.int64)


def devs(m, idx):
    return list((m.comp[idx] - m.base[m.cls[idx]]).astype(float))


def affected_cluster(m, wins, rng):
    """Seria i do 20 kopii placebo (m * H * takt, wszystkie sloty dotkniete kontrolne); None bez kopii."""
    idx, nxt = affected_idx(m, wins)
    step = m.h * m.period
    span = (m.dl[0] - wins[0][0], m.dl[-1] - wins[-1][1])
    lo_m, hi_m = int(np.ceil(span[0] / step)), int(np.floor(span[1] / step))
    copies, copies_n = [], []
    for _ in range(AFF_TRIES):
        if len(copies) == D.PLACEBO or hi_m <= lo_m:
            break
        mm = int(rng.integers(lo_m, hi_m + 1))
        if mm == 0:
            continue
        kk, kn = affected_idx(m, [(a + mm * step, b + mm * step) for a, b in wins])
        if len(kk) and m.ctl[kk].all():
            copies.append(devs(m, kk))
            copies_n.append(devs(m, kn))
    if not copies:
        return None
    return {"real": devs(m, idx), "pl": copies, "real_next": devs(m, nxt), "pl_next": copies_n}


def aff_stat(ss, key="real", pkey="pl"):
    """(Delta mediany, srednie S na serie) - est_gate.stat."""
    real = np.array([x for s in ss for x in s[key]])
    pl = np.array([x for s in ss for c in s[pkey] for x in c])
    if not len(real) or not len(pl):
        return np.nan, np.nan
    dmed = np.median(real) - np.median(pl)
    per = [sum(s[key]) - (np.mean([sum(c) for c in s[pkey]]) if s[pkey] else 0.0) for s in ss]
    return dmed, float(np.mean(per))


def aff_boot(ss, rng, key="real", pkey="pl"):
    point = aff_stat(ss, key, pkey)
    if not ss:
        return point, (np.nan, np.nan), (np.nan, np.nan)
    b = np.array([aff_stat([ss[i] for i in rng.integers(0, len(ss), len(ss))], key, pkey) for _ in range(D.BOOT)])
    with np.errstate(invalid="ignore"):
        lo, hi = np.nanpercentile(b, [2.5, 97.5], axis=0)
    return point, (lo[0], hi[0]), (lo[1], hi[1])


def series_s(ss):
    return np.array([sum(s["real"]) - np.mean([sum(c) for c in s["pl"]]) for s in ss])


def mean_boot(x, rng):
    x = np.asarray(x, dtype=float)
    if not len(x):
        return np.nan, np.nan, np.nan
    b = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(D.BOOT)]
    return float(x.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def k2s_boot(spp, sp, rng):
    """T = S(C'') - 0,5 S(C'), u_S = S(C'') / S(C'), roznica S(C'') - S(C'); strony losowane niezaleznie."""
    if not len(spp) or not len(sp):
        return {key: (np.nan, np.nan, np.nan) for key in ("T", "u", "d")}
    a0, b0 = spp.mean(), sp.mean()
    t, u, d = [], [], []
    for _ in range(D.BOOT):
        a = spp[rng.integers(0, len(spp), len(spp))].mean()
        b = sp[rng.integers(0, len(sp), len(sp))].mean()
        t.append(a - T_FACTOR * b)
        d.append(a - b)
        u.append(a / b if b != 0 else np.nan)
    q = lambda v: (float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5)))  # noqa: E731
    return {"T": (a0 - T_FACTOR * b0, *q(t)), "u": (a0 / b0 if b0 else np.nan, *q(u)), "d": (a0 - b0, *q(d))}


# ---------------------------------------------------------------- strona i H0

def analyze(run_dir, rngs):
    """Przebieg jednej strony: C (tylko --parser-check) i C' przez D.analyze_run, C'' przez analyze_run_e; potem
    O6 i miara slotow dotknietych (losowania placebo po klastrach R603D, jak est_affected.py)."""
    side = json.loads((run_dir / "meta.json").read_text())["side"]
    if side == "Cpp":
        r = analyze_run_e(run_dir, rngs, gated=True)
    else:
        r = D.analyze_run(run_dir, rngs)
        if side == "Cp":
            _, _, _, maps, kills, pouts = run_inputs(run_dir)
            viol, r["o6"] = pool_model(r["series"], kills, pouts, maps)
            if viol != r["pool_viol"]:
                die(f"{run_dir}: model puli R603E rozny od R603D")
    m = r["model"]
    for sr in r["series"]:
        if sr["kind"] == "ok":
            sr["aff"] = affected_cluster(m, sr["windows"], rngs["placebo"])
    return r


def h0_cpp_windows(m, rng, k, par):
    """Syntetyczna seria C'' na tle bez drenazu: obroty co turn_ns z rozrzutem, P0 przy bramce P0, porcje przy
    bramce porcji (albo po MAX_DEFERRALS odroczeniach); None, gdy seria nie miesci sie w slocie modelu."""
    cidx = np.flatnonzero(m.ctl)
    k0 = int(rng.choice(cidx))
    t0 = int(m.end[k0]) + int(rng.integers(par["phase"][0], par["phase"][1]))
    wins, defer, reserve = [], 0, RES_P0_NS
    for j in range((k + 1) * (MAX_DEFERRALS + 1)):
        st = t0 + j * par["turn_ns"] + int(rng.integers(0, par["jitter_ns"]))
        ok, _ = gate_state(m.dl, m.end, st, reserve)
        if ok or defer >= MAX_DEFERRALS:
            wins.append((st, st + (par["p0_ns"] if not wins else par["w_ns"])))
            defer, reserve = 0, RES_PORTION_NS
            if len(wins) == k + 1:
                return wins
        else:
            defer += 1
    return None


def h0_k2s(runs_cp, par, k, rng):
    """Kontrola H0 K2s: syntetyczne serie C'' na tle slotow kontrolnych C' tej kampanii (est_gate_h0.py)."""
    out = []
    for r in runs_cp:
        m = r["model"]
        for _ in range(sum(1 for sr in r["series"] if sr["kind"] == "ok")):
            wins = h0_cpp_windows(m, rng, k, par)
            if wins is None:
                continue
            idx, _ = affected_idx(m, wins)
            if not len(idx) or not m.ctl[idx].all():
                continue
            cl = affected_cluster(m, wins, rng)
            if cl is not None:
                out.append(cl)
    return out


# ---------------------------------------------------------------- raport

def k1_b(rs):
    """K1'' z warunku (b): warunki K1' R603D bez warunku gotowosci (a); opis jak D.k1_side."""
    if not rs:
        return "brak strony", ""
    _, txt = D.k1_side(rs)
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
    if not pos_ok:
        v = "NIEROZSTRZYGNIĘTE (aparatura: kontrola dodatnia - przebieg bez przepełnienia w ogonie)"
    elif n and excluded / n > A.EXCLUDED_MAX:
        v = f"NIEROZSTRZYGNIĘTE (aparatura: wyłączenia {excluded} z {n})"
    elif unexplained == 0 and pool_ok and tail_ok and viol == 0:
        v = "ZDANE"
    else:
        v = "NIEZDANE"
    return v, txt


def late_expected(rs):
    """Warunek (a) opisowo: (zaobserwowane, oczekiwane = serie * p50 serii / sredni odstep startow)."""
    n_ser = sum(len(r["series"]) for r in rs)
    dur = [v for r in rs for v in r["o3"]["dur"]]
    gaps = [b["start"] - a["start"] for r in rs for a, b in zip(r["conns"], r["conns"][1:])]
    exp = n_ser * pct(dur, 50) / np.mean(gaps) if dur and gaps else np.nan
    return sum(len(r["late"]) for r in rs), exp


def ser(rs, kind):
    return [sr for r in rs for sr in r["series"] if sr["kind"] == kind]


def portion_phase(r):
    """Faza startu porcji P1..Pk po koncu slotu z ostatnim terminem przed nia [ns] (jak faza P0 w R603D)."""
    m = r["model"]
    ts, _ = r["turns"]
    out = []
    for sr in r["series"]:
        if sr["kind"] != "ok":
            continue
        for j in sr["turns"]:
            i = int(np.searchsorted(m.dl, ts[j], side="right")) - 1
            if i >= 0:
                out.append(int(ts[j] - m.end[i]))
    return out


def fmt_ci(x, scale=1e-3, digits=2):
    return f"{x[0] * scale:+.{digits}f} ({x[1] * scale:+.{digits}f}..{x[2] * scale:+.{digits}f})"


def family_report(fam, P, Q, h0, rngs, ctx):
    """P = przebiegi C', Q = przebiegi C''."""
    runs = P + Q
    period = int(np.median([r["model"].period for r in runs]))
    lines = [f"## {fam}", "", f"Takt slotu: {period / 1e6:.3f} ms, H = {D.H[fam]}, k = {D.PORTIONS[fam]} "
             f"(z pojemności mmap: {sorted({x for r in runs for x in r['k_mmap']})}, pojemność "
             f"{sorted({x for r in runs for x in r['caps']})}).", "", "| wielkość | C' | C'' |", "|---|---|---|"]

    def row(label, f, only_q=False):
        lines.append(f"| {label} | {'-' if only_q or not P else f(P)} | {f(Q) if Q else '-'} |")

    rng = rngs["boot"]
    row("przebiegi / podłączenia", lambda x: f"{len(x)} / {sum(r['n_conns'] for r in x)}")
    row("serie: niezakłócone / przepełnienia / zakłócone", lambda x: f"{len(ser(x, 'ok'))} / {len(ser(x, 'overflow'))} / "
        f"{len(ser(x, 'disturbed'))}")
    row("O5: powody zakłóceń", lambda x: "; ".join(sorted({sr['reason'] for sr in ser(x, 'disturbed')})) or "-")
    row("O3: P0 [µs] p50 / p99 / max", lambda x: dist([v for r in x for v in r["o3"]["p0"]]))
    row("O3: faza P0 po końcu slotu [µs] p5 / p50 / p95", lambda x: dist([v for r in x for v in r["o3"]["phase"]], (5, 50, 95)))
    row("O3: faza porcji P1..Pk po końcu slotu [µs] p5 / p50 / p95",
        lambda x: dist([v for r in x for v in portion_phase(r)], (5, 50, 95)))
    row("O3: pełna porcja P1..Pk-1 [µs] p50 / p99 / max", lambda x: dist([v for r in x for v in r["o3"]["full"]]))
    row("O3: ostatnia porcja Pk [µs] p50 / p99 / max", lambda x: dist([v for r in x for v in r["o3"]["last"]]))
    row("O3: obrót Pk+1 [µs] p50 / p99 / max", lambda x: dist([v for r in x for v in r["o3"]["after"]]))
    row("O3: obrót bezczynny [µs] p50 / p99 / max", lambda x: dist(np.concatenate([r["idle_len"] for r in x])))
    row("O3: odstęp obrotów w serii [µs] p50 / p99 / max", lambda x: dist([v for r in x for v in r["o3"]["step"]]))
    row("O3: seria P0..Pk [ms] p50 / max", lambda x: (lambda v: f"{A.fmt_ms(pct(v, 50))} / {A.fmt_ms(pct(v, 100))}")(
        [v for r in x for v in r["o3"]["dur"]]))
    gq = [sr["gate"] for sr in ser(Q, "ok") if "gate" in sr]
    row("O3: oczekiwanie P0 [obroty, górna granica] p50 / p99 / max", lambda x: " / ".join(
        f"{pct([g['p0_wait'] for g in gq], q):.0f}" for q in (50, 99, 100)) if gq else "-", only_q=True)
    row("O3: P0 w obrocie z zamkniętą bramką modelu (z tego graniczne)", lambda x: (
        f"{sum(not g['p0_open'] for g in gq)} ({sum(not g['p0_open'] and g['p0_boundary'] for g in gq)}) z {len(gq)}"),
        only_q=True)
    row("O3: obroty z zamkniętą bramką w serii p50 / max", lambda x: (
        f"{pct([len(g['closed']) for g in gq], 50):.0f} / {pct([len(g['closed']) for g in gq], 100):.0f}" if gq else "-"),
        only_q=True)
    row("O3: kroki wymuszone limitem odroczeń / obroty graniczne w seriach", lambda x: (
        f"{sum(len(g['forced']) for g in gq)} / {sum(len(g['boundary']) for g in gq)}"), only_q=True)

    # K2e: sloty narazone na serie (definicja R603D), surowa liczba na serie.
    e = {sd: mean_boot([len(sr["cluster"]["real"]) for sr in ser(x, "ok")], rng) for sd, x in (("Cp", P), ("Cpp", Q))}
    row("K2e: sloty narażone na serię E (95 % bootstrap)", lambda x: (lambda v: f"{v[0]:.3f} ({v[1]:.3f}..{v[2]:.3f})")(
        e["Cp" if x is P else "Cpp"]))
    # K2s: koszt serii na slotach dotknietych.
    ss = {sd: [sr["aff"] for sr in ser(x, "ok") if sr.get("aff") is not None] for sd, x in (("Cp", P), ("Cpp", Q))}
    aff = {sd: aff_boot(v, rng) for sd, v in ss.items()}
    nxt = {sd: aff_boot(v, rng, "real_next", "pl_next") for sd, v in ss.items()}
    sm = {sd: mean_boot(series_s(v), rng) for sd, v in ss.items()}
    h0_s = mean_boot(series_s(h0), rng)
    h0_a = aff_boot(h0, rng)
    t = k2s_boot(series_s(ss["Cpp"]), series_s(ss["Cp"]), rng)
    sd_of = lambda x: "Cp" if x is P else "Cpp"  # noqa: E731
    row("K2s: serie z placebo / sloty dotknięte na serię", lambda x: f"{len(ss[sd_of(x)])} / "
        f"{np.mean([len(c['real']) for c in ss[sd_of(x)]]) if ss[sd_of(x)] else float('nan'):.1f}")
    row("K2s: S = suma odchyleń slotów dotkniętych na serię ponad placebo [µs] (95 %)", lambda x: fmt_ci(sm[sd_of(x)], digits=1))
    row("K2s: Δ mediany slotów dotkniętych [µs] (95 %)", lambda x: (lambda a: f"{a[0][0] / 1e3:+.2f} "
        f"({a[1][0] / 1e3:+.2f}..{a[1][1] / 1e3:+.2f})")(aff[sd_of(x)]))
    row("opisowo: Δ mediany slotów następnych po oknach [µs] (95 %)", lambda x: (lambda a: f"{a[0][0] / 1e3:+.2f} "
        f"({a[1][0] / 1e3:+.2f}..{a[1][1] / 1e3:+.2f})")(nxt[sd_of(x)]))
    lines.append(f"| H0 K2s (syntetyczne serie C'' na tle C'): serie / S [µs] / Δ mediany [µs] | - | {len(h0)} / "
                 f"{fmt_ci(h0_s, digits=1)} / {h0_a[0][0] / 1e3:+.2f} ({h0_a[1][0] / 1e3:+.2f}..{h0_a[1][1] / 1e3:+.2f}) |")
    # Opisowo R603D: K2a na slotach narazonych, O4.
    k2 = {sd: D.k2_summary([sr["cluster"] for sr in ser(x, "ok")], rng) for sd, x in (("Cp", P), ("Cpp", Q))}
    row("opisowo K2a R603D Δ_c [µs]; n slotów; serie z narażeniem", lambda x: D.k2_fmt(k2[sd_of(x)], 0, 1e-3, "µs"))
    no4 = {sd: D.o4_cost([sr["cluster"] for sr in ser(x, "ok")]) for sd, x in (("Cp", P), ("Cpp", Q))}
    row("opisowo O4 R603D: sloty narażone / suma odchyleń na serię ponad placebo [µs] (średnie)", lambda x: (
        lambda v: f"{v[0].mean():.2f} / {v[1].mean() / 1e3:.1f}" if len(v[0]) else "-")(no4[sd_of(x)]))
    for kk in ("e2e", "compute", "wake"):
        row(f"kontrola {kk} [µs] p50 / p99 / max", lambda x, kk=kk: dist(np.concatenate([r["ctl"][kk] for r in x])))
    o1 = lambda x, key: sum(r["base"]["o1"][key] for r in x)  # noqa: E731
    row("O1: futex wątku RT: sloty z futex / sloty w serii", lambda x: f"{o1(x, 'slots_with_futex')} / {o1(x, 'slots')} "
        f"({100.0 * o1(x, 'slots_with_futex') / max(1, o1(x, 'slots')):.3f} %)")
    row("O1: FUTEX_WAIT na muteksie kolejki: liczba / max [µs] / w oknie P0 / slot > takt", lambda x: (
        lambda v: f"{len(v)} / {fmt_us(pct(v, 100)) if v else '-'} / {o1(x, 'wait_in_window')} / {o1(x, 'wait_over_period')}")(
        [v for r in x for v in r["base"]["o1"]["wait_ns"]]))
    for kind, label in (("created", "kolejka utworzona"), ("pooled", "kolejka z puli")):
        row(f"O2: podłączenie, {label}: liczba / okno p50 [ms]", lambda x, kind=kind: (
            lambda ev: f"{len(ev)} / {A.fmt_ms(pct([e['len_ns'] for e in ev], 50))}")(
            [e for r in x for e in r["base"]["o2"] if e["kind"] == kind]))
    row("O6: kolejka utworzona, gdy pula miała tylko wpisy niegotowe", lambda x: f"{sum(len(r['o6']) for r in x)}")
    lines.append("")

    # K1''.
    kq, tq = k1_b(Q)
    kp, tp = k1_b(P)
    lq, eq = late_expected(Q)
    lp, ep = late_expected(P)
    lines.append(f"- **K1''** C'': {tq}. Werdykt C'' (warunek (b)): **{kq}**. Warunek (a) opisowo: serii niegotowych przed "
                 f"startem następnego klienta {lq}, oczekiwanych {eq:.1f}; O6 {sum(len(r['o6']) for r in Q)}.")
    lines.append(f"- K1' C' (opisowo, powtórzenie R603D, werdykt z (b)): {tp}. Werdykt C': {kp}. Warunek (a): {lp}, "
                 f"oczekiwanych {ep:.1f}; O6 {sum(len(r['o6']) for r in P)}.")
    # K2e.
    pos_e = not math.isnan(e["Cp"][1]) and e["Cp"][1] > E_POS
    if not pos_e:
        ve = f"opisowo (kontrola dodatnia C': dolna granica E(C') {e['Cp'][1]:.2f} ≤ {E_POS:.0f})"
    elif e["Cpp"][2] <= E_THR:
        ve = "ZDANE"
    elif e["Cpp"][1] > E_THR:
        ve = "NIEZDANE"
    else:
        ve = "NIEROZSTRZYGNIĘTE (przedział zawiera próg)"
    lines.append(f"- **K2e** (próg {E_THR} slotu na serię): E(C'') {e['Cpp'][0]:.3f} ({e['Cpp'][1]:.3f}..{e['Cpp'][2]:.3f}), "
                 f"kontrola dodatnia E(C') {e['Cp'][0]:.3f} ({e['Cp'][1]:.3f}..{e['Cp'][2]:.3f}). Werdykt C'': **{ve}**.")
    # K2s.
    half = (h0_s[2] - h0_s[1]) / 2 if not math.isnan(h0_s[1]) else np.nan
    reasons = []
    if not (not math.isnan(sm["Cp"][1]) and sm["Cp"][1] > 0):
        reasons.append(f"kontrola dodatnia: dolna granica S(C') {sm['Cp'][1] / 1e3:+.1f} µs ≤ 0")
    if not (not math.isnan(half) and half <= H0_HALF_MAX * sm["Cp"][0]):
        reasons.append(f"H0: półszerokość {half / 1e3:.1f} µs > {H0_HALF_MAX} · S(C') = "
                       f"{H0_HALF_MAX * sm['Cp'][0] / 1e3:.1f} µs")
    few = [sd for sd in ("Cp", "Cpp") if len(ss[sd]) < D.MIN_SERIES]
    if few:
        vs = "NIEROZSTRZYGNIĘTE (liczność: " + ", ".join(f"{sd} {len(ss[sd])}" for sd in few) + f" < {D.MIN_SERIES} serii)"
    elif reasons:
        vs = "NIEROZSTRZYGNIĘTE (miara: " + "; ".join(reasons) + ")"
    elif t["T"][2] < 0:
        vs = "ZDANE"
    elif t["T"][1] > 0:
        vs = "NIEZDANE"
    else:
        vs = "NIEROZSTRZYGNIĘTE (przedział T zawiera 0)"
    lines.append(f"- **K2s** (T = S(C'') - {T_FACTOR} · S(C')): T {fmt_ci(t['T'], digits=1)} µs; S(C'') "
                 f"{fmt_ci(sm['Cpp'], digits=1)}, S(C') {fmt_ci(sm['Cp'], digits=1)} µs; S(C'') - S(C') "
                 f"{fmt_ci(t['d'], digits=1)} µs; u_S {t['u'][0]:.2f} ({t['u'][1]:.2f}..{t['u'][2]:.2f}). Ważność: kontrola "
                 f"dodatnia {'tak' if not any(x.startswith('kontrola') for x in reasons) else 'NIE'}, H0 półszerokość "
                 f"{half / 1e3:.1f} µs wobec {H0_HALF_MAX * sm['Cp'][0] / 1e3:.1f} µs. Werdykt: **{vs}**.")
    vq = D.k2_verdict(D.with_verdict(k2["Cpp"], 0), D.DELTA_C_NS, True)
    vp = D.k2_verdict(D.with_verdict(k2["Cp"], 0), D.DELTA_C_NS, True)
    lines.append(f"- K2a R603D opisowo (δ_c = {D.DELTA_C_NS / 1e3:.0f} µs): C'' {D.k2_fmt(k2['Cpp'], 0, 1e-3, 'µs')} - {vq}; "
                 f"C' {D.k2_fmt(k2['Cp'], 0, 1e-3, 'µs')} - {vp}.")
    for key, q, label in (("compute", 50, "compute_ns p50"), ("wake", 99, "wake_lag_ns p99"), ("e2e", 99, "e2e_ns p99")):
        c = [pct(r["ctl"][key], q) for r in P]
        p = [pct(r["ctl"][key], q) for r in Q]
        c, p = [x for x in c if not math.isnan(x)], [x for x in p if not math.isnan(x)]
        if not (c and p):
            lines.append(f"- **K3**, {label}: brak danych obu stron.")
            continue
        diff = float(np.median(p) - np.median(c))
        spread = max(max(c) - min(c), max(p) - min(p))
        pv = A.permutation_mw_two_sided(c, p)
        state = "w szumie" if abs(diff) <= spread else ("REGRESJA C'' - osobne znalezisko" if diff > 0 else "C'' lepsze poza szumem")
        lines.append(f"- **K3**, {label} per przebieg: mediana C'' - C' = {diff / 1e3:.2f} µs, rozrzut wewnątrz strony do "
                     f"{spread / 1e3:.2f} µs, permutacyjny MW p = {pv:.3g} - {state}.")
    lines.append("")
    ctx["verdicts"][fam] = {"K1": kq, "K2e": ve, "K2s": vs, "K1p": kp}
    return lines


def run_dirs(fam_dir, side):
    return D.run_dirs(fam_dir, side)


def load_family(fam_dir, rngs):
    fam = fam_dir.name
    P = [analyze(d, rngs) for d in run_dirs(fam_dir, "Cp")]
    Q = [analyze(d, rngs) for d in run_dirs(fam_dir, "Cpp")]
    for r in P + Q:
        if any(x != D.PORTIONS[fam] for x in r["k_mmap"]):
            die(f"{fam}: k z pojemności mmap {r['k_mmap']} różne od {D.PORTIONS[fam]} - przesłanka protokołu nie zachodzi")
    return P, Q


def main_report(raw, seed, out):
    rngs = D.rng_set(seed)
    ctx = {"verdicts": {}}
    report = ["# R603E - wynik", "", f"Źródło: `{raw.name}`, ziarna: placebo {seed}, bootstrap {seed + 1}, H0 {seed + 2}, "
              f"pseudo-zdarzenia {seed + 3}.", ""]
    for fam_dir in sorted(p for p in raw.iterdir() if p.is_dir()):
        fam = fam_dir.name
        P, Q = load_family(fam_dir, rngs)
        par = D.h0_params(Q, D.PORTIONS[fam])
        h0 = h0_k2s(P, par, D.PORTIONS[fam], rngs["h0"])
        report += [f"Parametry H0 K2s {fam} (z C''): P0 {par['p0_ns'] / 1e3:.1f} µs, porcja {par['w_ns'] / 1e3:.1f} µs, obrót "
                   f"{par['turn_ns'] / 1e3:.1f} µs, faza {par['phase'][0] / 1e3:.0f}..{par['phase'][1] / 1e3:.0f} µs, "
                   f"rozrzut {par['jitter_ns'] / 1e3:.0f} µs.", ""]
        report += family_report(fam, P, Q, h0, rngs, ctx)
    report += ["## Werdykty", "", "| rodzina | K1'' C'' (b) | K2e C'' | K2s | K1' C' (b, opisowo) |", "|---|---|---|---|---|"]
    for fam, v in ctx["verdicts"].items():
        report.append(f"| {fam} | {v['K1']} | {v['K2e']} | {v['K2s']} | {v['K1p']} |")
    text = "\n".join(report) + "\n"
    if out:
        out.write_text(text)
    print(text)


# ---------------------------------------------------------------- bramki suchego przebiegu

def gate_h(runs):
    """Bramka H (aneks 1 R603D) dla stron C' i C''."""
    out = []
    for side in ("Cp", "Cpp"):
        rs = [r for r in runs if r["side"] == side]
        if not rs:
            continue
        h = D.H[rs[0]["fam"]]
        med = {}
        for hh in range(1, 2 * h + 1):
            med[hh] = float(np.median(np.concatenate([np.abs(r["model"].comp[hh:] - r["model"].comp[:-hh]) for r in rs])))
        order = sorted(med, key=lambda x: (med[x], x))
        hs = order[0]
        ok = h % hs == 0 and med[h] <= med[hs] * (1 + D.H_TOL)
        out.append((side, h, order[:4], [round(med[x] / 1e3, 3) for x in order[:4]], ok, hs == h))
    return out


def g2_prime(r, p99, p999):
    """G2' (C''): pelne porcje > p99,9 obrotu bezczynnego, obroty zamkniete <= p99 (po >= 99 %, bez granicznych),
    obrot Pk+1 <= p99 w kazdej serii (jak G2 R603D); serie z obrotem granicznym raportowane osobno."""
    ts, te = r["turns"]
    full, closed, after_ok, after_n, with_b, bad_b = [], [], 0, 0, 0, 0
    for sr in ser([r], "ok"):
        if not sr.get("turns"):
            continue
        g = sr["gate"]
        bset = set(g["boundary"])
        full += [int(te[j] - ts[j]) > p999 for j in sr["turns"][:-1] if j not in bset]
        closed += [int(te[j] - ts[j]) <= p99 for j in g["closed"] if j not in bset]
        a_ok = int(te[sr["after"]] - ts[sr["after"]]) <= p99
        after_n += 1
        after_ok += a_ok
        with_b += bool(bset)
        bad_b += bool(bset) and not a_ok
    ff = sum(full) / len(full) if full else np.nan
    fc = sum(closed) / len(closed) if closed else np.nan
    ok = bool(full) and ff >= G2_FRAC and (not closed or fc >= G2_FRAC) and after_n > 0 and after_ok == after_n
    txt = (f"pełne porcje > p99,9 bezczynnego {sum(full)}/{len(full)} ({ff:.3f}), obroty zamknięte ≤ p99 {sum(closed)}/"
           f"{len(closed)} ({fc:.3f}), Pk+1 ≤ p99 {after_ok}/{after_n} serii (serii z obrotem granicznym {with_b}, z nich "
           f"z Pk+1 > p99 {bad_b})")
    return ok, txt


def gates(raw):
    rngs = D.rng_set(6034)
    ok_all = True
    for fam_dir in sorted(p for p in raw.iterdir() if p.is_dir()):
        fam = fam_dir.name
        runs = [analyze(d, rngs) for side in ("Cp", "Cpp") for d in run_dirs(fam_dir, side)]
        print(f"## {fam} (k = {D.PORTIONS[fam]}, H = {D.H[fam]})")
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
                  f"{r['meta'].get('trace_overrun')}, obrotów {len(ts)} na {span_ms:.0f} ms śladu (pokrycie {cover:.0f} ms), "
                  f"odstęp p50 {np.median(per) / 1e3:.1f} µs, max poza podłączeniami i seriami {maxgap / 1e3:.1f} µs, sen "
                  f"innych wątków spoza RT {r['sleep_other']}, wątek {r['comm_tid']}")
            ok_all &= g1
            idle = r["idle_len"]
            p999, p99 = (pct(idle, 99.9), pct(idle, 99)) if len(idle) else (np.nan, np.nan)
            sers = ser([r], "ok")
            dist_txt = (f"obrót bezczynny p99 / p99,9 / max {fmt_us(p99)} / {fmt_us(p999)} / {fmt_us(pct(idle, 100))} µs "
                        f"(n = {len(idle)}); pełna porcja p50 / min {fmt_us(pct(r['o3']['full'], 50))} / "
                        f"{fmt_us(pct(r['o3']['full'], 0))} µs; Pk+1 p50 / max {fmt_us(pct(r['o3']['after'], 50))} / "
                        f"{fmt_us(pct(r['o3']['after'], 100))} µs; zakłócone {len(ser([r], 'disturbed'))} "
                        f"({'; '.join(sorted({sr['reason'] for sr in ser([r], 'disturbed')})) or '-'})")
            if r["side"] == "Cp":
                good, need = 0, [sr for sr in sers if sr.get("turns")]
                for sr in need:
                    lens = [int(te[j] - ts[j]) for j in sr["turns"]]
                    good += all(v > p999 for v in lens[:-1]) and int(te[sr["after"]] - ts[sr["after"]]) <= p99
                g2 = len(need) > 0 and good == len(need)
                print(f"  G2 {'OK' if g2 else 'NIE'} (C', jak R603D): serii niezakłóconych {len(sers)} (z obrotami "
                      f"{len(need)}), spełnia oba warunki {good}; {dist_txt}")
            else:
                g2, txt = g2_prime(r, p99, p999)
                gq = [sr["gate"] for sr in sers if "gate" in sr]
                print(f"  G2' {'OK' if g2 else 'NIE'}: {txt}; {dist_txt}; P0 w obrocie z zamkniętą bramką modelu "
                      f"{sum(not g['p0_open'] for g in gq)} (graniczne {sum(g['p0_boundary'] for g in gq)}), wymuszone "
                      f"{sum(len(g['forced']) for g in gq)}, oczekiwanie P0 max {max([g['p0_wait'] for g in gq], default=0)} "
                      f"obrotów")
            ok_all &= g2
            v, txt = k1_b([r])
            k1 = r["base"]["k1"]
            g3 = k1["kill_client"] > 0 and k1["pool_in"] > 0 and k1["pool_out"] > 0 and not r["pool_viol"]
            print(f"  G3 {'OK' if g3 else 'NIE'}: {txt}; kill klienta {k1['kill_client']}, wartości kill {k1['kill_ret']}; "
                  f"werdykt (b) na tym przebiegu: {v}; O6 {len(r['o6'])}; k z mmap {r['k_mmap']} (pojemność {r['caps']})")
            ok_all &= g3 and all(x == D.PORTIONS[fam] for x in r["k_mmap"])
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


# ---------------------------------------------------------------- test parsera na danych R603D

# README R603E, Ustalenia, punkt 3 (est_affected.py): slotow dotknietych na serie, Delta mediany (lo, hi), S (lo, hi).
EXPECTED_AFF = {("uc03", "C"): "1.0 / +48.00 (+47.37..+48.80) / +51.1 (+48.9..+53.3)",
                ("uc03", "Cp"): "2.2 / +26.43 (+25.06..+28.00) / +69.7 (+65.3..+74.6)",
                ("uc05", "C"): "3.4 / +39.80 (+37.58..+42.68) / +161.0 (+151.4..+171.7)",
                ("uc05", "Cp"): "32.0 / +3.57 (+3.37..+3.78) / +240.8 (+180.4..+305.5)",
                ("uc06", "C"): "2.3 / +40.27 (+36.55..+45.89) / +127.3 (-522.4..+903.9)",
                ("uc06", "Cp"): "12.2 / +11.94 (+11.53..+12.43) / +312.6 (-1436.9..+2092.3)"}
# README R603E, Ustalenia, punkt 1 (est_gate.py): odsetek porcji C' i P0 C' przy otwartej bramce modelu.
EXPECTED_GATE = {"uc03": "0.902 / 1.000", "uc05": "0.654 / 0.502", "uc06": "0.699 / 0.919"}


def parser_check(raw):
    bad = 0
    # 1. Wydruk R603D z analyze_run_e (wybor C') w miejscu D.analyze_run dla strony C' = wynik.md R603D bajt w bajt.
    wynik = (HERE.parent / "results_20261105_R603D" / "wynik.md").read_text()
    ref = wynik.split("## Wydruk analizy\n", 1)[1].strip("\n")
    orig, calls = D.analyze_run, {"e": 0}

    def patched(run_dir, rngs, h0_par=None, h0_n_from=None):
        if json.loads((run_dir / "meta.json").read_text())["side"] == "Cp":
            calls["e"] += 1
            return analyze_run_e(run_dir, rngs, gated=False)
        return orig(run_dir, rngs, h0_par=h0_par, h0_n_from=h0_n_from)

    tmp = io.StringIO()
    D.analyze_run = patched
    try:
        with contextlib.redirect_stdout(tmp):
            D.main_report(raw, 6034, None)
    finally:
        D.analyze_run = orig
    out = tmp.getvalue().rstrip("\n").split("\n")[1:]
    got = "\n".join(("#" + l) if l.startswith("#") else l for l in out).strip("\n")
    rl, gl = ref.split("\n"), got.split("\n")
    nd = sum(1 for a, b in zip(rl, gl) if a != b) + abs(len(rl) - len(gl))
    print(f"1. wydruk R603D z analyze_run_e (wybór C', {calls['e']} przebiegów C') wobec wynik.md R603D: {len(gl)} wierszy, "
          f"różnic {nd}")
    for a, b in [(a, b) for a, b in zip(rl, gl) if a != b][:5]:
        print(f"   wynik.md: {a}\n   teraz:    {b}")
    bad += nd != 0 or calls["e"] == 0

    # 2. Miara slotow dotknietych = Ustalenia, punkt 3 (kolejnosc losowan est_affected.py: rng_set(6034), bootstrap 6035).
    # 3. Model bramki = Ustalenia, punkt 1 (odsetki porcji i P0 C' przy otwartej bramce).
    rngs = D.rng_set(6034)
    boot = np.random.default_rng(6035)
    for fam_dir in sorted(p for p in raw.iterdir() if p.is_dir()):
        fam = fam_dir.name
        gate_cnt = [0, 0, 0, 0]
        for side in ("C", "Cp"):
            runs = [analyze(d, rngs) for d in run_dirs(fam_dir, side)]
            ss = [sr["aff"] for r in runs for sr in r["series"] if sr["kind"] == "ok" and sr["aff"] is not None]
            (dmed, dsum), (lo0, hi0), (lo1, hi1) = aff_boot(ss, boot)
            nsl = np.mean([len(s["real"]) for s in ss]) if ss else float("nan")
            shown = (f"{nsl:.1f} / {dmed / 1e3:+.2f} ({lo0 / 1e3:+.2f}..{hi0 / 1e3:+.2f}) / {dsum / 1e3:+.1f} "
                     f"({lo1 / 1e3:+.1f}..{hi1 / 1e3:+.1f})")
            exp = EXPECTED_AFF.get((fam, side))
            if exp is not None:
                ok2 = shown == exp
                bad += not ok2
                print(f"2. {fam} {side}: sloty dotknięte {shown} - {'OK' if ok2 else 'RÓŻNICA wobec ' + exp}")
            if side == "Cp":
                for r in runs:
                    m = r["model"]
                    for sr in ser([r], "ok"):
                        gate_cnt[0] += sum(gate_state(m.dl, m.end, a, RES_PORTION_NS)[0] for a, _ in sr["windows"][1:])
                        gate_cnt[1] += len(sr["windows"]) - 1
                        gate_cnt[2] += gate_state(m.dl, m.end, sr["p0"][0], RES_P0_NS)[0]
                        gate_cnt[3] += 1
        if fam in EXPECTED_GATE:
            shown = f"{gate_cnt[0] / max(1, gate_cnt[1]):.3f} / {gate_cnt[2] / max(1, gate_cnt[3]):.3f}"
            ok3 = shown == EXPECTED_GATE[fam]
            bad += not ok3
            print(f"3. {fam} C': bramka otwarta porcja / P0 {shown} - {'OK' if ok3 else 'RÓŻNICA wobec ' + EXPECTED_GATE[fam]}")
    print(f"parser-check: {'ZDANY' if bad == 0 else f'NIEZDANY ({bad} różnic)'}")
    return bad == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--seed", type=int, default=6034)
    ap.add_argument("--parser-check", action="store_true", help="--raw wskazuje surowe dane R603D")
    ap.add_argument("--gates", action="store_true", help="--raw wskazuje suchy przebieg R603E")
    args = ap.parse_args()
    if args.parser_check:
        sys.exit(0 if parser_check(args.raw) else 2)
    if args.gates:
        sys.exit(0 if gates(args.raw) else 2)
    main_report(args.raw, args.seed, args.out)


if __name__ == "__main__":
    main()
