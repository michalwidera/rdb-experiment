#!/usr/bin/env python3
"""Kontrola wejściowa K6 — czy przeskalowane workloady to nadal plany z K5.

K6 mierzy czas planów, których strukturę rozstrzygnął K5. Gdyby przeskalowanie
rate'u zmieniło strukturę, kampania mierzyłaby coś innego, niż zamknął werdykt
go/no-go. Ta kontrola jest warunkiem unieważniającym nr 4 z README: `net` i `r1`
muszą odtworzyć tabelę werdyktu K5, przepisaną niżej jako OCZEKIWANIA.

Rodzina W9 jest nowa i jej pierwsza predykcja **zawiodła**, co jest tu zapisane,
a nie zamiecione. Przewidziano `net = -2` przez analogię do testu
`select_cse_commutative_add` (usunięty substrat plus osierocony `STREAM_ADD`).
Pomiar compile-only dał `net = +1` dla `Q = 2` i `net = -1` dla `Q >= 4`.

Mechanizm opisany w README okazał się jednak dokładnie taki, jak zapisano:
liczba wykonań kosztownego programu pól na slot spada z **2 do 1**. Zmienia się
tylko to, czego nie wolno mierzyć liczbą węzłów:

| `Q` | `STRUCT` | `ALGSTRUCT` | wykonania programu na slot | `net` |
|---:|---|---|---:|---:|
| 1 | brak substratu | brak substratu | 1 -> 1 | 0 |
| 2 | brak substratu, dwa publiczne liczą same | jeden substrat + dwie lekkie projekcje | 2 -> 1 | **+1** |
| 4..32 | **dwa** substraty `STREAM_SELECT_*` | **jeden** substrat | 2 -> 1 | -1 |

Dla `Q = 2` plan jest **większy**, a praca na slot **mniejsza**. Dlatego
kryterium W9 nie jest `net`, lecz liczba substratów wykonujących wspólny program:
`exec = liczba STREAM_SELECT_* albo Q, gdy nie ma żadnego`. Wymagane jest
`exec_STRUCT = 2`, `exec_ALGSTRUCT = 1` i `r2 >= 1` dla `Q >= 2`, oraz brak
scalenia dla zdegenerowanego `Q = 1`. `net` jest raportowany, nie testowany —
i jest samodzielnym wynikiem dla artykułu, bo pokazuje na własnym przykładzie,
dlaczego H4 zabrania zastępowania korzyści rozmiarem planu.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
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
COMPILE_NS_RE = re.compile(r"^COMPILE_NS (\d+) sonda=(\d+)$", re.MULTILINE)
CAPACITY_RE = re.compile(r"^PLAN capacity: strumieni=(\d+) suma=(\d+) maks=(-?\d+)$", re.MULTILINE)

STAGE_ROOT = "/dev/shm"

# Tabela werdyktu K5 (research_plan.md, krok K5), przepisana dosłownie.
# W2, W4 i W8: net = -1, r1 = Q. W1: net = -1, r1 = 1. W5, W6, W7: zera.
K5_W3_NET = {1: -1, 2: -2, 3: -3}
K5_W3_R1 = {1: 8, 2: 9, 3: 10}


def parse_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source, delimiter="\t"))


def stage(case_dir: Path, code_repo: Path, work: Path) -> None:
    work.mkdir(parents=True)
    (work / "temp").mkdir()
    shutil.copy(case_dir / "query.rql", work / "query.rql")
    external = case_dir / "external_data.txt"
    if external.is_file():
        # R2: dane wejściowe są KOPIOWANE, nie symlinkowane. Symlink daje
        # silnikowi ścieżkę, przy której artefakt może powstać w repozytorium
        # kodu — defekt wykryty 2026-07-30.
        for relative in external.read_text(encoding="utf-8").split():
            shutil.copy(code_repo / relative, work / Path(relative).name)
    for extra in sorted(case_dir.glob("*.txt")):
        if extra.name != "external_data.txt":
            shutil.copy(extra, work / extra.name)


def compile_case(binary: Path, case_dir: Path, code_repo: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="rdb-k6-chk-", dir=STAGE_ROOT) as root:
        work = Path(root) / "case"
        stage(case_dir, code_repo, work)
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
                timeout=180,
                check=False,
            )
            returncode, stdout, stderr = completed.returncode, completed.stdout, completed.stderr
        except subprocess.TimeoutExpired as error:
            returncode, stdout, stderr = 124, error.stdout or "", (error.stderr or "") + "\nK6_TIMEOUT\n"

    nodes = sorted(set(NODE_RE.findall(stdout)))
    counters = COUNTER_RE.findall(stderr)
    bench = BENCH_RE.findall(stderr)
    compile_ns = COMPILE_NS_RE.findall(stderr)
    capacity = CAPACITY_RE.findall(stderr)

    if returncode != 0:
        status = "compile_failure"
    elif len(counters) != 1 or len(bench) != 1 or len(compile_ns) != 1 or len(capacity) != 1:
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
        result["compile_ns"] = int(compile_ns[0][0])
        result["probe_ns"] = int(compile_ns[0][1])
        result["capacity_streams"] = int(capacity[0][0])
        result["capacity_sum"] = int(capacity[0][1])
        result["capacity_max"] = int(capacity[0][2])
        values = [int(v) for v in bench[0]]
        out = values[12:16]
        result["wyjscie_publiczne"], result["wyjscie_substraty"] = out[0], out[1]
        result["wyjscie_tokeny_from"], result["wyjscie_tokeny_pol"] = out[2], out[3]
    return result


def expected(family: str, param: str, q: int) -> dict[str, object]:
    """Oczekiwanie dla rodziny; None oznacza brak oczekiwania na wartość."""
    if family == "W3":
        depth = int(param.split("=")[1])
        return {"net": K5_W3_NET[depth], "r1": K5_W3_R1[depth], "r2": None, "source": "K5"}
    if family in ("W2", "W4", "W8"):
        return {"net": -1, "r1": q, "r2": None, "source": "K5"}
    if family == "W1":
        return {"net": -1, "r1": 1, "r2": None, "source": "K5"}
    if family in ("W5", "W6", "W7"):
        return {"net": 0, "r1": 0, "r2": None, "source": "K5"}
    if family == "W9":
        # Kryterium mechanizmowe, nie węzłowe — patrz docstring modułu.
        if q == 1:
            return {"net": 0, "r1": 0, "r2": None, "source": "mechanizm K6", "net_relation": "report", "exec": (1, 1)}
        return {"net": None, "r1": 0, "r2": None, "source": "mechanizm K6", "net_relation": "report", "exec": (2, 1), "r2_min": 1}
    raise KeyError(family)


def shared_exec_count(nodes: list[str], q: int) -> int:
    """Liczba wykonań wspólnego programu pól na slot.

    Substrat `STREAM_SELECT_*` wykonuje program raz na slot dla wszystkich swoich
    konsumentów. Jeżeli żadnego nie ma, program liczy każdy strumień publiczny
    osobno, czyli `Q` razy.
    """
    shared = sum(1 for name in nodes if name.startswith("STREAM_SELECT_"))
    return shared if shared > 0 else q


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-repo", type=Path, required=True)
    parser.add_argument("--workloads", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--build-prefix", default="K6", help="przedrostek katalogów build/<prefix>-<slug>")
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
    compiled = 0
    for profile in profiles:
        slug = profile["slug"]
        binary = code_repo / f"build/{args.build_prefix}-{slug}/src/retractor/xretractor"
        if not binary.is_file():
            problems.append(f"brak binarki profilu {profile['profile']}: {binary}")
            continue
        observations[profile["profile"]] = {}
        for entry in index:
            case = str(entry["case"])
            record = compile_case(binary, workloads / case, code_repo)
            observations[profile["profile"]][case] = record
            if record["status"] == "compiled":
                compiled += 1
            else:
                problems.append(f"{profile['profile']}/{case}: {record['status']} rc={record['returncode']}")

    # Reguła zliczania: zero porównanych rzeczy jest błędem, nie zgodnością.
    if compiled == 0:
        print("BLAD: nie skompilowano ani jednego przypadku", file=sys.stderr)
        return 2

    comparisons: list[dict[str, object]] = []
    mismatches: list[str] = []
    for entry in index:
        case = str(entry["case"])
        family, param, q = str(entry["family"]), str(entry["param"]), int(entry["q"])
        struct = observations.get("STRUCT", {}).get(case)
        alg = observations.get("ALGSTRUCT", {}).get(case)
        if not struct or not alg or struct["status"] != "compiled" or alg["status"] != "compiled":
            mismatches.append(f"{case}: brak kompletnej pary STRUCT/ALGSTRUCT")
            continue
        net = int(alg["node_count"]) - int(struct["node_count"])
        exp = expected(family, param, q)
        exec_struct = shared_exec_count(list(struct["nodes"]), q)  # type: ignore[arg-type]
        exec_alg = shared_exec_count(list(alg["nodes"]), q)  # type: ignore[arg-type]
        record = {
            "exec_struct": exec_struct,
            "exec_alg": exec_alg,
            "family": family,
            "case": case,
            "param": param,
            "q": q,
            "net": net,
            "r1": alg["r1"],
            "r2": alg["r2"],
            "expected_net": exp["net"],
            "expected_r1": exp["r1"],
            "source": exp["source"],
            "nodes_struct": struct["node_count"],
            "nodes_alg": alg["node_count"],
            "removed": sorted(set(struct["nodes"]) - set(alg["nodes"])),
            "added": sorted(set(alg["nodes"]) - set(struct["nodes"])),
        }
        relation = exp.get("net_relation", "eq")
        if relation == "eq":
            if net != exp["net"]:
                mismatches.append(f"{case}: net={net}, oczekiwano {exp['net']} ({exp['source']})")
        elif relation == "report":
            # net jest raportowany, kryterium jest mechanizmowe.
            want_struct, want_alg = exp["exec"]  # type: ignore[misc]
            if (exec_struct, exec_alg) != (want_struct, want_alg):
                mismatches.append(
                    f"{case}: wykonania wspólnego programu {exec_struct}->{exec_alg}, "
                    f"oczekiwano {want_struct}->{want_alg} ({exp['source']})"
                )
        if exp["r1"] is not None and int(alg["r1"]) != int(exp["r1"]):
            mismatches.append(f"{case}: r1={alg['r1']}, oczekiwano {exp['r1']} ({exp['source']})")
        if "r2_min" in exp and int(alg["r2"]) < int(exp["r2_min"]):
            mismatches.append(f"{case}: r2={alg['r2']}, oczekiwano >= {exp['r2_min']} ({exp['source']})")
        comparisons.append(record)

    if not comparisons:
        print("BLAD: zero porównań; brak pary STRUCT/ALGSTRUCT", file=sys.stderr)
        return 2

    report = {
        "compiled_runs": compiled,
        "expected_runs": len(profiles) * len(index),
        "comparisons": len(comparisons),
        "problems": problems,
        "mismatches": mismatches,
        "records": comparisons,
    }
    (output / "counters.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Kontrola wejściowa K6 — liczniki wobec werdyktu K5",
        "",
        f"- kompilacji: {compiled} z {len(profiles) * len(index)}",
        f"- porównań STRUCT vs ALGSTRUCT: {len(comparisons)}",
        f"- niezgodności: {len(mismatches)}",
        "",
        "| Przypadek | net | oczekiwane | r1 | oczekiwane r1 | r2 | wykonania wspólnego programu | źródło |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for record in comparisons:
        lines.append(
            f"| `{record['case']}` | {record['net']} | {record['expected_net']} | {record['r1']} | "
            f"{record['expected_r1']} | {record['r2']} | {record['exec_struct']}->{record['exec_alg']} | "
            f"{record['source']} |"
        )
    if mismatches:
        lines += ["", "## Niezgodności", ""] + [f"- {m}" for m in mismatches]
    if problems:
        lines += ["", "## Problemy", ""] + [f"- {p}" for p in problems]
    (output / "counters.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"kompilacji: {compiled}, porównań: {len(comparisons)}, niezgodności: {len(mismatches)}")
    for problem in problems:
        print(f"problem: {problem}", file=sys.stderr)
    for mismatch in mismatches:
        print(f"niezgodność: {mismatch}", file=sys.stderr)
    return 1 if (mismatches or problems) else 0


if __name__ == "__main__":
    raise SystemExit(main())
