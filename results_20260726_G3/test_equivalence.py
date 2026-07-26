#!/usr/bin/env python3
"""Macierz K2/G3: mutacje, exhaustive i property-based dla reguły R1."""

import argparse
import json
import random
import sys
import time
from fractions import Fraction

from cases import SPECIAL_CASES, exhaustive_cases, period
from mutants import MUTANTS
from reference import (
    compare_observations,
    compare_structural_case,
    interleave_trace,
    lhs_observation,
    matched_offsets,
    rhs_observation,
    trace_null_coverage,
)


def run_mutations():
    results = {}
    for name, make_pair in MUTANTS.items():
        expected, mutant = make_pair()
        differences = compare_observations(expected, mutant)
        results[name] = {
            "detected": bool(differences),
            "layers": differences,
            "verdict": "OK" if differences else "PROBLEM: mutacja niewykryta",
        }

    # Nieskrócony stosunek jest kontrolą benign: 6/4 i 3/2 muszą być równe.
    i1, k1 = matched_offsets(6, 4, 1)
    i2, k2 = matched_offsets(3, 2, 1)
    left = lhs_observation(6, 4, i1, k1, 200)
    right = lhs_observation(3, 2, i2, k2, 200)
    # Czasy i interwały różnią się skalą 2, więc porównujemy ślad semantyczny
    # oraz ogon; stosunek, nie jednostka czasu, determinuje kolejność.
    benign = (
        [(x.source, x.source_index, x.values) for x in left.records]
        == [(x.source, x.source_index, x.values) for x in right.records]
        and left.tail == right.tail
    )
    results["unreduced_6_4_equals_3_2"] = {
        "detected": not benign,
        "layers": [] if benign else ["trace_or_tail"],
        "verdict": "OK (kontrola benign)" if benign else "PROBLEM: fałszywy alarm",
    }
    return results


def run_campaign(cases, label, verbose_every=0):
    started = time.monotonic()
    checked = 0
    positions = 0
    checksum = 0
    mismatches = []
    for a, b, multiplier, count in cases:
        ok, detail, case_checksum = compare_structural_case(a, b, multiplier, count)
        if not ok:
            mismatches.append(
                {
                    "case": f"{a}/{b}",
                    "multiplier": multiplier,
                    "count": count,
                    "detail": detail,
                }
            )
            if len(mismatches) >= 20:
                break
        checked += 1
        positions += count
        checksum ^= case_checksum
        if verbose_every and checked % verbose_every == 0:
            print(f"  {label}: {checked} przypadków", file=sys.stderr)
    return {
        "label": label,
        "cases": checked,
        "positions": positions,
        "checksum64": f"{checksum:016x}",
        "mismatches": mismatches,
        "seconds": round(time.monotonic() - started, 3),
    }


def special_cases():
    for a, b in SPECIAL_CASES:
        yield a, b, 2, max(120, 10 * period(a, b))


def random_cases(seed, count):
    rng = random.Random(seed)
    for _ in range(count):
        a = rng.randint(1, 10**6)
        b = rng.randint(1, 10**6)
        multiplier = rng.randint(0, 10)
        # Dla wielkich P testujemy długi prefiks, ale nie próbujemy materializować
        # całego okresu liczącego miliony pozycji.
        positions = min(max(200, 2 * period(a, b)), 2000)
        yield a, b, multiplier, positions


def check_payload_domain():
    delta_a = Fraction(1, 10)
    delta_b = Fraction(1, 5)
    shift_a, shift_b = matched_offsets(delta_a, delta_b, 2)
    lhs = lhs_observation(delta_a, delta_b, shift_a, shift_b, 1000)
    rhs = rhs_observation(delta_a, delta_b, shift_a + shift_b, 1000)
    differences = compare_observations(lhs, rhs)
    coverage = trace_null_coverage(lhs.records)
    valid = not differences and all(coverage.values())
    return {
        "valid": valid,
        "differences": differences,
        "coverage": coverage,
    }


