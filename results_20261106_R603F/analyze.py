#!/usr/bin/env python3
"""R603F: analiza przebiegow run_one.py wedlug kryteriow K0, K1'', K2s, K3, K3t i obserwacji z README.md.

Uzycie: analyze.py --raw KATALOG [--out RAPORT.md] [--seed 6034]
        analyze.py --raw KATALOG_SUCHY --gates               (bramki G1, G2/G2f, G3-G6 i H suchego przebiegu)
        analyze.py --raw SUROWE_R603E --parser-check          (test parsera na danych R603E, README, Kolejnosc, punkt 2)
KATALOG ma uklad <rodzina>/<strona>_<para>/ ze stronami Cp i D2s (slots.csv z kolumna P1, trace.txt, conns.tsv,
rt.txt, meta.json). Kod wyjscia: 0 - raport zapisany / test zdany, 2 - blad danych albo test niezdany.
Wymaga NumPy (np. retractordb/.venv-python).

Parser R603E (a przez niego R603D i R603C) jest importowany BEZ ZMIAN z ../results_20261106_R603E/analyze.py.
Ten modul podmienia w zaladowanym parserze R603C dwie funkcje (README R603F, Aparatura, punkt 4):
- kill_windows -> kill_windows_f: okno R_C od kill(pid, 0) z poolAbandonedQueue, z rozpoznaniem wykrycia przez sonde
  zycia (dwie pary openat -ENOENT + kill -ESRCH dla tego samego pid w jednym obrocie) i samotnego wykrycia (para bez
  zwolnienia przed nastepnym snem). Na danych z jednym kill na porzucenie daje okna kill_windows R603C (test parsera, 2);
- analyze_run -> wersja z poprawiona klasyfikacja martwego muteksu (decyzja czlowieka po R603E, punkt 1): takze
  zwolnienie bez kill przy znalezionym procesie klienta, i para martwego muteksu wyjasniona takze w ogonie.
Strona C' idzie przez analyze R603E (D.analyze_run), strona D2s przez analyze_run_f - kopie analyze_run_e R603E,
w ktorej k porcji jest osobne dla kazdej serii (z liczby komunikatow n^ w chwili wykrycia) i bez modelu bramki.
Ziarna: placebo --seed, bootstrap --seed+1, syntetyczne serie H0 --seed+2, pseudo-zdarzenia opisowe --seed+3,
pseudo-zdarzenia wewnatrz parsera R603C --seed+4 (jak R603D/R603E). Wydruk to liczby wyprowadzone; zadnej tresci korpusu.
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


def _load_r603e():
    spec = importlib.util.spec_from_file_location("analyze_r603e", HERE.parent / "results_20261106_R603E" / "analyze.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


E = _load_r603e()
D = E.D
A = E.A
pct, dist, fmt_us, ser, fmt_ci = D.pct, D.dist, D.fmt_us, E.ser, E.fmt_ci

ENOENT = 2
BATCH = D.DRAIN_BATCH  # kResponseQueueDrainBatch
BUFFER_S = 10  # cfgQueueBufferSeconds: pojemnosc kolejki = 10 s strumienia
BOUNDARY_MSG = 4  # seria graniczna: |n^ - 256 j| <= 4
L_MIN_NS, L_MAX_NS = -5_000_000, 1_010_000_000  # K0: granice opoznienia wykrycia
FOUND_DEAD_PAD_NS = 10_000_000  # martwy muteks (b): munmap najpozniej 10 ms po koncu klienta
SIDES = ("Cp", "D2s")
NAMES = {"Cp": "C'", "D2s": "D2s"}

_KW_R603C = A.kill_windows
_RUN_R603C = A.analyze_run


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------- rozpoznanie sondy (README, Okna i zdarzenia)

def _tid_index(events):
    by = {}
    for i, e in enumerate(events):
        by.setdefault(e[1], []).append(i)
    return by


def classify_kills(events, conns, rt):
    """Dla kazdego podlaczenia: indeks kill(pid, 0) okna R_C (albo None), wykrycia przez sonde i samotne wykrycia.

    kill wykrycia: po jego wyjsciu kolejne zdarzenia watku to openat (enter, exit) i kill(ten sam pid) - bez snu.
    kill okna R_C: przed nastepnym wejsciem w sen tego watku jest renameat albo munmap.
    kill samotny: ani jedno, ani drugie. Kill bez zadnego z tych wzorcow, ale przed ktorym nie ma snu w sladzie
    (koniec sladu), traktowany jak R603C (okno R_C).
    """
    by_pid = {}
    for i, e in enumerate(events):
        if e[2] == "kill" and e[3] == "enter" and e[1] not in rt and e[4].get("sig", -1) == 0:
            by_pid.setdefault(e[4].get("pid"), []).append(i)
    tidx = _tid_index(events)
    pos_in = {}
    for tid, seq in tidx.items():
        for k, i in enumerate(seq):
            pos_in[i] = k
    out = []
    for c in conns:
        cand = [i for i in by_pid.get(c["pid"], []) if events[i][0] > c["start"]]
        res = {"rc": None, "det": [], "lone": [], "det_before_rc": None}
        last_det = None
        for i in cand:
            tid = events[i][1]
            seq = tidx[tid]
            k = pos_in[i]
            # wyjscie z kill
            j = k + 1
            while j < len(seq) and not (events[seq[j]][2] == "kill" and events[seq[j]][3] == "exit"):
                j += 1
            if j >= len(seq):
                res["rc"] = i
                break
            t_exit = events[seq[j]][0]
            nxt = [events[seq[x]] for x in range(j + 1, min(j + 4, len(seq)))]
            is_det = (len(nxt) == 3 and nxt[0][2] == "openat" and nxt[0][3] == "enter" and nxt[1][2] == "openat"
                      and nxt[1][3] == "exit" and nxt[2][2] == "kill" and nxt[2][3] == "enter"
                      and nxt[2][4].get("pid") == c["pid"])
            if is_det:
                res["det"].append(t_exit)
                last_det = t_exit
                continue
            kind = None
            for x in range(j + 1, len(seq)):
                ev = events[seq[x]]
                if ev[2] in D.SLEEP and ev[3] == "enter":
                    break
                if (ev[2] in A.RENAME and ev[3] == "exit") or (ev[2] == "munmap" and ev[3] == "enter"):
                    kind = "rc"
                    break
            else:
                kind = "rc"  # koniec sladu bez snu - jak R603C
            if kind == "rc":
                res["rc"] = i
                res["det_before_rc"] = last_det
                break
            res["lone"].append(t_exit)
        out.append(res)
    return out


def _window_from(events, idx):
    """Wnetrze petli kill_windows R603C od kill o indeksie idx (bez zmian)."""
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
        elif (e[2] in A.RENAME and e[3] == "enter" and w["t_unlink"] is not None
              and e[0] - w["t_unlink"] > A.RENAME_AFTER_UNLINK_MAX_NS):
            break
        elif e[2] in A.RENAME and e[3] == "exit":
            if e[4] == 0:
                w["t1"], w["rename_idx"] = e[0], j
                break
        elif e[3] == "enter" and e[2] in ("kill", "openat", "mmap", "statfs", "fstatfs"):
            break
    pair = w["munmap"] > 0 and w["unlink"] > 0
    w["overflow"] = pair and w["t1"] is not None
    w["erased"] = pair and w["t1"] is None
    return w


def kill_windows_f(events, conns, rt):
    """Okna R_C jak kill_windows R603C, ale od kill z poolAbandonedQueue; pole t_det = wykrycie przez sonde."""
    out = []
    for c, res in zip(conns, classify_kills(events, conns, rt)):
        if res["rc"] is None:
            out.append(None)
            continue
        w = _window_from(events, res["rc"])
        w["t_det"] = res["det_before_rc"]
        out.append(w)
    return out


# ---------------------------------------------------------------- poprawka klasyfikacji martwego muteksu

def found_dead_mutex(events, conns, kills, pairs, rt):
    """Martwy muteks (b): para munmap + unlinkat w watku spoza RT, poza oknami R_C, poprzedzona w tym watku openat
    z sukcesem bez kill pomiedzy, z munmap w [pierwszy wiersz, koniec + 10 ms] klienta bez okna R_C.
    Wynik: {indeks podlaczenia: czas munmap pary}."""
    in_rc = {w["t_munmap"] for w in kills if w is not None and w["t_munmap"] is not None}
    tidx = _tid_index(events)
    t_of = {}
    for tid, seq in tidx.items():
        t_of[tid] = [events[i][0] for i in seq]
    out = {}
    used = set()
    for ci, (c, w) in enumerate(zip(conns, kills)):
        if w is not None or c["first"] is None:
            continue
        for p in pairs:
            t, _, tid, _ = p
            if tid in rt or t in in_rc or t in used or not (c["first"] <= t <= c["end"] + FOUND_DEAD_PAD_NS):
                continue
            seq = tidx[tid]
            k = int(np.searchsorted(t_of[tid], t, side="right")) - 1
            ok = False
            while k >= 0:
                ev = events[seq[k]]
                if ev[2] == "kill":
                    break
                if ev[2] == "openat" and ev[3] == "exit":
                    ok = ev[4] >= 0
                    break
                k -= 1
            if ok:
                out[ci] = t
                used.add(t)
                break
    return out


def analyze_run_c_fixed(run_dir, rng):
    """analyze_run R603C z poprawiona klasyfikacja martwego muteksu (README, Okna i zdarzenia)."""
    r = _RUN_R603C(run_dir, rng)
    conns = A.load_conns(run_dir / "conns.tsv")
    rt = A.rt_tids(run_dir / "rt.txt")
    events = A.parse_trace(run_dir / "trace.txt")
    maps = A.queue_mappings(events, conns, rt)
    pairs, _, _ = A.queue_pairs(events, maps)
    kills = A.kill_windows(events, conns, rt) if conns[0]["pid"] is not None else [None] * len(conns)
    k1 = r["k1"]
    dead = [ci for ci, (c, w) in enumerate(zip(conns, kills)) if w is not None and w["erased"] and w["kill_ret"] == -A.ESRCH
            and c["first"] is not None and w["t_kill"] - c["first"] < A.EARLY_ABANDON_NS]
    found = found_dead_mutex(events, conns, kills, pairs, rt)
    not_reaped = [ci for ci, (c, w) in enumerate(zip(conns, kills)) if w is None and c["reaped"] == 0 and ci not in found]
    no_kill_reaped = [ci for ci, (c, w) in enumerate(zip(conns, kills)) if w is None and c["reaped"] != 0 and ci not in found]
    first_rc = min((w["t0"] for w in kills if w is not None and w["t1"] is not None and w["t0"] is not None), default=None)
    last_start = conns[-1]["start"]
    in_overflow = [any(w is not None and w["overflow"] and w["t_kill"] <= p[0] <= w["t1"] for w in kills) for p in pairs]
    dead_t = {kills[ci]["t_munmap"] for ci in dead} | set(found.values())
    pairs_working = [p for p in pairs if first_rc is not None and first_rc <= p[0] <= last_start]
    pw_dead = sum(1 for p in pairs_working if p[0] in dead_t)
    tail = [(p, ov) for p, ov in zip(pairs, in_overflow) if p[0] > last_start]
    k1.update({
        "dead_mutex": len(dead) + len(found), "dead_mutex_found": len(found), "not_reaped": len(not_reaped),
        "no_kill_reaped": len(no_kill_reaped), "explained": len(dead) + len(found) + len(not_reaped),
        "pairs_working_unexplained": max(0, len(pairs_working) - pw_dead - len(not_reaped)),
        "erased_total": sum(1 for w in kills if w is not None and w["erased"]) + len(not_reaped) + len(found),
        "tail_outside_overflow": sum(1 for p, ov in tail if not ov and p[0] not in dead_t),
        "dead_ci": sorted(dead + list(found)), "not_reaped_ci": not_reaped,
        "erased_after_det": sum(1 for ci in dead if kills[ci].get("t_det") is not None)})
    return r


A.kill_windows = kill_windows_f
A.analyze_run = analyze_run_c_fixed


# ---------------------------------------------------------------- strona D2s

def analyze_run_f(run_dir, rngs):
    """Kopia E.analyze_run_e (bez bramki): P0 i k kolejnych obrotow, k osobno dla kazdej serii z n^."""
    meta = json.loads((run_dir / "meta.json").read_text())
    base = A.analyze_run(run_dir, rngs["base"])
    side, fam = meta["side"], meta["family"]
    h = D.H[fam]
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
    rate = caps[0] / BUFFER_S if caps else np.nan  # komunikatow na sekunde
    ts, te, comm_tid, sleep_other = D.comm_turns(events, tids, rt)
    comm_ev = [e for e in events if e[1] == comm_tid and e[2] not in D.SLEEP and e[3] == "enter"] if comm_tid else []
    comm_t = np.array([e[0] for e in comm_ev], dtype=np.int64)

    series = []
    for ci, w in enumerate(kills):
        if w is None or w["t0"] is None or w["t1"] is None:
            continue
        c = conns[ci]
        if w.get("t_det") is not None and c["first"] is not None:
            n_hat = int(round(rate * (w["t_det"] - c["first"]) / 1e9))
        else:
            n_hat = caps[0] if caps else 0  # porzucenie z pelnej kolejki
        k = D.capacity_portions(n_hat)
        boundary = any(abs(n_hat - BATCH * j) <= BOUNDARY_MSG for j in range(1, k + 2))
        sr = {"ci": ci, "t_kill": w["t_kill"], "t0": w["t0"], "p0": (w["t0"], w["t1"]), "windows": [(w["t0"], w["t1"])],
              "end": w["t1"], "kind": "overflow" if w["overflow"] else "ok", "reason": "", "turns": [], "n_hat": n_hat,
              "k": k, "boundary": boundary, "t_det": w.get("t_det")}
        j0 = int(np.searchsorted(ts, w["t0"], side="right")) - 1
        if j0 < 0 or te[j0] < w["t1"]:
            if sr["kind"] == "ok":
                sr["kind"], sr["reason"] = "disturbed", "P0 poza jednym obrotem"
        elif j0 + k + 1 >= len(ts):
            sr["kind"], sr["reason"] = "disturbed", "koniec sladu przed Pk+1"
        else:
            # P1 w obrocie P0 (aneks A1): probeSubscribers oddaje kolejke do puli przed releaseAbandonedQueues,
            # a ta w tym samym obrocie odbiera porcje z niegotowego wpisu - P1 = reszta obrotu P0 po renameat.
            # P2..Pk = k - 1 kolejnych obrotow, Pk+1 = nastepny.
            last = j0 + max(k, 1) - 1
            sr["turns"] = list(range(j0 + 1, last + 1))
            sr["after"] = last + 1
            if k:
                sr["p1"] = (w["t1"], int(te[j0]))
                sr["windows"].append(sr["p1"])
            sr["windows"] += [(int(ts[j]), int(te[j])) for j in sr["turns"]]
            sr["end"] = int(te[last]) if k else w["t1"]
            a, b = (w["t1"], int(te[last])) if k else (0, -1)
            inside = [e for e in comm_ev if a < e[0] <= b and not (e[0] <= int(te[j0]) and e[2] in A.RENAME)]
            if inside and sr["kind"] == "ok":
                names = sorted({e[2] for e in inside})
                sr["kind"], sr["reason"] = "disturbed", "wywolanie w P1..Pk: " + ", ".join(names)
        series.append(sr)

    excl = [(w["t_kill"], w["t1"] if w["t1"] is not None else (w["t0"] or w["t_kill"])) for w in kills if w is not None]
    excl += [(w["t_det"], w["t_kill"]) for w in kills if w is not None and w.get("t_det") is not None]
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
    busy += [(w["t_det"], w["t_kill"]) for w in kills if w is not None and w.get("t_det") is not None]
    idle = np.ones(len(ts), dtype=bool)
    for a, b in busy:
        idle &= ~((ts <= b) & (te >= a))
    if len(comm_t):
        j = np.searchsorted(ts, comm_t, side="right") - 1
        j = j[(j >= 0) & (comm_t <= te[np.clip(j, 0, max(0, len(te) - 1))])] if len(ts) else j[:0]
        idle[j] = False
    idle_len = (te - ts)[idle]

    p0_len = [sr["p0"][1] - sr["p0"][0] for sr in series if sr["kind"] != "overflow"]
    phase = []
    for sr in series:
        if sr["kind"] != "overflow":
            i = int(np.searchsorted(dl, sr["t0"], side="right")) - 1
            if i >= 0:
                phase.append(sr["t0"] - int(end_slot[i]))
    full = [int(te[j] - ts[j]) for sr in series if sr["kind"] == "ok" for j in sr["turns"][:-1]]
    last = [int(te[sr["turns"][-1]] - ts[sr["turns"][-1]]) for sr in series if sr["kind"] == "ok" and sr["turns"]]
    p1 = [sr["p1"][1] - sr["p1"][0] for sr in series if sr["kind"] == "ok" and "p1" in sr]
    after = [int(te[sr["after"]] - ts[sr["after"]]) for sr in series if sr["kind"] == "ok" and "after" in sr]
    step = [int(ts[j + 1] - ts[j]) for sr in series if sr["kind"] == "ok" for j in sr["turns"]]
    dur = [sr["end"] - sr["t0"] for sr in series if sr["kind"] == "ok"]

    pouts = D.pool_out_events(events, conns, maps, kills, rt)
    viol, o6 = E.pool_model(series, kills, pouts, maps)
    late = []
    for sr in series:
        nxt = next((c["start"] for c in conns if c["start"] > sr["t_kill"]), None)
        if nxt is not None and sr["end"] >= nxt:
            late.append(sr["ci"])
    tail_overflow = sum(1 for sr in series if sr["kind"] == "overflow" and sr["t_kill"] > conns[-1]["start"])

    series_span = (conns[0]["start"] - A.SERIES_PAD_NS, conns[-1]["end"] + A.SERIES_PAD_NS)
    desc = {}
    for part in ("P0", "Pk"):
        wins = [sr["windows"][0] for sr in series if sr["kind"] == "ok"] if part == "P0" else \
            [w for sr in series if sr["kind"] == "ok" for w in sr["windows"][1:]]
        ev = []
        for a, b in wins:
            mask = (dl <= b) & (end_slot >= a)
            if mask.any():
                ev.append(int(s["e2e"][mask].max()))
        ps = A.pseudo_events(dl, end_slot, s["e2e"], ctl, [b - a for a, b in wins], series_span, rngs["pseudo"]) if wins else []
        desc[part] = {"ev": ev, "ps": ps, "n_win": len(wins)}

    in_series = (dl >= series_span[0]) & (dl <= series_span[1])
    return {"meta": meta, "side": side, "fam": fam, "base": base, "series": series, "h0": [], "model": model,
            "ctl": {kk: s[kk][ctl] for kk in ("e2e", "compute", "wake")}, "n_conns": len(conns), "k": None, "k_mmap": k_mmap,
            "caps": caps, "turns": (ts, te), "comm_tid": comm_tid, "sleep_other": sleep_other, "idle_len": idle_len,
            "o3": {"p0": p0_len, "phase": phase, "full": full, "last": last, "after": after, "step": step, "dur": dur,
                   "p1": p1},
            "pool_viol": viol, "late": late, "pool_out_n": len(pouts), "tail_overflow": tail_overflow, "desc": desc,
            "comm_ev_n": len(comm_ev), "trace_span": (events[0][0], events[-1][0]) if events else (0, 0),
            "slots_in_series": int(in_series.sum()), "conns": conns, "o6": o6}


def probe_obs(run_dir, r):
    """K0 i sonda opisowo: wykrycia, samotne, opoznienia L, porzucenia z pelnej kolejki, openat z sukcesem."""
    events = A.parse_trace(run_dir / "trace.txt")
    rt = A.rt_tids(run_dir / "rt.txt")
    conns = r["conns"]
    cls = classify_kills(events, conns, rt)
    kills = kill_windows_f(events, conns, rt)
    excl = set(r["base"]["k1"]["dead_ci"]) | set(r["base"]["k1"]["not_reaped_ci"])
    L, full_q, bad = [], 0, []
    for ci, (c, w) in enumerate(zip(conns, kills)):
        if ci in excl or w is None:
            continue
        if w.get("t_det") is None:
            full_q += 1
            bad.append(ci)
            continue
        L.append(w["t_det"] - c["end"])
        if not (L_MIN_NS <= L[-1] <= L_MAX_NS) or w["t1"] is None:
            bad.append(ci)
    tid = r["comm_tid"]
    ok_open = [e[0] for e in events if e[1] == tid and e[2] == "openat" and e[3] == "exit" and e[4] >= 0]
    ok_open = np.array(ok_open, dtype=np.int64)
    in_conn = sum(int(((ok_open >= c["start"]) & (ok_open <= c["end"])).sum()) for c in conns)
    return {"det": sum(len(x["det"]) for x in cls), "lone": sum(len(x["lone"]) for x in cls), "L": L, "full_q": full_q,
            "bad": bad, "pooled": sum(1 for w in kills if w is not None and w["t1"] is not None),
            "open_in_conn": in_conn, "open_out_conn": int(len(ok_open)) - in_conn, "n_conns": len(conns)}


def analyze(run_dir, rngs):
    side = json.loads((run_dir / "meta.json").read_text())["side"]
    if side == "D2s":
        r = analyze_run_f(run_dir, rngs)
        m = r["model"]
        for sr in r["series"]:
            if sr["kind"] == "ok":
                sr["aff"] = E.affected_cluster(m, sr["windows"], rngs["placebo"])
    else:
        r = E.analyze(run_dir, rngs)
    r["probe"] = probe_obs(run_dir, r)
    return r


# ---------------------------------------------------------------- H0 dla serii D2s

def h0_windows_d2s(m, rng, k, par):
    """Seria o ksztalcie D2s (aneks A1): P0 i P1 jednym ciagiem w pierwszym obrocie, P2..Pk w k - 1 kolejnych
    obrotach; faza, obrot i rozrzut jak D.SlotModel.h0_windows."""
    cidx = np.flatnonzero(m.ctl)
    k0 = int(rng.choice(cidx))
    t0 = int(m.end[k0]) + int(rng.integers(par["phase"][0], par["phase"][1]))
    wins = [(t0, t0 + par["p0_ns"] + (par["p1_ns"] if k else 0))]
    for j in range(1, k):
        a = t0 + j * par["turn_ns"] + int(rng.integers(0, par["jitter_ns"]))
        wins.append((a, a + par["w_ns"]))
    return wins


def h0_d2s(runs_cp, par, ks, rng):
    """Syntetyczne serie o ksztalcie D2s (P0 + k porcji, k z empirycznego rozkladu D2s) na tle slotow kontrolnych C',
    E.H0_PER_SERIES na kazda niezaklocona serie C' (aneks A2 R603E)."""
    out = []
    if not ks:
        return out
    for r in runs_cp:
        m = r["model"]
        for _ in range(E.H0_PER_SERIES * sum(1 for sr in r["series"] if sr["kind"] == "ok")):
            k = int(ks[int(rng.integers(0, len(ks)))])
            wins = h0_windows_d2s(m, rng, k, par)
            idx, _ = E.affected_idx(m, wins)
            if not len(idx) or not m.ctl[idx].all():
                continue
            cl = E.affected_cluster(m, wins, rng)
            if cl is not None:
                out.append(cl)
    return out


