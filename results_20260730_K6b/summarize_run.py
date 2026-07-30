#!/usr/bin/env python3
"""Podsumowanie jednego przebiegu K6 — jeden wiersz `runs.csv`.

Czyta wszystko, co jedno uruchomienie `xretractor` wytworzyło:

- `e1_probe.csv` — sonda E1: `compute_ns`, `wake_lag_ns`, `e2e_ns`;
- `xretractor.log` — `PLAN bench`, `REWRITE_APPLIED`, `COMPILE_NS`,
  `PLAN capacity`, `MATERIALIZED`;
- `process.txt` — `VmHWM` i takty CPU zebrane przez próbnik `/proc`;
- `temp/` — artefakty strumieni, z których liczony jest checksum wyniku.

Pierwsze `WARMUP_FRACTION` slotów jest odrzucane jako transjent startowy.
Wartość jest tu, w kodzie, a nie w wywołaniu — nie wolno jej wybrać po
zobaczeniu danych.

Checksum wyniku obejmuje **wyłącznie strumienie nazwane przez użytkownika**
(źródła `DECLARE` i wyjścia `SELECT`). Substraty są wyłączone, bo ich nazwy
generuje kompilator i to właśnie ich zmiana JEST optymalizacją — checksum
obejmujący substraty rozjeżdżałby się między profilami z definicji i kontrola
poprawności wyniku byłaby zawsze negatywna. To ta sama granica, którą przyjęła
kontrola semantyczna K5.

Ignorowane są dodatkowo: ośmiobajtowy nagłówek `.meta` (znacznik czasu
utworzenia) oraz pole `RETMEMORY` w `.desc` — oba wyłączone imiennie już w K5.
"""
import argparse
import hashlib
import re
import statistics
from pathlib import Path

WARMUP_FRACTION = 0.05

PLAN_RE = re.compile(
    r"^PLAN bench \(publiczne/substraty/tokeny-from/tokeny-pol, dedup=(?:ON|OFF)\): "
    r"wejscie=(?:\d+)/(?:\d+)/(?:\d+)/(?:\d+)\s+"
    r"przed-dedup=(?:\d+)/(?:\d+)/(?:\d+)/(?:\d+)\s+"
    r"po-dedup=(?:\d+)/(?:\d+)/(?:\d+)/(?:\d+)\s+"
    r"wyjscie=(\d+)/(\d+)/(\d+)/(\d+)$",
    re.MULTILINE,
)
COUNTER_RE = re.compile(r"^REWRITE_APPLIED r1=(\d+) r2=(\d+)$", re.MULTILINE)
COMPILE_RE = re.compile(r"^COMPILE_NS (\d+) sonda=(\d+)$", re.MULTILINE)
CAPACITY_RE = re.compile(r"^PLAN capacity: strumieni=(\d+) suma=(\d+) maks=(-?\d+)$", re.MULTILINE)
MATERIALIZED_RE = re.compile(
    r"^MATERIALIZED trwale: dopisania=(\d+) nadpisania=(\d+) bajty=(\d+)\s+"
    r"pamieciowe: dopisania=(\d+) nadpisania=(\d+) bajty=(\d+)$",
    re.MULTILINE,
)
RETMEMORY_RE = re.compile(rb"^\s*RETMEMORY\s+\d+\s*$", re.MULTILINE)
STREAM_NAME_RE = re.compile(r"\bSTREAM\s+([A-Za-z_]\w*)")


def percentile(values: list[int], fraction: float) -> int:
    """Percentyl typu „najbliższa pozycja", bez interpolacji."""
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


def read_probe(path: Path) -> dict[str, int]:
    compute: list[int] = []
    wake: list[int] = []
    e2e: list[int] = []
    with path.open(encoding="utf-8") as handle:
        header = handle.readline().strip()
        if header != "iter,compute_ns,wake_lag_ns,e2e_ns":
            raise SystemExit(f"nieoczekiwany nagłówek sondy: {header}")
        for line in handle:
            parts = line.strip().split(",")
            if len(parts) != 4:
                continue
            compute.append(int(parts[1]))
            wake.append(int(parts[2]))
            e2e.append(int(parts[3]))
    if not compute:
        raise SystemExit("sonda nie zawiera żadnego slotu")
    skip = int(len(compute) * WARMUP_FRACTION)
    compute, wake, e2e = compute[skip:], wake[skip:], e2e[skip:]
    if not compute:
        raise SystemExit("po odrzuceniu transjentu nie został żaden slot")
    return {
        "slots": len(compute),
        "compute_median_ns": int(statistics.median(compute)),
        "compute_p99_ns": percentile(compute, 0.99),
        "compute_max_ns": max(compute),
        "compute_sum_ns": sum(compute),
        "wake_p999_ns": percentile(wake, 0.999),
        "e2e_p50_ns": percentile(e2e, 0.50),
        "e2e_p99_ns": percentile(e2e, 0.99),
        "e2e_p999_ns": percentile(e2e, 0.999),
        "e2e_max_ns": max(e2e),
    }


