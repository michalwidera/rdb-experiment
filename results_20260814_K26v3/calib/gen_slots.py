#!/usr/bin/env python3
"""Generuje ``slots.tsv`` z planow kompilatora i ``TimeLine`` silnika."""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

try:
    from .gen_calib import FAMILIES, scale_plan, source_paths
except ImportError:  # bezposrednie uruchomienie ./calib/gen_slots.py
    from gen_calib import FAMILIES, scale_plan, source_paths

HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE.parent
SCALES = [Fraction(1, 4), Fraction(1, 2), Fraction(1), Fraction(2), Fraction(4)]
PLAN_INTERVAL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\((\d+/\d+)\)", re.M)


def scale_tag(scale):
    return f"{scale.numerator}_{scale.denominator}"


def extract_intervals(plan_dump):
    intervals = sorted(set(PLAN_INTERVAL.findall(plan_dump)))
    if not intervals:
        raise RuntimeError("zrzut planu nie zawiera interwalow")
    return intervals


def engine_compile_flags(code_repo):
    commands = code_repo / "build" / "K26v3-DEFAULT" / "compile_commands.json"
    if not commands.is_file():
        raise RuntimeError(f"brak wygenerowanego {commands}")
    entries = json.loads(commands.read_text())
    for entry in entries:
        if entry.get("file", "").endswith("/CRSMath.cpp"):
            tokens = shlex.split(entry.get("command", ""))
            flags, index = [], 0
            while index < len(tokens):
                token = tokens[index]
                if token.startswith("-D") or token.startswith("-I"):
                    flags.append(token)
                elif token == "-isystem" and index + 1 < len(tokens):
                    flags.extend([token, tokens[index + 1]])
                    index += 1
                index += 1
            if flags:
                return flags
    raise RuntimeError("compile_commands.json nie zawiera flag CRSMath.cpp")


def compile_slot_grid(code_repo, target):
    command = [
        os.environ.get("CXX", "g++"), "-std=c++23", "-O2",
        *engine_compile_flags(code_repo),
        "-I", str(code_repo / "src" / "retractor" / "lib"),
        "-I", str(code_repo / "src" / "include"),
        str(HERE / "slot_grid.cpp"),
        str(code_repo / "src" / "retractor" / "lib" / "CRSMath.cpp"),
        "-o", str(target),
    ]
    subprocess.run(command, check=True)


def produce(code_repo):
    binary = code_repo / "build" / "K26v3-DEFAULT" / "src" / "retractor" / "xretractor"
    if not os.access(binary, os.X_OK):
        raise RuntimeError(f"brak binarium DEFAULT: {binary}")
    lines = ["family\tscale\tmin_slot_ms\tmax_slot_ms"]
    with tempfile.TemporaryDirectory(prefix="k26-slots-") as name:
        work = Path(name)
        grid = work / "slot_grid"
        compile_slot_grid(code_repo, grid)
        for scale in SCALES:
            for family in FAMILIES:
                source = (CAMPAIGN / "rql" / f"{family}_Q32.rql").read_text()
                scaled, _ = scale_plan(source, scale)
                query = work / "query.rql"
                query.write_text(scaled)
                for source_name in source_paths(scaled):
                    shutil.copy2(CAMPAIGN / "data" / "calib" / source_name, work / source_name)
                env = os.environ.copy()
                env["RDB_BENCH_PLAN"] = "1"
                completed = subprocess.run([binary, query, "-c"], cwd=work, env=env,
                                           check=True, text=True, capture_output=True)
                intervals = extract_intervals(completed.stdout)
                grid_out = subprocess.run([grid, *intervals], check=True, text=True,
                                          capture_output=True).stdout
                values = dict(line.split("\t", 1) for line in grid_out.splitlines())
                lines.append(f"{family}\t{scale_tag(scale)}\t{values['min_slot_ms']}\t{values['max_slot_ms']}")
                for source_name in source_paths(scaled):
                    (work / source_name).unlink(missing_ok=True)
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-repo", type=Path,
                        default=Path(os.environ.get("RDB_CODE_REPO", "/home/michal/github/retractordb")))
    parser.add_argument("--out", type=Path, default=HERE / "slots.tsv")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        content = produce(args.code_repo.resolve())
        if args.check:
            if not args.out.is_file() or args.out.read_text() != content:
                raise RuntimeError(f"{args.out} nie zgadza sie z planem i TimeLine silnika")
            print(f"OK: {args.out} zgodny z planem i TimeLine silnika")
        else:
            args.out.write_text(content)
            print(f"OK: zapisano {args.out} (15 komorek)")
        return 0
    except (KeyError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"BLAD: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
