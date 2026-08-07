#!/usr/bin/env python3
"""Bramka oracle'a — przypadki o ręcznie wyprowadzonej odpowiedzi.

Każdy ogon poniżej wyprowadzono z definicji, nie odczytano z silnika ani
z postaci zamkniętej. Reguła wyprowadzania jest jedna:

    rekord n strumienia S wymaga rekordów składowych o znanych chwilach
    dostępności; deficyt slotu n to  avail(n)/Delta_S - (n+1);
    W_S = max(0, max_n ceil(deficyt(n))).

Wyprowadzenia rodzinami (pełne rachunki w REPORT.md §2):

* przeplot A#B, oba źródła W=0: deficyt maksymalizuje się na slocie, w którym
  wypada element B o najgorszej fazie; dla 1#1 daje 1, dla 1#2 daje 2,
  dla 2#1 daje 1, dla 1/3#1/2 daje 2 (rachunek slot po slocie w REPORT.md);
* przesunięcie >N: odwzorowanie rekordów jest tożsamością, a emisja późniejsza
  o N*Delta, więc deficyt każdego slotu rośnie dokładnie o N;
* różnica o całkowitym ilorazie r: rekord n czyta indeks r*n, dostępny
  w chwili (rn+1)*Delta_zrodla, a slot n kończy się w (n+1)*r*Delta_zrodla;
  deficyt wynosi 1/r - 1 < 0, więc ogon jest zerowy dla każdego r >= 1;
* różnica o ilorazie niecałkowitym 8/3: maksymalny deficyt wypada ujemny
  (rachunek dla n=0..3 w REPORT.md), ogon zerowy;
* AGSE @(k,w) nad źródłem o F polach: rekord n potrzebuje pola n*k+|w|-1,
  czyli rekordu floor((n*k+|w|-1)/F); dla F=1,k=1,|w|=3 deficyt jest stały
  i równy 2; dla F=2,k=1,|w|=4 maksimum wypada 4;
* Theta i ~Theta: indeks składowej wyprowadzony z definicji rozplotu; dla
  badanych trójek deficyt wypada dokładnie zero (element powstaje w chwili
  końca slotu), więc ogon zerowy przy konwencji C1 i jeden przy C2;
* redukcje i projekcja: odwzorowanie tożsamościowe, ogon równy ogonowi źródła;
* suma A+B wg definicji z artykułu (b_{floor(n*Delta_a/Delta_b)}): rekord 0
  potrzebuje b_0, dostępnego dopiero w chwili Delta_b > Delta_a, stąd ogon
  dodatni, gdy strumień wolniejszy nie jest wielokrotnością szybszego.

Kolumna ``C2`` jest wartością tej samej reguły przy konwencji ostrej.
"""

import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "oracle"))

import plan as P  # noqa: E402


def _plan(nodes):
    return P.Plan(nodes=tuple(nodes))


def _src(name, delta, width=1):
    return P.make_source(name, delta, width)


