#!/usr/bin/env python3
"""F2 — niekliniczny potok cech EKG. Rdzeń Python (proceduralna pętla slotowa).

TO NIE JEST DETEKTOR KLINICZNY. Potok cech, bez twierdzeń diagnostycznych.

Pięć etapów: band-pass 25 -> różniczka 5 -> kwadrat/1000 -> MWI 30 -> próg 180.

Trzy obowiązki, których autor RQL nie ma i które widać niżej wprost:

1. **Okno i przesuwanie na każdym etapie** — cztery bufory, cztery pętle
   przesunięcia.
2. **Ogon każdego etapu osobno** — licznik zapełnienia per etap; ogon wyjścia
   (240 slotów) jest złożeniem 25+5+30+180 i nie da się go napisać jedną stałą
   bez ręcznego rozpisania etapów.
3. **Wyrównanie strumieni o RÓŻNYCH opóźnieniach** — `qrs_out` w slocie L łączy
   `mlii[L]`, `mwi[L]` i `mwi_thr[L]`, ale `mwi[L]` powstaje 3 sloty wcześniej,
   a `mwi_thr[L]` 4 sloty wcześniej. Trzeba je zapamiętać po indeksie.
   W RQL robi to `FROM mlii+mwi+mwi_thr`.

Arytmetyka całkowita wg `oracle/refsem.py`. NIE UŻYWAĆ `//`.
Orientacja okna: `win[0]` = próbka najnowsza (PREDECLARATION.md §11.1 E3).
Różniczka `[-1,-2,0,2,1]` jest asymetryczna, więc zła orientacja rozjedzie się
tutaj — w przeciwieństwie do symetrycznego band-passu.
"""
import sys
import time
from pathlib import Path

_p = Path(__file__).resolve()
while not (_p / "oracle" / "refsem.py").is_file():
    if _p == _p.parent:
        raise RuntimeError("nie znaleziono oracle/refsem.py w zadnym katalogu nadrzednym")
    _p = _p.parent
sys.path.insert(0, str(_p / "oracle"))
from refsem import avg, idiv, imul, isub, sumc  # noqa: E402


# CORE_BEGIN
def run(mlii, bp_coef, d_coef, slots):
    """Zwraca listę (logical_index, [pole0, pole1, pole2])."""
    WIN_BP = 25
    WIN_D = 5
    WIN_MWI = 30
    WIN_THR = 180
    INTERVAL_NS = 2_777_778
    win_bp = [0] * WIN_BP
    win_d = [0] * WIN_D
    win_mwi = [0] * WIN_MWI
    win_thr = [0] * WIN_THR
    cnt_bp = 0
    cnt_d = 0
    cnt_mwi = 0
    cnt_thr = 0
    mwi_at = {}
    thr_at = {}
    out = []
    t0 = time.monotonic_ns()
    for n in range(slots):
        deadline = t0 + n * INTERVAL_NS
        now = time.monotonic_ns()
        if now < deadline:
            time.sleep((deadline - now) / 1e9)
        x = mlii[n]

        for k in range(WIN_BP - 1, 0, -1):
            win_bp[k] = win_bp[k - 1]
        win_bp[0] = x
        cnt_bp = cnt_bp + 1
        if cnt_bp >= WIN_BP:
            bp = idiv(sumc([imul(win_bp[k], bp_coef[k]) for k in range(WIN_BP)]), 1000)
            for k in range(WIN_D - 1, 0, -1):
                win_d[k] = win_d[k - 1]
            win_d[0] = bp
            cnt_d = cnt_d + 1
            if cnt_d >= WIN_D:
                d = sumc([imul(win_d[k], d_coef[k]) for k in range(WIN_D)])
                sq = idiv(imul(d, d), 1000)
                for k in range(WIN_MWI - 1, 0, -1):
                    win_mwi[k] = win_mwi[k - 1]
                win_mwi[0] = sq
                cnt_mwi = cnt_mwi + 1
                if cnt_mwi >= WIN_MWI:
                    mwi = avg(win_mwi)
                    mwi_at[n + 3] = mwi
                    for k in range(WIN_THR - 1, 0, -1):
                        win_thr[k] = win_thr[k - 1]
                    win_thr[0] = mwi
                    cnt_thr = cnt_thr + 1
                    if cnt_thr >= WIN_THR:
                        thr_at[n + 4] = avg(win_thr)

        if n in mwi_at and n in thr_at:
            m = mwi_at[n]
            t = thr_at[n]
            out.append((n, [isub(x, 900), imul(m, 5), imul(isub(m, imul(t, 2)), 5)]))
    # CORE_END
    return out
