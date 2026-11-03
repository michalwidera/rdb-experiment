#!/usr/bin/env python3
"""Ocena powtorki R593 H9 przy Q=8 wobec kryteriow zapisanych w README.md przed pomiarem.

Nowy skrypt powtorki; liczy wylacznie funkcjami aparatury K26v3 skopiowanymi do
tego katalogu, bez wlasnej statystyki:

  * bramki P6 bez Flinka (`run_gates.py`): corpus_validity, oracle_mutants,
    public_identity, near_miss_controls, no_materialization;
  * redukcja metryki pierwotnej przy Q=8 wobec ablacji minimalnej rodziny
    (`verdict.reduction` na licznikach LOGICAL z P6), porownana z predykcja
    `verdict.PREDECLARED_RDB` w tolerancji `verdict.CURVE_TOLERANCE` i z progiem 40%;
  * cena czasowa: `verdict.paired_bootstrap_ratio` na medianach blokow z P8
    (`reduce_results.timing_rows` wobec blocks.tsv), prog gornej granicy CI 1,05.

Powtorka POTWIERDZA rodzine, gdy wszystkie bramki sa czyste, redukcja jest rowna
predykcji i nie mniejsza niz 40%, a gorna granica CI ceny nie przekracza 1,05.
Kod wyjscia: 0 - wszystkie trzy rodziny potwierdzone; 1 - co najmniej jedna nie;
2 - blad aparatury albo niepelne dane (bez werdyktu).
"""

import argparse
import os
import sys
from fractions import Fraction
from pathlib import Path

import reduce_results
import run_gates
import verdict

HERE = Path(__file__).resolve().parent
Q = verdict.DECISIVE_Q
# Wynik K26v3 przy Q=8 (results_20260814_K26v3/WERDYKT.md, "Wynik progowy";
# tab:h9-primary artykulu): redukcja wobec ablacji, cena i jej 95% CI.
K26V3 = {
    "F9-R2": ("50,000%", "0,9170 [0,9150; 0,9274]"),
    "F9-R1": ("50,000%", "0,9799 [0,9495; 0,9934]"),
    "F9-X": ("58,333%", "0,7399 [0,7207; 0,7437]"),
}
GATES = ["corpus_validity", "oracle_mutants", "public_identity", "near_miss_controls", "no_materialization"]


def pct(value):
    return f"{float(value) * 100:.3f}%".replace(".", ",")


def ratio(value):
    return f"{float(value):.4f}".replace(".", ",")


def run_p6_gates(p6, plans, work):
    gate_family = {family: {} for family in verdict.FAMILIES}

    def record(gate, problems):
        for name, issues in problems.items():
            gate_family[run_gates.FAMILY_TAG[name]][gate] = issues

    def report(line):
        print(line, flush=True)

    print("== bramki P6 (bez Flinka) ==")
    record("corpus_validity", run_gates.gate_corpus_validity(report))
    run_gates.gate_mutants(str(p6), str(work), report)
    record("oracle_mutants", {name: [] for name in run_gates.FAMILIES})
    _, problems = run_gates.gate_public_identity(str(p6), str(HERE / "rql"), report)
    record("public_identity", problems)
    record("near_miss_controls", run_gates.gate_near_miss(str(p6), str(plans), str(HERE / "rql"), report))
    problems = run_gates.gate_no_materialization(str(p6), report)
    structural = run_gates.gate_no_materialization_structure(str(plans), str(HERE / "rql"), report)
    for name in run_gates.FAMILIES:
        problems[name].extend(structural[name])
    record("no_materialization", problems)
    return gate_family


def logical_cell(p6, family, profile):
    plan = f"{reduce_results.FAMILY_FILE[family]}_Q{Q}"
    logical = reduce_results.read_single_match(p6 / profile / plan / "cell.counters",
                                               reduce_results.RDB_LOGICAL, "LOGICAL")
    return {"substrate_bytes": logical[2], "public_appends": logical[3]}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--p6", type=Path, required=True, help="katalog P6 RetractorDB (run_main_rdb.sh)")
    parser.add_argument("--raw", type=Path, required=True, help="katalog z rozpakowanymi rodzinami P8")
    parser.add_argument("--plans", type=Path, default=HERE / "corpus_validation" / "plans")
    parser.add_argument("--work", type=Path, default=Path("/tmp/r593_mutants"))
    parser.add_argument("--out", type=Path, required=True, help="plik raportu markdown")
    args = parser.parse_args()

    try:
        gates = run_p6_gates(args.p6, args.plans, args.work)
        timing = reduce_results.timing_rows(args.raw, HERE / "blocks.tsv")
        blocks = {}
        for row in timing:
            blocks.setdefault((row["family"], row["profile"]), {})[int(row["block"])] = Fraction(
                int(row["compute_median_ns"]))
        rows, confirmed = [], 0
        for family in verdict.FAMILIES:
            ablation = verdict.MINIMAL_ABLATION[family]
            red = verdict.reduction(logical_cell(args.p6, family, "DEFAULT"),
                                    logical_cell(args.p6, family, ablation))
            predicted = verdict.PREDECLARED_RDB[family][Q]
            bytes_ok = abs(red - predicted) <= verdict.CURVE_TOLERANCE and red >= verdict.THRESHOLD_REDUCTION
            default_blocks, ablation_blocks = blocks[(family, "DEFAULT")], blocks[(family, ablation)]
            if len(default_blocks) != verdict.BOOTSTRAP_BLOCKS or set(default_blocks) != set(ablation_blocks):
                raise ValueError(f"{family}: niepelne bloki P8")
            point, low, high = verdict.paired_bootstrap_ratio(default_blocks, ablation_blocks)
            time_ok = high <= verdict.THRESHOLD_TIME_CI_UPPER
            failed = [gate for gate in GATES if gates[family].get(gate)]
            ok = bytes_ok and time_ok and not failed
            confirmed += ok
            rows.append((family, ablation, red, predicted, bytes_ok, point, low, high, time_ok, failed, ok))
    except (OSError, ValueError, KeyError, reduce_results.ReductionError, verdict.Problem) as exc:
        print(f"BLAD: {exc}", file=sys.stderr)
        return 2

    lines = [
        "# R593 H9 - wynik powtorki przy Q=8",
        "",
        f"Silnik `{os.environ.get('R593_ENGINE', 'dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb')}`, "
        "kryteria z README.md (zapisane przed pomiarem).",
        "",
        "| Rodzina | Ablacja | Redukcja @Q=8 (predykcja) | Cena [95% CI] | Bramki | K26v3: redukcja, cena | Powtorka |",
        "|---|---|---:|---|---|---|---|",
    ]
    for family, ablation, red, predicted, bytes_ok, point, low, high, time_ok, failed, ok in rows:
        lines.append(
            f"| {family} | `{ablation}` | {pct(red)} ({pct(predicted)}){'' if bytes_ok else ' NIE'} | "
            f"{ratio(point)} [{ratio(low)}; {ratio(high)}]{'' if time_ok else ' NIE'} | "
            f"{'czyste' if not failed else 'FAIL: ' + ', '.join(failed)} | "
            f"{K26V3[family][0]}, {K26V3[family][1]} | {'POTWIERDZONA' if ok else 'NIEPOTWIERDZONA'} |")
    lines += ["", f"Potwierdzone rodziny: {confirmed}/{len(rows)}.", ""]
    args.out.write_text("\n".join(lines))
    print("\n".join(lines))
    return 0 if confirmed == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
