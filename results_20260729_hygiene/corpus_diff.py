#!/usr/bin/env python3
"""Badanie higieniczne: czy `Fix (#214)` zmienił jakikolwiek istniejący plan.

Każdy plik RQL korpusu jest kompilowany w trybie compile-only przez oba silniki —
sprzed i po poprawce — a zrzuty planu porównywane po normalizacji.

Normalizacja zamyka dług odnotowany w JOURNAL.md przy K4: `collect.py` hashował
surowe wyjście, które zawiera bezwzględną ścieżkę katalogu tymczasowego, przez co
hash był nieodtwarzalny między przebiegami. Tutaj ścieżka katalogu roboczego jest
zastępowana stałym znacznikiem PRZED policzeniem hasha.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

COUNTER_RE = re.compile(r"^REWRITE_APPLIED r1=(\d+) r2=(\d+)$", re.MULTILINE)
STAGE_ROOT = "/dev/shm"

# Pliki, które kompilator ma prawo odrzucić — lista przeniesiona z K4.
EXPECTED_FAILURES = {
    "examples/mwd/query-mwnd.rql",
    "examples/mwd/query-mwnd2.rql",
    "test/IntegrationTest_parallel/issue95_loopInCompile/brokenQuery.rql",
    "test/IntegrationTest_serial/Data/query.rql",
    "test/IntegrationTest_serial/Data/ut_example.rql",
}


def normalize(text: str, work: Path) -> str:
    """Usuwa z wyjścia fragmenty zależne od przebiegu, a nie od planu."""
    return text.replace(str(work), "<WORK>")


def discover(code_repo: Path) -> list[tuple[str, Path]]:
    roots = [
        ("integration_serial", code_repo / "test/IntegrationTest_serial"),
        ("integration_parallel", code_repo / "test/IntegrationTest_parallel"),
        ("examples", code_repo / "examples"),
    ]
    cases: list[tuple[str, Path]] = []
    for suite, root in roots:
        cases.extend((suite, path) for path in sorted(root.rglob("*.rql")))
    return cases


def compile_case(binary: Path, source: Path, raw_base: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="rdb-hyg-", dir=STAGE_ROOT) as stage:
        work = Path(stage) / "case"
        shutil.copytree(source.parent, work, ignore=shutil.ignore_patterns("__pycache__", "temp"))
        (work / "temp").mkdir(exist_ok=True)
        environment = os.environ.copy()
        environment["RDB_BENCH_PLAN"] = "1"
        try:
            done = subprocess.run(
                [str(binary), source.name, "-c"],
                cwd=work,
                env=environment,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=120,
                check=False,
            )
            returncode, stdout, stderr = done.returncode, done.stdout, done.stderr
        except subprocess.TimeoutExpired as error:
            returncode = 124
            stdout = error.stdout or ""
            stderr = (error.stderr or "") + "\nHYG_TIMEOUT\n"
        stdout = normalize(stdout, work)
        stderr = normalize(stderr, work)

    raw_base.parent.mkdir(parents=True, exist_ok=True)
    Path(f"{raw_base}.stdout").write_text(stdout, encoding="utf-8")
    Path(f"{raw_base}.stderr").write_text(stderr, encoding="utf-8")
    counters = COUNTER_RE.findall(stderr)
    return {
        "returncode": returncode,
        "plan": stdout,
        "plan_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
        "r1": int(counters[0][0]) if len(counters) == 1 else "",
        "r2": int(counters[0][1]) if len(counters) == 1 else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-repo", type=Path, required=True)
    parser.add_argument("--historical-binary", type=Path, required=True)
    parser.add_argument("--fixed-binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    code_repo = args.code_repo.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    corpus = discover(code_repo)

    rows: list[dict[str, object]] = []
    plan_differences: list[str] = []
    status_changes: list[dict[str, object]] = []
    counter_differences: list[str] = []

    for suite, source in corpus:
        relative = source.relative_to(code_repo).as_posix()
        digest = hashlib.sha256(relative.encode("utf-8")).hexdigest()[:12]
        stem = f"{source.stem}-{digest}"
        historical = compile_case(args.historical_binary, source, output / "raw/corpus/HISTORICAL" / suite / stem)
        fixed = compile_case(args.fixed_binary, source, output / "raw/corpus/FIXED" / suite / stem)

        identical_plan = historical["plan"] == fixed["plan"]
        same_status = historical["returncode"] == fixed["returncode"]
        same_counters = (historical["r1"], historical["r2"]) == (fixed["r1"], fixed["r2"])

        if not identical_plan:
            plan_differences.append(relative)
        if not same_status:
            status_changes.append(
                {"path": relative, "historical_rc": historical["returncode"], "fixed_rc": fixed["returncode"]}
            )
        if not same_counters:
            counter_differences.append(relative)

        rows.append(
            {
                "suite": suite,
                "path": relative,
                "expected_failure": relative in EXPECTED_FAILURES,
                "historical_rc": historical["returncode"],
                "fixed_rc": fixed["returncode"],
                "historical_r1": historical["r1"],
                "fixed_r1": fixed["r1"],
                "historical_r2": historical["r2"],
                "fixed_r2": fixed["r2"],
                "historical_plan_sha256": historical["plan_sha256"],
                "fixed_plan_sha256": fixed["plan_sha256"],
                "plan_identical": identical_plan,
            }
        )

    with (output / "corpus.csv").open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    def totals(prefix: str) -> dict[str, int]:
        compiled = [r for r in rows if r[f"{prefix}_rc"] == 0]
        return {
            "skompilowane": len(compiled),
            "odrzucone": len(rows) - len(compiled),
            "r1": sum(int(r[f"{prefix}_r1"]) for r in compiled if r[f"{prefix}_r1"] != ""),
            "r2": sum(int(r[f"{prefix}_r2"]) for r in compiled if r[f"{prefix}_r2"] != ""),
        }

    payload = {
        "korpus": len(rows),
        "historical": totals("historical"),
        "fixed": totals("fixed"),
        "plan_differences": plan_differences,
        "status_changes": status_changes,
        "counter_differences": counter_differences,
    }
    (output / "corpus.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"korpus: {len(rows)} plików")
    print(f"różnice planu: {len(plan_differences)}")
    print(f"zmiany statusu kompilacji: {len(status_changes)}")
    print(f"różnice liczników R1/R2: {len(counter_differences)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
