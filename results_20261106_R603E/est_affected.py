"""R603E, Ustalenia przed pomiarem, punkt 3. Uzycie: est_affected.py SUROWE_R603D.

Koszt serii C' (R603D) na mierze 'sloty dotkniete' = narazone (definicja R603D) + slot nastepny po kazdym oknie
serii; placebo jak R603D (kopie przesuniete o m*H*takt, sloty kontrolne). Tylko liczby wyprowadzone."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import est_gate as E
D = E.D

def affected(m, wins):
    idx = set(int(x) for x in m.exposed(wins))
    for a, b in wins:
        j = int(np.searchsorted(m.t_on, b, side="right"))
        if j < len(m.dl): idx.add(j)
    return np.array(sorted(idx), dtype=np.int64)

def run(raw):
    rngs = D.rng_set(6034); boot = np.random.default_rng(6035)
    for fam_dir in sorted(p for p in Path(raw).iterdir() if p.is_dir()):
        out = {}
        for side in ("C", "Cp"):
            ss = []
            for d in D.run_dirs(fam_dir, side):
                r = D.analyze_run(d, rngs); m = r["model"]; step = m.h * m.period
                for sr in r["series"]:
                    if sr["kind"] != "ok": continue
                    w = sr["windows"]; idx = affected(m, w)
                    real = (m.comp[idx] - m.base[m.cls[idx]]).astype(float)
                    span = (m.dl[0] - w[0][0], m.dl[-1] - w[-1][1])
                    lo_m, hi_m = int(np.ceil(span[0] / step)), int(np.floor(span[1] / step))
                    copies = []
                    for _ in range(200):
                        if len(copies) == 20 or hi_m <= lo_m: break
                        mm = int(rngs["placebo"].integers(lo_m, hi_m + 1))
                        if mm == 0: continue
                        k = affected(m, [(a + mm * step, b + mm * step) for a, b in w])
                        if len(k) and m.ctl[k].all():
                            copies.append(list((m.comp[k] - m.base[m.cls[k]]).astype(float)))
                    if copies: ss.append({"real": list(real), "pl": copies})
            dmed, dsum = E.stat(ss)
            b = np.array([E.stat([ss[i] for i in boot.integers(0, len(ss), len(ss))]) for _ in range(E.BOOT)])
            lo, hi = np.nanpercentile(b, [2.5, 97.5], axis=0)
            nsl = np.mean([len(s["real"]) for s in ss])
            out[side] = f"{side}: serii {len(ss)}, slotow dotknietych na serie {nsl:.1f}, Δ mediany {dmed/1e3:+.2f} ({lo[0]/1e3:+.2f}..{hi[0]/1e3:+.2f}) us, suma na serie {dsum/1e3:+.1f} ({lo[1]/1e3:+.1f}..{hi[1]/1e3:+.1f}) us"
        print(fam_dir.name, "|", out["C"], "|", out["Cp"])

run(sys.argv[1])
