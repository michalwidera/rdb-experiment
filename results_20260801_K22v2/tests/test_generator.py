#!/usr/bin/env python3
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


generator = load("k22v2_generator", HERE / "generate_variants.py")
campaign = load("k22v2_campaign", HERE / "run_campaign.py")


class GeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="k22v2_generator_test_")
        generator.TASKS = Path(cls.temp.name) / "tasks"
        generator.generate_m1_f1(); generator.generate_m1_f2(); generator.generate_m1_f3()
        for family in generator.FAMILIES:
            generator.generate_m2(family)
            generator.generate_m3(family)
            generator.generate_m4(family)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_exactly_36_cores_and_no_cache(self):
        cores = [p for p in generator.TASKS.rglob("*") if p.name in {
            "core.rql", "core.py", "F1Fir.java", "F2Ecg.java", "F3Multirate.java"}]
        self.assertEqual(36, len(cores))
        self.assertFalse(list(generator.TASKS.rglob("__pycache__")))

    def test_all_rql_variants_compile(self):
        for path in generator.TASKS.glob("M*/*/rql/core.rql"):
            completed = subprocess.run([str(campaign.XRETRACTOR), str(path), "-c"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                       text=True, timeout=20, check=False)
            self.assertEqual(0, completed.returncode, f"{path}: {completed.stderr}")

    def test_all_python_variants_parse(self):
        for path in generator.TASKS.glob("M*/*/python/core.py"):
            compile(path.read_text(encoding="utf-8"), str(path), "exec")

    def test_all_java_variants_compile(self):
        for path in generator.TASKS.glob("M*/*/flink/*.java"):
            with tempfile.TemporaryDirectory(prefix="k22v2_javac_") as out:
                completed = subprocess.run([str(campaign.JAVAC), "-nowarn", "-cp", str(campaign.FLINK_JAR),
                                            "-d", out, str(path)], stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT, text=True, timeout=30, check=False)
                self.assertEqual(0, completed.returncode, f"{path}: {completed.stdout}")


class CampaignUnitTests(unittest.TestCase):
    def test_parse_tail(self):
        self.assertEqual(60, campaign.parse_tail("mwi_q(1/360)\ttail=60\n", "mwi_q"))

    def test_elide_pacing_only_one_line(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "core.py"
            diff = Path(temp) / "pacing.diff"
            source.write_text("if now < deadline:\n    pass\n", encoding="utf-8")
            changed = campaign.elide_pacing(source, "python", diff)
            self.assertIn("if False and now < deadline:", changed)
            self.assertIn("-if now < deadline:", diff.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
