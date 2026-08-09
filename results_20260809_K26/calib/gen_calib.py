#!/usr/bin/env python3
"""Plany kalibracyjne P7 — zamrożony plan przeskalowany wspólnym czynnikiem.

Co ten skrypt robi
------------------
Bierze ZAMROŻONY plan `rql/<RODZINA>_Q32.rql` i produkuje jego wariant, w którym
KAŻDY interwał `DECLARE` jest pomnożony przez ten sam czynnik `rate_scale`.
Niczego innego nie zmienia: program pól, kolejność monitorów, stałe przesunięć
`>2`, `>1`, `>3` oraz `STORAGE`/`SUBSTRAT` przechodzą znak w znak.

Dlaczego wolno to zrobić, skoro `rql/` jest zamrożone
-----------------------------------------------------
Plików w `rql/` skrypt NIE ZAPISUJE — czyta je i wypisuje nowe pliki do
`calib/plans/`. `manifest.sha256` pozostaje zgodny. PREDEKLARACJA §0.2 mówi
wprost, że predeklaracja zamraża PROTOKÓŁ kalibracji, a wartość rate wchodzi
jako ANEKS-1; §8.1 mówi, że kalibracja „skaluje WSZYSTKIE interwały wspólnym
czynnikiem, zachowując ich stosunki — stałe i=2, k=1, >3 pozostają
nienaruszone". Skalowanie wyłącznie `DECLARE` realizuje jedno i drugie: stosunek
Δ_A/Δ_B jest zachowany z definicji, a stałe przesunięć są w treści `SELECT`,
której skrypt nie dotyka. Relacja i·Δ_A = k·Δ_B przeżywa skalowanie obu stron
tym samym czynnikiem.

Dane: `data/calib/` (ziarno 20260809_2602, 600/300 rekordów) — OSOBNE od danych
głównych, bo §10 zabrania kalibrować na danych, które potem liczą metrykę.

Bramka własna: `--check` sprawdza, że przy `rate_scale=1` wynik jest IDENTYCZNY
z plikiem zamrożonym. Skrypt, który tego nie umie, mógłby po cichu zmieniać plan
razem z rate'em.
"""

import argparse
import re
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE.parent

FAMILIES = ["F9_R2", "F9_R1", "F9_X"]

#: Ile iteracji pętli, żeby źródła oddały komplet rekordów kalibracyjnych.
#: Dane kalibracyjne są 5x krótsze od głównych (600/300 wobec 3000/1500), więc
#: przelicznik jest tym samym, co zmierzony w P6, podzielonym przez 5.
#: `-m` jest limitem ITERACJI PĘTLI, nie licznikiem rekordów, i NIE zależy od
#: rate'u: przeskalowanie osi czasu zmienia długość przebiegu w sekundach,
#: a nie liczbę slotów.
SLOTS = {"F9_R2": 600, "F9_R1": 1200, "F9_X": 1200}

DECLARE = re.compile(
    r"^(DECLARE\s+[A-Za-z_][A-Za-z0-9_]*\s+INTEGER\s+STREAM\s+\w+,\s*)"
    r"(\d+/\d+)(\s*)(FILE\s+'.*')\s*$"
)


def scale_plan(text, scale):
    """Zwraca plan z interwałami `DECLARE` pomnożonymi przez `scale`."""
    out, touched = [], 0
    for line in text.splitlines():
        m = DECLARE.match(line)
        if not m:
            out.append(line)
            continue
        head, interval, gap, tail = m.groups()
        value = Fraction(interval) * scale
        # Szerokość pola zachowana, żeby diff wobec zamrożonego pliku pokazywał
        # wyłącznie zmianę liczby, a nie przesunięcie kolumn.
        new = f"{value.numerator}/{value.denominator}"
        out.append(f"{head}{new}{' ' * max(1, len(interval) + len(gap) - len(new))}{tail}")
        touched += 1
    if touched == 0:
        raise SystemExit("BLAD: plan nie zawiera ani jednego DECLARE — zly plik wejsciowy")
    return "\n".join(out) + "\n", touched


def source_paths(text):
    """Nazwy plików źródeł wymienione w planie."""
    return re.findall(r"FILE\s+'([^']+)'", text)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scale", help="czynnik skalujacy jako ulamek, np. 1/2, 1, 3, 5/2")
    parser.add_argument("--out", default=str(HERE / "plans"), help="katalog wynikowy")
    parser.add_argument("--check", action="store_true",
                        help="bramka: przy scale=1 wynik musi byc IDENTYCZNY z plikiem zamrozonym")
    args = parser.parse_args()

    if args.check:
        bad = []
        for family in FAMILIES:
            frozen = (CAMPAIGN / "rql" / f"{family}_Q32.rql").read_text()
            produced, touched = scale_plan(frozen, Fraction(1))
            status = "zgodny" if produced == frozen else "ROZNI SIE"
            print(f"  {family}_Q32  scale=1  DECLARE przeskalowanych: {touched}  -> {status}")
            if produced != frozen:
                bad.append(family)
        if bad:
            print(f"BLAD: przy scale=1 plan zmienil sie dla: {', '.join(bad)}", file=sys.stderr)
            return 1
        print("OK: przy scale=1 generator oddaje zamrozony plan znak w znak")
        return 0

    if not args.scale:
        parser.error("podaj --scale albo --check")
    scale = Fraction(args.scale)
    if scale <= 0:
        parser.error("scale musi byc dodatnie")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tag = f"{scale.numerator}_{scale.denominator}"
    for family in FAMILIES:
        frozen = (CAMPAIGN / "rql" / f"{family}_Q32.rql").read_text()
        produced, _ = scale_plan(frozen, scale)
        target = out / f"{family}_Q32_s{tag}.rql"
        target.write_text(produced)
        print(f"  {target.name}  slots={SLOTS[family]}  zrodla={','.join(sorted(set(source_paths(produced))))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
