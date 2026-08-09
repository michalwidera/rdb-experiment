#!/usr/bin/env python3
"""Weryfikacja kandydata legalnej rodziny F9-X po K23.

Skrypt nie dotyka zamrozonego katalogu K23. Tworzy deterministyczne dane i
artefakty w katalogu tymczasowym, a nastepnie sprawdza:

* odrzucenie historycznego, nielegalnego odwolania A[0]...D[0] przez #;
* zdolnosc bramki do odroznienia legalnego, lecz niedzielonego programu mN[*];
* plan 2x2 R1 x R2 w czterech profilach;
* identycznosc ośmiu publicznych wynikow i niezalezny oracle wartosci;
* deskryptor oraz brak NULL/luk oczami xtrdb.
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent
QUERY = HERE / "F9_X_Q8.rql"
CODE_REPO = HERE.parent.parent / "retractordb"

FAST_COUNT = 1500
SLOW_COUNT = 750
LOOP_LIMIT = 3000
MIN_WINDOW = 2000

PROFILE_EXPECTATIONS = {
    "DEFAULT": {
        "commutative": "ON",
        "factor": "ON",
        "select": 1,
        "hash": 4,
        "timemove": 0,
    },
    "NO_R2_CANON": {
        "commutative": "OFF",
        "factor": "ON",
        "select": 2,
        "hash": 4,
        "timemove": 0,
    },
    "NO_R1_FACTOR": {
        "commutative": "ON",
        "factor": "OFF",
        "select": 2,
        "hash": 4,
        "timemove": 6,
    },
    "NO_R1_NO_R2": {
        "commutative": "OFF",
        "factor": "OFF",
        "select": 4,
        "hash": 4,
        "timemove": 6,
    },
}


class VerificationError(RuntimeError):
    pass


def run(command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise VerificationError(
            f"polecenie zakonczylo sie kodem {result.returncode}: {' '.join(command)}\n{output}"
        )
    return output


def compile_query(binary: Path, query: Path) -> str:
    output = run([str(binary), "-c", str(query)])
    if "Check result:" in output:
        raise VerificationError(f"zapytanie {query.name} zostalo odrzucone:\n{output}")
    if ":STORAGE" not in output:
        raise VerificationError(f"zapytanie {query.name} nie zwrocilo planu")
    return output


def expect_compile_rejection(binary: Path, query: Path, fragment: str) -> None:
    result = subprocess.run([str(binary), "-c", str(query)], text=True, capture_output=True)
    output = result.stdout + result.stderr
    if result.returncode == 0 or "Check result:" not in output or fragment not in output:
        raise VerificationError(
            f"mutant {query.name} nie zostal odrzucony niezerowym kodem i oczekiwanym "
            f"komunikatem {fragment!r}: kod={result.returncode}\n{output}"
        )


def plan_counts(plan: str) -> dict[str, int]:
    return {
        "select": len(re.findall(r"^STREAM_SELECT_", plan, re.MULTILINE)),
        "hash": len(re.findall(r"^STREAM_HASH_", plan, re.MULTILINE)),
        "timemove": len(re.findall(r"^STREAM_TIMEMOVE_", plan, re.MULTILINE)),
    }


def profile_binary(code_repo: Path, profile: str) -> Path:
    return code_repo / "build" / f"K23-{profile}" / "src" / "retractor" / "xretractor"


def check_profiles(code_repo: Path) -> Path:
    default_binary = None
    for profile, expected in PROFILE_EXPECTATIONS.items():
        binary = profile_binary(code_repo, profile)
        if not binary.is_file():
            raise VerificationError(
                f"brak binarki profilu {profile}: {binary}; zbuduj profile przez "
                "results_20260808_K23v2/build_profiles.sh"
            )
        info = run([str(binary), "--build-info"])
        required = {
            f"RDB_OPT_COMMUTATIVE_ADD={expected['commutative']}",
            f"RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES={expected['factor']}",
        }
        missing = sorted(item for item in required if item not in info)
        if missing:
            raise VerificationError(f"profil {profile} ma zla konfiguracje: brak {missing}")
        counts = plan_counts(compile_query(binary, QUERY))
        wanted = {key: expected[key] for key in ("select", "hash", "timemove")}
        if counts != wanted:
            raise VerificationError(f"profil {profile}: plan {counts}, oczekiwano {wanted}")
        print(f"ok  profil {profile:<13} plan={counts}")
        if profile == "DEFAULT":
            default_binary = binary
    assert default_binary is not None
    return default_binary


def write_mutants(work: Path) -> tuple[Path, Path]:
    source = QUERY.read_text(encoding="utf-8")
    illegal = re.sub(
        r"Sqrt\(front\*front\+rear\*rear\)",
        "Sqrt(A[0]*C[0]+B[0]*D[0])",
        source,
    )
    illegal_path = work / "mutant_illegal_constituents.rql"
    illegal_path.write_text(illegal, encoding="utf-8")

    own_lines = []
    for line in source.splitlines():
        match = re.match(r"SELECT Sqrt\(front\*front\+rear\*rear\) STREAM (m\d+) (.*)", line)
        if match:
            monitor, rest = match.groups()
            line = (
                f"SELECT Sqrt({monitor}[0]*{monitor}[0]+{monitor}[1]*{monitor}[1]) "
                f"STREAM {monitor} {rest}"
            )
        own_lines.append(line)
    own_path = work / "mutant_own_stream.rql"
    own_path.write_text("\n".join(own_lines) + "\n", encoding="utf-8")
    return illegal_path, own_path


def check_mutants(default_binary: Path, work: Path) -> None:
    illegal, own = write_mutants(work)
    expect_compile_rejection(default_binary, illegal, "constituent of an interleave")
    print("ok  mutant odwolania A[0]...D[0] odrzucony przez bramke F9/S3")

    own_counts = plan_counts(compile_query(default_binary, own))
    if own_counts["select"] == PROFILE_EXPECTATIONS["DEFAULT"]["select"]:
        raise VerificationError(
            "mutant z odwolaniem mN[*] zachowal wspoldzielenie R2; bramka nie odroznia wariantu obalonego"
        )
    if own_counts["select"] != 0:
        raise VerificationError(f"mutant mN[*]: oczekiwano select=0, otrzymano {own_counts}")
    print("ok  mutant mN[*] legalny, ale traci R2 (select=0) - odrzucony jako projekt rodziny")


def series(count: int, multiplier: int, offset: int, modulus: int) -> list[int]:
    return [((multiplier * i + offset) % modulus) + 1 for i in range(count)]


def write_series(path: Path, values: list[int]) -> None:
    path.write_text("".join(f"{value}\n" for value in values), encoding="ascii")


def interleave(fast: list[int], slow: list[int]) -> list[int]:
    """Przeplot dla delt 1/100 i 1/50: B0,A0,A1,B1,A2,A3,..."""
    result = []
    fast_index = 0
    slow_index = 0
    slot = 0
    while fast_index < len(fast) or slow_index < len(slow):
        if slot % 3 == 0:
            if slow_index >= len(slow):
                break
            result.append(slow[slow_index])
            slow_index += 1
        else:
            if fast_index >= len(fast):
                break
            result.append(fast[fast_index])
            fast_index += 1
        slot += 1
    return result


def read_integers(path: Path) -> list[int]:
    raw = path.read_bytes()
    if len(raw) % 4:
        raise VerificationError(f"{path}: rozmiar {len(raw)} nie dzieli sie przez INTEGER=4 B")
    return [value[0] for value in struct.iter_unpack("<i", raw)]


def normalized_descriptor(path: Path) -> str:
    return re.sub(r"m\d+_", "m_", path.read_text(encoding="utf-8", errors="replace"))


def null_gap_map(xtrdb: Path, artifact: Path) -> list[str]:
    output = run([str(xtrdb), "-n", "-s", str(artifact)])
    kept = []
    for line in output.splitlines():
        body = line.strip("│┌┐└┘├┤ \t")
        if re.search(r"(Segments|records|no nulls|nullfill|gap|partial)", body):
            if any(label in body for label in ("Legend", "DESCRIPTOR", "DATA", "META")):
                continue
            kept.append(re.sub(r"\s+", " ", body))
    return kept


def run_runtime(default_binary: Path, xtrdb: Path, work: Path) -> None:
    runtime = work / "runtime"
    runtime.mkdir()
    shutil.copy2(QUERY, runtime / QUERY.name)

    a = series(FAST_COUNT, 17, 3, 997)
    b = series(SLOW_COUNT, 29, 5, 991)
    c = series(FAST_COUNT, 37, 7, 983)
    d = series(SLOW_COUNT, 43, 11, 977)
    write_series(runtime / "front_vib.txt", a)
    write_series(runtime / "front_cur.txt", b)
    write_series(runtime / "rear_vib.txt", c)
    write_series(runtime / "rear_cur.txt", d)
    (runtime / "temp").mkdir()

    # Nazwa argv[0] wchodzi do nazwy locka uslugi. Symlink i PATH utrzymuja ja
    # jako proste `xretractor`, niezaleznie od polozenia profilu builda.
    bindir = runtime / "bin"
    bindir.mkdir()
    (bindir / "xretractor").symlink_to(default_binary.resolve())
    env = os.environ.copy()
    env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    run(["xretractor", QUERY.name, "-m", str(LOOP_LIMIT), "-r", "-k"], cwd=runtime, env=env)

    artifacts = [runtime / "temp" / f"m{i}" for i in range(1, 9)]
    records = [read_integers(path) for path in artifacts]
    if len(records[0]) < MIN_WINDOW:
        raise VerificationError(f"okno {len(records[0])}, wymagane >= {MIN_WINDOW}")
    for index, current in enumerate(records[1:], start=2):
        if current != records[0]:
            raise VerificationError(f"m{index} rozni sie od m1 na publicznym ciagu wartosci")

    front = interleave(a, b)
    rear = interleave(c, d)
    oracle = [math.isqrt(left * left + right * right) for left, right in zip(front, rear)]
    observed = records[0]
    if observed != oracle[: len(observed)]:
        mismatch = next(i for i, pair in enumerate(zip(observed, oracle)) if pair[0] != pair[1])
        raise VerificationError(
            f"oracle rozjechal sie w rekordzie {mismatch}: {observed[mismatch]} wobec {oracle[mismatch]}"
        )

    descriptor = normalized_descriptor(artifacts[0].with_suffix(".desc"))
    reference_map = null_gap_map(xtrdb, artifacts[0])
    for artifact in artifacts[1:]:
        if normalized_descriptor(artifact.with_suffix(".desc")) != descriptor:
            raise VerificationError(f"deskryptor {artifact.name} rozni sie od m1")
        if null_gap_map(xtrdb, artifact) != reference_map:
            raise VerificationError(f"mapa NULL/luk {artifact.name} rozni sie od m1")

    if not any("records, no nulls" in row for row in reference_map):
        raise VerificationError(f"xtrdb nie potwierdzil braku NULL/luk: {reference_map}")
    print(
        f"ok  runtime: 8/8 identycznych wynikow, {len(observed)} rekordow, "
        "oracle 100%, bez NULL/luk"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-repo", type=Path, default=CODE_REPO)
    parser.add_argument("--xtrdb", type=Path, default=Path(shutil.which("xtrdb") or ""))
    parser.add_argument("--skip-runtime", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    code_repo = args.code_repo.resolve()
    if not code_repo.is_dir():
        raise VerificationError(f"brak repozytorium silnika: {code_repo}")
    if not args.skip_runtime and not args.xtrdb.is_file():
        raise VerificationError("brak xtrdb; podaj --xtrdb /sciezka/do/xtrdb")

    with tempfile.TemporaryDirectory(prefix="f9x-redesign-") as temp:
        work = Path(temp)
        default_binary = check_profiles(code_repo)
        check_mutants(default_binary, work)
        if not args.skip_runtime:
            run_runtime(default_binary, args.xtrdb.resolve(), work)
    print("PASS: legalna rodzina F9-X zachowuje semantyke i uklad R1 x R2")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as error:
        raise SystemExit(f"FAIL: {error}") from error
