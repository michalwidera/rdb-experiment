# K24 — punkt odniesienia (F0)

Zamrożone 2026-08-03, przed napisaniem oracle'a. Wszystkie wyniki K24 dotyczą
**wyłącznie** tego stanu silnika. K24 nie zmienia ani jednej linii silnika.

## Repozytoria

| Repozytorium | Gałąź | SHA | Stan drzewa |
|---|---|---|---|
| `retractordb` (silnik) | `issue_223-fixes` | `5e3eb42e75628d25dd01430ceef9893e08363283` | czyste |
| `rdb-experiment` (badanie) | `experiment/20270803_K24_H10` | `0390a8910d72ecaa80772f3fd31a5f18a05369aa` | robocze (ten katalog) |

Gałąź silnika wyprzedza `master` o dwa commity (`5e3eb42`, `ff9c25b`) i nie jest
za nim opóźniona. Wynik K24 dotyczy tej gałęzi, nie `master`.

**Uwaga nazewnicza:** nazwa gałęzi badania niesie datę `20270803`, podczas gdy
badanie jest z **2026-08-03**. Katalog wyników trzyma się konwencji
`results_YYYYMMDD_K24`, więc nazywa się `results_20260803_K24`. Rozjazd nazwy
gałęzi i daty odnotowany świadomie — do rozstrzygnięcia przy scalaniu.

## Binaria i środowisko

```
Branch: issue_223-fixes:5e3eb42, Code compiler: GNU Ver. 15.2.0, Type: Debug
RDB_OPT_DEDUP_SUBSTRATES=ON
RDB_OPT_SHARE_EQUIVALENT_SELECTS=ON
RDB_OPT_COMMUTATIVE_ADD=ON
RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=ON
RDB_BENCH_PROBE=OFF
```

Python 3.14.4. Kampania używa binarium **Debug** (`build/Debug/src/retractor/xretractor`);
tryb compile-only nie zależy od poziomu optymalizacji, a konfiguracja
optymalizatora planu jest identyczna w obu typach budowy.

## Weryfikacja punktu odniesienia

| Kontrola | Wynik |
|---|---|
| `ninja` + `ninja install` (Debug) | bez błędów |
| `ctest` Debug | **174/174 passed**, 158,5 s |
| `ninja` (Release) | bez błędów |
| `ctest` Release | **174/174 passed**, 119,2 s |

## Materiał dowodowy postaci zamkniętej

Rachunek badany przez K24 znajduje się w:

| Plik | SHA-256 |
|---|---|
| `src/retractor/lib/compiler.cpp` (`computeStartupLatency`, linie 950–1055) | `244315253847adbfc656bf9d8c31916815d45b1fa4ae9973f3243045547e2fbd` |
| `src/include/SOperations.hpp` (`Hash`, `Div`, `Mod`, `Subtract`, `AgseStartupLatency`, `SubtractStartupLatency`) | `f61157d8a616d47e758eb496849253cfecae403755172f78f4da27aa8052fabf` |

Replika tego rachunku w Pythonie (`oracle/closedform.py`) służy wyłącznie
bramce mutantów; jej wierność wobec silnika sprawdza `tests/test_closedform.py`.
