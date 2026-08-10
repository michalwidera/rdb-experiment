#!/usr/bin/env python3
"""Compile and execute the six representative K26 plans in all profiles.

This is a premeasurement executability gate.  It records plans and probe
counters, but it does not interpret or compare costs.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CODE_REPO = Path(os.environ.get("RDB_CODE_REPO", ROOT.parent.parent / "retractordb")).resolve()
PROFILES = ["DEFAULT", "NO_R2_CANON", "NO_R1_FACTOR", "NO_R1_NO_R2"]
PLANS = [
    "F9_R2_Q8",
    "F9_R1_Q8",
    "F9_X_Q8",
    "F9_R2_controls",
    "F9_R1_controls",
    "F9_X_controls",
]
MAIN_PLANS = {"F9_R2_Q8", "F9_R1_Q8", "F9_X_Q8"}
SLOTS = int(os.environ.get("SLOTS", "100"))


class PilotError(RuntimeError):
    pass


def binary(profile):
    path = CODE_REPO / "build" / f"K26v2-{profile}" / "src" / "retractor" / "xretractor"
    if not path.is_file() or not os.access(path, os.X_OK):
        raise PilotError(f"missing profile binary: {path}")
    return path


def fresh_dir(path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def assert_runtime(label, completed, want_substrate):
    if completed.returncode != 0:
        raise PilotError(f"{label}: runtime exit code {completed.returncode}")
    logical = re.search(
        r"^LOGICAL substrat: dopisania=(\d+).*?publiczne: dopisania=(\d+)",
        completed.stderr,
        re.MULTILINE,
    )
    if logical is None:
        raise PilotError(f"{label}: missing LOGICAL probe row")
    if int(logical.group(2)) <= 0:
        raise PilotError(f"{label}: zero public records")
    if want_substrate and int(logical.group(1)) <= 0:
        raise PilotError(f"{label}: main family did not materialize a substrate")
    if re.search(r"^WORK ", completed.stderr, re.MULTILINE) is None:
        raise PilotError(f"{label}: missing WORK probe row")
    return int(logical.group(1)), int(logical.group(2))


def compile_plan(executable, rql, work):
    prepare_work(work)
    env = os.environ.copy()
    env["RDB_BENCH_PLAN"] = "1"
    return subprocess.run([executable, rql, "-c"], cwd=work, env=env, text=True, capture_output=True)


def run_plan(executable, rql, work):
    prepare_work(work)
    env = os.environ.copy()
    env["RDB_BENCH_LOGICAL"] = "1"
    env["RDB_BENCH_WORK"] = "1"
    return subprocess.run(
        [executable, rql, "-m", str(SLOTS), "-r", "-k"],
        cwd=work,
        env=env,
        text=True,
        capture_output=True,
        timeout=300,
    )


def copy_data(work):
    for source in (ROOT / "data" / "main").glob("*.txt"):
        shutil.copy2(source, work / source.name)


def prepare_work(work):
    storage = work / "temp"
    if storage.exists():
        shutil.rmtree(storage)
    storage.mkdir()
    for descriptor in work.glob("*.desc"):
        descriptor.unlink()


def negative_runtime_gate(work, out):
    source = (ROOT / "rql" / "F9_R2_Q8.rql").read_text()
    invalid = work / "F9_R2_Q8_abs.rql"
    invalid.write_text(source.replace("Sqrt(", "Abs("))
    compiled = compile_plan(binary("DEFAULT"), invalid, work)
    (out / "compile.out").write_text(compiled.stdout)
    (out / "compile.err").write_text(compiled.stderr)
    if compiled.returncode != 0:
        raise PilotError("runtime mutant no longer compiles; it does not test the runtime boundary")
    executed = run_plan(binary("DEFAULT"), invalid, work)
    (out / "runtime.out").write_text(executed.stdout)
    (out / "runtime.counters").write_text(executed.stderr)
    (out / "runtime.rc").write_text(f"{executed.returncode}\n")
    try:
        assert_runtime("runtime mutant", executed, True)
    except PilotError as exc:
        (out / "rejection.txt").write_text(f"{exc}\n")
        return
    raise PilotError("compile-valid runtime mutant passed the executability gate")


def main():
    out = HERE / "out"
    out_rt = HERE / "out_rt"
    neg = HERE / "neg"
    fresh_dir(out)
    fresh_dir(out_rt)
    fresh_dir(neg)
    with tempfile.TemporaryDirectory(prefix="k26-pilot-") as temp_name:
        work = Path(temp_name)
        copy_data(work)
        negative_runtime_gate(work, neg)
        cells = 0
        for profile in PROFILES:
            executable = binary(profile)
            for plan in PLANS:
                rql = ROOT / "rql" / f"{plan}.rql"
                compiled = compile_plan(executable, rql, work)
                tag = f"{profile}_{plan}"
                (out / f"{tag}.plan").write_text(compiled.stdout)
                (out / f"{tag}.probe").write_text(compiled.stderr)
                if compiled.returncode != 0:
                    raise PilotError(f"{tag}: compile exit code {compiled.returncode}")

                executed = run_plan(executable, rql, work)
                (out_rt / f"{tag}.out").write_text(executed.stdout)
                (out_rt / f"{tag}.counters").write_text(executed.stderr)
                substrate, public = assert_runtime(tag, executed, plan in MAIN_PLANS)
                print(f"ok {tag:<38} substrate={substrate:<6} public={public:<6}")
                cells += 1
        print(f"OK: {cells} compile-only and runtime cells; runtime mutant rejected first")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (PilotError, OSError, subprocess.SubprocessError) as exc:
        print(f"BLAD: {exc}", file=sys.stderr)
        sys.exit(1)
