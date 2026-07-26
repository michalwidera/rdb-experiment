#!/usr/bin/env python3
"""Niezależny oracle reguły R1 (shift-matching).

Definicja nie używa wzoru Beatty'ego ani pętli wykonawczej RetractorDB.
Przeplot jest scaleniem dwóch arytmetycznych siatek zdarzeń:

    A[k] = (k + 1) * delta_a
    B[j] =  j      * delta_b

Operator ``>N`` opóźnia całą siatkę o ``N * delta``. Gdy
``i*delta_a == k*delta_b``, obie siatki lewej strony przesuwają się o ten
sam czas fizyczny. Prawa strona przesuwa gotowy przeplot o ``i+k`` slotów
wyniku.
"""

from dataclasses import dataclass, replace
from fractions import Fraction
from math import gcd
from typing import Iterable

SOURCE_A = "A"
SOURCE_B = "B"
SCHEMA = (("value", "INTEGER"), ("aux", "INTEGER"))


@dataclass(frozen=True)
class TraceItem:
    phase: int
    logical_time: Fraction
    source: str
    source_index: int
    values: tuple[int | None, int | None]

    @property
    def null_bitset(self) -> tuple[bool, bool]:
        return tuple(value is None for value in self.values)


@dataclass(frozen=True)
class Observation:
    interval: Fraction
    tail: int
    schema: tuple[tuple[str, str], ...]
    records: tuple[TraceItem, ...]
    gaps: tuple[int, ...] = ()
    materialization: str = "DEFAULT"


def reduced_ratio(delta_a: Fraction | int, delta_b: Fraction | int) -> tuple[int, int]:
    """Zwraca względnie pierwsze ``p,q`` dla ``delta_a/delta_b = p/q``."""
    ratio = Fraction(delta_a) / Fraction(delta_b)
    return ratio.numerator, ratio.denominator


def output_interval(delta_a: Fraction | int, delta_b: Fraction | int) -> Fraction:
    delta_a = Fraction(delta_a)
    delta_b = Fraction(delta_b)
    if delta_a <= 0 or delta_b <= 0:
        raise ValueError("interwały muszą być dodatnie")
    return (delta_a * delta_b) / (delta_a + delta_b)


