#!/usr/bin/env python3
"""Zestawienie kampanii 360 Hz: K18 (rewizja wadliwa) vs extend (po poprawce).

Czyta raporty obu badan i wypisuje tabele porownawcza na stdout.
Uruchomienie z korzenia repozytorium wynikow:

    python3 results_20260728_extend/rate_extend/compare_k18.py \
      > results_20260728_extend/rate_extend/comparison_k18.md
"""

import re
import sys
from pathlib import Path

OLD = "results_20260728_K18/rate_k18/study_01/results.md"
NEW = "results_20260728_extend/rate_extend/study_01/results.md"

METRICS = [
    ("E1/mediana", "E1 mediana [us]"),
    ("E1/p99", "E1 p99 [us]"),
    ("E1/max", "E1 max [us]"),
    ("E2E/mediana", "queue-emission mediana [us]"),
    ("E2E/p99", "queue-emission p99 [us]"),
    ("E2E/p99,9", "queue-emission p99,9 [us]"),
    ("E2E/max", "queue-emission max [us]"),
    ("wake/mediana", "wake_lag mediana [us]"),
    ("wake/max", "wake_lag max [us]"),
]


def grab(path: str) -> dict[str, float]:
    values: dict[str, float] = {}
    section = None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("--- E1"):
            section = "E1"
        elif line.startswith("--- E2E"):
            section = "E2E"
        elif line.startswith("--- jitter"):
            section = "wake"
        matched = re.match(r"^(mediana|p99|p99,9|max)\s*:\s*([\d.]+)", line.strip())
        if matched and section:
            values[f"{section}/{matched.group(1)}"] = float(matched.group(2))
    return values


def main() -> int:
    old, new = grab(OLD), grab(NEW)

    print("# Porównanie kampanii 360 Hz: K18 (rewizja wadliwa) vs extend (po poprawce)\n")
    print("- K18 `study_01`: commit `bc37186`, 2026-07-28T15:06:54")
    print("- extend `study_01`: commit `3db7817`, 2026-07-28T21:00:04")
    print("- identyczna konfiguracja: `rate_hz=360, clients=1, samples=20000, sink=null`;")
    print("  plik konfiguracji ma ten sam SHA-256 co w K18")
    print("  (`69f82adac208cd1d3c05f8ef5d8eb5f01de220a774f9a9842a256bbe8d0eafaf`)\n")
    print("| Metryka | K18 (bc37186) | extend (3db7817) | zmiana |")
    print("|---|---:|---:|---:|")
    for key, label in METRICS:
        if key in old and key in new:
            delta = (new[key] - old[key]) / old[key] * 100
            print(f"| {label} | {old[key]:.1f} | {new[key]:.1f} | {delta:+.1f}% |")

    print("""
## Interpretacja

Poprawka zwiększa o jeden rekord pojemność bufora `MEMORY` każdego źródła okna
AGSE — w tym potoku dotyczy to czterech strumieni po 4 bajty na rekord. Liczba
odczytów okna na slot się nie zmienia, a arytmetyka nie zależy od wartości
danych, więc oczekiwaną zmianą metryk było zero.

Wszystkie metryki opóźnienia mieszczą się w ±2 %. Wyjątkiem jest maksimum
jitteru pobudki (+34,6 %, 54,3 → 73,1 us): to pojedynczy outlier planisty,
nieskorelowany z treścią poprawki i o dwa rzędy wielkości mniejszy od budżetu
slotu.

Żadnej z tych różnic **nie należy czytać jako efektu poprawki**. Każda kampania
to jedno badanie 20 000 interwałów, bez powtórzeń, więc nie ma podstawy do
oddzielenia efektu od zmienności międzyprzebiegowej. Wniosek, który dane
uprawniają, jest słabszy i wystarczający: poprawka nie zmieniła rzędu wielkości
ani marginesu budżetu slotu — potok nadal mieści się w budżecie 2777,8 us
z zapasem około 30 %.

Istotna różnica jakościowa nie jest widoczna w metrykach czasowych: kampania K18
mierzyła potok, który liczył `mwi ≡ 0`, czyli z martwą detekcją QRS. Kampania
extend mierzy ten sam potok liczący poprawnie. Praca procesora jest ta sama, ale
twierdzenie „potok detekcji QRS mieści się w 360 Hz" ma pokrycie w danych dopiero
w tej drugiej kampanii.""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
