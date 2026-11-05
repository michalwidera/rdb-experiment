#!/usr/bin/env python3
"""R603C: analiza przebiegow run_one.py wedlug kryteriow K1', K2, K3 i obserwacji O1-O3 z README.md.

Uzycie: analyze.py --raw KATALOG [--out RAPORT.md] [--seed 6031]
        analyze.py --raw SUROWE_R600 --parser-check   (strona B R600: okna R_B i werdykt K2 jak w R600)
KATALOG ma uklad <rodzina>/<strona>_<para>/ (slots.csv z kolumna P1, trace.txt, conns.tsv, rt.txt, meta.json).
Kod wyjscia: 0 - raport zapisany, 2 - blad danych (przebieg niewazny, brak plikow).
Wymaga NumPy (np. retractordb/.venv-python).

Okna (README R603C, *Okna i zdarzenia*):
- R_B: od wejscia w munmap mapowania kolejki do wyjscia z nastepnego unlinkat tego watku (parser R603).
- R_C: od wyjscia z kill(pid_klienta, 0) w watku komunikacyjnym do wyjscia z nastepnego renameat tego watku;
  para munmap + unlinkat w srodku = okno przepelnienia puli (poza K2).
- Oddanie z puli: renameat poza oknami R_C, w czasie podlaczenia klienta, bez mmap nowej kolejki.
"""

import argparse
import itertools
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

EVENT = re.compile(r"^\s*\S+-(\d+)\s+\[(\d+)\]\s+\S+\s+(\d+)\.(\d+):\s+sys_(\w+)(\(.*\)| -> (0x[0-9a-f]+))\s*$")
ARG = re.compile(r"(\w+): ([0-9a-f]+)")
WINDOW_START_CALLS = ("statfs", "fstatfs", "openat")
RENAME = ("renameat", "renameat2")
MAP_SHARED = 0x1
FD_NONE = {0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF}
ESRCH = 3
GUARD_NS = 500_000_000
SERIES_PAD_NS = 2_000_000_000
PSEUDO_PER_EVENT = 20
PSEUDO_TRIES = 2000
MIN_N = 100
ALPHA = 0.01
BOOT_N = 2000
POOL = 2  # kResponseQueuePoolSegments w C
EARLY_ABANDON_NS = 9_500_000_000  # porzucenie wczesniej = martwy muteks po SIGINT (README, Ustalenia, punkt 3)
EXCLUDED_MAX = 0.05
# Poprawka po kampanii (wynik.md, Odstepstwa): w przepelnieniu renameat idzie zaraz po unlinkat (kod uzytkownika,
# w kampanii max 314 us). Pozniejszy renameat to oddanie z puli dla nastepnego klienta, nie koniec tego okna.
RENAME_AFTER_UNLINK_MAX_NS = 10_000_000
FUTEX_OPS = {0: "WAIT", 1: "WAKE", 6: "LOCK_PI", 7: "UNLOCK_PI", 9: "WAIT_BITSET", 10: "WAKE_BITSET"}


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def signed(v):
    return v - (1 << 64) if v >= 1 << 63 else v


def parse_trace(path):
    """Zdarzenia (t_ns, tid, wywolanie, 'enter'|'exit', argumenty|wartosc ze znakiem, cpu)."""
    events = []
    for line in path.read_text().splitlines():
        m = EVENT.match(line)
        if not m:
            continue
        tid, cpu, sec, frac, call = int(m[1]), int(m[2]), m[3], m[4], m[5]
        t_ns = int(sec) * 1_000_000_000 + int(frac.ljust(9, "0")[:9])
        if m[7] is not None:
            events.append((t_ns, tid, call, "exit", signed(int(m[7], 16)), cpu))
        else:
            events.append((t_ns, tid, call, "enter", {k: int(v, 16) for k, v in ARG.findall(m[6])}, cpu))
    return events


def rt_tids(path):
    return {int(re.search(r"tid=(\d+)", l)[1]) for l in path.read_text().splitlines() if "policy=SCHED_FIFO" in l}


def load_conns(path):
    rows = [l.split("\t") for l in path.read_text().splitlines()[1:]]
    out = []
    for r in rows:
        out.append({"start": int(r[1]), "first": int(r[2]) if r[2] != "-" else None, "end": int(r[3]), "rc": r[4],
                    "pid": int(r[5]) if len(r) > 5 else None, "reaped": int(r[6]) if len(r) > 6 else None})
    return out


