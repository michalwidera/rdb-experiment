#!/usr/bin/env python3
"""R376: analiza przebiegow run_one.py wedlug kryteriow z README.md.

Uzycie: analyze.py --raw KATALOG [--out RAPORT.md] [--seed 376]
KATALOG ma uklad <rodzina>/<strona>_<para>/ (slots.csv, trace.txt, conns.tsv, rt.txt, meta.json).
Kod wyjscia: 0 - raport zapisany, 2 - blad danych (przebieg niewazny, brak plikow).
Wymaga NumPy (np. retractordb/.venv-python).
"""

import argparse
import itertools
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

EVENT = re.compile(r"^\s*\S+-(\d+)\s+\[\d+\]\s+\S+\s+(\d+)\.(\d+):\s+sys_(\w+)(\(.*\)| -> (0x[0-9a-f]+))\s*$")
ARG = re.compile(r"(\w+): ([0-9a-f]+)")
WINDOW_START_CALLS = ("statfs", "fstatfs", "openat")
MAP_SHARED = 0x1
FD_NONE = {0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF}
GUARD_NS = 500_000_000
SERIES_PAD_NS = 2_000_000_000
BOOTSTRAP = 2000
PSEUDO_PER_EVENT = 20
PSEUDO_TRIES = 2000


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def parse_trace(path):
    """Zdarzenia (t_ns, tid, wywolanie, 'enter'|'exit', argumenty|wartosc)."""
    events = []
    for line in path.read_text().splitlines():
        m = EVENT.match(line)
        if not m:
            continue
        tid, sec, frac, call = int(m[1]), m[2], m[3], m[4]
        t_ns = int(sec) * 1_000_000_000 + int(frac.ljust(9, "0")[:9])
        if m[6] is not None:
            events.append((t_ns, tid, call, "exit", int(m[6], 16)))
        else:
            events.append((t_ns, tid, call, "enter", {k: int(v, 16) for k, v in ARG.findall(m[5])}))
    return events


def rt_tids(path):
    return {int(re.search(r"tid=(\d+)", l)[1]) for l in path.read_text().splitlines() if "policy=SCHED_FIFO" in l}


def windows_for_run(events, conns, rt):
    """Dla kazdego klienta: okno budowy kolejki W i okno zwolnienia (albo None)."""
    out = []
    for start, end in conns:
        inside = [e for e in events if start <= e[0] <= end and e[1] not in rt]
        win, release = None, None
        for i, (t, tid, call, kind, val) in enumerate(inside):
            if call == "mmap" and kind == "enter" and val.get("flags", 0) & MAP_SHARED and val.get("fd") not in FD_NONE:
                exit_ev = next((e for e in inside[i + 1:] if e[1] == tid and e[2] == "mmap" and e[3] == "exit"), None)
                if exit_ev is None:
                    continue
                first = min((e[0] for e in inside[:i] if e[1] == tid and e[3] == "enter" and e[2] in WINDOW_START_CALLS),
                            default=t)
                win = (first, exit_ev[0], exit_ev[0] - t, val.get("len", 0), exit_ev[4], tid)
                break
        if win is not None:
            release = find_release(events, win[4], win[1])
        out.append((win, release))
    return out


def find_release(events, addr, after):
    """Zwolnienie kolejki: munmap jej mapowania i nastepujacy po nim unlinkat w tym samym watku.

    broadcast() kasuje kolejke dopiero po jej zapelnieniu (~10 s po wyjsciu klienta) i robi
    to w watku slotu, wiec szukane jest w calym sladzie, w dowolnym watku.
    Wynik: (poczatek munmap, koniec unlinkat albo munmap, tid) albo None.
    """
    for i, (t, tid, call, kind, val) in enumerate(events):
        if t > after and call == "munmap" and kind == "enter" and val.get("addr") == addr:
            end = None
            for e in events[i + 1:]:
                if e[1] != tid:
                    continue
                if e[2] == "munmap" and e[3] == "exit" and end is None:
                    end = e[0]
                elif e[2] == "unlinkat" and e[3] == "exit":
                    end = e[0]
                    break
                elif e[3] == "enter" and e[2] not in ("unlinkat",):
                    break
            return (t, end, tid) if end is not None else None
    return None