# ---------------------------------------------------------------- raport

def k1_f(rs, rs_cp):
    """K1'' (warunek (b)) z kontrola dodatnia D4: przepelnienie w ogonie kazdego przebiegu C' tej rodziny, oddanie z puli
    w kazdym przebiegu strony; dla strony C' (rs is rs_cp) kontrola jak R603E."""
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
    pos_cp = bool(rs_cp) and all(r["tail_overflow"] >= 1 for r in rs_cp)
    pos_out = all(r["pool_out_n"] >= 1 for r in rs)
    viol = sum(len(r["pool_viol"]) for r in rs)
    if not (pos_cp and pos_out):
        v = ("NIEROZSTRZYGNIĘTE (aparatura: kontrola dodatnia - " + ("przebieg C' bez przepełnienia w ogonie" if not pos_cp
             else "przebieg bez oddania z puli") + ")")
    elif n and excluded / n > A.EXCLUDED_MAX:
        v = f"NIEROZSTRZYGNIĘTE (aparatura: wyłączenia {excluded} z {n})"
    elif unexplained == 0 and pool_ok and tail_ok and viol == 0:
        v = "ZDANE"
    else:
        v = "NIEZDANE"
    late = sum(len(r["late"]) for r in rs)
    txt = (f"do puli {k1('pool_in')} z {n} (wyłączenia {excluded}: martwy muteks {k1('dead_mutex')}, z tego przy znalezionym "
           f"procesie {k1('dead_mutex_found')} i po wykryciu przez sondę {k1('erased_after_det')}, niezebrany "
           f"{k1('not_reaped')}), pary w fazie pracy niewyjaśnione {k1('pairs_working_unexplained')}, zwolnienia bez puli "
           f"niewyjaśnione {k1('erased_other') + k1('no_kill_reaped')}, kolejki utworzone / z puli {k1('created')} / "
           f"{k1('pool_out')}, przepełnienia {k1('overflow')} (kontrola dodatnia: przepełnienie w ogonie każdego przebiegu C' "
           f"- {'tak' if pos_cp else 'NIE'}, oddanie z puli w każdym przebiegu - {'tak' if pos_out else 'NIE'}), spójność "
           f"ogona {'tak' if tail_ok else 'NIE'}, model puli: naruszeń {viol}, serii niegotowych przed następnym "
           f"podłączeniem {late}")
    return v, txt