def queue_mappings(events, conns, rt):
    """Okno budowy W i mapowanie kolejki utworzonej w czasie podlaczenia (jak R600); None = bez mmap kolejki."""
    out = []
    for c in conns:
        inside = [e for e in events if c["start"] <= e[0] <= c["end"] and e[1] not in rt]
        win = None
        for i, (t, tid, call, kind, val, _) in enumerate(inside):
            if call == "mmap" and kind == "enter" and val.get("flags", 0) & MAP_SHARED and val.get("fd") not in FD_NONE:
                exit_ev = next((e for e in inside[i + 1:] if e[1] == tid and e[2] == "mmap" and e[3] == "exit"), None)
                if exit_ev is None:
                    continue
                first = min((e[0] for e in inside[:i] if e[1] == tid and e[3] == "enter" and e[2] in WINDOW_START_CALLS),
                            default=t)
                win = {"w0": first, "w1": exit_ev[0], "mmap_ns": exit_ev[0] - t, "len": val.get("len", 0),
                       "addr": exit_ev[4], "tid": tid, "t_map": exit_ev[0]}
                break
        out.append(win)
    return out


def find_release_r600(events, addr, after):
    """R600 bez zmian (tylko --parser-check): munmap adresu mapowania i nastepny unlinkat tego watku."""
    for i, (t, tid, call, kind, val, _) in enumerate(events):
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
    """Parser R603 bez zmian: ciag munmap w [addr, addr + length) i nastepny unlinkat tego watku.

    Wynik: (poczatek, koniec, tid, liczba munmap) albo None.
    """
    for i, (t, tid, call, kind, val, _) in enumerate(events):
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


def queue_pairs(events, maps):
    """Wszystkie pary munmap + unlinkat na mapowaniach kolejek odpowiedzi, w dowolnym watku, z czasem waznosci mapowania.

    Mapowanie jest wazne od wyjscia z jego mmap do pierwszego munmap w jego zakresie. Wynik: lista
    (poczatek munmap, koniec unlinkat, tid, indeks mapowania) i czas munmap kazdego mapowania (albo None).
    """
    live = [m for m in maps if m is not None]
    unmapped = [None] * len(live)
    pairs = []
    for i, (t, tid, call, kind, val, _) in enumerate(events):
        if call != "munmap" or kind != "enter":
            continue
        a = val.get("addr", -1)
        j = next((k for k, m in enumerate(live) if unmapped[k] is None and m["t_map"] < t
                  and m["addr"] <= a < m["addr"] + max(m["len"], 1)), None)
        if j is None:
            continue
        unmapped[j] = t
        end = None
        for e in events[i + 1:]:
            if e[1] != tid:
                continue
            if e[2] == "unlinkat" and e[3] == "exit":
                end = e[0]
                break
            if e[3] == "enter" and e[2] not in ("munmap", "unlinkat"):
                break
        if end is not None:
            pairs.append((t, end, tid, j))
    return pairs, live, unmapped


def kill_windows(events, conns, rt):
    """Okna R_C: kill(pid_klienta, 0) w watku spoza RT, potem do wyjscia z renameat tego watku.

    Wynik dla kazdego podlaczenia: None (brak kill z jego pid) albo slownik z polami
    t_kill, t0 (wyjscie z kill), kill_ret, t1 (wyjscie z udanego renameat albo None), overflow (para munmap +
    unlinkat przed renameat), erased (para munmap + unlinkat bez udanego renameat), tid, rename_idx.
    """
    by_pid = {}
    for i, e in enumerate(events):
        if e[2] == "kill" and e[3] == "enter" and e[1] not in rt and e[4].get("sig", -1) == 0:
            by_pid.setdefault(e[4].get("pid"), []).append(i)
    out = []
    for c in conns:
        idx = next((i for i in by_pid.get(c["pid"], []) if events[i][0] > c["start"]), None)
        if idx is None:
            out.append(None)
            continue
        t_kill, tid = events[idx][0], events[idx][1]
        w = {"t_kill": t_kill, "t0": None, "kill_ret": None, "t1": None, "overflow": False, "erased": False, "tid": tid,
             "rename_idx": None, "munmap": 0, "unlink": 0, "t_munmap": None, "t_unlink": None}
        for j in range(idx + 1, len(events)):
            e = events[j]
            if e[1] != tid:
                continue
            if e[2] == "kill" and e[3] == "exit" and w["t0"] is None:
                w["t0"], w["kill_ret"] = e[0], e[4]
            elif e[2] == "munmap" and e[3] == "enter":
                w["munmap"] += 1
                if w["t_munmap"] is None:
                    w["t_munmap"] = e[0]
            elif e[2] == "unlinkat" and e[3] == "exit":
                w["unlink"] += 1
                w["t_unlink"] = e[0]
            elif (e[2] in RENAME and e[3] == "enter" and w["t_unlink"] is not None
                  and e[0] - w["t_unlink"] > RENAME_AFTER_UNLINK_MAX_NS):
                break  # skasowanie: kolejny renameat nalezy do oddania z puli
            elif e[2] in RENAME and e[3] == "exit":
                if e[4] == 0:
                    w["t1"], w["rename_idx"] = e[0], j
                    break
            elif e[3] == "enter" and e[2] in ("kill", "openat", "mmap", "statfs", "fstatfs"):
                break  # nastepne zwolnienie albo budowa kolejki: okno bez udanego renameat
        pair = w["munmap"] > 0 and w["unlink"] > 0
        w["overflow"] = pair and w["t1"] is not None
        w["erased"] = pair and w["t1"] is None
        out.append(w)
    return out


