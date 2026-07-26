#!/usr/bin/env python3
"""Przypadki obowiązkowe oraz deterministyczne generatory kampanii K2/G3."""

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class EngineCase:
    name: str
    delta_a_num: int
    delta_b_num: int
    multiplier: int
    loops: int
    min_interval_ms: int = 2

    @property
    def ratio(self) -> Fraction:
        return Fraction(self.delta_a_num, self.delta_b_num)


SPECIAL_CASES = [
    (1, 1),
    (1, 2),
    (2, 1),
    (3, 2),
    (6, 4),
    (3, 1),
    (1, 3),
    (1, 16),
    (16, 1),
    (7, 11),
    (160, 147),
    (1000, 999),
]


ENGINE_CASES = [
    EngineCase("p2_equal", 1, 1, 1, 90, 10),
    EngineCase("p3_regression", 1, 2, 1, 70, 100),
    EngineCase("p3_reverse", 2, 1, 1, 80, 10),
    EngineCase("p4_skew", 1, 3, 1, 90, 10),
    EngineCase("p5_remainder1", 2, 3, 1, 100, 10),
    EngineCase("p7_remainder1", 3, 4, 1, 110, 10),
    EngineCase("p8_remainder2", 3, 5, 1, 120, 10),
    EngineCase("p5_fast", 3, 2, 2, 130, 2),
    EngineCase("p5_slow", 3, 2, 2, 70, 20),
    EngineCase("p18_fast", 7, 11, 1, 180, 2),
    EngineCase("p18_slow", 7, 11, 1, 90, 20),
    EngineCase("p3_unreduced", 6, 4, 1, 90, 10),
    EngineCase("p307_audio", 160, 147, 1, 1050, 2),
]


def period(a: int, b: int) -> int:
    ratio = Fraction(a, b)
    return ratio.numerator + ratio.denominator


def exhaustive_cases(limit: int):
    for a in range(1, limit + 1):
        for b in range(1, limit + 1):
            multiplier = 1 + ((a * 17 + b * 31) % 3)
            yield a, b, multiplier, 10 * period(a, b)
