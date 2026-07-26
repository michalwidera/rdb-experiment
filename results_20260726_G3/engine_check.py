#!/usr/bin/env python3
"""Most niezależnego oracle'a K2/G3 do aktualnego silnika RetractorDB."""

import argparse
import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

from cases import ENGINE_CASES
from reference import (
    SCHEMA,
    ceil_fraction,
    lhs_observation,
    matched_offsets,
    reduced_ratio,
    rhs_observation,
    trace_null_coverage,
)

OUTPUTS = ("optimized", "blocked", "explicit_rhs")

QUERY_TEMPLATE = """STORAGE '.'
SUBSTRAT 'memory'

DECLARE value INTEGER, aux INTEGER STREAM A_opt, {delta_a} FILE 'a.txt'
DECLARE value INTEGER, aux INTEGER STREAM B_opt, {delta_b} FILE 'b.txt'
DECLARE value INTEGER, aux INTEGER STREAM A_blk, {delta_a} FILE 'a.txt'
DECLARE value INTEGER, aux INTEGER STREAM B_blk, {delta_b} FILE 'b.txt'
DECLARE value INTEGER, aux INTEGER STREAM A_rhs, {delta_a} FILE 'a.txt'
DECLARE value INTEGER, aux INTEGER STREAM B_rhs, {delta_b} FILE 'b.txt'

SELECT * STREAM optimized FROM (A_opt>{shift_a})#(B_opt>{shift_b})

SELECT * STREAM shifted_a FROM A_blk>{shift_a}
SELECT * STREAM shifted_b FROM B_blk>{shift_b}
SELECT * STREAM blocked FROM shifted_a#shifted_b

SELECT * STREAM explicit_rhs FROM (A_rhs#B_rhs)>{combined}
"""


def fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def source_values(source: str, index: int):
    from reference import source_values as oracle_values

    return oracle_values(source, index)


def write_source(path: Path, source: str, records: int):
    def cell(value):
        return "NULL" if value is None else str(value)

    with path.open("w", encoding="utf-8") as handle:
        for index in range(records):
            values = source_values(source, index)
            handle.write(" ".join(cell(value) for value in values) + "\n")


def decode_payload(path: Path):
    raw = path.read_bytes()
    record_size = 2 * 4
    if len(raw) % record_size:
        raise ValueError(f"{path}: rozmiar {len(raw)} nie jest wielokrotnością {record_size}")
    values = struct.unpack(f"<{len(raw) // 4}i", raw)
    return [tuple(values[pos : pos + 2]) for pos in range(0, len(values), 2)]