def check_unmatched_guard():
    results = []
    for a, b in SPECIAL_CASES:
        ratio = Fraction(a, b)
        shift_a, shift_b = matched_offsets(a, b, 1)
        shift_b += 1
        lhs = interleave_trace(
            ratio.numerator,
            ratio.denominator,
            120,
            shift_a=shift_a,
            shift_b=shift_b,
        )
        rhs = rhs_observation(
            ratio.numerator,
            ratio.denominator,
            shift_a + shift_b,
            120,
        )
        differs = lhs != rhs.records
        results.append({"case": f"{a}/{b}", "rejected": differs})
    return {
        "cases": results,
        "all_rejected": all(result["rejected"] for result in results),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--seed", type=int, default=20260726)
    parser.add_argument("--json")
    args = parser.parse_args()

    print("== 1/4 kwalifikacja mutacji ==")
    mutations = run_mutations()
    for name, info in mutations.items():
        print(f"  {name:30s} {info['verdict']}: {', '.join(info['layers']) or '-'}")
    blocking = [name for name, info in mutations.items() if not info["verdict"].startswith("OK")]
    if blocking:
        print(f"PRZERWANO: nieskuteczne kontrole: {blocking}", file=sys.stderr)
        return 1

    print("\n== 2/4 jawne wartości i mapy NULL ==")
    payload_domain = check_payload_domain()
    print(f"  pokrycie: {payload_domain['coverage']}; wynik={payload_domain['valid']}")
    if not payload_domain["valid"]:
        return 1
    unmatched = check_unmatched_guard()
    print(
        f"  niedopasowane przesunięcia odrzucone: "
        f"{sum(case['rejected'] for case in unmatched['cases'])}/{len(unmatched['cases'])}"
    )
    if not unmatched["all_rejected"]:
        return 1

    limit = 32 if args.quick else 256
    print(f"\n== 3/4 exhaustive 1 <= a,b <= {limit}, co najmniej 10P pozycji ==")
    exhaustive = run_campaign(
        exhaustive_cases(limit),
        f"exhaustive<={limit}",
        verbose_every=2048,
    )
    print(
        f"  {exhaustive['cases']} przypadków, {exhaustive['positions']} pozycji, "
        f"{len(exhaustive['mismatches'])} rozbieżności, {exhaustive['seconds']} s"
    )

    random_count = 500 if args.quick else 10_000
    print(f"\n== 4/4 property-based: {random_count} par do 10^6 ==")
    random_result = run_campaign(
        random_cases(args.seed, random_count),
        "property<=1e6",
        verbose_every=1000,
    )
    special = run_campaign(special_cases(), "special")
    print(
        f"  losowe: {random_result['cases']} przypadków, {random_result['positions']} pozycji, "
        f"{len(random_result['mismatches'])} rozbieżności, {random_result['seconds']} s"
    )
    print(
        f"  obowiązkowe: {special['cases']} przypadków, {special['positions']} pozycji, "
        f"{len(special['mismatches'])} rozbieżności"
    )

    campaigns = [exhaustive, random_result, special]
    verdict = all(not campaign["mismatches"] for campaign in campaigns)
    summary = {
        "seed": args.seed,
        "quick": args.quick,
        "mutations": mutations,
        "payload_domain": payload_domain,
        "unmatched_guard": unmatched,
        "campaigns": campaigns,
        "totals": {
            "cases": sum(campaign["cases"] for campaign in campaigns),
            "positions": sum(campaign["positions"] for campaign in campaigns),
            "mismatches": sum(len(campaign["mismatches"]) for campaign in campaigns),
        },
        "verdict": "OK" if verdict else "MISMATCH",
    }
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, ensure_ascii=False)

    print(f"\nWYNIK: {'zero rozbieżności' if verdict else 'ROZBIEŻNOŚCI OBECNE'}")
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
