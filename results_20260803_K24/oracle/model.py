#!/usr/bin/env python3
"""Niezależny oracle zdarzeniowy K24 — indeks pierwszego w pełni określonego
rekordu wyjściowego, wyprowadzony z definicji operatorów i czasu zdarzeń.

Oracle NIE używa postaci zamkniętej z ``compiler::computeStartupLatency()``.
Nie występuje tu ani ``ceil((p+q-1)/p)``, ani ``AgseStartupLatency``, ani
``SubtractStartupLatency``. Ogon jest tu wielkością **wyprowadzoną**:

    rekord n strumienia S jest emitowany w chwili (n + 1 + W_S) * Delta_S;
    zależy od rekordów składowych, każdy o własnej chwili dostępności;
    W_S jest najmniejszą liczbą całkowitą >= 0, dla której emisja każdego
    rekordu wypada nie wcześniej niż dostępność wszystkich jego zależności.

Odwzorowanie rekordów (który rekord składowej wchodzi do rekordu n) pochodzi
z definicji operatorów w §Formal Foundations artykułu, czyli z semantyki,
a nie z rachunku ogona.

Konwencja dostępności (predeklarowana, patrz PREDECLARATION.md):
  C1 — nieostra: rekord dostępny w chwili swojej emisji; konsument o slocie
       kończącym się w tej samej chwili może go użyć (producenci publikują
       przed konsumentami w takcie — dataModel::processRows przetwarza
       deklaracje jako pierwsze, dalej porządek topologiczny).
  C2 — ostra: odczyt w tym samym takcie jest niedozwolony.
Werdykt główny liczony jest w C1; C2 raportowany jest jako kolumna wrażliwości.
"""

from dataclasses import dataclass
from fractions import Fraction

from plan import (ADD, AGSE, HASH, NTHETA, PASS, REDUCE, SHIFT, SOURCE, SUB,
                  THETA, period_hint)

C1 = "C1"
C2 = "C2"

ADD_MAPPING = "spec"   # "spec" | "engine" — patrz dependencies(); kampania: "spec"

MIN_PROBE = 64
PROBE_FACTOR = 4


class OracleError(RuntimeError):
    """Awaria aparatury oracle'a — zatrzymuje iterację, nie jest wynikiem."""


def _floor(value):
    return value.numerator // value.denominator