def k0_verdict(P, Q):
    det_cp = sum(r["probe"]["det"] for r in P)
    bad = sum(len(r["probe"]["bad"]) for r in Q)
    full_q = sum(r["probe"]["full_q"] for r in Q)
    n_ok = sum(len(r["probe"]["L"]) for r in Q)
    if not Q:
        return "brak strony D2s"
    if bad == 0 and full_q == 0 and det_cp == 0 and n_ok > 0:
        return "ZDANE"
    return (f"NIEZDANE (D2s: porzuceń poza wyłączeniami bez wykrycia albo z L poza granicami {bad}, w tym z pełnej kolejki "
            f"{full_q}; C': wykryć przez sondę {det_cp})")


def regress_lines(P, Q, items, label_prefix):
    lines = []
    for key, f, label in items:
        c = [f(r) for r in P]
        p = [f(r) for r in Q]
        c, p = [x for x in c if not math.isnan(x)], [x for x in p if not math.isnan(x)]
        if not (c and p):
            lines.append(f"- **{label_prefix}**, {label}: brak danych obu stron.")
            continue
        diff = float(np.median(p) - np.median(c))
        spread = max(max(c) - min(c), max(p) - min(p))
        pv = A.permutation_mw_two_sided(c, p)
        state = "w szumie" if abs(diff) <= spread else ("REGRESJA D2s - osobne znalezisko" if diff > 0 else "D2s lepsze poza szumem")
        lines.append(f"- **{label_prefix}**, {label} per przebieg: mediana D2s - C' = {diff / 1e3:.2f} µs, rozrzut wewnątrz "
                     f"strony do {spread / 1e3:.2f} µs, permutacyjny MW p = {pv:.3g} - {state}.")
    return lines


