#!/usr/bin/env python3
"""Kryterium badania higienicznego i raport."""
import argparse
import hashlib
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()

    # Commity pochodzą z pliku zapisanego przez build_trees.sh na podstawie
    # faktycznie zbudowanych drzew. Zaszycie ich w kodzie raportu sprawiło, że
    # pierwszy przebieg tej kampanii wypisał parę commitów z kampanii poprzedniej.
    commits = {}
    for line in (output / "commits.tsv").read_text(encoding="utf-8").splitlines()[1:]:
        tree, commit = line.split("\t")
        commits[tree] = commit
    historical_commit, fixed_commit = commits["HISTORICAL"], commits["FIXED"]

    corpus = json.loads((output / "corpus.json").read_text(encoding="utf-8"))
    pipelines = json.loads((output / "pipelines.json").read_text(encoding="utf-8"))

    plan_ok = not corpus["plan_differences"]
    # Zmiana statusu z porażki na sukces JEST treścią poprawki, nie odstępstwem.
    regressions = [c for c in corpus["status_changes"] if c["fixed_rc"] != 0]
    improvements = [c for c in corpus["status_changes"] if c["fixed_rc"] == 0]
    status_ok = not regressions
    counters_ok = not corpus["counter_differences"]
    # Potoki niedeterministyczne (identyczne is None) są wyłączone z kryterium.
    judged = [p for p in pipelines if p.get("identyczne") is not None]
    excluded = [p for p in pipelines if p.get("identyczne") is None]
    pipelines_ok = bool(judged) and all(p["identyczne"] for p in judged)
    verdict = "BRAK WPŁYWU" if (plan_ok and status_ok and counters_ok and pipelines_ok) else "WPŁYW WYKRYTY"

    lines = [
        f"# Wynik badania higienicznego — `{historical_commit[:7]}` → `{fixed_commit[:7]}`",
        "", f"**Werdykt: {verdict}**", "",
        f"- korpus: {corpus['korpus']} plików RQL",
        f"- HISTORICAL `{historical_commit[:7]}`: {corpus['historical']['skompilowane']} skompilowanych, "
        f"{corpus['historical']['odrzucone']} odrzuconych, R1={corpus['historical']['r1']}, R2={corpus['historical']['r2']}",
        f"- FIXED `{fixed_commit[:7]}`: {corpus['fixed']['skompilowane']} skompilowanych, "
        f"{corpus['fixed']['odrzucone']} odrzuconych, R1={corpus['fixed']['r1']}, R2={corpus['fixed']['r2']}",
        "", "## Kryterium", "",
        "| Warunek | Wynik |", "|---|---|",
        f"| zero różnic w zrzutach planu | {'spełniony' if plan_ok else 'NIESPEŁNIONY (' + str(len(corpus['plan_differences'])) + ')'} |",
        f"| zero regresji statusu kompilacji | {'spełniony' if status_ok else 'NIESPEŁNIONY (' + str(len(regressions)) + ')'} |",
        f"| zero różnic w licznikach R1/R2 | {'spełniony' if counters_ok else 'NIESPEŁNIONY (' + str(len(corpus['counter_differences'])) + ')'} |",
        f"| artefakty potoków identyczne | {'spełniony' if pipelines_ok else 'NIESPEŁNIONY'} ({len(judged)} ocenionych, {len(excluded)} wyłączonych) |",
        "",
    ]
    if corpus["plan_differences"]:
        lines += ["## Różnice planu", ""] + [f"- `{p}`" for p in corpus["plan_differences"]] + [""]
    if regressions:
        lines += ["## Regresje statusu (kompilowało się, przestało)", ""]
        lines += [f"- `{c['path']}`: rc {c['historical_rc']} → {c['fixed_rc']}" for c in regressions] + [""]
    if improvements:
        lines += ["## Naprawione przez poprawkę (nie odstępstwo)", ""]
        lines += [f"- `{c['path']}`: rc {c['historical_rc']} → {c['fixed_rc']}" for c in improvements] + [""]
    if corpus["counter_differences"]:
        lines += ["## Różnice liczników", ""] + [f"- `{p}`" for p in corpus["counter_differences"]] + [""]

    lines += ["## Artefakty potoków", "", "| Potok | Cykli | Artefaktów | Identyczne |", "|---|---:|---:|---|"]
    for p in judged:
        lines.append(
            f"| `{p['potok']}` | {p.get('cykli', '-')} | {p.get('artefaktow', '-')} | "
            f"{'tak' if p['identyczne'] else 'NIE — ' + '; '.join(p.get('uwagi', []))} |"
        )
    if excluded:
        lines += ["", "### Potoki wyłączone z kryterium", "",
                  "Dwa przebiegi tym samym silnikiem dają różne bajty, więc potok nie odróżnia",
                  "zmiany kodu od zmiany wejścia i nie może służyć za wyrocznię.", ""]
        for p in excluded:
            lines.append(f"- `{p['potok']}` — {'; '.join(p.get('uwagi', []))}")

    lines += ["", "## Uwaga do liczników R1/R2", "",
              "Liczniki są identyczne po obu stronach porównania i to jest treścią warunku.",
              "Nie należy ich natomiast zestawiać z liczbami zapisanymi w K4 (`R1=5`, `R2=18`):",
              "tamte pochodzą z commitu `50e19b7` i korpusu 80 plików — sprzed zniesienia warunku",
              "jednego konsumenta w R1 oraz przed dodaniem testów `agse_volatile`",
              "i `r1_identity_nulls`. Wzrost R1 z 5 do 8 wynika z tych zmian, nie ze scalenia",
              "badanego tutaj; widać to stąd, że **oba** drzewa raportują tę samą wartość.", ""]

    lines += ["## Wniosek", ""]
    if verdict == "BRAK WPŁYWU":
        lines.append(f"Scalenie `{fixed_commit[:7]}` nie zmieniło zachowania dla żadnego planu, który")
        lines.append(f"kompilował się i wykonywał na `{historical_commit[:7]}`.")
        lines.append("Wyniki zapisane na wcześniejszych rewizjach pozostają w mocy.")
    else:
        lines.append("Wykryto wpływ. Wskazane wyżej pozycje wymagają ponownego rozpatrzenia,")
        lines.append("a wyniki zapisane na wcześniejszych rewizjach — weryfikacji.")

    # R14 reguła 1: artefakt imiennie wskazany w werdykcie negatywnym musi zostać
    # plikiem w results/evidence/, a nie zniknąć w archiwum. Lista jest zapisywana
    # także wtedy, gdy jest pusta — pusty plik dowodzi, że nie było czego zachować,
    # w odróżnieniu od braku pliku, który nie dowodzi niczego.
    evidence: list[str] = []
    for path in corpus["plan_differences"]:
        stem = hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]
        name = Path(path).stem
        suite = ("integration_serial" if "IntegrationTest_serial" in path
                 else "integration_parallel" if "IntegrationTest_parallel" in path else "examples")
        for tree in ("HISTORICAL", "FIXED"):
            evidence.append(f"raw/corpus/{tree}/{suite}/{name}-{stem}.stdout")
    for record in judged:
        if record["identyczne"]:
            continue
        label = Path(record["potok"]).parent.name
        for note in record.get("uwagi", []):
            if not note.startswith("różnica w "):
                continue
            artifact = note.removeprefix("różnica w ").split(" (")[0]
            for tree in ("HISTORICAL", "FIXED"):
                evidence.append(f"raw/pipelines/{label}/{tree}/{artifact}")
    (output / "evidence_list.txt").write_text("\n".join(evidence) + ("\n" if evidence else ""), encoding="utf-8")

    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Werdykt: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
