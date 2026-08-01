#!/usr/bin/env python3
"""Testy o znanej odpowiedzi dla skryptu metryk K22.

Wartości oczekiwane są wyliczone RĘCZNIE z `coding_manual.md`, przez
przejście fixture'a linia po linii — nie odczytane z wyjścia `measure.py`.
Fixture'y są celowo małe, żeby ręczne wyliczenie dało się powtórzyć podczas
przeglądu.

Zakres asercji: kolumny C1..C7, C3d, C4d — czyli wszystko, co wchodzi do
kryterium go/no-go i do tabeli. `loc` i `cyclomatic` są raportowane
informacyjnie i NIE są tu przypinane: są metrykami drugorzędnymi, nigdy nie
wchodzą do kryterium (PREDECLARATION.md §7.3), a ich przypinanie czyniłoby
test kruchym na formatowanie bez zysku dowodowego.

Dwie rzeczy równie ważne:
  * liczniki muszą TRAFIAĆ, gdy konstrukcja jest obecna (kontrole pozytywne
    C5 i C6) — licznik, który zawsze zwraca zero, nie jest pomiarem;
  * aparatura musi ZAWODZIĆ na wejściu niepoprawnym, zamiast liczyć po cichu.
"""
import os
import sys

from measure import METRICS, MeasureError, aggregate, main, measure_file

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

failures = 0
checks = 0


def expect_counts(name, relpath, want):
    """`want` podaje tylko metryki niezerowe; reszta musi byc zerem."""
    global failures, checks
    checks += 1
    path = os.path.join(FIX, relpath)
    try:
        hits, _loc, _cyc, _kind = measure_file(path)
    except MeasureError as exc:
        print(f"FAIL  {name}: nieoczekiwany blad aparatury: {exc}")
        failures += 1
        return
    got = aggregate(hits)
    full = {m: want.get(m, 0) for m in METRICS}
    diff = {m: (got[m], full[m]) for m in METRICS if got[m] != full[m]}
    if diff:
        print(f"FAIL  {name}: rozbieznosci (jest, oczekiwano) = {diff}")
        failures += 1
        return
    print(f"ok    {name}: " + " ".join(f"{m}={got[m]}" for m in METRICS if got[m]))


def expect_error(name, fn):
    global failures, checks
    checks += 1
    try:
        fn()
    except MeasureError:
        print(f"ok    {name}  (blad aparatury wykryty)")
        return
    print(f"FAIL  {name}: oczekiwano MeasureError, nie podniesiono")
    failures += 1


# --- RQL --------------------------------------------------------------------
# 5 instrukcji (2 DECLARE + 3 SELECT) -> C7=5.
# Jedno `@(` -> C3d=1. Dwa interwaly w DECLARE (1/1000 oraz 1) -> C4d=2.
# Zadnej konstrukcji imperatywnej -> C1..C6 = 0. To jest WYNIK POMIARU,
# nie zalozenie: analizator skanuje liste tokenow imperatywnych i nie znajduje
# zadnego (coding_manual.md §1, RQL_IMPERATIVE).
expect_counts("RQL: minimalny FIR", "rql/fir_min.rql", {"C7": 5, "C3d": 1, "C4d": 2})

# --- Python -----------------------------------------------------------------
# C1=1: jedna petla slotowa `for n in range(10)` (brak petli zagniezdzonej,
#       bo dodawanie jest wypisane wprost).
# C4=1: `time.monotonic_ns()` — odczyt zegara (C4-01).
# C3=1: `win` — kontener zbudowany `np.zeros(` i przesuwany `win[:-1]=win[1:]`;
#       nazwa liczona RAZ, mimo dwoch trafien.
# C2=1: `total` — stan nie-kontenerowy, inicjowany poza petla, mutowany w niej.
# C6=0: `y` jest odczytane tylko raz, wiec nie jest wspoldzieleniem.
# C7=3: `WIN = 3`, `win[-1] = src[n]`, `y = win[0] + win[1]`.
expect_counts("Python: minimalna petla slotowa", "python/fir_min.py",
              {"C1": 1, "C2": 1, "C3": 1, "C4": 1, "C7": 3})