def load_slots(path):
    data = np.loadtxt(path, delimiter=",", skiprows=1, dtype=np.int64, ndmin=2)
    if data.shape[1] != 5:
        die(f"{path}: oczekiwano 5 kolumn (latka P1), jest {data.shape[1]}")
    return {"compute": data[:, 1], "wake": data[:, 2], "e2e": data[:, 3], "deadline": data[:, 4]}


def analyze_run(run_dir, rng):
    meta = json.loads((run_dir / "meta.json").read_text())
    if not meta.get("rt_ok") or meta.get("governor") != "performance":
        die(f"{run_dir}: przebieg niewazny (rt_ok={meta.get('rt_ok')}, governor={meta.get('governor')})")
    if meta["xretractor_sha256"] != meta["build_xretractor_sha256"]:
        die(f"{run_dir}: binarka uruchomiona rozni sie od zbudowanej")
    rows = [l.split("\t") for l in (run_dir / "conns.tsv").read_text().splitlines()[1:]]
    conns = [(int(r[1]), int(r[3])) for r in rows]
    # Klient po pierwszym wierszu konczy sie sam (0) albo przez SIGINT (-2); zly jest tylko brak wiersza
    # albo zabicie po 5 s (run_one.py, client()). Ponizej ~1 kHz xqry zwykle zdazy skonczyc sie sam.
    bad_rc = [r for r in rows if r[4].startswith(("no_row", "killed"))]
    rt = rt_tids(run_dir / "rt.txt")
    wins = windows_for_run(parse_trace(run_dir / "trace.txt"), conns, rt)
    s = load_slots(run_dir / "slots.csv")
    dl, end = s["deadline"], s["deadline"] + s["e2e"]

    rel_slots = np.zeros(len(dl), dtype=bool)
    for _, rel in wins:
        if rel is not None:
            rel_slots |= (dl <= rel[1]) & (end >= rel[0])
    events, hit_slots = [], np.zeros(len(dl), dtype=bool)
    for win, _ in wins:
        if win is None:
            continue
        w0, w1 = win[0], win[1]
        mask = (dl <= w1) & (end >= w0)
        hit_slots |= mask
        events.append({"w_ns": w1 - w0, "mmap_ns": win[2], "len": win[3],
                       "max_e2e": int(s["e2e"][mask].max()) if mask.any() else None, "n_slots": int(mask.sum()),
                       "on_release": bool((mask & rel_slots).any())})
    releases = []
    for _, rel in wins:
        if rel is None:
            continue
        mask = (dl <= rel[1]) & (end >= rel[0])
        releases.append({"len_ns": rel[1] - rel[0], "in_rt": rel[2] in rt,
                         "max_e2e": int(s["e2e"][mask].max()) if mask.any() else None})
    control = (dl >= conns[0][0] - SERIES_PAD_NS) & (dl <= conns[-1][1] + SERIES_PAD_NS)
    for c0, c1 in conns:
        control &= ~((dl >= c0 - GUARD_NS) & (dl <= c1 + GUARD_NS))
    for _, rel in wins:
        if rel is not None:
            control &= ~((dl >= rel[0] - GUARD_NS) & (dl <= rel[1] + GUARD_NS))
    pseudo = pseudo_events(dl, end, s["e2e"], control, [e["w_ns"] for e in events],
                           (conns[0][0] - SERIES_PAD_NS, conns[-1][1] + SERIES_PAD_NS), rng)
    return {"meta": meta, "events": events, "unassigned": sum(w is None for w, _ in wins), "bad_rc": len(bad_rc),
            "hit_e2e": s["e2e"][hit_slots], "ctl": {k: s[k][control] for k in ("e2e", "compute", "wake")},
            "pseudo": pseudo, "releases": releases, "slots": len(dl)}


