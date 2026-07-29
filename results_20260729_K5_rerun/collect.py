#!/usr/bin/env python3
"""Kolektor K5 — kompilacja compile-only każdego workloadu pod każdym profilem.

Metryką pierwotną jest ZBIÓR NAZW WĘZŁÓW planu wyjściowego, bo pytanie K5
dotyczy węzłów, a nie liczb. Metryki wtórne: czwórka `PLAN bench` i liczniki
`REWRITE_APPLIED`.

Wyjście kompilatora nie jest hashowane w całości — zawiera ścieżki bezwzględne
katalogu roboczego i jest nieodtwarzalne między przebiegami. Hashowany jest
znormalizowany zbiór nazw węzłów.
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

NODE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\(", re.MULTILINE)
COUNTER_RE = re.compile(r"^REWRITE_APPLIED r1=(\d+) r2=(\d+)$", re.MULTILINE)
BENCH_RE = re.compile(
    r"^PLAN bench \(publiczne/substraty/tokeny-from/tokeny-pol, dedup=(?:ON|OFF)\): "
    r"wejscie=(\d+)/(\d+)/(\d+)/(\d+)\s+"
    r"przed-dedup=(\d+)/(\d+)/(\d+)/(\d+)\s+"
    r"po-dedup=(\d+)/(\d+)/(\d+)/(\d+)\s+"
    r"wyjscie=(\d+)/(\d+)/(\d+)/(\d+)$",
    re.MULTILINE,
)

STAGE_ROOT = "/dev/shm"


def parse_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source, delimiter="\t"))


def compile_case(binary: Path, case_dir: Path, code_repo: Path, raw_base: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="rdb-k5-", dir=STAGE_ROOT) as stage:
        work = Path(stage) / "case"
        work.mkdir()
        (work / "temp").mkdir()
        shutil.copy(case_dir / "query.rql", work / "query.rql")

        external = case_dir / "external_data.txt"
        if external.is_file():
            # Duże wejścia (rekord EKG) tylko dowiązane — repozytorium kodu
            # pozostaje wyłącznie źródłem odczytu (REQUIREMENTS.md R2).
            for relative in external.read_text(encoding="utf-8").split():
                source = code_repo / relative
                (work / source.name).symlink_to(source)
        for extra in sorted(case_dir.glob("*.txt")):
            if extra.name != "external_data.txt":
                shutil.copy(extra, work / extra.name)

        environment = os.environ.copy()
        environment["RDB_BENCH_PLAN"] = "1"
        try:
            completed = subprocess.run(
                [str(binary), "query.rql", "-c"],
                cwd=work,
                env=environment,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=120,
                check=False,
            )
            returncode, stdout, stderr = completed.returncode, completed.stdout, completed.stderr
        except subprocess.TimeoutExpired as error:
            returncode = 124
            stdout = error.stdout or ""
            stderr = (error.stderr or "") + "\nK5_TIMEOUT\n"

    raw_base.parent.mkdir(parents=True, exist_ok=True)
    Path(f"{raw_base}.stdout").write_text(stdout, encoding="utf-8")
    Path(f"{raw_base}.stderr").write_text(stderr, encoding="utf-8")

    nodes = sorted(set(NODE_RE.findall(stdout)))
    counters = COUNTER_RE.findall(stderr)
    bench = BENCH_RE.findall(stderr)

    if returncode != 0:
        status = "compile_failure"
    elif len(counters) != 1 or len(bench) != 1:
        status = "missing_or_duplicate_probe"
    else:
        status = "compiled"

    result: dict[str, object] = {
        "status": status,
        "returncode": returncode,
        "nodes": nodes,
        "node_count": len(nodes),
        "nodes_sha256": hashlib.sha256("\n".join(nodes).encode("utf-8")).hexdigest(),
    }
    if status == "compiled":
        result["r1"], result["r2"] = (int(v) for v in counters[0])
        values = [int(v) for v in bench[0]]
        for offset, stage_name in enumerate(("wejscie", "przed_dedup", "po_dedup", "wyjscie")):
            public, substrates, from_tokens, field_tokens = values[offset * 4 : offset * 4 + 4]
            result[f"{stage_name}_publiczne"] = public
            result[f"{stage_name}_substraty"] = substrates
            result[f"{stage_name}_tokeny_from"] = from_tokens
            result[f"{stage_name}_tokeny_pol"] = field_tokens
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-repo", type=Path, required=True)
    parser.add_argument("--workloads", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    code_repo = args.code_repo.resolve()
    workloads = args.workloads.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    profiles = parse_tsv(here / "profiles.tsv")
    index = json.loads((workloads / "index.json").read_text(encoding="utf-8"))

    observations: dict[str, dict[str, dict[str, object]]] = {}
    problems: list[str] = []
    for profile in profiles:
        slug = profile["slug"]
        binary = code_repo / f"build/K5r-{slug}/src/retractor/xretractor"
        if not binary.is_file():
            problems.append(f"brak binarki profilu {profile['profile']}: {binary}")
            continue
        observations[profile["profile"]] = {}
        for entry in index:
            case = entry["case"]
            raw_base = output / "raw/compile" / slug / case
            observations[profile["profile"]][case] = compile_case(binary, workloads / case, code_repo, raw_base)

    if problems:
        # Bez kompletu profili porównanie STRUCT/ALGSTRUCT nie ma sensu.
        for problem in problems:
            print(problem)
        return 2

    # Przypadek wchodzi do reguły decyzyjnej tylko wtedy, gdy kompiluje się
    # czysto pod KAŻDYM profilem. Inaczej różnica mogłaby pochodzić z wady
    # kompilatora (defect_interval_resolution.md), a nie z badanych reguł.
    excluded: dict[str, list[str]] = {}
    for entry in index:
        case = entry["case"]
        bad = [name for name in observations if observations[name][case]["status"] != "compiled"]
        if bad:
            excluded[case] = sorted(bad)

    rows: list[dict[str, object]] = []
    for entry in index:
        case = entry["case"]
        for name in observations:
            record = observations[name][case]
            row: dict[str, object] = {
                "family": entry["family"],
                "case": case,
                "param": entry["param"],
                "q": entry["q"],
                "profile": name,
                "excluded": case in excluded,
            }
            row.update({key: value for key, value in record.items() if key != "nodes"})
            rows.append(row)

    comparisons: list[dict[str, object]] = []
    for entry in index:
        case = entry["case"]
        if case in excluded:
            continue
        struct = set(observations["STRUCT"][case]["nodes"])
        algstruct = set(observations["ALGSTRUCT"][case]["nodes"])
        comparisons.append(
            {
                "family": entry["family"],
                "case": case,
                "param": entry["param"],
                "q": entry["q"],
                "struct_nodes": len(struct),
                "algstruct_nodes": len(algstruct),
                "net": len(algstruct) - len(struct),
                "usuniete": sorted(struct - algstruct),
                "dodane": sorted(algstruct - struct),
                "struct_tokeny_from": observations["STRUCT"][case]["wyjscie_tokeny_from"],
                "algstruct_tokeny_from": observations["ALGSTRUCT"][case]["wyjscie_tokeny_from"],
                "struct_tokeny_pol": observations["STRUCT"][case]["wyjscie_tokeny_pol"],
                "algstruct_tokeny_pol": observations["ALGSTRUCT"][case]["wyjscie_tokeny_pol"],
                "r1": observations["ALGSTRUCT"][case]["r1"],
                "r2": observations["ALGSTRUCT"][case]["r2"],
            }
        )

    fieldnames = sorted({key for row in rows for key in row})
    with (output / "counts.csv").open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames, lineterminator="\n", restval="")
        writer.writeheader()
        writer.writerows(rows)

    with (output / "comparison.csv").open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(
            target,
            fieldnames=[
                "family", "case", "param", "q", "struct_nodes", "algstruct_nodes", "net",
                "usuniete", "dodane", "struct_tokeny_from", "algstruct_tokeny_from",
                "struct_tokeny_pol", "algstruct_tokeny_pol", "r1", "r2",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for record in comparisons:
            flat = dict(record)
            flat["usuniete"] = " ".join(record["usuniete"])
            flat["dodane"] = " ".join(record["dodane"])
            writer.writerow(flat)

    payload = {
        "code_commit": subprocess.check_output(
            ["git", "-C", str(code_repo), "rev-parse", "HEAD"], text=True
        ).strip(),
        "profiles": profiles,
        "cases": len(index),
        "excluded": excluded,
        "observations": observations,
        "comparisons": comparisons,
        "problems": problems,
    }
    (output / "counts.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if problems:
        for problem in problems:
            print(problem)
        return 2
    print(f"OK: {len(profiles)} profili x {len(index)} przypadków; wykluczone: {len(excluded)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
