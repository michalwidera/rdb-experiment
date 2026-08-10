#!/usr/bin/env python3
"""Worker P8 K26: jedna rodzina, dokladnie 480 zamrozonych przebiegow.

Skrypt jest uruchamiany osobno dla kazdej rodziny przez nadzorce. Czyta
``blocks.tsv``, wykonuje po jednym warm-upie Q=32 na profil poza wynikiem,
sprawdza srodowisko i binaria, a po kazdej komorce egzekwuje STOP-8.
"""

import argparse
import csv
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tarfile
from fractions import Fraction
from pathlib import Path

from calib.gen_calib import scale_plan
from reduce_results import SUMMARY_COLUMNS, ReductionError, summarize_probe, write_tsv

HERE = Path(__file__).resolve().parent
FAMILIES = ["F9-R2", "F9-R1", "F9-X"]
FAMILY_FILE = {family: family.replace("-", "_") for family in FAMILIES}
PROFILES = ["DEFAULT", "NO_R2_CANON", "NO_R1_FACTOR", "NO_R1_NO_R2"]
SLOTS = {"F9-R2": 3000, "F9-R1": 6000, "F9-X": 6000}
LOGICAL = re.compile(
    r"^LOGICAL substrat: dopisania=\d+ nadpisania=\d+ bajty=\d+\s+"
    r"publiczne: dopisania=(\d+) nadpisania=\d+ bajty=\d+", re.M
)


class MatrixError(RuntimeError):
    pass


def key_values(path):
    values = {}
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            if not raw.strip() or raw.startswith("#"):
                continue
            fields = raw.rstrip("\n").split("\t")
            if fields in (["key", "value"], ["profile", "sha256"]):
                continue
            if len(fields) != 2 or fields[0] in values:
                raise MatrixError(f"{path}: nieprawidlowy albo zdublowany wiersz")
            values[fields[0]] = fields[1]
    return values


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def temperature_millic():
    candidates = sorted(Path("/sys/class/thermal").glob("thermal_zone*/temp"))
    values = []
    for path in candidates:
        try:
            values.append(int(path.read_text().strip()))
        except (OSError, ValueError):
            pass
    if not values:
        raise MatrixError("brak czytelnego czujnika temperatury")
    return max(values)


def check_environment(cpu, code_repo, start_record, annex_bin, annex_env):
    start = key_values(start_record)
    binaries = key_values(annex_bin)
    environment = key_values(annex_env)
    required_start = {"engine_sha", "experiment_sha"}
    if not required_start <= set(start):
        raise MatrixError("ANEKS-0_start.tsv nie zawiera wiazacego SHA silnika i eksperymentu")
    actual_sha = subprocess.run(
        ["git", "-C", code_repo, "rev-parse", "HEAD"], check=True, text=True, capture_output=True
    ).stdout.strip()
    if actual_sha != start["engine_sha"]:
        raise MatrixError(f"HEAD silnika {actual_sha} != pin kampanii {start['engine_sha']}")
    experiment_repo = HERE.parent
    experiment_sha = subprocess.run(
        ["git", "-C", experiment_repo, "rev-parse", "HEAD"], check=True, text=True, capture_output=True
    ).stdout.strip()
    if experiment_sha != start["experiment_sha"]:
        raise MatrixError(f"HEAD eksperymentu {experiment_sha} != pin kampanii {start['experiment_sha']}")
    experiment_dirty = subprocess.run(
        ["git", "-C", experiment_repo, "status", "--short"], check=True, text=True, capture_output=True
    ).stdout
    if experiment_dirty:
        raise MatrixError("drzewo eksperymentu jest brudne")
    dirty = subprocess.run(
        ["git", "-C", code_repo, "status", "--short"], check=True, text=True, capture_output=True
    ).stdout
    if dirty:
        raise MatrixError("drzewo silnika jest brudne")
    kernel = subprocess.run(["uname", "-r"], check=True, text=True, capture_output=True).stdout.strip()
    if kernel != environment.get("kernel"):
        raise MatrixError(f"kernel {kernel} != ANEKS-3 {environment.get('kernel')}")
    governor_path = Path(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor")
    governor = governor_path.read_text().strip()
    if governor != "performance" or environment.get("governor") != "performance":
        raise MatrixError(f"governor cpu{cpu}={governor}, wymagane performance")
    if str(cpu) not in environment.get("cpu_isolated", "").split(","):
        raise MatrixError(f"cpu{cpu} nie jest wymieniony jako izolowany w ANEKS-3")
    for profile in PROFILES:
        binary = code_repo / "build" / f"K26v2-{profile}" / "src" / "retractor" / "xretractor"
        if not os.access(binary, os.X_OK):
            raise MatrixError(f"brak binarium {profile}: {binary}")
        if file_sha256(binary) != binaries.get(profile):
            raise MatrixError(f"SHA binarium {profile} nie zgadza sie z ANEKS-2")
        capabilities = subprocess.run(["getcap", binary], check=True, text=True,
                                      capture_output=True).stdout
        if "cap_sys_nice" not in capabilities or "cap_ipc_lock" not in capabilities:
            raise MatrixError(f"binarium {profile} nie ma capabilities RT")


def rows_for_family(path, family):
    with path.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle, delimiter="\t") if row["family"] == family]
    if len(rows) != 480:
        raise MatrixError(f"blocks.tsv: rodzina {family} ma {len(rows)} przebiegow, oczekiwano 480")
    expected = {(block, q, profile) for block in range(1, 21) for q in (1, 2, 4, 8, 16, 32)
                for profile in PROFILES}
    actual = {(int(row["block"]), int(row["q"]), row["profile"]) for row in rows}
    if actual != expected:
        raise MatrixError("blocks.tsv: niepelny produkt 20 blokow x 6 Q x 4 profile")
    return rows


