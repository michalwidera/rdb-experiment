#!/usr/bin/env python3
"""Most oracle'a G3 do silnika - poprawka z 2026-10-02 (retractordb #353).

Przebieg jest ten sam co w results_20260726_G3/engine_check.py: ten sam plan, te same zrodla
i to samo porownanie wartosci z oracle'em G3. run_case i funkcje pomocnicze sa importowane
z katalogu zamrozonego, ktorego nie wolno zmieniac. Poprawione sa tylko dwie oceny:

1. Cisza wyjscia to origin + tail. Od 5f310515 plan drukuje oba pola osobno, a brak pola
   znaczy 0. Zamrozony plan_tail czytal samo tail=.
2. Oczekiwana cisza kazdego ksztaltu pochodzi z modelu zdarzeniowego K24 w konwencji C1
   (results_20260912_K24f/apparatus/oracle), a nie z zalozenia rownej ciszy trzech ksztaltow,
   ktore kodowalo regule W = W_src sprzed fcc5a444. Model jest sprawdzany wobec twierdzenia
   causal_shift_matching_declared (retractordb/math_proofs/Profs/InterleaveTailExact.lean):
   nad zrodlami deklarowanymi rowny origin, lhs.tail = W >= 1, rhs.tail = max(0, W - L).
   Sprzecznosc konczy przebieg bledem aparatury (kod 2).

Dodatkowo rekordy + cisza musza byc wspolne trzem wyjsciom: maja ten sam interwal i ten sam
przebieg, wiec krotsza cisza oznacza dokladnie tyle samo rekordow wiecej.

  engine_check.py --xretractor <binarka> --engine-commit <pelne SHA> --json <wynik>
"""
import argparse
import hashlib
import importlib.util
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

# Import nie moze zostawic __pycache__ w katalogach zamrozonych.
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
FROZEN = EXPERIMENT / "results_20260726_G3"
K24_ORACLE = EXPERIMENT / "results_20260912_K24f" / "apparatus" / "oracle"
sys.path.insert(0, str(K24_ORACLE))
sys.path.insert(0, str(FROZEN))

# Pod inna nazwa niz ten plik, zeby import nie zalezal od kolejnosci sys.path.
_spec = importlib.util.spec_from_file_location("g3_frozen_engine_check", FROZEN / "engine_check.py")
G3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G3)

import model as K24  # noqa: E402
from plan import Plan, make_hash, make_shift, make_source  # noqa: E402

OUTPUTS = G3.OUTPUTS
# Ksztalt kazdego wyjscia; optimized ma ksztalt prawej strony, gdy R1 przepisal plan.
SHAPES = {"optimized": None, "blocked": "lhs", "explicit_rhs": "rhs"}


class ApparatusError(RuntimeError):
    """Oracle przeczy twierdzeniu - nie moze rozstrzygac o silniku."""


def silence(plan, stream):
    line = re.search(rf"^{re.escape(stream)}\([^)\n]*\)(.*)$", plan, re.MULTILINE)
    if line is None:
        raise ValueError(f"brak strumienia {stream} w planie")
    fields = [re.search(rf"\b{key}=(\d+)", line.group(1)) for key in ("origin", "tail")]
    return tuple(int(found.group(1)) if found else 0 for found in fields)


def expected_silence(result):
    """Origin i ogon obu ksztaltow w modelu K24 (C1), sprawdzone wobec twierdzenia Lean."""
    a = make_source("A", Fraction(result["delta_a"]), 2)
    b = make_source("B", Fraction(result["delta_b"]), 2)
    shifted_a = make_shift("SA", a, result["shift_a"])
    shifted_b = make_shift("SB", b, result["shift_b"])
    plain = make_hash("H", a, b)
    shapes = {
        "lhs": (a, b, shifted_a, shifted_b, make_hash("O", shifted_a, shifted_b)),
        "rhs": (a, b, plain, make_shift("O", plain, result["combined"])),
    }
    found = {}
    hash_tail = None
    for shape, nodes in shapes.items():
        evaluated = {node.name: node for node in K24.evaluate(Plan(nodes=nodes), convention=K24.C1)}
        found[shape] = (evaluated["O"].origin, evaluated["O"].tail)
        if shape == "rhs":
            hash_tail = evaluated["H"].tail
    shift = result["combined"]
    if (
        hash_tail < 1
        or found["lhs"][0] != found["rhs"][0]
        or found["lhs"][1] != hash_tail
        or found["rhs"][1] != max(0, hash_tail - shift)
    ):
        raise ApparatusError(
            f"K24-C1 przeczy causal_shift_matching_declared w {result['case']}: "
            f"lhs {found['lhs']}, rhs {found['rhs']}, W={hash_tail}, L={shift}"
        )
    return found, hash_tail


