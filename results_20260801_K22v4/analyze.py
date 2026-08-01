#!/usr/bin/env python3
"""Metryki konstrukcji, D1/D2, pełne drugie kodowanie i werdykt K22v4."""

import csv
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "results_20260801_K22"
TASKS = HERE / "tasks"
RESULTS = HERE / "results"
EVIDENCE = HERE / "evidence"
FAMILY_DIR = {"F1": "F1_fir", "F2": "F2_ecg", "F3": "F3_multirate"}
MODEL_PATH = {
    "rql": ("rql/core.rql", "rql/core.rql"),
    "python": ("python/core.py", "python/core.py"),
    "flink": ("flink/F1Fir.java", "flink/F1Fir.java"),
}
JAVA_NAME = {"F1": "F1Fir.java", "F2": "F2Ecg.java", "F3": "F3Multirate.java"}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


measure_mod = load_module("k22v2_measure", HERE / "metrics/measure.py")
sys.path.insert(0, str(HERE / "metrics"))
diff_mod = load_module("k22v2_diffsites", HERE / "metrics/diffsites.py")


class AnalysisError(RuntimeError):
    pass


def paths(task, family, model):
    base_root = PILOT / "corpus" / FAMILY_DIR[family]
    var_root = TASKS / task / FAMILY_DIR[family]
    rel = {"rql": "rql/core.rql", "python": "python/core.py",
           "flink": f"flink/{JAVA_NAME[family]}"}[model]
    return base_root / rel, var_root / rel