def read_log(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    plan = PLAN_RE.findall(text)
    counters = COUNTER_RE.findall(text)
    compile_ns = COMPILE_RE.findall(text)
    capacity = CAPACITY_RE.findall(text)
    materialized = MATERIALIZED_RE.findall(text)
    missing = [
        name
        for name, found in (
            ("PLAN bench", plan),
            ("REWRITE_APPLIED", counters),
            ("COMPILE_NS", compile_ns),
            ("PLAN capacity", capacity),
            ("MATERIALIZED", materialized),
        )
        if len(found) != 1
    ]
    if missing:
        raise SystemExit(f"brak lub duplikat instrumentu: {', '.join(missing)}")
    return {
        "nodes_public": int(plan[0][0]),
        "nodes_substrates": int(plan[0][1]),
        "tokens_from": int(plan[0][2]),
        "tokens_fields": int(plan[0][3]),
        "r1": int(counters[0][0]),
        "r2": int(counters[0][1]),
        "compile_ns": int(compile_ns[0][0]),
        "probe_ns": int(compile_ns[0][1]),
        "capacity_streams": int(capacity[0][0]),
        "capacity_sum": int(capacity[0][1]),
        "capacity_max": int(capacity[0][2]),
        "mat_bytes": int(materialized[0][2]),
        "mat_mem_bytes": int(materialized[0][5]),
    }


def read_process(path: Path) -> dict[str, int]:
    values = {"vmhwm_kb": 0, "utime_ticks": 0, "stime_ticks": 0}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                if key in values and value.strip().isdigit():
                    values[key] = int(value.strip())
    return {"vmhwm_kb": values["vmhwm_kb"], "cpu_ticks": values["utime_ticks"] + values["stime_ticks"]}


def normalize_artifact(path: Path) -> bytes:
    """Bajty artefaktu bez pól celowo niedeterministycznych lub nieobserwowalnych."""
    payload = path.read_bytes()
    if path.suffix == ".meta":
        # Ośmiobajtowy nagłówek zawiera znacznik czasu utworzenia.
        return payload[8:]
    if path.suffix == ".desc":
        # RETMEMORY to pojemność historii; K5 wyłączył ją z kryterium imiennie.
        return RETMEMORY_RE.sub(b"RETMEMORY <pominiete>", payload)
    return payload


def user_named_streams(query: Path) -> set[str]:
    """Strumienie nazwane przez autora zapytania — źródła DECLARE i wyjścia SELECT."""
    return set(STREAM_NAME_RE.findall(query.read_text(encoding="utf-8")))


def checksum_artifacts(root: Path, streams: set[str]) -> tuple[str, int]:
    """Checksum wyniku: artefakty strumieni użytkownika, w kolejności nazw."""
    digest = hashlib.sha256()
    count = 0
    if root.is_dir():
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            # Nazwa strumienia to nazwa pliku bez rozszerzenia artefaktu.
            stem = path.name.split(".")[0]
            if stem not in streams:
                continue
            payload = normalize_artifact(path)
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(str(len(payload)).encode("utf-8"))
            digest.update(payload)
            count += 1
    return digest.hexdigest(), count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--rep", type=int, required=True)
    parser.add_argument("--samples", type=int, required=True)
    # Rate jest w K6b zmienną kampanii (per rodzina), nie stałą. Zapisujemy go
    # przy KAŻDYM przebiegu, bo warunek unieważniający nr 6 wymaga sprawdzenia,
    # że w obrębie komórki jest identyczny dla wszystkich profili.
    parser.add_argument("--scale", required=True, help="mnożnik rate'u albo '-' dla rate'u ze źródła")
    parser.add_argument("--f-phi-hz", required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--wall-ms", type=int, required=True)
    parser.add_argument("--append", type=Path, required=True)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    probe = read_probe(run_dir / "e1_probe.csv")
    log = read_log(run_dir / "xretractor.log")
    process = read_process(run_dir / "process.txt")
    streams = user_named_streams(run_dir / "query.rql")
    artifacts_sha, artifact_count = checksum_artifacts(run_dir / "temp", streams)

    # Reguła zliczania: przebieg bez artefaktów nie jest przebiegiem zgodnym,
    # jest przebiegiem bez danych. Zero porównywalnych rzeczy to błąd.
    if artifact_count == 0:
        raise SystemExit("przebieg nie wytworzył ani jednego artefaktu strumienia użytkownika")

    row = [
        args.case,
        args.profile,
        str(args.rep),
        args.scale,
        args.f_phi_hz,
        str(probe["slots"]),
        str(args.exit_code),
        str(probe["compute_median_ns"]),
        str(probe["compute_p99_ns"]),
        str(probe["compute_max_ns"]),
        str(probe["compute_sum_ns"]),
        str(probe["wake_p999_ns"]),
        str(probe["e2e_p50_ns"]),
        str(probe["e2e_p99_ns"]),
        str(probe["e2e_p999_ns"]),
        str(probe["e2e_max_ns"]),
        str(process["vmhwm_kb"]),
        str(process["cpu_ticks"]),
        str(log["compile_ns"]),
        str(log["probe_ns"]),
        str(log["r1"]),
        str(log["r2"]),
        str(log["nodes_public"]),
        str(log["nodes_substrates"]),
        str(log["tokens_from"]),
        str(log["tokens_fields"]),
        str(log["capacity_streams"]),
        str(log["capacity_sum"]),
        str(log["capacity_max"]),
        str(log["mat_bytes"]),
        str(log["mat_mem_bytes"]),
        artifacts_sha,
        str(artifact_count),
        str(args.wall_ms),
    ]
    with args.append.open("a", encoding="utf-8") as handle:
        handle.write(",".join(row) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