def load_slots(path):
    data = np.loadtxt(path, delimiter=",", skiprows=1, dtype=np.int64, ndmin=2)
    if data.shape[1] != 5:
        die(f"{path}: oczekiwano 5 kolumn (latka P1), jest {data.shape[1]}")
    return {"compute": data[:, 1], "wake": data[:, 2], "e2e": data[:, 3], "deadline": data[:, 4]}


def pseudo_events(dl, end, e2e, control, widths, series, rng):
    """Pseudo-zdarzenia jak w R600: okna tej samej dlugosci w calosci w slotach kontrolnych, max e2e."""
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


def futex_obs(events, rt, live, unmapped, windows, dl, end, e2e, period):
    """O1: wywolania futex watku RT; na adresie zywego mapowania kolejki albo poza nim."""
    out = {"queue": {}, "other": 0, "enters": 0, "wait_ns": [], "wait_in_window": 0, "wait_over_period": 0,
           "slots_with_futex": 0}
    slot_hit = np.zeros(len(dl), dtype=bool)
    pending = {}
    for i, (t, tid, call, kind, val, _) in enumerate(events):
        if call != "futex" or tid not in rt:
            continue
        if kind == "enter":
            out["enters"] += 1
            k = int(np.searchsorted(dl, t, side="right")) - 1
            if 0 <= k < len(dl) and end[k] >= t:
                slot_hit[k] = True
            ua, op = val.get("uaddr", -1), val.get("op", -1) & 0x7F
            q = any(m["t_map"] <= t and (unmapped[j] is None or t < unmapped[j]) and m["addr"] <= ua < m["addr"] + m["len"]
                    for j, m in enumerate(live))
            if q:
                name = FUTEX_OPS.get(op, str(op))
                out["queue"][name] = out["queue"].get(name, 0) + 1
                if op in (0, 9, 6):
                    pending[tid] = (t, k)
            else:
                out["other"] += 1
        elif tid in pending:
            t0, k = pending.pop(tid)
            out["wait_ns"].append(t - t0)
            if any(w0 <= t0 <= w1 for w0, w1 in windows):
                out["wait_in_window"] += 1
            if 0 <= k < len(dl) and e2e[k] > period:
                out["wait_over_period"] += 1
    out["slots_with_futex"] = int(slot_hit.sum())
    return out


