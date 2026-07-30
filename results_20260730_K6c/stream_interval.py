#!/usr/bin/env python3
"""Rzeczywisty interwał strumienia mierzonego — pytamy o niego SILNIK.

Powód istnienia tego pliku jest wprost ustaleniem z K6b. Predeklaracje v1 i v2
wyliczały `slot(phi)` arytmetycznie, jako interwał przeplotu **dwóch** strumieni
`A#B`, czyli `1/(15·s)`. Dla rodzin, których strumień wyjściowy jest głębszym
zagnieżdżeniem, to jest po prostu nieprawda — przeplot **sumuje częstotliwości**,
więc każdy kolejny poziom zagęszcza slot:

    W2_Q32  s=24   wyliczone 1/360   silnik 1/360    zgodne
    W3_d1   s=24   wyliczone 1/360   silnik 1/360    zgodne
    W3_d3   s=24   wyliczone 1/360   silnik 1/810    2,25x gestszy
    W8      mon_j  zalozone 1/360    silnik 1/720    2x gestszy

Skutek w K6b: `W3_d3` przeszła regułę „`p99 <= 0,5 · slot`" (1122 µs wobec
budżetu 1389 µs), choć wobec **prawdziwego** slotu 1235 µs pracowała na 91 %
i była praktycznie nasycona — czyli dokładnie w reżimie, którego ta reguła
zakazuje. Drugi skutek: przebiegi trwały ~3,5 s zamiast zaplanowanych 8 s.

Wniosek metodologiczny, ten sam co po v1: **wielkości, które system zna, należy
z systemu odczytywać, a nie odtwarzać rachunkiem obok niego.** Interwał każdego
strumienia jest znany w czasie kompilacji i silnik go publikuje (`xqry -t`).
Rachunek w generatorze był kopią tej wiedzy, która rozjechała się z oryginałem.
"""
import re
import shutil
import subprocess
import time
from fractions import Fraction
from pathlib import Path

# Ile czekamy, aż serwer wystartuje i odpowie na pytanie o strumień. Kompilacja
# głębokich planów (W3_d3, W8_Q32) trwa zauważalnie dłużej niż płytkich.
STARTUP_POLL_INTERVAL_S = 0.5
STARTUP_MAX_POLLS = 40

# Budżet przebiegu pomocniczego. Musi wystarczyć na start serwera i odpowiedź,
# a poza tym nie ma znaczenia — z tego przebiegu nie bierzemy żadnej metryki.
PROBE_SLOTS = 20000

DELTA_RE = re.compile(r"^\s*delta:\s*(\d+)\s*/\s*(\d+)\s*$", re.MULTILINE)


def _xqry_binary() -> str:
    found = shutil.which("xqry")
    if found is None:
        raise SystemExit("xqry nie jest na PATH — nie da się zapytać silnika o interwał strumienia")
    return found


def measure_interval(engine: Path, work_dir: Path, stream: str) -> Fraction:
    """Interwał strumienia `stream` wg silnika, jako ułamek sekundy.

    `work_dir` musi być gotowym katalogiem przebiegu (query.rql + dane + temp/).
    Uruchamiamy serwer, pytamy `xqry -t <stream>` i czytamy pole `delta`.
    Z tego przebiegu nie bierzemy ŻADNEJ metryki czasowej — służy wyłącznie
    odczytaniu wielkości, którą silnik zna z kompilacji.
    """
    xqry = _xqry_binary()
    engine_process = subprocess.Popen(
        [str(engine), "query.rql", "-r", "-k", "-m", str(PROBE_SLOTS)],
        cwd=work_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    try:
        for _ in range(STARTUP_MAX_POLLS):
            time.sleep(STARTUP_POLL_INTERVAL_S)
            if engine_process.poll() is not None:
                raise SystemExit(f"silnik zakończył się przed odpowiedzią o strumień {stream}")
            completed = subprocess.run(
                [xqry, "-t", stream],
                cwd=work_dir,
                capture_output=True,
                text=True,
                errors="replace",
                stdin=subprocess.DEVNULL,
                check=False,
            )
            match = DELTA_RE.search(completed.stdout)
            if match:
                return Fraction(int(match.group(1)), int(match.group(2)))
        raise SystemExit(f"silnik nie podał interwału strumienia {stream} w wyznaczonym czasie")
    finally:
        engine_process.terminate()
        try:
            engine_process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            engine_process.kill()
            engine_process.wait()


def parse_delta(text: str) -> Fraction | None:
    """Wyłuskanie `delta: n/d` z wyjścia `xqry -t`. Wydzielone, żeby dało się
    sprawdzić parsowanie bez uruchamiania silnika."""
    match = DELTA_RE.search(text)
    if not match:
        return None
    return Fraction(int(match.group(1)), int(match.group(2)))


def slots_for(interval: Fraction, run_seconds: int, slots_min: int, slots_max: int) -> int:
    """Budżet przebiegu wobec RZECZYWISTEGO slotu.

    Ta sama postać co w v2 (`clamp(round(run_seconds / slot), min, max)`), tyle że
    `slot` pochodzi teraz z silnika. W K6b `W3_d3` dostawała przez to 2880 slotów
    „na 8 sekund", które w rzeczywistości trwały 3,5 s.
    """
    return max(slots_min, min(slots_max, round(run_seconds / float(interval))))
