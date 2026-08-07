# K24p — punkt odniesienia

Zamrożone 2026-08-07, przed kampanią. Wszystkie wyniki K24p dotyczą
**wyłącznie** tego stanu silnika. K24p nie zmienia ani jednej linii silnika.

## Repozytoria

| Repozytorium | Gałąź | SHA | Stan drzewa |
|---|---|---|---|
| `retractordb` (silnik) | `master` | `db4a3604bd31ad06e7cc89e95739f7f7e87597d6` | czyste |
| `rdb-experiment` (badanie) | `experiment/20260807_K24p` | robocze (ten katalog) | robocze |

Silnik jest przypięty do `master`, nie do gałęzi roboczej. Wobec punktu
odniesienia K24r (`c4b63a7`) różni się trzema scaleniami:

| SHA | Tytuł | Znaczenie dla K24p |
|---|---|---|
| `79e19eb` | rescale picture | brak — jedna linia w `src/CMakeLists.txt` |
| `5f31051` | Issue 227 precesja (#228) | **przedmiot badania** — przestemplowanie okna `@`, przeniesienie `>N` do origin, nowy przebieg `computeLogicalOrigin()`, nowy model pojemności `@` |
| `db4a360` | Discard DECLARE in AD-Hoc | brak dla kampanii — dotyczy wyłącznie ścieżki ad-hoc (`executorsm::getAdHoc`), a aparatura woła `xretractor -c` oraz `-r -k -m` |

## Binaria i środowisko

```
Branch: master:db4a360, Type: Debug
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
na tej samej maszynie co K24 i K24r.

## Weryfikacja punktu odniesienia

| Kontrola | Wynik |
|---|---|
| `ninja` + `ninja install` (Debug) | bez błędów |
| `ctest` Debug | **181/181 passed**, 187,5 s |
| `ninja` (Release, świeża konfiguracja) | bez błędów |
| `ctest` Release | **181/181 passed**, 130,4 s |

## Materiał dowodowy rachunku

| Plik | SHA-256 |
|---|---|
| `src/retractor/lib/compiler.cpp` | `66187159af1de4f3870a0148e7068235b95f03da475e5c5bacd96bd5c0f0d025` |
| `src/include/SOperations.hpp` | `1d9ec7c1d52d5fbaef6ea5cc9edeee3a505b79fa5ba95761e4fca4fa9e5c1e4e` |
| `src/retractor/lib/dataModel.cpp` | `2518c5e5c9deea799a5788baf0351e0f83b99f963367edd4d4c7c87d647a9ac3` |
| `src/retractor/lib/streamInstance.cpp` | `049c424dd9875ca0f84c674e2f34175ef7b6e058d31d60c27bad6115966a87bb` |

`compiler::computeLogicalOrigin()` liczy początek logiczny,
`compiler::computeStartupLatency()` — ogon; `AgseStartupLatency()`,
`AgseLogicalOrigin()` i `AddStartupLatency()` w `SOperations.hpp` niosą postacie
zamknięte; `dataModel.cpp` i `streamInstance.cpp` niosą odwzorowanie rekordów
(w tym `constructAgsePayload()` z oknem stemplowanym końcem przedziału), które
musi się zgadzać z odwzorowaniem oracle'a.

## Aparatura

Skopiowana z `results_20260804_K24r`. **Zmiany merytoryczne, wymuszone zmianą
mierzonej wielkości** (pełne uzasadnienie w REPORT.md §1):

| Plik | Zmiana |
|---|---|
| `oracle/model.py` | okno `@` stemplowane końcem; `>N` jako przesunięcie indeksu, nie opóźnienie czasu; **origin jako wielkość pierwszej klasy**, wyprowadzana z warunku ciągłości; ogon liczony od origin, nie od zera |
| `oracle/closedform.py` | replika idzie za silnikiem: `evaluate_origins()`, `agse_origin()`, `agse_tail()` bez członu fazowego, ogon `>N` bez `N`, `first_index_reaching()` |
| `oracle/engine.py` | parsowanie `origin=` ze zrzutu planu; wykrywanie `unresolved logical origin` |
| `oracle/execute.py` | pozycja w artefakcie przeliczana na indeks logiczny przez origin |
| `oracle/mutants.py` | rodzina `ORIGIN_MUTANTS` (5 nowych) plus dwa mutanty ogona odtwarzające stan sprzed przestemplowania |
| `tests/hand_cases.py` | 42 przypadki (było 41): przeliczone ogony `>N` i `@`, dopisane początki logiczne, pięć nowych kompozycji na propagację origin |
| `capacity.py` | model pojemności `@` jako dokładny przegląd okresu fazowego; sondowanie od origin |
| `run_campaign.py`, `verdict.py` | kolumny i tabele origin oraz sumy origin+ogon; reguła lokalna A bez wyjątku dla `>N` |

**`generator.py` jest bajtowo bez zmian** wobec K24 i K24r — to warunek
porównywalności trzech kampanii.

## Bramki aparatury przed kampanią

| Bramka | Wynik |
|---|---|
| `tests/test_independence.py` | PRZESZŁA |
| `tests/test_oracle.py` | PRZESZŁA (42 przypadki ręczne, 200 porównań) |
| `tests/test_mutants.py` | PRZESZŁA (12 mutantów: 7 ogona + 5 origin, 100% wykrytych) |
| `tests/test_closedform.py` | WIERNOŚĆ REPLIKI POTWIERDZONA (50 węzłów, ogon i origin) |