def analyze_run(run_dir, rng):
    meta = json.loads((run_dir / "meta.json").read_text())
    if not meta.get("rt_ok") or meta.get("governor") != "performance":
        die(f"{run_dir}: przebieg niewazny (rt_ok={meta.get('rt_ok')}, governor={meta.get('governor')})")
    if meta["xretractor_sha256"] != meta["build_xretractor_sha256"]:
        die(f"{run_dir}: binarka uruchomiona rozni sie od zbudowanej")
    if meta.get("trace_overrun", 0) != 0:
        die(f"{run_dir}: przepelnienie bufora ftrace ({meta['trace_overrun']} zdarzen) - przebieg niewazny")
    side = meta["side"]
    conns = load_conns(run_dir / "conns.tsv")
    rt = rt_tids(run_dir / "rt.txt")
    events = parse_trace(run_dir / "trace.txt")
    s = load_slots(run_dir / "slots.csv")
    dl, end = s["deadline"], s["deadline"] + s["e2e"]
    period = int(np.median(np.diff(dl)))
    maps = queue_mappings(events, conns, rt)
    pairs, live, unmapped = queue_pairs(events, maps)
    kills = kill_windows(events, conns, rt) if conns[0]["pid"] is not None else [None] * len(conns)

    # Okna K2 i okna do wykluczenia ze slotow kontrolnych.
    windows, excl = [], []
    if side == "B":
        for m in maps:
            if m is None:
                continue
            rel = find_release(events, m["addr"], m["len"], m["w1"])
            if rel is not None:
                windows.append({"t0": rel[0], "t1": rel[1], "in_rt": rel[2] in rt, "by_builder": rel[2] == m["tid"]})
    else:
        for w in kills:
            if w is not None and w["t0"] is not None and w["t1"] is not None and not w["overflow"]:
                windows.append({"t0": w["t0"], "t1": w["t1"], "in_rt": w["tid"] in rt, "by_builder": True})
    for w in kills:
        if w is not None:
            excl.append((w["t_kill"], w["t1"] if w["t1"] is not None else (w["t0"] or w["t_kill"])))
    excl += [(p[0], p[1]) for p in pairs]
    excl += [(w["t0"], w["t1"]) for w in windows]

    for w in windows:
        mask = (dl <= w["t1"]) & (end >= w["t0"])
        w["len_ns"] = w["t1"] - w["t0"]
        w["hit"] = bool(mask.any())
        if mask.any():
            w["e2e"] = int(s["e2e"][mask].max())
            w["woken_wake"] = float(np.median(s["wake"][mask]))
            w["woken_compute"] = float(np.median(s["compute"][mask]))

    control = (dl >= conns[0]["start"] - SERIES_PAD_NS) & (dl <= conns[-1]["end"] + SERIES_PAD_NS)
    for c in conns:
        control &= ~((dl >= c["start"] - GUARD_NS) & (dl <= c["end"] + GUARD_NS))
    for a, b in excl:
        control &= ~((dl >= a - GUARD_NS) & (dl <= b + GUARD_NS))
    series = (conns[0]["start"] - SERIES_PAD_NS, conns[-1]["end"] + SERIES_PAD_NS)
    pseudo = pseudo_events(dl, end, s["e2e"], control, [w["len_ns"] for w in windows], series, rng)

    # K1': klasyfikacja porzucen i par.
    first_rc = min((w["t0"] for w in kills if w is not None and w["t1"] is not None and w["t0"] is not None),
                   default=None)
    last_start = conns[-1]["start"]
    in_overflow = [any(w is not None and w["overflow"] and w["t_kill"] <= p[0] <= w["t1"] for w in kills) for p in pairs]
    pool_in = sum(1 for w in kills if w is not None and w["kill_ret"] == -ESRCH and w["t1"] is not None)
    dead_mutex = [c for c, w in zip(conns, kills) if w is not None and w["erased"] and w["kill_ret"] == -ESRCH
                  and c["first"] is not None and w["t_kill"] - c["first"] < EARLY_ABANDON_NS]
    not_reaped = [c for c, w in zip(conns, kills) if w is None and c["reaped"] == 0]
    no_kill_reaped = [c for c, w in zip(conns, kills) if w is None and c["reaped"] != 0]
    erased_other = [w for c, w in zip(conns, kills) if w is not None and w["erased"] and c not in dead_mutex]
    pairs_working = [p for p in pairs if first_rc is not None and first_rc <= p[0] <= last_start]
    pairs_before = [p for p in pairs if first_rc is None or p[0] < first_rc]
    explained = len(dead_mutex) + len(not_reaped)
    # Para w fazie pracy jest wyjasniona tylko przez wylaczenie aparatury: martwy muteks (para w jego oknie kill)
    # albo klient niezebrany (bez okna kill; liczony sztuka za sztuke).
    dead_t = {w["t_munmap"] for c, w in zip(conns, kills) if c in dead_mutex}
    pw_dead = sum(1 for p in pairs_working if p[0] in dead_t)
    pairs_working_unexplained = max(0, len(pairs_working) - pw_dead - len(not_reaped))
    erased_total = sum(1 for w in kills if w is not None and w["erased"]) + len(not_reaped)
    tail = [(p, ov) for p, ov in zip(pairs, in_overflow) if p[0] > last_start]
    overflow_n = sum(1 for w in kills if w is not None and w["overflow"])
    created = sum(m is not None for m in maps)

    # Oddania z puli: renameat w watku spoza RT, poza oknami R_C, w czasie podlaczenia bez mmap kolejki.
    rc_rename = {w["rename_idx"] for w in kills if w is not None and w["rename_idx"] is not None}
    pool_out = []
    for i, e in enumerate(events):
        if e[2] in RENAME and e[3] == "enter" and e[1] not in rt:
            j = next((k for k in range(i + 1, len(events)) if events[k][1] == e[1] and events[k][2] == e[2]
                      and events[k][3] == "exit"), None)
            if j is None or j in rc_rename or events[j][4] != 0:
                continue
            ci = next((k for k, c in enumerate(conns) if c["start"] <= e[0] <= c["end"]), None)
            if ci is not None and maps[ci] is None:
                pool_out.append((ci, e[0], events[j][0]))

    # O2: zdarzenie podlaczenia.
    conn_ev = []
    for ci, m in enumerate(maps):
        if m is not None:
            conn_ev.append(("created", m["w0"], m["w1"]))
    for ci, t0, t1 in pool_out:
        conn_ev.append(("pooled", t0, t1))
    o2 = []
    for kind, w0, w1 in conn_ev:
        mask = (dl <= w1) & (end >= w0)
        o2.append({"kind": kind, "len_ns": w1 - w0, "e2e": int(s["e2e"][mask].max()) if mask.any() else None})

    o1 = futex_obs(events, rt, live, unmapped, [(w["t0"], w["t1"]) for w in windows], dl, end, s["e2e"], period)
    in_series = (dl >= series[0]) & (dl <= series[1])
    o1["slots"] = int(in_series.sum())

    kill_client = sum(w is not None for w in kills)
    return {"meta": meta, "side": side, "windows": windows, "pseudo": pseudo, "period": period,
            "ctl": {k: s[k][control] for k in ("e2e", "compute", "wake")}, "n_conns": len(conns),
            "k1": {"pairs": len(pairs), "kill_client": kill_client, "pool_in": pool_in, "pool_out": len(pool_out),
                   "created": created, "overflow": overflow_n, "pairs_working": len(pairs_working),
                   "pairs_before": len(pairs_before), "pairs_working_unexplained": pairs_working_unexplained,
                   "tail_pairs": len(tail), "tail_outside_overflow": sum(1 for _, ov in tail if not ov),
                   "dead_mutex": len(dead_mutex), "not_reaped": len(not_reaped), "no_kill_reaped": len(no_kill_reaped),
                   "erased_other": len(erased_other), "explained": explained, "erased_total": erased_total,
                   "kill_ret": sorted({w["kill_ret"] for w in kills if w is not None}, key=lambda v: (v is None, v)),
                   "releases_B": len(windows) if side == "B" else None,
                   "rc_windows_in_rt": sum(1 for w in kills if w is not None and w["tid"] in rt)},
            "o1": o1, "o2": o2,
            "overflow_len": [w["t1"] - w["t0"] for w in kills if w is not None and w["overflow"] and w["t0"]],
            "pair_cpus": sorted({e[5] for p in pairs for e in events if e[0] == p[0] and e[1] == p[2]})}


