#!/usr/bin/env python3
"""Uruchamia R593 K22v5: część semantyczna K22v5 (3 bazy i 12 wariantów, trzy modele, wspólny oracle)
na silniku dfcc42d2. Kopia results_20260801_K22v5/run_campaign.py; zmiany opisuje README.md."""

import argparse
import csv
import difflib
import filecmp
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "results_20260801_K22"
FROZEN = HERE.parent / "results_20260801_K22v5"
TASKS = FROZEN / "tasks"
CORES = HERE / "config/cores"
RESULTS = HERE / "results"
EVIDENCE = HERE / "evidence"
CODE = Path(os.environ.get("CODE_REPO", "/home/michal/github/retractordb"))
# Bez wartości domyślnej: ~/.local/bin nie jest buildem dfcc42d2. Obok xretractor musi leżeć xtrdb,
# bo emit_rql.py woła go po nazwie z PATH przypiętego do tego katalogu.
XRETRACTOR = Path(os.environ["XRETRACTOR"])
FLINK_JAR = Path(os.environ.get("FLINK_JAR", "/home/michal/opt/flink-2.3.0/lib/flink-dist-2.3.0.jar"))
JAVA = Path(os.environ.get("JAVA17", "/usr/lib/jvm/java-17-openjdk-amd64/bin/java"))
JAVAC = Path(os.environ.get("JAVAC17", "/usr/lib/jvm/java-17-openjdk-amd64/bin/javac"))
SPAN = 2000
FAMILY_DIR = {"F1": "F1_fir", "F2": "F2_ecg", "F3": "F3_multirate"}
JAVA_FILE = {"F1": "F1Fir.java", "F2": "F2Ecg.java", "F3": "F3Multirate.java"}
JAVA_CLASS = {"F1": "F1Fir", "F2": "F2Ecg", "F3": "F3Multirate"}
TARGET = {
    ("M4", "F1"): "f1_q", ("M4", "F2"): "mwi_q", ("M4", "F3"): "f3_q",
}


class CampaignError(RuntimeError):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(cmd, cwd, log, timeout=90, stdout_path=None, ok_codes=(0,)):
    with open(log, "w", encoding="utf-8") as handle:
        try:
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            env["PATH"] = f"{XRETRACTOR.parent}:{env.get('PATH', '')}"
            completed = subprocess.run(
                [str(x) for x in cmd], cwd=cwd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, timeout=timeout, check=False,
                env=env)
        except subprocess.TimeoutExpired as exc:
            handle.write((exc.stdout or "") if isinstance(exc.stdout, str) else "")
            handle.write(f"\nTIMEOUT po {timeout}s: {' '.join(map(str, cmd))}\n")
            raise CampaignError(f"timeout: {cmd[0]} ({cwd})") from exc
        handle.write(completed.stdout)
    if stdout_path:
        Path(stdout_path).write_text(completed.stdout, encoding="utf-8")
    if completed.returncode not in ok_codes:
        raise CampaignError(f"kod {completed.returncode}: {' '.join(map(str, cmd))}; log={log}")
    return completed.stdout if ok_codes == (0,) else (completed.returncode, completed.stdout)


def write_lines(path, values):
    path.write_text("".join(f"{value}\n" for value in values), encoding="utf-8")


def prepare_data(work, task, family):
    if family == "F1":
        write_lines(work / "f1_source.txt", [((i * 37) % 1000) - 500 for i in range(4096)])
        write_lines(work / "f1_source2.txt", [2000 - i for i in range(4097)])
        # Plik przeniesiony z test/IntegrationTest_parallel/dsp/ (300f23c6); treść bez zmian (freeze_check.sh).
        coef = [int(x) for x in (CODE / "test/IntegrationTest/dsp/filterremez.txt").read_text().split()]
        if task == "M2":
            coef += [0] * 19
        write_lines(work / "f1_coef.txt", coef)
    elif family == "F2":
        for name in ("rec205", "bp_coef.txt", "d_coef.txt"):
            shutil.copy2(CODE / "examples/ecg/rec205" / name, work / name)
    else:
        a = [i + 1 for i in range(8000)]
        b = [1001 + i for i in range(8000)]
        write_lines(work / "f3_a.txt", a)
        write_lines(work / "f3_b.txt", b)
        (work / "f3_a2.txt").write_text("".join(f"{v} {20000+i}\n" for i, v in enumerate(a)), encoding="utf-8")
        (work / "f3_b2.txt").write_text("".join(f"{v} {30000+i}\n" for i, v in enumerate(b)), encoding="utf-8")


