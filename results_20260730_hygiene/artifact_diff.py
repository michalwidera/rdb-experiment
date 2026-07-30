#!/usr/bin/env python3
"""Badanie higieniczne, warstwa druga: artefakty wykonania, nie tylko plan.

Identyczny zrzut planu nie dowodzi jeszcze identycznego zachowania — poprawka
dotyczy interwałów, które karmią `computeStartupLatency` i
`computeRequiredCapacities`, a te wpływają na pojemność buforów w czasie
wykonania. Dlatego reprezentatywne potoki są uruchamiane pod oboma silnikami,
a wszystkie artefakty porównywane bajtowo.

Nagłówek `.meta` (8 bajtów) zawiera znacznik czasu utworzenia i jest wyłączony
z porównania — inaczej każdy przebieg różniłby się z definicji.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

STAGE_ROOT = "/dev/shm"
META_HEADER = 8

# Potoki dobrane tak, by przechodziły przez ścieżki ruszone poprawką:
# STREAM_AGSE (okna), programy jednoelementowe i agregaty.
PIPELINES = [
    ("examples/ecg/rec205/rec205-qrs.rql", 4000),
    ("test/IntegrationTest_parallel/dsp/query.rql", 400),
    ("test/IntegrationTest_serial/optimizer_ablation/query.rql", 200),
    ("test/IntegrationTest_serial/agse_volatile/query.rql", 200),
]


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).digest()
        for path in root.rglob("*")
        if path.is_file()
    }


def run(binary: Path, case_dir: Path, source_name: str, cycles: int, keep: Path) -> int:
    with tempfile.TemporaryDirectory(prefix="rdb-hyg-run-", dir=STAGE_ROOT) as stage:
        work = Path(stage) / "case"
        shutil.copytree(case_dir, work, ignore=shutil.ignore_patterns("__pycache__", "temp"))
        (work / "temp").mkdir(exist_ok=True)
        # Nie wszystkie potoki mają dyrektywę STORAGE — `rec205-qrs.rql`
        # i `agse_volatile` piszą do katalogu roboczego, nie do `temp/`.
        # Zbieranie wyłącznie z `temp/` dawało dla nich PUSTE porównanie
        # raportowane jako zgodność.
        before = snapshot(work)

        done = subprocess.run(
            [str(binary), source_name, "-r", "-k", "-m", str(cycles)],
            cwd=work,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=900,
            check=False,
        )

        if keep.exists():
            shutil.rmtree(keep)
        keep.mkdir(parents=True)
        # Artefaktem jest każdy plik nowy albo zmieniony względem wejścia.
        for path in sorted(work.rglob("*")):
            if not path.is_file():
                continue
            relative = str(path.relative_to(work))
            digest = hashlib.sha256(path.read_bytes()).digest()
            if before.get(relative) == digest:
                continue
            shutil.copy(path, keep / relative.replace("/", "__"))
        return done.returncode


def compare(left: Path, right: Path) -> tuple[bool, list[str], int]:
    notes: list[str] = []
    left_files = {p.name for p in left.iterdir() if p.is_file()}
    right_files = {p.name for p in right.iterdir() if p.is_file()}
    # Puste porównanie NIE jest zgodnością. Milczenie nie może wyglądać jak sukces.
    if not left_files and not right_files:
        notes.append("brak artefaktów do porównania — potok nic nie wyprodukował")
        return False, notes, 0
    if left_files != right_files:
        notes.append(
            f"różny zestaw artefaktów: tylko HISTORICAL={sorted(left_files - right_files)} "
            f"tylko FIXED={sorted(right_files - left_files)}"
        )
        return False, notes, 0
    ok = True
    for name in sorted(left_files):
        a = (left / name).read_bytes()
        b = (right / name).read_bytes()
        if name.endswith(".meta"):
            a, b = a[META_HEADER:], b[META_HEADER:]
        if a != b:
            ok = False
            notes.append(f"różnica w {name} ({len(a)} vs {len(b)} bajtów)")
    return ok, notes, len(left_files)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-repo", type=Path, required=True)
    parser.add_argument("--historical-binary", type=Path, required=True)
    parser.add_argument("--fixed-binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    code_repo = args.code_repo.resolve()
    output = args.output.resolve()
    artifacts = output / "raw/pipelines"
    artifacts.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, object]] = []
    failures = 0
    for relative, cycles in PIPELINES:
        source = code_repo / relative
        if not source.is_file():
            results.append({"potok": relative, "identyczne": False, "uwagi": ["brak pliku"]})
            failures += 1
            continue
        label = source.parent.name
        record: dict[str, object] = {"potok": relative, "cykli": cycles}
        codes = {}
        for name, binary in (("HISTORICAL", args.historical_binary), ("FIXED", args.fixed_binary)):
            codes[name] = run(binary, source.parent, source.name, cycles, artifacts / label / name)
            record[f"{name}_rc"] = codes[name]

        # Kontrola determinizmu. Potok, którego dwa przebiegi TYM SAMYM silnikiem
        # dają różne bajty, nie może służyć za wyrocznię porównania między
        # silnikami — różnica pochodziłaby ze źródła, nie z kodu. Dotyczy to
        # `dsp`, którego wejściem jest `/dev/urandom`.
        codes["HISTORICAL_2"] = run(
            args.historical_binary, source.parent, source.name, cycles, artifacts / label / "HISTORICAL_2"
        )
        deterministic, _, _ = compare(artifacts / label / "HISTORICAL", artifacts / label / "HISTORICAL_2")
        record["deterministyczny"] = deterministic
        if not deterministic:
            record["identyczne"] = None  # wyłączony z kryterium
            record["uwagi"] = [
                "potok niedeterministyczny — dwa przebiegi tym samym silnikiem dają różne bajty; "
                "wyłączony z kryterium, bo nie odróżnia zmiany kodu od zmiany wejścia"
            ]
            results.append(record)
            print(f"{relative}: NIEDETERMINISTYCZNY — wyłączony z kryterium")
            continue

        if any(code != 0 for code in codes.values()):
            record["identyczne"] = False
            record["uwagi"] = [f"niezerowy kod zakończenia: {codes}"]
            failures += 1
        else:
            identical, notes, count = compare(artifacts / label / "HISTORICAL", artifacts / label / "FIXED")
            record["identyczne"] = identical
            record["uwagi"] = notes
            record["artefaktow"] = count
            if not identical:
                failures += 1
        results.append(record)
        print(f"{relative}: identyczne={record['identyczne']} {record.get('uwagi') or ''}")

    (output / "pipelines.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