def pct(a, q):
    return float(np.percentile(a, q, method="inverted_cdf")) if len(a) else float("nan")


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
    """Dokladny dwustronny test permutacyjny statystyki U dla malych prob (9 vs 9), jak R600."""
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


def dist(a, qs=(50, 99, 100)):
    return " / ".join("-" if (q == 99 and len(a) < MIN_N) else fmt_ms(pct(a, q)) for q in qs)


def side_summary(rs):
    win = [w for r in rs for w in r["windows"]]
    ev = [w["e2e"] for w in win if w["hit"]]
    ps = [p for r in rs for p in r["pseudo"]]
    p = mann_whitney_greater(ev, ps)
    return {"runs": rs, "win": win, "ev": ev, "ps": ps, "p": p,
            "delta": pct(ev, 50) - pct(ps, 50) if ev and ps else float("nan"),
            "period": int(np.median([r["period"] for r in rs])) if rs else 0,
            "ctl": {k: np.concatenate([r["ctl"][k] for r in rs]) for k in ("e2e", "compute", "wake")} if rs else {},
            "per_run": {"compute_p50": [pct(r["ctl"]["compute"], 50) for r in rs],
                        "wake_p99": [pct(r["ctl"]["wake"], 99) for r in rs],
                        "e2e_p99": [pct(r["ctl"]["e2e"], 99) for r in rs]}}


def k2_verdict(x, control_ok):
    if len(x["ev"]) < MIN_N:
        return f"NIEROZSTRZYGNIĘTE (n = {len(x['ev'])} < {MIN_N})"
    if not control_ok:
        return "NIEROZSTRZYGNIĘTE (kontrola dodatnia B nie wykazała efektu)"
    return "ZDANE" if x["p"] >= ALPHA else "NIEZDANE"


