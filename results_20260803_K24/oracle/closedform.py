#!/usr/bin/env python3
"""Replika postaci zamkniętej ``compiler::computeStartupLatency()``.

UWAGA — ten moduł istnieje **wyłącznie** na potrzeby bramki mutantów. Oracle
(model.py) nie importuje go i nie ma prawa go importować. Replika odtwarza
rachunek z `src/retractor/lib/compiler.cpp` oraz `src/include/SOperations.hpp`
w wersji przypiętej w PIN.md; jej wierność sprawdza test_closedform.py,
porównując ją ze zrzutem planu silnika.

Mutanty w mutants.py psują tę replikę w jednym miejscu każdy. Bramka wymaga,
by oracle odróżnił replikę od każdego mutanta.
"""

from fractions import Fraction
from math import gcd

from plan import (ADD, AGSE, HASH, NTHETA, PASS, REDUCE, SHIFT, SOURCE, SUB,
                  THETA)


def _floor(value):
    return value.numerator // value.denominator


def _ceil(value):
    return -((-value.numerator) // value.denominator)


def to_slots(width, delta_source, delta_target):
    if width <= 0:
        return 0
    return _ceil(Fraction(width) * delta_source / delta_target)


def hash_own(delta1, delta2, phase_delta=0, swap=False, drop_own=False, first_phase=False):
    """Własny ogon przeplotu: ceil((p+q-1)/p) dla zredukowanego delta1/delta2.

    ``first_phase`` daje wariant sprzed K2 — człon pierwszej fazy ceil(q/p),
    który chroni B[0], ale nie najgorszą fazę późniejszą. Używa go reguła
    lokalna B w analizie członu (b); nie jest to mutant.
    """
    if drop_own:
        return 0
    if first_phase:
        return _ceil(delta2 / delta1)
    ratio = (delta1 / delta2) if swap else (delta2 / delta1)
    period = ratio.denominator
    advance = ratio.numerator
    return (period + advance - 2) // period + 1 + phase_delta


def subtract_tail(delta_source, delta_target, source_tail, source_declared):
    ratio = delta_target / delta_source
    q = ratio.denominator
    phase = Fraction(q - 1, q)
    if source_declared:
        return _floor(phase / ratio) + 1
    return _ceil((Fraction(source_tail) + phase) / ratio)


def agse_tail(source_width, step, length, source_tail):
    """Postać po korekcie H10a: ceil((P + (1+W_src)*F)/step) - 1.

    Poprzednia postać floor((W_src*F + P)/step) + 1 zgadzała się z granicą
    zdarzeniową dla 31,8% węzłów `@` korpusu; ta zgadza się dla 100%.
    """
    length_abs = abs(length)
    unit = gcd(source_width, step)
    phase_bound = ((length_abs - 1) // unit) * unit
    numerator = phase_bound + (1 + source_tail) * source_width
    return _ceil(Fraction(numerator, step)) - 1


def add_tail(delta_source, delta_target, source_tail):
    """Postać po korekcie H10a: ceil((1+W_src)*D_src/D_out) - 1 per składowa.

    Poprzednia postać ceil(W_src*D_src/D_out) zgadzała się dla 42,3% węzłów `+`.
    """
    return _ceil(Fraction(1 + source_tail) * delta_source / delta_target) - 1


def evaluate(plan, mutation=None, given_tails=None):
    """Ogony wszystkich węzłów wg postaci zamkniętej (opcjonalnie zmutowanej).

    ``given_tails`` podmienia ogony składowych na zadane z zewnątrz. Służy
    atrybucji per klasa operatora: wtedy każdy węzeł jest liczony z ogonów
    składowych wziętych z oracle'a, więc niezgodność w węźle pochodzi z reguły
    tego węzła, a nie jest odziedziczona po dziecku.
    """
    mutation = mutation or {}
    tails = {}
    for node in plan.nodes:
        if node.kind == SOURCE:
            tails[node.name] = 0
            continue

        children = [plan.by_name(name) for name in node.children]
        first = children[0]
        source_tails = given_tails if given_tails is not None else tails
        w1 = source_tails[first.name]
        result = to_slots(w1, first.delta, node.delta)

        if node.kind == PASS:
            result = w1
        elif node.kind == SHIFT:
            result = w1 + node.param
        elif node.kind == HASH:
            second = children[1]
            own = hash_own(first.delta, second.delta,
                           phase_delta=mutation.get("hash_phase", 0),
                           swap=mutation.get("hash_swap", False),
                           drop_own=mutation.get("hash_drop_own", False),
                           first_phase=mutation.get("hash_first_phase", False))
            result = max(to_slots(w1, first.delta, node.delta),
                         to_slots(source_tails[second.name], second.delta, node.delta) + own)
        elif node.kind == ADD:
            second = children[1]
            result = max(add_tail(first.delta, node.delta, w1),
                         add_tail(second.delta, node.delta, source_tails[second.name]))
        elif node.kind == THETA:
            result += 0 if mutation.get("theta_zero_own", False) else 1
        elif node.kind == NTHETA:
            pass
        elif node.kind == SUB:
            result = subtract_tail(first.delta, node.delta, w1, first.kind == SOURCE)
        elif node.kind == AGSE:
            step, length = node.param
            result = agse_tail(first.width, step, length, w1)
        elif node.kind == REDUCE:
            pass
        else:
            raise ValueError(f"replika: nieznany węzeł {node.kind}")

        tails[node.name] = result
    return tails
