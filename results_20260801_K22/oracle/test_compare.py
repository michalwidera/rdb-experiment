#!/usr/bin/env python3
"""Testy o znanej odpowiedzi dla komparatora K22.

Sprawdzają dwie rzeczy, obie konieczne:
  1. komparator ORZEKA PASS, gdy strumienie są zgodne (inaczej cała kampania
     zwracałaby porażki niezależnie od danych);
  2. komparator ŁAPIE każdą klasę rozjazdu, którą predeklaracja uznaje za
     porażkę (inaczej PASS nic nie znaczy).

Punkt 2 jest ważniejszy. Komparator, który nigdy nie zawodzi, jest gorszy niż
brak komparatora, bo wygląda na dowód.
"""
import os
import sys

from compare import OracleError, compare, load

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

failures = 0
checks = 0


def fx(name):
    return load(os.path.join(FIX, name))


def expect(name, want_verdict, streams, tails, span=4, want_rows=None):
    global failures, checks
    checks += 1
    try:
        verdict, detail, start, stop, rows = compare(streams, tails, span)
    except OracleError as exc:
        print(f"FAIL  {name}: nieoczekiwany blad aparatury: {exc}")
        failures += 1
        return
    if verdict != want_verdict:
        print(f"FAIL  {name}: oczekiwano {want_verdict}, jest {verdict} ({detail})")
        failures += 1
        return
    if want_rows is not None and rows != want_rows:
        print(f"FAIL  {name}: oczekiwano {want_rows} porownanych rekordow, jest {rows}")
        failures += 1
        return
    print(f"ok    {name}  [{start},{stop}) rows={rows} {detail}")


def expect_apparatus_error(name, fn):
    global failures, checks
    checks += 1
    try:
        fn()
    except OracleError:
        print(f"ok    {name}  (blad aparatury wykryty)")
        return
    print(f"FAIL  {name}: oczekiwano OracleError, nie podniesiono")
    failures += 1


base = fx("base.csv")

# --- kontrola pozytywna -----------------------------------------------------
expect("trzy zgodne modele -> PASS", "PASS",
       {"rql": base, "python": fx("base.csv"), "flink": fx("base.csv")},
       {"rql": 2, "python": 2, "flink": 2}, span=4, want_rows=4)

# Rozne ogony: zakres zaczyna sie od MAKSIMUM (PREDECLARATION.md §5.3).
expect("rozne ogony, zakres od max(tail) -> PASS", "PASS",
       {"rql": base, "python": fx("base.csv"), "flink": fx("base.csv")},
       {"rql": 2, "python": 2, "flink": 4}, span=4, want_rows=4)

# --- kazda klasa rozjazdu MUSI byc zlapana ----------------------------------
expect("rozna wartosc w zakresie -> FAIL", "FAIL",
       {"rql": base, "python": fx("mismatch_value.csv")},
       {"rql": 2, "python": 2}, span=4)

expect("rozny is_null -> FAIL", "FAIL",
       {"rql": base, "python": fx("mismatch_null.csv")},
       {"rql": 2, "python": 2}, span=4)

expect("luka w modelu porownywanym -> FAIL", "FAIL",
       {"rql": base, "python": fx("gap_in_range.csv")},
       {"rql": 2, "python": 2}, span=4)

expect("luka w modelu odniesienia -> FAIL", "FAIL",
       {"rql": fx("gap_in_range.csv"), "python": base},
       {"rql": 2, "python": 2}, span=4)

expect("brakujacy indeks -> FAIL", "FAIL",
       {"rql": base, "python": fx("missing_index.csv")},
       {"rql": 2, "python": 2}, span=4)

expect("zamieniona kolejnosc pol -> FAIL", "FAIL",
       {"rql": base, "python": fx("fieldorder.csv")},
       {"rql": 2, "python": 2}, span=4)

# Rozjazd POZA zakresem porownania nie jest porazka: modele maja prawo do
# roznych ogonow (PREDECLARATION.md §5.3). Indeks 0 i 1 sa przed T=2.
expect("rozjazd przed ogonem nie jest porazka -> PASS", "PASS",
       {"rql": base, "python": fx("mismatch_value.csv")},
       {"rql": 5, "python": 5}, span=3, want_rows=3)

# --- bledy aparatury, nie wyniki -------------------------------------------
expect_apparatus_error("pusty strumien", lambda: fx("empty.csv"))
expect_apparatus_error("is_null=1 z niepusta wartoscia", lambda: fx("malformed_null.csv"))
expect_apparatus_error("brak zadeklarowanego tail",
                       lambda: compare({"rql": base, "python": base}, {"rql": 2}, 4))
expect_apparatus_error("jeden model to nie porownanie",
                       lambda: compare({"rql": base}, {"rql": 2}, 4))
expect_apparatus_error("zerowy zakres porownania",
                       lambda: compare({"rql": base, "python": base}, {"rql": 2, "python": 2}, 0))

print(f"\n{checks - failures}/{checks} kontroli OK")
sys.exit(1 if failures else 0)
