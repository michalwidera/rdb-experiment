#!/usr/bin/env python3
"""Werdykt badania higienicznego 1bb2d2c — osobny krok, kryterium zamrożone.

Kryterium przepisane z README (predeklaracja), bez zmian:

    r_STRONA(c) = mediana(ALGSTRUCT, strona) / mediana(STRUCT, strona)
    Δ(c)        = r_PO(c) − r_PRZED(c)

CI(c): bootstrap 95 %, 10 000 replikacji, ziarno 20260731, percentyle 2,5/97,5.
Margines równoważności ±0,02.

    BRAK WPŁYWU      — dla KAŻDEJ komórki CI(c) zawiera się w (−0,02; +0,02)
    JEST WPŁYW       — dla choćby jednej CI(c) leży poza marginesem
    NIEROZSTRZYGNIĘTE— CI(c) przecina granicę marginesu

To jest test RÓWNOWAŻNOŚCI, nie test różnicy. Samo „CI zawiera zero" nie
wystarcza i nie jest tu za taki uznawane.
"""

import argparse
import csv
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPLICATIONS = 10_000
SEED = 20260731
MARGIN = 0.02
LOW_PCT, HIGH_PCT = 2.5, 97.5


def ratio(alg: list[float], struct: list[float]) -> float:
    return statistics.median(alg) / statistics.median(struct)


def bootstrap_delta(samples: dict[tuple[str, str], list[float]], rng: random.Random) -> list[float]:
    """Rozkład Δ przy losowaniu ze zwracaniem, osobno w każdej z czterech grup."""
    deltas = []
    for _ in range(REPLICATIONS):
        drawn = {}
        for key, values in samples.items():
            drawn[key] = [values[rng.randrange(len(values))] for _ in values]
        r_before = ratio(drawn[("PRZED", "ALGSTRUCT")], drawn[("PRZED", "STRUCT")])
        r_after = ratio(drawn[("PO", "ALGSTRUCT")], drawn[("PO", "STRUCT")])
        deltas.append(r_after - r_before)
    return sorted(deltas)


def percentile(ordered: list[float], pct: float) -> float:
    index = min(int(len(ordered) * pct / 100.0), len(ordered) - 1)
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", default=str(Path(__file__).resolve().parent / "results" / "runs.csv"))
    parser.add_argument("--metric", default="compute_median_ns")
    args = parser.parse_args()

    grouped: dict[str, dict[tuple[str, str], list[float]]] = defaultdict(lambda: defaultdict(list))
    bad_client = 0
    with open(args.runs, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["client_rc"] not in ("0", "143"):
                bad_client += 1
            grouped[row["cell"]][(row["side"], row["profile"])].append(float(row[args.metric]))

    if not grouped:
        print("BLAD: zero porownanych komorek — to blad, nie zgoda", file=sys.stderr)
        return 1

    print(f"metryka: {args.metric}")
    print(f"komorek porownanych: {len(grouped)}")
    if bad_client:
        print(f"UWAGA: przebiegow z niezerowym kodem klienta: {bad_client}")

    verdicts = []
    for cell in sorted(grouped):
        samples = grouped[cell]
        expected_keys = {("PRZED", "STRUCT"), ("PRZED", "ALGSTRUCT"), ("PO", "STRUCT"), ("PO", "ALGSTRUCT")}
        missing = expected_keys - set(samples)
        if missing:
            print(f"BLAD: {cell} nie ma grup {sorted(missing)}", file=sys.stderr)
            return 1

        counts = {k: len(v) for k, v in samples.items()}
        r_before = ratio(samples[("PRZED", "ALGSTRUCT")], samples[("PRZED", "STRUCT")])
        r_after = ratio(samples[("PO", "ALGSTRUCT")], samples[("PO", "STRUCT")])
        delta = r_after - r_before

        rng = random.Random(SEED)
        ordered = bootstrap_delta(samples, rng)
        ci_low = percentile(ordered, LOW_PCT)
        ci_high = percentile(ordered, HIGH_PCT)

        if -MARGIN < ci_low and ci_high < MARGIN:
            cell_verdict = "BRAK WPLYWU"
        elif ci_low >= MARGIN or ci_high <= -MARGIN:
            cell_verdict = "JEST WPLYW"
        else:
            cell_verdict = "NIEROZSTRZYGNIETE"
        verdicts.append(cell_verdict)

        print(f"\n--- {cell} ---")
        print(f"  przebiegow w grupach: {counts}")
        print(f"  r_PRZED = {r_before:.4f}   r_PO = {r_after:.4f}")
        print(f"  delta   = {delta:+.4f}   CI95 = ({ci_low:+.4f}; {ci_high:+.4f})   margines +/-{MARGIN}")
        print(f"  werdykt komorki: {cell_verdict}")

    if all(v == "BRAK WPLYWU" for v in verdicts):
        final = "BRAK WPLYWU"
    elif any(v == "JEST WPLYW" for v in verdicts):
        final = "JEST WPLYW"
    else:
        final = "NIEROZSTRZYGNIETE"

    print(f"\n=== WERDYKT ({len(verdicts)} komorek): {final} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
