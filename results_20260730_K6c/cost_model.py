#!/usr/bin/env python3
"""K6b.7 — model kosztu slotu (K20 etap 1). Uruchamiane na nadzorcy.

**Produkt uboczny, nie reguła kampanii.** Reguła wyboru rate'u pozostaje
empiryczna: o tym, który szczebel drabiny wchodzi, rozstrzyga pełne przemiecenie
drabiny, nie predykcja. Ten skrypt niczego nie mierzy i nie uruchamia silnika —
dopasowuje model na danych, które i tak powstały.

Motywacja (`research_plan.md` K20): plan jest statyczny, a harmonogram
deterministyczny, więc praca na slot jest wielkością znaną w czasie kompilacji.
Brakuje wyłącznie stałych maszyny. Kalibracja v1 ustaliła jedną informację —
„żaden szczebel nie przechodzi" — kosztem 96 przebiegów; przy działającym
modelu byłoby to rachunkiem.

    koszt_slotu ~ a * tokeny + b * bajty_trwale_na_slot + c * bajty_pamieciowe_na_slot

Materializacje muszą mieć **własny współczynnik**: `W4_Q32` to ~33 µs na element
okna, czyli koszt siedzi w zapisach przez `storage`, nie w arytmetyce. Model
liczący same tokeny pomyli się o rzędy wielkości — i dokładnie po to `W4` jest
w zbiorze testowym, nie uczącym.

Podział rodzin jest **zamrożony w README v2**, przed dopasowaniem:
dopasowanie na `{W2, W3, W5, W7}`, predykcja na `{W4, W9}`.

Wejście:
- `results/rate.json` — pary (komórka, rate, `p99`) z kalibracji wraz
  z licznikami planu i materializacji z tych samych przebiegów;
- `results/compile_runs.csv` — Tier A, kontrola zgodności liczników planu;
- `ablation/study_*/runs.csv` — Tier B, walidacja na medianach.
"""
import argparse
import csv
import json
import statistics
from pathlib import Path

TRAIN_FAMILIES = ["W2", "W3", "W5", "W7"]
TEST_FAMILIES = ["W4", "W9"]

# Cechy modelu: praca arytmetyczna osobno, praca zapisu osobno, a w pracy zapisu
# ścieżka trwała osobno od pamięciowej.
#
# ODSTĘPSTWO OD DOSŁOWNEGO ZAPISU PREDEKLARACJI, opisane w cost_model.md.
# README v2 mówi `a*tokeny + b*materializacje + c*bajty`. Liczniki, które silnik
# faktycznie udostępnia w jednym przebiegu, mierzą materializację **w bajtach**
# (`MATERIALIZED ... bajty=`), rozdzielnie dla ścieżki trwałej i pamięciowej;
# osobnej liczby materializacji `read_log` nie zachowuje. Trzecim wymiarem jest
# więc podział bajtów na trwałe i pamięciowe, a nie liczba obok bajtów.
#
# To rozróżnienie jest tu istotne, a nie kosmetyczne: przepowiednia z predeklaracji
# mówi, że koszt `W4` siedzi w zapisach przez `storage`, więc współczynnik przy
# bajtach TRWAŁYCH ma zdominować pamięciowe. Model z jedną wspólną liczbą bajtów
# nie umiałby tego rozstrzygnąć.
#
# Pierwsza wersja tego pliku brała jako trzecią cechę `nodes_public +
# nodes_substrates` pod nazwą „materializacje". To była pomyłka: to jest rozmiar
# planu, nie liczba zapisów. Objawiła się UJEMNYM współczynnikiem, czyli
# wielkością fizycznie niemożliwą dla kosztu.
FEATURES = ["tokeny", "bajty_trwale_na_slot", "bajty_pamieciowe_na_slot"]


def solve_least_squares(rows: list[list[float]], targets: list[float]) -> list[float]:
    """Równania normalne dla modelu bez wyrazu wolnego, eliminacja Gaussa.

    Wymiar to 3, więc nie ma powodu wciągać zależności numerycznej dla samego
    rozwiązania układu 3x3. Wyraz wolny jest świadomie pominięty: koszt slotu
    pustego planu jest zerem, a nie stałą maszyny.
    """
    size = len(FEATURES)
    normal = [[sum(row[i] * row[j] for row in rows) for j in range(size)] for i in range(size)]
    right = [sum(row[i] * target for row, target in zip(rows, targets)) for i in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda r: abs(normal[r][column]))
        if abs(normal[pivot][column]) < 1e-12:
            raise SystemExit(f"układ normalny jest osobliwy w kolumnie {column} — za mało zróżnicowanych cech")
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