def pseudo_events(dl, end, e2e, control, widths, series, rng):
    """Kontrola dla metryki zdarzeniowej: max e2e w oknach o dlugosci okien W polozonych losowo.

    Maksimum z kilku slotow okna jest z konstrukcji wieksze od pojedynczego slotu, wiec zdarzenie
    porownuje sie z tym samym maksimum wzietym tam, gdzie podlaczenia nie bylo: PSEUDO_PER_EVENT
    okien na zdarzenie, kazde w calosci w slotach kontrolnych i z co najmniej jednym slotem.
    """
    out = []
    span_back = int(e2e.max()) if len(e2e) else 0
    for w in widths:
        got = 0
        for _ in range(PSEUDO_TRIES):
            if got == PSEUDO_PER_EVENT:
                break
            t = int(rng.integers(series[0], max(series[0] + 1, series[1] - w)))
            lo = int(np.searchsorted(dl, t - span_back, side="left"))
            hi = int(np.searchsorted(dl, t + w, side="right"))
            idx = np.arange(lo, hi)
            idx = idx[end[idx] >= t]
            if len(idx) == 0 or not control[idx].all():
                continue
            out.append(int(e2e[idx].max()))
            got += 1
    return out


def pct(a, q):
    return float(np.percentile(a, q, method="inverted_cdf")) if len(a) else float("nan")


def boot_p99(a, rng):
    idx = rng.integers(0, len(a), size=(BOOTSTRAP, len(a)))
    reps = np.percentile(np.asarray(a)[idx], 99, axis=1, method="inverted_cdf")
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return float(lo), float(hi)


def mann_whitney_greater(x, y):
    """Jednostronny test Manna-Whitneya H1: x > y, przyblizenie normalne z poprawka na wiazania."""
    x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return float("nan")
    allv = np.concatenate([x, y])
    order = allv.argsort(kind="mergesort")
    ranks = np.empty(len(allv))
    sv = allv[order]
    _, first, counts = np.unique(sv, return_index=True, return_counts=True)
    avg = first + (counts + 1) / 2.0
    ranks[order] = np.repeat(avg, counts)
    u = ranks[:n1].sum() - n1 * (n1 + 1) / 2.0
    n = n1 + n2
    tie = (counts**3 - counts).sum()
    sigma = math.sqrt(n1 * n2 / 12.0 * ((n + 1) - tie / (n * (n - 1))))
    if sigma == 0:
        return 1.0
    z = (u - n1 * n2 / 2.0 - 0.5) / sigma
    return 0.5 * math.erfc(z / math.sqrt(2))


def permutation_mw_two_sided(x, y):
    """Dokladny dwustronny test permutacyjny statystyki U dla malych prob (9 vs 9)."""
    allv = list(x) + list(y)
    n1 = len(x)

    def u(sel):
        a = [allv[i] for i in sel]
        b = [allv[i] for i in range(len(allv)) if i not in sel]
        return sum((p > q) + 0.5 * (p == q) for p in a for q in b)

    centre = n1 * (len(allv) - n1) / 2.0
    obs = abs(u(set(range(n1))) - centre)
    combos = list(itertools.combinations(range(len(allv)), n1))
    extreme = sum(abs(u(set(c)) - centre) >= obs - 1e-9 for c in combos)
    return extreme / len(combos)


def fmt_ms(ns):
    return "-" if ns is None or (isinstance(ns, float) and math.isnan(ns)) else f"{ns / 1e6:.3f}"


