#!/usr/bin/env python3
"""Kampania exhaustive i kwalifikacja mutacji dla K19/G16."""

import argparse
import json
from fractions import Fraction
from itertools import product

from reference import (
    Observation,
    agse_tail,
    agse_window,
    compare_observations,
    reduce_sum,
    retained_capacity_agse,
    subtract_index,
    subtract_tail,
)


def check_subtract(limit: int) -> tuple[int, int]:
    checked = 0
    for source_den, target_num, target_den in product(
        range(1, limit + 1), repeat=3
    ):
        source = Fraction(1, source_den)
        target = Fraction(target_num, target_den)
        if target < source:
            continue
        for strict in (False, True):
            tail = subtract_tail(source, target, 0, strict)
            ratio = target / source
            retained_max = 1
            for n in range(2 * ratio.denominator + 4):
                index = subtract_index(source, target, n)
                physical = Fraction(tail + n) * ratio
                if index == 0:
                    available = physical >= 0
                else:
                    available = physical > index if strict else physical >= index
                if not available:
                    raise AssertionError(
                        f"SUBTRACT: src={source} dst={target} n={n} W={tail}"
                    )
                if strict:
                    count = physical.numerator // physical.denominator + 2
                    retained_max = max(retained_max, count - index)
                checked += 1
            if strict:
                compiler_bound = (
                    (Fraction(tail) * ratio).numerator
                    // (Fraction(tail) * ratio).denominator
                    + 2
                )
                if compiler_bound < retained_max:
                    raise AssertionError(
                        f"SUBTRACT capacity: src={source} dst={target}: "
                        f"{compiler_bound} < {retained_max}"
                    )
    return checked, 0


def check_agse(limit: int) -> tuple[int, int]:
    checked = 0
    for width, step, length, source_tail in product(
        range(1, limit + 1),
        range(1, limit + 1),
        range(1, limit + 1),
        range(3),
    ):
        tail = agse_tail(width, step, length, source_tail, True)
        for n in range(4 * width + 4):
            last_record = (n * step + length - 1) // width
            physical = Fraction(tail + n) * step / width
            if not physical > source_tail + last_record:
                raise AssertionError(
                    f"AGSE: F={width} k={step} L={length} "
                    f"Wsrc={source_tail} n={n} W={tail}"
                )
            checked += 1

        required, compiler_bound = retained_capacity_agse(
            width, step, length, source_tail, source_tail == 0
        )
        if compiler_bound < required:
            raise AssertionError(
                f"capacity: F={width} k={step} L={length} "
                f"Wsrc={source_tail}: {compiler_bound} < {required}"
            )
    return checked, 0


def check_nulls_and_reductions() -> dict:
    values = (10, 20, None, 40, 50, 60)
    forward = tuple(agse_window(values, 1, 3, n) for n in range(4))
    mirror = tuple(agse_window(values, 1, -3, n) for n in range(4))
    sums = tuple((reduce_sum(window),) for window in forward)
    expected = Observation(
        interval=Fraction(1),
        tail=3,
        schema=("INTEGER", "INTEGER", "INTEGER"),
        records=forward,
    )
    mutants = {
        "partial_window": Observation(
            expected.interval,
            0,
            expected.schema,
            ((10, None, None),) + forward,
        ),
        "null_to_zero": Observation(
            expected.interval,
            expected.tail,
            expected.schema,
            tuple(tuple(0 if x is None else x for x in row) for row in forward),
        ),
        "gap_injection": Observation(
            expected.interval,
            expected.tail,
            expected.schema,
            forward,
            gaps=(2,),
        ),
        "materialization_change": Observation(
            expected.interval,
            expected.tail,
            expected.schema,
            forward,
            materialization="VOLATILE",
        ),
    }
    detected = {
        name: compare_observations(expected, mutant)
        for name, mutant in mutants.items()
    }
    if not all(detected.values()):
        raise AssertionError(f"niewykryte mutacje: {detected}")
    if mirror[0] != (10, 20, None) or sums[:3] != ((30,), (60,), (90,)):
        raise AssertionError("NULL or reduction changed the semantics")
    return {
        "forward": forward,
        "mirror": mirror,
        "sums": sums,
        "mutations": detected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--json")
    args = parser.parse_args()

    subtract_checks, _ = check_subtract(args.limit)
    agse_checks, _ = check_agse(args.limit)
    payload = check_nulls_and_reductions()
    result = {
        "limit": args.limit,
        "subtract_phase_checks": subtract_checks,
        "agse_phase_checks": agse_checks,
        "mutations": payload["mutations"],
        "gap_policy": "computed streams: empty",
        "verdict": "OK",
    }
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, ensure_ascii=False, default=str)
    print(
        f"OK: SUBTRACT={subtract_checks} faz, AGSE={agse_checks} faz, "
        f"mutacje={len(payload['mutations'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