def source_root(task, family):
    if task == "base":
        return PILOT / "corpus" / FAMILY_DIR[family]
    return TASKS / task / FAMILY_DIR[family]


def task_target(task, family):
    if (task, family) in TARGET:
        return TARGET[(task, family)]
    return {"F1": "f1_out", "F2": "qrs_out", "F3": "f3_out"}[family]


def parse_tail_origin(plan_text, target):
    # Od 5f310515 / 34db1a29 wydruk -c podaje tail i origin, każde tylko gdy niezerowe
    # (presenter.cpp, onlyCompileShowProgram); cisza strumienia trwa origin + tail slotów.
    match = re.search(rf"^{re.escape(target)}\([^\n]*\)((?:\t[^\n]*)?)$", plan_text, re.M)
    if not match:
        raise CampaignError(f"nie odczytano wiersza celu {target}")
    attrs = dict(item.split("=", 1) for item in match.group(1).split("\t") if "=" in item)
    return int(attrs.get("tail", 0)), int(attrs.get("origin", 0))


def k22v5_first_index():
    # Decyzja D1 (ii): rekord 0 artefaktu dostaje zamrożony pierwszy indeks logiczny K22v5.
    with (FROZEN / "results/semantic.csv").open(newline="", encoding="utf-8") as handle:
        return {(row["task"], row["family"]): int(row["tail"]) for row in csv.DictReader(handle)}


K22V5_FIRST = k22v5_first_index()


def compare(models, label0, cwd, log):
    cmd = [sys.executable, PILOT / "oracle/compare.py", "--span", str(SPAN)]
    for name in models:
        cmd += ["--tail", f"{name}={label0}"]
    cmd += [f"{name}={path}" for name, path in models.items()]
    code, out = run(cmd, cwd, log, timeout=60, ok_codes=(0, 1))
    return ("PASS" if code == 0 else "FAIL"), out


def load_stream(path):
    rows = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        family, variant, index, field, value, null, gap = line.split(",")
        rows.setdefault(int(index), []).append((field, value, null, gap))
    return rows


def constant_shift(rql_csv, other_csv, label0):
    # Klasa P (README, kryteria): ciągi zgodne przy stałym przesunięciu k != 0, |k| <= 10,
    # na indeksach [label0 + 10, label0 + SPAN - 10).
    rql, other = load_stream(rql_csv), load_stream(other_csv)
    for k in sorted(range(-10, 11), key=abs):
        if k and all(rql.get(i + k) == other.get(i) for i in range(label0 + 10, label0 + SPAN - 10)):
            return k
    return None


def elide_pacing(source, language, diff_path):
    old = source.read_text(encoding="utf-8")
    needle = "if now < deadline:" if language == "python" else "if (now < deadline) {"
    replacement = "if False and now < deadline:" if language == "python" else "if (false && now < deadline) {"
    if old.count(needle) != 1:
        raise CampaignError(f"{source}: oczekiwano jednego warunku pacing, jest {old.count(needle)}")
    new = old.replace(needle, replacement)
    diff = difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile=str(source), tofile="execution-copy")
    diff_path.write_text("".join(diff), encoding="utf-8")
    return new


def model_args(family, task, slots, out):
    common = ["--slots", str(slots), "--family", family, "--variant", task, "--out", str(out)]
    if family == "F1":
        args = ["--source", "f1_source.txt", "--coef", "f1_coef.txt"]
        if task == "M1":
            args += ["--source2", "f1_source2.txt"]
        return args + common
    if family == "F2":
        return ["--rec", "rec205", "--bp", "bp_coef.txt", "--d", "d_coef.txt"] + common
    return ["--a", "f3_a.txt", "--b", "f3_b.txt"] + common


def expected_rate(task, family):
    if task != "M3":
        return None
    return {"F1": ("1/750", "1_333_333", "1_333_333L"),
            "F2": ("1/250", "4_000_000", "4_000_000L"),
            "F3": ("1/12", "58_823_529", "58_823_529L")}[family]