def bootstrap_ratio(ev_b, ps_b, ev_c, ps_c, rng, n=BOOT_N):
    """95 % przedzial u = Delta_e2e(C) / Delta_e2e(B), losowanie ze zwracaniem (jak C4 R603)."""
    a = [np.asarray(v, dtype=np.float64) for v in (ev_b, ps_b, ev_c, ps_c)]
    if any(len(v) == 0 for v in a):
        return float("nan"), float("nan")
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
    B = side_summary([r for r in runs if r["side"] == "B"])
    C = side_summary([r for r in runs if r["side"] == "C"])
    period = B["period"] or C["period"]
    lines += [f"Takt slotu (mediana odstępu deadline_ns): {period / 1e6:.3f} ms.", "", "| wielkość | B | C |", "|---|---|---|"]

    def row(label, f):
        lines.append(f"| {label} | {f(B)} | {f(C)} |")

    def row_c(label, f):
        # Wiersz wlasciwy tylko dla puli (strona C); w B nie ma okien R_C, wiec liczby nie maja znaczenia.
        lines.append(f"| {label} | - | {f(C)} |")

    def k1sum(x, key):
        return sum(r["k1"][key] for r in x["runs"])

    row("przebiegi / podłączenia", lambda x: f"{len(x['runs'])} / {sum(r['n_conns'] for r in x['runs'])}")
    row("K1': pary munmap+unlinkat kolejki (wszystkie)", lambda x: str(k1sum(x, "pairs")))
    row("K1': kill(pid_klienta, 0) / do puli (ESRCH → renameat)",
        lambda x: f"{k1sum(x, 'kill_client')} / {k1sum(x, 'pool_in')}")
    row("K1': kolejki utworzone / oddane z puli", lambda x: f"{k1sum(x, 'created')} / {k1sum(x, 'pool_out')}")
    row_c("K1': pary w fazie pracy / przed nią / w ogonie (poza przepełnieniem)",
        lambda x: f"{k1sum(x, 'pairs_working')} / {k1sum(x, 'pairs_before')} / {k1sum(x, 'tail_pairs')} "
                  f"({k1sum(x, 'tail_outside_overflow')})")
    row_c("K1': przepełnienia puli / oczekiwane (utworzone - zwolnione bez puli - 2)",
        lambda x: f"{k1sum(x, 'overflow')} / "
                  f"{sum(max(0, r['k1']['created'] - r['k1']['erased_total'] - POOL) for r in x['runs'])}")
    row_c("K1': wyłączenia: martwy muteks / klient niezebrany; inne zwolnienia bez puli",
        lambda x: f"{k1sum(x, 'dead_mutex')} / {k1sum(x, 'not_reaped')}; "
                  f"{k1sum(x, 'erased_other') + k1sum(x, 'no_kill_reaped')}")
    row("wartości powrotu kill", lambda x: ", ".join(sorted({str(v) for r in x["runs"] for v in r["k1"]["kill_ret"]})) or "-")
    row("rdzenie par munmap+unlinkat", lambda x: ", ".join(sorted({str(c) for r in x["runs"] for c in r["pair_cpus"]})) or "-")
    row("okna K2 (R_B / R_C): liczba / w wątku RT", lambda x: f"{len(x['win'])} / {sum(w['in_rt'] for w in x['win'])}")
    row("okno K2 [ms] p50 / max", lambda x: f"{fmt_ms(pct([w['len_ns'] for w in x['win']], 50))} / "
                                          f"{fmt_ms(pct([w['len_ns'] for w in x['win']], 100))}")
    row("okno przepełnienia [ms] p50 / max (liczba)", lambda x: (
        lambda v: f"{fmt_ms(pct(v, 50))} / {fmt_ms(pct(v, 100))} ({len(v)})")([v for r in x["runs"] for v in r["overflow_len"]]))
    row("okna trafione w slot: n / odsetek", lambda x: f"{len(x['ev'])} / "
        f"{100.0 * len(x['ev']) / len(x['win']) if x['win'] else float('nan'):.1f} %")
    row("zdarzenie: max e2e [ms] p50 / p99 / max", lambda x: dist(x["ev"]))
    row("pseudo-zdarzenie: liczba / max e2e [ms] p50 / p99 / max", lambda x: f"{len(x['ps'])} / {dist(x['ps'])}")
    row("Δ_e2e [µs]; MW p", lambda x: f"{x['delta'] / 1e3:.2f}; {x['p']:.3g}" if x["ev"] and x["ps"] else "-")
    row("okna z max e2e > takt: zdarzenia / pseudo", lambda x: (
        f"{100.0 * np.mean([e > period for e in x['ev']]):.1f} % / {100.0 * np.mean([p > period for p in x['ps']]):.1f} %")
        if x["ev"] and x["ps"] else "-")
    row("sloty obudzone w oknie: wake_lag / compute p50 [µs] (mediana po zdarzeniach)", lambda x: (
        f"{np.median([w['woken_wake'] for w in x['win'] if w['hit']]) / 1e3:.1f} / "
        f"{np.median([w['woken_compute'] for w in x['win'] if w['hit']]) / 1e3:.1f}") if x["ev"] else "-")
    for k in ("e2e", "compute", "wake"):
        row(f"kontrola {k} [ms] p50 / p99 / max", lambda x, k=k: dist(x["ctl"][k]) if x["ctl"] else "-")

    def o1(x, key):
        return sum(r["o1"][key] for r in x["runs"])

    row("O1: futex wątku RT: wejścia / sloty z futex / sloty w serii", lambda x: (
        f"{o1(x, 'enters')} / {o1(x, 'slots_with_futex')} / {o1(x, 'slots')} "
        f"({100.0 * o1(x, 'slots_with_futex') / max(1, o1(x, 'slots')):.3f} %)"))
    row("O1: futex na muteksie kolejki według op / poza kolejkami", lambda x: (
        ", ".join(f"{k} {v}" for k, v in sorted({k: sum(r["o1"]["queue"].get(k, 0) for r in x["runs"])
                                                for r in x["runs"] for k in r["o1"]["queue"]}.items())) or "0")
        + f" / {o1(x, 'other')}")
    row("O1: czekanie na muteks kolejki [ms] p50 / max; w oknie K2; slot > takt", lambda x: (
        lambda v: f"{fmt_ms(pct(v, 50))} / {fmt_ms(pct(v, 100))}; {o1(x, 'wait_in_window')}; {o1(x, 'wait_over_period')}"
        if v else "brak")([v for r in x["runs"] for v in r["o1"]["wait_ns"]]))
    for kind, label in (("created", "kolejka utworzona"), ("pooled", "kolejka z puli")):
        row(f"O2: podłączenie, {label}: liczba / okno p50 [ms] / trafione / max e2e p50 / max [ms]", lambda x, kind=kind: (
            lambda ev: f"{len(ev)} / {fmt_ms(pct([e['len_ns'] for e in ev], 50))} / "
                       f"{sum(e['e2e'] is not None for e in ev)} / "
                       f"{fmt_ms(pct([e['e2e'] for e in ev if e['e2e'] is not None], 50))} / "
                       f"{fmt_ms(pct([e['e2e'] for e in ev if e['e2e'] is not None], 100))}")(
            [e for r in x["runs"] for e in r["o2"] if e["kind"] == kind]))
    lines.append("")

    # K1'.
    b_ok = bool(B["runs"]) and all(r["k1"]["releases_B"] == r["n_conns"] and r["k1"]["kill_client"] == 0 for r in B["runs"])
    n_ab = sum(r["n_conns"] for r in C["runs"])
    excluded = sum(r["k1"]["explained"] for r in C["runs"])
    unexplained = sum(r["k1"]["pairs_working_unexplained"] + r["k1"]["erased_other"] + r["k1"]["no_kill_reaped"]
                      for r in C["runs"])
    pool_ok = sum(r["k1"]["pool_in"] for r in C["runs"]) == n_ab - excluded
    # Kazda utworzona kolejka konczy w puli (najwyzej POOL), w przepelnieniu albo w zwolnieniu bez puli.
    tail_ok = all(r["k1"]["tail_outside_overflow"] == 0
                  and r["k1"]["overflow"] == max(0, r["k1"]["created"] - r["k1"]["erased_total"] - POOL) for r in C["runs"])
    if not C["runs"]:
        k1 = "brak strony C"
    elif not b_ok:
        k1 = "NIEWAŻNE (kontrola dodatnia B niepowtórzona)"
    elif n_ab and excluded / n_ab > EXCLUDED_MAX:
        k1 = f"NIEROZSTRZYGNIĘTE (aparatura: wyłączenia {excluded} z {n_ab})"
    elif unexplained == 0 and pool_ok and tail_ok:
        k1 = "ZDANE"
    else:
        k1 = "NIEZDANE"
    lines.append(f"- **K1'**: kontrola dodatnia B ({sum(r['k1']['releases_B'] or 0 for r in B['runs'])} zwolnień "
                 f"munmap+unlinkat na {sum(r['n_conns'] for r in B['runs'])} podłączeń, kill klienta "
                 f"{sum(r['k1']['kill_client'] for r in B['runs'])}) {'powtórzona' if b_ok else 'NIEPOWTÓRZONA'}; "
                 f"C: do puli {sum(r['k1']['pool_in'] for r in C['runs'])} z {n_ab} (wyłączenia {excluded}), "
                 f"pary w fazie pracy niewyjaśnione {sum(r['k1']['pairs_working_unexplained'] for r in C['runs'])}, "
                 f"zwolnienia bez puli niewyjaśnione {sum(r['k1']['erased_other'] + r['k1']['no_kill_reaped'] for r in C['runs'])}, "
                 f"spójność ogona {'tak' if tail_ok else 'NIE'}. Werdykt: {k1}.")

    # K2.
    ctl_ok = len(B["ev"]) >= MIN_N and B["p"] < ALPHA
    lines.append(f"- **K2**: kontrola dodatnia mocy B: n = {len(B['ev'])}, p = {B['p']:.3g} - "
                 f"{'spełniona' if ctl_ok else 'NIESPEŁNIONA'}; C: n = {len(C['ev'])}, p = {C['p']:.3g}, "
                 f"Δ_e2e B = {B['delta'] / 1e3:.2f} µs, C = {C['delta'] / 1e3:.2f} µs. Werdykt C: {k2_verdict(C, ctl_ok)}.")
    lo, hi = bootstrap_ratio(B["ev"], B["ps"], C["ev"], C["ps"], rng_boot)
    u = C["delta"] / B["delta"] if B["delta"] and B["delta"] > 0 else float("nan")
    lines.append(f"- K2 opisowo: u = Δ_e2e(C) / Δ_e2e(B) = {u:.2f} (95 % bootstrap {lo:.2f}..{hi:.2f}).")

    # K3.
    for key, label in (("compute_p50", "compute_ns p50"), ("wake_p99", "wake_lag_ns p99"), ("e2e_p99", "e2e_ns p99")):
        b = [x for x in B["per_run"][key] if not math.isnan(x)]
        c = [x for x in C["per_run"][key] if not math.isnan(x)]
        if not (b and c):
            lines.append(f"- **K3**, {label} per przebieg: brak danych obu stron - nie do oceny.")
            continue
        diff = float(np.median(c) - np.median(b))
        spread = max(max(b) - min(b), max(c) - min(c))
        p = permutation_mw_two_sided(b, c)
        state = "w szumie" if abs(diff) <= spread else ("REGRESJA C - osobne znalezisko" if diff > 0 else "C lepsze poza szumem")
        lines.append(f"- **K3**, {label} per przebieg: mediana C-B = {diff / 1e3:.2f} µs, rozrzut wewnątrz strony do "
                     f"{spread / 1e3:.2f} µs, permutacyjny MW p = {p:.3g} - {state}.")
    lines.append("")
    return lines