def ceil_fraction(value: Fraction) -> int:
    return -(-value.numerator // value.denominator)


def source_values(source: str, index: int) -> tuple[int | None, int | None]:
    """Deterministyczny rekord dwupolowy z częściowymi i pełnymi NULL-ami."""
    if source == SOURCE_A:
        values: list[int | None] = [index + 1, 100_000 + index]
        if index % 17 in {1, 5, 6, 7}:
            values[0] = None
        if index % 19 in {3, 7}:
            values[1] = None
    elif source == SOURCE_B:
        values = [1_000_000 + index, 2_000_000 + index]
        if index % 13 in {2, 9}:
            values[0] = None
        if index % 23 in {4, 9}:
            values[1] = None
    else:
        raise ValueError(f"nieznane źródło: {source}")
    return values[0], values[1]


def _next_event(
    delta_a: Fraction,
    delta_b: Fraction,
    next_a: int,
    next_b: int,
    shift_a: int,
    shift_b: int,
    tie_to_a: bool,
) -> tuple[str, int, Fraction]:
    time_a = (next_a + 1 + shift_a) * delta_a
    time_b = (next_b + shift_b) * delta_b
    if time_a < time_b or (time_a == time_b and tie_to_a):
        return SOURCE_A, next_a, time_a
    return SOURCE_B, next_b, time_b


def interleave_trace(
    delta_a: Fraction | int,
    delta_b: Fraction | int,
    count: int,
    *,
    shift_a: int = 0,
    shift_b: int = 0,
    tie_to_a: bool = True,
    swap_sources: bool = False,
) -> tuple[TraceItem, ...]:
    """Scala bezpośrednio dwie przesunięte siatki zdarzeń."""
    delta_a = Fraction(delta_a)
    delta_b = Fraction(delta_b)
    if delta_a <= 0 or delta_b <= 0:
        raise ValueError("interwały muszą być dodatnie")
    if min(count, shift_a, shift_b) < 0:
        raise ValueError("liczba pozycji i przesunięcia muszą być nieujemne")

    trace: list[TraceItem] = []
    next_a = 0
    next_b = 0
    for phase in range(count):
        source, index, logical_time = _next_event(
            delta_a, delta_b, next_a, next_b, shift_a, shift_b, tie_to_a
        )
        if source == SOURCE_A:
            next_a += 1
        else:
            next_b += 1
        if swap_sources:
            source = SOURCE_B if source == SOURCE_A else SOURCE_A
        trace.append(
            TraceItem(
                phase=phase,
                logical_time=logical_time,
                source=source,
                source_index=index,
                values=source_values(source, index),
            )
        )
    return tuple(trace)


def interleave_tail(delta_a: Fraction | int, delta_b: Fraction | int) -> int:
    """Ogon przyczynowego przeplotu wyprowadzony z dostępności B[0].

    B[0] staje się dostępne po jednym interwale B. Liczba pełnych taktów A,
    które trzeba odczekać, jest więc sufitem ``delta_b/delta_a``.
    """
    return ceil_fraction(Fraction(delta_b) / Fraction(delta_a))


def matched_offsets(delta_a: Fraction | int, delta_b: Fraction | int, multiplier: int) -> tuple[int, int]:
    if multiplier < 0:
        raise ValueError("mnożnik przesunięcia musi być nieujemny")
    p, q = reduced_ratio(delta_a, delta_b)
    return multiplier * q, multiplier * p


def lhs_observation(
    delta_a: Fraction | int,
    delta_b: Fraction | int,
    shift_a: int,
    shift_b: int,
    count: int,
    *,
    tie_to_a: bool = True,
) -> Observation:
    """Bezpośrednia lewa strona: phi(tau_i(A), tau_k(B))."""
    delta_a = Fraction(delta_a)
    delta_b = Fraction(delta_b)
    delay_a = shift_a * delta_a
    delay_b = shift_b * delta_b
    if delay_a != delay_b:
        raise ValueError("lewa strona R1 wymaga dopasowanych przesunięć")
    delta_c = output_interval(delta_a, delta_b)
    delay_slots = delay_a / delta_c
    if delay_slots.denominator != 1:
        raise AssertionError("dopasowany czas nie jest całkowitą liczbą slotów wyniku")
    return Observation(
        interval=delta_c,
        tail=interleave_tail(delta_a, delta_b) + delay_slots.numerator,
        schema=SCHEMA,
        records=interleave_trace(
            delta_a,
            delta_b,
            count,
            shift_a=shift_a,
            shift_b=shift_b,
            tie_to_a=tie_to_a,
        ),
    )


def rhs_observation(
    delta_a: Fraction | int,
    delta_b: Fraction | int,
    combined_shift: int,
    count: int,
    *,
    tie_to_a: bool = True,
    swap_sources: bool = False,
) -> Observation:
    """Bezpośrednia prawa strona: tau_(i+k)(phi(A,B))."""
    delta_a = Fraction(delta_a)
    delta_b = Fraction(delta_b)
    delta_c = output_interval(delta_a, delta_b)
    delay = combined_shift * delta_c
    base = interleave_trace(
        delta_a,
        delta_b,
        count,
        tie_to_a=tie_to_a,
        swap_sources=swap_sources,
    )
    shifted = tuple(replace(item, logical_time=item.logical_time + delay) for item in base)
    return Observation(
        interval=delta_c,
        tail=interleave_tail(delta_a, delta_b) + combined_shift,
        schema=SCHEMA,
        records=shifted,
    )


def compare_observations(expected: Observation, actual: Observation) -> list[str]:
    differences = []
    for field in ("interval", "tail", "schema", "records", "gaps", "materialization"):
        if getattr(expected, field) != getattr(actual, field):
            differences.append(field)
    return differences


def with_dropped_nulls(observation: Observation, *, zeros: bool) -> Observation:
    """Mutant mapy NULL: usuwa bity, opcjonalnie zastępując brak wartością zero."""
    records = []
    for item in observation.records:
        values = tuple(0 if value is None and zeros else value for value in item.values)
        if not zeros:
            values = tuple(index + 7 if value is None else value for index, value in enumerate(values))
        records.append(replace(item, values=values))
    return replace(observation, records=tuple(records))


def trace_null_coverage(trace: Iterable[TraceItem]) -> dict[str, int]:
    result = {"present": 0, "partial_null": 0, "all_null": 0}
    for item in trace:
        count = sum(item.null_bitset)
        if count == 0:
            result["present"] += 1
        elif count == len(item.null_bitset):
            result["all_null"] += 1
        else:
            result["partial_null"] += 1
    return result


def compare_structural_case(
    a: int,
    b: int,
    multiplier: int,
    count: int,
) -> tuple[bool, str, int]:
    """Szybka wersja macierzy: porównuje oba niezależne scalania strumieniowo.

    Czasy są liczone w całkowitych jednostkach wspólnej skali. Dzięki temu
    pełne exhaustive<=256 nie wykonuje setek milionów operacji na Fraction.
    """
    divisor = gcd(a, b)
    p = a // divisor
    q = b // divisor
    shift_a = multiplier * q
    shift_b = multiplier * p
    common_delay = multiplier * p * q

    lhs_a = lhs_b = rhs_a = rhs_b = 0
    checksum = 0
    for phase in range(count):
        lhs_time_a = (lhs_a + 1 + shift_a) * p
        lhs_time_b = (lhs_b + shift_b) * q
        if lhs_time_a <= lhs_time_b:
            lhs_source, lhs_index, lhs_time = 0, lhs_a, lhs_time_a
            lhs_a += 1
        else:
            lhs_source, lhs_index, lhs_time = 1, lhs_b, lhs_time_b
            lhs_b += 1

        rhs_time_a = (rhs_a + 1) * p
        rhs_time_b = rhs_b * q
        if rhs_time_a <= rhs_time_b:
            rhs_source, rhs_index, rhs_time = 0, rhs_a, rhs_time_a + common_delay
            rhs_a += 1
        else:
            rhs_source, rhs_index, rhs_time = 1, rhs_b, rhs_time_b + common_delay
            rhs_b += 1

        if (lhs_source, lhs_index, lhs_time) != (rhs_source, rhs_index, rhs_time):
            return (
                False,
                f"phase={phase}: lhs={(lhs_source, lhs_index, lhs_time)}, "
                f"rhs={(rhs_source, rhs_index, rhs_time)}",
                checksum,
            )
        checksum = ((checksum * 1_000_003) ^ (lhs_source << 24) ^ lhs_index ^ lhs_time) & ((1 << 64) - 1)
    return True, "", checksum

