"""R603E, Ustalenia przed pomiarem, punkt 2. Uzycie: est_gate_h0.py SUROWE_R603D.

H0 dla estymatora 'slot nastepny po porcji przepuszczonej przez bramke C''': syntetyczne serie porcji
(parametry C' z R603D, h0_params) na tle strony C, w czasie kontrolnym. Tylko liczby wyprowadzone."""
import importlib.util, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import est_gate as E
D = E.D

def run(raw):
    rngs = D.rng_set(6034)
    boot = np.random.default_rng(6035)
    for fam_dir in sorted(p for p in Path(raw).iterdir() if p.is_dir()):
        fam = fam_dir.name
        cp = [D.analyze_run(d, rngs) for d in D.run_dirs(fam_dir, "Cp")]
        par = D.h0_params(cp, D.PORTIONS[fam])
        ss = []
        for d in D.run_dirs(fam_dir, "C"):
            r = D.analyze_run(d, rngs)
            m = r["model"]
            n = len([s for s in r["series"] if s["kind"] == "ok"])
            for _ in range(n):
                wins = m.h0_windows(rngs["h0"], D.PORTIONS[fam], par)[1:]
                real, ok_ctl, seen = [], True, set()
                for a, b in wins:
                    ok, j = E.gate_open(m, a, E.RES_PORTION)
                    if not ok or b >= m.t_on[j]:
                        continue
                    if not m.ctl[j]:
                        ok_ctl = False; break
                    if j not in seen:
                        seen.add(j); real.append(E.next_dev(m, j))
                if not ok_ctl or not real:
                    continue
                step = m.h * m.period
                copies = []
                for _ in range(200):
                    if len(copies) == 20: break
                    mm = int(rngs["placebo"].integers(-50, 51))
                    if mm == 0: continue
                    c, bad, seen2 = [], False, set()
                    for a, b in wins:
                        a2 = a + mm * step; b2 = b + mm * step
                        if a2 < m.dl[0] or b2 > m.dl[-1]: bad = True; break
                        ok, j = E.gate_open(m, a2, E.RES_PORTION)
                        if not ok or b2 >= m.t_on[j]: continue
                        if not m.ctl[j]: bad = True; break
                        if j not in seen2:
                            seen2.add(j); c.append(E.next_dev(m, j))
                    if not bad: copies.append(c)
                if copies:
                    ss.append({"real": real, "pl": copies})
        dmed, dsum = E.stat(ss)
        b = np.array([E.stat([ss[i] for i in boot.integers(0, len(ss), len(ss))]) for _ in range(E.BOOT)])
        lo, hi = np.nanpercentile(b, [2.5, 97.5], axis=0)
        print(f"{fam} H0: serii {len(ss)}, slotow {sum(len(s['real']) for s in ss)}; Δ mediany {dmed/1e3:+.2f} us "
              f"({lo[0]/1e3:+.2f}..{hi[0]/1e3:+.2f}), suma na serie {dsum/1e3:+.1f} us ({lo[1]/1e3:+.1f}..{hi[1]/1e3:+.1f})")

run(sys.argv[1])
