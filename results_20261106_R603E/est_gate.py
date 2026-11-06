"""R603E, Ustalenia przed pomiarem, punkt 1. Uzycie: est_gate.py SUROWE_R603D (uklad <rodzina>/<strona>_<para>/).

Szacunek przed R603E na surowych danych R603D (strona Cp): co bramka C'' przepuscilaby i jaki jest
koszt slotu NASTEPNEGO po porcji, ktora go nie naklada. Wypisuje tylko liczby wyprowadzone."""

import importlib.util
import sys
from pathlib import Path

import numpy as np

R603D = Path(__file__).resolve().parent.parent / "results_20261105_R603D"
spec = importlib.util.spec_from_file_location("an", R603D / "analyze.py")
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)

RES_PORTION = 200_000
RES_P0 = 500_000
BOOT = 2000


def gate_open(m, t, reserve):
    """Bramka C'' w chwili t: termin = najblizszy przyszly termin, o ile poprzedni slot juz sie skonczyl."""
    j = int(np.searchsorted(m.dl, t, side="right"))  # pierwszy slot z dl > t
    if j >= len(m.dl):
        return False, j
    if j > 0 and m.end[j - 1] > t:
        return False, j  # slot j-1 jeszcze liczy (albo nadrabianie): opublikowany termin w przeszlosci
    return t + reserve < m.dl[j], j


def next_dev(m, j):
    return float(m.comp[j] - m.base[m.cls[j]])


def per_run(run_dir, rngs):
    r = D.analyze_run(run_dir, rngs)
    m = r["model"]
    step = m.h * m.period
    out = {"open_p": 0, "all_p": 0, "open_p0": 0, "all_p0": 0, "series": []}
    for sr in r["series"]:
        if sr["kind"] != "ok":
            continue
        ok0, _ = gate_open(m, sr["p0"][0], RES_P0)
        out["all_p0"] += 1
        out["open_p0"] += ok0
        real, pl, overlap, seen = [], [], 0, set()
        wins = sr["windows"][1:]
        for a, b in wins:
            ok, j = gate_open(m, a, RES_PORTION)
            out["all_p"] += 1
            if not ok:
                continue
            out["open_p"] += 1
            if b >= m.t_on[j]:
                overlap += 1  # porcja dluzsza niz rezerwa: naklada sie mimo bramki
                continue
            if j not in seen:
                seen.add(j)
                real.append(next_dev(m, j))
        # placebo: cala seria przesunieta o m*H*takt, slot nastepny po oknach, ktore bramka by przepuscila
        span = (m.dl[0] - wins[0][0], m.dl[-1] - wins[-1][1]) if wins else (0, 0)
        lo_m, hi_m = int(np.ceil(span[0] / step)), int(np.floor(span[1] / step))
        copies = []
        for _ in range(200):
            if len(copies) == 20 or hi_m <= lo_m or not wins:
                break
            mm = int(rngs["placebo"].integers(lo_m, hi_m + 1))
            if mm == 0:
                continue
            c, bad, seen2 = [], False, set()
            for a, b in wins:
                a2, b2 = a + mm * step, b + mm * step
                ok, j = gate_open(m, a2, RES_PORTION)
                if not ok or b2 >= m.t_on[j]:
                    continue
                if not m.ctl[j]:
                    bad = True
                    break
                if j not in seen2:
                    seen2.add(j)
                    c.append(next_dev(m, j))
            if not bad:
                copies.append(c)
        out["series"].append({"real": real, "pl": copies, "overlap": overlap, "n_win": len(wins)})
    return out


def stat(ss):
    real = np.array([x for s in ss for x in s["real"]])
    pl = np.array([x for s in ss for c in s["pl"] for x in c])
    if not len(real) or not len(pl):
        return np.nan, np.nan
    dmed = np.median(real) - np.median(pl)
    per = [sum(s["real"]) - (np.mean([sum(c) for c in s["pl"]]) if s["pl"] else 0.0) for s in ss]
    return dmed, float(np.mean(per))


def main(raw):
    rngs = D.rng_set(6034)
    boot = np.random.default_rng(6035)
    for fam_dir in sorted(p for p in Path(raw).iterdir() if p.is_dir()):
        runs = [per_run(d, rngs) for d in D.run_dirs(fam_dir, "Cp")]
        ss = [s for r in runs for s in r["series"] if s["pl"]]
        op = sum(r["open_p"] for r in runs) / max(1, sum(r["all_p"] for r in runs))
        o0 = sum(r["open_p0"] for r in runs) / max(1, sum(r["all_p0"] for r in runs))
        ov = sum(s["overlap"] for s in ss)
        nreal = sum(len(s["real"]) for s in ss)
        dmed, dsum = stat(ss)
        b = np.array([stat([ss[i] for i in boot.integers(0, len(ss), len(ss))]) for _ in range(BOOT)])
        lo, hi = np.nanpercentile(b, [2.5, 97.5], axis=0)
        print(f"{fam_dir.name}: bramka otwarta porcja {op:.3f}, P0 {o0:.3f}; serii {len(ss)}, "
              f"slotow nastepnych (unikalnych) {nreal}, z nakladaniem mimo bramki {ov}; "
              f"slot nastepny: Δ mediany {dmed / 1e3:+.2f} us ({lo[0] / 1e3:+.2f}..{hi[0] / 1e3:+.2f}), "
              f"suma na serie ponad placebo {dsum / 1e3:+.1f} us ({lo[1] / 1e3:+.1f}..{hi[1] / 1e3:+.1f})")


if __name__ == "__main__":
    main(sys.argv[1])
