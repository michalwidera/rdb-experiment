#!/usr/bin/env python3
"""R376b: analiza przebiegow run_one.py R376 wedlug kryteriow z README.md (metryka G).

Uzycie: analyze.py --raw KATALOG [--out RAPORT.md] [--seed 3762] [--conns 60]
KATALOG ma uklad <rodzina>/<strona>_<para>/ jak w R376. Funkcje przypisania podlaczenia do slotu,
okna zwolnienia, pseudo-zdarzen i testow pochodza bez zmian z ../results_20261104_R376/analyze.py;
dla kazdej rodziny drukowany jest najpierw jej raport R376 (kryterium R376 na wszystkich zdarzeniach,
opisowo), potem metryka G z werdyktem. Rodziny i generator losowan jak w R376, wiec na surowych
danych R376 (--seed 376 --conns 30) czesc R376 wydruku jest identyczna z wydrukiem R376.
Kod wyjscia: 0 - raport zapisany, 2 - blad danych.
Wymaga NumPy (np. retractordb/.venv-python).
"""

import argparse
import importlib.util
import json
import math
from pathlib import Path

import numpy as np

_spec = importlib.util.spec_from_file_location(
    "r376", Path(__file__).resolve().parent.parent / "results_20261104_R376" / "analyze.py")
r376 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(r376)
pct, fmt_ms, boot_p99, mw = r376.pct, r376.fmt_ms, r376.boot_p99, r376.mann_whitney_greater

# Sumy binarek z meta.json przebiegow uc05 R376 (README, Strony porownania).
WANT = {
    "A": ("6e84c5497ecab47717ec4bf88491f578c0c9e3ec65213160c7f19fb0901a432d",
          "2f6004834740f006ef019dc65ebb25fc6cb27453bf02fedb1adbe765dace5f05"),
    "B": ("d01c95d5888e9c2bf01b1d400fab10e399bb2a13cb9e4a559661bc0aa33e6bd5",
          "6bfdb5ee2b844f69ff88771e0c3f37a0fea9dac5ee533975a2fe3f6497e4da8d"),
}
MIN_RUNS = 8
MIN_HIT = 100
# Wartosci R376 dla uc05 (results_20261104_R376/wynik.md) - do odtwarzalnosci, opisowo.
R376_G_P99 = {"A": 11.055, "B": 1.254}
R376_P50 = {"A": 9.873, "B": 1.024}
R376_EXCESS_B = 0.105


def validity(run_dir, conns):
    """Powody niewaznosci przebiegu (pusta lista = wazny), README, Waznosc przebiegu."""
    if not (run_dir / "meta.json").exists():
        return ["brak meta.json"]
    meta = json.loads((run_dir / "meta.json").read_text())
    side, why = meta.get("side"), []
    if not meta.get("rt_ok"):
        why.append("rt_ok=false")
    if meta.get("governor") != "performance":
        why.append(f"governor={meta.get('governor')}")
    if meta.get("conns") != conns:
        why.append(f"conns={meta.get('conns')}")
    if side not in WANT or meta.get("xretractor_sha256") != meta.get("build_xretractor_sha256") \
            or (meta.get("xretractor_sha256"), meta.get("xqry_sha256")) != WANT[side]:
        why.append("sumy binarek")
    fifo = [l.split("\t") for l in (run_dir / "rt.txt").read_text().splitlines() if "policy=SCHED_FIFO" in l]
    if not fifo or any(f[-1].strip() != "3" for f in fifo):
        why.append("watek SCHED_FIFO poza rdzeniem 3")
    rows = [l.split("\t") for l in (run_dir / "conns.tsv").read_text().splitlines()[1:]]
    if len(rows) != conns or any(r[4].startswith(("no_row", "killed")) for r in rows):
        why.append("klient bez wiersza")
    return why


