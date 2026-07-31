#!/usr/bin/env python3
"""Model kosztu slotu z rodzina okienna w zbiorze uczacym (K20 etap 1c).

Cel: `p99_ns` slotu z kampanii K6c. Cechy: liczniki planu z K6c oraz praca na
slot z sondy E4 (`work.json`, zebrane w results_20260731_instrument).

Podzial rodzin ZAMROZONY w README tego katalogu i ROZNY od etapu 1: uczenie
{W2, W3, W5, W7, W8}, predykcja {W4, W9}. Powod zmiany: tylko W4 i W8 uzywaja
operatorow okna, a podzial etapu 1 trzymal obie poza zbiorem uczacym, przez co
kolumna `agse_elements` byla tam tozsamosciowo zerowa i uklad wychodzil
osobliwy (wynik E4).

ODNIESIENIEM OCENY jest wariant `v1` na TYM SAMYM podziale, a nie liczba 258,3%
z etapu 1 -- tamta pochodzi z innego zbioru uczacego, wiec porownanie do niej
mieszaloby dwie zmiany naraz i przypisywaloby cesze zasluge za dodanie W8.

Wszystkie cztery warianty cech sa liczone i raportowane RAZEM. Nie wolno wybrac
wariantu po zobaczeniu wyniku -- oceniany jest `v2`.

Wyraz wolny swiadomie pominiety: koszt slotu pustego planu to zero, a nie stala
maszyny (ta sama decyzja co w etapie 1).
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.dont_write_bytecode = True

TRAIN_FAMILIES = {"W2", "W3", "W5", "W7", "W8"}
TEST_FAMILIES = {"W4", "W9"}

# Zamrozone w predeklaracji (README, sekcja "Model i podzial").
VARIANTS: dict[str, list[str]] = {
    "v1": ["tokeny", "bajty_trwale", "bajty_pamieciowe"],
    "v2": ["tokeny", "bajty_trwale", "bajty_pamieciowe", "agse_elements"],
    "v3": ["agse_elements", "agse_reads", "eval_tokens"],
    "v4": ["agse_elements", "agse_reads", "eval_tokens", "bajty_trwale"],
}
# Kontekst historyczny, NIE punkt odniesienia oceny: etap 1 liczyl na INNYM
# zbiorze uczacym (bez W8), wiec porownanie do tej liczby mieszaloby dwie zmiany.
HISTORICAL_MAE_TEST = 258.3  # results_20260730_K6c/results/cost_model.md
SUCCESS_MAE_TEST = 50.0  # prog zamrozony w predeklaracji
OVERFIT_RATIO = 2.0  # MAE_train nie gorszy niz 2x MAE_test


def solve_least_squares(rows: list[list[float]], targets: list[float]) -> list[float] | None:
    """Rownania normalne bez wyrazu wolnego, eliminacja Gaussa z wyborem elementu glownego."""
    size = len(rows[0])
    normal = [[sum(r[i] * r[j] for r in rows) for j in range(size)] for i in range(size)]
    right = [sum(r[i] * t for r, t in zip(rows, targets)) for i in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda r: abs(normal[r][column]))
        if abs(normal[pivot][column]) < 1e-12:
            return None
        normal[column], normal[pivot] = normal[pivot], normal[column]
        right[column], right[pivot] = right[pivot], right[column]
        for row in range(column + 1, size):
            factor = normal[row][column] / normal[column][column]
            for col in range(column, size):
                normal[row][col] -= factor * normal[column][col]
            right[row] -= factor * right[column]
    solution = [0.0] * size
    for row in reversed(range(size)):
        total = right[row] - sum(normal[row][col] * solution[col] for col in range(row + 1, size))
        solution[row] = total / normal[row][row]
    return solution


def mean_abs_relative_error(coefficients: list[float], features: list[str], group: list[dict]) -> float:
    errors = []
    for observation in group:
        predicted = sum(c * observation[f] for c, f in zip(coefficients, features))
        errors.append(abs(predicted - observation["y"]) / observation["y"])
    return 100.0 * statistics.fmean(errors)


def build_observations(rate_json: dict, work_json: dict) -> list[dict]:
    """Laczy cel z K6c z cechami E4 po kluczu (case, scale).

    Regula zliczania: zwracamy LICZBE polaczonych obserwacji, a brak pary jest
    bledem, nie cichym pominieciem. Cel bez cech oznaczalby, ze model uczy sie
    na innym zbiorze niz zadeklarowany.
    """
    work_by_key = {(str(r["case"]), int(r["scale"])): r for r in work_json["records"]}
    observations: list[dict] = []
    missing: list[str] = []
    for entry in rate_json["observations"]:
        counters = entry.get("counters")
        if not counters:
            continue
        key = (str(entry["case"]), int(entry["scale"]))
        work = work_by_key.get(key)
        if work is None:
            missing.append(f"{key[0]}@s{key[1]}")
            continue
        slots = float(entry["slots"])
        observations.append(
            {
                "case": str(entry["case"]),
                "family": str(entry["family"]),
                "scale": int(entry["scale"]),
                "y": float(entry["p99_ns"]),
                "tokeny": float(counters.get("tokens_from", 0)) + float(counters.get("tokens_fields", 0)),
                "bajty_trwale": float(counters.get("mat_bytes", 0)) / slots,
                "bajty_pamieciowe": float(counters.get("mat_mem_bytes", 0)) / slots,
                "agse_elements": float(work["agse_elements"]),
                "agse_reads": float(work["agse_reads"]),
                "eval_tokens": float(work["eval_tokens"]),
            }
        )
    if missing:
        raise SystemExit(f"BLAD: {len(missing)} celow bez cech E4: {', '.join(missing[:8])}")
    return observations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate-json", type=Path, required=True, help="rate.json z K6c (cele p99)")
    parser.add_argument("--work-json", type=Path, required=True, help="work.json z collect_work.py (cechy E4)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rate_json = json.loads(args.rate_json.read_text(encoding="utf-8"))
    work_json = json.loads(args.work_json.read_text(encoding="utf-8"))
    observations = build_observations(rate_json, work_json)

    train = [o for o in observations if o["family"] in TRAIN_FAMILIES]
    test = [o for o in observations if o["family"] in TEST_FAMILIES]
    if not train or not test:
        raise SystemExit(f"BLAD: zbior uczacy={len(train)}, testowy={len(test)} -- zero nie jest dopasowaniem")

    results: list[dict] = []
    for name, features in VARIANTS.items():
        if len(train) < len(features):
            raise SystemExit(f"BLAD: {len(train)} obserwacji uczacych na {len(features)} wspolczynnikow ({name})")
        coefficients = solve_least_squares([[o[f] for f in features] for o in train], [o["y"] for o in train])
        if coefficients is None:
            results.append({"variant": name, "features": features, "singular": True})
            continue
        results.append(
            {
                "variant": name,
                "features": features,
                "singular": False,
                "coefficients": dict(zip(features, coefficients)),
                "mae_train": mean_abs_relative_error(coefficients, features, train),
                "mae_test": mean_abs_relative_error(coefficients, features, test),
                "negative": [f for c, f in zip(coefficients, features) if c < 0],
            }
        )

    graded = next(r for r in results if r["variant"] == "v2")
    baseline = next(r for r in results if r["variant"] == "v1")
    if graded.get("singular") or baseline.get("singular"):
        verdict = "UKLAD OSOBLIWY dla wariantu ocenianego albo odniesienia -- brak werdyktu"
        passed = False
        beats_baseline = None
    else:
        # Warunek 3 z predeklaracji: cecha musi wygrac z odniesieniem NA TYM SAMYM
        # podziale. Bez tego poprawa moglaby pochodzic z dodania W8 do uczenia,
        # a nie z nowej cechy -- i przypisalibysmy zasluge nie tej zmianie.
        beats_baseline = graded["mae_test"] < baseline["mae_test"]
        passed = (
            graded["mae_test"] <= SUCCESS_MAE_TEST
            and graded["mae_train"] <= OVERFIT_RATIO * graded["mae_test"]
            and beats_baseline
        )
        if passed:
            verdict = "SUKCES wg kryterium zamrozonego"
        elif not beats_baseline:
            verdict = "CECHA NIC NIE WNOSI -- v2 nie jest lepszy od v1 na tym samym podziale"
        elif graded["mae_test"] < baseline["mae_test"]:
            verdict = "POPRAWA BEZ PRZYDATNOSCI -- blad spadl ponizej odniesienia, ale prog 50% nie zostal osiagniety"
        else:
            verdict = "POGORSZENIE wzgledem odniesienia"

    lines = [
        "# K20 etap 1c — model kosztu slotu z rodzina okienna w zbiorze uczacym",
        "",
        f"- obserwacji: {len(observations)} (uczace {len(train)}, testowe {len(test)})",
        f"- podzial ZAMROZONY: dopasowanie {sorted(TRAIN_FAMILIES)}, predykcja {sorted(TEST_FAMILIES)}",
        "- odniesienie oceny: wariant `v1` NA TYM SAMYM podziale (nie liczba z etapu 1)",
        f"- kontekst historyczny (etap 1, inny zbior uczacy): MAE_test = {HISTORICAL_MAE_TEST}%",
        f"- prog sukcesu zamrozony w predeklaracji: MAE_test <= {SUCCESS_MAE_TEST}%,"
        f" MAE_train <= {OVERFIT_RATIO}x MAE_test",
        "",
        "## Warianty cech — wszystkie policzone, zaden nie wybrany po fakcie",
        "",
        "| wariant | cechy | MAE_train | MAE_test | wspolczynniki ujemne |",
        "|---|---|---:|---:|---|",
    ]
    for record in results:
        if record.get("singular"):
            lines.append(f"| `{record['variant']}` | {', '.join(record['features'])} | — | — | UKLAD OSOBLIWY |")
            continue
        negative = ", ".join(f"`{n}`" for n in record["negative"]) if record["negative"] else "—"
        lines.append(
            f"| `{record['variant']}` | {', '.join(record['features'])} | "
            f"{record['mae_train']:.1f}% | {record['mae_test']:.1f}% | {negative} |"
        )

    lines += ["", "## Werdykt", "", f"**{verdict}**", ""]
    if not graded.get("singular"):
        lines += [
            f"Wariant oceniany `v2` (odniesienie + `agse_elements`): MAE_train {graded['mae_train']:.1f}%, "
            f"MAE_test {graded['mae_test']:.1f}%.",
            "",
            f"Odniesienie `v1` na TYM SAMYM podziale: MAE_train {baseline['mae_train']:.1f}%, "
            f"MAE_test {baseline['mae_test']:.1f}%.",
            "",
            f"Wklad samej cechy `agse_elements`: {baseline['mae_test']:.1f}% -> {graded['mae_test']:.1f}% "
            f"({'poprawa' if beats_baseline else 'brak poprawy'}).",
            "",
            f"Kontekst historyczny (etap 1, bez W8 w uczeniu): MAE_test = {HISTORICAL_MAE_TEST}%. "
            "Ta liczba NIE jest punktem odniesienia oceny -- pochodzi z innego podzialu.",
        ]
        if graded["negative"]:
            lines += [
                "",
                "**Ostrzezenie: wspolczynnik ujemny przy "
                + ", ".join(f"`{n}`" for n in graded["negative"])
                + ".** Koszt nie bywa ujemny, wiec to objaw wspolliniowosci cech, a nie wielkosc"
                " fizyczna. Liczby nalezy czytac z tym zastrzezeniem.",
            ]

    lines += [
        "",
        "## Zagrozenie trafnosci — jawne",
        "",
        "Cechy pochodza z buildu instrumentowanego (`issue_219-instrument`), a cele `p99`"
        " z kampanii K6c na `1bb2d2c`. Zestawienie jest uprawnione tylko przy przechodzacym"
        " badaniu higienicznym i pozostaje slabsze niz pomiar z jednego drzewa kodu."
        " Decyzja o tym odstepstwie: czlowiek, 2026-07-31 (README, sekcja Odstepstwo).",
    ]

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "cost_model_v2.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (args.output / "cost_model_v2.json").write_text(
        json.dumps(
            {
                "train_families": sorted(TRAIN_FAMILIES),
                "test_families": sorted(TEST_FAMILIES),
                "historical_mae_test": HISTORICAL_MAE_TEST,
                "baseline_mae_test": None if baseline.get("singular") else baseline["mae_test"],
                "beats_baseline": beats_baseline,
                "success_mae_test": SUCCESS_MAE_TEST,
                "observations": len(observations),
                "variants": results,
                "graded_variant": "v2",
                "passed": passed,
                "verdict": verdict,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"model v2: {len(observations)} obserwacji, werdykt: {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