def family_report(fam, P, Q, h0, rngs, ctx):
    """P = przebiegi C', Q = przebiegi D2s."""
    runs = P + Q
    period = int(np.median([r["model"].period for r in runs]))
    lines = [f"## {fam}", "", f"Takt slotu: {period / 1e6:.3f} ms, H = {D.H[fam]}, k C' = {D.PORTIONS[fam]} "
             f"(z pojemności mmap: {sorted({x for r in runs for x in r['k_mmap']})}, pojemność "
             f"{sorted({x for r in runs for x in r['caps']})}).", "", "| wielkość | C' | D2s |", "|---|---|---|"]

    def row(label, f, only_q=False):
        lines.append(f"| {label} | {'-' if only_q or not P else f(P)} | {f(Q) if Q else '-'} |")

    rng = rngs["boot"]
    pr = lambda x, key: sum(r["probe"][key] for r in x)  # noqa: E731
    row("przebiegi / podłączenia", lambda x: f"{len(x)} / {sum(r['n_conns'] for r in x)}")
    row("K0: wykrycia przez sondę / samotne wykrycia", lambda x: f"{pr(x, 'det')} / {pr(x, 'lone')}")
    row("K0: porzucenia poza wyłączeniami: z wykryciem / z pełnej kolejki / poza granicami L", lambda x: (
        f"{sum(len(r['probe']['L']) for r in x)} / {pr(x, 'full_q')} / "
        f"{sum(len(r['probe']['bad']) for r in x) - pr(x, 'full_q')}"))
    row("K0: opóźnienie wykrycia L po końcu klienta [ms] min / p50 / p99 / max", lambda x: (
        lambda v: " / ".join(f"{pct(v, q) / 1e6:.1f}" for q in (0, 50, 99, 100)) if v else "-")(
        [v for r in x for v in r["probe"]["L"]]), only_q=True)
    row("sonda: openat z sukcesem w wątku komunikacyjnym w oknach podłączeń na podłączenie / poza oknami", lambda x: (
        f"{pr(x, 'open_in_conn') / max(1, pr(x, 'n_conns')):.3f} / {pr(x, 'open_out_conn')}"))
    row("serie: niezakłócone / przepełnienia / zakłócone", lambda x: f"{len(ser(x, 'ok'))} / {len(ser(x, 'overflow'))} / "
        f"{len(ser(x, 'disturbed'))}")
    row("O5: powody zakłóceń", lambda x: "; ".join(sorted({sr['reason'] for sr in ser(x, 'disturbed')})) or "-")
    oq = [sr for sr in ser(Q, "ok")]
    row("O3: n^ komunikatów w chwili wykrycia p50 / średnio / max", lambda x: (
        lambda v: f"{pct(v, 50):.0f} / {np.mean(v):.0f} / {pct(v, 100):.0f}" if v else "-")([sr["n_hat"] for sr in oq]),
        only_q=True)
    row("O3: k porcji po P0: rozkład (k = 0, 1, ...) / średnio / serie graniczne", lambda x: (
        lambda v: (" / ".join(f"{np.mean(np.array(v) == j):.3f}" for j in range(max(v) + 1)) +
                   f"; {np.mean(v):.2f}; {sum(sr['boundary'] for sr in oq)}") if v else "-")([sr["k"] for sr in oq]),
        only_q=True)
    row("O3: P0 [µs] p50 / p99 / max", lambda x: dist([v for r in x for v in r["o3"]["p0"]]))
    row("O3: faza P0 po końcu slotu [µs] p5 / p50 / p95", lambda x: dist([v for r in x for v in r["o3"]["phase"]], (5, 50, 95)))
    row("O3: P1 w obrocie P0, od wyjścia z renameat [µs] p50 / p99 / max (aneks A1)",
        lambda x: dist([v for r in x for v in r["o3"]["p1"]]), only_q=True)
    row("O3: pełna porcja w osobnym obrocie (C' P1..Pk-1, D2s P2..Pk-1) [µs] p50 / p99 / max",
        lambda x: dist([v for r in x for v in r["o3"]["full"]]))
    row("O3: ostatnia porcja Pk [µs] p50 / p99 / max", lambda x: dist([v for r in x for v in r["o3"]["last"]]))
    row("O3: obrót Pk+1 [µs] p50 / p99 / max", lambda x: dist([v for r in x for v in r["o3"]["after"]]))
    row("O3: obrót bezczynny [µs] p50 / p99 / max", lambda x: dist(np.concatenate([r["idle_len"] for r in x])))
    row("O3: odstęp obrotów w serii [µs] p50 / p99 / max", lambda x: dist([v for r in x for v in r["o3"]["step"]]))
    row("O3: seria P0..Pk [ms] p50 / max", lambda x: (lambda v: f"{A.fmt_ms(pct(v, 50))} / {A.fmt_ms(pct(v, 100))}")(
        [v for r in x for v in r["o3"]["dur"]]))

    sd_of = lambda x: "Cp" if x is P else "D2s"  # noqa: E731
    e = {sd: E.mean_boot([len(sr["cluster"]["real"]) for sr in ser(x, "ok")], rng) for sd, x in (("Cp", P), ("D2s", Q))}
    row("opisowo E: sloty narażone na serię (95 % bootstrap)", lambda x: (lambda v: f"{v[0]:.3f} ({v[1]:.3f}..{v[2]:.3f})")(
        e[sd_of(x)]))
    ss = {sd: [sr["aff"] for sr in ser(x, "ok") if sr.get("aff") is not None] for sd, x in (("Cp", P), ("D2s", Q))}
    aff = {sd: E.aff_boot(v, rng) for sd, v in ss.items()}
    nxt = {sd: E.aff_boot(v, rng, "real_next", "pl_next") for sd, v in ss.items()}
    sm = {sd: E.mean_boot(E.series_s(v), rng) for sd, v in ss.items()}
    h0_s = E.mean_boot(E.series_s(h0), rng)
    h0_a = E.aff_boot(h0, rng)
    t = E.k2s_boot(E.series_s(ss["D2s"]), E.series_s(ss["Cp"]), rng)
    row("K2s: serie z placebo / sloty dotknięte na serię", lambda x: f"{len(ss[sd_of(x)])} / "
        f"{np.mean([len(c['real']) for c in ss[sd_of(x)]]) if ss[sd_of(x)] else float('nan'):.1f}")
    row("K2s: S = suma odchyleń slotów dotkniętych na serię ponad placebo [µs] (95 %)", lambda x: fmt_ci(sm[sd_of(x)], digits=1))
    row("K2s: Δ mediany slotów dotkniętych [µs] (95 %)", lambda x: (lambda a: f"{a[0][0] / 1e3:+.2f} "
        f"({a[1][0] / 1e3:+.2f}..{a[1][1] / 1e3:+.2f})")(aff[sd_of(x)]))
    row("opisowo: Δ mediany slotów następnych po oknach [µs] (95 %)", lambda x: (lambda a: f"{a[0][0] / 1e3:+.2f} "
        f"({a[1][0] / 1e3:+.2f}..{a[1][1] / 1e3:+.2f})")(nxt[sd_of(x)]))
    lines.append(f"| H0 K2s (syntetyczne serie D2s na tle C'): serie / S [µs] / Δ mediany [µs] | - | {len(h0)} / "
                 f"{fmt_ci(h0_s, digits=1)} / {h0_a[0][0] / 1e3:+.2f} ({h0_a[1][0] / 1e3:+.2f}..{h0_a[1][1] / 1e3:+.2f}) |")
    k2 = {sd: D.k2_summary([sr["cluster"] for sr in ser(x, "ok")], rng) for sd, x in (("Cp", P), ("D2s", Q))}
    row("opisowo K2a R603D Δ_c [µs]; n slotów; serie z narażeniem", lambda x: D.k2_fmt(k2[sd_of(x)], 0, 1e-3, "µs"))
    no4 = {sd: D.o4_cost([sr["cluster"] for sr in ser(x, "ok")]) for sd, x in (("Cp", P), ("D2s", Q))}
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

    v0 = k0_verdict(P, Q)
    lines.append(f"- **K0** (wykrycie przez sondę, {L_MIN_NS / 1e6:.0f} ms ≤ L ≤ {L_MAX_NS / 1e9:.3f} s): D2s porzuceń z "
                 f"wykryciem {sum(len(r['probe']['L']) for r in Q)}, z pełnej kolejki {pr(Q, 'full_q')}; C' wykryć "
                 f"{pr(P, 'det')}. Werdykt: **{v0}**.")
    kq, tq = k1_f(Q, P)
    kp, tp = k1_f(P, P)
    lq, eq = E.late_expected(Q)
    lp, ep = E.late_expected(P)
    lines.append(f"- **K1''** D2s: {tq}. Werdykt D2s (warunek (b)): **{kq}**. Warunek (a) opisowo: serii niegotowych przed "
                 f"startem następnego klienta {lq}, oczekiwanych {eq:.1f}; O6 {sum(len(r['o6']) for r in Q)}.")
    lines.append(f"- K1'' C' (opisowo, poprawiona klasyfikacja): {tp}. Werdykt C': {kp}. Warunek (a): {lp}, "
                 f"oczekiwanych {ep:.1f}; O6 {sum(len(r['o6']) for r in P)}.")
    half = (h0_s[2] - h0_s[1]) / 2 if not math.isnan(h0_s[1]) else np.nan
    reasons = []
    if not (not math.isnan(sm["Cp"][1]) and sm["Cp"][1] > 0):
        reasons.append(f"kontrola dodatnia: dolna granica S(C') {sm['Cp'][1] / 1e3:+.1f} µs ≤ 0")
    if not (not math.isnan(half) and half <= E.H0_HALF_MAX * sm["Cp"][0]):
        reasons.append(f"H0: półszerokość {half / 1e3:.1f} µs > {E.H0_HALF_MAX} · S(C') = "
                       f"{E.H0_HALF_MAX * sm['Cp'][0] / 1e3:.1f} µs")
    few = [sd for sd in SIDES if len(ss[sd]) < D.MIN_SERIES]
    if few:
        vs = "NIEROZSTRZYGNIĘTE (liczność: " + ", ".join(f"{NAMES[sd]} {len(ss[sd])}" for sd in few) + f" < {D.MIN_SERIES} serii)"
    elif reasons:
        vs = "NIEROZSTRZYGNIĘTE (miara: " + "; ".join(reasons) + ")"
    elif t["T"][2] < 0:
        vs = "ZDANE"
    elif t["T"][1] > 0:
        vs = "NIEZDANE"
    else:
        vs = "NIEROZSTRZYGNIĘTE (przedział T zawiera 0)"
    lines.append(f"- **K2s** (T = S(D2s) - {E.T_FACTOR} · S(C')): T {fmt_ci(t['T'], digits=1)} µs; S(D2s) "
                 f"{fmt_ci(sm['D2s'], digits=1)}, S(C') {fmt_ci(sm['Cp'], digits=1)} µs; S(D2s) - S(C') "
                 f"{fmt_ci(t['d'], digits=1)} µs; u_S {t['u'][0]:.2f} ({t['u'][1]:.2f}..{t['u'][2]:.2f}). Ważność: kontrola "
                 f"dodatnia {'tak' if not any(x.startswith('kontrola') for x in reasons) else 'NIE'}, H0 półszerokość "
                 f"{half / 1e3:.1f} µs wobec {E.H0_HALF_MAX * sm['Cp'][0] / 1e3:.1f} µs. Werdykt: **{vs}**.")
    lines += regress_lines(P, Q, [(k, lambda r, k=k, q=q: pct(r["ctl"][k], q), lab) for k, q, lab in (
        ("compute", 50, "compute_ns p50"), ("wake", 99, "wake_lag_ns p99"), ("e2e", 99, "e2e_ns p99"))], "K3")
    lines += regress_lines(P, Q, [("idle50", lambda r: pct(r["idle_len"], 50), "obrót bezczynny p50"),
                                  ("idle99", lambda r: pct(r["idle_len"], 99), "obrót bezczynny p99")], "K3t")
    lines.append("")
    ctx["verdicts"][fam] = {"K0": v0, "K1": kq, "K2s": vs, "K1p": kp}
    return lines