def g_report(runs, seed):
    """Metryka glowna G: zdarzenia bez slotu w oknie zwolnienia kolejki (regula on_release R376)."""
    lines = ["### Metryka główna G (bez zdarzeń na zwolnieniu)", ""]
    g, allh, pseudo, excl = {}, {}, {}, {}
    for s in "AB":
        ev = [e for r in runs if r["meta"]["side"] == s for e in r["events"] if e["max_e2e"] is not None]
        allh[s] = [e["max_e2e"] for e in ev]
        g[s] = [e["max_e2e"] for e in ev if not e["on_release"]]
        excl[s] = len(allh[s]) - len(g[s])
        pseudo[s] = [x for r in runs if r["meta"]["side"] == s for x in r["pseudo"]]
    # Osobny generator, jak eksploracja R376: przy --seed 376 G odtwarza jej przedzialy.
    rng = np.random.default_rng(seed)
    p99, stable, ci = {}, {}, {}
    for s in "AB":
        p99[s] = pct(g[s], 99)
        if len(g[s]) >= MIN_HIT:
            lo, hi = boot_p99(g[s], rng)
            ci[s] = (lo, hi)
            stable[s] = (hi - lo) / 2 <= 0.10 * p99[s]
    lines += ["| wielkość [ms] | A | B |", "|---|---|---|"]

    def row(label, fa, fb):
        lines.append(f"| {label} | {fa} | {fb} |")

    row("zdarzenia z przypisanym slotem / na zwolnieniu (wyłączone)", *(f"{len(allh[s])} / {excl[s]}" for s in "AB"))
    row("G: n_hit", *(str(len(g[s])) for s in "AB"))
    row("G: p50 / max", *(f"{fmt_ms(pct(g[s], 50))} / {fmt_ms(pct(g[s], 100))}" for s in "AB"))
    row("G: p99 [CI 95 %]", *(
        f"{fmt_ms(p99[s])} [{fmt_ms(ci[s][0])}, {fmt_ms(ci[s][1])}] {'stabilne' if stable[s] else 'NIESTABILNE'}"
        if s in ci else f"{fmt_ms(p99[s])}, n_hit < {MIN_HIT}" for s in "AB"))
    row("G: p50 - p50 pseudo-zdarzeń tej strony (skala efektu)",
        *(fmt_ms(pct(g[s], 50) - pct(pseudo[s], 50)) if g[s] and pseudo[s] else "-" for s in "AB"))
    lines.append("")

    p_ab = mw(g["A"], g["B"])
    p_res = mw(g["B"], pseudo["B"])
    lines.append(f"- Mann-Whitney G A > B: p = {p_ab:.3g}; G B > pseudo-zdarzenia B (ryzyko szczątkowe): "
                 f"p = {p_res:.3g}, mediana G B - mediana pseudo B = "
                 f"{fmt_ms(pct(g['B'], 50) - pct(pseudo['B'], 50)) if g['B'] and pseudo['B'] else '-'} ms.")

    # Kolejnosc rozstrzygniec (README, Aneksy, A1): brak efektu w kierunku albo w tescie przesadza,
    # potem stabilnosc i licznosc, potem kontrola aparatury.
    nruns = {s: sum(r["meta"]["side"] == s for r in runs) for s in "AB"}
    ctl_ok, ctl_txt = True, []
    for key, label in (("compute", "compute_ns p50"), ("wake", "wake_lag_ns p99")):
        q = 50 if key == "compute" else 99
        a = [x for x in (pct(r["ctl"][key], q) for r in runs if r["meta"]["side"] == "A") if not math.isnan(x)]
        b = [x for x in (pct(r["ctl"][key], q) for r in runs if r["meta"]["side"] == "B") if not math.isnan(x)]
        if not (a and b):
            ctl_ok = False
            ctl_txt.append(f"{label}: nie do oceny")
            continue
        diff = float(np.median(a) - np.median(b))
        ok = abs(diff) <= max(max(a) - min(a), max(b) - min(b))
        ctl_ok &= ok
        ctl_txt.append(f"{label}: {'w szumie' if ok else 'POZA SZUMEM'}")
    if p_ab >= 0.01 or not p99["B"] < p99["A"]:
        verdict = "NIEPOTWIERDZONY"
    elif min(nruns.values()) < MIN_RUNS or len(ci) < 2 or not all(stable.values()):
        verdict = "NIEROZSTRZYGNIĘTY"
    elif not ctl_ok:
        verdict = "NIEROZSTRZYGNIĘTY (kontrola aparatury wstrzymuje wniosek)"
    else:
        verdict = "POTWIERDZONY"
    why = []
    if min(nruns.values()) < MIN_RUNS:
        why.append(f"ważne przebiegi A / B = {nruns['A']} / {nruns['B']} < {MIN_RUNS}")
    why += [f"n_hit {s} < {MIN_HIT}" for s in "AB" if s not in ci]
    why += [f"p99 {s} niestabilne" for s in "AB" if s in ci and not stable[s]]
    lines.append(f"- Kontrola aparatury (z wydruku R376 wyżej): {'; '.join(ctl_txt)}.")
    lines.append(f"- **Efekt #283 w uc05 według G: {verdict}**"
                 f" (p99 B {'<' if p99['B'] < p99['A'] else '≥'} p99 A, MW p {'<' if p_ab < 0.01 else '≥'} 0.01"
                 f"{'; ' + '; '.join(why) if why else ''}).")
    lines.append(f"- Odtwarzalność R376 (opisowo): G p99 A / B = {fmt_ms(p99['A'])} / {fmt_ms(p99['B'])} wobec "
                 f"{R376_G_P99['A']:.3f} / {R376_G_P99['B']:.3f}; p50 wszystkich zdarzeń A / B = "
                 f"{fmt_ms(pct(allh['A'], 50))} / {fmt_ms(pct(allh['B'], 50))} wobec "
                 f"{R376_P50['A']:.3f} / {R376_P50['B']:.3f}; nadmiar B (wszystkie zdarzenia) = "
                 f"{fmt_ms(pct(allh['B'], 50) - pct(pseudo['B'], 50)) if allh['B'] and pseudo['B'] else '-'} "
                 f"wobec {R376_EXCESS_B:.3f} ms.")
    lines.append("")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--seed", type=int, default=3762)
    ap.add_argument("--conns", type=int, default=60)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    report = ["# R376b - wynik", "", f"Źródło: `{args.raw.name}`, bootstrap {r376.BOOTSTRAP} losowań, ziarno {args.seed}, "
              f"{args.conns} podłączeń na przebieg.", ""]
    for fam_dir in sorted(p for p in args.raw.iterdir() if p.is_dir()):
        dirs = sorted(p for p in fam_dir.iterdir() if p.is_dir())
        bad = {d.name: validity(d, args.conns) for d in dirs}
        bad = {k: v for k, v in bad.items() if v}
        runs = [r376.analyze_run(d, rng) for d in dirs if d.name not in bad]
        if not runs:
            continue
        report += r376.family_report(fam_dir.name, runs, rng)
        bad_txt = "; ".join(k + ": " + ", ".join(v) for k, v in bad.items()) if bad else "brak"
        report.append(f"- Przebiegi nieważne (wyłączone, bez powtórzenia): {bad_txt}.")
        report.append("")
        report += g_report(runs, args.seed)
    text = "\n".join(report) + "\n"
    if args.out:
        args.out.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
