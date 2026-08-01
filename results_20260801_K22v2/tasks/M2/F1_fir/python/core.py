#!/usr/bin/env python3
"""F1 — FIR z oknem i redukcją. Rdzeń Python (proceduralna pętla slotowa).

Model: jawna pętla próbkowa z absolutnymi terminami slotów i jawnie
zarządzanym stanem okna. To jest najprostsza POPRAWNA implementacja tego
zadania w tym modelu — nie jest ani sztucznie rozdmuchana, ani skrócona
o obowiązki, które model realnie nakłada (PREDECLARATION.md §3, reguła
„najprostsza poprawna").

Arytmetyka: całkowita, wg semantyki silnika (`oracle/refsem.py`).
NIE WOLNO użyć `//` — `-7 // 2 == -4`, a silnik daje `-3`.

Orientacja okna: `win[0]` to próbka NAJNOWSZA (PREDECLARATION.md §11.1 E3).
Zła orientacja policzyłaby poprawnie wyglądającą, ale inną funkcję.

Ogon: silnik nie emituje przez pierwsze `WIN` slotów, więc ten rdzeń też nie.
Tu jest to jawny licznik rozgrzewki — obowiązek, którego autor RQL nie ma.

Wczytanie plików, format wyjścia i zapis to harness (`run.py`), poza rdzeniem.
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
from refsem import idiv, imul, sumc  # noqa: E402


# CORE_BEGIN
def run(samples, coef, slots):
    """Zwraca listę (logical_index, wartość) dla `slots` slotów."""
    WIN = 45
    INTERVAL_NS = 1_000_000
    win = [0] * WIN
    out = []
    t0 = time.monotonic_ns()
    for n in range(slots):
        deadline = t0 + n * INTERVAL_NS
        now = time.monotonic_ns()
        if now < deadline:
            time.sleep((deadline - now) / 1e9)
        x = samples[n]
        for k in range(WIN - 1, 0, -1):
            win[k] = win[k - 1]
        win[0] = x
        if n < WIN - 1:
            continue
        acc = sumc([imul(win[k], coef[k]) for k in range(WIN)])
        y = idiv(idiv(acc, WIN), 1000)
        out.append((n + 1, y))
    # CORE_END
    return out
