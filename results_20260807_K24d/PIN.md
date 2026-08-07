# K24d — punkt odniesienia

Zamrożone 2026-08-07, przed kampanią. Wszystkie wyniki K24d dotyczą
**wyłącznie** tego stanu silnika. K24d nie zmienia ani jednej linii silnika.

## Powód istnienia tego katalogu

K24p przypięta jest do `db4a360`. Tego samego dnia dwie klasy operatorów
zmieniły reżim: `>N` po naprawie adresowania (`fcc5a44`, krok 3d) i `#` po
wdrożeniu dokładnej reguły ogona (`34db1a2`, krok 3c). Liczby K24p opisują więc
silnik, którego nie da się wysłać do pakietu artefaktów bez rozjazdu z tabelą
w artykule — ten sam mechanizm, który wymusił K24p wobec K24r. K24d dostarcza
kolumny **silnik wobec oracle'a przy SHA, który faktycznie pójdzie do pakietu**.

## Repozytoria

| Repozytorium | Gałąź | SHA | Stan drzewa |
|---|---|---|---|
| `retractordb` (silnik) | `master` | `34db1a291fff686d63402270722edf9c772bd4b6` | czyste |
| `rdb-experiment` (badanie) | `experiment/20260807_K24d` | robocze (ten katalog) | robocze |

Wobec punktu odniesienia K24p (`db4a360`) różnią się trzy commity:

| SHA | Tytuł | Znaczenie dla K24d |
|---|---|---|
| `fcc5a44` | fix math fetchBack->fetchForward | **przedmiot badania** — `τ_N` adresowane indeksem logicznym, ogon `max(0, W_src − N)`, nowy model pojemności dla przesunięcia |
| `adfbeb9` | fix for ut | wzorce testów i skrypty weryfikacyjne, bez zmian w rachunku |
| `34db1a2` | 3c - PASS - HashStartupLatency | **przedmiot badania** — ogon `#` liczony przeglądem okresu fazowego zamiast postaci O(1) |

## Binaria i środowisko

```
Branch: master:34db1a2, Type: Debug
RDB_OPT_DEDUP_SUBSTRATES=ON
RDB_OPT_SHARE_EQUIVALENT_SELECTS=ON
RDB_OPT_COMMUTATIVE_ADD=ON
RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=ON
RDB_BENCH_PROBE=OFF
```

Python 3.14.4. Kampania używa binarium **Debug**
(`build/Debug/src/retractor/xretractor`); tryb compile-only nie zależy od
poziomu optymalizacji, a konfiguracja optymalizatora planu jest identyczna
w obu typach budowy. Ta sama maszyna co K24, K24r, K24b i K24p.

## Weryfikacja punktu odniesienia

| Kontrola | Wynik |
|---|---|
| `ninja` + `ninja install` (Debug) | bez błędów |
| `ctest` Debug | **181/181 passed**, 193,4 s |
| `ninja` + `ninja install` (Release) | bez błędów |
| `ctest` Release | **181/181 passed**, 110,9 s |

Oba przebiegi `ctest` wykonano z **zainstalowanym binarium właściwego typu**:
testy integracyjne uruchamiają program z `~/.local/bin`, więc przebieg Release
bez `ninja install` mierzyłby binarium Debug i niczego nie dowodził.

## Materiał dowodowy rachunku

| Plik | SHA-256 |
|---|---|
| `src/retractor/lib/compiler.cpp` | `50db2ba6822979e5a814a1a1e6ad038d9a0cb387f0e0baf98b1329b7e49e67d0` |
| `src/include/SOperations.hpp` | `34c921ea7b28801028abbc1c0f52c440e2e547bcc44756dc94d895e71ce59420` |
| `src/retractor/lib/dataModel.cpp` | `6a2b3ab0dcc37604557ef8b868ae79bd67d8a989a9f21715a13b84189264b991` |
| `src/retractor/lib/streamInstance.cpp` | `049c424dd9875ca0f84c674e2f34175ef7b6e058d31d60c27bad6115966a87bb` |

