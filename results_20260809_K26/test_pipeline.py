#!/usr/bin/env python3
"""Testy znanych odpowiedzi i mutantow aparatury wykonawczej K26."""

import csv
import subprocess
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

import capture_worker
from calib import gen_calib
from calib import gen_slots
import reduce_results
import run_matrix_worker

HERE = Path(__file__).resolve().parent


def write_probe(path, values, iterations=None):
    iterations = iterations if iterations is not None else range(len(values))
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["iter", "compute_ns", "wake_lag_ns", "e2e_ns"])
        for iteration, value in zip(iterations, values):
            writer.writerow([iteration, value, 0, value])


class CalibrationPlanTest(unittest.TestCase):
    def test_f9x_named_fields_are_scaled(self):
        source = (HERE / "rql" / "F9_X_Q8.rql").read_text()
        scaled, touched = gen_calib.scale_plan(source, Fraction(2))
        self.assertEqual(touched, 4)
        self.assertIn("DECLARE front INTEGER STREAM A, 1/50", scaled)
        self.assertIn("DECLARE rear INTEGER STREAM D, 1/25", scaled)

    def test_intervals_are_read_from_plan_dump(self):
        dump = "A(1/100) file\nB(1/50) file\nM(1/150)\n"
        self.assertEqual(gen_slots.extract_intervals(dump), ["1/100", "1/150", "1/50"])


