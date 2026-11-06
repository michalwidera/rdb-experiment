#!/usr/bin/env python3
"""R603G: analiza przebiegow run_one.py wedlug kryteriow K3p, K4, K3, K3t i bramek W1-W4 z README.md.

Uzycie (Python >= 3.10 z NumPy, np. retractordb/.venv-python/bin/python3):
  analyze.py --raw <katalog>/raw [--out wynik.txt] [--seed 6034]   raport kampanii (raw/uc05/N<n>/<strona>_<para>)
  analyze.py --raw <katalog> --gates                               bramki W1-W4 per przebieg (suchy przebieg)
  analyze.py --raw <R603F>/raw --parser-check                      test analizy na danych R603F (Kolejnosc, punkt 2)

Parser R603F (a przez niego R603E, R603D i R603C) jest importowany BEZ ZMIAN z ../results_20261106_R603F/analyze.py:
parse_trace, rt_tids, comm_turns, load_slots, SlotModel, affected_idx, affected_cluster, series_s, mean_boot, aff_boot,
permutation_mw_two_sided. Wypisuje tylko liczby wyprowadzone (embargo korpusu).
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


def _load_r603f():
    spec = importlib.util.spec_from_file_location("analyze_r603f", HERE.parent / "results_20261106_R603F" / "analyze.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


F = _load_r603f()
E = F.E
D = F.D
A = F.A

FAM = "uc05"
RATE = 799.9  # wiersze/s strumienia uc05 (pojemnosc 8000 / 10 s, R603F Ustalenia punkt 6)
DELTA_S_NS = 10_000  # K3p, G2
H0_HALF_MAX_NS = 5_000  # waznosc K3p: polszerokosc H0 <= delta_S / 2
K4_MAX_NS = 1_000_000  # K4: p99 E_p przy N = 32 <= kQueuePollInterval
K4_N = 32
K3_REL = 0.05  # K3: delta = 5 % mediany C'
K3T_NS = 500  # K3t: delta_t
W2_MIN = 0.95
GAP_LO_NS, GAP_HI_NS = 999_998_000, 1_010_000_000  # W4: odstep przebiegow sondy 1,000-1,010 s (kwant znacznika 1 us)
H0_SETS = 5
MIN_RUNS = 8
# Sloty kontrolne D2s: bez slotow dotknietych przez przebieg sondy i bez CTL_PAD_SLOTS slotow przed i po nich (aneks A1;
# GUARD_NS R603C = 500 ms przy przebiegu co 1 s nie zostawilby ani jednego slotu kontrolnego).
CTL_PAD_SLOTS = 2
SIDES = ("Cp", "D2s")
NAMES = {"Cp": "C'", "D2s": "D2s"}
BIG_MUNMAP = 1 << 20


def die(msg):
    print(f"analyze.py: {msg}", file=sys.stderr)
    sys.exit(2)


def pct(a, q):
    return A.pct(a, q) if len(a) else float("nan")


def us(ns, digits=1):
    return D.fmt_us(ns, digits)


# ---------------------------------------------------------------- jeden przebieg

def load_clients(path):
    out = []
    for line in path.read_text().splitlines()[1:]:
        r = line.split("\t")
        out.append({"i": int(r[0]), "pid": int(r[1]), "start": int(r[2]), "first": None if r[3] == "-" else int(r[3]),
                    "rows0": int(r[4]), "c0": int(r[5]), "rows1": int(r[6]), "c1": int(r[7]), "alive": r[8] == "1"})
    return out


def cpu_busy(path):
    """Srednia zajetosc rdzeni 0-2 w oknie z dwoch odczytow /proc/stat."""
    blocks, cur = {}, None
    for line in path.read_text().splitlines():
        if line.startswith("#"):
            cur = line[2:]
            blocks[cur] = {}
        else:
            f = line.split()
            blocks[cur][f[0]] = [int(x) for x in f[1:]]
    busy = []
    for cpu, b in blocks["t1"].items():
        a = blocks["t0"][cpu]
        d = [y - x for x, y in zip(a, b)]
        idle = d[3] + d[4]
        busy.append(1.0 - idle / sum(d[:8]) if sum(d[:8]) else float("nan"))
    return float(np.mean(busy))


def turn_index(ts, te, t):
    j = int(np.searchsorted(ts, t, side="right")) - 1
    return j if j >= 0 and t <= te[j] else -1


def futex_rt(events, rt):
    """O1: (liczba wywolan futex watku RT, najdluzsze [ns])."""
    open_, durs = {}, []
    for t, tid, call, kind, _, _ in events:
        if call != "futex" or tid not in rt:
            continue
        if kind == "enter":
            open_[tid] = t
        elif tid in open_:
            durs.append(t - open_.pop(tid))
    return len(durs), (max(durs) if durs else 0)


def analyze_run(run_dir, rngs):
    meta = json.loads((run_dir / "meta.json").read_text())
    side, n = meta["side"], meta["n"]
    win = json.loads((run_dir / "window.json").read_text())
    t0, t1 = win["t0_ns"], win["t1_ns"]
    w_s = (t1 - t0) / 1e9
    events = A.parse_trace(run_dir / "trace.txt")
    rt = A.rt_tids(run_dir / "rt.txt")
    ts, te, comm_tid, others = D.comm_turns(events, None, rt)
    turn_len = te - ts

    ok_by, fail_by, ok_first = Counter(), Counter(), {}
    big_unmap = unlink = rename = kills = 0
    for t, tid, call, kind, val, _ in events:
        if call == "openat" and kind == "exit" and tid == comm_tid:
            j = turn_index(ts, te, t)
            (ok_by if val >= 0 else fail_by)[j] += 1
            if val >= 0 and j >= 0:
                ok_first.setdefault(j, t)
        elif kind == "enter" and call == "munmap" and val.get("len", 0) >= BIG_MUNMAP:
            big_unmap += 1
        elif kind == "enter" and call == "unlinkat":
            unlink += 1
        elif kind == "enter" and call in A.RENAME:
            rename += 1
        elif kind == "enter" and call == "kill":
            kills += 1
    probe = sorted(j for j in ok_by if j >= 0)
    is_probe = np.zeros(len(ts), dtype=bool)
    is_probe[probe] = True
    idle_len = turn_len[~is_probe]
    med_idle = float(np.median(idle_len)) if len(idle_len) else float("nan")
    ep = turn_len[probe] - med_idle
    gaps = np.diff([ok_first[j] for j in probe]) if len(probe) > 1 else np.zeros(0)

    # Bramki W1-W4 (README, Kolejnosc, punkt 3)
    clients = load_clients(run_dir / "clients.tsv")
    w1 = bool(meta.get("rt_ok")) and meta.get("trace_overrun") == 0 and meta.get("governor") == "performance"
    rates = [(c["rows1"] - c["rows0"]) / ((c["c1"] - c["c0"]) / 1e9) for c in clients]
    w2 = len(clients) == n and all(c["alive"] for c in clients) and all(r >= W2_MIN * RATE for r in rates)
    w3 = big_unmap == 0 and unlink == 0 and rename == 0 and kills == 0
    if side == "D2s":
        w4 = (all(ok_by[j] == n for j in probe) and sum(fail_by[j] for j in probe) == 0 and ok_by.get(-1, 0) == 0
              and abs(len(probe) - w_s) <= 1 and bool(len(gaps)) and bool(((gaps >= GAP_LO_NS) & (gaps <= GAP_HI_NS)).all()))
    else:
        w4 = sum(ok_by.values()) == 0
    gates = {"W1": w1, "W2": w2, "W3": w3, "W4": w4}

    # Sloty okna pomiaru
    s = A.load_slots(run_dir / "slots.csv")
    sel = (s["deadline"] >= t0) & (s["deadline"] <= t1)
    sw = {k: v[sel] for k, v in s.items()}
    h = D.H[meta["family"]]
    model = D.SlotModel(sw, np.ones(len(sw["deadline"]), dtype=bool), h)
    windows = [(int(ts[j]), int(te[j])) for j in probe]
    ctl = np.ones(len(sw["deadline"]), dtype=bool)
    for w in windows:
        idx, _ = E.affected_idx(model, [w])
        for i in idx:
            ctl[max(0, i - CTL_PAD_SLOTS):i + CTL_PAD_SLOTS + 1] = False
    model = D.SlotModel(sw, ctl, h)
    clusters = [c for c in (E.affected_cluster(model, [w], rngs["placebo"]) for w in windows) if c is not None]

    k3 = {"compute50": pct(sw["compute"][ctl], 50), "wake99": pct(sw["wake"][ctl], 99), "e2e99": pct(sw["e2e"][ctl], 99)}
    p99_idle = pct(idle_len, 99)
    trim = float(idle_len[idle_len <= p99_idle].mean()) if len(idle_len) else float("nan")
    fx_n, fx_max = futex_rt(events, rt)
    return {"dir": run_dir, "meta": meta, "side": side, "n": n, "pair": meta["run"], "w_s": w_s, "t0": t0, "t1": t1,
            "ts": ts, "te": te, "comm_tid": comm_tid, "sleep_other": others, "probe": probe, "ok_by": ok_by,
            "fail_by": fail_by, "orphan_ok": ok_by.get(-1, 0), "gaps": gaps, "idle_len": idle_len, "med_idle": med_idle,
            "trim": trim, "ep": ep, "probe_len": turn_len[probe], "w3": (big_unmap, unlink, rename, kills), "gates": gates,
            "valid": all(gates.values()), "rates": rates, "clients": clients, "model": model, "ctl": ctl,
            "clusters": clusters, "n_windows": len(windows), "k3": k3, "all50": pct(sw["compute"], 50),
            "alle2e99": pct(sw["e2e"], 99), "cpu": cpu_busy(run_dir / "cpu.txt"), "futex": (fx_n, fx_max),
            "vmlck": meta.get("rt_vmlck_kB_connected"), "n_slots": int(len(sw["deadline"])), "n_ctl": int(ctl.sum())}


def h0_clusters(r, lengths, rng):
    """Okna syntetyczne na przebiegu C': po jednym na sekunde okna, od poczatku obrotu najblizszego fazie jednostajnej,
    dlugosc losowana z przebiegow sondy D2s tego samego N; H0_SETS zestawow."""
    out = []
    m, ts = r["model"], r["ts"]
    for _ in range(H0_SETS):
        for k in range(int(r["w_s"])):
            t = r["t0"] + k * 1_000_000_000 + int(rng.integers(0, 1_000_000_000))
            j = int(np.searchsorted(ts, t))
            if j >= len(ts):
                continue
            a = int(ts[j])
            c = E.affected_cluster(m, [(a, a + int(rng.choice(lengths)))], rng)
            if c is not None:
                out.append(c)
    return out


# ---------------------------------------------------------------- raport

def run_dirs(n_dir, side):
    return sorted(p for p in n_dir.iterdir() if p.is_dir() and p.name.startswith(side + "_"))


def regress(P, Q, f, delta_of, label, prefix):
    c = [f(r) for r in P]
    p = [f(r) for r in Q]
    c, p = [x for x in c if not math.isnan(x)], [x for x in p if not math.isnan(x)]
    if not (c and p):
        return f"- **{prefix}**, {label}: brak danych obu stron.", "BRAK DANYCH"
    diff = float(np.median(p) - np.median(c))
    spread = max(max(c) - min(c), max(p) - min(p))
    delta = delta_of(c)
    thr = max(spread, delta)
    pv = A.permutation_mw_two_sided(c, p)
    state = "REGRESJA D2s" if diff > thr else ("D2s lepsze poza progiem" if diff < -thr else "bez regresji")
    line = (f"- **{prefix}**, {label} per przebieg: mediana D2s - C' = {diff / 1e3:.3f} µs, rozrzut wewnątrz strony do "
            f"{spread / 1e3:.3f} µs, δ = {delta / 1e3:.3f} µs, permutacyjny MW p = {pv:.3g} - **{state}**.")
    return line, state


def n_report(n, P, Q, rngs, ctx):
    Pv, Qv = [r for r in P if r["valid"]], [r for r in Q if r["valid"]]
    lines = [f"## N = {n}", "", "| wielkość | C' | D2s |", "|---|---|---|"]

    def row(label, f):
        lines.append(f"| {label} | {f(Pv)} | {f(Qv)} |")

    def cat(rs, key):
        return np.concatenate([r[key] for r in rs]) if rs else np.zeros(0)

    lines.append(f"| przebiegi: ważne / wszystkie | {len(Pv)} / {len(P)} | {len(Qv)} / {len(Q)} |")
    row("przebiegi sondy na przebieg: min / max", lambda x: f"{min(len(r['probe']) for r in x)} / {max(len(r['probe']) for r in x)}" if x else "-")
    row("odstęp przebiegów sondy [ms] min / p50 / max", lambda x: " / ".join(
        f"{v / 1e6:.3f}" for v in (lambda g: (g.min(), np.median(g), g.max()))(cat(x, "gaps"))) if len(cat(x, "gaps")) else "-")
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

    # K3p
    ss = [c for r in Qv for c in r["clusters"]]
    lengths = np.concatenate([r["probe_len"] for r in Qv]) if Qv else np.zeros(0)
    h0 = [c for r in Pv for c in h0_clusters(r, lengths, rngs["h0"])] if len(lengths) else []
    sp = E.mean_boot(E.series_s(ss), rngs["boot"]) if ss else (np.nan,) * 3
    s0 = E.mean_boot(E.series_s(h0), rngs["boot"]) if h0 else (np.nan,) * 3
    (dmed, _), dci, _ = E.aff_boot(ss, rngs["boot"]) if ss else ((np.nan, np.nan), (np.nan, np.nan), None)
    half = (s0[2] - s0[1]) / 2 if h0 else float("nan")
    lines += [f"| K3p: przebiegi sondy z placebo / sloty dotknięte na przebieg | - | {len(ss)} / "
              f"{np.mean([len(c['real']) for c in ss]) if ss else float('nan'):.2f} |",
              f"| K3p: S_p [µs/przebieg] (95 %) | - | {sp[0] / 1e3:+.2f} ({sp[1] / 1e3:+.2f}..{sp[2] / 1e3:+.2f}) |",
              f"| K3p: Δ mediany slotów dotkniętych [µs] (95 %) | - | {dmed / 1e3:+.2f} ({dci[0] / 1e3:+.2f}..{dci[1] / 1e3:+.2f}) |",
              f"| H0 K3p (okna syntetyczne na C'): okna / S_H0 [µs] (95 %) / półszerokość [µs] | {len(h0)} / "
              f"{s0[0] / 1e3:+.2f} ({s0[1] / 1e3:+.2f}..{s0[2] / 1e3:+.2f}) / {half / 1e3:.2f} | - |", ""]

    enough = len(Pv) >= MIN_RUNS and len(Qv) >= MIN_RUNS
    if not enough:
        k3p = "NIEROZSTRZYGNIĘTE (liczność)"
    elif not (half <= H0_HALF_MAX_NS):
        k3p = f"NIEROZSTRZYGNIĘTE (miara: półszerokość H0 {half / 1e3:.2f} µs > {H0_HALF_MAX_NS / 1e3:.1f} µs)"
    elif sp[2] < DELTA_S_NS:
        k3p = "ZDANE"
    elif sp[1] > DELTA_S_NS:
        k3p = "NIEZDANE"
    else:
        k3p = "NIEROZSTRZYGNIĘTE"
    lines.append(f"- **K3p** (δ_S = {DELTA_S_NS / 1e3:.0f} µs): S_p {sp[0] / 1e3:+.2f} ({sp[1] / 1e3:+.2f}..{sp[2] / 1e3:+.2f}) "
                 f"µs, H0 półszerokość {half / 1e3:.2f} µs. Werdykt: **{k3p}**.")

    ep = np.concatenate([r["ep"] for r in Qv]) if Qv else np.zeros(0)
    k4 = None
    if n == K4_N:
        if not enough:
            k4 = "NIEROZSTRZYGNIĘTE (liczność)"
        else:
            k4 = "ZDANE" if pct(ep, 99) <= K4_MAX_NS else "NIEZDANE"
        lines.append(f"- **K4** (N = {K4_N}): p99 E_p = {us(pct(ep, 99))} µs wobec {K4_MAX_NS / 1e3:.0f} µs. Werdykt: **{k4}**.")
    else:
        lines.append(f"- K4 (opisowo przy N = {n}): p99 E_p = {us(pct(ep, 99))} µs.")

    verdicts = {"K3p": k3p, "K4": k4 or "-"}
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
    lines.append("")
    ctx["verdicts"][n] = verdicts
    ctx["ep_med"] += [(n, float(np.median(r["ep"]))) for r in Qv if len(r["ep"])]
    ctx["trim_d"][n] = float(np.median([r["trim"] for r in Qv]) - np.median([r["trim"] for r in Pv])) if Pv and Qv else float("nan")
    return lines


def main_report(raw, seed, out):
    rngs = D.rng_set(seed)
    ctx = {"verdicts": {}, "ep_med": [], "trim_d": {}}
    fam_dir = raw / FAM
    report = ["# R603G - wynik", "", f"Źródło: `{raw.name}`, ziarna: placebo {seed}, bootstrap {seed + 1}, H0 {seed + 2}.", ""]
    n_dirs = sorted((p for p in fam_dir.iterdir() if p.is_dir() and p.name.startswith("N")), key=lambda p: int(p.name[1:]))
    for n_dir in n_dirs:
        n = int(n_dir.name[1:])
        P = [analyze_run(d, rngs) for d in run_dirs(n_dir, "Cp")]
        Q = [analyze_run(d, rngs) for d in run_dirs(n_dir, "D2s")]
        bad = [f"{r['dir'].name} ({', '.join(k for k, v in r['gates'].items() if not v)})" for r in P + Q if not r["valid"]]
        report += n_report(n, P, Q, rngs, ctx)
        report += [f"Przebiegi nieważne: {', '.join(bad) if bad else 'brak'}.", ""]
    report += ["## Koszt sondy na subskrybenta (K4, opisowo)", ""]
    if len({n for n, _ in ctx["ep_med"]}) >= 2:
        x = np.array([n for n, _ in ctx["ep_med"]], dtype=float)
        y = np.array([v for _, v in ctx["ep_med"]])
        slope, icpt = np.polyfit(x, y, 1)
        n1 = (K4_MAX_NS - icpt) / slope if slope > 0 else float("inf")
        report.append(f"Prosta najmniejszych kwadratów median E_p przebiegów D2s względem N: nachylenie {slope / 1e3:.2f} µs "
                      f"na subskrybenta, wyraz wolny {icpt / 1e3:.2f} µs; p50 E_p = 1 ms przy N ≈ {n1:.0f} (ekstrapolacja).")
    report.append("K3t: d (średnia obcięta, mediana D2s - mediana C') według N: " + ", ".join(
        f"N = {n}: {d / 1e3:+.3f} µs" for n, d in sorted(ctx["trim_d"].items())) + ".")
    report += ["", "## Werdykty", "", "| N | K3p | K4 | K3 compute p50 | K3 wake p99 | K3 e2e p99 | K3t |", "|---|---|---|---|---|---|---|"]
    for n, v in sorted(ctx["verdicts"].items()):
        report.append(f"| {n} | {v['K3p']} | {v['K4']} | {v['K3 compute_ns p50']} | {v['K3 wake_lag_ns p99']} | "
                      f"{v['K3 e2e_ns p99']} | {v['K3t']} |")
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
        print(f"{r['dir'].relative_to(raw)}: N={r['n']} {g}; sonda: przebiegi {len(r['probe'])}, openat/przebieg "
              f"{sorted(set(r['ok_by'][j] for j in r['probe']))}, nieudane w przebiegach {sum(r['fail_by'][j] for j in r['probe'])}, "
              f"poza obrotami {r['orphan_ok']}, odstęp [ms] {D.dist(r['gaps']) if len(r['gaps']) else '-'}; "
              f"W3 munmap>=1MiB/unlinkat/renameat/kill {r['w3']}; wiersze/s min {min(r['rates']) if r['rates'] else float('nan'):.1f}; "
              f"zajętość 0-2 {r['cpu']:.3f}; E_p [µs] {D.dist(r['ep'])}; obrót bezczynny p50/p99/p99,9 "
              f"{us(pct(r['idle_len'], 50))} / {us(pct(r['idle_len'], 99))} / {us(pct(r['idle_len'], 99.9))} µs; "
              f"średnia obcięta {r['trim'] / 1e3:.3f} µs; sloty okna/kontrolne {r['n_slots']}/{r['n_ctl']}; "
              f"przebiegi sondy z placebo {len(r['clusters'])}/{r['n_windows']}")
    for n in sorted({r["n"] for r in runs}):
        P = [r for r in runs if r["n"] == n and r["side"] == "Cp"]
        Q = [r for r in runs if r["n"] == n and r["side"] == "D2s"]
        if P and Q:
            lengths = np.concatenate([r["probe_len"] for r in Q])
            h0 = [c for r in P for c in h0_clusters(r, lengths, rngs["h0"])] if len(lengths) else []
            s0 = E.mean_boot(E.series_s(h0), rngs["boot"]) if h0 else (np.nan,) * 3
            ss = [c for r in Q for c in r["clusters"]]
            sp = E.mean_boot(E.series_s(ss), rngs["boot"]) if ss else (np.nan,) * 3
            print(f"N={n}: wstępnie S_p {sp[0] / 1e3:+.2f} ({sp[1] / 1e3:+.2f}..{sp[2] / 1e3:+.2f}) µs z {len(ss)} przebiegów sondy; "
                  f"H0 {len(h0)} okien, S_H0 {s0[0] / 1e3:+.2f}, półszerokość {(s0[2] - s0[1]) / 2e3:.2f} µs")
    ok = all(r["valid"] for r in runs)
    print("BRAMKI W1-W4: " + ("wszystkie spełnione" if ok else "NIESPEŁNIONE"))


EXPECTED_IDLE = {"Cp": "13.0 / 31.0 / 1410.0", "D2s": "14.0 / 34.0 / 1303.0"}  # R603F wynik.md, uc05, obrót bezczynny


def parser_check(raw):
    """(1) funkcje R603F na danych R603F uc05 daja obrot bezczynny jak Wydruk analizy R603F;
    (2) obroty z udanym openat watku komunikacyjnego poza oknami podlaczen: 0 na obu stronach."""
    rngs = D.rng_set(6034)
    fam_dir = raw / FAM
    P, Q = F.load_family(fam_dir, rngs)
    ok = True
    for side, rs in (("Cp", P), ("D2s", Q)):
        got = D.dist(np.concatenate([r["idle_len"] for r in rs]))
        same = got == EXPECTED_IDLE[side]
        ok &= same
        print(f"(1) {NAMES[side]}: obrót bezczynny {got} (R603F: {EXPECTED_IDLE[side]}) - {'zgodne' if same else 'RÓŻNE'}")
    for side in SIDES:
        outside = 0
        for d in F.run_dirs(fam_dir, side):
            events = A.parse_trace(d / "trace.txt")
            rt = A.rt_tids(d / "rt.txt")
            ts, te, comm_tid, _ = D.comm_turns(events, None, rt)
            conns = A.load_conns(d / "conns.tsv")
            turns = set()
            for t, tid, call, kind, val, _ in events:
                if call == "openat" and kind == "exit" and tid == comm_tid and val >= 0:
                    if not any(c["start"] <= t <= c["end"] for c in conns):
                        turns.add(turn_index(ts, te, t))
            outside += len(turns)
        ok &= outside == 0
        print(f"(2) {NAMES[side]}: obroty z udanym openat poza oknami podłączeń: {outside}")
    print("TEST ANALIZY: " + ("ZDANY" if ok else "NIEZDANY"))
    if not ok:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--seed", type=int, default=6034)
    ap.add_argument("--gates", action="store_true", help="bramki W1-W4 per przebieg (suchy przebieg)")
    ap.add_argument("--parser-check", action="store_true", help="--raw wskazuje surowe dane R603F")
    args = ap.parse_args()
    if args.parser_check:
        parser_check(args.raw)
    elif args.gates:
        gates(args.raw)
    else:
        main_report(args.raw, args.seed, args.out)


if __name__ == "__main__":
    main()