def decode_meta(path: Path):
    raw = path.read_bytes()
    entries = []
    pos = 8
    while pos < len(raw):
        if pos + 17 > len(raw):
            raise ValueError(f"{path}: ucięty nagłówek wpisu meta przy {pos}")
        is_gap = bool(raw[pos])
        count, bit_count = struct.unpack_from("<QQ", raw, pos + 1)
        byte_count = (bit_count + 7) // 8
        pos += 17
        if pos + byte_count > len(raw):
            raise ValueError(f"{path}: ucięty bitset wpisu meta przy {pos}")
        packed = raw[pos : pos + byte_count]
        pos += byte_count
        bitset = tuple(bool(packed[index // 8] >> (index % 8) & 1) for index in range(bit_count))
        entries.append({"gap": is_gap, "records": count, "null": bitset})
    return entries


def expand_nulls(entries):
    result = []
    for entry in entries:
        if not entry["gap"]:
            result.extend([entry["null"]] * entry["records"])
    return result


def gap_trace(entries):
    return [entry["records"] for entry in entries if entry["gap"]]


def descriptor_schema(path: Path):
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.replace("{", "").strip().split()
        if len(parts) == 2 and parts[0].isupper():
            result.append((parts[1], parts[0]))
    return tuple(result)


def plan_tail(plan: str, stream: str):
    match = re.search(rf"^{re.escape(stream)}\([^\n]+?\)\s+tail=(\d+)", plan, re.MULTILINE)
    if not match:
        return None
    return int(match.group(1))


def plan_interval(plan: str, stream: str):
    match = re.search(rf"^{re.escape(stream)}\(([^)]+)\)", plan, re.MULTILINE)
    if not match:
        return None
    return Fraction(match.group(1))


def run_checked(command, *, cwd: Path, timeout: int):
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout,
    )


def compare_output(workdir: Path, stream: str, oracle_records):
    payload = decode_payload(workdir / stream)
    entries = decode_meta(workdir / f"{stream}.meta")
    nulls = expand_nulls(entries)
    compared = min(len(payload), len(oracle_records))
    mismatches = []
    mismatch_count = 0
    for position in range(compared):
        expected_item = oracle_records[position]
        expected_values = tuple(0 if value is None else value for value in expected_item.values)
        expected_nulls = expected_item.null_bitset
        actual = payload[position]
        actual_nulls = nulls[position] if position < len(nulls) else None
        if actual != expected_values or actual_nulls != expected_nulls:
            mismatch_count += 1
            if len(mismatches) < 8:
                mismatches.append(
                    {
                        "position": position,
                        "expected_values": expected_values,
                        "actual_values": actual,
                        "expected_nulls": expected_nulls,
                        "actual_nulls": actual_nulls,
                        "source": expected_item.source,
                        "source_index": expected_item.source_index,
                    }
                )

    return {
        "records": len(payload),
        "meta_records": len(nulls),
        "compared": compared,
        "gaps": gap_trace(entries),
        "schema": descriptor_schema(workdir / f"{stream}.desc"),
        "mismatch_count": mismatch_count,
        "first_mismatches": mismatches,
    }


def run_case(binary: Path, workroot: Path, case):
    workdir = workroot / case.name
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)

    # Wspólna skala zachowuje stosunek; szybkie i wolne kontrole rozdzielają
    # błąd semantyczny od niedotrzymania bardzo krótkiego taktu.
    denominator = min(case.delta_a_num, case.delta_b_num) * 1000 // case.min_interval_ms
    delta_a = Fraction(case.delta_a_num, denominator)
    delta_b = Fraction(case.delta_b_num, denominator)
    shift_a, shift_b = matched_offsets(delta_a, delta_b, case.multiplier)
    combined = shift_a + shift_b
    records = max(2500, 3 * case.loops + combined + 100)

    write_source(workdir / "a.txt", "A", records)
    write_source(workdir / "b.txt", "B", records)
    query = QUERY_TEMPLATE.format(
        delta_a=fraction_text(delta_a),
        delta_b=fraction_text(delta_b),
        shift_a=shift_a,
        shift_b=shift_b,
        combined=combined,
    )
    (workdir / "query.rql").write_text(query, encoding="utf-8")

    compile_run = run_checked([str(binary), "query.rql", "-c"], cwd=workdir, timeout=30)
    plan = compile_run.stdout
    (workdir / "plan.txt").write_text(plan, encoding="utf-8")

    run_checked(
        [str(binary), "query.rql", "-r", "-k", "-m", str(case.loops)],
        cwd=workdir,
        timeout=120,
    )

    lengths = [len(decode_payload(workdir / stream)) for stream in OUTPUTS]
    expected_count = max(lengths)
    lhs = lhs_observation(delta_a, delta_b, shift_a, shift_b, expected_count)
    rhs = rhs_observation(delta_a, delta_b, combined, expected_count)
    oracle_equal = lhs == rhs
    output_results = {
        stream: compare_output(workdir, stream, rhs.records)
        for stream in OUTPUTS
    }

    expected_tail = rhs.tail
    expected_interval = rhs.interval
    p, q = reduced_ratio(delta_a, delta_b)
    current_hash_tail = ceil_fraction(Fraction(q, p))
    phase_safe_hash_tail = max(
        ceil_fraction(Fraction((index + 1) * q, p)) - (index * q // p)
        for index in range(p)
    )
    tails = {stream: plan_tail(plan, stream) for stream in OUTPUTS}
    intervals = {stream: plan_interval(plan, stream) for stream in OUTPUTS}
    schemas = {stream: output_results[stream]["schema"] for stream in OUTPUTS}
    coverage = trace_null_coverage(rhs.records[: min(lengths)])

    optimized_shape = (
        "STREAM_HASH_A_opt_B_opt" in plan
        and "STREAM_TIMEMOVE_A_opt" not in plan
        and "STREAM_TIMEMOVE_B_opt" not in plan
    )
    blocked_shape = "shifted_a(" in plan and "shifted_b(" in plan
    output_ok = all(
        result["mismatch_count"] == 0
        and result["records"] == result["meta_records"]
        and result["gaps"] == []
        and result["schema"] == SCHEMA
        for result in output_results.values()
    )
    plan_ok = (
        all(tail == expected_tail for tail in tails.values())
        and all(interval == expected_interval for interval in intervals.values())
        and optimized_shape
        and blocked_shape
    )
    nonempty_domain = all(coverage.values()) and min(lengths) > 0
    status = "OK" if oracle_equal and output_ok and plan_ok and nonempty_domain else "MISMATCH"

    return {
        "case": case.name,
        "delta_a": str(delta_a),
        "delta_b": str(delta_b),
        "ratio": str(delta_a / delta_b),
        "shift_a": shift_a,
        "shift_b": shift_b,
        "combined": combined,
        "loops": case.loops,
        "min_interval_ms": case.min_interval_ms,
        "source_records": records,
        "expected_interval": str(expected_interval),
        "expected_tail": expected_tail,
        "current_hash_tail": current_hash_tail,
        "phase_safe_hash_tail": phase_safe_hash_tail,
        "tail_deficit": phase_safe_hash_tail - current_hash_tail,
        "tails": tails,
        "intervals": {name: str(value) if value is not None else None for name, value in intervals.items()},
        "optimized_shape": optimized_shape,
        "blocked_shape": blocked_shape,
        "oracle_lhs_equals_rhs": oracle_equal,
        "null_coverage": coverage,
        "outputs": output_results,
        "optimized_equals_rhs": (
            decode_payload(workdir / "optimized") == decode_payload(workdir / "explicit_rhs")
            and expand_nulls(decode_meta(workdir / "optimized.meta"))
            == expand_nulls(decode_meta(workdir / "explicit_rhs.meta"))
        ),
        "blocked_equals_rhs": (
            decode_payload(workdir / "blocked") == decode_payload(workdir / "explicit_rhs")
            and expand_nulls(decode_meta(workdir / "blocked.meta"))
            == expand_nulls(decode_meta(workdir / "explicit_rhs.meta"))
        ),
        "schemas_equal": len(set(schemas.values())) == 1,
        "status": status,
    }


def git_revision(path: Path):
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    default_binary = Path(__file__).resolve().parents[3] / "build/Debug/src/retractor/xretractor"
    parser.add_argument("--xretractor", default=str(default_binary))
    parser.add_argument("--workdir", default="work")
    parser.add_argument("--json")
    args = parser.parse_args()

    binary = Path(args.xretractor).resolve()
    if not binary.exists():
        found = shutil.which("xretractor")
        if not found:
            print("nie znaleziono xretractor — podaj --xretractor", file=sys.stderr)
            return 2
        binary = Path(found).resolve()

    experiment_repo = Path(__file__).resolve().parents[1]
    code_repo = experiment_repo.parents[1]
    build_info = run_checked([str(binary), "--build-info"], cwd=Path.cwd(), timeout=10).stdout.strip()

    workroot = Path(args.workdir).resolve()
    workroot.mkdir(parents=True, exist_ok=True)
    results = []
    for case in ENGINE_CASES:
        print(f"-- {case.name}")
        result = run_case(binary, workroot, case)
        results.append(result)
        counts = "/".join(str(result["outputs"][name]["records"]) for name in OUTPUTS)
        print(
            f"   ratio={result['ratio']:>8s} shift={result['shift_a']}+{result['shift_b']} "
            f"tail={result['expected_tail']} records={counts} "
            f"blocked_mismatch={result['outputs']['blocked']['mismatch_count']} {result['status']}"
        )

    failed = [result for result in results if result["status"] != "OK"]
    report = {
        "binary": str(binary),
        "build_info": build_info,
        "code_commit": git_revision(code_repo),
        "experiment_commit": git_revision(experiment_repo),
        "python": sys.version,
        "platform": platform.platform(),
        "gap_policy": "computed R1 outputs must have an empty gap trace",
        "cases": results,
        "verdict": "OK" if not failed else "MISMATCH",
    }
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nWYNIK: {len(results) - len(failed)}/{len(results)} przypadków zgodnych z oracle'em")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