def evaluate(result, plan):
    want, hash_tail = expected_silence(result)
    shape = {name: SHAPES[name] or ("rhs" if result["optimized_shape"] else "lhs") for name in OUTPUTS}
    got = {name: silence(plan, name) for name in OUTPUTS}
    outputs = [result["outputs"][name] for name in OUTPUTS]
    checks = (
        ("oracle G3 lhs=rhs", result["oracle_lhs_equals_rhs"]),
        ("wartosci", all(o["mismatch_count"] == 0 for o in outputs)),
        (
            "meta/luki/schemat",
            all(o["records"] == o["meta_records"] and o["gaps"] == [] and o["schema"] == G3.SCHEMA for o in outputs),
        ),
        ("interwal", all(value == result["expected_interval"] for value in result["intervals"].values())),
        ("ksztalt R1", result["optimized_shape"]),
        ("ksztalt blocked", result["blocked_shape"]),
        ("pusta dziedzina", all(result["null_coverage"].values()) and min(o["records"] for o in outputs) > 0),
        ("cisza", all(got[name] == want[shape[name]] for name in OUTPUTS)),
        ("rekordy+cisza", len({o["records"] + sum(got[name]) for name, o in zip(OUTPUTS, outputs)}) == 1),
    )
    failed = [label for label, ok in checks if not ok]
    return {
        "hash_tail": hash_tail,
        "shape": shape,
        "silence": {name: list(got[name]) for name in OUTPUTS},
        "expected_silence": {name: list(want[shape[name]]) for name in OUTPUTS},
        "failed": failed,
        "status": "OK" if not failed else "MISMATCH",
    }


def pairs_text(pairs):
    return "/".join(f"{origin}+{tail}" for origin, tail in pairs)


def git_state(path):
    commit = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True,
                            check=True).stdout.strip()
    status = subprocess.run(["git", "-C", str(path), "status", "--short"], capture_output=True, text=True,
                            check=True).stdout.splitlines()
    return {"commit": commit, "dirty": bool(status), "status": status}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--xretractor", required=True)
    # Binarka nie zna wlasnego SHA (napis Branch w --help powstaje przy konfiguracji), wiec
    # przypiecie podaje sie jawnie i nie zgaduje.
    parser.add_argument("--engine-commit", required=True)
    parser.add_argument("--workdir")
    parser.add_argument("--json")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.engine_commit):
        print("--engine-commit musi byc pelnym SHA (40 znakow)", file=sys.stderr)
        return 2

    binary = Path(args.xretractor).resolve()
    build_info = G3.run_checked([str(binary), "--build-info"], cwd=Path.cwd(), timeout=10).stdout.strip()
    workroot = Path(args.workdir).resolve() if args.workdir else Path(tempfile.mkdtemp(prefix="g3b-"))
    workroot.mkdir(parents=True, exist_ok=True)

    cases = []
    try:
        for case in G3.ENGINE_CASES:
            result = G3.run_case(binary, workroot, case)
            plan = (workroot / case.name / "plan.txt").read_text(encoding="utf-8")
            verdict = evaluate(result, plan)
            report = {key: value for key, value in result.items() if key not in ("tails", "expected_tail", "status")}
            report["frozen_status"] = result["status"]
            report.update(verdict)
            cases.append(report)
            records = "/".join(str(result["outputs"][name]["records"]) for name in OUTPUTS)
            print(
                f"{case.name:<14} cisza {pairs_text(verdict['silence'][n] for n in OUTPUTS)} "
                f"(K24-C1 {pairs_text(verdict['expected_silence'][n] for n in OUTPUTS)}) rekordy {records} "
                f"{verdict['status']}" + (f" ({', '.join(verdict['failed'])})" if verdict["failed"] else "")
            )
    except ApparatusError as error:
        print(f"BLAD APARATURY: {error}", file=sys.stderr)
        return 2
    finally:
        if not args.workdir:
            shutil.rmtree(workroot, ignore_errors=True)

    failed = [case for case in cases if case["status"] != "OK"]
    report = {
        "apparatus": "results_20261002_G3b/engine_check.py",
        "issue": "retractordb #353",
        "binary_name": binary.name,
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "build_info": build_info,
        "engine_commit": args.engine_commit,
        "experiment": git_state(EXPERIMENT),
        "python": sys.version,
        "platform": platform.platform(),
        "silence_reference": "K24 event model, convention C1, checked against causal_shift_matching_declared",
        "cases": cases,
        "verdict": "OK" if not failed else "MISMATCH",
    }
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWYNIK: {len(cases) - len(failed)}/{len(cases)} przypadkow zgodnych")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
