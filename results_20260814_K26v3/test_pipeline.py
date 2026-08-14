#!/usr/bin/env python3
"""Testy znanych odpowiedzi i mutantow aparatury wykonawczej K26."""

import csv
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
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


class FamilyWrapperTest(unittest.TestCase):
    """Wrapper rodziny: status nienadpisywalny, ale podejscia wznawialne.

    Bieg przerwany twardym wylaczeniem nie zostawia `runner.rc`, wiec wrapper
    musi dac sie uruchomic po raz drugi na tym samym katalogu kontrolnym.
    Nienadpisywalny pozostaje wylacznie status zakonczonej rodziny.
    """

    def wrapper_root(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        shutil.copy2(HERE / "run_matrix_family.sh", root / "run_matrix_family.sh")
        runner = root / "run_matrix_worker.py"
        runner.write_text(
            "#!/usr/bin/env bash\n"
            "echo fake-runner \"$@\"\n"
            "exit ${FAKE_RC:-0}\n"
        )
        runner.chmod(0o755)
        (root / "control").mkdir()
        return temp, root

    def run_wrapper(self, root, runner_rc=0, resume=False):
        environment = dict(os.environ, FAKE_RC=str(runner_rc))
        if resume:
            environment["RESUME"] = "1"
        return subprocess.run(
            [str(root / "run_matrix_family.sh"), "F9-R2", "3", "/code", "/p6", "/out",
             "/archive", str(root / "control")],
            text=True, capture_output=True, env=environment,
        )

    def test_wrapper_persists_zero_status_and_log(self):
        temp, root = self.wrapper_root()
        with temp:
            completed = self.run_wrapper(root)
            control = root / "control"
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual((control / "runner.rc").read_text(), "0\n")
            self.assertIn("fake-runner --family F9-R2", (control / "runner.log").read_text())
            attempts = (control / "started.tsv").read_text().splitlines()
            self.assertEqual(attempts[0].split("\t")[:2], ["attempt", "family"])
            self.assertEqual(attempts[1].split("\t")[:2], ["1", "F9-R2"])

    def test_wrapper_persists_failure_status(self):
        temp, root = self.wrapper_root()
        with temp:
            completed = self.run_wrapper(root, runner_rc=7)
            self.assertEqual(completed.returncode, 7)
            self.assertEqual((root / "control" / "runner.rc").read_text(), "7\n")

    def test_wrapper_refuses_to_overwrite_status(self):
        temp, root = self.wrapper_root()
        with temp:
            self.assertEqual(self.run_wrapper(root).returncode, 0)
            repeated = self.run_wrapper(root, resume=True)
            self.assertEqual(repeated.returncode, 2)
            self.assertIn("odmowa nadpisania", repeated.stderr)
            self.assertEqual((root / "control" / "runner.rc").read_text(), "0\n")

    def test_second_attempt_after_crash_appends_and_resumes(self):
        """Twarde wylaczenie: brak `runner.rc`, wiec rodzina musi ruszyc ponownie."""
        temp, root = self.wrapper_root()
        with temp:
            control = root / "control"
            self.assertEqual(self.run_wrapper(root).returncode, 0)
            (control / "runner.rc").unlink()  # tego pliku bieg przerwany nie zapisuje
            self.assertEqual(self.run_wrapper(root, resume=True).returncode, 0)
            attempts = (control / "started.tsv").read_text().splitlines()
            self.assertEqual(len(attempts), 3, "kazde podejscie ma dopisac wlasny wiersz")
            self.assertEqual(attempts[2].split("\t")[0], "2")
            self.assertEqual(attempts[2].split("\t")[4], "1")
            log = (control / "runner.log").read_text()
            self.assertEqual(log.count("=== podejscie"), 2, "log poprzedniego podejscia zginal")
            self.assertIn("--resume", log)


class ChainTest(unittest.TestCase):
    """N10 pkt 3: lancuch rodzin nalezy do workera, nie do sesji trzymanej przez SSH.

    Kazde wywolanie obsluguje jedna rodzine i konczy sie prosba o restart, bo
    usluga jest wlaczona na boot. Powrot po zaniku zasilania i restart miedzy
    rodzinami ida wiec ta sama sciezka — testy chodza po niej wielokrotnie.
    """

    FAMILIES = ["F9-R2", "F9-R1", "F9-X"]

    def chain_root(self, family_rc=0, stop8=False, run_complete=True):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        family = root / "family.sh"
        # Atrapa trzyma sie tego samego kontraktu co `run_matrix_family.sh`:
        # zastany `runner.rc` jest odmowa, a nie cichym nadpisaniem statusu.
        lines = ["#!/usr/bin/env bash", 'out="$5"', 'archives="$6"', 'control="$7"',
                 'if [ -e "$control/runner.rc" ]; then echo "odmowa nadpisania" >&2; exit 2; fi',
                 'mkdir -p "$out" "$archives"',
                 f'printf "%s\\n" "$1" >>"{root}/family-calls.txt"']
        if stop8:
            lines.append('touch "$out/STOP-8"')
        if run_complete:
            # Runner konczy rodzine w tej kolejnosci: wynik, archiwum, suma.
            lines.append('printf "480/480\\n" >"$out/RUN_COMPLETE"')
            lines.append('printf "tar\\n" >"$archives/K26v3-P8-$1.tar.gz"')
            lines.append('printf "sum\\n" >"$archives/K26v3-P8-$1.sha256"')
        lines.append('printf "%s\\n" "$?" >"$control/runner.rc"')
        lines.append(f"exit {family_rc}")
        family.write_text("\n".join(lines) + "\n")
        family.chmod(0o755)
        sudo = root / "sudo.sh"
        sudo.write_text(
            "#!/usr/bin/env bash\n"
            f'printf "%s\\n" "$*" >>"{root}/sudo-calls.txt"\n'
            "exit 0\n"
        )
        sudo.chmod(0o755)
        return temp, root

    def run_chain(self, root):
        environment = dict(
            os.environ, P8_OUT=str(root / "p8"), CONTROL=str(root / "control"),
            ARCHIVES=str(root / "archives"), FAMILY_SCRIPT=str(root / "family.sh"),
            SUDO=str(root / "sudo.sh"), SETTLE_SECONDS="0",
            CODE_REPO="/code", P6_RDB="/p6",
        )
        return subprocess.run([str(HERE / "run_matrix_chain.sh")], text=True,
                              capture_output=True, env=environment)

    def calls(self, root, name):
        path = root / name
        return path.read_text().splitlines() if path.exists() else []

    def test_one_invocation_runs_one_family_and_asks_for_reboot(self):
        temp, root = self.chain_root()
        with temp:
            completed = self.run_chain(root)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(self.calls(root, "family-calls.txt"), ["F9-R2"])
            sudo = self.calls(root, "sudo-calls.txt")
            self.assertIn("systemctl --no-block reboot", sudo)
            self.assertTrue(any("scaling_governor" in call for call in sudo),
                            "governor musi byc ustawiony po kazdym boocie")
            self.assertFalse(any("disable" in call for call in sudo))
            self.assertFalse((root / "p8" / "P8_COMPLETE").exists())

    def test_three_invocations_walk_the_whole_chain_and_disable_the_unit(self):
        temp, root = self.chain_root()
        with temp:
            for _ in self.FAMILIES:
                self.assertEqual(self.run_chain(root).returncode, 0)
            self.assertEqual(self.calls(root, "family-calls.txt"), self.FAMILIES)
            sudo = self.calls(root, "sudo-calls.txt")
            self.assertEqual(sudo.count("systemctl --no-block reboot"), 2,
                             "po ostatniej rodzinie worker nie ma sie restartowac")
            self.assertIn("systemctl disable k26v3-p8.service", sudo)
            self.assertEqual((root / "p8" / "P8_COMPLETE").read_text(), "3/3 rodzin\n")
            # Kolejny boot nie moze zaczac niczego od nowa.
            self.assertEqual(self.run_chain(root).returncode, 0)
            self.assertEqual(self.calls(root, "family-calls.txt"), self.FAMILIES)

    def test_stop8_halts_the_chain_and_never_reboots(self):
        temp, root = self.chain_root(family_rc=2, stop8=True, run_complete=False)
        with temp:
            completed = self.run_chain(root)
            self.assertEqual(completed.returncode, 2)
            halt = run_matrix_worker.key_values(root / "p8" / "HALT")
            self.assertEqual(halt["reason"], "stop8")
            self.assertEqual(halt["family"], "F9-R2")
            self.assertNotIn("systemctl --no-block reboot", self.calls(root, "sudo-calls.txt"))
            # Zastany HALT blokuje kazde nastepne wejscie, takze po boocie.
            repeated = self.run_chain(root)
            self.assertEqual(repeated.returncode, 2)
            self.assertEqual(self.calls(root, "family-calls.txt"), ["F9-R2"])

    def test_failure_without_stop8_halts_as_apparatus(self):
        temp, root = self.chain_root(family_rc=3, run_complete=False)
        with temp:
            completed = self.run_chain(root)
            self.assertEqual(completed.returncode, 3)
            self.assertEqual(run_matrix_worker.key_values(root / "p8" / "HALT")["reason"],
                             "apparatus")

    def test_family_counted_but_without_closed_archive_is_repacked(self):
        """Twarde wylaczenie miedzy `RUN_COMPLETE` a suma archiwum.

        Rodzina policzona, ale bez zamknietego archiwum, nie moze byc uznana za
        zrobiona: archiwum jest tym, co wyjezdza z workera. Niezamknieta paczka
        musi zniknac, inaczej runner odmowi jej nadpisania.
        """
        temp, root = self.chain_root()
        with temp:
            done = root / "p8" / "F9-R2"
            done.mkdir(parents=True)
            (done / "RUN_COMPLETE").write_text("480/480\n")
            (root / "archives").mkdir()
            partial = root / "archives" / "K26v3-P8-F9-R2.tar.gz"
            partial.write_text("urwane pakowanie")
            control = root / "control" / "F9-R2"
            control.mkdir(parents=True)
            (control / "runner.rc").write_text("0\n")  # status podejscia sprzed przerwy
            self.assertEqual(self.run_chain(root).returncode, 0)
            self.assertEqual(self.calls(root, "family-calls.txt"), ["F9-R2"])
            self.assertEqual(partial.read_text(), "tar\n", "niezamknieta paczka przetrwala")
            self.assertTrue((root / "archives" / "K26v3-P8-F9-R2.sha256").exists())
            rotated = list(control.glob("runner.rc.*"))
            self.assertEqual(len(rotated), 1, "status poprzedniego podejscia mial pojsc do historii")

    def test_zero_status_without_run_complete_is_apparatus(self):
        """Rodzina bez `RUN_COMPLETE` nie liczy sie za zrobiona, choc runner dal 0."""
        temp, root = self.chain_root(run_complete=False)
        with temp:
            completed = self.run_chain(root)
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(run_matrix_worker.key_values(root / "p8" / "HALT")["reason"],
                             "apparatus_bez_run_complete")


class WorkerServiceTest(unittest.TestCase):
    """Kontrakt unitu systemd — jedynego miejsca, w ktorym opisany jest start P8."""

    def unit_text(self):
        completed = subprocess.run([str(HERE / "install_worker_service.sh"), "--print"],
                                   text=True, capture_output=True, check=True)
        return completed.stdout

    def test_unit_starts_at_boot_and_never_restarts_itself(self):
        text = self.unit_text()
        self.assertIn("WantedBy=multi-user.target", text)
        self.assertIn("Restart=no", text)
        self.assertNotIn("Restart=always", text)
        self.assertNotIn("Restart=on-failure", text,
                         "STOP-8 ma zatrzymac lancuch, a nie zapetlic go")
        self.assertIn("ExecStart=" + str(HERE / "run_matrix_chain.sh"), text)
        self.assertIn("User=michal", text)

    def test_install_refuses_to_overwrite_a_different_unit(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            unit = root / "k26v3-p8.service"
            unit.write_text("[Service]\nExecStart=/bin/false\n")
            completed = subprocess.run(
                [str(HERE / "install_worker_service.sh")], text=True, capture_output=True,
                env=dict(os.environ, UNIT_PATH=str(unit), CONTROL=str(root / "control"),
                         SUDO=str(root / "nie-ma-sudo")),
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("rozni sie od generowanego", completed.stderr)
            self.assertEqual(unit.read_text(), "[Service]\nExecStart=/bin/false\n")


class NoScreenTest(unittest.TestCase):
    """Po N10 zadna czesc P8 nie wisi na sesji `screen` po zadnej ze stron."""

    P8_SCRIPTS = ["run_matrix_chain.sh", "run_matrix_family.sh", "install_worker_service.sh",
                  "start_matrix_p8.sh", "collect_p8_archives.sh"]

    def code_lines(self, name):
        for number, line in enumerate((HERE / name).read_text().splitlines(), start=1):
            if not line.lstrip().startswith("#"):
                yield number, line

    def test_p8_no_longer_depends_on_screen(self):
        for name in self.P8_SCRIPTS:
            for number, line in self.code_lines(name):
                self.assertNotIn("screen", line, f"{name}:{number} — P8 nie uzywa juz screen")

    def test_no_script_uses_the_two_broken_screen_constructs(self):
        """D4 i D5 jako kontrakt statyczny.

        Wersja K26v2 tego testu WYMAGALA obecnosci `screen -DmS`, czyli utrwalala
        defekt D4. Konstrukcje moga wystepowac wylacznie w komentarzach, jako
        zapis historii.
        """
        for path in sorted(HERE.rglob("*.sh")):
            for number, line in self.code_lines(path.relative_to(HERE)):
                self.assertNotIn("-DmS", line, f"{path.name}:{number} — `-DmS` nie forkuje (D4)")
                self.assertNotIn("-Q select", line, f"{path.name}:{number} — `-Q select` wisi (D5)")


MINIMAL_ABLATION = {"F9-R2": "NO_R2_CANON", "F9-R1": "NO_R1_FACTOR", "F9-X": "NO_R1_NO_R2"}


def legacy_instances(family, cell):
    """Definicja z K26v2, zachowana wylacznie po to, by test D7 mial zeby."""
    if family == "F9-R1":
        return sum(name.startswith("STREAM_HASH_") for name in cell["substrates"])
    return len(cell["selects"])


class MechanismKnownAnswerTest(unittest.TestCase):
    def test_q8_instances_match_predeclaration(self):
        # §7.2: `instances` liczy zmaterializowane substraty wewnetrzne. F9-X
        # rozklada wspolny podplan na piec wezlow, co zgadza sie z tabela §6.
        expected = {"F9-R2": 1, "F9-R1": 1, "F9-X": 5}
        for family, instances in expected.items():
            plan = family.replace("-", "_") + "_Q8"
            cell = reduce_results.mechanism_table.cell(
                HERE / "pilot" / "out" / f"DEFAULT_{plan}.plan",
                HERE / "pilot" / "out" / f"DEFAULT_{plan}.probe",
                HERE / "rql" / f"{plan}.rql",
            )
            self.assertEqual(reduce_results.rdb_instances(cell), instances)

    def _plan_cells(self, family, q):
        plan = f"{family.replace('-', '_')}_Q{q}"
        plans = HERE / "corpus_validation" / "plans"
        out = {}
        for profile in ("DEFAULT", MINIMAL_ABLATION[family]):
            out[profile] = reduce_results.mechanism_table.cell(
                plans / profile / f"{plan}.plan",
                plans / profile / f"{plan}.stderr",
                HERE / "rql" / f"{plan}.rql",
            )
        return out["DEFAULT"], out[MINIMAL_ABLATION[family]]

    def test_default_never_materializes_more_than_ablation(self):
        """Straznik izolacji mechanizmu (§7.2) na zamrozonych zrzutach planu.

        To jest bramka P4. W K26v2 ten warunek po raz pierwszy wykonal sie
        dopiero w P9 i uniewaznil iteracje (D7).
        """
        for family in MINIMAL_ABLATION:
            for q in (1, 2, 4, 8, 16, 32):
                default, ablation = self._plan_cells(family, q)
                self.assertLessEqual(
                    reduce_results.rdb_instances(default),
                    reduce_results.rdb_instances(ablation),
                    f"{family} Q={q}: DEFAULT materializuje wiecej substratow niz ablacja",
                )

    def test_legacy_hash_named_counter_would_invert_the_guard(self):
        """D7 wprost: stara definicja odwraca straznika w F9-R1 przy Q=1 i Q=2."""
        inverted = []
        for q in (1, 2, 4, 8, 16, 32):
            default, ablation = self._plan_cells("F9-R1", q)
            if legacy_instances("F9-R1", default) > legacy_instances("F9-R1", ablation):
                inverted.append(q)
        self.assertEqual(inverted, [1, 2])

    def test_broken_input_exits_with_two_never_one(self):
        """§7.5: kod 1 znaczy wazny wynik negatywny i awaria nie moze go udawac.

        W K26v2 nieprzechwycony `ZeroDivisionError` zakonczyl werdykt kodem 1 (D6).
        """
        with tempfile.TemporaryDirectory() as name:
            matrix = Path(name)
            subprocess.run([str(HERE / "verdict.py"), "--emit-synthetic", str(matrix)],
                           check=True, capture_output=True)
            # (a) blad rozpoznany przez `run` — kod 2 juz w K26v2
            path = matrix / "mechanism.tsv"
            rows = path.read_text().splitlines()
            header = rows[0].split("\t")
            broken = rows[1].split("\t")
            broken[header.index("substrate_bytes")] = "nie-liczba"
            rows[1] = "\t".join(broken)
            path.write_text("\n".join(rows) + "\n")
            done = subprocess.run([str(HERE / "verdict.py"), "--matrix", str(matrix)],
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 2, done.stdout + done.stderr)

            # (b) awaria NIEROZPOZNANA — w K26v2 wychodzila kodem 1
            path.write_text("\n".join(rows[:1] + rows[1:]) + "\n")
            gates = matrix / "gates.tsv"
            gates.unlink()
            gates.mkdir()
            done = subprocess.run([str(HERE / "verdict.py"), "--matrix", str(matrix)],
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
            self.assertIn("BRAK WERDYKTU", done.stderr)

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
                # `--worker ""` wylacza rozsylke na workera (D3); test jest lokalny,
                # a domyslne zachowanie MUSI wysylac, zeby nikt o tym nie zapomnial.
                [str(HERE / "calib" / "analyze_calib.py"), "--runs", str(runs),
                 "--slots", str(slots), "--out", str(annex), "--worker", ""],
                text=True, capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            values = run_matrix_worker.key_values(annex)
            self.assertEqual(values["calibration_saw_effect"], "no")
            self.assertEqual(values["runs"], "60")
            self.assertIn("slot_min_ms_F9_X", values)


if __name__ == "__main__":
    unittest.main()


class ResumeTest(unittest.TestCase):
    """N10: bieg przerwany w polowie musi dac sie wznowic bez straty i bez duplikatu.

    Pomiar trwa 16 h na rodzine, wiec kampania nie moze wymagac, zeby urzadzenie
    przetrwalo caly ten czas bez przerwy. Test uzywa zredukowanej macierzy — regula
    ksiegowania jest ta sama niezaleznie od liczby komorek.
    """

    def cell(self, root, complete=True, median=200):
        root.mkdir(parents=True, exist_ok=True)
        write_probe(root / "slot.csv", [100, median, 300])
        (root / "run.rc").write_text("0\n")
        if complete:
            reduce_results.write_tsv(root / "summary.tsv", reduce_results.SUMMARY_COLUMNS, [{
                "family": "F9-R2", "profile": "DEFAULT", "q": 8, "block": 1, "order": 0,
                "compute_median_ns": median, "compute_p99_ns": 300, "slot_ns": 1000,
                "lost_records": 0, "probe_rows": 3, "public_appends": 10,
                "temp_before_millic": 40000, "temp_after_millic": 41000,
            }])
        return root

    def test_complete_cell_is_recognised(self):
        with tempfile.TemporaryDirectory() as name:
            path = self.cell(Path(name) / "cell")
            self.assertTrue(run_matrix_worker.cell_is_complete(path))

    def test_partial_cells_are_never_trusted(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            missing_summary = self.cell(root / "a", complete=False)
            self.assertFalse(run_matrix_worker.cell_is_complete(missing_summary))

            nonzero_rc = self.cell(root / "b")
            (nonzero_rc / "run.rc").write_text("2\n")
            self.assertFalse(run_matrix_worker.cell_is_complete(nonzero_rc))

            truncated = self.cell(root / "c")
            write_probe(truncated / "slot.csv", [100])  # sonda krotsza niz w summary
            self.assertFalse(run_matrix_worker.cell_is_complete(truncated))

            no_probe = self.cell(root / "d")
            (no_probe / "slot.csv").unlink()
            self.assertFalse(run_matrix_worker.cell_is_complete(no_probe))

    def test_resume_skips_done_cells_and_redoes_partial_ones(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            done = self.cell(root / "done")
            before = (done / "summary.tsv").read_bytes()
            partial = self.cell(root / "partial", complete=False)
            (partial / "marker").write_text("slad przerwanego biegu")

            self.assertFalse(run_matrix_worker.prepare_cell(done, resume=True))
            self.assertEqual((done / "summary.tsv").read_bytes(), before,
                             "komorka sprzed przerwy zostala naruszona")
            self.assertTrue(run_matrix_worker.prepare_cell(partial, resume=True))
            self.assertFalse(partial.exists(), "niekompletna komorka musi zniknac przed powtorzeniem")

    def test_without_resume_existing_cell_is_refused(self):
        with tempfile.TemporaryDirectory() as name:
            path = self.cell(Path(name) / "cell")
            with self.assertRaisesRegex(run_matrix_worker.MatrixError, "odmowa nadpisania"):
                run_matrix_worker.prepare_cell(path, resume=False)

    def test_missing_cell_is_simply_run(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "nie-ma"
            self.assertTrue(run_matrix_worker.prepare_cell(path, resume=True))
            self.assertTrue(run_matrix_worker.prepare_cell(path, resume=False))

    def _rate_annex(self, path):
        reduce_results.write_tsv(path, ["key", "value"], [
            {"key": "rate_scale", "value": "4"},
            {"key": "slot_min_ms_F9_R2", "value": "25"},
            {"key": "slot_min_ms_F9_R1", "value": "25"},
            {"key": "slot_min_ms_F9_X", "value": "25"},
        ])
        return path

    def test_interrupted_run_resumes_to_a_complete_matrix(self):
        """Pelna ksiegowosc wznowienia na prawdziwej petli `main()`.

        `run_one` jest zastapione atrapa, zeby test nie trwal 16 h; przerwanie
        udaje `KeyboardInterrupt`, ktorego `main()` nie lapie — tak jak nie zlapie
        zabicia procesu. Zywy test twardego wylaczenia workera jest osobno.
        """
        crash_after = 100
        calls, crashed = [], []

        def fake_run_one(family, profile, q, block, order, out, *rest, **kwargs):
            if not crashed and len(calls) == crash_after and not kwargs.get("warmup"):
                crashed.append(True)  # przerwanie zdarza sie RAZ, nie przy kazdym wznowieniu
                raise KeyboardInterrupt("udawane zabicie procesu")
            calls.append(out)
            out.mkdir(parents=True, exist_ok=False)
            write_probe(out / "slot.csv", [100, 200, 300])
            (out / "run.rc").write_text("0\n")
            reduce_results.write_tsv(out / "summary.tsv", reduce_results.SUMMARY_COLUMNS, [{
                "family": family, "profile": profile, "q": q, "block": block, "order": order,
                "compute_median_ns": 200, "compute_p99_ns": 300, "slot_ns": 1000,
                "lost_records": 0, "probe_rows": 3, "public_appends": 10,
                "temp_before_millic": 40000, "temp_after_millic": 41000,
            }])
            return {"compute_p99_ns": 300}

        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            out, archives = root / "out", root / "archives"
            annex = self._rate_annex(root / "rate.tsv")
            argv = ["run_matrix_worker.py", "--family", "F9-R2", "--out", str(out),
                    "--archive-dir", str(archives), "--p6-rdb", str(root / "p6"),
                    "--rate-annex", str(annex)]

            with mock.patch.object(run_matrix_worker, "check_environment"), \
                 mock.patch.object(run_matrix_worker, "run_one", fake_run_one), \
                 mock.patch.object(sys, "argv", argv):
                with self.assertRaises(KeyboardInterrupt):
                    run_matrix_worker.main()

            # `crash_after` liczy WSZYSTKIE zapisy: 4 warm-upy + reszta to komorki.
            written = len(calls)
            cells_done = crash_after - len(run_matrix_worker.PROFILES)
            self.assertEqual(written, crash_after)
            self.assertFalse((out / "RUN_COMPLETE").exists())

            # Ostatnia komorka udaje przerwanie W TRAKCIE zapisu.
            truncated = calls[-1]
            (truncated / "summary.tsv").unlink()
            fingerprints = {path: (path / "summary.tsv").read_bytes() for path in calls[:-1]}

            with mock.patch.object(run_matrix_worker, "check_environment"), \
                 mock.patch.object(run_matrix_worker, "run_one", fake_run_one), \
                 mock.patch.object(sys, "argv", argv + ["--resume"]):
                self.assertEqual(run_matrix_worker.main(), 0)

            self.assertEqual((out / "RUN_COMPLETE").read_text(), "480/480\n")
            summaries = [p for p in out.rglob("summary.tsv") if "warmup" not in p.parts]
            self.assertEqual(len(summaries), 480, "macierz nie jest kompletna")
            self.assertEqual(len(summaries), len({p.parent for p in summaries}), "duplikat komorki")
            for path, content in fingerprints.items():
                self.assertEqual((path / "summary.tsv").read_bytes(), content,
                                 f"komorka sprzed przerwy zmieniona: {path}")
            self.assertIn(truncated, calls[written:], "niekompletna komorka nie zostala powtorzona")
            self.assertEqual(len(calls) - written, 480 - cells_done + 1,
                             "wznowienie policzylo komorki juz zrobione")
