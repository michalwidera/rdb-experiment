# R618 - produkty artykułu na rewizji silnika z postacią zamkniętą ogona przeplotu

Kampania potwierdzająca w ramach retractordb #618, droga (b): przepięcie silnika artefaktu z `e389edd3596e4b83b6f3f4a9e238905a91c667b4` (pin z `rdb-artifact/MANIFEST.md` od 2026-11-07) na R = `16c516f9eb76c473d5ff8510a2a812b8c23a893d` (`master` = `dev/muro`, scalenie #617). Plan zatwierdzony przez człowieka 2026-11-11 (komentarz #618 6791719096, decyzje D1-D5). Ten katalog nie poprawia K24e, K24f ani R593 K18b i nie zastępuje ich liczb: każda zostaje wynikiem swojej rewizji. Status kampanii K24e i K24f w artykule pozostaje „confirmation at a pinned revision” (D4: bez nowego ziarna).

## Dlaczego pomiar, a nie wymiana SHA

Między `e389edd3` a R są dwa scalenia:

- #613 (`4f091e26`): poprawki przykładów, w `examples/` 9 plików, w tym 4 programy `.rql`; `src/` bez zmian;
- #617 (`07d62785`): `HashStartupLatency()` w `src/include/SOperations.hpp` liczy ogon przeplotu `#` postacią zamkniętą w O(1) dla każdego okresu fazowego, zamiast przeglądu jednego okresu z progiem `kHashPhaseScanLimit = 100000` i oszacowaniem zawyżającym powyżej progu; w `src/retractor/lib/compiler.cpp` dochodzi straż zakresu wyniku. Równość postaci zamkniętej z maksimum po okresie dowodzi `exactInterleaveTail_closed` w `math_proofs/Profs/InterleaveTailExact.lean`.

Kampanie K24e i K24f mierzą ogon i początek logiczny każdego węzła, w tym `#`, więc zgodności ich zapisanych wyników z R nie można przyjąć bez przebiegu.

## Binarki (etap 0, przed tą predeklaracją)

Czyste drzewo `retractordb` na R (`git status --porcelain --untracked-files=all` pusty przed i po budowie), nowe katalogi budowy, Conan i CMake jak `scripts/buildrdb.sh release` / `release-ablation`, zmienne wstrzykujące flagi usunięte ze środowiska, cele `xretractor`, `xqry`, `xtrdb`:

| Wariant | Katalog | `--build-info` | SHA-256 `xretractor` | SHA-256 `xqry` |
|---|---|---|---|---|
| all-on | `build/R618-Release` | 5 × `RDB_OPT_*=ON`, `RDB_BENCH_PROBE=OFF` | `955fdc71e75aa21889fadcd6bb869d62f5c49c6ac3f784b4ead657ae813685c7` | `cdafeb8aaca2753696bea8dc859192cd94b26c5b839dae52f472b064056b74b3` |
| all-off | `build/R618-Ablation-alloff` | 5 × `RDB_OPT_*=OFF`, `RDB_BENCH_PROBE=OFF` | `6d98b2c0901333b53981d4f9954ea10e6cf9bb9569391662dbcc78475e3d75e3` | `2f7d12a2ed16a074c104c9672ff41e80d1a59005265b9f0885a6d2e6667bd0ed` |

Odniesienie: binarka pinu `e389edd3` z `paper-arXiv/measurment-tool/run/bin/e389edd3596e4b83b6f3f4a9e238905a91c667b4/xretractor` (ta sama, której użyła kontrola zgodności 2026-11-07 wobec `40c28dbe`). Korpus: `rdb-experiment` na pinie artefaktu `84fee502acb77b111b0f83bb07a2104b7477e560`.

## Kryteria - zapisane przed przebiegami

Przebiegi etapu 2 biegną na hoście x86_64. Wynik jest **POTWIERDZONY**, gdy wszystkie warunki zachodzą jednocześnie:

