#!/usr/bin/env python3
"""Runtime preflight and independent value oracle for the legal Flink F9-X port."""

import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FLINK_HOME = Path(os.environ.get("FLINK_HOME", "/home/michal/opt/flink-2.3.0"))
JAVA = Path(os.environ.get("JAVA17", "/usr/lib/jvm/java-17-openjdk-amd64/bin/java"))
SLOTS = 100


class VerificationError(RuntimeError):
    pass


def read_ints(path, count):
    return [int(line) for line in path.read_text().splitlines()[:count]]


def interleave(fast, slow):
    """Definition-level merge on a 1/100 time grid; slow wins equal-time ties."""
    events = [(2 * index, 0, value) for index, value in enumerate(slow)]
    events += [(index, 1, value) for index, value in enumerate(fast)]
    events.sort(key=lambda item: (item[0], item[1]))
    return [value for _, _, value in events]


def expected_values():
    data = ROOT / "data" / "main"
    front = interleave(
        read_ints(data / "front_vib.txt", SLOTS),
        read_ints(data / "front_cur.txt", SLOTS // 2),
    )
    rear = interleave(
        read_ints(data / "rear_vib.txt", SLOTS),
        read_ints(data / "rear_cur.txt", SLOTS // 2),
    )
    return [math.isqrt(left * left + right * right) for left, right in zip(front, rear)]


def classpath():
    jars = sorted((FLINK_HOME / "lib").glob("*.jar"))
    return os.pathsep.join([str(ROOT / "flink" / "build"), *(str(path) for path in jars)])


def run_variant(variant, out):
    data = ROOT / "data" / "main"
    completed = subprocess.run(
        [
            JAVA,
            "-cp",
            classpath(),
            "F9XJob",
            "--variant",
            variant,
            "--q",
            "8",
            "--slots",
            str(SLOTS),
            "--a",
            data / "front_vib.txt",
            "--b",
            data / "front_cur.txt",
            "--c",
            data / "rear_vib.txt",
            "--d",
            data / "rear_cur.txt",
            "--out-dir",
            out,
            "--sink-dir",
            out,
        ],
        text=True,
        capture_output=True,
        timeout=120,
    )
    (out / "job.out").write_text(completed.stdout)
    (out / "job.err").write_text(completed.stderr)
    if completed.returncode != 0 or "LOGICAL " not in completed.stdout:
        raise VerificationError(f"Flink {variant} did not execute: rc={completed.returncode}")


def read_csv(path):
    rows = []
    for line in path.read_text().splitlines():
        monitor, slot, value = line.split(",")
        rows.append((monitor, int(slot), int(value)))
    return rows


def main():
    output = HERE / "flink_runtime"
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()
    expected = expected_values()
    report = ["variant\tmonitor\trecords\toracle_match\tcontinuous_slots"]
    for variant in ("natural", "manual"):
        out = output / variant
        out.mkdir()
        run_variant(variant, out)
        for index in range(1, 9):
            monitor = f"m{index}"
            rows = read_csv(out / f"f9x_{monitor}.csv")
            values = [value for _, _, value in rows]
            slots = [slot for _, slot, _ in rows]
            continuous = slots == list(range(slots[0], slots[0] + len(slots)))
            match = values == expected
            report.append(f"{variant}\t{monitor}\t{len(rows)}\t{str(match).lower()}\t{str(continuous).lower()}")
            if not match or not continuous:
                raise VerificationError(
                    f"{variant}/{monitor}: records={len(rows)}, oracle={match}, continuous={continuous}"
                )
    (output / "verification.tsv").write_text("\n".join(report) + "\n")
    print(f"OK: 16/16 F9-X streams, {len(expected)} values each, independent oracle 100%")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (VerificationError, OSError, subprocess.SubprocessError) as exc:
        print(f"BLAD: {exc}", file=sys.stderr)
        sys.exit(1)
