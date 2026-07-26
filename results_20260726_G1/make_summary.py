#!/usr/bin/env python3
"""Składa results/summary.md z jednego lub wielu plików probe.json (per profil)."""

import glob
import json
import os
import sys

LAYERS = [
    ("values", "wartości"),
    ("null_map", "mapa null"),
    ("zero_prefix", "prefiks zer"),
    ("field_names", "nazwy pól"),
    ("gaps", "luki"),
]


def load(paths):
    reports = []
    for path in sorted(paths):
        with open(path) as handle:
            reports.append(json.load(handle))
    return reports


def render_cases(report, out):
    out.append(f"### Przypadki — profil `{report['profile']}`\n")
    flags = " ".join(f"{k}={v}" for k, v in report["build_info"].items())
    out.append(f"Konfiguracja binarki: `{flags}`\n")
    out.append("| przypadek | nazwy pól | prefiks zer | rekordy all-null | wpisy gap | pierwsze wartości |")
    out.append("|---|---|---:|---|---|---|")
    for name, case in report["cases"].items():
        head = ", ".join(
            str(rec[0]) if len(rec) == 1 else "/".join(map(str, rec))
            for rec in case["records"][:9]
        )
        gaps = case.get("gap_entries", [])
        out.append(
            f"| `{name}` | `{', '.join(case['field_names'])}` | {case['zero_prefix']} "
            f"| {case['all_null_records']}/{case['records_total']} "
            f"| {len(gaps)} | {head} … |"
        )
    out.append("")


def render_pairs(report, out):
    out.append(f"### Pary planów — profil `{report['profile']}`\n")
    out.append("| rola | para | " + " | ".join(label for _, label in LAYERS) + " | uwaga |")
    out.append("|---|---|" + "---|" * len(LAYERS) + "---|")
    for pair in report["pairs"]:
        # Starsze raporty (sprzed dołożenia warstwy) nie mają wszystkich kluczy — "—" znaczy
        # "warstwa nie była wtedy mierzona", a nie "zgodna".
        cells = " | ".join("—" if key not in pair else ("=" if pair[key] else "**≠**") for key, _ in LAYERS)
        out.append(
            f"| {pair['role']} | `{pair['left']}` ↔ `{pair['right']}` | {cells} | {pair['note']} |"
        )
    out.append("")
    if not report["controls_ok"]:
        out.append("> **Kontrola zawiodła — wyniki tego profilu są nieważne.**\n")


def main():
    paths = sys.argv[1:] or glob.glob("results/probe*.json")
    if not paths:
        sys.exit("brak plików results/probe*.json — uruchom najpierw probe.py")

    reports = load(paths)
    out = [
        "# G1/K1 — obserwowalność planu: wyniki sondy",
        "",
        "Wygenerowane przez `make_summary.py`. Nie edytować ręcznie.",
        "Legenda: `=` warstwa zgodna między planami, `≠` rozbieżna.",
        "",
    ]
    for report in reports:
        render_cases(report, out)
        render_pairs(report, out)

    os.makedirs("results", exist_ok=True)
    with open("results/summary.md", "w") as handle:
        handle.write("\n".join(out) + "\n")
    print("zapisano: results/summary.md")


if __name__ == "__main__":
    main()
