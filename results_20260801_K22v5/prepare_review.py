#!/usr/bin/env python3
"""Przygotowuje zaślepione diffy i trafienia bez automatycznych D1/D2."""

import csv
import difflib
import importlib.util
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "results_20260801_K22"
TASKS = HERE / "tasks"
REVIEW = HERE / "evidence/review"
FAMILY_DIR = {"F1": "F1_fir", "F2": "F2_ecg", "F3": "F3_multirate"}
JAVA_NAME = {"F1": "F1Fir.java", "F2": "F2Ecg.java", "F3": "F3Multirate.java"}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(HERE / "metrics"))
diffsites = load("k22v3_review_diffsites", HERE / "metrics/diffsites.py")
measure = load("k22v3_review_measure", HERE / "metrics/measure.py")


def core(task, family, model, base=False):
    root = PILOT / "corpus" / FAMILY_DIR[family] if base else TASKS / task / FAMILY_DIR[family]
    rel = {"rql": "rql/core.rql", "python": "python/core.py",
           "flink": f"flink/{JAVA_NAME[family]}"}[model]
    return root / rel


def main():
    if (HERE / "results/modifications_auto.csv").exists():
        raise SystemExit("BLAD: automatyczne D1/D2 już istnieje; nie można deklarować zaślepionego kodowania")
    REVIEW.mkdir(parents=True, exist_ok=True)
    manual_rows, hit_rows = [], []
    for task in ("M1", "M2", "M3", "M4"):
        for family in FAMILY_DIR:
            for model in ("rql", "python", "flink"):
                base, variant = core(task, family, model, True), core(task, family, model, False)
                left = diffsites.normalized_lines(base)
                right = diffsites.normalized_lines(variant)
                text = [f"# {task}/{family}/{model}\n", "# BASE (znormalizowane)\n"]
                text += [f"B{line:04d} {value}\n" for line, value in left]
                text += ["# VARIANT (znormalizowane)\n"]
                text += [f"V{line:04d} {value}\n" for line, value in right]
                text += ["# DIFF -U0 (bez automatycznych liczników)\n"]
                text += difflib.unified_diff([x[1] + "\n" for x in left], [x[1] + "\n" for x in right], n=0)
                (REVIEW / f"{task}_{family}_{model}.txt").write_text("".join(text), encoding="utf-8")
                manual_rows.append({"task": task, "family": family, "model": model,
                                    "D1": "", "D2": "", "coder": "Codex-manual"})
    for task in ("base", "M1", "M2", "M3", "M4"):
        for family in FAMILY_DIR:
            for model in ("rql", "python", "flink"):
                path = core("M1" if task == "base" else task, family, model, task == "base")
                _counts, hits, _loc, _cyc = measure.measure(path)
                for hit in hits:
                    hit_rows.append({"task": task, "family": family, "model": model,
                                     "metric": hit.metric, "rule_id": hit.rule_id,
                                     "path": hit.path, "line": hit.line,
                                     "confirmed": "", "coder": "Codex-manual"})
    with (HERE / "manual_coding_template.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manual_rows[0])); writer.writeheader(); writer.writerows(manual_rows)
    with (HERE / "manual_hits_review_template.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(hit_rows[0])); writer.writeheader(); writer.writerows(hit_rows)
    print(f"OK: {len(manual_rows)} zaślepionych diffów, {len(hit_rows)} trafień do przeglądu")
    return 0


if __name__ == "__main__":
    sys.exit(main())