`compiler::computeLogicalOrigin()` liczy początek logiczny,
`compiler::computeStartupLatency()` — ogon; `AgseStartupLatency()`,
`AgseLogicalOrigin()`, `AddStartupLatency()` i **nowa `HashStartupLatency()`**
w `SOperations.hpp` niosą postacie zamknięte; `dataModel.cpp`
i `streamInstance.cpp` niosą odwzorowanie rekordów, które musi się zgadzać
z odwzorowaniem oracle'a.

## Aparatura

Skopiowana z `results_20260807_K24p`. **`generator.py` jest bajtowo bez zmian**
wobec K24, K24r i K24p — to warunek porównywalności pięciu kampanii.
Model zdarzeniowy (`oracle/model.py`) jest **bajtowo bez zmian** wobec K24p:
naprawy z 2026-08-07 dotyczyły rachunku silnika, nie definicji operatorów, więc
oracle nie miał się z czego zmienić. To jest mocny warunek — gdyby oracle
wymagał zmiany, znaczyłoby to, że zmieniono semantykę, a nie naprawiono wzór.

Zmiany merytoryczne, wymuszone naprawami:

| Plik | Zmiana |
|---|---|
| `oracle/closedform.py` | replika idzie za silnikiem: ogon `>N` to `max(0, W_src − N)`; nowe `hash_tail()` (przegląd okresu fazowego, z progiem `HASH_PHASE_SCAN_LIMIT = 100 000` jak w silniku) oraz `hash_pick()`; zastąpiona postać O(1) zachowana jako `hash_tail_o1()` — jest i ścieżką powyżej progu, i rodziną mutantów |
| `oracle/mutants.py` | trzy nowe mutanty ogona: `shift_tail_keeps_source` (postać `db4a360` dla `>N`), `hash_closed_form_o1` (postać `db4a360` dla `#`), `hash_scan_half_period` (przegląd skrócony o połowę). Razem **15 mutantów**: 10 ogona, 5 origin |
| `tests/hand_cases.py` | **44 przypadki** (było 42) — dwa dołożone, oba o ręcznie wyprowadzonej odpowiedzi, opisane niżej |

### Dlaczego dołożono dwa przypadki ręczne

To jest wynik metodyczny, nie kosmetyka. Po dopisaniu trzech nowych mutantów
bramka **nie przeszła**: `hash_closed_form_o1` i `hash_scan_half_period`
pozostały niewykryte. Przyczyna: w korpusie bramkowym K24p **nie było ani
jednego węzła `#` o obu składowych z niezerowym ogonem**, a bez tego zastąpiona
postać O(1) i reguła dokładna dają tę samą liczbę. Bramka mutantów przechodziła
więc również dla postaci obalonej w K24.

Ta sama pułapka wystąpiła niezależnie w bramce `ctest` silnika przy kroku 3c
(pierwsza wersja `ut_h10aGate` przechodziła dla obu reguł). Dwa niezależne
wykrycia tego samego braku w jednym dniu są argumentem, żeby traktować to jako
regułę ogólną, a nie incydent: **korpus bramkowy trzeba sprawdzać na zdolność
odróżnienia reguły obalonej, a nie zakładać ją.**

Dołożone przypadki:

* `hash of two hashes (obie składowe z ogonem)` — `(1#1) # (1#1/2)`, ogon `n2`
  wyprowadzony spacerem po pięciu slotach okresu: **3**, podczas gdy postać O(1)
  daje 4;
* `hash with max in the second half of the period` — `s0@(1,1) # s1`, gdzie
  maksimum deficytu wypada na slocie 1 z trzech, więc przegląd skrócony
  do połowy okresu zwróciłby 2 zamiast 3.

## Bramki aparatury przed kampanią

| Bramka | Wynik |
|---|---|
| `tests/test_independence.py` | PRZESZŁA |
| `tests/test_oracle.py` | PRZESZŁA (44 przypadki ręczne, 220 porównań) |
| `tests/test_mutants.py` | PRZESZŁA (15 mutantów: 10 ogona + 5 origin, 100% wykrytych) |
| `tests/test_closedform.py` | WIERNOŚĆ REPLIKI POTWIERDZONA (55 węzłów, ogon i origin) |
