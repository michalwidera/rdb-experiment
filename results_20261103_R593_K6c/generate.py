#!/usr/bin/env python3
"""Obciazenia powtorki R593 K6c: zamrozony generator K6c i plany po migracji.

Harness (`worker/run_ablation_study.sh`) wola `$CAMPAIGN_DIR/generate.py --output DIR --scale S`.
Ten plik NIE generuje niczego sam. Uruchamia zamrozony generator kampanii
(`results_20260730_K6c/generate.py`) z tymi samymi argumentami, a potem podmienia
kazdy `query.rql` na plan po migracji z `plans/s<S>/<przypadek>/query.rql`.

Podmiana jest dozwolona wylacznie dla planu, ktorego tresc zgadza sie bajt w bajt
z planem, na ktorym wykonano migracje (`orig_sha256` w `migration/migration.tsv`);
plan po podmianie musi miec `migrated_sha256` z tej samej tabeli. Kazdy plan
wygenerowany i nieobjety tabela, plan bez statusu MIGRATED/SAME po stronie M1 albo
MIGRATED po stronie S, i kazdy wiersz tabeli bez planu wygenerowanego jest bledem.
Dane (`*.txt`, `external_data.txt`) zostaja takie, jakie dal generator.

Migracje (M1, S1, S2) wykonal `paper-arXiv/measurment-tool/migrate_corpus.py` z dowodem;
statusy i sumy sa w `migration/migration.tsv`, opis w README.md.
"""

import argparse
import csv
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FROZEN_GENERATOR = HERE.parent / "results_20260730_K6c" / "generate.py"
MIGRATION = HERE / "migration" / "migration.tsv"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scale", required=True)
    args = parser.parse_args()

    subprocess.run([sys.executable, str(FROZEN_GENERATOR), "--output", str(args.output), "--scale", args.scale],
                   check=True)

    prefix = f"s{args.scale}/"
    with MIGRATION.open(encoding="utf-8", newline="") as handle:
        table = {row["plan"]: row for row in csv.DictReader(handle, delimiter="\t")
                 if row["plan"].startswith(prefix)}
    if not table:
        sys.exit(f"BLAD: migration.tsv nie ma planow skali {args.scale}")

    generated = sorted(args.output.glob("*/query.rql"))
    keys = {f"{prefix}{path.parent.name}/query.rql" for path in generated}
    if keys != set(table):
        sys.exit(f"BLAD: plany generatora i migration.tsv sie roznia: "
                 f"tylko generator={sorted(keys - set(table))[:5]}, tylko tabela={sorted(set(table) - keys)[:5]}")

    for path in generated:
        row = table[f"{prefix}{path.parent.name}/query.rql"]
        if row["m1"] not in ("SAME", "MIGRATED") or row["s"] != "MIGRATED":
            sys.exit(f"BLAD: {row['plan']} ma status migracji m1={row['m1']} s={row['s']}")
        if sha256(path) != row["orig_sha256"]:
            sys.exit(f"BLAD: {row['plan']}: generator dal inny plan niz ten, ktory zmigrowano")
        migrated = HERE / "plans" / row["plan"]
        if sha256(migrated) != row["migrated_sha256"]:
            sys.exit(f"BLAD: {migrated}: suma inna niz w migration.tsv")
        shutil.copyfile(migrated, path)
    print(f"OK: skala {args.scale}: {len(generated)} planow podmienionych na plany po migracji")
    return 0


if __name__ == "__main__":
    sys.exit(main())