def features_of(observation: dict[str, object]) -> list[float] | None:
    counters = observation.get("counters")
    if not isinstance(counters, dict) or not counters:
        return None
    slots = float(observation["slots"])
    tokens = float(counters.get("tokens_from", 0)) + float(counters.get("tokens_fields", 0))
    persistent = float(counters.get("mat_bytes", 0)) / slots
    memory = float(counters.get("mat_mem_bytes", 0)) / slots
    return [tokens, persistent, memory]


PLAN_COUNTERS = ["tokens_from", "tokens_fields", "nodes_public", "nodes_substrates"]


def cross_check_tier_a(observations: list[dict[str, object]], path: Path) -> tuple[list[str], int]:
    """Liczniki planu z kalibracji muszą zgadzać się z Tier A dla tego samego przypadku.

    Oba pomiary biorą profil `OFF` i ten sam plan, tyle że przy różnych rate'ach,
    a liczniki planu są od rate'u niezależne. Rozjazd znaczyłby, że model dostaje
    cechy z innego planu niż ten, który mierzy Tier A.

    Reguła zliczania: zwracamy LICZBĘ porównanych przypadków. Zero porównanych
    przypadków jest błędem, nie zgodnością.
    """
    tier_a: dict[str, dict[str, int]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["profile"] != "OFF" or row["case"] in tier_a:
                continue
            tier_a[row["case"]] = {name: int(row[name]) for name in PLAN_COUNTERS}

    problems: list[str] = []
    compared = 0
    for case in sorted({str(o["case"]) for o in observations}):
        expected = tier_a.get(case)
        if expected is None:
            continue
        counters = next(o["features_source"] for o in observations if o["case"] == case)
        compared += 1
        differing = [
            f"{name}: kalibracja={counters.get(name)} TierA={expected[name]}"
            for name in PLAN_COUNTERS
            if counters.get(name) != expected[name]
        ]
        if differing:
            problems.append(f"{case}: " + "; ".join(differing))
    return problems, compared


def load_tier_b(paths: list[Path]) -> dict[str, float]:
    """Mediana `compute_median_ns` na przypadek, po wszystkich profilach.

    Walidacja modelu odbywa się na kosztach, nie na różnicach między profilami —
    model przewiduje koszt slotu planu, a nie efekt optymalizacji.
    """
    values: dict[str, list[float]] = {}
    for path in paths:
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                values.setdefault(row["case"], []).append(float(row["compute_median_ns"]))
    return {case: statistics.median(series) for case, series in values.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate-json", type=Path, required=True)
    parser.add_argument("--compile-runs", type=Path)
    parser.add_argument("--runs", type=Path, nargs="*", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    rate = json.loads(args.rate_json.resolve().read_text(encoding="utf-8"))
    observations = rate.get("observations", [])
    if not observations:
        raise SystemExit("BLAD: rate.json nie zawiera obserwacji kalibracyjnych")

    usable: list[dict[str, object]] = []
    skipped = 0
    for observation in observations:
        vector = features_of(observation)
        if vector is None:
            skipped += 1
            continue
        usable.append({**observation, "features": vector, "features_source": observation["counters"]})
    if not usable:
        raise SystemExit("BLAD: żadna obserwacja kalibracyjna nie ma liczników — nie ma z czego dopasować modelu")

    plan_problems: list[str] = []
    plan_compared = 0
    if args.compile_runs and args.compile_runs.is_file():
        plan_problems, plan_compared = cross_check_tier_a(usable, args.compile_runs.resolve())
        if plan_compared == 0:
            plan_problems.append("zero porównanych przypadków — kontrola liczników planu nic nie sprawdziła")

    train = [o for o in usable if o["family"] in TRAIN_FAMILIES]
    test = [o for o in usable if o["family"] in TEST_FAMILIES]
    # Reguła zliczania: zero rzeczy dopasowanych nie jest dopasowaniem.
    if len(train) < len(FEATURES):
        raise SystemExit(f"BLAD: {len(train)} obserwacji uczących na {len(FEATURES)} współczynników")

    coefficients = solve_least_squares(
        [list(o["features"]) for o in train], [float(o["p99_ns"]) for o in train]
    )

    def predict(observation: dict[str, object]) -> float:
        return sum(c * f for c, f in zip(coefficients, observation["features"]))

    def rows_for(group: list[dict[str, object]]) -> list[dict[str, object]]:
        records = []
        for observation in sorted(group, key=lambda o: (str(o["case"]), int(o["scale"]))):
            predicted = predict(observation)
            measured = float(observation["p99_ns"])
            records.append(
                {
                    "case": observation["case"],
                    "family": observation["family"],
                    "scale": observation["scale"],
                    "predicted_ns": predicted,
                    "measured_ns": measured,
                    "relative_error": (predicted - measured) / measured if measured else None,
                }
            )
        return records

    train_rows = rows_for(train)
    test_rows = rows_for(test)

    tier_b = load_tier_b([p.resolve() for p in args.runs])
    validation: list[dict[str, object]] = []
    by_case: dict[str, dict[str, object]] = {}
    for observation in usable:
        case = str(observation["case"])
        if case not in by_case or int(observation["scale"]) < int(by_case[case]["scale"]):
            by_case[case] = observation
    for case, median_ns in sorted(tier_b.items()):
        observation = by_case.get(case)
        if observation is None:
            continue
        predicted = predict(observation)
        validation.append(
            {
                "case": case,
                "predicted_ns": predicted,
                "tier_b_median_ns": median_ns,
                "relative_error": (predicted - median_ns) / median_ns if median_ns else None,
            }
        )

    def mean_absolute_error(records: list[dict[str, object]]) -> float:
        errors = [abs(float(r["relative_error"])) for r in records if r["relative_error"] is not None]
        return sum(errors) / len(errors) if errors else float("nan")

    report = {
        "features": FEATURES,
        "coefficients": dict(zip(FEATURES, coefficients)),
        "train_families": TRAIN_FAMILIES,
        "test_families": TEST_FAMILIES,
        "train_points": len(train_rows),
        "test_points": len(test_rows),
        "skipped_observations": skipped,
        "plan_counters_compared": plan_compared,
        "plan_counters_problems": plan_problems,
        "train": train_rows,
        "test": test_rows,
        "validation_tier_b": validation,
        "mae_train": mean_absolute_error(train_rows),
        "mae_test": mean_absolute_error(test_rows),
        "mae_validation": mean_absolute_error(validation),
    }
    (output / "cost_model.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    def table(records: list[dict[str, object]]) -> list[str]:
        lines = [
            "| Przypadek | `s` | przewidziane | zmierzone | błąd względny |",
            "|---|---:|---:|---:|---:|",
        ]
        for record in records:
            error = record["relative_error"]
            lines.append(
                f"| `{record['case']}` | {record['scale']} | {float(record['predicted_ns']) / 1000:.2f} µs | "
                f"{float(record['measured_ns']) / 1000:.2f} µs | "
                + (f"{float(error) * 100:+.1f}%" if error is not None else "—")
                + " |"
            )
        return lines

    lines = [
        "# K6b — model kosztu slotu (K20 etap 1)",
        "",
        "**To jest produkt uboczny, nie reguła kampanii.** Rate został wybrany empirycznie,",
        "przez pełne przemiecenie drabiny. Model dopasowano **po** kalibracji, na danych,",
        "które i tak powstały: zero dodatkowych przebiegów pomiarowych, zero zmian w silniku.",
        "",
        "- postać: `koszt_slotu ~ " + " + ".join(f"{chr(97 + i)}·{name}" for i, name in enumerate(FEATURES)) + "`",
        f"- dopasowanie na rodzinach: {', '.join(TRAIN_FAMILIES)} ({len(train_rows)} punktów)",
        f"- predykcja na rodzinach: {', '.join(TEST_FAMILIES)} ({len(test_rows)} punktów)",
        f"- obserwacji bez liczników (pominięte): {skipped}",
        f"- kontrola liczników planu wobec Tier A: {plan_compared} przypadków, "
        f"{len(plan_problems)} niezgodności"
        + ("" if not plan_problems else " — " + "; ".join(plan_problems)),
        "",
        "Podział rodzin był zamrożony w predeklaracji **przed** dopasowaniem. `W4` jest",
        "w zbiorze testowym celowo: to ona łamie model liczący same tokeny.",
        "",
        "**Odstępstwo od dosłownego zapisu predeklaracji.** README v2 mówi",
        "`a·tokeny + b·materializacje + c·bajty`. Liczniki, które silnik udostępnia",
        "w jednym przebiegu, mierzą materializację **w bajtach** (`MATERIALIZED ... bajty=`),",
        "rozdzielnie dla ścieżki trwałej i pamięciowej; osobnej liczby materializacji",
        "instrument nie zachowuje. Trzecim wymiarem jest więc podział bajtów na trwałe",
        "i pamięciowe, a nie liczba obok bajtów. Wymóg predeklaracji — żeby praca zapisu",
        "miała własny współczynnik, niezależny od tokenów — jest spełniony, i to",
        "mocniej: ścieżka trwała i pamięciowa mają współczynniki osobne, więc",
        "przepowiednia „koszt `W4` siedzi w zapisach przez `storage`" + '"' + " jest sprawdzalna",
        "wprost na znaku i wielkości `b` względem `c`.",
        "",
        "## Współczynniki",
        "",
        "| Cecha | Współczynnik |",
        "|---|---:|",
    ]
    for name, value in zip(FEATURES, coefficients):
        lines.append(f"| `{name}` | {value:.6g} ns |")

    # Koszt nie bywa ujemny. Ujemny wspolczynnik znaczy, ze cechy sa wspolliniowe
    # i dopasowanie kompensuje jedna druga -- model moze wtedy dobrze pasowac na
    # rodzinach uczacych i nie znaczyc nic poza nimi. To ma byc napisane wprost,
    # a nie zostawione czytelnikowi do wypatrzenia w tabeli.
    negative = [name for name, value in zip(FEATURES, coefficients) if value < 0]
    if negative:
        lines += [
            "",
            f"**Ostrzeżenie: współczynnik ujemny przy {', '.join(f'`{n}`' for n in negative)}.** "
            "Koszt nie bywa ujemny, więc to nie jest wielkość fizyczna, tylko objaw "
            "współliniowości cech: dopasowanie kompensuje jedną cechę drugą. Model może przez to "
            "pasować na rodzinach uczących i nie znaczyć nic poza nimi. Liczby niżej należy czytać "
            "z tym zastrzeżeniem.",
        ]

    lines += [
        "",
        "## Dopasowanie (rodziny uczące)",
        "",
        *table(train_rows),
        "",
        f"Średni bezwzględny błąd względny: **{report['mae_train'] * 100:.1f}%**.",
        "",
        "## Predykcja (rodziny testowe, niewidziane przy dopasowaniu)",
        "",
        *table(test_rows),
        "",
        f"Średni bezwzględny błąd względny: **{report['mae_test'] * 100:.1f}%**.",
        "",
        "## Walidacja na medianach Tier B",
        "",
    ]
    if validation:
        lines += [
            "Przewidywanie dotyczy `p99` z kalibracji, a porównanie — mediany Tier B, więc",
            "systematyczne przeszacowanie jest oczekiwane. Interesuje nas rząd wielkości",
            "i to, czy błąd nie eksploduje na rodzinie zdominowanej przez materializacje.",
            "",
            "| Przypadek | przewidziane | mediana Tier B | błąd względny |",
            "|---|---:|---:|---:|",
        ]
        for record in validation:
            error = record["relative_error"]
            lines.append(
                f"| `{record['case']}` | {float(record['predicted_ns']) / 1000:.2f} µs | "
                f"{float(record['tier_b_median_ns']) / 1000:.2f} µs | "
                + (f"{float(error) * 100:+.1f}%" if error is not None else "—")
                + " |"
            )
        lines += ["", f"Średni bezwzględny błąd względny: **{report['mae_validation'] * 100:.1f}%**."]
    else:
        lines.append("Brak danych Tier B — walidacja nie została wykonana.")

    lines += [
        "",
        "## Sprawdzalna przepowiednia",
        "",
        "Zapisana **przed** dopasowaniem: `W4_Q32` na `SUBSTRAT memory` powinna być",
        "radykalnie tańsza, bo jej koszt siedzi w zapisach przez `storage`, nie",
        "w arytmetyce. Sprawdzenie tej przepowiedni nie należy do K6b.",
        "",
        "Etap drugi K20 — kontrola dopuszczenia planu wewnątrz `xretractor` — jest zmianą",
        "w silniku i nie należy do tej kampanii.",
    ]

    (output / "cost_model.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"model kosztu slotu: {len(train_rows)} punktów uczących, {len(test_rows)} testowych, "
        f"MAE_test={report['mae_test'] * 100:.1f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