def expected_public(p6_dir, family, profile, q):
    plan = f"{FAMILY_FILE[family]}_Q{q}"
    text = (p6_dir / profile / plan / "cell.counters").read_text(encoding="utf-8", errors="replace")
    matches = LOGICAL.findall(text)
    if len(matches) != 1 or int(matches[0]) <= 0:
        raise MatrixError(f"P6 {profile}/{plan}: brak jednoznacznego niezerowego mianownika")
    return int(matches[0])


def make_query(family, q, rate_scale, target):
    frozen = (HERE / "rql" / f"{FAMILY_FILE[family]}_Q{q}.rql").read_text()
    scaled, _ = scale_plan(frozen, rate_scale)
    target.write_text(scaled)


def stop_reason(lost_records, p99_ns, slot_ns):
    if lost_records > 0:
        return "lost_records"
    if p99_ns * 5 > slot_ns * 4:
        return "p99_over_80_percent_slot"
    return None


def run_one(family, profile, q, block, order, out, code_repo, p6_dir, cpu,
            rate_scale, slot_ns, timeout_s, warmup=False):
    binary = code_repo / "build" / f"K26v2-{profile}" / "src" / "retractor" / "xretractor"
    out.mkdir(parents=True, exist_ok=False)
    (out / "temp").mkdir()
    make_query(family, q, rate_scale, out / "query.rql")
    for source in (HERE / "data" / "main").glob("*.txt"):
        shutil.copy2(source, out / source.name)
    env = os.environ.copy()
    env["RDB_BENCH_CSV"] = str(out / "slot.csv")
    env["RDB_BENCH_LOGICAL"] = "1"
    before = temperature_millic()
    command = ["timeout", str(timeout_s), "taskset", "-c", str(cpu), str(binary),
               "query.rql", "-m", str(SLOTS[family]), "-r", "-k", "-t"]
    with (out / "run.out").open("w") as stdout, (out / "run.err").open("w") as stderr:
        completed = subprocess.run(command, cwd=out, env=env, stdout=stdout, stderr=stderr)
    after = temperature_millic()
    (out / "run.rc").write_text(f"{completed.returncode}\n")
    for source in (HERE / "data" / "main").glob("*.txt"):
        (out / source.name).unlink(missing_ok=True)
    if completed.returncode != 0:
        raise MatrixError(f"{family}/{profile}/Q={q}/blok={block}: rc={completed.returncode}")
    probe = summarize_probe(out / "slot.csv")
    text = (out / "run.err").read_text(encoding="utf-8", errors="replace")
    matches = LOGICAL.findall(text)
    if len(matches) != 1:
        raise MatrixError(f"{out}: brak jednego wiersza LOGICAL")
    public = int(matches[0])
    wanted = expected_public(p6_dir, family, profile, q)
    if public > wanted:
        raise MatrixError(f"{out}: publiczne dopisania {public} > P6 {wanted}")
    lost = wanted - public
    summary = {
        "family": family, "profile": profile, "q": q, "block": block, "order": order,
        "compute_median_ns": probe["compute_median_ns"],
        "compute_p99_ns": probe["compute_p99_ns"], "slot_ns": slot_ns,
        "lost_records": lost, "probe_rows": probe["probe_rows"], "public_appends": public,
        "temp_before_millic": before, "temp_after_millic": after,
    }
    write_tsv(out / "summary.tsv", SUMMARY_COLUMNS, [summary])
    reason = stop_reason(lost, probe["compute_p99_ns"], slot_ns)
    if warmup and lost:
        raise MatrixError(f"warm-up {family}/{profile}: utracono {lost} publicznych rekordow")
    if not warmup and reason:
        (out.parent.parent.parent.parent / "STOP-8").write_text(
            f"family\t{family}\nprofile\t{profile}\nq\t{q}\nblock\t{block}\nreason\t{reason}\n"
        )
        raise MatrixError(f"STOP-8: {reason} w {family}/{profile}/Q={q}/blok={block}")
    return summary


