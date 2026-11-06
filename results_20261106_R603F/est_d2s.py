"""R603F, Ustalenia przed pomiarem. Uzycie: est_d2s.py SUROWE_R603E.

Na danych strony C' z R603E (analiza ../results_20261106_R603E/analyze.py bez zmian):
  1. tempo strumienia r = pojemnosc / mediana(kill - pierwszy wiersz) i rozklad liczby komunikatow n oraz porcji
     k po P0 w D2s: n = r * (koniec klienta - pierwszy wiersz + U(0, okres sondy + obrot)), k = ceil((n - 256) / 256);
  2. koszt samotnego okna P0 (256 komunikatow): S i Delta mediany slotow dotknietych przez samo P0 w seriach C',
     w ktorych wszystkie te sloty koncza sie przed startem P1;
  3. moc kontroli H0 K2s dla serii o ksztalcie D2s (P0 + k porcji, k losowane z punktu 1) na tle slotow
     kontrolnych C', 5 serii syntetycznych na serie C' (aneks A2 R603E): polszerokosc wobec 0,25 * S(C').
Ziarna: placebo 6034, bootstrap 6035, H0 6036 (jak R603E), Monte Carlo n 6040. Tylko liczby wyprowadzone."""
import importlib.util
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("analyze_r603e", HERE.parent / "results_20261106_R603E" / "analyze.py")
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)
D, A = E.D, E.A

BATCH = 256
PROBE_NS = 1_000_000_000  # kClientLivenessProbeInterval
MC = 100_000


def k_of(n):
    return np.maximum(0, np.ceil((n - BATCH) / BATCH)).astype(int)


def run(raw):
    rngs = D.rng_set(6034)
    boot = np.random.default_rng(6035)
    mc = np.random.default_rng(6040)
    for fam_dir in sorted(p for p in Path(raw).iterdir() if p.is_dir()):
        fam = fam_dir.name
        P = [E.analyze(d, rngs) for d in E.run_dirs(fam_dir, "Cp")]
        cap = P[0]["caps"][0]
        # 1. tempo i rozklad n, k
        fill = [sr["t_kill"] - r["conns"][sr["ci"]]["first"] for r in P for sr in r["series"]
                if sr["kind"] == "ok" and r["conns"][sr["ci"]]["first"] is not None]
        rate = cap / (np.median(fill) / 1e9)
        life = np.array([c["end"] - c["first"] for r in P for c in r["conns"] if c["first"] is not None], dtype=float)
        step = np.median([v for r in P for v in r["o3"]["step"]])
        p0 = np.median([v for r in P for v in r["o3"]["p0"]])
        full = np.median([v for r in P for v in r["o3"]["full"]])
        dt = mc.choice(life, MC) + mc.uniform(0, PROBE_NS + step, MC)
        n = np.floor(rate * dt / 1e9)
        k = k_of(n)
        pk = " / ".join(f"{np.mean(k == j):.3f}" for j in range(int(k.max()) + 1))
        dur = p0 + k * step
        print(f"{fam} | 1. pojemnosc {cap}, r {rate:.1f}/s (mediana zapelnienia {np.median(fill) / 1e9:.3f} s), "
              f"zycie po 1. wierszu p50 {np.median(life) / 1e6:.2f} ms; n p50 / sr / max {np.median(n):.0f} / "
              f"{n.mean():.0f} / {n.max():.0f} (sr n / pojemnosc {n.mean() / cap:.3f}); P(k=0..) {pk}, sr k {k.mean():.2f}; "
              f"seria (P0 + k obrotow) p50 / max {np.median(dur) / 1e6:.3f} / {dur.max() / 1e6:.3f} ms "
              f"(P0 C' {p0 / 1e3:.0f} us, porcja {full / 1e3:.0f} us, obrot {step / 1e3:.0f} us)")

        # 2. samotne okno P0
        lone = []
        for r in P:
            m = r["model"]
            for sr in r["series"]:
                if sr["kind"] != "ok" or len(sr["windows"]) < 2:
                    continue
                w0, p1 = sr["windows"][0], sr["windows"][1][0]
                idx, _ = E.affected_idx(m, [w0])
                if not len(idx) or (m.t_off[idx] >= p1).any():
                    continue
                cl = E.affected_cluster(m, [w0], rngs["placebo"])
                if cl is not None:
                    lone.append(cl)
        (dmed, s1), mci, sci = E.aff_boot(lone, boot)
        nsl = np.mean([len(c["real"]) for c in lone]) if lone else np.nan
        s_cp = E.series_s([sr["aff"] for r in P for sr in r["series"] if sr["kind"] == "ok" and sr.get("aff")])
        scp = E.mean_boot(s_cp, boot)
        win = 1 + k.mean()
        lin = n.mean() / BATCH
        print(f"{fam} | 2. samotne P0: serii {len(lone)}, slotow na serie {nsl:.2f}, Delta mediany {dmed / 1e3:+.2f} "
              f"({mci[0] / 1e3:+.2f}..{mci[1] / 1e3:+.2f}) us, S1 {s1 / 1e3:+.1f} ({sci[0] / 1e3:+.1f}..{sci[1] / 1e3:+.1f}) us; "
              f"S(C') {scp[0] / 1e3:+.1f} ({scp[1] / 1e3:+.1f}..{scp[2] / 1e3:+.1f}) us; przewidywane S(D2s): okna "
              f"{win:.2f} * S1 = {win * s1 / 1e3:+.1f} us, liniowo w n {lin:.2f} * S1 = {lin * s1 / 1e3:+.1f} us; "
              f"prog 0,5 * S(C') = {0.5 * scp[0] / 1e3:.1f} us")

        # 3. H0 dla serii D2s
        par = D.h0_params(P, 0)
        h0 = []
        for r in P:
            m = r["model"]
            for _ in range(E.H0_PER_SERIES * sum(1 for sr in r["series"] if sr["kind"] == "ok")):
                kk = int(k[mc.integers(0, MC)])
                wins = m.h0_windows(rngs["h0"], kk, par)
                idx, _ = E.affected_idx(m, wins)
                if not len(idx) or not m.ctl[idx].all():
                    continue
                cl = E.affected_cluster(m, wins, rngs["h0"])
                if cl is not None:
                    h0.append(cl)
        hs = E.mean_boot(E.series_s(h0), boot)
        half = (hs[2] - hs[1]) / 2
        print(f"{fam} | 3. H0 D2s: serii {len(h0)}, S {hs[0] / 1e3:+.1f} ({hs[1] / 1e3:+.1f}..{hs[2] / 1e3:+.1f}) us, "
              f"polszerokosc {half / 1e3:.1f} us wobec 0,25 * S(C') = {0.25 * scp[0] / 1e3:.1f} us "
              f"({'w progu' if half <= 0.25 * scp[0] else 'POZA progiem'})")
        sys.stdout.flush()


run(sys.argv[1])