def hand_cases():
    """Lista (etykieta, plan, {nazwa: ogon C1}, {nazwa: ogon C2})."""
    out = []

    def add(label, nodes, c1, c2):
        out.append((label, _plan(nodes), c1, c2))

    # --- przeplot ---
    for da, db, tail1, tail2 in [(1, 1, 1, 2), (1, 2, 2, 3), (2, 1, 1, 2),
                                 (Fraction(1, 3), Fraction(1, 2), 2, 3),
                                 (Fraction(1, 10), Fraction(1, 5), 2, 3),
                                 (Fraction(3, 10), Fraction(1, 5), 2, 2)]:
        a, b = _src("s0", da), _src("s1", db)
        add(f"hash {da}#{db}", [a, b, P.make_hash("n0", a, b)], {"n0": tail1}, {"n0": tail2})

    # --- przesunięcie ---
    for offset in (1, 2, 5):
        a = _src("s0", Fraction(1, 10))
        add(f"shift >{offset}", [a, P.make_shift("n0", a, offset)],
            {"n0": offset}, {"n0": offset + 1})

    # --- projekcja i redukcje ---
    a = _src("s0", Fraction(1, 10), 3)
    add("pass", [a, P.make_pass("n0", a)], {"n0": 0}, {"n0": 1})
    for reducer in P.REDUCERS:
        a = _src("s0", Fraction(1, 10), 3)
        add(f"reduce {reducer}", [a, P.make_reduce("n0", a, reducer)], {"n0": 0}, {"n0": 1})

    # --- różnica ---
    for ratio in (1, 2, 3, 5):
        a = _src("s0", Fraction(1, 100))
        add(f"sub ratio {ratio}", [a, P.make_sub("n0", a, Fraction(ratio, 100))],
            {"n0": 0}, {"n0": 1 if ratio == 1 else 0})
    a = _src("s0", Fraction(1, 8))
    add("sub 8/3", [a, P.make_sub("n0", a, Fraction(1, 3))], {"n0": 0}, {"n0": 0})

    # --- AGSE ---
    for width, step, length, tail1, tail2 in [(1, 1, 3, 2, 3), (1, 1, -3, 2, 3),
                                              (1, 2, 4, 1, 2), (2, 1, 4, 4, 5),
                                              (3, 2, 2, 1, 2), (4, 3, 5, 2, 2)]:
        a = _src("s0", Fraction(1, 10), width)
        add(f"agse F={width} @({step},{length})", [a, P.make_agse("n0", a, step, length)],
            {"n0": tail1}, {"n0": tail2})

    # --- rozplot ---
    for delta, other, theta1, theta2, ntheta1, ntheta2 in [
            (Fraction(1, 2), 1, 0, 1, 0, 0),
            (Fraction(2, 3), 1, 0, 1, 0, 0),
            (Fraction(2, 3), 2, 1, 1, 0, 0)]:
        a = _src("s0", delta)
        add(f"theta {delta}&{other}", [a, P.make_theta("n0", a, other)],
            {"n0": theta1}, {"n0": theta2})
        a = _src("s0", delta)
        add(f"ntheta {delta}%{other}", [a, P.make_ntheta("n0", a, other)],
            {"n0": ntheta1}, {"n0": ntheta2})

    # --- suma ---
    a, b = _src("s0", 1), _src("s1", 1)
    add("add 1+1", [a, b, P.make_add("n0", a, b)], {"n0": 0}, {"n0": 1})
    a, b = _src("s0", Fraction(1, 3)), _src("s1", Fraction(1, 2))
    add("add 1/3+1/2", [a, b, P.make_add("n0", a, b)], {"n0": 1}, {"n0": 1})
    a, b = _src("s0", Fraction(1, 10)), _src("s1", Fraction(1, 4))
    add("add 1/10+1/4", [a, b, P.make_add("n0", a, b)], {"n0": 2}, {"n0": 2})

    # --- kompozycje ---
    a, b = _src("s0", 1), _src("s1", 2)
    h = P.make_hash("n0", a, b)
    add("hash then shift", [a, b, h, P.make_shift("n1", h, 2)],
        {"n0": 2, "n1": 4}, {"n0": 3, "n1": 6})

    a, b = _src("s0", 1), _src("s1", 2)
    shifted = P.make_shift("n0", a, 1)
    add("shift under hash", [a, b, shifted, P.make_hash("n1", shifted, b)],
        {"n0": 1, "n1": 2}, {"n0": 2, "n1": 4})

    a, b, c = _src("s0", 1), _src("s1", 2), _src("s2", 3)
    h1 = P.make_hash("n0", a, b)
    add("hash of hash", [a, b, c, h1, P.make_hash("n1", h1, c)],
        {"n0": 2, "n1": 5}, {"n0": 3, "n1": 6})

    return out