def run_dirs(fam_dir, side):
    return D.run_dirs(fam_dir, side)


def load_family(fam_dir, rngs):
    fam = fam_dir.name
    P = [analyze(d, rngs) for d in run_dirs(fam_dir, "Cp")]
    Q = [analyze(d, rngs) for d in run_dirs(fam_dir, "D2s")]
    for r in P + Q:
        if any(x != D.PORTIONS[fam] for x in r["k_mmap"]):
            die(f"{fam}: k z pojemności mmap {r['k_mmap']} różne od {D.PORTIONS[fam]} - przesłanka protokołu nie zachodzi")
    return P, Q


def h0_par(Q):
    par = D.h0_params(Q, 0)
    p1 = [v for r in Q for v in r["o3"].get("p1", [])]
    par["p1_ns"] = int(pct(p1, 50)) if p1 else par["w_ns"]
    ks = [sr["k"] for sr in ser(Q, "ok")]
    return par, ks


def main_report(raw, seed, out):
    rngs = D.rng_set(seed)
    ctx = {"verdicts": {}}
    report = ["# R603F - wynik", "", f"Źródło: `{raw.name}`, ziarna: placebo {seed}, bootstrap {seed + 1}, H0 {seed + 2}, "
              f"pseudo-zdarzenia {seed + 3}.", ""]
    for fam_dir in sorted(p for p in raw.iterdir() if p.is_dir()):
        fam = fam_dir.name
        P, Q = load_family(fam_dir, rngs)
        par, ks = h0_par(Q)
        h0 = h0_d2s(P, par, ks, rngs["h0"])
        report += [f"Parametry H0 K2s {fam} (z D2s): P0 {par['p0_ns'] / 1e3:.1f} µs, porcja {par['w_ns'] / 1e3:.1f} µs, obrót "
                   f"{par['turn_ns'] / 1e3:.1f} µs, faza {par['phase'][0] / 1e3:.0f}..{par['phase'][1] / 1e3:.0f} µs, "
                   f"rozrzut {par['jitter_ns'] / 1e3:.0f} µs, P1 w obrocie P0 {par['p1_ns'] / 1e3:.1f} µs, k z {len(ks)} "
                   f"serii D2s.", ""]
        report += family_report(fam, P, Q, h0, rngs, ctx)
    report += ["## Werdykty", "", "| rodzina | K0 | K1'' D2s (b) | K2s | K1'' C' (b, opisowo) |", "|---|---|---|---|---|"]
    for fam, v in ctx["verdicts"].items():
        report.append(f"| {fam} | {v['K0']} | {v['K1']} | {v['K2s']} | {v['K1p']} |")
    text = "\n".join(report) + "\n"
    if out:
        out.write_text(text)
    print(text)


