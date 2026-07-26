#!/usr/bin/env python3
"""Kontrole mutacyjne K2/G3.

Każda funkcja zwraca obserwację celowo naruszającą jedną warstwę relacji.
Mutacje są uruchamiane i kwalifikowane przed właściwą macierzą.
"""

from dataclasses import replace
from fractions import Fraction

from reference import (
    lhs_observation,
    matched_offsets,
    rhs_observation,
    with_dropped_nulls,
)


def witness():
    delta_a = Fraction(1, 10)
    delta_b = Fraction(1, 5)
    shift_a, shift_b = matched_offsets(delta_a, delta_b, 1)
    lhs = lhs_observation(delta_a, delta_b, shift_a, shift_b, 120)
    rhs = rhs_observation(delta_a, delta_b, shift_a + shift_b, 120)
    return delta_a, delta_b, shift_a, shift_b, lhs, rhs


def rhs_shift_plus_one():
    delta_a, delta_b, shift_a, shift_b, lhs, _ = witness()
    return lhs, rhs_observation(delta_a, delta_b, shift_a + shift_b + 1, 120)


def lhs_shift_off_by_one():
    delta_a, delta_b, shift_a, shift_b, _, rhs = witness()
    # Celowo omijamy gwardę dopasowania i mutujemy bezpośrednio siatkę:
    # błędna implementacja zachowywałaby się jak RHS z innym czasem.
    wrong = rhs_observation(delta_a, delta_b, shift_a + shift_b + 1, 120)
    return rhs, wrong


def swapped_arguments():
    delta_a, delta_b, shift_a, shift_b, lhs, _ = witness()
    return lhs, rhs_observation(
        delta_a,
        delta_b,
        shift_a + shift_b,
        120,
        swap_sources=True,
    )


def tie_to_b():
    delta_a, delta_b, shift_a, shift_b, lhs, _ = witness()
    return lhs, rhs_observation(
        delta_a,
        delta_b,
        shift_a + shift_b,
        120,
        tie_to_a=False,
    )


def null_map_dropped():
    *_, lhs, rhs = witness()
    return lhs, with_dropped_nulls(rhs, zeros=False)


def null_as_zero():
    *_, lhs, rhs = witness()
    return lhs, with_dropped_nulls(rhs, zeros=True)


def injected_gap():
    *_, lhs, rhs = witness()
    return lhs, replace(rhs, gaps=(7,))


def changed_schema():
    *_, lhs, rhs = witness()
    return lhs, replace(rhs, schema=(("aux", "INTEGER"), ("value", "INTEGER")))


MUTANTS = {
    "rhs_shift_plus_one": rhs_shift_plus_one,
    "lhs_shift_off_by_one": lhs_shift_off_by_one,
    "swapped_arguments": swapped_arguments,
    "tie_to_b": tie_to_b,
    "null_map_dropped": null_map_dropped,
    "null_as_zero": null_as_zero,
    "injected_gap": injected_gap,
    "changed_schema": changed_schema,
}

