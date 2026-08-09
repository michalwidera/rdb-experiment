#!/usr/bin/env python3
"""Focused unit tests for K26 gates that differ materially from K23."""

import unittest

import gen_corpus
import oracle_values as ov
import validate_corpus


def stream(values, nullmap=None):
    return {
        "name": "m1",
        "fields": [("INTEGER", "m1_0")],
        "config": [],
        "width": 4,
        "records": [(value,) for value in values],
        "nullmap": nullmap or ["Segments: 1", f"records: {len(values)}", "no nulls"],
    }


class ObservableIdentityTest(unittest.TestCase):
    def test_shorter_optimized_tail_is_accepted(self):
        baseline = stream(range(2100))
        optimized = stream(range(2102))
        self.assertEqual(ov.compare_rdb_observable(optimized, baseline, "R1"), 2100)

    def test_longer_optimized_tail_is_rejected(self):
        baseline = stream(range(2102))
        optimized = stream(range(2100))
        with self.assertRaisesRegex(ov.Mismatch, r"Lat\(optimized\) <= Lat\(baseline\)"):
            ov.compare_rdb_observable(optimized, baseline, "R1-mutant")

    def test_common_prefix_value_change_is_rejected(self):
        baseline = stream(range(2100))
        values = list(range(2102))
        values[777] = -1
        with self.assertRaises(ov.Mismatch) as raised:
            ov.compare_rdb_observable(stream(values), baseline, "value-mutant")
        self.assertEqual(raised.exception.condition, "order_values")

    def test_null_or_gap_is_rejected(self):
        baseline = stream(range(2100))
        optimized = stream(range(2102), ["Segments: 1", "records: 2102", "gap: 7"])
        with self.assertRaises(ov.Mismatch) as raised:
            ov.compare_rdb_observable(optimized, baseline, "gap-mutant")
        self.assertEqual(raised.exception.condition, "null_gap_map")


class CorpusInventoryTest(unittest.TestCase):
    def test_generator_defines_exactly_21_plans(self):
        generated = sorted(name for name in gen_corpus.corpus() if name.startswith("rql/"))
        expected = [f"rql/{name}" for name in validate_corpus.expected_plans()]
        self.assertEqual(generated, expected)
        self.assertEqual(len(generated), 21)

    def test_historical_f9x_mutant_crosses_interleave_boundary(self):
        mutant = validate_corpus.HISTORICAL_INVALID_F9X
        self.assertIn("A[0]", mutant)
        self.assertIn("B[0]", mutant)
        self.assertIn("#", mutant)


if __name__ == "__main__":
    unittest.main()