class ProbeReductionTest(unittest.TestCase):
    def test_known_median_and_p99(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "slot.csv"
            values = list(range(1, 101))
            write_probe(path, values)
            result = reduce_results.summarize_probe(path)
            self.assertEqual(result["compute_median_ns"], 50)
            self.assertEqual(result["compute_p99_ns"], 100)
            self.assertEqual(result["probe_rows"], 100)

    def test_gap_mutant_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "slot.csv"
            write_probe(path, [10, 20, 30], [0, 2, 3])
            with self.assertRaisesRegex(reduce_results.ReductionError, "ciagly"):
                reduce_results.summarize_probe(path)

    def test_complete_timing_export_and_summary_mutant(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with (HERE / "blocks.tsv").open(newline="") as handle:
                blocks = list(csv.DictReader(handle, delimiter="\t"))
            first_summary = None
            for index, block in enumerate(blocks):
                cell = root / "raw" / f"cell-{index:04d}"
                cell.mkdir(parents=True)
                write_probe(cell / "slot.csv", [100, 200, 300])
                summary = {
                    "family": block["family"], "profile": block["profile"], "q": block["q"],
                    "block": block["block"], "order": block["order"],
                    "compute_median_ns": 200, "compute_p99_ns": 300, "slot_ns": 1000,
                    "lost_records": 0, "probe_rows": 3, "public_appends": 10,
                    "temp_before_millic": 40000, "temp_after_millic": 41000,
                }
                reduce_results.write_tsv(cell / "summary.tsv", reduce_results.SUMMARY_COLUMNS, [summary])
                first_summary = first_summary or cell / "summary.tsv"
            warmup = root / "warmup" / "DEFAULT"
            warmup.mkdir(parents=True)
            write_probe(warmup / "slot.csv", [1])
            reduce_results.write_tsv(warmup / "summary.tsv", reduce_results.SUMMARY_COLUMNS, [{
                "family": "F9-R2", "profile": "DEFAULT", "q": 32, "block": 0, "order": 0,
                "compute_median_ns": 1, "compute_p99_ns": 1, "slot_ns": 1000,
                "lost_records": 0, "probe_rows": 1, "public_appends": 10,
                "temp_before_millic": 40000, "temp_after_millic": 40000,
            }])
            rows = reduce_results.timing_rows(root, HERE / "blocks.tsv")
            self.assertEqual(len(rows), 1440)
            text = first_summary.read_text().replace("\t200\t300\t", "\t201\t300\t", 1)
            first_summary.write_text(text)
            with self.assertRaisesRegex(reduce_results.ReductionError, "surowa sonda"):
                reduce_results.timing_rows(root, HERE / "blocks.tsv")


class BlocksTest(unittest.TestCase):
    def test_each_family_is_exact_product(self):
        for family in run_matrix_worker.FAMILIES:
            rows = run_matrix_worker.rows_for_family(HERE / "blocks.tsv", family)
            self.assertEqual(len(rows), 480)

    def test_stop8_threshold_is_strict_and_lost_record_wins(self):
        self.assertIsNone(run_matrix_worker.stop_reason(0, 800, 1000))
        self.assertEqual(run_matrix_worker.stop_reason(0, 801, 1000),
                         "p99_over_80_percent_slot")
        self.assertEqual(run_matrix_worker.stop_reason(1, 100, 1000), "lost_records")


class MechanismKnownAnswerTest(unittest.TestCase):
    def test_q8_instances_match_predeclaration(self):
        expected = {"F9-R2": 1, "F9-R1": 1, "F9-X": 1}
        for family, instances in expected.items():
            plan = family.replace("-", "_") + "_Q8"
            cell = reduce_results.mechanism_table.cell(
                HERE / "pilot" / "out" / f"DEFAULT_{plan}.plan",
                HERE / "pilot" / "out" / f"DEFAULT_{plan}.probe",
                HERE / "rql" / f"{plan}.rql",
            )
            self.assertEqual(reduce_results.rdb_instances(family, cell), instances)

    def test_missing_work_mutant_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "job.out"
            path.write_text("LOGICAL substrat: zapisy=1 bajty=9  publiczne: rekordy=1\n")
            with self.assertRaises(reduce_results.ReductionError):
                reduce_results.read_single_match(path, reduce_results.FLINK_WORK, "WORK")

    def test_complete_mechanism_export_has_108_unique_rows(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            rdb, flink = root / "rdb", root / "flink"
            rdb_counters = (
                "LOGICAL substrat: dopisania=100 nadpisania=0 bajty=900  "
                "publiczne: dopisania=800 nadpisania=0 bajty=7200\n"
                "WORK agse: okna=0 elementy=0 odczyty=0  eval: wywolania=1000 tokeny=2000  "
                "hash: wybory=300  add: scalenia=400\n"
            )
            flink_counters = (
                "LOGICAL substrat: zapisy=100 bajty=900  publiczne: rekordy=800\n"
                "WORK eval: wywolania=1000 tokeny=2000  hash: wybory=300  add: scalenia=400\n"
            )
            for family in reduce_results.FAMILIES:
                slug = reduce_results.FAMILY_FILE[family]
                for q in reduce_results.Q_GRID:
                    for profile in reduce_results.PROFILES:
                        path = rdb / profile / f"{slug}_Q{q}" / "cell.counters"
                        path.parent.mkdir(parents=True)
                        path.write_text(rdb_counters)
                    for variant in ("natural", "manual"):
                        path = flink / f"{slug}_{variant}_q{q}" / "job.out"
                        path.parent.mkdir(parents=True)
                        path.write_text(flink_counters)
            rows = reduce_results.mechanism_rows(
                rdb, flink, HERE / "corpus_validation" / "plans", HERE / "rql",
                HERE / "flink" / "results" / "flink_q_curve.tsv",
                HERE / "flink" / "results" / "flink_work_q_curve.tsv",
            )
            keys = {(row["family"], row["system"], row["profile"], row["q"]) for row in rows}
            self.assertEqual(len(rows), 108)
            self.assertEqual(len(keys), 108)
            indexed = {(row["family"], row["system"], row["profile"], row["q"]): row for row in rows}
            self.assertEqual(indexed[("F9-R1", "RDB", "DEFAULT", 8)]["work_costly_evals"], 800)
            self.assertEqual(indexed[("F9-R2", "RDB", "DEFAULT", 8)]["work_costly_evals"], 400)
            self.assertEqual(indexed[("F9-R1", "FLINK", "NATURAL", 8)]["work_costly_evals"], 800)
            self.assertEqual(indexed[("F9-X", "FLINK", "NATURAL", 8)]["work_costly_evals"], 400)


class WorkerCaptureTest(unittest.TestCase):
    def test_exact_inventory(self):
        text = "\n".join(f"{key}\tvalue-{key}" for key in capture_worker.PROFILES)
        parsed = capture_worker.parse_key_values(text, capture_worker.PROFILES)
        self.assertEqual(list(parsed), capture_worker.PROFILES)
        binary_script, _ = capture_worker.remote_script("/code", 3)
        self.assertIn("RDB_OPT_SIMPLIFY_EXPRESSIONS=ON", binary_script)
        self.assertIn('wc -l <<<"$info"', binary_script)

    def test_duplicate_mutant_is_rejected(self):
        with self.assertRaises(capture_worker.CaptureError):
            capture_worker.parse_key_values("a\t1\na\t2\n", ["a"])


class CalibrationAnnexTest(unittest.TestCase):
    def test_analyzer_writes_annex_and_rejects_effect_access(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            runs, slots, annex = root / "runs", root / "slots.tsv", root / "ANEKS-1.tsv"
            slots.write_text("family\tscale\tmin_slot_ms\n" + "".join(
                f"{family}\t{scale}\t100.0\n"
                for scale in ("1_4", "1_2", "1_1", "2_1", "4_1")
                for family in ("F9_R2", "F9_R1", "F9_X")
            ))
            for profile in ("DEFAULT", "NO_R2_CANON", "NO_R1_FACTOR", "NO_R1_NO_R2"):
                for scale in ("1_4", "1_2", "1_1", "2_1", "4_1"):
                    for family in ("F9_R2", "F9_R1", "F9_X"):
                        path = runs / profile / f"{family}_s{scale}" / "slot.csv"
                        path.parent.mkdir(parents=True)
                        write_probe(path, [10_000_000, 20_000_000, 30_000_000])
            completed = subprocess.run(
                [str(HERE / "calib" / "analyze_calib.py"), "--runs", str(runs),
                 "--slots", str(slots), "--out", str(annex)],
                text=True, capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            values = run_matrix_worker.key_values(annex)
            self.assertEqual(values["calibration_saw_effect"], "no")
            self.assertEqual(values["runs"], "60")
            self.assertIn("slot_min_ms_F9_X", values)


if __name__ == "__main__":
    unittest.main()
