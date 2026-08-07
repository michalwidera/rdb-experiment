# K24r — punkt odniesienia

Zamrożone 2026-08-04, przed kampanią potwierdzającą. Wszystkie wyniki K24r
dotyczą **wyłącznie** tego stanu silnika. K24r nie zmienia ani jednej linii
silnika.

## Repozytoria

| Repozytorium | Gałąź | SHA | Stan drzewa |
|---|---|---|---|
| `retractordb` (silnik) | `master` | `c4b63a78adf7866db1a8a9f61fbe972dbeed9880` | czyste |
| `rdb-experiment` (badanie) | `experiment/20270803_K24_H10` | `215c776` | robocze (ten katalog) |

Silnik jest przypięty do `master`, nie do gałęzi roboczej: `c4b63a7`
(„Issue 225 capacity model (#226)”) to scalenie gałęzi `issue_225-capacity_model`
z zielonym CI. Drzewa `src/` i `test/` scalonego `master` są identyczne
z ostatnim zweryfikowanym stanem gałęzi (`0e36d9e`), co sprawdzono przez
`git diff --stat 0e36d9e master -- src/ test/` (pusty).

Wobec punktu odniesienia K24 (`5e3eb42`) silnik różni się pięcioma naprawami
defektów (D1–D5) oraz nowymi postaciami zamkniętymi ogona dla `+` i `@` —
to właśnie jest przedmiot tego badania.

## Binaria i środowisko

```
Branch: master:c4b63a7, Code compiler: GNU Ver. 15.2.0, Type: Debug
RDB_OPT_DEDUP_SUBSTRATES=ON
RDB_OPT_SHARE_EQUIVALENT_SELECTS=ON
RDB_OPT_COMMUTATIVE_ADD=ON
RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=ON
RDB_BENCH_PROBE=OFF
```

Python 3.14.4. Kampania używa binarium **Debug**
(`build/Debug/src/retractor/xretractor`); tryb compile-only nie zależy od
poziomu optymalizacji, a konfiguracja optymalizatora planu jest identyczna
w obu typach budowy. Bramka odwzorowania uruchamia to samo binarium Debug
na tej samej maszynie co K24 — inna maszyna unieważniłaby dwuskalową kontrolę
stabilności.

## Weryfikacja punktu odniesienia

| Kontrola | Wynik |
|---|---|
| `ninja` + `ninja install` (Debug) | bez błędów |
| `ctest` Debug | **175/175 passed**, 171,1 s |
| `ninja` (Release) | bez błędów |
| `ctest` Release | **175/175 passed**, 122,8 s |
| CI (CircleCI, `master`) | zielone (potwierdzone przez człowieka przed scaleniem) |

## Materiał dowodowy postaci zamkniętej

Rachunek badany przez K24r znajduje się w:

| Plik | SHA-256 |
|---|---|
| `src/retractor/lib/compiler.cpp` | `fd92eae2fbd0a9256088b37493ac84d71589c4385b4c439b5228edc6f7224e8f` |
| `src/include/SOperations.hpp` | `94884b8b8d517ee2936a0a45632aea2c48c60c821f8320e6e64a07ab6b733fc6` |
| `src/retractor/lib/dataModel.cpp` | `ff63f9fbd96fc7cb747dde0b6bf98d15b3827cd325a8bb609b0ef08ad8b47f33` |

`compiler::computeStartupLatency()` liczy ogon; `AddStartupLatency()`
i `AgseStartupLatency()` w `SOperations.hpp` niosą nowe postacie zamknięte;
`dataModel.cpp` niesie odwzorowanie rekordów (`Add()` dla sumy strumieni),
które musi się zgadzać z odwzorowaniem oracle'a.

## Aparatura

Skopiowana z `results_20260803_K24` bez zmian merytorycznych. Jedyny plik
różniący się treścią to `oracle/closedform.py` — replika postaci zamkniętej,
która z definicji idzie za silnikiem i służy wyłącznie bramce mutantów oraz
bramce wierności repliki. Oracle (`oracle/model.py`) jest bajtowo identyczny
z K24, co jest warunkiem porównywalności obu kampanii.

Sumy kontrolne wszystkich plików katalogu: [`SHA256SUMS`](SHA256SUMS).

## Bramki aparatury przed kampanią

| Bramka | Wynik |
|---|---|
| `tests/test_independence.py` | PRZESZŁA |
| `tests/test_oracle.py` | PRZESZŁA (37 przypadków ręcznych, 80 porównań) |
| `tests/test_mutants.py` | PRZESZŁA (100% mutantów wykrytych) |
| `tests/test_closedform.py` | WIERNOŚĆ REPLIKI POTWIERDZONA (40 węzłów) |
