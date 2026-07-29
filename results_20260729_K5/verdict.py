#!/usr/bin/env python3
"""Zastosowanie zamrożonej reguły decyzyjnej K5 i wygenerowanie summary.md.

Reguła pochodzi z README.md i była zacommitowana przed zebraniem danych.
Ten skrypt jej nie interpretuje — wylicza jej warunki i raportuje wynik,
również negatywny.
"""
import argparse
import json
from pathlib import Path

CONTROL_FAMILIES = ("W5", "W6", "W7")
EXTERNAL_FAMILY = "W8"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    counts = json.loads((output / "counts.json").read_text(encoding="utf-8"))
    semantic = json.loads((output / "semantic.json").read_text(encoding="utf-8"))
    comparisons = counts["comparisons"]
    semantic_by_case = {record["case"]: record for record in semantic}

    hits = [record for record in comparisons if record["net"] < 0]

    # (a) istnieje przypadek z net < 0
    condition_a = bool(hits)

    # (b) każdy taki przypadek jest bajtowo identyczny pod STRUCT i ALGSTRUCT
    unverified = [record["case"] for record in hits if record["case"] not in semantic_by_case]
    divergent = [
        record["case"]
        for record in hits
        if record["case"] in semantic_by_case and not semantic_by_case[record["case"]]["identyczne"]
    ]
    condition_b = bool(hits) and not unverified and not divergent

    # (c) net == 0 w rodzinach kontrolnych
    control_violations = [
        record for record in comparisons if record["family"] in CONTROL_FAMILIES and record["net"] != 0
    ]
    condition_c = not control_violations

    go = condition_a and condition_b and condition_c
    external_hit = any(record["family"] == EXTERNAL_FAMILY for record in hits)
    if not go:
        verdict = "NO-GO"
    elif external_hit:
        verdict = "GO"
    else:
        verdict = "GO warunkowe"

    lines = [
        "# Wynik K5 — punkt go/no-go",
        "",
        f"**Werdykt: {verdict}**",
        "",
        f"- commit kodu: `{counts['code_commit']}`",
        f"- przypadków: {counts['cases']}, profili: {len(counts['profiles'])}",
        f"- wykluczonych z reguły: {len(counts['excluded'])}",
        "",
        "## Warunki reguły decyzyjnej",
        "",
        "| Warunek | Treść | Wynik |",
        "|---|---|---|",
        f"| (a) | istnieje `(w,Q)` z `net < 0` | {'spełniony' if condition_a else 'NIESPEŁNIONY'} "
        f"({len(hits)} przypadków) |",
        f"| (b) | każdy taki przypadek bajtowo identyczny | {'spełniony' if condition_b else 'NIESPEŁNIONY'} |",
        f"| (c) | `net = 0` w W5, W6, W7 | {'spełniony' if condition_c else 'NIESPEŁNIONY'} |",
        f"| kwalifikator | redukcja w rodzinie umotywowanej zewnętrznie (W8) | "
        f"{'tak' if external_hit else 'NIE'} |",
        "",
    ]

    if unverified:
        lines += [f"Przypadki z `net < 0` bez kontroli semantycznej: {', '.join(unverified)}", ""]
    if divergent:
        lines += [f"Przypadki z rozbieżnością bajtową: {', '.join(divergent)}", ""]
    if control_violations:
        lines += ["Naruszenia kontroli negatywnej:", ""]
        for record in control_violations:
            lines.append(f"- `{record['case']}`: net = {record['net']}")
        lines.append("")

    lines += [
        "## Porównanie STRUCT → ALGSTRUCT",
        "",
        "`net` to zmiana liczby węzłów planu wyjściowego. Kolumny tokenów pochodzą",
        "z `PLAN bench` w punkcie wyjścia kompilatora.",
        "",
        "| Rodzina | Przypadek | Parametr | Węzły STRUCT | Węzły ALGSTRUCT | net | tokeny-from | tokeny-pól | r1 | r2 |",
        "|---|---|---|---:|---:|---:|---|---|---:|---:|",
    ]
    for record in comparisons:
        lines.append(
            f"| {record['family']} | `{record['case']}` | {record['param']} | "
            f"{record['struct_nodes']} | {record['algstruct_nodes']} | {record['net']} | "
            f"{record['struct_tokeny_from']} → {record['algstruct_tokeny_from']} | "
            f"{record['struct_tokeny_pol']} → {record['algstruct_tokeny_pol']} | "
            f"{record['r1']} | {record['r2']} |"
        )

    lines += ["", "## Usunięte węzły", "", "Imienna lista wymagana przez warunek (a).", ""]
    if hits:
        for record in hits:
            removed = ", ".join(f"`{name}`" for name in record["usuniete"]) or "*(brak)*"
            added = ", ".join(f"`{name}`" for name in record["dodane"]) or "*(brak)*"
            lines.append(f"- `{record['case']}` (net {record['net']}) — usunięte: {removed}; dodane: {added}")
    else:
        lines.append("*(brak — warunek (a) niespełniony)*")

    lines += ["", "## Skalowanie z Q (luka G6)", "",
              "Raportowane, ale **nieuwzględniane** w regule decyzyjnej.", ""]
    families = sorted({record["family"] for record in comparisons if record["q"] and record["family"] != "W3"})
    for family in families:
        series = sorted(
            (record for record in comparisons if record["family"] == family),
            key=lambda record: record["q"],
        )
        if len(series) < 2:
            continue
        net = ", ".join(f"Q={record['q']}: {record['net']}" for record in series)
        tokens = ", ".join(
            f"Q={record['q']}: {record['struct_tokeny_from'] - record['algstruct_tokeny_from']}"
            for record in series
        )
        lines.append(f"- **{family}** — net: {net}")
        lines.append(f"  - oszczędność tokenów FROM: {tokens}")

    lines += ["", "## Kontrola semantyczna", "",
              "| Przypadek | Cykli | Artefaktów | Identyczne |", "|---|---:|---:|---|"]
    for record in semantic:
        lines.append(
            f"| `{record['case']}` | {record['cycles']} | {record.get('artefakty', '-')} | "
            f"{'tak' if record['identyczne'] else 'NIE — ' + '; '.join(record['uwagi'])} |"
        )

    if counts["excluded"]:
        lines += ["", "## Wykluczone z reguły decyzyjnej", "",
                  "Przypadki niekompilujące się czysto pod każdym profilem "
                  "(patrz `defect_interval_resolution.md`).", ""]
        for case, profiles in sorted(counts["excluded"].items()):
            lines.append(f"- `{case}` — {', '.join(profiles)}")

    lines += ["", "## Atrybucja profili", "",
              "Liczba węzłów planu wyjściowego w każdym profilu.", "",
              "| Przypadek | " + " | ".join(p["profile"] for p in counts["profiles"]) + " |",
              "|---|" + "---:|" * len(counts["profiles"])]
    for record in comparisons:
        cells = []
        for profile in counts["profiles"]:
            observation = counts["observations"][profile["profile"]][record["case"]]
            cells.append(str(observation["node_count"]))
        lines.append(f"| `{record['case']}` | " + " | ".join(cells) + " |")

    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Werdykt: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
