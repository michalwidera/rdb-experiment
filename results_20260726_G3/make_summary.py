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
        "# K2/G3 — niezależny oracle shift-matching",
        "",
        f"- commit silnika: `{engine['code_commit']}`",
        f"- commit repozytorium eksperymentów przed kampanią: `{engine['experiment_commit']}`",
        f"- wygenerowano: {datetime.now(timezone.utc).isoformat()}",
        f"- wynik oracle'a: **{equivalence['verdict']}**",
        f"- wynik mostu do silnika: **{engine['verdict']}**",
        "",
        "## 1. Kwalifikacja mutacji",
        "",
        "| mutacja/kontrola | wykryta jako różnica | warstwy | werdykt |",
        "|---|---:|---|---|",
    ]
    for name, info in equivalence["mutations"].items():
        out.append(
            f"| `{name}` | {'tak' if info['detected'] else 'nie'} | "
            f"{', '.join(info['layers']) or '—'} | {info['verdict']} |"
        )

    coverage = equivalence["payload_domain"]["coverage"]
    out += [
        "",
        "## 2. Macierz czysto modelowa",
        "",
        "| kampania | przypadków | pozycji | rozbieżności | czas [s] | checksum64 |",
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
        f"Łącznie: **{totals['cases']} przypadków**, **{totals['positions']} pozycji**, "
        f"**{totals['mismatches']} rozbieżności**.",
        "",
        "Jawna kontrola dziedziny rekordów:",
        "",
        f"- bez NULL: {coverage['present']};",
        f"- częściowy NULL: {coverage['partial_null']};",
        f"- all-null: {coverage['all_null']}.",
        "",
        f"Niedopasowane przesunięcia odrzucone: "
        f"**{sum(case['rejected'] for case in equivalence['unmatched_guard']['cases'])}/"
        f"{len(equivalence['unmatched_guard']['cases'])}**.",
        "",
        "## 3. Most oracle — RetractorDB",
        "",
        "| przypadek | min Δ [ms] | ΔA/ΔB | i+k | W | ogon # bieżący/bezpieczny | "
        "rekordy opt/blocked/rhs | błędy blocked | wynik |",
        "|---|---:|---|---:|---:|---|---|---:|---|",
    ]
    for case in engine["cases"]:
        records = "/".join(str(case["outputs"][name]["records"]) for name in ("optimized", "blocked", "explicit_rhs"))
        out.append(
            f"| {case['case']} | {case['min_interval_ms']} | {case['ratio']} | {case['combined']} | "
            f"{case['expected_tail']} | {case['current_hash_tail']}/{case['phase_safe_hash_tail']} | "
            f"{records} | {case['outputs']['blocked']['mismatch_count']} | {case['status']} |"
        )

    out += [
        "",
        "Każdy przypadek wykonuje trzy postacie planu: LHS przepisaną przez R1, "
        "LHS zablokowaną przez publiczne strumienie przesunięcia oraz jawną RHS. "
        "Każda z nich jest porównywana bezpośrednio z oracle'em.",
        "",
        "`ogon # bezpieczny` jest maksimum wymaganego wyprzedzenia B po wszystkich "
        "fazach jednego okresu. Różnica względem bieżącego `ceil(delta_B/delta_A)` "
        "przewiduje dokładnie przypadki z rekordami all-null w nieprzepisanej LHS.",
        "",
        "## 4. Semantyka luk",
        "",
        "W bieżącym runtime detekcja luk nie zapisuje markerów dla strumieni "
        "obliczanych, więc obserwowalny ślad luk wyników R1 wynosi `G_S = ∅`. "
        "Macierz mutacyjna potwierdza, że komparator wykrywa wstrzyknięty marker. "
        "Włączenie propagacji luk byłoby zmianą semantyki należącą do K19/G16.",
        "",
        "## 5. Werdykt",
        "",
        (
            "**K2/G3 spełnia kryterium eksperymentalne: zero niewyjaśnionych rozbieżności.**"
            if equivalence["verdict"] == "OK" and engine["verdict"] == "OK"
            else "**K2/G3 pozostaje otwarte: wykryto rozbieżności.**"
        ),
        "",
    ]
    Path("results/summary.md").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    main()