# Kontrola pozytywna C6: `shared` policzone raz, odczytane przez dwa wyjscia.
# C7=2: dwa wywolania `.append(...)`. Linia `shared = ...` nalezy do C6
# i NIE moze byc policzona takze w C7 (rozlacznosc, coding_manual.md §0.1).
expect_counts("Python: reczne wspoldzielenie (C6 > 0)", "python/sharing_min.py",
              {"C1": 1, "C6": 1, "C7": 2})

# Kontrola pozytywna C5: trzy rozne reguly musza trafic.
# C5-04 `GROUP_DELAY = 29`, C5-03 `idx = n % 8`, C5-01 `if n < GROUP_DELAY`.
# C7=2: `continue` oraz `y = src[idx]`.
expect_counts("Python: reczny ogon i faza (C5 > 0)", "python/tail_min.py",
              {"C1": 1, "C5": 3, "C7": 2})

# --- Java -------------------------------------------------------------------
# C1=1: `for (int i = 0; ...)` — petla po odczepach (C1-02 nie wystepuje,
#       bo nie ma petli zewnetrznej: operator jest wolany per rekord).
# C3=1: `win` — `new double[3]` oraz `System.arraycopy(win, 1, win, 0, ...)`.
# C2=1: `counter` — POLE operatora przypisywane w metodach per rekord.
#       `acc` NIE jest liczone: to zmienna lokalna metody `map`, ktora nie
#       przezywa rekordu (coding_manual.md §1, C2).
# C7=11: klasa, dwie deklaracje pol, dwa naglowki metod, `counter = 0;`,
#        `win[win.length-1] = x;`, `double acc = 0.0;`, `acc += win[i];`,
#        `counter = counter + 1;`, `return acc;`.
expect_counts("Java: minimalny operator stanowy", "flink/BandPassMin.java",
              {"C1": 1, "C2": 1, "C3": 1, "C7": 11})

# Kontrola pozytywna JAVA-C5-01 (regresja po poprawce dlugu z K22c).
# C5=2: `if (filled < WIN)` oraz `if (n < WIN - 1)`. Pierwsza wersja wzorca
# lapala wylacznie `< x.length` i gubila oba, zanizajac C5 Flinka.
# Trzeci `if` porownuje z `Integer.MIN_VALUE` — to kontrola ZAKRESU, nie ogon,
# i NIE moze byc policzona; dlatego C5 wynosi 2, a nie 3.
# C2=1: pole `filled` (stala `WIN` nigdy nie jest przypisywana ponownie).
# C7=8: klasa, dwa pola, naglowek metody, `filled = filled + 1;`, dwa `return;`
#       oraz `throw ...;`.
expect_counts("Java: jawne warunki rozgrzewki (C5 > 0)", "flink/WarmupMin.java",
              {"C2": 1, "C5": 2, "C7": 8})

# --- aparatura musi zawodzic glosno ----------------------------------------
expect_error("brak znacznikow CORE_BEGIN/CORE_END",
             lambda: measure_file(os.path.join(FIX, "bad/no_markers.py")))
expect_error("CORE_BEGIN bez CORE_END",
             lambda: measure_file(os.path.join(FIX, "bad/unbalanced.rql")))
expect_error("nieobslugiwane rozszerzenie",
             lambda: measure_file(os.path.join(FIX, "bad/unsupported.txt")))
# Zero zeskanowanych programow to BLAD, nie wynik (PREDECLARATION.md §7.5 pkt 2).
expect_error("zero programow na wejsciu",
             lambda: main(["--out-dir", "/tmp/k22_zero"]))

print(f"\n{checks - failures}/{checks} kontroli OK")
sys.exit(1 if failures else 0)