def check_rate(task, family, rql, py, java):
    expected = expected_rate(task, family)
    if expected is None:
        return "NA"
    for label, text, token in (("rql", rql, expected[0]), ("python", py, expected[1]), ("flink", java, expected[2])):
        if token not in text:
            raise CampaignError(f"{task}/{family}: {label} nie deklaruje {token}")
    return "PASS"


def run_cell(task, family, evidence_group="raw"):
    label = f"{task}_{family}"
    evidence = EVIDENCE / evidence_group / label
    if evidence.exists():
        raise CampaignError(f"katalog dowodowy już istnieje: {evidence}")
    evidence.mkdir(parents=True)
    work = Path(tempfile.mkdtemp(prefix=f"r593k22v5_{label}_"))
    (work / "temp").mkdir()
    (work / "classes").mkdir()
    (work / "python").mkdir()
    prepare_data(work, task, family)
    root = source_root(task, family)
    rql_source = CORES / f"{label}.rql"
    py_source = root / "python/core.py"
    java_source = root / "flink" / JAVA_FILE[family]
    rql_text = rql_source.read_text(encoding="utf-8")
    py_text = py_source.read_text(encoding="utf-8")
    java_text = java_source.read_text(encoding="utf-8")
    rate = check_rate(task, family, rql_text, py_text, java_text)
    label0 = K22V5_FIRST[(task, family)]

    shutil.copy2(rql_source, work / "q.rql")
    # Nazwa, nie pełna ścieżka, jest zamierzona: RetractorDB używa argv[0] do
    # nazwy blokady. PATH jest przypięty wyżej do katalogu zahashowanej binarki.
    plan = run([XRETRACTOR.name, "q.rql", "-c"], work, evidence / "rql_compile.log", timeout=30)
    (evidence / "rql_plan.txt").write_text(plan, encoding="utf-8")
    target = task_target(task, family)
    tail, origin = parse_tail_origin(plan, target)
    cycles = (4200 if task == "M3" else 2850) if family == "F3" else SPAN + origin + tail + 20
    row = {"task": task, "family": family, "first_index": label0, "engine_tail": tail,
           "engine_origin": origin, "cycles": cycles, "span": SPAN}
    run([XRETRACTOR.name, "q.rql", "-m", str(cycles), "-k", "-r"], work,
        evidence / "rql_run.log", timeout=200 if family == "F3" else 90)
    rql_csv = evidence / "rql.csv"
    run([sys.executable, PILOT / "corpus/emit_rql.py", "--stream", f"temp/{target}",
         "--family", family, "--variant", task, "--tail", str(label0),
         "--limit", str(SPAN), "--out", rql_csv], work, evidence / "rql_emit.log", timeout=60)

    (work / "python/core.py").write_text(elide_pacing(py_source, "python", evidence / "python_pacing.diff"), encoding="utf-8")
    shutil.copy2(root / "python/run.py", work / "python/run.py")
    (work / "oracle").mkdir()
    shutil.copy2(PILOT / "oracle/refsem.py", work / "oracle/refsem.py")
    slots = SPAN + label0 + 30
    py_csv = evidence / "python.csv"
    run([sys.executable, work / "python/run.py", *model_args(family, task, slots, py_csv)],
        work, evidence / "python_run.log", timeout=60)

    exec_java = work / JAVA_FILE[family]
    exec_java.write_text(elide_pacing(java_source, "java", evidence / "flink_pacing.diff"), encoding="utf-8")
    run([JAVAC, "-nowarn", "-cp", FLINK_JAR, "-d", work / "classes", exec_java],
        work, evidence / "flink_compile.log", timeout=60)
    flink_csv = evidence / "flink.csv"
    run([JAVA, "-cp", f"{work / 'classes'}:{FLINK_JAR.parent}/*", JAVA_CLASS[family],
         *model_args(family, task, slots, flink_csv)], work, evidence / "flink_run.log", timeout=90)

    streams = {"rql": rql_csv, "python": py_csv, "flink": flink_csv}
    verdict, _ = compare(streams, label0, work, evidence / "oracle.log")
    for a, b in (("rql", "python"), ("rql", "flink"), ("python", "flink")):
        row[f"{a}_vs_{b}"], _ = compare({a: streams[a], b: streams[b]}, label0, work,
                                        evidence / f"oracle_{a}_{b}.log")
    row["verdict"] = verdict
    row["class"] = ""
    if verdict == "FAIL":
        shift = constant_shift(rql_csv, py_csv, label0) if row["python_vs_flink"] == "PASS" else None
        row["class"] = "W" if shift is None else f"P(k={shift})"
    row["rate"] = rate
    for name, path in streams.items():
        row[f"{name}_eq_k22v5"] = "YES" if filecmp.cmp(path, FROZEN / "evidence/raw" / label / path.name,
                                                      shallow=False) else "NO"
    with (evidence / "source_sha256.tsv").open("w", encoding="utf-8") as handle:
        for path in (rql_source, py_source, java_source):
            handle.write(f"{sha256(path)}\t{path.relative_to(HERE.parent)}\n")
    row["evidence"] = str(evidence.relative_to(HERE))
    return row