# ---------------------------------------------------------------- bramki suchego przebiegu

def gate_h(runs):
    """Bramka H (aneks 1 R603D) dla stron C' i D2s."""
    out = []
    for side in SIDES:
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


def g2f(r, p99, p999):
    """G2f (D2s, aneksy A1 i A2): pelne porcje w osobnych obrotach (P2..Pk-1) > p99,9 obrotu bezczynnego i obroty Pk+1
    <= p99, po >= 99 %, w niezakloconych seriach niegranicznych z k >= 1; serie z k = 0 osobno (obrot po P0 > p99)."""
    ts, te = r["turns"]
    full, after, k0_long, k0_n = [], [], 0, 0
    for sr in ser([r], "ok"):
        if sr["boundary"] or "after" not in sr:
            continue
        a_ok = int(te[sr["after"]] - ts[sr["after"]]) <= p99
        if sr["k"] == 0:
            k0_n += 1
            k0_long += not a_ok
            continue
        full += [int(te[j] - ts[j]) > p999 for j in sr["turns"][:-1]]
        after.append(a_ok)
    ff = sum(full) / len(full) if full else np.nan
    fa = sum(after) / len(after) if after else np.nan
    ok = (not after or fa >= E.G2_FRAC) and (not full or ff >= E.G2_FRAC)
    txt = (f"pełne porcje > p99,9 bezczynnego {sum(full)}/{len(full)} ({ff:.3f}), Pk+1 ≤ p99 w seriach z k ≥ 1 "
           f"{sum(after)}/{len(after)} ({fa:.3f}), osobno serie z k = 0: obrót po P0 > p99 w {k0_long} z {k0_n}, serie "
           f"graniczne {sum(sr['boundary'] for sr in ser([r], 'ok'))}")
    return ok, txt


