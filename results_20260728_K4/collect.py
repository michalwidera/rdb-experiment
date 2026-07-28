#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path


COUNTER_RE = re.compile(r"^REWRITE_APPLIED r1=(\d+) r2=(\d+)$", re.MULTILINE)


def parse_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source, delimiter="\t"))


def sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8", errors="replace")).hexdigest()


def discover_corpus(code_repo: Path) -> list[tuple[str, Path]]:
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
    with tempfile.TemporaryDirectory(prefix="rdb-k4-") as temp_name:
        work = Path(temp_name) / "case"
        shutil.copytree(source.parent, work, ignore=shutil.ignore_patterns("__pycache__"))
        query = work / source.name
        environment = os.environ.copy()
        environment["RDB_BENCH_PLAN"] = "1"
        try:
            completed = subprocess.run(
                [str(binary), str(query), "-c"],
                cwd=work,
                env=environment,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=30,
                check=False,
            )
            returncode = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as error:
            returncode = 124
            stdout = error.stdout or ""
            stderr = (error.stderr or "") + "\nK4_TIMEOUT\n"

    raw_base.parent.mkdir(parents=True, exist_ok=True)
    Path(f"{raw_base}.stdout").write_text(stdout, encoding="utf-8")
    Path(f"{raw_base}.stderr").write_text(stderr, encoding="utf-8")
    counters = COUNTER_RE.findall(stderr)
    return {
        "returncode": returncode,
        "stdout_sha256": sha256(stdout),
        "stderr_sha256": sha256(stderr),
        "counters": counters,
    }


