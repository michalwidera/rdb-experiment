#!/usr/bin/env python3
"""Rozbieznosc artefaktow R1-ON / R1-OFF w powtorce R593 K6c: zmiana Lat czy Val?

`analyze.py` K6c zglasza w siedmiu komorkach z R1 dwie sumy artefaktow, rozdzielone
dokladnie wedlug R1 (ALGSTRUCT, STRUCT_R1 wobec OFF, STRUCT). Harness kasuje artefakty po
policzeniu sumy, wiec ten skrypt odtwarza kazda komorke na hoscie z binarkami o tych
samych flagach i tym samym budzetem slotow (`-f`, bez zegara), i:

  1. sprawdza, ze suma artefaktow hosta (`summarize_run.checksum_artifacts`) rowna sie
     sumie z workera dla tej strony R1 - wtedy pliki hosta SA artefaktami pomiaru;
  2. porownuje kazdy strumien uzytkownika warunkami relacji Obs z aparatury H9
     (`oracle_values.compare_rdb_observable` bez wymogu okna >= 2000 rekordow, ktory jest
     regula predeklaracji H9): identyczny deskryptor, identyczny wspolny prefiks wartosci
     i kolejnosci, brak NULL i luk, liczba rekordow R1-ON nie mniejsza.

Wynik 7/7 Obs znaczy: R1 zmienia tylko Lat (krotszy ogon, wiecej rekordow), Val jest rowne
- dokladnie to, na co pozwala def:observable od fcc5a444. Kod 0 - 7/7; 1 - nie; 2 - blad.
"""

import argparse
import csv
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "results_20261103_R593_H9"))
sys.path.insert(0, str(HERE))
import oracle_values as ov  # noqa: E402
import summarize_run  # noqa: E402

CELLS = ["W2_Q01", "W2_Q08", "W2_Q32", "W3_d1", "W3_d3", "W4_Q08", "W4_Q32"]
# Profil K6c -> profil H9 o identycznych flagach (README K6c, "Binarki profili").
SIDES = {"R1_ON": ("ALGSTRUCT", "R593-DEFAULT"), "R1_OFF": ("STRUCT", "R593-NO_R1_NO_R2")}


def worker_sums():
    sums = {}
    for path in sorted(glob.glob(str(HERE / "ablation" / "study_*" / "runs.csv"))):
        for row in csv.DictReader(open(path, encoding="utf-8")):
            sums.setdefault((row["case"], row["profile"]), set()).add(row["artifacts_sha256"])
    return sums


def run_cell(binary, workloads, case, slots, code_repo, work):
    run = work / case
    run.mkdir(parents=True)
    (run / "temp").mkdir()
    for path in (workloads / case).iterdir():
        if path.name != "external_data.txt":
            shutil.copy2(path, run / path.name)
    external = workloads / case / "external_data.txt"
    if external.exists():
        for relative in external.read_text().split():
            shutil.copy2(code_repo / relative, run / Path(relative).name)
    env = dict(os.environ, RDB_NAMESPACE="r593obs")
    done = subprocess.run([str(binary), "query.rql", "-r", "-k", "-f", "-m", str(slots)], cwd=run, env=env,
                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=600)
    if done.returncode != 0:
        raise RuntimeError(f"{case}/{binary}: rc={done.returncode} {done.stderr[-300:]}")
    streams = summarize_run.user_named_streams(run / "query.rql")
    return run, streams, summarize_run.checksum_artifacts(run / "temp", streams)[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--code-repo", type=Path, default=Path.home() / "github" / "retractordb")
    parser.add_argument("--out", type=Path, required=True, help="raport markdown")
    args = parser.parse_args()
    rate = json.loads((HERE / "results" / "rate.json").read_text())
    sums = worker_sums()
    lines = ["| Komorka | suma hosta = worker (ON / OFF) | strumieni | Obs | rekordow ON / OFF (najdluzszy strumien) |",
             "|---|---|---:|---|---|"]
    ok_cells = 0
    try:
        with tempfile.TemporaryDirectory() as name:
            tmp = Path(name)
            for case in CELLS:
                cell = rate["cells"][case]
                scale = rate["families"][cell["family"]]["scale"]
                workloads = tmp / f"w{scale}"
                if not workloads.exists():
                    subprocess.run([sys.executable, str(HERE / "generate.py"), "--output", str(workloads),
                                    "--scale", str(scale)], check=True, stdout=subprocess.DEVNULL)
                runs, match = {}, []
                for side, (profile, build) in SIDES.items():
                    binary = args.code_repo / "build" / build / "src" / "retractor" / "xretractor"
                    run, streams, digest = run_cell(binary, workloads, case, int(cell["slots"]), args.code_repo,
                                                    tmp / side)
                    runs[side] = (run, streams)
                    match.append(sums.get((case, profile)) == {digest})
                problems, counts = [], (0, 0)
                run_on, streams = runs["R1_ON"]
                run_off, _ = runs["R1_OFF"]
                checked = 0
                for stream in sorted(streams):
                    if not (run_on / "temp" / stream).exists():
                        continue
                    on = ov.read_rdb_stream(str(run_on / "temp"), stream)
                    off = ov.read_rdb_stream(str(run_off / "temp"), stream)
                    # Warunki compare_rdb_observable poza wymogiem okna H9 (MIN_WINDOW=2000, §7.1
                    # predeklaracji K26v3): w K6c oknem jest caly artefakt komorki.
                    tag = f"{case}/{stream}"
                    try:
                        ov.check_descriptor(on, off, tag)
                        if len(on["records"]) < len(off["records"]):
                            raise ov.Mismatch("record_count_tail", f"{tag}: R1-ON {len(on['records'])} "
                                              f"< R1-OFF {len(off['records'])} rekordow")
                        ov.check_values(on["records"], off["records"], tag)
                        for side, data in (("R1-ON", on), ("R1-OFF", off)):
                            bad = [line for line in data["nullmap"]
                                   if re.search(r"partial null|nullfill|\bgap\b", line, re.IGNORECASE)]
                            if bad or not any("no nulls" in line.lower() for line in data["nullmap"]):
                                raise ov.Mismatch("null_gap_map", f"{tag}: {side}: {data['nullmap']}")
                    except ov.Mismatch as exc:
                        problems.append(str(exc))
                    counts = max(counts, (len(on["records"]), len(off["records"])))
                    checked += 1
                good = all(match) and not problems and checked > 0
                ok_cells += good
                lines.append(f"| {case} | {'tak' if match[0] else 'NIE'} / {'tak' if match[1] else 'NIE'} | {checked} | "
                             f"{'Obs' if not problems else 'NIE: ' + problems[0][:80]} | {counts[0]} / {counts[1]} |")
    except (RuntimeError, OSError, KeyError, subprocess.CalledProcessError, ov.Mismatch) as exc:
        print(f"BLAD: {exc}", file=sys.stderr)
        return 2
    lines += ["", f"Komorki z Obs i sumami zgodnymi z workerem: {ok_cells}/{len(CELLS)}.", ""]
    args.out.write_text("\n".join(lines))
    print("\n".join(lines))
    return 0 if ok_cells == len(CELLS) else 1


if __name__ == "__main__":
    sys.exit(main())
