#!/usr/bin/env python3
"""Niezależny model granic operatorów objętych K19/G16.

Model używa wyłącznie indeksów postępujących i wymiernego czasu logicznego.
Nie importuje kodu RetractorDB ani jego zamkniętych postaci C++.
"""

from dataclasses import dataclass
from fractions import Fraction
from math import ceil, gcd


def ceil_fraction(value: Fraction) -> int:
    return -(-value.numerator // value.denominator)


def subtract_index(delta_source: Fraction, delta_target: Fraction, n: int) -> int:
    if delta_target < delta_source:
        raise ValueError("wynik SUBTRACT nie może być szybszy od źródła")
    return ceil_fraction(Fraction(n) * delta_target / delta_source)


def subtract_tail(
    delta_source: Fraction,
    delta_target: Fraction,
    source_tail: int,
    strict_boundary: bool,
) -> int:
    ratio = delta_target / delta_source
    period = ratio.denominator
    phase = Fraction(period - 1, period)
    value = (Fraction(source_tail) + phase) / ratio
    return value.numerator // value.denominator + int(
        strict_boundary or value.denominator != 1
    )


def agse_phase_bound(width: int, step: int, length: int) -> int:
    unit = gcd(width, step)
    return ((abs(length) - 1) // unit) * unit


def agse_tail(
    width: int,
    step: int,
    length: int,
    source_tail: int,
    strict_boundary: bool,
) -> int:
    numerator = source_tail * width + agse_phase_bound(width, step, length)
    value = Fraction(numerator, step)
    if strict_boundary:
        return value.numerator // value.denominator + 1
    return ceil_fraction(value)


def agse_window(values, step: int, length: int, n: int):
    """Pełne okno logiczne; dodatnia szerokość: najnowsze pole najpierw."""
    start = n * step
    window = tuple(values[start : start + abs(length)])
    if len(window) != abs(length):
        raise IndexError("niepełne okno nie należy do obserwowalnego strumienia")
    return window if length < 0 else tuple(reversed(window))


def reduce_sum(window):
    present = [value for value in window if value is not None]
    return None if not present else sum(present)


@dataclass(frozen=True)
class Observation:
    interval: Fraction
    tail: int
    schema: tuple[str, ...]
    records: tuple[tuple[int | None, ...], ...]
    gaps: tuple[int, ...] = ()
    materialization: str = "DEFAULT"


def compare_observations(expected: Observation, actual: Observation) -> list[str]:
    return [
        field
        for field in (
            "interval",
            "tail",
            "schema",
            "records",
            "gaps",
            "materialization",
        )
        if getattr(expected, field) != getattr(actual, field)
    ]


def retained_capacity_agse(
    width: int,
    step: int,
    length: int,
    source_tail: int,
    source_declared: bool,
) -> tuple[int, int]:
    """Zwraca (wymagane minimum z symulacji faz, bound kompilatora)."""
    tail = agse_tail(width, step, length, source_tail, True)
    ratio = Fraction(step, width)
    maximum = 1
    period = width // gcd(width, step)
    for n in range(4 * period + 4):
        physical = Fraction(tail + n) * ratio
        if source_declared:
            count = physical.numerator // physical.denominator + 2
        else:
            count = max(0, ceil_fraction(physical - source_tail))
        first_record = (n * step) // width
        maximum = max(maximum, count - first_record)

    phase = Fraction(width - gcd(width, step), width)
    retained = Fraction(tail) * ratio - source_tail + phase
    bound = (
        retained.numerator // retained.denominator + 2
        if source_declared
        else ceil_fraction(retained)
    )
    return maximum, max(bound, 1)
