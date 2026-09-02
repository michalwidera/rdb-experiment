#!/usr/bin/env python3
"""Generuje results/summary.md wyłącznie z surowych JSON-ów eksperymentu."""

import json
from datetime import datetime, timezone
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    equivalence = load("results/equivalence.json")
    engine = load("results/engine.json")
    out = [
        "# K2/G3 — independent shift-matching oracle",
        "",
        f"- engine commit: `{engine['code_commit']}`",
        f"- engine worktree: **{'dirty' if engine['code_worktree']['dirty'] else 'clean'}**, "
        f"diff SHA-256: `{engine['code_worktree']['diff_sha256'] or '—'}`",
        f"- experiment repository commit before the campaign: `{engine['experiment_commit']}`",
        f"- experiment worktree: **{'dirty' if engine['experiment_worktree']['dirty'] else 'clean'}**, "
        f"diff SHA-256: `{engine['experiment_worktree']['diff_sha256'] or '—'}`",
        f"- generated: {datetime.now(timezone.utc).isoformat()}",
        f"- oracle result: **{equivalence['verdict']}**",
        f"- engine bridge result: **{engine['verdict']}**",
        "",
        "## 1. Mutation qualification",
        "",
        "| mutation/control | detected as a difference | layers | verdict |",
        "|---|---:|---|---|",
    ]
    for name, info in equivalence["mutations"].items():
        out.append(
            f"| `{name}` | {'yes' if info['detected'] else 'no'} | "
            f"{', '.join(info['layers']) or '—'} | {info['verdict']} |"
        )

    coverage = equivalence["payload_domain"]["coverage"]
    out += [
        "",
        "## 2. Purely model-level matrix",
        "",
        "| campaign | cases | positions | mismatches | time [s] | checksum64 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for campaign in equivalence["campaigns"]:
        out.append(
            f"| {campaign['label']} | {campaign['cases']} | {campaign['positions']} | "
            f"{len(campaign['mismatches'])} | {campaign['seconds']} | `{campaign['checksum64']}` |"
        )
    totals = equivalence["totals"]
    out += [
        "",
        f"In total: **{totals['cases']} cases**, **{totals['positions']} positions**, "
        f"**{totals['mismatches']} mismatches**.",
        "",
        "Explicit check of the record domain:",
        "",
        f"- no NULL: {coverage['present']};",
        f"- partial NULL: {coverage['partial_null']};",
        f"- all-null: {coverage['all_null']}.",
        "",
        f"Unmatched shifts rejected: "
        f"**{sum(case['rejected'] for case in equivalence['unmatched_guard']['cases'])}/"
        f"{len(equivalence['unmatched_guard']['cases'])}**.",
        "",
        "## 3. Oracle — RetractorDB bridge",
        "",
        "| case | min Δ [ms] | ΔA/ΔB | i+k | W | # tail legacy/safe | "
        "records opt/blocked/rhs | blocked errors | result |",
        "|---|---:|---|---:|---:|---|---|---:|---|",
    ]
    for case in engine["cases"]:
        records = "/".join(str(case["outputs"][name]["records"]) for name in ("optimized", "blocked", "explicit_rhs"))
        out.append(
            f"| {case['case']} | {case['min_interval_ms']} | {case['ratio']} | {case['combined']} | "
            f"{case['expected_tail']} | {case['legacy_hash_tail']}/{case['phase_safe_hash_tail']} | "
            f"{records} | {case['outputs']['blocked']['mismatch_count']} | {case['status']} |"
        )

    out += [
        "",
        "Every case executes three plan forms: the LHS rewritten by R1, the LHS "
        "blocked by public shift streams, and the explicit RHS. Each of them is "
        "compared directly against the oracle.",
        "",
        "`# tail safe` is the maximum required lookahead of B over all phases of one "
        "period. The difference against the former `ceil(delta_B/delta_A)` predicted "
        "exactly the cases with all-null records in the non-rewritten LHS.",
        "",
        "## 4. Gap semantics",
        "",
        "In the current runtime, gap detection writes no markers for computed "
        "streams, so the observable gap trace of R1 results is `G_S = ∅`. The "
        "mutation matrix confirms that the comparator detects an injected marker. "
        "Enabling gap propagation would be a semantic change belonging to K19/G16.",
        "",
        "## 5. Verdict",
        "",
        (
            "**K2/G3 meets the experimental criterion: zero unexplained mismatches.**"
            if equivalence["verdict"] == "OK" and engine["verdict"] == "OK"
            else "**K2/G3 remains open: mismatches were detected.**"
        ),
        "",
    ]
    Path("results/summary.md").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    main()
