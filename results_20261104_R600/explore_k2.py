#!/usr/bin/env python3
"""R600 - eksploracja po pomiarze (poza kryteriami README): skad bierze sie resztka K2 w B.

Kryterium K2 bierze max e2e_ns wszystkich slotow, ktore zachodza na okno zwolnienia R. Tu sloty
dzieli sie na dwie grupy, bo #600 chroni tylko druga z nich:
  - slot trwajacy, gdy zwolnienie ruszylo (deadline < poczatek R <= koniec slotu) - zwykle slot,
    ktory kolejke porzucil i sam wykonuje dodatkowa prace porzucenia;
  - sloty obudzone w trakcie zwolnienia (poczatek R <= deadline <= koniec R).
Dla drugiej grupy: test MW wobec pseudo-zdarzen zwolnienia z analyze.py (te same ziarna 600/601),
odsetek okien ze slotem dluzszym od taktu oraz wake_lag_ns i compute_ns wobec slotow kontrolnych.
Takt = mediana odstepu kolejnych deadline_ns.

Uzycie: python3 -I explore_k2.py --raw <raw> [rodzina ...]
"""
import argparse
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import analyze as az  # noqa: E402


def fmt(a):
    if not a:
        return "n=0"
    p99 = f"{np.percentile(a, 99) / 1e6:.3f}" if len(a) >= az.MIN_N else "-"
    return f"n={len(a)} p50={np.median(a) / 1e6:.3f} p99={p99} max={max(a) / 1e6:.3f} ms"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, type=pathlib.Path)
    ap.add_argument("families", nargs="*", default=["uc03", "uc05", "uc06"])
    args = ap.parse_args()
    for fam in args.families:
        for side in "AB":
            rng, rng_rel = np.random.default_rng(600), np.random.default_rng(601)
            ongoing, woken, pseudo = [], [], []
            wk = {"wake": [], "compute": []}
            ctl = {"wake": [], "compute": []}
            period = None
            for rd in sorted((args.raw / fam).glob(f"{side}_??")):
                r = az.analyze_run(rd, rng, rng_rel)
                pseudo += r["rel_pseudo"]
                for k in ctl:
                    ctl[k] += r["ctl"][k].tolist()
                rows = [l.split("\t") for l in (rd / "conns.tsv").read_text().splitlines()[1:]]
                conns = [(int(x[1]), int(x[3])) for x in rows]
                wins = az.windows_for_run(az.parse_trace(rd / "trace.txt"), conns, az.rt_tids(rd / "rt.txt"))
                s = az.load_slots(rd / "slots.csv")
                dl, end = s["deadline"], s["deadline"] + s["e2e"]
                period = int(np.median(np.diff(dl)))
                for _, rel in wins:
                    if rel is None:
                        continue
                    m_on = (dl < rel[0]) & (end >= rel[0])
                    m_wk = (dl >= rel[0]) & (dl <= rel[1])
                    if m_on.any():
                        ongoing.append(int(s["e2e"][m_on].max()))
                    if m_wk.any():
                        woken.append(int(s["e2e"][m_wk].max()))
                        for k in wk:
                            wk[k] += s[k][m_wk].tolist()
            over = lambda a: f"{np.mean(np.array(a) > period) * 100:.1f} %" if a else "-"
            p = az.mann_whitney_greater(woken, pseudo) if woken else float("nan")
            print(f"## {fam} {side} (takt {period / 1e6:.3f} ms)")
            print(f"- slot trwajacy przy starcie zwolnienia: {fmt(ongoing)}")
            print(f"- sloty obudzone w trakcie zwolnienia:   {fmt(woken)}; > takt {over(woken)}; MW > pseudo p = {p:.3g}")
            print(f"- pseudo-zdarzenia zwolnienia:           {fmt(pseudo)}; > takt {over(pseudo)}")
            for k in ("wake", "compute"):
                if wk[k]:
                    print(f"- {k} obudzonych p50 / p99: {np.median(wk[k]) / 1e3:.1f} / {np.percentile(wk[k], 99) / 1e3:.1f} us"
                          f" (kontrola {np.median(ctl[k]) / 1e3:.1f} / {np.percentile(ctl[k], 99) / 1e3:.1f} us)")
            print()


if __name__ == "__main__":
    main()
