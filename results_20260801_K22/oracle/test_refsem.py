#!/usr/bin/env python3
"""Testy o znanej odpowiedzi dla semantyki referencyjnej K22.

Wartości oczekiwane są wyliczone RĘCZNIE z reguł silnika (PREDECLARATION.md §4),
nie wygenerowane przez `refsem.py`. Test, którego oczekiwania pochodzą
z testowanego kodu, nie jest testem.

Nacisk na przypadki ODRÓŻNIAJĄCE semantykę silnika od domyślnej semantyki
Pythona — bo to na nich port po cichu się rozjedzie:
  * obcięcie do zera vs `//` (podłoga),
  * dzielnik `.avg` = liczba pól nie-NULL vs szerokość okna,
  * dokładne dzielenie wymierne przed obcięciem.
"""
import sys

from refsem import (INT_MAX, INT_MIN, NULL, avg, iadd, idiv, imul, isub,
                    range_is_safe, sumc, worst_case_abs)

CASES = []


def case(name, got, want):
    CASES.append((name, got, want))


# --- dzielenie: OBCIĘCIE DO ZERA, nie podłoga -------------------------------
# Rozstrzygające: Python `-7 // 2` daje -4, silnik daje -3.
case("idiv 7/2", idiv(7, 2), 3)
case("idiv -7/2 (podloga dalaby -4)", idiv(-7, 2), -3)
case("idiv 7/-2 (podloga dalaby -4)", idiv(7, -2), -3)
case("idiv -7/-2", idiv(-7, -2), 3)
case("idiv -1/2 (podloga dalaby -1)", idiv(-1, 2), 0)
case("idiv 0/5", idiv(0, 5), 0)
case("idiv 6/3 dokladne", idiv(6, 3), 2)

# --- dzielenie przez zero: NULL, nie wyjatek --------------------------------
case("idiv 5/0 -> NULL", idiv(5, 0), NULL)
case("idiv 0/0 -> NULL", idiv(0, 0), NULL)

# --- NULL pochlaniajacy -----------------------------------------------------
case("iadd NULL+5", iadd(NULL, 5), NULL)
case("iadd 5+NULL", iadd(5, NULL), NULL)
case("isub 5-NULL", isub(5, NULL), NULL)
case("imul 3*NULL", imul(3, NULL), NULL)
case("idiv NULL/2", idiv(NULL, 2), NULL)
case("iadd 2+3 (kontrola pozytywna)", iadd(2, 3), 5)
case("imul 1000*1000", imul(1000, 1000), 1000000)

# --- .avg: dzielnik = liczba pol NIE-NULL -----------------------------------
# Rozstrzygające: baseline'y zero-fill dziela przez pelne N i tu sie rozjada.
case("avg [1,2,3,4] = 10/4 -> 2", avg([1, 2, 3, 4]), 2)
case("avg [-1,-2,-3,-4] = -10/4 -> -2 (podloga dalaby -3)", avg([-1, -2, -3, -4]), -2)
case("avg [1,2,NULL,4] dzieli przez 3, nie przez 4", avg([1, 2, NULL, 4]), 2)
case("avg [NULL,NULL] -> NULL", avg([NULL, NULL]), NULL)
case("avg [] -> NULL", avg([]), NULL)
case("avg [5] -> 5", avg([5]), 5)
case("avg [1,2] = 3/2 -> 1", avg([1, 2]), 1)
case("avg [-1,-2] = -3/2 -> -1 (podloga dalaby -2)", avg([-1, -2]), -1)
case("avg [1,1,1,1,2] = 6/5 -> 1", avg([1, 1, 1, 1, 2]), 1)
case("avg [-1,-1,-1,-1,-2] = -6/5 -> -1 (podloga dalaby -2)", avg([-1, -1, -1, -1, -2]), -1)
# Okno 30 z pieciu obecnymi probkami: dzielnik 5, nie 30.
case("avg okno30 z 5 obecnymi = 15/5 -> 3", avg([1, 2, 3, 4, 5] + [NULL] * 25), 3)

# --- .sumc ------------------------------------------------------------------
case("sumc [1,2,3]", sumc([1, 2, 3]), 6)
case("sumc [1,NULL,3] pomija NULL", sumc([1, NULL, 3]), 4)
case("sumc [NULL] -> NULL", sumc([NULL]), NULL)
case("sumc [] -> NULL", sumc([]), NULL)
case("sumc nasyca do INT_MAX", sumc([INT_MAX, 1]), INT_MAX)
case("sumc nasyca do INT_MIN", sumc([INT_MIN, -1]), INT_MIN)
case("sumc ujemne", sumc([-5, 3]), -2)

# --- wykluczenie przepelnienia zakresem danych ------------------------------
case("worst_case F1 (500 x 32767 x 25)", worst_case_abs(500, 32767, 25), 409587500)
case("F1 miesci sie w int32", range_is_safe(500, 32767, 25), True)
case("okno 200 juz sie nie miesci", range_is_safe(500, 32767, 200), False)


def main():
    failures = 0
    for name, got, want in CASES:
        if got != want:
            print(f"FAIL  {name}: oczekiwano {want!r}, jest {got!r}")
            failures += 1

    # imul poza int32 ma byc bledem doboru danych, nie cicha wartoscia.
    try:
        imul(100000, 100000)
        print("FAIL  imul poza int32 powinno rzucic OverflowError")
        failures += 1
    except OverflowError:
        pass

    total = len(CASES) + 1
    if total == 0:
        print("FAIL  zero przypadkow testowych — blad aparatury")
        return 2
    print(f"{total - failures}/{total} przypadkow OK")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