def family_report(fam, runs, rng):
    lines = [f"## {fam}", ""]
    side = {}
    for sd in ("A", "B"):
        rs = [r for r in runs if r["meta"]["side"] == sd]
        ev = [e for r in rs for e in r["events"]]
        hit = [e["max_e2e"] for e in ev if e["max_e2e"] is not None]
        side[sd] = {
            "runs": rs, "events": ev, "hit": hit,
            "hit_slots": np.concatenate([r["hit_e2e"] for r in rs]) if rs else np.array([]),
            "ctl": {k: np.concatenate([r["ctl"][k] for r in rs]) for k in ("e2e", "compute", "wake")},
            "per_run_compute_p50": [pct(r["ctl"]["compute"], 50) for r in rs],
            "per_run_wake_p99": [pct(r["ctl"]["wake"], 99) for r in rs],
            "pseudo": [x for r in rs for x in r["pseudo"]],
        }
    lines += ["| wielkość [ms] | A | B |", "|---|---|---|"]

    def row(label, fa, fb):
        lines.append(f"| {label} | {fa} | {fb} |")

    row("przebiegi / podłączenia / bez przypisania / klient bez wiersza lub zabity",
        *(f"{len(side[s]['runs'])} / {len(side[s]['events']) + sum(r['unassigned'] for r in side[s]['runs'])} / "
          f"{sum(r['unassigned'] for r in side[s]['runs'])} / {sum(r['bad_rc'] for r in side[s]['runs'])}" for s in "AB"))
    row("okno W p50 / max", *(f"{fmt_ms(pct([e['w_ns'] for e in side[s]['events']], 50))} / "
                              f"{fmt_ms(pct([e['w_ns'] for e in side[s]['events']], 100))}" for s in "AB"))
    row("mmap kolejki p50 / max", *(f"{fmt_ms(pct([e['mmap_ns'] for e in side[s]['events']], 50))} / "
                                    f"{fmt_ms(pct([e['mmap_ns'] for e in side[s]['events']], 100))}" for s in "AB"))
    rel = {s: [x for r in side[s]["runs"] for x in r["releases"]] for s in "AB"}
    row("zwolnienie kolejki: liczba / w wątku RT", *(f"{len(rel[s])} / {sum(x['in_rt'] for x in rel[s])}" for s in "AB"))
    row("zwolnienie kolejki (munmap+unlinkat) p50 / max",
        *(f"{fmt_ms(pct([x['len_ns'] for x in rel[s]], 50))} / {fmt_ms(pct([x['len_ns'] for x in rel[s]], 100))}"
          for s in "AB"))
    row("zwolnienie: max e2e slotu p50 / p99 / max",
        *(f"{fmt_ms(pct([x['max_e2e'] for x in rel[s] if x['max_e2e'] is not None], 50))} / "
          f"{fmt_ms(pct([x['max_e2e'] for x in rel[s] if x['max_e2e'] is not None], 99))} / "
          f"{fmt_ms(pct([x['max_e2e'] for x in rel[s] if x['max_e2e'] is not None], 100))}" for s in "AB"))
    verdict = {}
    for s in "AB":
        h = side[s]["hit"]
        if len(h) >= 100:
            lo, hi = boot_p99(h, rng)
            p99 = pct(h, 99)
            stable = (hi - lo) / 2 <= 0.10 * p99
            verdict[s] = (p99, stable)
            side[s]["p99txt"] = f"{fmt_ms(p99)} [{fmt_ms(lo)}, {fmt_ms(hi)}] {'stabilne' if stable else 'NIESTABILNE'}"
        else:
            side[s]["p99txt"] = f"n_hit < 100"
    row("zdarzenie: n_hit", *(str(len(side[s]["hit"])) for s in "AB"))
    row("zdarzenie: p50 / max e2e", *(f"{fmt_ms(pct(side[s]['hit'], 50))} / {fmt_ms(pct(side[s]['hit'], 100))}"
                                      for s in "AB"))
    row("zdarzenie: p99 e2e [CI 95 %]", side["A"]["p99txt"], side["B"]["p99txt"])
    row("pseudo-zdarzenie (kontrola): liczba / p50 / p99 / max",
        *(f"{len(side[s]['pseudo'])} / {fmt_ms(pct(side[s]['pseudo'], 50))} / {fmt_ms(pct(side[s]['pseudo'], 99))} / "
          f"{fmt_ms(pct(side[s]['pseudo'], 100))}" for s in "AB"))
    row("slot z podłączeniem: liczba / p99 / max",
        *(f"{len(side[s]['hit_slots'])} / {fmt_ms(pct(side[s]['hit_slots'], 99))} / "
          f"{fmt_ms(pct(side[s]['hit_slots'], 100))}" for s in "AB"))
    for k, label in (("e2e", "kontrola e2e"), ("compute", "kontrola compute"), ("wake", "kontrola wake_lag")):
        row(f"{label}: p50 / p99 / max",
            *(f"{fmt_ms(pct(side[s]['ctl'][k], 50))} / {fmt_ms(pct(side[s]['ctl'][k], 99))} / "
              f"{fmt_ms(pct(side[s]['ctl'][k], 100))}" for s in "AB"))
    lines.append("")

    p_ab = mann_whitney_greater(side["A"]["hit"], side["B"]["hit"])
    p_bctl = mann_whitney_greater(side["B"]["hit"], side["B"]["pseudo"])
    p_actl = mann_whitney_greater(side["A"]["hit"], side["A"]["pseudo"])
    confirmed = (len(verdict) == 2 and all(v[1] for v in verdict.values()) and verdict["B"][0] < verdict["A"][0]
                 and p_ab < 0.01)
    lines.append(f"- Mann-Whitney zdarzenia A > B: p = {p_ab:.3g}; zdarzenia A > pseudo-zdarzenia A: p = {p_actl:.3g}; "
                 f"zdarzenia B > pseudo-zdarzenia B (ryzyko szczątkowe): p = {p_bctl:.3g}.")
    lines.append(f"- Efekt #283 wg kryterium README: {'POTWIERDZONY' if confirmed else 'NIEPOTWIERDZONY'}"
                 f"{'' if len(verdict) == 2 else ' (p99 nieraportowane przy n_hit < 100)'}.")

    if side["B"]["hit"] and side["B"]["pseudo"]:
        excess = pct(side["B"]["hit"], 50) - pct(side["B"]["pseudo"], 50)
        lines.append(f"- Ryzyko szczątkowe, wielkość: mediana zdarzeń B - mediana pseudo-zdarzeń B = {fmt_ms(excess)} ms.")
    # Eksploracja po pomiarze, poza kryteriami: zdarzenia, ktorych sloty nie trafiaja na okno zwolnienia kolejki.
    clean = {s: [e["max_e2e"] for e in side[s]["events"] if e["max_e2e"] is not None and not e["on_release"]] for s in "AB"}
    parts = []
    for s in "AB":
        txt = f"{s}: n = {len(clean[s])} (odrzucone {len(side[s]['hit']) - len(clean[s])}), p50 / max {fmt_ms(pct(clean[s], 50))} / {fmt_ms(pct(clean[s], 100))}"
        if len(clean[s]) >= 100:
            # Osobny generator: eksploracja nie przesuwa losowan kryteriow w kolejnych rodzinach.
            lo, hi = boot_p99(clean[s], np.random.default_rng(376))
            p99 = pct(clean[s], 99)
            txt += f", p99 {fmt_ms(p99)} [{fmt_ms(lo)}, {fmt_ms(hi)}] {'stabilne' if (hi - lo) / 2 <= 0.10 * p99 else 'NIESTABILNE'}"
        parts.append(txt)
    lines.append(f"- Eksploracja po pomiarze (poza kryteriami), zdarzenia bez slotu w oknie zwolnienia: {'; '.join(parts)}; "
                 f"MW A > B p = {mann_whitney_greater(clean['A'], clean['B']):.3g}, "
                 f"B > pseudo B p = {mann_whitney_greater(clean['B'], side['B']['pseudo']):.3g}.")

    for key, label in (("per_run_compute_p50", "compute_ns p50"), ("per_run_wake_p99", "wake_lag_ns p99")):
        a = [x for x in side["A"][key] if not math.isnan(x)]
        b = [x for x in side["B"][key] if not math.isnan(x)]
        if not (a and b):
            lines.append(f"- Kontrola aparatury, {label} per przebieg: brak slotów kontrolnych - nie do oceny.")
        else:
            diff = float(np.median(a) - np.median(b))
            spread = max(max(a) - min(a), max(b) - min(b))
            p = permutation_mw_two_sided(a, b)
            ok = abs(diff) <= spread
            lines.append(f"- Kontrola aparatury, {label} per przebieg: mediana A-B = {diff / 1e3:.2f} µs, rozrzut "
                         f"wewnątrz strony do {spread / 1e3:.2f} µs, permutacyjny MW p = {p:.3g} - "
                         f"{'w szumie' if ok else 'POZA SZUMEM, wniosek wstrzymany'}.")
    lines.append("")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--seed", type=int, default=376)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    report = ["# R376 - wynik", "", f"Źródło: `{args.raw.name}`, bootstrap {BOOTSTRAP} losowań, ziarno {args.seed}.", ""]
    for fam_dir in sorted(p for p in args.raw.iterdir() if p.is_dir()):
        runs = [analyze_run(d, rng) for d in sorted(p for p in fam_dir.iterdir() if p.is_dir())]
        if runs:
            report += family_report(fam_dir.name, runs, rng)
    text = "\n".join(report) + "\n"
    if args.out:
        args.out.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