def archive_family(out, archive_dir, family):
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive = archive_dir / f"K26v2-P8-{family}.tar.gz"
    if archive.exists():
        raise MatrixError(f"archiwum juz istnieje: {archive}")
    with tarfile.open(archive, "w:gz", compresslevel=9) as handle:
        handle.add(out, arcname=family, recursive=True)
    digest = file_sha256(archive)
    (archive_dir / f"K26v2-P8-{family}.sha256").write_text(f"{digest}  {archive.name}\n")
    return archive, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", required=True, choices=FAMILIES)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--p6-rdb", type=Path, required=True)
    parser.add_argument("--code-repo", type=Path, default=Path.home() / "K26")
    parser.add_argument("--start-record", type=Path, default=HERE / "results" / "ANEKS-0_start.tsv")
    parser.add_argument("--annex-bin", type=Path, default=HERE / "ANEKS-2_worker_binaria.tsv")
    parser.add_argument("--annex-env", type=Path, default=HERE / "ANEKS-3_worker_srodowisko.tsv")
    parser.add_argument("--rate-annex", type=Path, default=HERE / "results" / "ANEKS-1_rate.tsv")
    parser.add_argument("--cpu", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    try:
        if args.out.exists():
            raise MatrixError(f"odmowa nadpisania istniejacego katalogu {args.out}")
        if subprocess.run(["pgrep", "-x", "xretractor"], stdout=subprocess.DEVNULL).returncode == 0:
            raise MatrixError("xretractor juz dziala")
        check_environment(args.cpu, args.code_repo.resolve(), args.start_record,
                          args.annex_bin, args.annex_env)
        rate = key_values(args.rate_annex)
        scale = Fraction(rate["rate_scale"])
        slot_key = f"slot_min_ms_{FAMILY_FILE[args.family]}"
        slot_ns = int(Fraction(rate[slot_key]) * 1_000_000)
        rows = rows_for_family(HERE / "blocks.tsv", args.family)
        args.out.mkdir(parents=True)
        for profile in PROFILES:
            run_one(args.family, profile, 32, 0, 0,
                    args.out / "warmup" / profile, args.code_repo.resolve(), args.p6_rdb,
                    args.cpu, scale, slot_ns, args.timeout, warmup=True)
        for index, row in enumerate(rows, 1):
            block, q, order, profile = (int(row["block"]), int(row["q"]),
                                         int(row["order"]), row["profile"])
            target = args.out / "raw" / f"block-{block:02d}" / f"q-{q}" / f"order-{order}_{profile}"
            summary = run_one(args.family, profile, q, block, order, target,
                              args.code_repo.resolve(), args.p6_rdb, args.cpu, scale,
                              slot_ns, args.timeout)
            print(f"[{index:03d}/480] {args.family} b={block} q={q} {profile} "
                  f"p99={summary['compute_p99_ns']} ns", flush=True)
        (args.out / "RUN_COMPLETE").write_text("480/480\n")
        archive, digest = archive_family(args.out, args.archive_dir, args.family)
        print(f"OK: {args.family} 480/480; {archive} sha256={digest}")
        return 0
    except (KeyError, OSError, subprocess.CalledProcessError, ReductionError, MatrixError) as exc:
        print(f"BLAD: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