def _ceil(value):
    return -((-value.numerator) // value.denominator)


def dependencies(node, children, n):
    """Zależności rekordu ``n``: lista (nazwa składowej, indeks, opóźnienie).

    Opóźnienie jest czasem fizycznym doklejanym do dostępności — używa go
    wyłącznie przesunięcie czasowe, które nie zmienia odwzorowania rekordów.
    """
    kind = node.kind
    if kind == PASS:
        return [(children[0].name, n, Fraction(0))]
    if kind == SHIFT:
        return [(children[0].name, n, Fraction(node.param) * node.delta)]
    if kind == REDUCE:
        return [(children[0].name, n, Fraction(0))]
    if kind == HASH:
        left, right = children
        z = right.delta / (left.delta + right.delta)
        if _floor(z * n) == _floor(z * (n + 1)):
            return [(right.name, n - _floor(z * n), Fraction(0))]
        return [(left.name, _floor(z * n), Fraction(0))]
    if kind == ADD:
        left, right = children
        # ADD_MAPPING == "spec": odwzorowanie z Definicji sumy strumieni
        # (artykuł, eq. sum): c_n = (a_n, b_{floor(n*D_a/D_b)}).
        # ADD_MAPPING == "engine": odwzorowanie zaobserwowane w silniku,
        # b_{floor((n+1)*D_a/D_b)} — wariant WYŁĄCZNIE diagnostyczny, do
        # rozstrzygnięcia, ile z rozbieżności klasy `+` pochodzi z różnicy
        # definicji, a ile z rachunku ogona. Kampania używa "spec".
        offset = 1 if ADD_MAPPING == "engine" else 0
        if left.delta <= right.delta:
            return [(left.name, n, Fraction(0)),
                    (right.name, _floor(Fraction(n + offset) * left.delta / right.delta), Fraction(0))]
        return [(left.name, _floor(Fraction(n + offset) * right.delta / left.delta), Fraction(0)),
                (right.name, n, Fraction(0))]
    if kind == SUB:
        src = children[0]
        if node.delta == src.delta:
            return [(src.name, n, Fraction(0))]
        return [(src.name, _ceil(Fraction(n) * node.delta / src.delta), Fraction(0))]
    if kind == THETA:
        src = children[0]
        return [(src.name, n + _ceil(Fraction(n + 1) * node.delta / node.param), Fraction(0))]
    if kind == NTHETA:
        src = children[0]
        return [(src.name, n + _floor(Fraction(n) * node.delta / node.param), Fraction(0))]
    if kind == AGSE:
        src = children[0]
        step, length = node.param
        last_field = n * step + abs(length) - 1
        return [(src.name, last_field // src.width, Fraction(0))]
    raise OracleError(f"oracle: brak modelu dla węzła {kind}")


@dataclass(frozen=True)
class NodeResult:
    name: str
    kind: str
    delta: Fraction
    tail: int
    probe: int
    argmax_slot: int
    stable: bool


def _emission(delta, tail, index):
    return (Fraction(index) + 1 + tail) * delta


def _tail_over_window(node, children, avail, window, convention):
    """Ogon wymuszony przez sloty ``0..window-1``; zwraca (ogon, slot maksimum)."""
    best = 0
    best_slot = 0
    for n in range(window):
        required = None
        for child_name, index, delay in dependencies(node, children, n):
            if index < 0:
                raise OracleError(f"oracle: ujemny indeks składowej w {node.name} dla slotu {n}")
            moment = avail[child_name](index) + delay
            if required is None or moment > required:
                required = moment
        deficit = required / node.delta - (n + 1)
        if convention == C1:
            candidate = _ceil(deficit)
        else:
            candidate = _floor(deficit) + 1
        if candidate > best:
            best = candidate
            best_slot = n
    return max(best, 0), best_slot


def evaluate(plan, convention=C1, min_probe=MIN_PROBE, probe_factor=PROBE_FACTOR):
    """Ogony wszystkich węzłów planu, w porządku topologicznym."""
    tails = {}
    avail = {}
    results = []

    for node in plan.nodes:
        if node.kind == SOURCE:
            tails[node.name] = 0
            avail[node.name] = (lambda delta: (lambda index: _emission(delta, 0, index)))(node.delta)
            results.append(NodeResult(node.name, node.kind, node.delta, 0, 0, 0, True))
            continue

        children = [plan.by_name(name) for name in node.children]
        window = max(min_probe, probe_factor * period_hint(node, children))
        tail, slot = _tail_over_window(node, children, avail, window, convention)
        wide, _ = _tail_over_window(node, children, avail, 2 * window, convention)
        if wide != tail:
            raise OracleError(
                f"oracle: okno sondowania {window} za wąskie dla {node.name} ({tail} != {wide})")

        tails[node.name] = tail
        avail[node.name] = (lambda delta, w: (lambda index: _emission(delta, w, index)))(node.delta, tail)
        results.append(NodeResult(node.name, node.kind, node.delta, tail, window, slot, True))

    return results


def tails_by_name(plan, convention=C1):
    return {result.name: result.tail for result in evaluate(plan, convention=convention)}


# --- model treści rekordu -----------------------------------------------------
#
# Treść jest tym samym odwzorowaniem rekordów co dependencies(), tyle że
# przeniesionym na wartości. Służy bramce poprawności odwzorowania: dopóki
# silnik emituje dokładnie te wartości, które przewiduje oracle, rozbieżność
# ogona jest rozbieżnością ogona, a nie różnicą w definicji operatora.

def source_value(source_index, record_index, field_index):
    return (source_index + 1) * 1_000_000 + record_index * 10 + field_index


def source_record(source_index, record_index, width):
    return tuple(source_value(source_index, record_index, f) for f in range(width))


def content(plan, name, n, source_order=None):
    """Krotka wartości rekordu ``n`` strumienia ``name``."""
    if source_order is None:
        source_order = [node.name for node in plan.nodes if node.kind == SOURCE]
    node = plan.by_name(name)
    if node.kind == SOURCE:
        return source_record(source_order.index(node.name), n, node.width)

    children = [plan.by_name(child) for child in node.children]
    deps = dependencies(node, children, n)

    if node.kind in (PASS, SHIFT, HASH, SUB, THETA, NTHETA):
        child_name, index, _ = deps[0]
        return content(plan, child_name, index, source_order)
    if node.kind == ADD:
        left = content(plan, deps[0][0], deps[0][1], source_order)
        right = content(plan, deps[1][0], deps[1][1], source_order)
        return left + right
    if node.kind == REDUCE:
        values = content(plan, deps[0][0], deps[0][1], source_order)
        # Reduktory zwracają pole RATIONAL — para (licznik, mianownik).
        if node.param == "sumc":
            return (sum(values), 1)
        if node.param == "min":
            return (min(values), 1)
        if node.param == "max":
            return (max(values), 1)
        average = Fraction(sum(values), len(values))
        return (average.numerator, average.denominator)
    if node.kind == AGSE:
        src = children[0]
        step, length = node.param
        fields = []
        for offset in range(abs(length)):
            flat = n * step + offset
            record = content(plan, src.name, flat // src.width, source_order)
            fields.append(record[flat % src.width])
        # Orientacja okna jest konwencją prezentacyjną ustaloną obserwacyjnie
        # na zbiorze kalibracyjnym: dodatnia długość daje pole najnowsze jako
        # pierwsze, ujemna odwraca. Odwzorowanie w czasie (które rekordy wchodzą
        # do okna) pochodzi z definicji operatora, nie z obserwacji.
        if length > 0:
            fields.reverse()
        return tuple(fields)
    raise OracleError(f"oracle: brak modelu treści dla {node.kind}")