1. **K24e, oba ziarna.** Generator K24e z pinu korpusu (`results_20260818_K24e/`, ten sam generator, oracle i reguła werdyktu; w kopii roboczej jedynie S1 `FILE` -> `TEXTFILE` źródeł `*.txt`, jak w kontroli 2026-11-07), 10 010 planów na ziarno, silnik all-on R. Plik CSV kampanii bajt w bajt równy zapisanemu `raw/campaign_seed20260818.csv` (ziarno w próbie) i `raw/campaign_seed20260820.csv` (ziarno potwierdzające).
2. **K24f, oba ziarna.** Generator K24f z oknami rekordowymi (`results_20260912_K24f/apparatus/`, `--with-window`), ziarna `20260912` i `20260913`, silnik all-on R. CSV bajt w bajt równy `raw/h10_20260912.csv` i `raw/h10_20260913.csv`.
3. **Pozostałe grupy kontroli zgodności wstecznej.** `paper-arXiv/measurment-tool/check_backward_corpus_compatibility.sh` z silnikiem pod testem all-on R wobec binarki pinu `e389edd3`, wszystkie siedem grup (`plans`, `runs`, `artifacts`, `g3`, `k24e`, `k24f`, `ecg`; kryteria 1 i 2 to grupy `k24e` i `k24f` tego przebiegu), tryb domyślny (po migracji M1, S1, S2): wynik `ZGODNY`, kod 0, zero niezaakceptowanych rozbieżności, plik akceptacji bez zmian (3 wpisy), kopie `current/` bajtowo równe planom silnika pod testem po migracji.
4. **Przykłady.** Każdy plik `.rql` z `examples/` w drzewie R (27 programów; po #613 zmienione 4) kompiluje się binarką all-on i all-off z własnego katalogu (`-c -m -q <plik>` i `-c -q <plik>`, kod 0); stdout obu trybów jest bajtowo identyczny ON/OFF dla każdego programu. Kontrola trafności porównania: trzy kontrole pozytywne z #612 (`test/IntegrationTest/issue167_dedup_positive/query.rql`, `issue202_hash_shift_factorization/matched.rql`, `select_cse_commutative_add/query.rql`) dają różne zwykłe listingi (`-c -q`) ON/OFF.

**Każda rozbieżność zatrzymuje kampanię** i idzie do człowieka z surowymi danymi. Bez korekt po fakcie: przebieg nie jest powtarzany ani poprawiany po cichu, plik akceptacji, aparatura kampanii i skrypt kontroli nie są zmieniane po starcie. Czerwony wynik niczego nie psuje w artefakcie: droga powrotu do (a) w #618 jest otwarta do etapu 6.

**Opisowo, poza kryterium (punkt 7 #618):** największy okres fazowy `p+q` węzła `#` w korpusie K24e na ziarnie potwierdzającym `20260820`. Policzony z generatora pinu korpusu, bez silnika, przed tą predeklaracją (§ *Punkt 7* niżej); nie wpływa na kryteria, bo R nie ma już progu.

Kotwica czasowa K18 na R (etap 3, R618 K18c na pi400, protokół R593 K18b bez zmian) dostaje własne kryteria, zapisane przed pomiarem w osobnym katalogu.

## Punkt 7 - największe `p+q` węzła `#`

Metoda: `generate(ziarno, 10010)` z pinu korpusu (K24f: `strata=STRATA_WITH_WINDOW`), dla każdego węzła `#` skrócone `delta_A/delta_B = p/q` jego składowych, czyli wielkość `period` porównywana z `kHashPhaseScanLimit` w `HashStartupLatency()` pinu `e389edd3`. Delty składowych sprawdzone z kolumną `delta` zapisanego CSV kampanii: wszystkie obecne w nim węzły równe. Dla porównania z `results_20260818_K24e/STOP.md` §2 podane też maksimum `period_hint` po wszystkich klasach (`oracle/plan.py`, tak liczy tamta tabela).

| Kampania | Ziarno | Węzły `#` | max `p+q` (`#`) | Gdzie | `p+q > 100000` | max `period_hint` (wszystkie klasy) |
|---|---|---:|---:|---|---:|---:|
| K24e | `20260818` (w próbie) | 5 953 | 13 087 | plan 7597, `n3` = `343/1000 # 147/1441` | 0 | 19 087 (węzeł `+`, plan 9659) |
| K24e | `20260819` (spalone, iteracja 1) | 5 967 | 31 841 | plan 8878, `n2` = `2/203 # 147/1000` | 0 | 31 841 |
| K24e | **`20260820`** (potwierdzające) | 5 958 | **31 841** | plan 4454, `n1` = `294/2441 # 1/100` | **0** | 31 841 |
| K24f | `20260912` | 5 755 | 4 793 | plan 7202, `n3` = `147/1588 # 2/11` | 0 | 7 087 (`+`) |
| K24f | `20260913` | 5 742 | 15 847 | plan 3024, `n1` = `1/100 # 147/1147` | 0 | 17 323 (`+`) |

Kalibracja: wartości 19 087 (`20260818`) i 31 841 (`20260819`) z STOP.md odtwarzają się co do liczby. 19 087 jest maksimum po wszystkich klasach (węzeł `+`); po samych węzłach `#` ziarno `20260818` ma 13 087. Próg 100 000 przeglądu w `e389edd3` nie był osiągany w żadnym z pięciu ziaren.

## Stan

Predeklaracja zapisana; przebiegi etapu 2 nierozpoczęte.
