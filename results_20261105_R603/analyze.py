#!/usr/bin/env python3
"""R603: analiza przebiegow run_one.py wedlug kryteriow C0-C4 z README.md (na bazie analizy R600).

Uzycie: analyze.py --raw KATALOG [--out RAPORT.md] [--seed 603]
        analyze.py --raw SUROWE_R600 --parser-check   (nowy parser okna zwolnienia na danych R600)
KATALOG ma uklad <rodzina>/<strona>_<para>/ (slots.csv z kolumnami P1 + P2, trace.txt, conns.tsv, rt.txt, meta.json).
Kod wyjscia: 0 - raport zapisany, 2 - blad danych (przebieg niewazny, brak plikow).
Wymaga NumPy (np. retractordb/.venv-python).
Zmiany wobec R600: strony B i Bp; parser okna zwolnienia przyjmuje ciag munmap w zakresie kolejki (B');
miary PMU z latki P2 (T, L2A, L2R); kryteria C0-C4 zamiast K1-K3; bez okna budowy kolejki i zdarzen podlaczenia.
"""

import argparse
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
PSEUDO_PER_EVENT = 20
PSEUDO_TRIES = 2000
MIN_N = 100
ALPHA = 0.01
CHUNK = 1 << 20
BOOT_N = 2000
PMU = ["l1d_tlb_refill", "l1i_tlb_refill", "l2d_cache", "l2d_cache_refill", "l1d_cache_refill", "inst_retired"]
MEASURES = ["e2e", "T", "L2A", "L2R", "wake_l1i", "wake_l2a", "wake_l2r"]


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
            release = find_release(events, win[4], win[3], win[1])
        out.append((win, release))
    return out