def write_summary(
    target: Path,
    rows: list[dict[str, object]],
    profiles: list[dict[str, str]],
    expected_failures: dict[str, str],
) -> None:
    lines = [
        "# Wynik K4",
        "",
        "Jednostką zliczania jest pojedyncza kompilacja istniejącego pliku RQL.",
        "Wyniki zerowe są zachowane jawnie.",
        "",
        "## Agregaty profili",
        "",
        "| Profil | Skompilowane | Oczekiwane odrzucenia | R1 | R2 | Pliki z R1 | Pliki z R2 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for profile in profiles:
        subset = [row for row in rows if row["profile"] == profile["profile"]]
        compiled = [row for row in subset if row["status"] == "compiled"]
        expected = [row for row in subset if row["status"] == "expected_failure"]
        r1_total = sum(int(row["r1"]) for row in compiled)
        r2_total = sum(int(row["r2"]) for row in compiled)
        r1_files = sum(int(row["r1"]) > 0 for row in compiled)
        r2_files = sum(int(row["r2"]) > 0 for row in compiled)
        lines.append(
            f"| `{profile['profile']}` | {len(compiled)} | {len(expected)} | "
            f"{r1_total} | {r2_total} | {r1_files} | {r2_files} |"
        )

    lines.extend(
        [
            "",
            "## Trafienia reguł w profilu ALGSTRUCT",
            "",
            "| Plik | R1 | R2 |",
            "|---|---:|---:|",
        ]
    )
    hits = [
        row
        for row in rows
        if row["profile"] == "ALGSTRUCT"
        and row["status"] == "compiled"
        and (int(row["r1"]) > 0 or int(row["r2"]) > 0)
    ]
    if hits:
        for row in hits:
            lines.append(f"| `{row['path']}` | {row['r1']} | {row['r2']} |")
    else:
        lines.append("| *(brak)* | 0 | 0 |")

    lines.extend(["", "## Jawne wyłączenia", ""])
    for path, reason in sorted(expected_failures.items()):
        lines.append(f"- `{path}` — {reason}")

    lines.extend(
        [
            "",
            "## Interpretacja",
            "",
            "- R1 oznacza skuteczne przepisanie planu.",
            "- R2 oznacza unikalny węzeł, którego odcisk wymagał przemiennej zamiany dzieci.",
            "- R2 nie jest liczbą usuniętych węzłów ani miarą przyspieszenia.",
            "- Korpus obejmuje istniejące testy integracyjne i przykłady, nie syntetyczny workload K5.",
        ]
    )
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    code_repo = args.code_repo.resolve()
    output = args.output.resolve()
    raw_dir = output / "raw/corpus"
    profiles = parse_tsv(here / "profiles.tsv")
    expected_rows = parse_tsv(here / "expected_failures.tsv")
    expected_failures = {row["path"]: row["reason"] for row in expected_rows}
    corpus = discover_corpus(code_repo)

    rows: list[dict[str, object]] = []
    problems: list[str] = []
    for profile in profiles:
        binary = code_repo / f"build/K4-{profile['slug']}/src/retractor/xretractor"
        if not binary.is_file():
            problems.append(f"brak binarki profilu {profile['profile']}: {binary}")
            continue
        for suite, source in corpus:
            relative = source.relative_to(code_repo).as_posix()
            digest = hashlib.sha256(relative.encode("utf-8")).hexdigest()[:12]
            raw_base = raw_dir / profile["slug"] / suite / f"{source.stem}-{digest}"
            outcome = compile_case(binary, source, raw_base)
            counters = outcome.pop("counters")
            expected_failure = relative in expected_failures
            if outcome["returncode"] == 0 and len(counters) == 1:
                status = "unexpected_success" if expected_failure else "compiled"
                r1, r2 = map(int, counters[0])
            elif outcome["returncode"] != 0 and expected_failure:
                status = "expected_failure"
                r1 = r2 = ""
            elif outcome["returncode"] != 0:
                status = "unexpected_failure"
                r1 = r2 = ""
            else:
                status = "missing_or_duplicate_counter"
                r1 = r2 = ""

            row: dict[str, object] = {
                "profile": profile["profile"],
                "slug": profile["slug"],
                "suite": suite,
                "path": relative,
                "expected_failure": expected_failure,
                "status": status,
                "r1": r1,
                "r2": r2,
                **outcome,
            }
            rows.append(row)
            if status not in {"compiled", "expected_failure"}:
                problems.append(f"{profile['profile']}: {relative}: {status}")

    for profile in profiles:
        compiled = [
            row
            for row in rows
            if row["profile"] == profile["profile"] and row["status"] == "compiled"
        ]
        if profile["factor"] == "OFF" and any(int(row["r1"]) != 0 for row in compiled):
            problems.append(f"{profile['profile']}: R1 nie jest zerem przy wyłączonej regule")
        if profile["commutative"] == "OFF" and any(int(row["r2"]) != 0 for row in compiled):
            problems.append(f"{profile['profile']}: R2 nie jest zerem przy wyłączonej regule")

    output.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "profile",
        "slug",
        "suite",
        "path",
        "expected_failure",
        "status",
        "returncode",
        "r1",
        "r2",
        "stdout_sha256",
        "stderr_sha256",
    ]
    with (output / "counts.csv").open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    corpus_rows = [
        {
            "suite": suite,
            "path": source.relative_to(code_repo).as_posix(),
            "expected": "compile_failure"
            if source.relative_to(code_repo).as_posix() in expected_failures
            else "compiled",
            "reason": expected_failures.get(source.relative_to(code_repo).as_posix(), "-"),
        }
        for suite, source in corpus
    ]
    with (output / "corpus.tsv").open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(
            target,
            fieldnames=["suite", "path", "expected", "reason"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(corpus_rows)

    payload = {
        "code_commit": subprocess.check_output(
            ["git", "-C", str(code_repo), "rev-parse", "HEAD"], text=True
        ).strip(),
        "profiles": profiles,
        "corpus_size": len(corpus),
        "rows": rows,
        "problems": problems,
    }
    (output / "counts.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_summary(output / "summary.md", rows, profiles, expected_failures)

    if problems:
        for problem in problems:
            print(problem)
        return 2
    print(f"OK: {len(profiles)} profili, {len(corpus)} plików RQL, {len(rows)} wyników")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
