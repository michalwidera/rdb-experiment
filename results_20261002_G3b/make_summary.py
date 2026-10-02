#!/usr/bin/env python3
"""results/summary.md z wszystkich results/engine-*.json poprawionego mostu G3."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUTS = ("optimized", "blocked", "explicit_rhs")


def pairs(mapping):
    return "/".join(f"{origin}+{tail}" for origin, tail in (mapping[name] for name in OUTPUTS))


lines = [
    "# Poprawiony most G3 - wyniki",
    "",
    "Cisza `origin+tail` w kolejnosci optimized/blocked/explicit_rhs; oczekiwana z K24-C1,",
    "sprawdzonego wobec `causal_shift_matching_declared`. Generuje `make_summary.py`.",
]
for path in sorted((HERE / "results").glob("engine-*.json")):
    report = json.loads(path.read_text(encoding="utf-8"))
    ok = sum(case["status"] == "OK" for case in report["cases"])
    lines += [
        "",
        f"## Silnik `{report['engine_commit']}`",
        "",
        f"- plik: `results/{path.name}`, werdykt **{report['verdict']}** ({ok}/{len(report['cases'])})",
        f"- binarka: `{report['binary_name']}`, sha256 `{report['binary_sha256'][:12]}`",
        f"- przelaczniki: {' '.join(report['build_info'].split())}",
        f"- rdb-experiment: `{report['experiment']['commit'][:8]}`"
        + (" (drzewo niezacommitowane)" if report["experiment"]["dirty"] else ""),
        "",
        "| przypadek | W_hash | cisza | K24-C1 | rekordy | rozbieznosci wartosci | zamrozony G3 | wynik |",
        "|---|--:|---|---|---|---|---|---|",
    ]
    for case in report["cases"]:
        records = "/".join(str(case["outputs"][name]["records"]) for name in OUTPUTS)
        mismatch = "/".join(str(case["outputs"][name]["mismatch_count"]) for name in OUTPUTS)
        status = case["status"] + (f" ({', '.join(case['failed'])})" if case["failed"] else "")
        lines.append(
            f"| {case['case']} | {case['hash_tail']} | {pairs(case['silence'])} | {pairs(case['expected_silence'])} "
            f"| {records} | {mismatch} | {case['frozen_status']} | {status} |"
        )
(HERE / "results" / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"zapisano {HERE / 'results' / 'summary.md'}")