def find_release_r600(events, addr, after):
    """R600 (bez zmian, tylko do --parser-check). Zwolnienie kolejki: munmap jej mapowania i nastepujacy po nim unlinkat w tym samym watku.

    broadcast() porzuca kolejke dopiero po jej zapelnieniu (~10 s po wyjsciu klienta); w A zwalnia ja
    watek slotu, w B (#600) watek komunikacyjny, wiec szukane jest w calym sladzie, w dowolnym watku.
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


def find_release(events, addr, length, after):
    """Zwolnienie kolejki w R603: ciag munmap w zakresie mapowania kolejki i nastepujacy unlinkat tego watku.

    Okno zaczyna wejscie w pierwszy munmap (po `after`), ktorego adres lezy w [addr, addr + length).
    Kolejne wejscia i wyjscia munmap tego watku w tym zakresie naleza do okna (B': kawalki 1 MiB i koncowy
    munmap z queue.reset()); koniec = wyjscie z unlinkat, a bez niego wyjscie z pierwszego munmap
    (jak R600). Kazde inne wejscie konczy szukanie. Na danych R600 (jeden munmap) wynik jest ten sam co
    w find_release_r600 - sprawdza to --parser-check.
    Wynik: (poczatek, koniec, tid, liczba munmap) albo None.
    """
    for i, (t, tid, call, kind, val) in enumerate(events):
        if t > after and call == "munmap" and kind == "enter" and addr <= val.get("addr", -1) < addr + max(length, 1):
            end, first_exit, n = None, None, 1
            for e in events[i + 1:]:
                if e[1] != tid:
                    continue
                if e[2] == "munmap" and e[3] == "exit":
                    if first_exit is None:
                        first_exit = e[0]
                elif e[2] == "munmap" and e[3] == "enter" and addr <= e[4].get("addr", -1) < addr + max(length, 1):
                    n += 1
                elif e[2] == "unlinkat" and e[3] == "exit":
                    end = e[0]
                    break
                elif e[3] == "enter" and e[2] not in ("unlinkat",):
                    break
            end = end if end is not None else first_exit
            return (t, end, tid, n) if end is not None else None
    return None


def load_slots(path):
    data = np.loadtxt(path, delimiter=",", skiprows=1, dtype=np.int64, ndmin=2)
    if data.shape[1] != 17:
        die(f"{path}: oczekiwano 17 kolumn (latki P1 + P2), jest {data.shape[1]}")
    if (data[1:, 5:] == -1).any():
        die(f"{path}: kolumny P2 z wartoscia -1 po pierwszym slocie - przebieg niewazny")
    c = {name: data[:, 5 + i] + data[:, 11 + i] for i, name in enumerate(PMU)}
    return {"compute": data[:, 1], "wake": data[:, 2], "e2e": data[:, 3], "deadline": data[:, 4],
            "T": c["l1d_tlb_refill"] + c["l1i_tlb_refill"], "L2A": c["l2d_cache"], "L2R": c["l2d_cache_refill"],
            "wake_l1i": data[:, 6], "wake_l2a": data[:, 7], "wake_l2r": data[:, 8]}


def pseudo_events(s, control, widths, series, rng):
    """Pseudo-zdarzenia zwolnienia jak w R600 (okna tej dlugosci w calosci w slotach kontrolnych), wszystkie miary."""
    dl, end = s["deadline"], s["deadline"] + s["e2e"]
    out = []
    span_back = int(s["e2e"].max()) if len(dl) else 0
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
            out.append({k: int(s[k][idx].max()) for k in MEASURES})
            got += 1
    return out


def analyze_run(run_dir, rng):
    meta = json.loads((run_dir / "meta.json").read_text())
    if not meta.get("rt_ok") or meta.get("governor") != "performance" or meta.get("pmu_invalid_rows", 1) != 0:
        die(f"{run_dir}: przebieg niewazny (rt_ok={meta.get('rt_ok')}, governor={meta.get('governor')}, "
            f"pmu_invalid_rows={meta.get('pmu_invalid_rows')})")
    if meta["xretractor_sha256"] != meta["build_xretractor_sha256"]:
        die(f"{run_dir}: binarka uruchomiona rozni sie od zbudowanej")
    rows = [l.split("\t") for l in (run_dir / "conns.tsv").read_text().splitlines()[1:]]
    conns = [(int(r[1]), int(r[3])) for r in rows]
    rt = rt_tids(run_dir / "rt.txt")
    wins = windows_for_run(parse_trace(run_dir / "trace.txt"), conns, rt)
    s = load_slots(run_dir / "slots.csv")
    dl, end = s["deadline"], s["deadline"] + s["e2e"]
    releases = []
    for win, rel in wins:
        if rel is None:
            continue
        mask = (dl <= rel[1]) & (end >= rel[0])
        x = {"len_ns": rel[1] - rel[0], "in_rt": rel[2] in rt, "by_builder": rel[2] == win[5], "n_munmap": rel[3],
             "map_len": win[3], "hit": bool(mask.any())}
        if mask.any():
            x.update({k: int(s[k][mask].max()) for k in MEASURES})
            x["woken_wake"] = float(np.median(s["wake"][mask]))
            x["woken_compute"] = float(np.median(s["compute"][mask]))
        releases.append(x)
    control = (dl >= conns[0][0] - SERIES_PAD_NS) & (dl <= conns[-1][1] + SERIES_PAD_NS)
    for c0, c1 in conns:
        control &= ~((dl >= c0 - GUARD_NS) & (dl <= c1 + GUARD_NS))
    for _, rel in wins:
        if rel is not None:
            control &= ~((dl >= rel[0] - GUARD_NS) & (dl <= rel[1] + GUARD_NS))
    series = (conns[0][0] - SERIES_PAD_NS, conns[-1][1] + SERIES_PAD_NS)
    pseudo = pseudo_events(s, control, [x["len_ns"] for x in releases], series, rng)
    return {"meta": meta, "releases": releases, "pseudo": pseudo, "period": int(np.median(np.diff(dl))),
            "no_release": sum(w is not None and r is None for w, r in wins),
            "ctl": {k: s[k][control] for k in ("e2e", "compute", "wake")}}


def pct(a, q):
    return float(np.percentile(a, q, method="inverted_cdf")) if len(a) else float("nan")


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


def fmt_ms(ns):
    return "-" if ns is None or (isinstance(ns, float) and math.isnan(ns)) else f"{ns / 1e6:.3f}"


def delta(ev, ps, k):
    return pct([e[k] for e in ev], 50) - pct([p[k] for p in ps], 50)


def bootstrap_share(ev_b, ps_b, ev_p, ps_p, rng, n=BOOT_N):
    """95 % przedzial u_r = Delta_e2e(B') / Delta_e2e(B): losowanie ze zwracaniem zdarzen i pseudo-zdarzen obu stron."""
    a = [np.asarray([e["e2e"] for e in x], dtype=np.float64) for x in (ev_b, ps_b, ev_p, ps_p)]
    out = []
    for _ in range(n):
        r = [np.median(v[rng.integers(0, len(v), len(v))]) for v in a]
        db = r[0] - r[1]
        if db > 0:
            out.append((r[2] - r[3]) / db)
    if len(out) < n * 0.9:
        return float("nan"), float("nan")
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def family_report(fam, runs, rng_boot):
    lines = [f"## {fam}", ""]
    side = {}
    for sd in ("B", "Bp"):
        rs = [r for r in runs if r["meta"]["side"] == sd]
        rel = [x for r in rs for x in r["releases"]]
        side[sd] = {"runs": rs, "rel": rel, "ev": [x for x in rel if x["hit"]], "ps": [p for r in rs for p in r["pseudo"]],
                    "period": int(np.median([r["period"] for r in rs])) if rs else 0,
                    "ctl": {k: np.concatenate([r["ctl"][k] for r in rs]) for k in ("e2e", "compute", "wake")} if rs else {}}
    B, P = side["B"], side["Bp"]
    period = B["period"]
    lines += [f"Takt slotu (mediana odstępu deadline_ns): {period / 1e6:.3f} ms.", "",
              "| wielkość | B | B' |", "|---|---|---|"]

    def row(label, f):
        lines.append(f"| {label} | {f(B)} | {f(P)} |")

    def dist(a, qs=(50, 99, 100)):
        return " / ".join("-" if (q == 99 and len(a) < MIN_N) else fmt_ms(pct(a, q)) for q in qs)

    row("przebiegi / zwolnienia / w wątku RT / podłączenia bez zwolnienia",
        lambda x: f"{len(x['runs'])} / {len(x['rel'])} / {sum(r['in_rt'] for r in x['rel'])} / "
                  f"{sum(r['no_release'] for r in x['runs'])}")
    row("munmap na zwolnienie: min / p50 / max", lambda x: " / ".join(
        str(int(pct([r["n_munmap"] for r in x["rel"]], q))) for q in (0, 50, 100)) if x["rel"] else "-")
    row("zwolnienie (okno R) [ms] p50 / max",
        lambda x: f"{fmt_ms(pct([r['len_ns'] for r in x['rel']], 50))} / {fmt_ms(pct([r['len_ns'] for r in x['rel']], 100))}")
    row("zwolnienia trafione w slot: n / odsetek",
        lambda x: f"{len(x['ev'])} / {100.0 * len(x['ev']) / len(x['rel']) if x['rel'] else float('nan'):.1f} %")
    row("zdarzenie: max e2e [ms] p50 / p99 / max", lambda x: dist([e["e2e"] for e in x["ev"]]))
    row("pseudo-zdarzenie: liczba / max e2e [ms] p50 / p99 / max",
        lambda x: f"{len(x['ps'])} / {dist([p['e2e'] for p in x['ps']])}")
    row("okna z max e2e > takt: zdarzenia / pseudo", lambda x: (
        f"{100.0 * np.mean([e['e2e'] > period for e in x['ev']]):.1f} % / "
        f"{100.0 * np.mean([p['e2e'] > period for p in x['ps']]):.1f} %") if x["ev"] and x["ps"] else "-")
    for k, label in (("e2e", "Δ_e2e [µs]"), ("T", "Δ_T (l1d+l1i TLB refill)"), ("L2A", "Δ_L2A (l2d_cache)"),
                     ("L2R", "Δ_L2R (l2d_cache_refill)"), ("wake_l1i", "Δ wake_l1i_tlb_refill (opisowo)"),
                     ("wake_l2a", "Δ wake_l2d_cache (opisowo)"), ("wake_l2r", "Δ wake_l2d_cache_refill (opisowo)")):
        scale = 1e3 if k == "e2e" else 1.0
        row(f"{label}; MW p", lambda x, k=k, scale=scale: (
            f"{delta(x['ev'], x['ps'], k) / scale:.2f}; {mann_whitney_greater([e[k] for e in x['ev']], [p[k] for p in x['ps']]):.3g}")
            if x["ev"] and x["ps"] else "-")
    row("sloty obudzone w zwolnieniu: wake_lag / compute p50 [µs] (mediana po zdarzeniach)", lambda x: (
        f"{np.median([e['woken_wake'] for e in x['ev']]) / 1e3:.1f} / {np.median([e['woken_compute'] for e in x['ev']]) / 1e3:.1f}")
        if x["ev"] else "-")
    for k in ("e2e", "compute", "wake"):
        row(f"kontrola {k} [ms] p50 / p99 / max", lambda x, k=k: dist(x["ctl"][k]) if x["ctl"] else "-")
    lines.append("")

    def k2(x):
        return mann_whitney_greater([e["e2e"] for e in x["ev"]], [p["e2e"] for p in x["ps"]])

    pb, pp = k2(B), k2(P)
    c0 = len(B["ev"]) >= MIN_N and pb < ALPHA
    lines.append(f"- **C0** kontrola dodatnia (K2 R600 na B): n = {len(B['ev'])}, p = {pb:.3g} - "
                 f"{'spełniona' if c0 else 'NIESPEŁNIONA (rodzina nierozstrzygnięta)'}.")
    need = [math.ceil(r["map_len"] / CHUNK) for r in P["rel"]]
    c1 = bool(P["rel"]) and all(r["n_munmap"] >= n for r, n in zip(P["rel"], need)) and not any(r["in_rt"] for r in P["rel"])
    lines.append(f"- **C1** B' zwalnia w kawałkach: {sum(r['n_munmap'] >= n for r, n in zip(P['rel'], need))} z "
                 f"{len(P['rel'])} zwolnień ma ≥ ⌈mapowanie / 1 MiB⌉ munmap, w wątku RT {sum(r['in_rt'] for r in P['rel'])} - "
                 f"{'spełnione' if c1 else 'NIESPEŁNIONE (rodzina nieważna)'}.")
    if not (c0 and c1):
        lines += ["- C2-C4: nie rozstrzyga się (C0 albo C1 niespełnione).", ""]
        return lines
    de_b, de_p = delta(B["ev"], B["ps"], "e2e"), delta(P["ev"], P["ps"], "e2e")
    dt_b, dt_p = delta(B["ev"], B["ps"], "T"), delta(P["ev"], P["ps"], "T")
    pt_b = mann_whitney_greater([e["T"] for e in B["ev"]], [p["T"] for p in B["ps"]])
    e_ok = de_p <= 0.5 * de_b
    t_ok = pt_b < ALPHA and dt_b > 0 and dt_p <= 0.5 * dt_b
    c2 = ("WSPARTA" if t_ok else "WSPARTA TYLKO INTERWENCYJNIE") if e_ok else "NIEWSPARTA"
    lines.append(f"- **C2** H-a: Δ_e2e B = {de_b / 1e3:.2f} µs, B' = {de_p / 1e3:.2f} µs (warunek B' ≤ 0,5 · B: "
                 f"{'tak' if e_ok else 'nie'}); Δ_T B = {dt_b:.1f} (MW p = {pt_b:.3g}), B' = {dt_p:.1f} - {c2}.")
    pl2 = mann_whitney_greater([e["L2R"] for e in P["ev"]], [p["L2R"] for p in P["ps"]])
    rest = len(P["ev"]) >= MIN_N and pp < ALPHA
    state = "istnieje" if rest else ("brak" if len(P["ev"]) >= MIN_N else "nierozstrzygnięte (n < 100)")
    if rest and pl2 < ALPHA:
        state += f"; L2R zdarzeń > pseudo w B' (MW p = {pl2:.3g}): zgodna z H-b"
    if de_p > de_b:
        state += "; B' gorszy od B (Δ_e2e(B') > Δ_e2e(B)): wskazanie H-c"
    lines.append(f"- **C3** resztka po B': K2 na B' p = {pp:.3g} (n = {len(P['ev'])}) - {state}.")
    lo, hi = bootstrap_share(B["ev"], B["ps"], P["ev"], P["ps"], rng_boot)
    ur = de_p / de_b if de_b > 0 else float("nan")
    k2p = ("NIEROZSTRZYGNIĘTE (n < 100)" if len(P["ev"]) < MIN_N else ("ZDANE" if pp >= ALPHA else "NIEZDANE"))
    lines.append(f"- **C4** udział: u_a = {1 - ur:.2f}, u_r = {ur:.2f} (95 % bootstrap u_r: {lo:.2f}..{hi:.2f}); "
                 f"K2 R600 dla B': {k2p}.")
    lines.append("")
    return lines


def parser_check(raw):
    """Nowy find_release na danych R600 musi dac okna identyczne z find_release_r600."""
    n, diff = 0, 0
    for run_dir in sorted(p for f in raw.iterdir() if f.is_dir() for p in f.iterdir() if p.is_dir()):
        rows = [l.split("\t") for l in (run_dir / "conns.tsv").read_text().splitlines()[1:]]
        conns = [(int(r[1]), int(r[3])) for r in rows]
        events = parse_trace(run_dir / "trace.txt")
        for win, rel in windows_for_run(events, conns, rt_tids(run_dir / "rt.txt")):
            if win is None:
                continue
            old = find_release_r600(events, win[4], win[1])
            n += 1
            if (old is None) != (rel is None) or (old is not None and tuple(old) != tuple(rel[:3])):
                diff += 1
                print(f"{run_dir}: R600 {old} R603 {rel}")
    print(f"parser-check: {n} okien, {diff} różnic")
    return diff == 0 and n > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--seed", type=int, default=603)
    ap.add_argument("--parser-check", action="store_true", help="--raw wskazuje surowe dane R600")
    args = ap.parse_args()
    if args.parser_check:
        sys.exit(0 if parser_check(args.raw) else 2)
    rng = np.random.default_rng(args.seed)
    rng_boot = np.random.default_rng(args.seed + 1)
    report = ["# R603 - wynik", "",
              f"Źródło: `{args.raw.name}`, ziarno pseudo-zdarzeń {args.seed}, ziarno bootstrapu {args.seed + 1}.", ""]
    for fam_dir in sorted(p for p in args.raw.iterdir() if p.is_dir()):
        runs = [analyze_run(d, rng) for d in sorted(p for p in fam_dir.iterdir() if p.is_dir())]
        if runs:
            report += family_report(fam_dir.name, runs, rng_boot)
    text = "\n".join(report) + "\n"
    if args.out:
        args.out.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