def write_csv(path, rows, fields=None):
    if not rows and fields is None:
        raise AnalysisError(f"brak wierszy dla {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def construction_metrics():
    rows, hits = [], []
    programs = [("base", family) for family in FAMILY_DIR]
    programs += [(task, family) for task in ("M1", "M2", "M3", "M4") for family in FAMILY_DIR]
    for task, family in programs:
        for model in ("rql", "python", "flink"):
            path = paths("M1" if task == "base" else task, family, model)[0 if task == "base" else 1]
            counts, found, loc, cyclomatic = measure_mod.measure(path)
            rows.append({"task": task, "family": family, "model": model,
                         **counts, "loc": loc, "cyclomatic": cyclomatic})
            for hit in found:
                record = {"task": task, "family": family, "model": model}
                record.update(hit.__dict__)
                hits.append(record)
    write_csv(RESULTS / "constructs.csv", rows)
    write_csv(RESULTS / "hits.csv", hits)
    return rows, hits


def modification_metrics():
    rows = []
    for task in ("M1", "M2", "M3", "M4"):
        for family in FAMILY_DIR:
            for model in ("rql", "python", "flink"):
                base, variant = paths(task, family, model)
                result = diff_mod.compare(base, variant)
                cell = EVIDENCE / "diffs" / task / family
                cell.mkdir(parents=True, exist_ok=True)
                (cell / f"{model}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                (cell / f"{model}.diff").write_text("".join(result["diff"]), encoding="utf-8")
                rows.append({"task": task, "family": family, "model": model,
                             "D1": result["D1"], "D2": result["D2"],
                             "sites_file": str((cell / f"{model}.json").relative_to(HERE))})
    write_csv(RESULTS / "modifications_auto.csv", rows)
    return rows


def load_manual():
    path = HERE / "manual_coding.csv"
    if not path.is_file():
        raise AnalysisError("brak manual_coding.csv: pełne drugie kodowanie jest bramką")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def reconcile(auto, manual):
    keys = lambda row: (row["task"], row["family"], row["model"])
    auto_by = {keys(row): row for row in auto}
    manual_by = {keys(row): row for row in manual}
    if set(auto_by) != set(manual_by):
        missing = sorted(set(auto_by) - set(manual_by))
        extra = sorted(set(manual_by) - set(auto_by))
        raise AnalysisError(f"drugie kodowanie: brak={missing}, nadmiar={extra}")
    rows = []
    for key in sorted(auto_by):
        a, m = auto_by[key], manual_by[key]
        if int(m["D1"]) != a["D1"] or int(m["D2"]) != a["D2"]:
            raise AnalysisError(f"rozbieżność drugiego kodowania {key}: auto D1/D2={a['D1']}/{a['D2']}, ręczne={m['D1']}/{m['D2']}")
        rows.append({**a, "manual_D1": m["D1"], "manual_D2": m["D2"], "coder": m["coder"], "agreement": "YES"})
    write_csv(RESULTS / "modifications.csv", rows)
    return rows


def verify_hits(hits):
    path = HERE / "manual_hits_review.csv"
    if not path.is_file():
        raise AnalysisError("brak manual_hits_review.csv: pełny przegląd trafień jest bramką")
    with path.open(newline="", encoding="utf-8") as handle:
        review = list(csv.DictReader(handle))
    expected = {(x["task"], x["family"], x["model"], x["metric"], x["rule_id"],
                 x["path"], str(x["line"])) for x in hits}
    observed = {(x["task"], x["family"], x["model"], x["metric"], x["rule_id"],
                 x["path"], x["line"]) for x in review if x["confirmed"] == "YES"}
    if expected != observed:
        raise AnalysisError(f"przegląd trafień nie jest pełny: expected={len(expected)}, confirmed={len(observed)}")


def verdict(rows):
    by = {(r["task"], r["family"], r["model"]): int(r["D2"]) for r in rows}
    cells = []
    for family in FAMILY_DIR:
        wins = 0
        for task in ("M1", "M2", "M3", "M4"):
            rql, py, flink = by[(task, family, "rql")], by[(task, family, "python")], by[(task, family, "flink")]
            computed = rql < py and rql < flink
            forced = task == "M1" and family in {"F2", "F3"}
            win = False if forced else computed
            wins += int(win)
            cells.append({"task": task, "family": family, "D2_rql": rql, "D2_python": py,
                          "D2_flink": flink, "computed_win": "YES" if computed else "NO",
                          "forced_nonwin": "YES" if forced else "NO", "counted_win": "YES" if win else "NO"})
        threshold = 3
        passed = wins >= threshold
        for row in cells:
            if row["family"] == family:
                row["family_wins"] = wins
                row["family_threshold"] = threshold
                row["family_pass"] = "YES" if passed else "NO"
    write_csv(RESULTS / "wins.csv", cells)
    family_pass = {family: cells_for[0]["family_pass"] == "YES" for family in FAMILY_DIR
                   if (cells_for := [x for x in cells if x["family"] == family])}
    support = sum(family_pass.values()) >= 2
    lines = ["# K22v4 — werdykt H8", "", "Kampania jest prospektywną kontynuacją po zatrzymanym pilocie K22.", "",
             "| Rodzina | Wygrane | Próg | Wynik |", "|---|---:|---:|---|"]
    for family in FAMILY_DIR:
        row = next(x for x in cells if x["family"] == family)
        lines.append(f"| {family} | {row['family_wins']}/4 | {row['family_threshold']}/4 | {'PASS' if family_pass[family] else 'FAIL'} |")
    lines += ["", f"**H8: {'OGRANICZONE WSPARCIE' if support else 'BRAK WSPARCIA'}** ({sum(family_pass.values())}/3 rodzin).", "",
              "M1/F2 i M1/F3 pozostają z góry zapisanymi brakami wygranej niezależnie od pomiaru."]
    (RESULTS / "verdict.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    subprocess.run([str(HERE / "freeze_check.sh")], check=True)
    manual = load_manual()
    constructs, hits = construction_metrics()
    auto = modification_metrics()
    rows = reconcile(auto, manual)
    verify_hits(hits)
    verdict(rows)
    print("OK: metryki, pełne drugie kodowanie i werdykt")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AnalysisError, OSError, subprocess.CalledProcessError, measure_mod.MeasureError) as exc:
        print(f"BLAD APARATURY: {exc}", file=sys.stderr)
        sys.exit(2)