def failed_cell_row(task, family, evidence_group, exc):
    # Klasa T: emiter odrzuca typ albo deskryptor; klasa A: każdy inny błąd aparatury.
    evidence = EVIDENCE / evidence_group / f"{task}_{family}"
    emit_log = evidence / "rql_emit.log"
    emit_text = emit_log.read_text(encoding="utf-8") if emit_log.exists() else ""
    is_type = "nieobslugiwany typ" in emit_text or "nierozpoznany wiersz deskryptora" in emit_text
    (evidence / "apparatus_error.txt").write_text(f"{exc}\n", encoding="utf-8")
    return {"task": task, "family": family, "first_index": K22V5_FIRST[(task, family)],
            "engine_tail": "", "engine_origin": "", "cycles": "", "span": SPAN,
            "rql_vs_python": "", "rql_vs_flink": "", "python_vs_flink": "", "verdict": "FAIL",
            "class": "T" if is_type else "A", "rate": "", "rql_eq_k22v5": "", "python_eq_k22v5": "",
            "flink_eq_k22v5": "", "evidence": str(evidence.relative_to(HERE))}


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def evidence_index():
    rows = []
    for path in sorted((EVIDENCE / "raw").rglob("*")):
        if path.is_file():
            rows.append({"sha256": sha256(path), "bytes": path.stat().st_size,
                         "path": str(path.relative_to(HERE))})
    write_csv(EVIDENCE / "sha256.csv", rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="pojedyncza komórka, np. M2_F1 albo base_F1")
    parser.add_argument("--smoke", action="store_true",
                        help="zapisz przedkampanijną kontrolę jednej lub wszystkich komórek w evidence/smoke")
    args = parser.parse_args()
    subprocess.run([str(HERE / "freeze_check.sh")], check=True)
    if not TASKS.is_dir():
        raise CampaignError("brak tasks/: najpierw generate_variants.py")
    cells = [("base", family) for family in FAMILY_DIR]
    cells += [(task, family) for task in ("M1", "M2", "M3", "M4") for family in FAMILY_DIR]
    if args.only:
        cells = [tuple(args.only.split("_", 1))]
    rows = []
    group = "smoke" if args.smoke else "raw"
    for task, family in cells:
        print(f"== {task}/{family}", flush=True)
        # FAIL ani błąd aparatury jednej komórki nie zatrzymują pozostałych: wynik inny niż 15/15
        # idzie do człowieka z surowymi danymi wszystkich komórek (README, kryteria).
        try:
            row = run_cell(task, family, group)
        except CampaignError as exc:
            print(f"BLAD APARATURY {task}/{family}: {exc}", file=sys.stderr, flush=True)
            row = failed_cell_row(task, family, group, exc)
        print(f"   verdict={row['verdict']} class={row['class'] or '-'}", flush=True)
        rows.append(row)
    if not args.only and not args.smoke:
        write_csv(RESULTS / "semantic.csv", rows)
        evidence_index()
    passed = sum(row["verdict"] == "PASS" for row in rows)
    print(f"{'OK' if passed == len(rows) else 'NIEPOTWIERDZONE'}: {passed}/{len(rows)} komórek semantycznych PASS")
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (CampaignError, OSError, subprocess.CalledProcessError) as exc:
        print(f"BLAD APARATURY: {exc}", file=sys.stderr)
        sys.exit(2)
