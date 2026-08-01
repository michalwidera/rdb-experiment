#!/usr/bin/env python3
"""F3 — monitor wieloczęstotliwościowy. Rdzeń Python (proceduralna pętla slotowa).

Zadanie: dwa źródła o wymiernych interwałach (A = 1/10 s, B = 1/5 s), przeplot
`#` i przesunięcie `>N`. W RQL to jedna instrukcja:

    SELECT * STREAM f3_out FROM (A>2)#(B>1)

Tutaj autor musi napisać sam trzy rzeczy:

1. **Dwa niezależne zegary źródeł na wspólnej siatce.** Przeplot nie jest
   próbkowaniem „kto akurat jest gotowy" — to scalanie dwóch strumieni zdarzeń
   uporządkowanych w czasie. Siatka wspólna to 1/30 s: A co 3 jednostki,
   B co 6 jednostek.

2. **Regułę rozstrzygania remisu.** Gdy oba źródła wypadają w tej samej chwili
   (t = 0, 1/5, 2/5, …), silnik wystawia najpierw B. Ustalone POMIAREM na
   artefakcie `f3_out`: sekwencja zaczyna się `1001, 1, 2, 1002, 3, 4`, czyli
   `B0, A0, A1, B1, A2, A3`. Zła reguła remisu daje poprawnie wyglądającą,
   ale przestawioną sekwencję.

3. **Złożenie opóźnień i okno agregujące.** Przesunięcie to 5 slotów: 2 wnosi
   sam przeplot (`STREAM_HASH_A_B`), 3 przesunięcie po przepisaniu
   `(A>2)#(B>1)` na `(A#B)>3`. Do tego dochodzi okno agregujące 30, więc ogon
   wyjścia to 35. Autor RQL nie liczy tego wcale — kompilator publikuje
   `tail=35`; tutaj trzeba złożyć to ręcznie z trzech składników.

Arytmetyka całkowita wg `oracle/refsem.py`: `.avg` to dokładne dzielenie sumy
przez liczbę pól nie-NULL, dopiero potem obcięcie do zera.
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
from refsem import avg  # noqa: E402


# CORE_BEGIN
def run(a_values, b_values, slots):
    """Zwraca listę (logical_index, wartość) dla `slots` zdarzeń scalonych."""
    HASH_NUM = 12
    HASH_DEN = 17
    INTERVAL_NS = 58_823_529
    SHIFT = 21
    WIN = 30
    ia = 0
    ib = 0
    win = [0] * WIN
    filled = 0
    out = []
    t0 = time.monotonic_ns()
    for r in range(slots):
        deadline = t0 + r * INTERVAL_NS
        now = time.monotonic_ns()
        if now < deadline:
            time.sleep((deadline - now) / 1e9)
        take_b = (HASH_NUM * r) // HASH_DEN == (HASH_NUM * (r + 1)) // HASH_DEN
        if take_b:
            value = b_values[ib]
            ib = ib + 1
        else:
            value = a_values[ia]
            ia = ia + 1
        for k in range(WIN - 1, 0, -1):
            win[k] = win[k - 1]
        win[0] = value
        filled = filled + 1
        if filled < WIN:
            continue
        out.append((SHIFT + r + 1, avg(win)))
    # CORE_END
    return out
