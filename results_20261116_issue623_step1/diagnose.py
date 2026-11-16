#!/usr/bin/env python3
"""Lokalna diagnoza kroku 1 #623; nie modyfikuje silnika ani zamrozonego H9."""

import argparse
import csv
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import random
import re
import shutil
import statistics
import subprocess
import tarfile


PROFILES = ("DEFAULT", "NO_R2_CANON", "NO_R1_FACTOR", "NO_R1_NO_R2")
FAMILIES = ("F9_R1", "F9_X", "F9_R2")
SEED = 62320261116


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def output(command, **kwargs):
    return subprocess.check_output(command, text=True, **kwargs)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n")


def write_tsv(path, rows):
    with path.open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("manifest", "plans", "timing", "profile", "summary", "analyze"))
    parser.add_argument("--repo", type=Path, default=Path("/home/michal/github/retractordb"))
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--build-prefix", default="R593-")
    parser.add_argument("--blocks", type=int, default=20)
    parser.add_argument("--cpu", type=int, default=15)
    parser.add_argument("--paced", action="store_true")
    parser.add_argument("--slot-divisor", type=int, default=1)
    args = parser.parse_args()
    repo, root = args.repo.resolve(), args.out.resolve()
    root.mkdir(parents=True, exist_ok=True)
    h9 = repo / "test/research_gate/h9"
    work = root / "work"
    work.mkdir(exist_ok=True)
    (work / "ipc").mkdir(exist_ok=True)
    (work / "config").mkdir(exist_ok=True)
    (work / "empty.toml").write_text("")
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(("RDB_", "XRETRACTOR_")):
            del env[name]
    env.update(RDB_NAMESPACE="issue623_step1", TMPDIR=str(work / "ipc"),
               XDG_CONFIG_HOME=str(work / "config"))
    binaries = {p: repo / "build" / (args.build_prefix + p) / "src/retractor/xretractor"
                for p in PROFILES}

    def prepare(family, q, profile):
        temp = work / "temp"
        if temp.exists():
            shutil.rmtree(temp)
        temp.mkdir()
        text = (h9 / "rql" / f"{family}_Q{q}.rql").read_text()
        text = re.sub(r"\bFILE\s+('.*?\.txt')", r"TEXTFILE \1", text)
        (work / "query.rql").write_text(text)
        for source in (h9 / "data/main").glob("*.txt"):
            shutil.copyfile(source, work / source.name)
        shutil.copyfile(binaries[profile], work / "xretractor")
        shutil.copymode(binaries[profile], work / "xretractor")
        assert sha(work / "xretractor") == sha(binaries[profile])

    def run(command, destination, probe_env=None):
        destination.parent.mkdir(parents=True, exist_ok=True)
        command = ["taskset", "-c", str(args.cpu)] + command
        with destination.with_suffix(".out").open("w") as stdout:
            with destination.with_suffix(".err").open("w") as stderr:
                result = subprocess.run(command, cwd=work, env=env | (probe_env or {}),
                                        stdout=stdout, stderr=stderr, timeout=180)
        write_json(destination.with_suffix(".command.json"), command)
        if result.returncode:
            raise RuntimeError(f"{destination}: rc={result.returncode}")
        error_text = destination.with_suffix(".err").read_text()
        if re.search(r"\[error\]|\[critical\]|fatal error:", error_text, re.I):
            raise RuntimeError(f"{destination}: blad w stderr")

    def slots(family):
        return (3000 if family == "F9_R2" else 6000) // args.slot_divisor

    runtime = ["./xretractor", "query.rql", "-r", "-k", "--config", "empty.toml"]
    if not args.paced:
        runtime += ["--no-clock"]

    if args.mode == "manifest":
        manifest = {"revision": output(["git", "rev-parse", "HEAD"], cwd=repo).strip(),
                    "status": output(["git", "status", "--porcelain"], cwd=repo),
                    "src_tree": output(["git", "rev-parse", "HEAD:src"], cwd=repo).strip(),
                    "runner_sha256": sha(Path(__file__).resolve()),
                    "compiler": output(["c++", "--version"]),
                    "valgrind": output(["valgrind", "--version"]).strip(),
                    "platform": platform.platform(), "cpu": args.cpu,
                    "cpuinfo": Path("/proc/cpuinfo").read_text().split("\n\n")[0],
                    "seed": SEED, "affinity": sorted(os.sched_getaffinity(0)),
                    "runtime": runtime, "profiles": {}, "inputs": {}}
        for profile, binary in binaries.items():
            build = binary.parents[2]
            cache = (build / "CMakeCache.txt").read_text()
            assert f"CMAKE_HOME_DIRECTORY:INTERNAL={repo}\n" in cache
            assert "CMAKE_BUILD_TYPE:STRING=Release\n" in cache
            info = output([str(binary), "--build-info"])
            factor = "OFF" if profile in ("NO_R1_FACTOR", "NO_R1_NO_R2") else "ON"
            canon = "OFF" if profile in ("NO_R2_CANON", "NO_R1_NO_R2") else "ON"
            expected = ("RDB_OPT_DEDUP_SUBSTRATES=ON\nRDB_OPT_SHARE_EQUIVALENT_SELECTS=ON\n"
                        f"RDB_OPT_COMMUTATIVE_ADD={canon}\n"
                        f"RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES={factor}\n"
                        "RDB_BENCH_PROBE=ON\nRDB_OPT_SIMPLIFY_EXPRESSIONS=ON\n")
            assert info == expected, (profile, info)
            before = sha(binary)
            verified_build = output(["ninja", "-C", str(build), "-j", "8", "xretractor"])
            assert sha(binary) == before, f"{profile}: binarium zmienilo sie po pomiarze"
            manifest["profiles"][profile] = {"binary": str(binary), "sha256": sha(binary),
                                               "build_info": info,
                                               "verified_build": verified_build}
            (root / f"cache-{profile}.txt").write_text(cache)
        for source in list((h9 / "data/main").glob("*.txt")) + [
                h9 / "rql" / f"{f}_Q{q}.rql" for f in FAMILIES for q in (1, 2)]:
            manifest["inputs"][str(source.relative_to(repo))] = sha(source)
        write_json(root / "manifest.json", manifest)

    elif args.mode == "plans":
        for family in FAMILIES:
            for q in (1, 2):
                for profile in PROFILES:
                    prepare(family, q, profile)
                    destination = root / "plans" / f"{family}_Q{q}_{profile}"
                    run(["./xretractor", "-c", "query.rql", "-v", "--config", "empty.toml"],
                        destination, {"RDB_BENCH_PLAN": "1"})
                    shutil.copyfile(work / "query.rql", destination.with_suffix(".rql"))
                    run(runtime + ["-v", "-m", str(slots(family))],
                        destination.with_name(destination.name + "_runtime"),
                        {"RDB_BENCH_PLAN": "1", "RDB_BENCH_WORK": "1",
                         "RDB_BENCH_LOGICAL": "1", "RDB_BENCH_MATERIALIZE": "1"})

    elif args.mode == "timing":
        label = "paced" if args.paced else "offline"
        target = root / label
        target.mkdir(exist_ok=False)
        rows = []
        rng = random.Random(SEED)
        for block in range(args.blocks + 1):
            cells = [(f, q) for f in FAMILIES for q in (1, 2)]
            rng.shuffle(cells)
            for family, q in cells:
                profiles = list(PROFILES)
                rng.shuffle(profiles)
                for order, profile in enumerate(profiles):
                    prepare(family, q, profile)
                    name = f"b{block:02}_{family}_Q{q}_{profile}"
                    destination = target / name
                    slot_csv = target / (name + ".csv")
                    run(runtime + ["-m", str(slots(family))], destination,
                        {"RDB_BENCH_CSV": str(slot_csv), "RDB_BENCH_WORK": "1",
                         "RDB_BENCH_LOGICAL": "1", "RDB_BENCH_MATERIALIZE": "1"})
                    with slot_csv.open() as stream:
                        values = [int(r["compute_ns"]) for r in csv.DictReader(stream)]
                    assert len(values) == slots(family) - 1, (name, len(values))
                    retained = values[max(30, len(values) // 10):]
                    rows.append({"block": block, "family": family, "q": q, "profile": profile,
                                 "order": order, "rows": len(values), "kept": len(retained),
                                 "median_ns": statistics.median(retained),
                                 "mean_ns": statistics.mean(retained)})
                    with slot_csv.open("rb") as source, gzip.open(str(slot_csv) + ".gz", "wb") as dest:
                        shutil.copyfileobj(source, dest)
                    slot_csv.unlink()
            write_tsv(target / "timing.tsv", rows)
            print(f"{label}: block {block}/{args.blocks}", flush=True)

    elif args.mode == "profile":
        for family in FAMILIES:
            for q in (1, 2):
                for profile in ("DEFAULT", "NO_R1_FACTOR"):
                    prepare(family, q, profile)
                    destination = root / "callgrind" / f"{family}_Q{q}_{profile}"
                    destination.parent.mkdir(exist_ok=True)
                    raw = destination.with_suffix(".cg")
                    run(["valgrind", "--tool=callgrind", "--cache-sim=yes",
                         "--collect-atstart=no", "--toggle-collect=*processRows*",
                         f"--callgrind-out-file={raw}"] + runtime + ["-m", str(slots(family))],
                        destination, {"RDB_BENCH_WORK": "1", "RDB_BENCH_LOGICAL": "1",
                                      "RDB_BENCH_MATERIALIZE": "1"})
                    annotated = output(["callgrind_annotate", "--inclusive=yes", "--tree=both",
                                        "--show=Ir,Dr,Dw", "--show-percs=no", "--threshold=100",
                                        "--auto=no", str(raw)])
                    destination.with_suffix(".annotated.txt").write_text(annotated)
                    with raw.open("rb") as source, gzip.open(str(raw) + ".gz", "wb") as dest:
                        shutil.copyfileobj(source, dest)
                    raw.unlink()
                    print(destination.name, flush=True)

    elif args.mode == "summary":
        spec = importlib.util.spec_from_file_location("h9_verdict", h9 / "verdict.py")
        verdict = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verdict)
        rows = []
        for label in ("offline", "paced"):
            source = root / label / "timing.tsv"
            if not source.exists():
                continue
            with source.open() as stream:
                raw = list(csv.DictReader(stream, delimiter="\t"))
            for family in FAMILIES:
                for q in (1, 2):
                    def series(profile):
                        return {int(r["block"]): float(r["median_ns"]) for r in raw
                                if r["family"] == family and int(r["q"]) == q
                                and r["profile"] == profile and int(r["block"]) > 0}
                    for numerator, denominator in (("DEFAULT", "NO_R1_FACTOR"),
                                                   ("NO_R2_CANON", "NO_R1_NO_R2"),
                                                   ("DEFAULT", "NO_R2_CANON"),
                                                   ("NO_R1_FACTOR", "NO_R1_NO_R2")):
                        a, b = series(numerator), series(denominator)
                        point, lo, hi = verdict.paired_bootstrap_ratio(a, b)
                        rows.append({"mode": label, "family": family, "q": q,
                                     "numerator": numerator, "denominator": denominator,
                                     "blocks": len(a), "numerator_ns": statistics.median(a.values()),
                                     "denominator_ns": statistics.median(b.values()),
                                     "ratio": float(point), "ci_low": float(lo), "ci_high": float(hi)})
        write_tsv(root / "summary.tsv", rows)

    elif args.mode == "analyze":
        metrics = []

        def collect(mode, family, q, profile, block, records):
            values = [int(r["compute_ns"]) for r in records]
            kept = records[max(30, len(values) // 10):]
            stable = [int(r["compute_ns"]) for r in kept]
            row = {"mode": mode, "family": family, "q": q, "profile": profile,
                   "block": block, "rows": len(values), "full_median_ns": statistics.median(values),
                   "median_ns": statistics.median(stable), "mean_ns": statistics.mean(stable),
                   "p99_ns": sorted(stable)[int(0.99 * len(stable))]}
            for phase in range(4):
                phase_values = [int(r["compute_ns"]) for r in kept if int(r["iter"]) % 4 == phase]
                row[f"phase{phase}_ns"] = statistics.median(phase_values)
            metrics.append(row)

        for source in sorted((root / "offline").glob("b*.csv.gz")):
            match = re.fullmatch(r"b(\d+)_(F9_R1|F9_X|F9_R2)_Q([12])_(.+)\.csv\.gz", source.name)
            block, family, q, profile = match.groups()
            if int(block) == 0:
                continue
            with gzip.open(source, "rt") as stream:
                collect("current_offline", family, int(q), profile, int(block), list(csv.DictReader(stream)))

        experiment = root.parent
        frozen = experiment / "results_20260814_K26v3/matrix/timing.tsv"
        with frozen.open() as stream:
            pinned = {(r["family"].replace("-", "_"), int(r["q"]), r["profile"], int(r["block"])):
                      int(r["compute_median_ns"]) for r in csv.DictReader(stream, delimiter="\t")}
        archives = {}
        for family in FAMILIES:
            archive = experiment / "artifacts/K26v3/k26v3_archives" / (
                "K26v3-P8-" + family.replace("_", "-") + ".tar.gz")
            archives[str(archive)] = sha(archive)
            with tarfile.open(archive, "r|gz") as tar:
                for member in tar:
                    match = re.search(r"/raw/block-(\d+)/q-([12])/order-\d+_(.+)/slot.csv$", member.name)
                    if not match:
                        continue
                    block, q, profile = match.groups()
                    assert profile in PROFILES, profile
                    text = tar.extractfile(member).read().decode()
                    records = list(csv.DictReader(io.StringIO(text)))
                    collect("K26v3_paced_RT", family, int(q), profile, int(block), records)
                    assert int(metrics[-1]["full_median_ns"]) == pinned[
                        family, int(q), profile, int(block)], member.name
            print("historical", family, flush=True)
        write_json(root / "historical-archives.json", archives)
        assert len(metrics) == 960, len(metrics)
        write_tsv(root / "slot-metrics.tsv", metrics)
        aggregates = []
        for mode in ("current_offline", "K26v3_paced_RT"):
            for family in FAMILIES:
                for q in (1, 2):
                    for profile in PROFILES:
                        selected = [r for r in metrics if r["mode"] == mode and r["family"] == family
                                    and r["q"] == q and r["profile"] == profile]
                        assert len(selected) == 20
                        row = {"mode": mode, "family": family, "q": q, "profile": profile}
                        for column in ("full_median_ns", "median_ns", "mean_ns", "p99_ns",
                                       "phase0_ns", "phase1_ns", "phase2_ns", "phase3_ns"):
                            row[column] = statistics.median(r[column] for r in selected)
                        aggregates.append(row)
        write_tsv(root / "phase-summary.tsv", aggregates)

        spec = importlib.util.spec_from_file_location("h9_verdict", h9 / "verdict.py")
        verdict = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verdict)
        comparisons = []
        for mode in ("current_offline", "K26v3_paced_RT"):
            for family in FAMILIES:
                for q in (1, 2):
                    for metric in ("full_median_ns", "median_ns", "mean_ns", "phase3_ns", "p99_ns"):
                        def series(profile):
                            return {r["block"]: r[metric] for r in metrics if r["mode"] == mode
                                    and r["family"] == family and r["q"] == q and r["profile"] == profile}
                        a, b = series("DEFAULT"), series("NO_R1_FACTOR")
                        point, lo, hi = verdict.paired_bootstrap_ratio(a, b)
                        comparisons.append({"mode": mode, "family": family, "q": q, "metric": metric,
                                            "ratio": float(point), "ci_low": float(lo), "ci_high": float(hi)})
        write_tsv(root / "metric-ratios.tsv", comparisons)

        controls, counters, capacities = {}, [], []
        for family in FAMILIES:
            for q in (1, 2):
                def listing(profile):
                    return root / "plans" / f"{family}_Q{q}_{profile}.out"
                for a, b in (("DEFAULT", "NO_R2_CANON"), ("NO_R1_FACTOR", "NO_R1_NO_R2")):
                    assert listing(a).read_bytes() == listing(b).read_bytes()
                    controls[f"{family}_Q{q}_{a}_equals_{b}"] = sha(listing(a))
                if family == "F9_R2":
                    assert listing("DEFAULT").read_bytes() == listing("NO_R1_FACTOR").read_bytes()
                for profile in PROFILES:
                    stem = root / "plans" / f"{family}_Q{q}_{profile}_runtime"
                    text = stem.with_suffix(".err").read_text()
                    numbers = {tag: list(map(int, re.findall(r"\d+", next(
                        line for line in text.splitlines() if line.startswith(tag + " ")))))
                        for tag in ("LOGICAL", "WORK", "MATERIALIZED")}
                    logical, work_counts, material = (numbers[k] for k in ("LOGICAL", "WORK", "MATERIALIZED"))
                    counters.append({"family": family, "q": q, "profile": profile,
                                     "substrate_appends": logical[0], "substrate_bytes": logical[2],
                                     "public_appends": logical[3], "public_bytes": logical[5],
                                     "disk_appends": material[0], "memory_appends": material[3],
                                     "eval_calls": work_counts[3], "eval_tokens": work_counts[4],
                                     "hash_picks": work_counts[5], "add_merges": work_counts[6]})
                    expected_counters = [line for line in text.splitlines()
                                         if line.startswith(("LOGICAL ", "WORK ", "MATERIALIZED "))]
                    for raw in (root / "offline").glob(f"b*_{family}_Q{q}_{profile}.err"):
                        actual = [line for line in raw.read_text().splitlines()
                                  if line.startswith(("LOGICAL ", "WORK ", "MATERIALIZED "))]
                        assert actual == expected_counters, raw
                    for line in stem.with_suffix(".out").read_text().splitlines():
                        match = re.fullmatch(r"\|\s*\d+\|\s*([^|]+)\|\s*(\d+)\|\s*([^|]+)\|", line)
                        if match:
                            capacities.append({"family": family, "q": q, "profile": profile,
                                               "stream": match[3].strip(), "interval": match[1].strip(),
                                               "required_history_cap": int(match[2])})
        write_json(root / "control-plans.json", controls)
        write_tsv(root / "runtime-counters.tsv", counters)
        write_tsv(root / "capacities.tsv", capacities)

        functions = []
        targets = ("dataModel::processRows(", "dataModel::constructInputPayload(", "dataModel::fetchForward(",
                   "rdb::storage::read(", "rdb::storage::revRead(", "rdb::storage::write(",
                   "rdb::payload::operator=(rdb::payload const&)", "rdb::memoryFile::read(",
                   "rdb::memoryFile::write(", "rdb::MetaIndexStore::overwriteLast(")
        for source in sorted((root / "callgrind").glob("*.annotated.txt")):
            for block in source.read_text().split("\n\n"):
                match = re.search(r"^\s*([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+\*\s+(.+?)\s+\[", block, re.M)
                if match and any(t in match[4] for t in targets):
                    functions.append({"cell": source.name.removesuffix(".annotated.txt"),
                                      "function": match[4].removeprefix("???:"),
                                      "calls": sum(int(n.replace(",", "")) for n in
                                                   re.findall(r"^\s*[\d,]+\s+[\d,]+\s+[\d,]+\s+< .*\(([\d,]+)x\)",
                                                              block, re.M)),
                                      "Ir": int(match[1].replace(",", "")),
                                      "Dr": int(match[2].replace(",", "")),
                                      "Dw": int(match[3].replace(",", ""))})
        for row in functions:
            if row["function"].startswith("dataModel::processRows("):
                assert row["calls"] == (2999 if row["cell"].startswith("F9_R2") else 5999), row
        write_tsv(root / "callgrind-functions.tsv", functions)


if __name__ == "__main__":
    main()
