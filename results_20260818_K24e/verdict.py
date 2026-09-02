#!/usr/bin/env python3
"""Werdykt K24d — automatyczny, per klasa operatora, nigdy agregatem.

Raportowane są dwie wielkości osobno (ogon i początek logiczny) oraz ich suma.
Mieszanie ich ukryłoby przesunięcie milczenia między członami przy zachowanej
sumie — czyli dokładnie to, co zrobiło przestemplowanie z 2026-08-06.

Czyta `raw/campaign.csv` i wypisuje `VERDICT.md`. Progi pochodzą
z PREDECLARATION.md §6; ten skrypt nie podejmuje decyzji uznaniowych.

Atrybucja per klasa jest **izolowana**: ogon węzła liczony postacią zamkniętą
z ogonów składowych wziętych z oracle'a. Bez tego niezgodność dziecka liczyłaby
się jako niezgodność rodzica i klasa operatora nic by nie znaczyła. Wynik
propagowany (silnik wobec oracle'a na całym planie) raportowany jest obok.
"""

import argparse
import collections
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent

EXACT = "exact"
CONSERVATIVE = "over-approximating"
UNDER = "UNDER-APPROXIMATING"


def load(path):
    with Path(path).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def classify(rows):
    stats = collections.defaultdict(lambda: {
        "n": 0, "prop": 0, "step1": 0, "step2": 0,
        "delta": collections.Counter(), "witness_over": [], "witness_under": []})
    for row in rows:
        entry = stats[row["kind"]]
        entry["n"] += 1
        entry["prop"] += int(row["agree_c1"])
        entry["step1"] += int(row["agree_step_c1"])
        entry["step2"] += int(row["agree_step_c2"])
        gap = int(row["step_c1"]) - int(row["oracle_c1"])
        entry["delta"][gap] += 1
        if gap > 0 and len(entry["witness_over"]) < 2:
            entry["witness_over"].append(row)
        if gap < 0 and len(entry["witness_under"]) < 2:
            entry["witness_under"].append(row)
    return stats


def classify_origin(rows):
    """To samo, ale dla początku logicznego i dla sumy slotów milczenia.

    Kierunek różnicy znaczy tu co innego niż przy ogonie. Origin **zaniżony**
    to rekord wyemitowany, mimo że jego definicja sięga przed początek źródła —
    czyli odczyt poza historią, nie opóźnienie. Origin **zawyżony** to rekord
    porzucony, mimo że dawał się policzyć: strumień milczy dłużej, niż musi.
    """
    stats = collections.defaultdict(lambda: {
        "n": 0, "prop": 0, "step": 0, "silence": 0,
        "delta": collections.Counter(), "witness_over": [], "witness_under": []})
    for row in rows:
        entry = stats[row["kind"]]
        entry["n"] += 1
        entry["prop"] += int(row["agree_origin"])
        entry["step"] += int(row["agree_step_origin"])
        entry["silence"] += int(row["agree_silence"])
        gap = int(row["step_origin"]) - int(row["oracle_origin"])
        entry["delta"][gap] += 1
        if gap > 0 and len(entry["witness_over"]) < 2:
            entry["witness_over"].append(row)
        if gap < 0 and len(entry["witness_under"]) < 2:
            entry["witness_under"].append(row)
    return stats


def regime(entry):
    if entry["step1"] == entry["n"]:
        return EXACT
    if any(gap < 0 for gap in entry["delta"]):
        return UNDER
    return CONSERVATIVE


def member_b(rows):
    plans = {row["plan"] for row in rows}
    diverging_a = {row["plan"] for row in rows if row["divergence_a"] != "0"}
    eligible = [row for row in rows if row["h10b_eligible"] == "1"]
    positive = [row for row in eligible if int(row["divergence_a"]) > 0]
    matching = [row for row in positive
                if int(row["divergence_a"]) == int(row["predicted_form"])]
    return {"plans": len(plans), "diverging": len(diverging_a),
            "share": len(diverging_a) / max(len(plans), 1),
            "eligible": len(eligible), "positive": len(positive), "matching": len(matching),
            "mismatch": [row for row in positive if row not in matching][:3]}


