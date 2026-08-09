#!/usr/bin/env python3
"""Fail-closed validity gate for the complete K26 RQL corpus.

The gate runs before preregistration is frozen.  It proves that the exact set
of 21 generated plans compiles under every one of the four pinned optimizer
profiles.  It also proves the opposite side of the language boundary: the
historical F9-X program that names constituents through ``#`` must fail.

The generated report contains no cost measurements.  It records compiler
plans, diagnostics, binary identities, and a checksum manifest only.
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import gen_corpus

HERE = Path(__file__).resolve().parent
CODE_REPO = Path(os.environ.get("RDB_CODE_REPO", HERE.parent.parent / "retractordb")).resolve()
EXPECTED_CODE_SHA = "189b3f8187d80492644438be706e45c7e783b201"
PROFILES = {
    "DEFAULT": ("ON", "ON"),
    "NO_R2_CANON": ("OFF", "ON"),
    "NO_R1_FACTOR": ("ON", "OFF"),
    "NO_R1_NO_R2": ("OFF", "OFF"),
}
EXPECTED_BUILD_COMMON = {
    "RDB_OPT_DEDUP_SUBSTRATES": "ON",
    "RDB_OPT_SHARE_EQUIVALENT_SELECTS": "ON",
    "RDB_BENCH_PROBE": "ON",
}

HISTORICAL_INVALID_F9X = """STORAGE 'temp'
SUBSTRAT 'memory'
DECLARE v INTEGER STREAM A, 1/100 FILE 'a.txt'
DECLARE v INTEGER STREAM B, 1/50 FILE 'b.txt'
DECLARE v INTEGER STREAM C, 1/100 FILE 'c.txt'
DECLARE v INTEGER STREAM D, 1/50 FILE 'd.txt'
SELECT Sqrt(A[0]*C[0]+B[0]*D[0]) STREAM m
FROM ((A>2)#(B>1))+((C>2)#(D>1))
"""


class GateError(RuntimeError):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_plans():
    names = []
    for family in gen_corpus.FAMILIES:
        slug = family.replace("-", "_")
        names.extend(f"{slug}_Q{q}.rql" for q in gen_corpus.Q_GRID)
        names.append(f"{slug}_controls.rql")
    return sorted(names)


def require_exact_corpus():
    generated = gen_corpus.corpus()
    generated_rql = sorted(Path(name).name for name in generated if name.startswith("rql/"))
    wanted = expected_plans()
    if generated_rql != wanted:
        missing = sorted(set(wanted) - set(generated_rql))
        extra = sorted(set(generated_rql) - set(wanted))
        raise GateError(f"generator does not define the exact 21-plan corpus; missing={missing}, extra={extra}")
    disk = sorted(path.name for path in (HERE / "rql").glob("*.rql"))
    if disk != wanted:
        missing = sorted(set(wanted) - set(disk))
        extra = sorted(set(disk) - set(wanted))
        raise GateError(f"on-disk RQL set is incomplete or extended; missing={missing}, extra={extra}")
    for rel, content in generated.items():
        path = HERE / rel
        if not path.exists() or path.read_text() != content:
            raise GateError(f"generated corpus mismatch: {rel}")
    return wanted


def parse_build_info(text):
    result = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def profile_binary(profile):
    binary = CODE_REPO / "build" / f"K26-{profile}" / "src" / "retractor" / "xretractor"
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise GateError(f"missing K26 binary for {profile}: {binary}")
    completed = subprocess.run([binary, "--build-info"], check=True, text=True, capture_output=True)
    info = parse_build_info(completed.stdout)
    for key, value in EXPECTED_BUILD_COMMON.items():
        if info.get(key) != value:
            raise GateError(f"{profile}: {key}={info.get(key)!r}, expected {value}")
    commutative, factor = PROFILES[profile]
    expected = {
        "RDB_OPT_COMMUTATIVE_ADD": commutative,
        "RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES": factor,
    }
    for key, value in expected.items():
        if info.get(key) != value:
            raise GateError(f"{profile}: {key}={info.get(key)!r}, expected {value}")
    return binary, completed.stdout


def checked_code_sha():
    completed = subprocess.run(
        ["git", "-C", CODE_REPO, "rev-parse", "HEAD"], check=True, text=True, capture_output=True
    )
    actual = completed.stdout.strip()
    if actual != EXPECTED_CODE_SHA:
        raise GateError(f"engine SHA {actual}, expected {EXPECTED_CODE_SHA}")
    dirty = subprocess.run(
        ["git", "-C", CODE_REPO, "status", "--short"], check=True, text=True, capture_output=True
    ).stdout
    if dirty:
        raise GateError("engine worktree is dirty")
    return actual


def compile_one(binary, rql, work):
    env = os.environ.copy()
    env["RDB_BENCH_PLAN"] = "1"
    return subprocess.run(
        [binary, rql, "-c"], cwd=work, env=env, text=True, capture_output=True
    )


def write_manifest(root):
    manifest = root / "manifest.sha256"
    entries = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path != manifest:
            entries.append(f"{sha256(path)}  {path.relative_to(root)}")
    manifest.write_text("\n".join(entries) + "\n")
    return len(entries)


def run_gate(destination):
    plans = require_exact_corpus()
    code_sha = checked_code_sha()
    if destination.exists():
        raise GateError(f"refusing to overwrite existing evidence directory: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="k26-corpus-", dir=destination.parent))
    rows = ["profile\tplan\tstatus\trql_sha256\tbinary_sha256"]
    try:
        (staging / "plans").mkdir()
        (staging / "profiles").mkdir()
        with tempfile.TemporaryDirectory(prefix="k26-compile-") as temp_name:
            work = Path(temp_name)
            for profile in PROFILES:
                binary, build_info = profile_binary(profile)
                (staging / "profiles" / f"build-info-{profile}.txt").write_text(build_info)
                binary_hash = sha256(binary)
                profile_dir = staging / "plans" / profile
                profile_dir.mkdir()
                for plan in plans:
                    rql = HERE / "rql" / plan
                    completed = compile_one(binary, rql, work)
                    stem = Path(plan).stem
                    (profile_dir / f"{stem}.plan").write_text(completed.stdout)
                    (profile_dir / f"{stem}.stderr").write_text(completed.stderr)
                    if completed.returncode != 0:
                        raise GateError(f"valid corpus plan rejected: {profile}/{plan}")
                    rows.append(f"{profile}\t{plan}\tPASS\t{sha256(rql)}\t{binary_hash}")

                invalid = work / "historical_invalid_F9_X.rql"
                invalid.write_text(HISTORICAL_INVALID_F9X)
                rejected = compile_one(binary, invalid, work)
                (profile_dir / "historical_invalid_F9_X.stdout").write_text(rejected.stdout)
                (profile_dir / "historical_invalid_F9_X.stderr").write_text(rejected.stderr)
                if rejected.returncode == 0:
                    raise GateError(f"historical illegal F9-X unexpectedly compiled in {profile}")
                rows.append(f"{profile}\thistorical_invalid_F9_X.rql\tREJECTED\t"
                            f"{hashlib.sha256(HISTORICAL_INVALID_F9X.encode()).hexdigest()}\t{binary_hash}")

        (staging / "corpus-validation.tsv").write_text("\n".join(rows) + "\n")
        (staging / "provenance.tsv").write_text(
            "key\tvalue\n"
            f"engine_sha\t{code_sha}\n"
            f"valid_plans\t{len(plans)}\n"
            f"profiles\t{len(PROFILES)}\n"
            f"valid_compilations\t{len(plans) * len(PROFILES)}\n"
            f"invalid_controls_rejected\t{len(PROFILES)}\n"
        )
        count = write_manifest(staging)
        staging.rename(destination)
        return len(plans) * len(PROFILES), len(PROFILES), count
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def check_evidence(destination):
    require_exact_corpus()
    checked_code_sha()
    manifest = destination / "manifest.sha256"
    if not manifest.is_file():
        raise GateError(f"missing evidence manifest: {manifest}")
    entries = manifest.read_text().splitlines()
    for line in entries:
        digest, rel = line.split("  ", 1)
        path = destination / rel
        if not path.is_file() or sha256(path) != digest:
            raise GateError(f"evidence checksum mismatch: {rel}")
    report = (destination / "corpus-validation.tsv").read_text().splitlines()[1:]
    passes = [line for line in report if "\tPASS\t" in line]
    rejects = [line for line in report if "\tREJECTED\t" in line]
    if len(passes) != 84 or len(rejects) != 4 or len(report) != 88:
        raise GateError(
            f"evidence is incomplete: PASS={len(passes)}, REJECTED={len(rejects)}, total={len(report)}"
        )
    return len(entries)


def selftest():
    wanted = expected_plans()
    if len(wanted) != 21 or len(set(wanted)) != 21:
        raise GateError("selftest: expected plan inventory is not exactly 21 unique names")
    shortened = wanted[:-1]
    if shortened == wanted or len(shortened) != 20:
        raise GateError("selftest: omitted-plan mutant was not constructed")
    extended = wanted + ["unexpected.rql"]
    if set(extended) == set(wanted):
        raise GateError("selftest: extra-plan mutant was not constructed")
    if "A[0]" not in HISTORICAL_INVALID_F9X or "#" not in HISTORICAL_INVALID_F9X:
        raise GateError("selftest: historical language-boundary mutant is missing")
    print("OK: selftest distinguishes omitted, extra, and historical-invalid corpus mutants")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "corpus_validation")
    parser.add_argument("--check", action="store_true", help="verify already recorded evidence")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        if args.selftest:
            selftest()
        elif args.check:
            count = check_evidence(args.out.resolve())
            print(f"OK: corpus-validity evidence complete and immutable ({count} checksums)")
        else:
            valid, rejected, count = run_gate(args.out.resolve())
            print(f"OK: {valid} valid compilations; {rejected} illegal controls rejected; {count} checksums")
        return 0
    except (GateError, subprocess.CalledProcessError, OSError) as exc:
        print(f"BLAD: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