def parser_check(raw, seed):
    """Strona B danych R600: okna R_B identyczne z find_release_r600 i werdykt K2 strony B jak w R600."""
    n, diff = 0, 0
    rng = np.random.default_rng(seed)
    for fam_dir in sorted(p for p in raw.iterdir() if p.is_dir()):
        runs = []
        for run_dir in sorted(p for p in fam_dir.iterdir() if p.is_dir() and p.name.startswith("B_")):
            conns = load_conns(run_dir / "conns.tsv")
            rt = rt_tids(run_dir / "rt.txt")
            events = parse_trace(run_dir / "trace.txt")
            for m in queue_mappings(events, conns, rt):
                if m is None:
                    continue
                old = find_release_r600(events, m["addr"], m["w1"])
                new = find_release(events, m["addr"], m["len"], m["w1"])
                n += 1
                if (old is None) != (new is None) or (old is not None and tuple(old) != tuple(new[:3])):
                    diff += 1
                    print(f"{run_dir}: R600 {old} R603C {new}")
            runs.append(analyze_run(run_dir, rng))
        x = side_summary(runs)
        pairs = sum(r["k1"]["pairs"] for r in runs)
        print(f"{fam_dir.name}: B n = {len(x['ev'])}, p = {x['p']:.3g}, Δ_e2e = {x['delta'] / 1e6:.3f} ms, "
              f"K2 B (bez kontroli A): {k2_verdict(x, True)}; okien {len(x['win'])}, par munmap+unlinkat {pairs}")
    print(f"parser-check: {n} okien, {diff} różnic")
    return diff == 0 and n > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--seed", type=int, default=6031)
    ap.add_argument("--parser-check", action="store_true", help="--raw wskazuje surowe dane R600")
    args = ap.parse_args()
    if args.parser_check:
        sys.exit(0 if parser_check(args.raw, args.seed) else 2)
    rng = np.random.default_rng(args.seed)
    rng_boot = np.random.default_rng(args.seed + 1)
    report = ["# R603C - wynik", "",
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
