#!/usr/bin/env python3
"""Semantyka referencyjna K22 — arytmetyka silnika retractordb@abe075e.

Ten moduł jest JEDYNYM źródłem prawdy o arytmetyce dla portów Python i Flink
w kampanii K22. Rdzenie Pythona importują go wprost; rdzeń Javy odwzorowuje
te same reguły, a `oracle/test_refsem.py` pilnuje zgodności obu przez
fixture'y o znanej odpowiedzi.

Każda reguła ma odniesienie do kodu silnika. Odniesienia są częścią
predeklaracji (`PREDECLARATION.md` §4) — recenzent ma móc je sprawdzić bez
uruchamiania czegokolwiek.

NIE UŻYWAĆ `//` ANI `round()`. `-7 // 2 == -4`, a silnik daje `-3`.
"""
from fractions import Fraction

INT_MAX = 2**31 - 1
INT_MIN = -(2**31)

# Wartość nieobecna. Silnik reprezentuje ją jako std::monostate w descFldVT
# (fldType.hpp:15); tu jest to None. NULL jest wartością POCHŁANIAJĄCĄ —
# "dane oczekiwane a nieobecne", nigdy rezerwacją miejsca na dane
# (expressionEvaluator.cpp:190-197).
NULL = None


def _is_null(v):
    return v is NULL


def iadd(a, b):
    """Dodawanie z pochłaniającym NULL (expressionEvaluator.cpp:84)."""
    if _is_null(a) or _is_null(b):
        return NULL
    return a + b


def isub(a, b):
    """Odejmowanie z pochłaniającym NULL (expressionEvaluator.cpp:114)."""
    if _is_null(a) or _is_null(b):
        return NULL
    return a - b


def imul(a, b):
    """Mnożenie z pochłaniającym NULL (expressionEvaluator.cpp:146).

    UWAGA: silnik mnoży zwykłe `int` bez ochrony przed przepełnieniem
    (expressionEvaluator.cpp:155) — inaczej niż `.sumc`, które nasyca.
    Tu nie symulujemy przepełnienia: rodziny K22 mają je WYKLUCZONE zakresem
    danych, co sprawdza `test_range.py`. Gdyby wynik wyszedł poza int32,
    jest to błąd doboru danych, nie wynik — dlatego asercja.
    """
    if _is_null(a) or _is_null(b):
        return NULL
    r = a * b
    if not (INT_MIN <= r <= INT_MAX):
        raise OverflowError(
            f"imul({a}, {b}) = {r} poza int32 — zakres danych nie wyklucza "
            f"przepelnienia; patrz PREDECLARATION.md 4.1 pkt 4"
        )
    return r


def idiv(a, b):
    """Dzielenie całkowite z OBCIĘCIEM DO ZERA (expressionEvaluator.cpp:206).

    To jest semantyka C++ `int/int`, NIE `//` Pythona:
        idiv(-7, 2) == -3        (-7 // 2 == -4)

    Dzielenie przez zero daje NULL i strumień pracuje dalej — nie wyjątek
    (expressionEvaluator.cpp:189-199).
    """
    if _is_null(a) or _is_null(b):
        return NULL
    if b == 0:
        return NULL
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


def _finalize_int(value):
    """Rzutowanie wyniku agregatu z rational na INTEGER.

    `rational_cast<int>` obcina do zera, a wartości poza zakresem są NASYCANE
    do INT_MAX / INT_MIN (streamInstance.cpp:352-362).
    """
    if value > INT_MAX:
        return INT_MAX
    if value < INT_MIN:
        return INT_MIN
    num, den = value.numerator, value.denominator
    q = abs(num) // abs(den)
    return -q if (num < 0) != (den < 0) else q


def sumc(fields):
    """Agregat `.sumc` po polach jednego rekordu.

    Pola NULL są POMIJANE (streamInstance.cpp:288-290). Sumowanie odbywa się
    dokładnie, na liczbach wymiernych (streamInstance.cpp:256-275), a wynik
    jest finalizowany do INTEGER z nasyceniem.

    Brak pól nie-NULL → wynik NULL (streamInstance.cpp:312-316).
    """
    acc = Fraction(0)
    valid = 0
    for f in fields:
        if _is_null(f):
            continue
        valid += 1
        acc += Fraction(f)
    if valid == 0:
        return NULL
    return _finalize_int(acc)


def avg(fields):
    """Agregat `.avg` po polach jednego rekordu.

    KLUCZOWE: dzielnikiem jest liczba pól NIE-NULL (`validItemCount`),
    a NIE szerokość okna (streamInstance.cpp:288-290 oraz 318-319).
    Oba istniejące baseline'y (np.zeros / new double[WIN]) dzielą przez pełne
    N i dlatego NIE są równoważne silnikowi na ogonie startowym
    (PREDECLARATION.md §4.1 pkt 3).

    Dzielenie jest dokładne (wymierne) i dopiero wynik jest obcinany do zera
    — nie wolno obcinać sumy przed dzieleniem.
    """
    acc = Fraction(0)
    valid = 0
    for f in fields:
        if _is_null(f):
            continue
        valid += 1
        acc += Fraction(f)
    if valid == 0:
        return NULL
    return _finalize_int(acc / valid)


def worst_case_abs(max_abs_value, max_abs_coef, width):
    """Największa możliwa |suma| splotu — do wykluczenia przepełnienia."""
    return max_abs_value * max_abs_coef * width


def range_is_safe(max_abs_value, max_abs_coef, width):
    """Czy zakres danych WYKLUCZA przepełnienie int32 (PREDECLARATION.md §4.1 pkt 4)."""
    return worst_case_abs(max_abs_value, max_abs_coef, width) <= INT_MAX
