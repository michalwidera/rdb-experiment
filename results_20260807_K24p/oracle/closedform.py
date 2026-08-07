#!/usr/bin/env python3
"""Replika rachunku silnika: ``compiler::computeLogicalOrigin()``
i ``compiler::computeStartupLatency()``.

UWAGA — ten moduł istnieje **wyłącznie** na potrzeby bramki mutantów. Oracle
(model.py) nie importuje go i nie ma prawa go importować. Replika odtwarza
rachunek z `src/retractor/lib/compiler.cpp` oraz `src/include/SOperations.hpp`
w wersji przypiętej w PIN.md; jej wierność sprawdza test_closedform.py,
porównując ją ze zrzutem planu silnika.

Mutanty w mutants.py psują tę replikę w jednym miejscu każdy. Bramka wymaga,
by oracle odróżnił replikę od każdego mutanta.

**Zmiana wobec K24r (przestemplowanie z 2026-08-06).** Silnik niesie teraz dwie
wielkości zamiast jednej. Origin nie jest w pełni postacią zamkniętą: dla `+`,
`#`, `-`, `Θ` i `~Θ` silnik szuka najmniejszego indeksu spełniającego warunek
przez połowienie po niemalejącym odwzorowaniu (``firstIndexReaching``), a nie
przez wzór. Replika odtwarza to wiernie — razem z tym ograniczeniem, które jest
przedmiotem raportu, a nie usterką repliki.
"""

from fractions import Fraction
from math import gcd

from plan import (ADD, AGSE, HASH, NTHETA, PASS, REDUCE, SHIFT, SOURCE, SUB,
                  THETA)

# compiler.cpp: kOriginSearchLimit
ORIGIN_SEARCH_LIMIT = 1 << 24


class ReplicaError(RuntimeError):
    """Replika nie potrafiła odtworzyć rachunku silnika."""


def _floor(value):
    return value.numerator // value.denominator


