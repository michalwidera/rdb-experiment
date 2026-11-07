#!/usr/bin/env python3
"""R607: analiza przebiegow run_one.py wedlug kryteriow K4, K4n, K0, K3, K3t, opisu K3p i bramek W1-W5 z README.md.

Uzycie (Python >= 3.10 z NumPy, np. retractordb/.venv-python/bin/python3):
  analyze.py --raw <katalog>/raw [--out wynik.txt] [--seed 6034]    raport kampanii (raw/uc05/N<n>/<strona>_<para>)
  analyze.py --raw <katalog> --gates                                bramki W1-W5 per przebieg (suchy przebieg)
  analyze.py --raw <R603G>/raw --r603f <R603F>/raw --parser-check   test analizy (README, Kolejnosc, punkt 2)

Parser R603G (a przez niego R603F, R603E, R603D i R603C) jest importowany BEZ ZMIAN z
../results_20261106_R603G/analyze.py. Strona odniesienia to D2s, strona badana D2r. Przebieg sondy = ciag kolejnych
obrotow watku komunikacyjnego z udanym openat (na D2s jeden obrot z N openat, na D2r N obrotow z jednym).
Wypisuje tylko liczby wyprowadzone (embargo korpusu).
"""

import argparse
import importlib.util
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def _load_r603g():
    spec = importlib.util.spec_from_file_location("analyze_r603g", HERE.parent / "results_20261106_R603G" / "analyze.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


G = _load_r603g()
F, E, D, A = G.F, G.E, G.D, G.A

FAM = "uc05"
RATE = G.RATE
K4_MAX_NS = 1_000_000  # K4: p99 E_p przy N = K4_N <= kQueuePollInterval
K4_N = 16
DELTA_N_NS = 5_000  # K4n: nachylenie median E_p wzgledem N [ns na subskrybenta]
L_MIN_NS = -5_000_000  # K0, jak R603F
L_MAX_NS = 1_010_000_000  # K0 D2s (granica R603F); D2r: + N * TURN_BOUND_NS (granica P1)
TURN_BOUND_NS = 1_500_000
RISK_NS = 10_000  # regula odczytu ryzyka K3p: S(D2r) - S(D2s) wobec 10 us na sekunde (delta_S R603G)
K3_REL = 0.05
K3T_NS = 500
W2_MIN = 0.95
GAP_LO_NS, GAP_HI_NS = G.GAP_LO_NS, G.GAP_HI_NS
H0_SETS = 5
H0_GAP_SLOTS = 3  # H0 K3p: okno syntetyczne nie blizej niz 3 sloty od przebiegu sondy D2s
MIN_RUNS = 8
CTL_PAD_SLOTS = 2  # aneks A1 R603G
SIDES = ("D2s", "D2r")
BIG_MUNMAP = G.BIG_MUNMAP
# Wydruk analizy R603G, kolumna D2s (test analizy, punkt 1; kontrola odtwarzalnosci w raporcie)
R603G_EP = {1: "124.0 / 187.0 / 218.0", 8: "612.0 / 743.0 / 765.0", 16: "1197.0 / 1352.0 / 1920.0"}
R603G_IDLE = {1: "13.0 / 23.0 / 1753.0", 8: "15.0 / 33.0 / 992.0", 16: "16.0 / 34.0 / 5093.0"}
R603G_SP_N1 = "+15.81 (+10.83..+21.25)"
# Wydruk analizy R603F, strona D2s: K0 (wykrycia, samotne, L min / p50 / p99 / max [ms])
R603F_K0 = {"uc03": (270, 0, "1.5 / 554.0 / 983.2 / 994.8"), "uc05": (270, 0, "1.9 / 501.8 / 996.3 / 997.7"),
            "uc06": (266, 1, "10.9 / 532.4 / 991.9 / 998.8")}


def pct(a, q):
    return A.pct(a, q) if len(a) else float("nan")


def us(ns, digits=1):
    return D.fmt_us(ns, digits)


def ms_dist(a):
    return " / ".join(f"{pct(a, q) / 1e6:.1f}" for q in (0, 50, 99, 100)) if len(a) else "-"


def l_max_ns(side, n):
    return L_MAX_NS + (n * TURN_BOUND_NS if side == "D2r" else 0)


# ---------------------------------------------------------------- jeden przebieg

def rounds_of(probe):
    """Ciagi kolejnych indeksow obrotow z sonda."""
    out = []
    for j in probe:
        if out and j == out[-1][-1] + 1:
            out[-1].append(j)
        else:
            out.append([j])
    return out


def load_deaths(path):
    out = []
    for line in path.read_text().splitlines()[1:]:
        r = line.split("\t")
        out.append({"i": int(r[0]), "pid": int(r[1]), "start": int(r[2]), "end": int(r[3]), "rc": r[4],
                    "alive_before": int(r[5]), "first": None, "reaped": 1})
    return out


def death_phase(run_dir, side, n, rt):
    """K0: wykrycie zgonu kazdego zabitego klienta (wzorzec R603F, classify_kills / kill_windows_f bez zmian)."""
    deaths = load_deaths(run_dir / "deaths.tsv")
    if not deaths:
        return {"deaths": [], "L": [], "cat": Counter(), "rank": [], "det_turn": [], "lone": 0}
    events = A.parse_trace(run_dir / "trace_death.txt")
    cls = F.classify_kills(events, deaths, rt)
    kws = F.kill_windows_f(events, deaths, rt)
    ts, te, _, _ = D.comm_turns(events, None, rt)
    t_det = []
    for c, res, w in zip(deaths, cls, kws):
        t_det.append(w["t_det"] if w is not None else (res["det"][0] if res["det"] else None))
    hi = l_max_ns(side, n)
    cat, L, rank, det_turn = Counter(), [], [], []
    for k, (c, res, w, td) in enumerate(zip(deaths, cls, kws, t_det)):
        if td is None:
            cat["bez wykrycia, zwolnione" if w is not None else "niewykryte"] += 1
            continue
        L.append(td - c["end"])
        cat["w granicy" if L_MIN_NS <= L[-1] <= hi else "poza granica"] += 1
        if w is None:
            cat["wykryte, bez zwolnienia w sladzie"] += 1
        elif w["t1"] is None:
            cat["wykryte, zwolnione bez puli"] += 1
        # Pozycja w przebiegu: obserwowani w chwili zabicia = jeszcze niezabici albo zabici, ale niewykryci.
        watched = [d["pid"] for d2, (d, t2) in enumerate(zip(deaths, t_det))
                   if d2 >= k or (t2 is not None and t2 > c["start"]) or t2 is None]
        rank.append((sum(1 for p in watched if p < c["pid"]), L[-1]))
        j = G.turn_index(ts, te, td)
        if j >= 0:
            det_turn.append(int(te[j] - ts[j]))
    return {"deaths": deaths, "L": L, "cat": cat, "rank": rank, "det_turn": det_turn,
            "lone": sum(len(r["lone"]) for r in cls)}


def analyze_run(run_dir, rngs, side=None):
    """Jak analyze_run R603G (kod przeniesiony bez zmian tam, gdzie strona D2s), z przebiegiem D2r i faza zgonow.
    side: wymuszenie strony (test analizy, punkt 3)."""
    meta = json.loads((run_dir / "meta.json").read_text())
    side, n = side or meta["side"], meta["n"]
    win = json.loads((run_dir / "window.json").read_text())
    t0, t1 = win["t0_ns"], win["t1_ns"]
    w_s = (t1 - t0) / 1e9
    events = [e for e in A.parse_trace(run_dir / "trace.txt") if t0 <= e[0] <= t1]
    rt = A.rt_tids(run_dir / "rt.txt")
    ts, te, comm_tid, others = D.comm_turns(events, None, rt)
    turn_len = te - ts

    ok_by, fail_by = Counter(), Counter()
    big_unmap = unlink = rename = kills = 0
    for t, tid, call, kind, val, _ in events:
        if call == "openat" and kind == "exit" and tid == comm_tid:
            j = G.turn_index(ts, te, t)
            (ok_by if val >= 0 else fail_by)[j] += 1
        elif kind == "enter" and call == "munmap" and val.get("len", 0) >= BIG_MUNMAP:
            big_unmap += 1
        elif kind == "enter" and call == "unlinkat" and tid == comm_tid:
            unlink += 1
        elif kind == "enter" and call in A.RENAME and tid == comm_tid:
            rename += 1
        elif kind == "enter" and call == "kill" and tid == comm_tid:
            kills += 1
    probe = sorted(j for j in ok_by if j >= 0)
    is_probe = np.zeros(len(ts), dtype=bool)
    is_probe[probe] = True
    idle_len = turn_len[~is_probe]
    med_idle = float(np.median(idle_len)) if len(idle_len) else float("nan")
    ep = turn_len[probe] - med_idle

    # Przebiegi sondy: na D2s kazdy obrot z sonda osobno (jak R603G), na D2r ciag kolejnych obrotow.
    rounds = rounds_of(probe) if side == "D2r" else [[j] for j in probe]
    # Przebieg D2r przeciety granica okna (zaczety przed t0 albo konczony po t1) ma mniej niz N obrotow.
    edge = [g[0] == 0 or g[-1] == len(ts) - 1 for g in rounds]
    partial = [side == "D2r" and len(g) != n for g in rounds]
    starts = np.array([ts[g[0]] for g, e in zip(rounds, edge) if not (e and g[0] == 0 and side == "D2r")], dtype=np.int64)
    gaps = np.diff(starts) if len(starts) > 1 else np.zeros(0)

    clients = G.load_clients(run_dir / "clients.tsv")
    pinned = [l.split("\t")[-1] == "0" for l in (run_dir / "rt.txt").read_text().splitlines()
              if l.startswith("tid=") and "policy=SCHED_FIFO" not in l]
    w1 = (bool(meta.get("rt_ok")) and meta.get("trace_overrun") == 0 and meta.get("governor") == "performance"
          and bool(pinned) and all(pinned))
    rates = [(c["rows1"] - c["rows0"]) / ((c["c1"] - c["c0"]) / 1e9) for c in clients]
    w2 = len(clients) == n and all(c["alive"] for c in clients) and all(r >= W2_MIN * RATE for r in rates)
    w3 = big_unmap == 0 and unlink == 0 and rename == 0 and kills == 0
    gaps_ok = bool(len(gaps)) and bool(((gaps >= GAP_LO_NS) & (gaps <= GAP_HI_NS)).all())
    if side == "D2s":
        w4 = (all(ok_by[j] == n for j in probe) and sum(fail_by[j] for j in probe) == 0 and ok_by.get(-1, 0) == 0
              and abs(len(probe) - w_s) <= 1 and gaps_ok)
    else:
        w4 = (all(ok_by[j] == 1 for j in probe) and sum(fail_by[j] for j in probe) == 0 and ok_by.get(-1, 0) == 0
              and all(e for p, e in zip(partial, edge) if p) and abs(len(rounds) - w_s) <= 1 and gaps_ok)
    gates = {"W1": w1, "W2": w2, "W3": w3, "W4": w4}

    s = A.load_slots(run_dir / "slots.csv")
    sel = (s["deadline"] >= t0) & (s["deadline"] <= t1)
    sw = {k: v[sel] for k, v in s.items()}
    h = D.H[meta["family"]]
    model = D.SlotModel(sw, np.ones(len(sw["deadline"]), dtype=bool), h)
    windows = [(int(ts[g[0]]), int(te[g[-1]])) for g in rounds]
    ctl = np.ones(len(sw["deadline"]), dtype=bool)
    for w in windows:
        idx, _ = E.affected_idx(model, [w])
        for i in idx:
            ctl[max(0, i - CTL_PAD_SLOTS):i + CTL_PAD_SLOTS + 1] = False
    model = D.SlotModel(sw, ctl, h)
    clusters = [c for c in (E.affected_cluster(model, [w], rngs["placebo"]) for w, p in zip(windows, partial) if not p)
                if c is not None]
    round_len = np.array([b - a for (a, b), p in zip(windows, partial) if not p], dtype=np.int64)

    k3 = {"compute50": pct(sw["compute"][ctl], 50), "wake99": pct(sw["wake"][ctl], 99), "e2e99": pct(sw["e2e"][ctl], 99)}
    p99_idle = pct(idle_len, 99)
    trim = float(idle_len[idle_len <= p99_idle].mean()) if len(idle_len) else float("nan")
    fx_n, fx_max = G.futex_rt(events, rt)
    r = {"dir": run_dir, "meta": meta, "side": side, "n": n, "pair": meta["run"], "w_s": w_s, "t0": t0, "t1": t1,
         "ts": ts, "te": te, "comm_tid": comm_tid, "sleep_other": others, "probe": probe, "ok_by": ok_by,
         "fail_by": fail_by, "orphan_ok": ok_by.get(-1, 0), "gaps": gaps, "idle_len": idle_len, "med_idle": med_idle,
         "trim": trim, "ep": ep, "probe_len": turn_len[probe], "w3": (big_unmap, unlink, rename, kills), "gates": gates,
         "rates": rates, "clients": clients, "model": model, "ctl": ctl, "clusters": clusters,
         "n_windows": len(windows), "k3": k3, "all50": pct(sw["compute"], 50), "alle2e99": pct(sw["e2e"], 99),
         "cpu": G.cpu_busy(run_dir / "cpu.txt"), "futex": (fx_n, fx_max), "vmlck": meta.get("rt_vmlck_kB_connected"),
         "n_slots": int(len(sw["deadline"])), "n_ctl": int(ctl.sum()), "rounds": rounds, "partial": sum(partial),
         "round_len": round_len, "windows": windows}
    if (run_dir / "deaths.tsv").exists():
        dp = death_phase(run_dir, side, n, rt)
        rcs = [d["rc"] for d in dp["deaths"]]
        gates["W5"] = (len(dp["deaths"]) == n and all(rc == "-9" for rc in rcs) and meta.get("death_trace_overrun") == 0
                       and meta.get("engine_rc") == 0 and not meta.get("leftovers_after"))
        r["death"] = dp
    r["valid"] = all(gates.values())
    return r


def h0_clusters(r, lengths, rng):
    """H0 K3p: okna syntetyczne o dlugosciach przebiegow D2r tego samego N na przebiegu D2s, po jednym na sekunde okna,
    od poczatku obrotu najblizszego fazie jednostajnej, nie blizej niz H0_GAP_SLOTS slotow od przebiegu sondy D2s."""
    out = []
    m, ts = r["model"], r["ts"]
    gap = H0_GAP_SLOTS * m.period
    wins = r["windows"]
    for _ in range(H0_SETS):
        for k in range(int(r["w_s"])):
            t = r["t0"] + k * 1_000_000_000 + int(rng.integers(0, 1_000_000_000))
            j = int(np.searchsorted(ts, t))
            if j >= len(ts):
                continue
            a = int(ts[j])
            b = a + int(rng.choice(lengths))
            if any(a - gap <= wb and wa <= b + gap for wa, wb in wins):
                continue
            c = E.affected_cluster(m, [(a, b)], rng)
            if c is not None:
                out.append(c)
    return out


# ---------------------------------------------------------------- raport

def run_dirs(n_dir, side):
    return sorted(p for p in n_dir.iterdir() if p.is_dir() and p.name.startswith(side + "_"))


def regress(P, Q, f, delta_of, label, prefix):
    """Reguła R603G: P = D2s (odniesienie), Q = D2r."""
    c = [x for x in (f(r) for r in P) if not math.isnan(x)]
    p = [x for x in (f(r) for r in Q) if not math.isnan(x)]
    if not (c and p):
        return f"- **{prefix}**, {label}: brak danych obu stron.", "BRAK DANYCH"
    diff = float(np.median(p) - np.median(c))
    spread = max(max(c) - min(c), max(p) - min(p))
    delta = delta_of(c)
    thr = max(spread, delta)
    pv = A.permutation_mw_two_sided(c, p)
    state = "REGRESJA D2r" if diff > thr else ("D2r lepsze poza progiem" if diff < -thr else "bez regresji")
    line = (f"- **{prefix}**, {label} per przebieg: mediana D2r - D2s = {diff / 1e3:.3f} µs, rozrzut wewnątrz strony do "
            f"{spread / 1e3:.3f} µs, δ = {delta / 1e3:.3f} µs, permutacyjny MW p = {pv:.3g} - **{state}**.")
    return line, state


def diff_boot(a, b, rng):
    """Srednia a - srednia b, strony losowane niezaleznie."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if not (len(a) and len(b)):
        return np.nan, np.nan, np.nan
    d = [a[rng.integers(0, len(a), len(a))].mean() - b[rng.integers(0, len(b), len(b))].mean() for _ in range(D.BOOT)]
    return float(a.mean() - b.mean()), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def k0_side(rs, side, n):
    L = np.array([x for r in rs for x in r["death"]["L"]], dtype=np.int64) if rs else np.zeros(0, dtype=np.int64)
    cat = Counter()
    for r in rs:
        cat.update(r["death"]["cat"])
    killed = sum(len(r["death"]["deaths"]) for r in rs)
    ok = killed > 0 and cat["w granicy"] == killed
    return {"L": L, "cat": cat, "killed": killed, "ok": ok, "hi": l_max_ns(side, n),
            "turn": np.array([x for r in rs for x in r["death"]["det_turn"]], dtype=np.int64),
            "rank": [x for r in rs for x in r["death"]["rank"]], "lone": sum(r["death"]["lone"] for r in rs)}


def n_report(n, P, Q, rngs, ctx):
    Pv, Qv = [r for r in P if r["valid"]], [r for r in Q if r["valid"]]
    lines = [f"## N = {n}", "", "| wielkość | D2s | D2r |", "|---|---|---|"]

    def row(label, f):
        lines.append(f"| {label} | {f(Pv)} | {f(Qv)} |")

    def cat(rs, key):
        return np.concatenate([r[key] for r in rs]) if rs else np.zeros(0)

    lines.append(f"| przebiegi: ważne / wszystkie | {len(Pv)} / {len(P)} | {len(Qv)} / {len(Q)} |")
    row("obroty z sondą na przebieg: min / max", lambda x: f"{min(len(r['probe']) for r in x)} / {max(len(r['probe']) for r in x)}" if x else "-")
    row("przebiegi sondy na przebieg: min / max (w tym przecięte granicą okna)", lambda x: (
        f"{min(len(r['rounds']) for r in x)} / {max(len(r['rounds']) for r in x)} ({sum(r['partial'] for r in x)})") if x else "-")
    row("odstęp początków przebiegów [ms] min / p50 / max", lambda x: " / ".join(
        f"{v / 1e6:.3f}" for v in (lambda g: (g.min(), np.median(g), g.max()))(cat(x, "gaps"))) if len(cat(x, "gaps")) else "-")
    row("przebieg sondy [µs] p50 / p99 / max", lambda x: D.dist(cat(x, "round_len")))
    row("K4: obrót z sondą [µs] p50 / p99 / max", lambda x: D.dist(cat(x, "probe_len")))
    row("K4: nadwyżka E_p [µs] p50 / p99 / max", lambda x: D.dist(cat(x, "ep")))
    row("obrót bezczynny [µs] p50 / p99 / max", lambda x: D.dist(cat(x, "idle_len")))
    row("obrót bezczynny, średnia obcięta do p99 [µs] (mediana przebiegów)",
        lambda x: f"{np.median([r['trim'] for r in x]) / 1e3:.3f}" if x else "-")
    row("sloty okna / kontrolne (średnio na przebieg)",
        lambda x: f"{np.mean([r['n_slots'] for r in x]):.0f} / {np.mean([r['n_ctl'] for r in x]):.0f}" if x else "-")
    row("compute p50 wszystkich slotów okna [µs] (mediana przebiegów)",
        lambda x: f"{np.median([r['all50'] for r in x]) / 1e3:.2f}" if x else "-")
    row("e2e p99 wszystkich slotów okna [µs] (mediana przebiegów)",
        lambda x: f"{np.median([r['alle2e99'] for r in x]) / 1e3:.2f}" if x else "-")
    row("zajętość rdzeni 0-2 (średnio)", lambda x: f"{np.mean([r['cpu'] for r in x]):.3f}" if x else "-")
    row("wiersze/s klienta: min / mediana", lambda x: f"{min(v for r in x for v in r['rates']):.1f} / "
        f"{np.median([v for r in x for v in r['rates']]):.1f}" if x else "-")
    row("VmLck po podłączeniu [MiB] (mediana)", lambda x: f"{np.median([r['vmlck'] for r in x]) / 1024:.0f}" if x else "-")
    row("O1: futex wątku RT na przebieg / max [µs]",
        lambda x: f"{np.mean([r['futex'][0] for r in x]):.1f} / {max(r['futex'][1] for r in x) / 1e3:.0f}" if x else "-")

    # K3p (opisowo, J3)
    sp_ss, sr_ss = [c for r in Pv for c in r["clusters"]], [c for r in Qv for c in r["clusters"]]
    lengths = cat(Qv, "round_len")
    h0 = [c for r in Pv for c in h0_clusters(r, lengths, rngs["h0"])] if len(lengths) else []
    s_p = E.mean_boot(E.series_s(sp_ss), rngs["boot"]) if sp_ss else (np.nan,) * 3
    s_r = E.mean_boot(E.series_s(sr_ss), rngs["boot"]) if sr_ss else (np.nan,) * 3
    s0 = E.mean_boot(E.series_s(h0), rngs["boot"]) if h0 else (np.nan,) * 3
    dd = diff_boot(E.series_s(sr_ss), E.series_s(sp_ss), rngs["boot"]) if sp_ss and sr_ss else (np.nan,) * 3
    dm_p = E.aff_boot(sp_ss, rngs["boot"]) if sp_ss else ((np.nan, np.nan), (np.nan, np.nan), None)
    dm_r = E.aff_boot(sr_ss, rngs["boot"]) if sr_ss else ((np.nan, np.nan), (np.nan, np.nan), None)
    half = (s0[2] - s0[1]) / 2 if h0 else float("nan")

    def ci(v, k=2):
        return f"{v[0] / 1e3:+.{k}f} ({v[1] / 1e3:+.{k}f}..{v[2] / 1e3:+.{k}f})"

    lines += [
        f"| K3p: przebiegi sondy z placebo / sloty dotknięte na przebieg | {len(sp_ss)} / "
        f"{np.mean([len(c['real']) for c in sp_ss]) if sp_ss else float('nan'):.2f} | {len(sr_ss)} / "
        f"{np.mean([len(c['real']) for c in sr_ss]) if sr_ss else float('nan'):.2f} |",
        f"| K3p: S [µs/przebieg = µs/s] (95 %) | {ci(s_p)} | {ci(s_r)} |",
        f"| K3p: Δ mediany slotów dotkniętych [µs] (95 %) | {dm_p[0][0] / 1e3:+.2f} ({dm_p[1][0] / 1e3:+.2f}..{dm_p[1][1] / 1e3:+.2f}) | "
        f"{dm_r[0][0] / 1e3:+.2f} ({dm_r[1][0] / 1e3:+.2f}..{dm_r[1][1] / 1e3:+.2f}) |",
        f"| H0 K3p (okna o długości przebiegów D2r na D2s): okna / S_H0 [µs] (95 %) / półszerokość [µs] | {len(h0)} / "
        f"{ci(s0)} / {half / 1e3:.2f} | - |"]

    # K0 (faza zgonów)
    k0 = {side: k0_side(rs, side, n) for side, rs in (("D2s", Pv), ("D2r", Qv))}

    def k0_row(label, f):
        lines.append(f"| {label} | {f(k0['D2s'])} | {f(k0['D2r'])} |")

    k0_row("K0: zabici / w granicy / poza granicą / bez wykrycia (zwolnieni) / niewykryci", lambda k: (
        f"{k['killed']} / {k['cat']['w granicy']} / {k['cat']['poza granica']} / {k['cat']['bez wykrycia, zwolnione']} / "
        f"{k['cat']['niewykryte']}"))
    k0_row("K0: granica L [s]", lambda k: f"{k['hi'] / 1e9:.4f}")
    k0_row("K0: L [ms] min / p50 / p99 / max", lambda k: ms_dist(k["L"]))
    k0_row("K0: wykryte, zwolnione bez puli / bez zwolnienia w śladzie / samotne wykrycia", lambda k: (
        f"{k['cat']['wykryte, zwolnione bez puli']} / {k['cat']['wykryte, bez zwolnienia w sladzie']} / {k['lone']}"))
    k0_row("K0: obrót z wykryciem [µs] p50 / p99 / max", lambda k: D.dist(k["turn"]))
    k0_row("K0: nachylenie L wobec pozycji w przebiegu [ms na pozycję]", lambda k: (
        f"{np.polyfit([a for a, _ in k['rank']], [b for _, b in k['rank']], 1)[0] / 1e6:+.2f}"
        if len({a for a, _ in k['rank']}) >= 2 else "-"))
    lines.append("")

    enough = len(Pv) >= MIN_RUNS and len(Qv) >= MIN_RUNS
    # K4
    ep = cat(Qv, "ep")
    if n == K4_N:
        k4 = ("NIEROZSTRZYGNIĘTE (liczność)" if not enough else ("ZDANE" if pct(ep, 99) <= K4_MAX_NS else "NIEZDANE"))
        lines.append(f"- **K4** (N = {K4_N}): p99 E_p D2r = {us(pct(ep, 99))} µs wobec {K4_MAX_NS / 1e3:.0f} µs "
                     f"(D2s: {us(pct(cat(Pv, 'ep'), 99))} µs). Werdykt: **{k4}**.")
    else:
        k4 = "-"
        lines.append(f"- K4 (opisowo przy N = {n}): p99 E_p D2r = {us(pct(ep, 99))} µs, D2s = {us(pct(cat(Pv, 'ep'), 99))} µs.")
    # K0
    if not enough:
        k0v = "NIEROZSTRZYGNIĘTE (liczność)"
    else:
        k0v = "ZDANE" if k0["D2s"]["ok"] and k0["D2r"]["ok"] else "NIEZDANE"
    lines.append(f"- **K0** (-5 ms ≤ L ≤ {k0['D2r']['hi'] / 1e9:.4f} s na D2r, ≤ {k0['D2s']['hi'] / 1e9:.4f} s na D2s): D2r "
                 f"{k0['D2r']['cat']['w granicy']} z {k0['D2r']['killed']} w granicy, D2s {k0['D2s']['cat']['w granicy']} z "
                 f"{k0['D2s']['killed']}. Werdykt: **{k0v}**.")
    # K3p: reguła odczytu ryzyka
    if math.isnan(dd[1]):
        risk = "brak danych"
    elif dd[1] > RISK_NS:
        risk = "potwierdzone"
    elif dd[2] < RISK_NS:
        risk = "wykluczone"
    else:
        risk = "nierozstrzygnięte"
    lines.append(f"- K3p (opisowo, J3): S(D2r) - S(D2s) = {ci(dd)} µs na sekundę, H0 półszerokość {half / 1e3:.2f} µs. "
                 f"Ryzyko z planu (próg {RISK_NS / 1e3:.0f} µs/s): **{risk}**.")

    verdicts = {"K4": k4, "K0": k0v, "K3p ryzyko": risk}
    for key, f, label in (("compute50", lambda r: r["k3"]["compute50"], "compute_ns p50"),
                          ("wake99", lambda r: r["k3"]["wake99"], "wake_lag_ns p99"),
                          ("e2e99", lambda r: r["k3"]["e2e99"], "e2e_ns p99")):
        line, state = regress(Pv, Qv, f, lambda c: K3_REL * float(np.median(c)), label, "K3")
        lines.append(line)
        verdicts[f"K3 {label}"] = state
    line, state = regress(Pv, Qv, lambda r: r["trim"], lambda c: K3T_NS, "obrót bezczynny, średnia obcięta do p99", "K3t")
    lines.append(line)
    verdicts["K3t"] = state
    for f, label in ((lambda r: pct(r["idle_len"], 50), "obrót bezczynny p50"),
                     (lambda r: pct(r["idle_len"], 99), "obrót bezczynny p99")):
        line, _ = regress(Pv, Qv, f, lambda c: 0.0, label + " (opisowo, reguła R603F)", "K3t")
        lines.append(line.replace(", δ = 0.000 µs", ""))
    # Odtwarzalność R603G (opisowo)
    if n in R603G_EP:
        lines.append(f"- Odtwarzalność R603G (strona D2s, opisowo): E_p p50 / p99 / max {D.dist(cat(Pv, 'ep'))} µs wobec "
                     f"{R603G_EP[n]} µs; obrót bezczynny {D.dist(cat(Pv, 'idle_len'))} µs wobec {R603G_IDLE[n]} µs.")
    lines.append("")
    ctx["verdicts"][n] = verdicts
    for side, rs in (("D2s", Pv), ("D2r", Qv)):
        ctx["ep_runs"][side][n] = [(float(np.median(r["ep"])), float(pct(r["ep"], 99))) for r in rs if len(r["ep"])]
    return lines


def slope_boot(by_n, idx, rng):
    """Nachylenie prostej najmniejszych kwadratow (wartosc idx per przebieg) wzgledem N; przebiegi losowane w obrebie N."""
    ns = sorted(n for n, v in by_n.items() if v)
    if len(ns) < 2:
        return (np.nan,) * 3

    def fit(sample):
        x = [n for n in ns for _ in sample[n]]
        y = [v[idx] for n in ns for v in sample[n]]
        return np.polyfit(x, y, 1)[0]

    point = fit(by_n)
    b = []
    for _ in range(D.BOOT):
        b.append(fit({n: [by_n[n][i] for i in rng.integers(0, len(by_n[n]), len(by_n[n]))] for n in ns}))
    return float(point), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def main_report(raw, seed, out):
    rngs = D.rng_set(seed)
    ctx = {"verdicts": {}, "ep_runs": {"D2s": {}, "D2r": {}}}
    fam_dir = raw / FAM
    report = ["# R607 - wynik", "", f"Źródło: `{raw.name}`, ziarna: placebo {seed}, bootstrap {seed + 1}, H0 {seed + 2}.", ""]
    n_dirs = sorted((p for p in fam_dir.iterdir() if p.is_dir() and p.name.startswith("N")), key=lambda p: int(p.name[1:]))
    for n_dir in n_dirs:
        n = int(n_dir.name[1:])
        P = [analyze_run(d, rngs) for d in run_dirs(n_dir, "D2s")]
        Q = [analyze_run(d, rngs) for d in run_dirs(n_dir, "D2r")]
        bad = [f"{r['dir'].name} ({', '.join(k for k, v in r['gates'].items() if not v)})" for r in P + Q if not r["valid"]]
        report += n_report(n, P, Q, rngs, ctx)
        report += [f"Przebiegi nieważne: {', '.join(bad) if bad else 'brak'}.", ""]
    report += ["## Niezależność od N (K4n)", ""]
    k4n = "-"
    for side in SIDES:
        sl = slope_boot(ctx["ep_runs"][side], 0, rngs["boot"])
        s99 = slope_boot(ctx["ep_runs"][side], 1, rngs["boot"])
        report.append(f"- {side}: nachylenie median E_p przebiegów względem N {sl[0] / 1e3:+.2f} ({sl[1] / 1e3:+.2f}.."
                      f"{sl[2] / 1e3:+.2f}) µs na subskrybenta; nachylenie p99 (opisowo) {s99[0] / 1e3:+.2f} "
                      f"({s99[1] / 1e3:+.2f}..{s99[2] / 1e3:+.2f}) µs.")
        if side == "D2r":
            runs_ok = all(len(v) >= MIN_RUNS for v in ctx["ep_runs"]["D2r"].values()) and len(ctx["ep_runs"]["D2r"]) >= 2
            if not runs_ok:
                k4n = "NIEROZSTRZYGNIĘTE (liczność)"
            elif sl[2] < DELTA_N_NS:
                k4n = "ZDANE"
            elif sl[1] > DELTA_N_NS:
                k4n = "NIEZDANE"
            else:
                k4n = "NIEROZSTRZYGNIĘTE"
    report += [f"- **K4n** (δ_n = {DELTA_N_NS / 1e3:.0f} µs na subskrybenta, strona D2r). Werdykt: **{k4n}**.", ""]
    report += ["## Werdykty", "", f"K4n: {k4n}.", "",
               "| N | K4 | K0 | K3 compute p50 | K3 wake p99 | K3 e2e p99 | K3t | K3p: ryzyko (opisowo) |",
               "|---|---|---|---|---|---|---|---|"]
    for n, v in sorted(ctx["verdicts"].items()):
        report.append(f"| {n} | {v['K4']} | {v['K0']} | {v['K3 compute_ns p50']} | {v['K3 wake_lag_ns p99']} | "
                      f"{v['K3 e2e_ns p99']} | {v['K3t']} | {v['K3p ryzyko']} |")
    text = "\n".join(report) + "\n"
    if out:
        out.write_text(text)
    print(text)


# ---------------------------------------------------------------- bramki i test analizy

def gates(raw):
    rngs = D.rng_set(6034)
    runs = []
    for meta_path in sorted(raw.rglob("meta.json")):
        r = analyze_run(meta_path.parent, rngs)
        runs.append(r)
        g = " ".join(f"{k}={'tak' if v else 'NIE'}" for k, v in r["gates"].items())
        dp = r.get("death", {"L": [], "cat": Counter(), "deaths": []})
        lens = Counter(len(x) for x in r["rounds"])
        print(f"{r['dir'].relative_to(raw)}: N={r['n']} {g}; sonda: obroty {len(r['probe'])}, przebiegi {len(r['rounds'])} "
              f"(długości {dict(sorted(lens.items()))}, przecięte {r['partial']}), openat/obrót "
              f"{sorted(set(r['ok_by'][j] for j in r['probe']))}, nieudane {sum(r['fail_by'][j] for j in r['probe'])}, "
              f"poza obrotami {r['orphan_ok']}, odstęp [µs] {D.dist(r['gaps']) if len(r['gaps']) else '-'}; "
              f"W3 {r['w3']}; wiersze/s min {min(r['rates']) if r['rates'] else float('nan'):.1f}; zajętość 0-2 {r['cpu']:.3f}; "
              f"E_p [µs] {D.dist(r['ep'])}; przebieg [µs] {D.dist(r['round_len'])}; obrót bezczynny p50/p99/p99,9 "
              f"{us(pct(r['idle_len'], 50))} / {us(pct(r['idle_len'], 99))} / {us(pct(r['idle_len'], 99.9))} µs; "
              f"średnia obcięta {r['trim'] / 1e3:.3f} µs; sloty okna/kontrolne {r['n_slots']}/{r['n_ctl']}; "
              f"K0: zabici {len(dp['deaths'])}, {dict(dp['cat'])}, L [ms] {ms_dist(np.array(dp['L']))}, "
              f"granica {l_max_ns(r['side'], r['n']) / 1e9:.4f} s; client_rc {r['meta'].get('client_rc')}; "
              f"death_overrun {r['meta'].get('death_trace_overrun')}; engine_rc {r['meta'].get('engine_rc')}")
    for n in sorted({r["n"] for r in runs}):
        P = [r for r in runs if r["n"] == n and r["side"] == "D2s"]
        Q = [r for r in runs if r["n"] == n and r["side"] == "D2r"]
        if P and Q:
            lengths = np.concatenate([r["round_len"] for r in Q])
            h0 = [c for r in P for c in h0_clusters(r, lengths, rngs["h0"])] if len(lengths) else []
            s0 = E.mean_boot(E.series_s(h0), rngs["boot"]) if h0 else (np.nan,) * 3
            for side, rs in (("D2s", P), ("D2r", Q)):
                ss = [c for r in rs for c in r["clusters"]]
                s = E.mean_boot(E.series_s(ss), rngs["boot"]) if ss else (np.nan,) * 3
                print(f"N={n} {side}: wstępnie S {s[0] / 1e3:+.2f} ({s[1] / 1e3:+.2f}..{s[2] / 1e3:+.2f}) µs z {len(ss)} przebiegów")
            print(f"N={n}: H0 {len(h0)} okien, S_H0 {s0[0] / 1e3:+.2f}, półszerokość {(s0[2] - s0[1]) / 2e3:.2f} µs")
    ok = all(r["valid"] for r in runs)
    print("BRAMKI W1-W5: " + ("wszystkie spełnione" if ok else "NIESPEŁNIONE"))


def _same(a, b):
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        return np.array_equal(np.asarray(a), np.asarray(b))
    return a == b


def parser_check(raw_g, raw_f):
    """(1) analyze_run na danych D2s R603G = analyze_run R603G (pola i klastry placebo) i Wydruk analizy R603G;
    (2) rozpoznanie wykrycia fazy zgonow na danych D2s R603F = wiersze K0 Wydruku analizy R603F;
    (3) przebieg D2r na danych D2s R603G: N = 1 -> 60 przebiegow po 1 obrocie, N = 8 i 16 -> 0 obrotow z jednym openat."""
    ok = True
    rg, rm = D.rng_set(6034), D.rng_set(6034)
    fam_dir = raw_g / FAM
    n_dirs = sorted((p for p in fam_dir.iterdir() if p.is_dir() and p.name.startswith("N")), key=lambda p: int(p.name[1:]))
    for n_dir in n_dirs:
        n = int(n_dir.name[1:])
        mine, diffs = [], []
        for d in run_dirs(n_dir, "D2s"):
            a = G.analyze_run(d, rg)
            b = analyze_run(d, rm)
            mine.append(b)
            for key in ("probe", "ep", "idle_len", "gaps", "ctl", "trim", "k3", "n_ctl", "gates", "valid"):
                if not _same(a[key], b[key]):
                    diffs.append(f"{d.name}:{key}")
            if len(a["clusters"]) != len(b["clusters"]) or any(
                    x["real"] != y["real"] or x["pl"] != y["pl"] for x, y in zip(a["clusters"], b["clusters"])):
                diffs.append(f"{d.name}:clusters")
        ep = D.dist(np.concatenate([r["ep"] for r in mine]))
        idle = D.dist(np.concatenate([r["idle_len"] for r in mine]))
        same = not diffs and ep == R603G_EP[n] and idle == R603G_IDLE[n]
        line = f"(1) N = {n}: pola i klastry {'równe' if not diffs else 'RÓŻNE ' + ', '.join(diffs[:6])}; E_p {ep} (R603G: {R603G_EP[n]}); obrót bezczynny {idle} (R603G: {R603G_IDLE[n]})"
        if n == 1:
            sp = E.mean_boot(E.series_s([c for r in mine for c in r["clusters"]]), D.rng_set(6034)["boot"])
            got = f"{sp[0] / 1e3:+.2f} ({sp[1] / 1e3:+.2f}..{sp[2] / 1e3:+.2f})"
            same &= got == R603G_SP_N1
            line += f"; S_p {got} (R603G: {R603G_SP_N1})"
        ok &= same
        print(line + (" - zgodne" if same else " - RÓŻNE"))
        # (3)
        forced = [analyze_run(d, D.rng_set(6034), side="D2r") for d in run_dirs(n_dir, "D2s")]
        one = sum(sum(1 for j in r["probe"] if r["ok_by"][j] == 1) for r in forced)
        if n == 1:
            good = all(len(r["rounds"]) == 60 and all(len(g) == 1 for g in r["rounds"]) for r in forced)
            print(f"(3) N = 1: przebiegi D2r na przebieg {sorted({len(r['rounds']) for r in forced})}, długości "
                  f"{sorted({len(g) for r in forced for g in r['rounds']})} - {'zgodne' if good else 'RÓŻNE'}")
        else:
            good = one == 0
            print(f"(3) N = {n}: obroty z jednym udanym openat {one} - {'zgodne' if good else 'RÓŻNE'}")
        ok &= good
    for fam, (det_exp, lone_exp, dist_exp) in R603F_K0.items():
        L, det, lone = [], 0, 0
        for d in F.run_dirs(raw_f / fam, "D2s"):
            events = A.parse_trace(d / "trace.txt")
            rt = A.rt_tids(d / "rt.txt")
            conns = A.load_conns(d / "conns.tsv")
            cls = F.classify_kills(events, conns, rt)
            kws = F.kill_windows_f(events, conns, rt)
            det += sum(len(x["det"]) for x in cls)
            lone += sum(len(x["lone"]) for x in cls)
            # Jak probe_obs R603F: L tylko dla okien R_C z wykryciem (wylaczenia K1'' nie maja wykrycia przed R_C).
            L += [w["t_det"] - c["end"] for c, w in zip(conns, kws) if w is not None and w.get("t_det") is not None]
        got = ms_dist(np.array(L))
        good = det == det_exp and lone == lone_exp and got == dist_exp
        ok &= good
        print(f"(2) {fam}: wykrycia {det} / samotne {lone}, L [ms] {got} (R603F: {det_exp} / {lone_exp}, {dist_exp}) - "
              f"{'zgodne' if good else 'RÓŻNE'}")
    print("TEST ANALIZY: " + ("ZDANY" if ok else "NIEZDANY"))
    if not ok:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--seed", type=int, default=6034)
    ap.add_argument("--gates", action="store_true", help="bramki W1-W5 per przebieg (suchy przebieg)")
    ap.add_argument("--parser-check", action="store_true", help="--raw wskazuje surowe dane R603G")
    ap.add_argument("--r603f", type=Path, help="surowe dane R603F (test analizy, punkt 2)")
    args = ap.parse_args()
    if args.parser_check:
        if not args.r603f:
            sys.exit("--parser-check wymaga --r603f")
        parser_check(args.raw, args.r603f)
    elif args.gates:
        gates(args.raw)
    else:
        main_report(args.raw, args.seed, args.out)


if __name__ == "__main__":
    main()