def gates(raw):
    rngs = D.rng_set(6034)
    ok_all = True
    for fam_dir in sorted(p for p in raw.iterdir() if p.is_dir()):
        fam = fam_dir.name
        runs = [analyze(d, rngs) for side in SIDES for d in run_dirs(fam_dir, side)]
        P = [r for r in runs if r["side"] == "Cp"]
        print(f"## {fam} (k C' = {D.PORTIONS[fam]}, H = {D.H[fam]})")
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
            dist_txt = (f"obrót bezczynny p50 / p99 / p99,9 / max {fmt_us(pct(idle, 50))} / {fmt_us(p99)} / {fmt_us(p999)} / "
                        f"{fmt_us(pct(idle, 100))} µs (n = {len(idle)}); pełna porcja p50 / min "
                        f"{fmt_us(pct(r['o3']['full'], 50))} / {fmt_us(pct(r['o3']['full'], 0))} µs; Pk+1 p50 / max "
                        f"{fmt_us(pct(r['o3']['after'], 50))} / {fmt_us(pct(r['o3']['after'], 100))} µs; zakłócone "
                        f"{len(ser([r], 'disturbed'))} ({'; '.join(sorted({sr['reason'] for sr in ser([r], 'disturbed')})) or '-'})")
            if r["side"] == "Cp":
                good, need = 0, [sr for sr in sers if sr.get("turns")]
                for sr in need:
                    lens = [int(te[j] - ts[j]) for j in sr["turns"]]
                    good += all(v > p999 for v in lens[:-1]) and int(te[sr["after"]] - ts[sr["after"]]) <= p99
                g2 = len(need) > 0 and good == len(need)
                print(f"  G2 {'OK' if g2 else 'NIE'} (C', jak R603D): serii niezakłóconych {len(sers)} (z obrotami "
                      f"{len(need)}), spełnia oba warunki {good}; {dist_txt}")
            else:
                g2, txt = g2f(r, p99, p999)
                ks = [sr["k"] for sr in sers]
                print(f"  G2f {'OK' if g2 else 'NIE'}: {txt}; k w seriach {sorted(set(ks))} (średnio "
                      f"{np.mean(ks) if ks else float('nan'):.2f}); {dist_txt}")
            ok_all &= g2
            v, txt = k1_f([r], P if r["side"] == "D2s" else [r])
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
            pb = r["probe"]
            if r["side"] == "D2s":
                g6 = not pb["bad"] and pb["full_q"] == 0 and len(pb["L"]) > 0
                Ls = pb["L"]
                print(f"  G6 {'OK' if g6 else 'NIE'}: porzuceń z wykryciem {len(Ls)} (L min / p50 / max "
                      f"{(pct(Ls, 0) / 1e6) if Ls else float('nan'):.1f} / {(pct(Ls, 50) / 1e6) if Ls else float('nan'):.1f} / "
                      f"{(pct(Ls, 100) / 1e6) if Ls else float('nan'):.1f} ms), z pełnej kolejki {pb['full_q']}, poza "
                      f"granicami {len(pb['bad']) - pb['full_q']}, samotnych wykryć {pb['lone']}, openat z sukcesem w oknach "
                      f"podłączeń {pb['open_in_conn']} / poza {pb['open_out_conn']}")
            else:
                g6 = pb["det"] == 0
                print(f"  G6 {'OK' if g6 else 'NIE'} (C'): wykryć przez sondę {pb['det']}, samotnych {pb['lone']}, openat z "
                      f"sukcesem w oknach podłączeń {pb['open_in_conn']} / poza {pb['open_out_conn']}")
            ok_all &= g6
        for side, h, order, meds, ok, exact in gate_h(runs):
            print(f"- H {side}: {'OK' if ok else 'NIE'}: najmniejsze mediany |Δ compute| przy h = {order} ({meds} µs); "
                  f"argmin {'=' if exact else '≠'} H = {h}")
            ok_all &= ok
        print()
    print("BRAMKI: " + ("wszystkie spełnione" if ok_all else "CO NAJMNIEJ JEDNA NIESPEŁNIONA - decyzja człowieka"))
    return ok_all


