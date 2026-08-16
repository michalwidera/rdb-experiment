#!/usr/bin/env python3
"""Bramka reguly ANEKS-4 na przypadkach o znanej odpowiedzi.

Nie czyta zadnych danych kampanii. Sprawdza wylacznie, czy uzupelnienie
zdegenerowanej metryki zachowuje sie dokladnie tak, jak deklaruje ANEKS-4,
i czy nie zmienia zachowania w przypadku niezdegenerowanym.
"""

import sys
from fractions import Fraction

import verdict_aneks4 as V


def cell(substrate_bytes, public_appends):
    return {"substrate_bytes": substrate_bytes, "public_appends": public_appends}


def main():
    cases = [
        ("niezdegenerowany: 50% redukcji",
         lambda: V.reduction(cell(500, 100), cell(1000, 100)), Fraction(1, 2)),
        ("niezdegenerowany: brak redukcji",
         lambda: V.reduction(cell(1000, 100), cell(1000, 100)), Fraction(0)),
        ("niezdegenerowany: wzrost -> redukcja ujemna",
         lambda: V.reduction(cell(2000, 100), cell(1000, 100)), Fraction(-1)),
        ("ANEKS-4: zero po obu stronach -> redukcja 0",
         lambda: V.reduction(cell(0, 2999), cell(0, 2999)), Fraction(0)),
        ("ANEKS-4: zero tylko w odniesieniu -> BRAK WERDYKTU",
         lambda: V.reduction(cell(1, 2999), cell(0, 2999)), V.Problem),
        ("§10 bez zmian: zerowy mianownik DEFAULT -> BRAK WERDYKTU",
         lambda: V.reduction(cell(0, 0), cell(1000, 100)), V.Problem),
        ("§10 bez zmian: zerowy mianownik odniesienia -> BRAK WERDYKTU",
         lambda: V.reduction(cell(1000, 100), cell(1000, 0)), V.Problem),
    ]

    failures = 0
    for index, (name, run, expected) in enumerate(cases, start=1):
        if isinstance(expected, type):
            try:
                got = run()
            except expected:
                status, shown = "OK ", f"{expected.__name__}"
            except Exception as exc:  # noqa: BLE001 - kazdy inny wyjatek to blad
                status, shown, failures = "BLAD", f"{type(exc).__name__}: {exc}", failures + 1
            else:
                status, shown, failures = "BLAD", f"brak wyjatku, zwrocono {got}", failures + 1
        else:
            try:
                got = run()
            except Exception as exc:  # noqa: BLE001
                status, shown, failures = "BLAD", f"{type(exc).__name__}: {exc}", failures + 1
            else:
                status = "OK " if got == expected else "BLAD"
                shown = str(got)
                if got != expected:
                    failures += 1
        print(f"[{status}] przypadek {index}: {name} -> {shown}")

    print()
    if failures:
        print(f"BRAMKA ANEKS-4: {failures} z {len(cases)} przypadkow NIEZGODNYCH")
        return 1
    print(f"BRAMKA ANEKS-4: {len(cases)}/{len(cases)} przypadkow o znanej odpowiedzi zgodnych")
    return 0


if __name__ == "__main__":
    sys.exit(main())