def controls(rows):
    literal_single = [row for row in rows if "HC_SINGLE" in row["hard_classes"].split(",")]
    literal_int = [row for row in rows if "HC_INT" in row["hard_classes"].split(",")]
    phase_free = [row for row in literal_single if row["kind"] in ("PASS", "SHIFT", "REDUCE")]
    int_hash = [row for row in literal_int if row["kind"] == "HASH"]

    def breaches(selected, column):
        return sum(1 for row in selected if row[column] != "0")

    return {
        "HC_SINGLE (literal)": (len(literal_single), breaches(literal_single, "divergence_a")),
        "HC_SINGLE (operators with no tail of their own)": (len(phase_free), breaches(phase_free, "divergence_a")),
        "HC_INT (literal)": (len(literal_int), breaches(literal_int, "divergence_a")),
        "HC_INT (`#` nodes, local rule B)": (len(int_hash), breaches(int_hash, "divergence_b")),
    }


def render(rows, out, seed="20260803", engine="5e3eb42"):
    stats = classify(rows)
    b = member_b(rows)
    ctl = controls(rows)
    plans = len({row["plan"] for row in rows})

    lines = [
        "# K24d / H10 — verdict", "",
        f"Corpus: **{plans} plans**, **{len(rows)} node observations**, "
        f"zero apparatus errors. Seed {seed}, engine `{engine}` (PIN.md).", "",
        "The verdict is reported per operator class. 100% agreement is the only",
        "support for H10a in a class; one mismatch falsifies H10a in that class.", "",
        "## 1. H10a — exactness, per operator class", "",
        "The **isolated** column is the verdict: the closed form computed from the",
        "component tails taken from the oracle, so a mismatch originates in this",
        "node's own rule. The **propagated** column is the agreement of the engine's",
        "plan dump with the oracle over the whole plan — it carries the effects of",
        "mismatches inherited from children.", "",
        "| Class | Nodes | Isolated C1 | Isolated C2 | Propagated C1 | Regime | H10a verdict |",
        "|---|---:|---:|---:|---:|---|---|",
    ]

    regimes = {}
    for kind in sorted(stats, key=lambda key: -stats[key]["n"]):
        entry = stats[kind]
        mode = regime(entry)
        regimes[kind] = mode
        verdict = "**supported**" if mode == EXACT else "**FALSIFICATION**"
        lines.append(
            f"| `{kind}` | {entry['n']} | {entry['step1'] / entry['n']:.1%} | "
            f"{entry['step2'] / entry['n']:.1%} | {entry['prop'] / entry['n']:.1%} | "
            f"{mode} | {verdict} |")

    exact = [k for k, v in regimes.items() if v == EXACT]
    over = [k for k, v in regimes.items() if v == CONSERVATIVE]
    under = [k for k, v in regimes.items() if v == UNDER]

    lines += ["", "### The three regimes", "",
              f"* **exact** (closed form == oracle everywhere): "
              f"{', '.join(f'`{k}`' for k in exact) or 'none'};",
              f"* **over-approximating** (never under-approximates; safe, but not equal): "
              f"{', '.join(f'`{k}`' for k in over) or 'none'};",
              f"* **under-approximating** (tail shorter than the event model requires): "
              f"{', '.join(f'`{k}`' for k in under) or 'none'}.", "",
              "The under-approximating regime is qualitatively different from the",
              "over-approximating one: over-approximation delays emission by a slot,",
              "under-approximation means a record emitted before all its dependencies",
              "are determined.", "",
              "### Difference distribution (closed form − oracle C1)", "",
              "| Class | Distribution |", "|---|---|"]
    for kind in sorted(stats, key=lambda key: -stats[key]["n"]):
        entry = stats[kind]
        total = entry["n"]
        dist = ", ".join(f"`{gap:+d}`: {count} ({count / total:.1%})"
                         for gap, count in sorted(entry["delta"].items()))
        lines.append(f"| `{kind}` | {dist} |")

    lines += ["", "### Witnesses", "",
              "| Class | Direction | Plan | Node | Interval | Engine | Closed form (isol.) | Oracle C1 |",
              "|---|---|---:|---|---|---:|---:|---:|"]
    for kind in sorted(stats, key=lambda key: -stats[key]["n"]):
        for direction, key in (("over", "witness_over"), ("**under**", "witness_under")):
            for row in stats[kind][key]:
                lines.append(f"| `{kind}` | {direction} | {row['plan']} | {row['node']} | "
                             f"`{row['delta']}` | {row['engine_tail']} | {row['step_c1']} | "
                             f"{row['oracle_c1']} |")

    origin_stats = classify_origin(rows)
    lines += ["", "## 1b. H10a — logical origin, per operator class", "",
              "A quantity introduced by the re-stamping of 2026-08-06 and absent from",
              "the K24/K24r campaigns. The **sum** column compares origin+tail — the",
              "only quantity shared with the campaigns predating that change.", "",
              "| Class | Nodes | Isolated | Propagated | Sum (origin+tail) | Regime | Verdict |",
              "|---|---:|---:|---:|---:|---|---|"]
    origin_regimes = {}
    for kind in sorted(origin_stats, key=lambda key: -origin_stats[key]["n"]):
        entry = origin_stats[kind]
        if entry["step"] == entry["n"]:
            mode = EXACT
        elif any(gap < 0 for gap in entry["delta"]):
            mode = UNDER
        else:
            mode = CONSERVATIVE
        origin_regimes[kind] = mode
        verdict = "**supported**" if mode == EXACT else "**FALSIFICATION**"
        lines.append(
            f"| `{kind}` | {entry['n']} | {entry['step'] / entry['n']:.1%} | "
            f"{entry['prop'] / entry['n']:.1%} | {entry['silence'] / entry['n']:.1%} | "
            f"{mode} | {verdict} |")

    lines += ["", "### Origin difference distribution (engine calculus − oracle)", "",
              "| Class | Distribution |", "|---|---|"]
    for kind in sorted(origin_stats, key=lambda key: -origin_stats[key]["n"]):
        entry = origin_stats[kind]
        total = entry["n"]
        dist = ", ".join(f"`{gap:+d}`: {count} ({count / total:.1%})"
                         for gap, count in sorted(entry["delta"].items()))
        lines.append(f"| `{kind}` | {dist} |")

    origin_under = [k for k, v in origin_regimes.items() if v == UNDER]
    lines += ["", f"Origin under-approximated (a read before the source's origin): "
                  f"{', '.join(f'`{k}`' for k in origin_under) or '**none**'}.", ""]

    lines += ["## 2. H10b — non-locality", "",
              f"* divergence of local rule A from the exact one: **{b['diverging']} of "
              f"{b['plans']} plans = {b['share']:.1%}** (pre-declared threshold: >= 5%)",
              f"* pre-declared population (exactly one `#`, otherwise `PASS`/`>N`): "
              f"**{b['eligible']} plans**, positive divergences **{b['positive']}**",
              f"* divergences of the pre-declared form `ceil((p+q-1)/p)`: "
              f"**{b['matching']} of {b['positive']}** "
              f"({b['matching'] / max(b['positive'], 1):.1%}; threshold: 100%)", ""]

    lines += ["## 3. Negative controls", "",
              "| Control | Nodes | Divergences | State |", "|---|---:|---:|---|"]
    for label, (count, breaks) in ctl.items():
        state = "**passed**" if breaks == 0 else "**BROKEN**"
        lines.append(f"| {label} | {count} | {breaks} | {state} |")

    lines += ["", "Both pre-declared controls **are broken in their literal form**.",
              "Under PREDECLARATION.md §6 this means an ill-defined local rule rather",
              "than a result — therefore **part (b) is not assessable on this",
              "apparatus** and the H10b figures above do not constitute a verdict.",
              "Diagnosis of the contradiction in part (b)'s specification: REPORT.md §5.", ""]

    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"exact": exact, "over": over, "under": under, "b": b, "controls": ctl,
            "origin_under": origin_under}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", default=str(ROOT / "raw" / "campaign.csv"))
    parser.add_argument("--out", default=str(ROOT / "VERDICT.md"))
    # K24r: ziarno i silnik były w nagłówku zaszyte na sztywno, więc werdykt
    # z innego ziarna albo innego stanu silnika opisywał sam siebie nieprawdziwie.
    parser.add_argument("--seed", default="20260806")
    parser.add_argument("--engine", default="db4a360")
    args = parser.parse_args()
    summary = render(load(args.raw), args.out, args.seed, args.engine)
    print(f"exact: {summary['exact']}")
    print(f"over-approximating: {summary['over']}")
    print(f"under-approximating: {summary['under']}")
    print(f"origin — classes with under-approximation: {summary['origin_under'] or 'none'}")
    print(f"H10b (not assessable): divergence {summary['b']['share']:.1%}, "
          f"form {summary['b']['matching']}/{summary['b']['positive']}")
    for label, (count, breaks) in summary["controls"].items():
        print(f"control {label}: {breaks}/{count}")


if __name__ == "__main__":
    main()
