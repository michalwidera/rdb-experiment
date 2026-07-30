#!/usr/bin/env python3
"""Diagnostyka W4 po nieudanej kalibracji K6.0 — NIE jest danymi kampanii.

Pytanie: czy ~35 ms w `W4_Q32` to koszt liniowy w Q i staly co-slot (wtedy to
wlasciwosc obciazenia: okno `@(1,30)` liczy sie w probkach, nie w czasie, wiec
zwolnienie rate'u nie zmniejsza pracy na slot), czy artefakt ogona (mediana
mala, p99 duze — wtedy szukamy przyczyny outlierow).
"""
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/home/michal/rdb-experiment/results_20260730_K6")
import calibrate  # noqa: E402

CODE_REPO = Path("/home/michal/retractordb")
WORKLOADS = Path("/dev/shm/k6-diag/workloads")
CASES = ["W4_Q01", "W4_Q08", "W4_Q32", "W2_Q32"]
PROFILE = "STRUCT"
SLOTS = 1200
SCALE = 6

if WORKLOADS.exists():
    subprocess.run(["rm", "-rf", str(WORKLOADS)], check=True)
subprocess.run(
    [sys.executable, "/home/michal/rdb-experiment/results_20260730_K6/generate.py",
     "--output", str(WORKLOADS), "--scale", str(SCALE)],
    check=True, capture_output=True,
)

binary = CODE_REPO / f"build/K6-{PROFILE}/src/retractor/xretractor"
slot_ms = 1000.0 / (15 * SCALE)
print(f"profil {PROFILE}, scale={SCALE} (slot {slot_ms:.2f} ms), {SLOTS} slotow, 1 powtorzenie")
print(f"{'przypadek':<10} {'mediana':>10} {'p99':>10} {'max':>10} {'p99/mediana':>12} {'slotow':>7}")
for case in CASES:
    case_dir = WORKLOADS / case
    if not case_dir.is_dir():
        print(f"{case:<10} BRAK KATALOGU")
        continue
    r = calibrate.run_once(binary, case_dir, SLOTS)
    ratio = r["p99_ns"] / r["median_ns"] if r["median_ns"] else 0
    print(f"{case:<10} {r['median_ns']/1e6:>9.2f}m {r['p99_ns']/1e6:>9.2f}m "
          f"{r['max_ns']/1e6:>9.2f}m {ratio:>12.2f} {int(r['slots']):>7}")
