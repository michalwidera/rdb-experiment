#!/usr/bin/env python3
"""Focused unit tests for K26 gates that differ materially from K23."""

import re
import unittest
from pathlib import Path

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


class ScriptContractTest(unittest.TestCase):
    """Kontrakty, ktorych zlamanie kosztowalo K26v2 fazy calej kampanii."""

    CAMPAIGN = "K26v3"
    HERE = Path(__file__).resolve().parent

    def scripts(self):
        for suffix in ("*.sh", "*.py"):
            for path in sorted(self.HERE.rglob(suffix)):
                if "__pycache__" not in path.parts:
                    yield path

    def test_every_cited_predeclaration_paragraph_exists(self):
        """D1: skrypty cytowaly paragrafy 8.1 i 0.2, ktorych predeklaracja nie miala."""
        text = (self.HERE / "PREDEKLARACJA.md").read_text(encoding="utf-8")
        headings = set(re.findall(r"^#{2,3}\s+(\d+(?:\.\d+)?)\.", text, re.M))
        missing = []
        for path in self.scripts():
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                # Cytat innego dokumentu nie jest cytatem predeklaracji.
                if re.search(r"\b\w+\.md\b", line) and "PREDEKLARACJA.md" not in line:
                    continue
                for cited in re.findall(r"§\s?(\d+(?:\.\d+)?)", line):
                    if cited not in headings:
                        missing.append(f"{path.relative_to(self.HERE)}:{number} cytuje §{cited}")
        self.assertEqual(missing, [], "cytowane paragrafy nie istnieja w PREDEKLARACJA.md")

    def test_no_default_points_at_another_campaign(self):
        """D2: domyslny CODE_REPO wskazywal katalog uniewaznionej kampanii K26."""
        allowed = {"/home/michal/github/retractordb", "$HOME/" + self.CAMPAIGN,
                   "/home/michal/" + self.CAMPAIGN}
        offenders = []
        pattern = re.compile(r'^(\w+)="\$\{\1:-([^}]*)\}"')
        # Ta sama pulapka siedziala po stronie Pythona: `--code-repo` mialo
        # domyslnie `Path.home() / "K26"`, czyli katalog uniewaznionej kampanii.
        python_default = re.compile(r'"--code-repo".*default=Path\.home\(\)\s*/\s*"([^"]+)"')
        for path in self.scripts():
            if path.suffix == ".py":
                for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                    found = python_default.search(line)
                    if found and found.group(1) != self.CAMPAIGN:
                        offenders.append(f"{path.relative_to(self.HERE)}:{number} -> {found.group(1)}")
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                found = pattern.match(line.strip())
                if not found:
                    continue
                name, default = found.groups()
                if "CODE_REPO" not in name:
                    continue
                if default not in allowed:
                    offenders.append(f"{path.relative_to(self.HERE)}:{number} {name}={default}")
        self.assertEqual(offenders, [], "domyslne repozytorium kodu spoza biezacej kampanii")

    def test_no_path_default_names_a_foreign_campaign(self):
        """Zadna domyslna sciezka nie moze wskazywac cudzej kampanii."""
        foreign = re.compile(r"[Kk]2[0-9](?:v\d)?(?![0-9])")
        offenders = []
        for path in self.scripts():
            if path.suffix != ".sh":
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if line.lstrip().startswith("#") or ":-" not in line:
                    continue
                for name in foreign.findall(line):
                    if name.lower() != self.CAMPAIGN.lower():
                        offenders.append(f"{path.relative_to(self.HERE)}:{number} -> {name}")
        self.assertEqual(offenders, [], "domyslna wartosc wskazuje cudza kampanie")

    def test_annex1_is_shipped_to_worker_and_gated_on_both_sides(self):
        """D3: ANEKS-1 powstaje na hoscie, a konsumuje go worker.

        W K26v2 nic go nie przenosilo, a bramka `macierz` sprawdzala kopie hosta,
        czyli nie te, ktorej uzywa macierz: byla zielona i bezuzyteczna.
        Zywy test obu stron nalezy do fazy z wlaczonym workerem.
        """
        analyzer = (self.HERE / "calib" / "analyze_calib.py").read_text(encoding="utf-8")
        self.assertIn("def ship_to_worker", analyzer)
        self.assertIn("ANEKS-1_rate.tsv", analyzer)
        self.assertIn("test ! -e", analyzer, "wysylka musi odmawiac nadpisania")

        gate = (self.HERE / "freeze_check.sh").read_text(encoding="utf-8")
        matrix = gate.split("check_matrix()", 1)[1].split("\n}", 1)[0]
        self.assertIn("WORKER_CAMPAIGN_DIR", matrix, "bramka nie siega po kopie workera")
        self.assertIn("ANEKS-1 na workerze wobec kopii hosta", matrix)
