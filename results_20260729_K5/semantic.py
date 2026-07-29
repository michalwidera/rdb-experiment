#!/usr/bin/env python3
"""Kontrola semantyczna K5 — czy redukcja planu zachowuje wynik co do bajtu.

Sama redukcja liczby węzłów nie odróżnia optymalizacji od zepsucia planu, więc
reprezentatywne przypadki są wykonywane pod STRUCT i ALGSTRUCT, a artefakty
strumieni publicznych porównywane bajtowo. Substraty nie trafiają na dysk
(`SUBSTRAT 'memory'`), a ich nazwy i tak różnią się między profilami — to
właśnie jest przedmiot optymalizacji, a nie rozbieżność wyniku.
"""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

STAGE_ROOT = "/dev/shm"
META_HEADER = 8  # znacznik czasu utworzenia — wyłączony z porównania

# Potok EKG ma znacznie dłuższy ogon startowy niż workloady syntetyczne.
CYCLES = {"W8": 600}
DEFAULT_CYCLES = 200


def select_cases(counts: dict[str, object]) -> list[tuple[str, str]]:
    """Przypadki objęte kontrolą semantyczną.

    Warunek (b) reguły decyzyjnej mówi „dla KAŻDEGO takiego (w,Q)", więc brane
    są wszystkie przypadki z `net < 0` — nie próbka. Dodatkowo po jednym
    reprezentancie każdej rodziny bez redukcji, żeby brak różnicy w planie też
    był potwierdzony wynikiem, a nie założony.
    """
    selected: list[tuple[str, str]] = []
    seen_families: set[str] = set()
    for record in counts["comparisons"]:
        if record["net"] < 0:
            selected.append((record["family"], record["case"]))
            seen_families.add(record["family"])
    for record in counts["comparisons"]:
        if record["net"] == 0 and record["family"] not in seen_families:
            selected.append((record["family"], record["case"]))
            seen_families.add(record["family"])
    return selected


def stage(case_dir: Path, code_repo: Path, work: Path) -> None:
    work.mkdir(parents=True)
    (work / "temp").mkdir()
    shutil.copy(case_dir / "query.rql", work / "query.rql")
    external = case_dir / "external_data.txt"
    if external.is_file():
        for relative in external.read_text(encoding="utf-8").split():
            source = code_repo / relative
            (work / source.name).symlink_to(source)
    for extra in sorted(case_dir.glob("*.txt")):
        if extra.name != "external_data.txt":
            shutil.copy(extra, work / extra.name)


def run_case(binary: Path, case_dir: Path, code_repo: Path, cycles: int, keep: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="rdb-k5-sem-", dir=STAGE_ROOT) as root:
        work = Path(root) / "case"
        stage(case_dir, code_repo, work)
        completed = subprocess.run(
            [str(binary), "query.rql", "-r", "-k", "-m", str(cycles)],
            cwd=work,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=600,
            check=False,
        )
        if keep.exists():
            shutil.rmtree(keep)
        shutil.copytree(work / "temp", keep)
        return {"returncode": completed.returncode, "stderr": completed.stderr[-2000:]}


def compare(left: Path, right: Path) -> tuple[bool, list[str]]:
    notes: list[str] = []
    left_files = {p.name for p in left.iterdir() if p.is_file()}
    right_files = {p.name for p in right.iterdir() if p.is_file()}
    if left_files != right_files:
        notes.append(f"różny zestaw artefaktów: tylko STRUCT={sorted(left_files - right_files)} "
                     f"tylko ALGSTRUCT={sorted(right_files - left_files)}")
        return False, notes
    if not left_files:
        notes.append("brak artefaktów do porównania")
        return False, notes
    ok = True
    for name in sorted(left_files):
        a = (left / name).read_bytes()
        b = (right / name).read_bytes()
        if name.endswith(".meta"):
            a, b = a[META_HEADER:], b[META_HEADER:]
        if a != b:
            ok = False
            notes.append(f"różnica w {name} ({len(a)} vs {len(b)} bajtów)")
    return ok, notes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-repo", type=Path, required=True)
    parser.add_argument("--workloads", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    code_repo = args.code_repo.resolve()
    workloads = args.workloads.resolve()
    output = args.output.resolve()
    artifacts = output / "raw/semantic"
    artifacts.mkdir(parents=True, exist_ok=True)

    counts = json.loads((output / "counts.json").read_text(encoding="utf-8"))
    selection = select_cases(counts)

    results: list[dict[str, object]] = []
    failures = 0
    for family, case in selection:
        cycles = CYCLES.get(family, DEFAULT_CYCLES)
        record: dict[str, object] = {"family": family, "case": case, "cycles": cycles}
        runs = {}
        for profile in ("STRUCT", "ALGSTRUCT"):
            binary = code_repo / f"build/K5-{profile}/src/retractor/xretractor"
            runs[profile] = run_case(binary, workloads / case, code_repo, cycles, artifacts / case / profile)
            record[f"{profile}_rc"] = runs[profile]["returncode"]

        if any(runs[p]["returncode"] != 0 for p in runs):
            record["identyczne"] = False
            record["uwagi"] = ["przebieg zakończony błędem"] + [
                f"{p}: {runs[p]['stderr'][-300:]}" for p in runs if runs[p]["returncode"] != 0
            ]
            failures += 1
        else:
            identical, notes = compare(artifacts / case / "STRUCT", artifacts / case / "ALGSTRUCT")
            record["identyczne"] = identical
            record["uwagi"] = notes
            record["artefakty"] = len([p for p in (artifacts / case / "STRUCT").iterdir() if p.is_file()])
            if not identical:
                failures += 1
        results.append(record)
        print(f"{case}: identyczne={record['identyczne']} {record.get('uwagi') or ''}")

    (output / "semantic.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