def _ceil(value):
    return -((-value.numerator) // value.denominator)


def to_slots(width, delta_source, delta_target):
    if width <= 0:
        return 0
    return _ceil(Fraction(width) * delta_source / delta_target)


# --- odwzorowania indeksu (SOperations.hpp) -----------------------------------
#
# Te same funkcje, którymi silnik ADRESUJE składowe w dataModel. Origin liczy
# się po nich, bo origin jest pytaniem „od którego indeksu odwzorowanie trafia
# w istniejący rekord”.

def map_add(delta_out, delta_src, n):
    if delta_out == delta_src:
        return n
    return _floor(Fraction(n) * delta_out / delta_src)


def map_subtract(delta_source, delta_target, n):
    if delta_source == delta_target:
        return n
    return _ceil(Fraction(n) * delta_target / delta_source)


def map_div(delta_a, delta_b, n):
    """Θ — lewa składowa: a_i = c_{i+ceil((i+1)*dA/dB)}."""
    return n + _ceil(Fraction(n + 1) * delta_a / delta_b)


def map_mod(delta_a, delta_b, n):
    """~Θ — prawa składowa: b_i = c_{i+floor(i*dB/dA)}."""
    return n + _floor(Fraction(n) * delta_b / delta_a)


def first_index_reaching(mapping, threshold, node_id="?"):
    """Najmniejsze n >= 0, dla którego niemalejące odwzorowanie osiąga próg.

    Replika ``firstIndexReaching`` z compiler.cpp: podwajanie górnego
    ograniczenia, potem połowienie.
    """
    if threshold <= 0:
        return 0
    hi = 1
    while mapping(hi) < threshold:
        if hi > ORIGIN_SEARCH_LIMIT:
            raise ReplicaError(f"replika: poszukiwanie origin rozbiegło się dla '{node_id}'")
        hi *= 2
    lo = 0
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if mapping(mid) < threshold:
            lo = mid + 1
        else:
            hi = mid
    return lo


# --- postacie zamknięte ogona -------------------------------------------------

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


def agse_tail(source_width, step, source_tail):
    """Postać po przestemplowaniu: ceil((1+W_src)*F/step) - 1.

    Człon fazowy P = floor((|L|-1)/gcd(F,step))*gcd(F,step), obecny w postaci
    z K24r, zniknął z ogona: rozpiętość okna nie jest już czekaniem, tylko
    niedefiniowalnością, i przeszła do origin (agse_origin niżej). Minimum
    reszty (n*step) mod F wynosi zero i jest osiągane niezależnie od tego, od
    którego n zaczyna się strumień, więc origin nie wchodzi do ogona.
    """
    return _ceil(Fraction((1 + source_tail) * source_width, step)) - 1


def agse_origin(source_width, step, length, source_origin, drop_span=False, off_by_one=0):
    """Początek logiczny okna: ceil((O_src*F + |L| - 1)/step).

    Okno rekordu n sięga pozycji n*step-(|L|-1); warunek mieszczenia się
    w istniejącej części źródła daje wprost powyższy wzór.
    """
    span = 0 if drop_span else abs(length) - 1
    return _ceil(Fraction(source_origin * source_width + span, step)) + off_by_one


def add_tail(delta_source, delta_target, source_tail):
    """ceil((1+W_src)*D_src/D_out) - 1 per składowa (bez zmian wobec K24r)."""
    return _ceil(Fraction(1 + source_tail) * delta_source / delta_target) - 1


# --- przebiegi ----------------------------------------------------------------

def evaluate_origins(plan, mutation=None, given_origins=None):
    """Początki logiczne wg rachunku silnika (opcjonalnie zmutowanego)."""
    mutation = mutation or {}
    origins = {}
    for node in plan.nodes:
        if node.kind == SOURCE:
            origins[node.name] = 0
            continue

        children = [plan.by_name(name) for name in node.children]
        first = children[0]
        source_origins = given_origins if given_origins is not None else origins
        o1 = source_origins[first.name]
        result = o1

        if node.kind in (PASS, REDUCE):
            result = o1
        elif node.kind == SHIFT:
            result = o1 + (0 if mutation.get("shift_drop_origin", False) else node.param)
        elif node.kind == AGSE:
            _step, length = node.param
            step = node.param[0]
            result = agse_origin(first.width, step, length, o1,
                                 drop_span=mutation.get("agse_drop_span", False),
                                 off_by_one=mutation.get("agse_origin_delta", 0))
        elif node.kind == SUB:
            result = first_index_reaching(
                lambda n: map_subtract(first.delta, node.delta, n), o1, node.name)
        elif node.kind == THETA:
            result = first_index_reaching(
                lambda n: map_div(node.delta, node.param, n), o1, node.name)
        elif node.kind == NTHETA:
            result = first_index_reaching(
                lambda n: map_mod(node.param, node.delta, n), o1, node.name)
        elif node.kind == ADD:
            second = children[1]
            o2 = source_origins[second.name]
            result = max(
                first_index_reaching(lambda n: map_add(node.delta, first.delta, n), o1, node.name),
                first_index_reaching(lambda n: map_add(node.delta, second.delta, n), o2, node.name))
        elif node.kind == HASH:
            second = children[1]
            o2 = source_origins[second.name]
            zet = second.delta / (first.delta + second.delta)
            left = first_index_reaching(lambda n: _floor(zet * n), o1, node.name)
            right = first_index_reaching(lambda n: n - _floor(zet * n), o2, node.name)
            if mutation.get("hash_origin_left_only", False):
                result = left
            else:
                result = max(left, right)
        else:
            raise ReplicaError(f"replika: nieznany węzeł {node.kind}")

        origins[node.name] = result
    return origins


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
            # Ogon samego przesunięcia jest ZEROWY: rekord n czyta rekord n-N
            # producenta, czyli starszy od bieżącego. Ogon równy ogonowi
            # producenta wynika z tego, że fetchBack adresuje offsetem
            # względnym. `N` siedzi w origin.
            result = w1 + (node.param if mutation.get("shift_tail_keeps_n", False) else 0)
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
            if mutation.get("agse_tail_keeps_phase", False):
                unit = gcd(first.width, step)
                phase_bound = ((abs(length) - 1) // unit) * unit
                result = _ceil(Fraction(phase_bound + (1 + w1) * first.width, step)) - 1
            else:
                result = agse_tail(first.width, step, w1)
        elif node.kind == REDUCE:
            pass
        else:
            raise ReplicaError(f"replika: nieznany węzeł {node.kind}")

        tails[node.name] = result
    return tails