# ---------------------------------------------------------------- test parsera na danych R603E

# Decyzje czlowieka po wyniku R603E, punkt 1: uc06 po zaliczeniu obu zdarzen martwego muteksu do wylaczen.
EXPECTED_K1_UC06 = {
    "Cpp": ("- **K1''** C'': do puli 265 z 270 (wyłączenia 5: martwy muteks 5, niezebrany 0), pary w fazie pracy niewyjaśnione 0, "
            "zwolnienia bez puli niewyjaśnione 0,", "spójność ogona tak", "Werdykt C'' (warunek (b)): **ZDANE**"),
    "Cp": ("- K1' C' (opisowo, powtórzenie R603D, werdykt z (b)): do puli 265 z 270 (wyłączenia 5: martwy muteks 5, niezebrany 0), "
           "pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0,", "spójność ogona tak", "Werdykt C': ZDANE")}


def parser_check(raw):
    bad = 0
    # 1. Raport R603E z poprawiona klasyfikacja = wynik.md R603E poza K1'' / K1' uc06 i wierszem uc06 Werdyktow.
    wynik = (HERE.parent / "results_20261106_R603E" / "wynik.md").read_text()
    ref = wynik.split("## Wydruk analizy\n", 1)[1].split("\n## ", 1)[0].strip("\n")
    tmp = io.StringIO()
    with contextlib.redirect_stdout(tmp):
        E.main_report(raw, 6034, None)
    out = tmp.getvalue().rstrip("\n").split("\n")[1:]
    got = "\n".join(("#" + l) if l.startswith("#") else l for l in out).strip("\n")
    rl, gl = ref.split("\n"), got.split("\n")
    diffs = [(i, a, b) for i, (a, b) in enumerate(zip(rl, gl)) if a != b]
    sec = {}
    cur = None
    for i, l in enumerate(rl):
        if l.startswith("### "):
            cur = l[4:]
        sec[i] = cur
    allowed = 0
    for i, a, b in diffs:
        if sec[i] == "uc06" and b.startswith("- **K1''** C'':"):
            ok = all(x in b for x in EXPECTED_K1_UC06["Cpp"])
        elif sec[i] == "uc06" and b.startswith("- K1' C'"):
            ok = all(x in b for x in EXPECTED_K1_UC06["Cp"])
        elif sec[i] == "Werdykty" and b.startswith("| uc06 |"):
            ok = b.startswith("| uc06 | ZDANE |") and b.endswith("| ZDANE |")
        else:
            ok = False
        allowed += ok
        print(f"   różnica w wierszu {i + 1} ({sec[i]}) - {'oczekiwana' if ok else 'NIEOCZEKIWANA'}:\n     wynik.md: {a}\n"
              f"     teraz:    {b}")
    nd = len(diffs) + abs(len(rl) - len(gl))
    ok1 = len(rl) == len(gl) and nd == 3 and allowed == 3
    print(f"1. raport R603E z poprawioną klasyfikacją martwego muteksu wobec wynik.md R603E: {len(gl)} wierszy, różnic {nd}, "
          f"oczekiwanych {allowed} z 3 - {'OK' if ok1 else 'NIE'}")
    bad += not ok1

    # 2. Kontrola ujemna: na danych R603E brak wykryc przez sonde, okna R_C = kill_windows R603C.
    n_runs, det, lone, neq = 0, 0, 0, 0
    for fam_dir in sorted(p for p in raw.iterdir() if p.is_dir()):
        for run_dir in sorted(p for p in fam_dir.iterdir() if p.is_dir()):
            events = A.parse_trace(run_dir / "trace.txt")
            rt = A.rt_tids(run_dir / "rt.txt")
            conns = A.load_conns(run_dir / "conns.tsv")
            cls = classify_kills(events, conns, rt)
            det += sum(len(x["det"]) for x in cls)
            lone += sum(len(x["lone"]) for x in cls)
            new = kill_windows_f(events, conns, rt)
            old = _KW_R603C(events, conns, rt)
            for a, b in zip(new, old):
                if a is None or b is None:
                    neq += (a is None) != (b is None)
                    continue
                neq += {k: v for k, v in a.items() if k != "t_det"} != b
            n_runs += 1
    ok2 = n_runs > 0 and det == 0 and neq == 0
    print(f"2. kontrola ujemna na {n_runs} przebiegach R603E: wykryć przez sondę {det}, samotnych {lone}, okien R_C różnych od "
          f"kill_windows R603C {neq} - {'OK' if ok2 else 'NIE'}")
    bad += not ok2
    print(f"parser-check: {'ZDANY' if bad == 0 else f'NIEZDANY ({bad} punktów)'}")
    return bad == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--seed", type=int, default=6034)
    ap.add_argument("--parser-check", action="store_true", help="--raw wskazuje surowe dane R603E")
    ap.add_argument("--gates", action="store_true", help="--raw wskazuje suchy przebieg R603F")
    args = ap.parse_args()
    if args.parser_check:
        sys.exit(0 if parser_check(args.raw) else 2)
    if args.gates:
        sys.exit(0 if gates(args.raw) else 2)
    main_report(args.raw, args.seed, args.out)


if __name__ == "__main__":
    main()
