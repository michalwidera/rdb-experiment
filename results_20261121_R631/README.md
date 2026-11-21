# R631 - produkty artykułu na rewizji silnika z dowodami złożenia planu

Kampania potwierdzająca w ramach retractordb #632, etap 1: przepięcie silnika artefaktu z `16c516f9eb76c473d5ff8510a2a812b8c23a893d` (pin z `rdb-artifact/MANIFEST.md` od 2026-11-11, R618) na R = `758be53b3b8339d176dc678f9a75a259b8926925` (`master` = `dev/muro`, scalenie #631). Plan zatwierdzony przez człowieka 2026-11-21 (issue #632; kotwica czasowa mierzona na nowo, wariant a). Ten katalog nie poprawia K24e, K24f ani R618 i nie zastępuje ich liczb: każda zostaje wynikiem swojej rewizji.

## Dlaczego pomiar, a nie wymiana SHA

Powód przesunięcia: na `16c516f9` nie ma dowodów Lean złożenia planu z #630 (`math_proofs/Profs/StartupBoundaries.lean`, `PlanComposition.lean`, `PlanInstances.lean`, `PlanValues.lean`), więc ani artefakt, ani recenzent ich nie widzi. Przesunięcie przesuwa jednak cały silnik: między `16c516f9` a R są 22 commity, w tym zmiany w `src/`:

- #626: strażnik R1 dla `VAR` w `src/retractor/lib/compiler.cpp` (R1 nie odpala nad zapytaniem czytającym `VAR`);
- `ce2c65eb`: walidacja interwału rozplotu `&` / `%` w `compiler.cpp`;
- #621: nieznana opcja `xtrdb` (`src/rdb/xtrdbLauncher.cpp`);
- poprawki CTidy (`qry.cpp`, `payload.cc`, `qTree.cpp`, `ipcServer.hpp`, `processLimits.hpp`, `api/cpp/src/client.cpp`);
- `VERSION` 0.1.12 -> 0.1.14.

#626 i `ce2c65eb` mogą zmienić wydruk planu albo odrzucić plan przyjmowany dotąd, więc zgodności korpusu z R nie można przyjąć bez przebiegu. Suchy przebieg `rdb-artifact/bin/move_pin.sh` (#632 krok 0, 2026-11-21): 0 problemów, w delcie brak pliku tekstowego >= 1,2 MB i brak dodanej linii pasującej do terminów anonimizacji.

## Binarki (przed tą predeklaracją)

Czyste drzewo `retractordb` na R (`git status --porcelain --untracked-files=all` pusty przed i po budowie), nowe katalogi budowy, Conan i CMake jak `scripts/buildrdb.sh release` (konfiguracja `production_cmake_args`), zmienne wstrzykujące flagi usunięte ze środowiska, cele `xretractor`, `xqry`, `xtrdb`:

| Wariant | Katalog | `--build-info` | SHA-256 `xretractor` | SHA-256 `xqry` |
|---|---|---|---|---|
| all-on | `build/R631-Release` | 5 × `RDB_OPT_*=ON`, `RDB_BENCH_PROBE=OFF` | `9d5950c6c5ad5d173389fdd9256d8988461dc340aa8a153eb8f1ef28e27f2f9b` | `749112090fe21bec82f3c9f55e72bd841d38ef549d9ad7e898eb8f8a39180713` |
| all-off | `build/R631-Ablation-alloff` | 5 × `RDB_OPT_*=OFF`, `RDB_BENCH_PROBE=OFF` (zbudowana 2026-11-21 po kryteriach 1-3, przed przebiegiem kryterium 4, ten sam przepis) | `573cd48bdbeffca69d99861c82f4c293b9635ed4efc8609a77012041bfd0004c` | `f589244b3c71c61e5cf6930232791c34bab0653b808fec50e3deace4bc164e87` |

Odniesienie: binarka pinu `16c516f9` z `paper-arXiv/measurment-tool/run/bin/16c516f9eb76c473d5ff8510a2a812b8c23a893d/xretractor` (zbudowana przez `trend.py` 2026-11-12, `--build-info` 5 × `RDB_OPT_*=ON`, `RDB_BENCH_PROBE=OFF`), SHA-256 `ef8ef4c4a30ad5a2e2393dc33a87ce82b58a74e8cbcae4f944edd35094acf4e1`. Korpus: `rdb-experiment` na pinie artefaktu `ff5a116b5e51002cc6b27c6a6300e526538a07c7`; drzewo `current/` bez zmian wobec `84fee502` (R618).

Aparatura bez zmian wobec R618 iteracji 2: `paper-arXiv/measurment-tool/check_backward_corpus_compatibility.sh` SHA-256 `1540b7127f11bcce85fe492472b1f7a52ddfa7ba61cbe77b2625b141d9de7834` (zacommitowany w `paper-arXiv` `2da2d7c`, czysty), `migrate_corpus.py` SHA-256 `8be34ca79c2d8064ffa7f4439638f02e3f5667884484c3e7904f3a5a93285b28`, plik akceptacji `check_backward_corpus_compatibility.accepted` SHA-256 `e56d3ed315c5a369a7fe635f089f694b133acfde86c1164c668ac3f40b1479f4` (3 wpisy).

## Kryteria - zapisane przed przebiegami

Przebiegi biegną na hoście x86_64. Wynik jest **POTWIERDZONY**, gdy wszystkie warunki zachodzą jednocześnie:

1. **K24e, oba ziarna.** Grupa `k24e` kontroli zgodności: generator K24e z pinu korpusu (`results_20260818_K24e/`), 10 010 planów na ziarno, silnik all-on R. Plik CSV kampanii bajt w bajt równy zapisanemu `raw/campaign_seed20260818.csv` i `raw/campaign_seed20260820.csv`.
2. **K24f, oba ziarna.** Grupa `k24f`: generator K24f z oknami rekordowymi (`results_20260912_K24f/apparatus/`, `--with-window`), ziarna `20260912` i `20260913`, silnik all-on R. CSV bajt w bajt równy `raw/h10_20260912.csv` i `raw/h10_20260913.csv`.
3. **Pozostałe grupy kontroli zgodności wstecznej.** `check_backward_corpus_compatibility.sh` z silnikiem pod testem all-on R wobec binarki pinu `16c516f9`, wszystkie siedem grup (`plans`, `runs`, `artifacts`, `g3`, `k24e`, `k24f`, `ecg`), tryb domyślny (po migracji M1, S1, S2), nowy katalog roboczy `run/compat-20261121-758be53b`: wynik `ZGODNY`, kod 0, zero niezaakceptowanych rozbieżności, plik akceptacji bez zmian; każda kopia `current/` zgodna albo zgodna modulo M1 (`kopie_current_zgodne + kopie_current_zgodne_modulo_m1` = liczba kopii, żadna kopia nie jest rozbieżnością; oczekiwane z R618: 170 + 54 = 224). Liczba planów grupy `plans` nie jest kryterium (pin korpusu `ff5a116` ma plany dodane po R618); kryterium jest zero rozbieżności i zero planów przyjmowanych na pinie, a odrzucanych na R.
4. **Przykłady.** Każdy plik `.rql` z `examples/` w drzewie R (27 programów, bez zmian wobec `16c516f9`) kompiluje się binarką all-on i all-off z własnego katalogu (`-c -m -q <plik>` i `-c -q <plik>`, kod 0); stdout obu trybów jest bajtowo identyczny ON/OFF dla każdego programu. Kontrola trafności porównania: trzy kontrole pozytywne z #612 (`test/IntegrationTest/issue167_dedup_positive/query.rql`, `issue202_hash_shift_factorization/matched.rql`, `select_cse_commutative_add/query.rql`) dają różne zwykłe listingi (`-c -q`) ON/OFF. Narzędzie: `results_20261111_R618/tools/examples_census.sh` bez zmian.
5. **Tryb dowodowy.** Świeży katalog z `rdb-artifact/bin/checkout.sh` z pinem silnika R (`REPRODUCE.md` §6): w `math_proofs/` `./render.sh` kończy się `DOWODY: OK`; `proof_drift` i `ut_proofOracle` zielone; `test/proof_manifest.tsv` R: 151 twierdzeń, 86 TEST, 0 niepokrytych, 65 poza zakresem, pokrycie 86 z 86.
6. **Dokumentacja.** `doc_drift_scalar_functions` i `proof_drift` na R przeciw `documentation-rdb` `00e571783c232e635bce924e294b99bd43033919` zielone; przy zielonym wyniku pin dokumentacji w artefakcie zostaje.

**Każda rozbieżność zatrzymuje kampanię** i idzie do człowieka z surowymi danymi (`STOP.md`). Bez korekt po fakcie: przebieg nie jest powtarzany ani poprawiany po cichu, plik akceptacji, aparatura kampanii i skrypt kontroli nie są zmieniane po starcie. Czerwony wynik niczego nie psuje w artefakcie: pin `16c516f9` zostaje, dopóki kampania nie jest potwierdzona.

Kryteria 1-3 rozstrzyga jeden przebieg kontroli zgodności; kryteria 4-6 mogą biec w osobnej sesji, z tymi samymi kryteriami, bez nowej predeklaracji. Kotwica czasowa K18 na R (R631 K18d na pi400, protokół R618 K18c bez zmian) dostaje własne kryteria, zapisane przed pomiarem w osobnym katalogu.

## Stan

Predeklaracja zapisana w `6351fc1`, przed przebiegami. **Kampania w toku: kryteria 1-4 POTWIERDZONE 2026-11-21, kryteria 5-6 nie biegły.**

**Iteracja 1 nieliczona.** Przebieg skończył się `ZGODNY` z 0 rozbieżności, ale binarka odniesienia `run/bin/16c516f9…` ma wbudowaną rewizję `e389edd3`; szczegóły w [`PREDECLARATION-2.md`](PREDECLARATION-2.md) §1, wyciąg w [`compat-it1-summary.txt`](compat-it1-summary.txt).

**Iteracja 2 ([`PREDECLARATION-2.md`](PREDECLARATION-2.md), `e50c041`): kryteria 1-3 zachodzą na R `758be53b` wobec czystej binarki pinu `16c516f9` (`build/R618-Release`, `955fdc71…`).**

1. K24e: ziarno `20260818` 35 835 obserwacji, ziarno `20260820` 35 703, oba bajt w bajt jak `raw/campaign_seed*.csv`;
2. K24f: ziarno `20260912` 36 162, ziarno `20260913` 36 089, oba bajt w bajt jak `raw/h10_*.csv`;
3. kontrola zgodności (2026-11-21 22:12-22:19, skrypt SHA-256 `1540b712…`, `paper-arXiv` `2da2d7c`): `WYNIK: ZGODNY`, kod 0, 0 rozbieżności w siedmiu grupach. `plans` 709 (673 zgodne, 36 odrzucanych przez oba silniki, 0 przyjętych dopiero teraz; wobec R618 +27 planów z pinu korpusu `ff5a116`), kopie `current/` 170 bajtowo równych + 54 zgodnych modulo M1 = 224; `runs` 67/67; `artifacts` 48/48 (replay K18 67 plików: pin = silnik, plan pinu = plan S1/S2, dwa przebiegi silnika równe); `g3` 13/13; `fig:qrs` 3/3 kanały, 400 próbek, 0 NULL, 0 rozbieżności wartości, piki MLII `x=122,365`. Trzy wpisy pliku akceptacji nieużyte jak w R618; plik bez zmian. Wyciąg z logu: [`compat-it2-summary.txt`](compat-it2-summary.txt).

Ani #626 (strażnik R1 dla `VAR`), ani `ce2c65eb` (walidacja interwału rozplotu) nie zmienia wydruku żadnego planu korpusu ani wyniku żadnego przebiegu.

**Kryterium 4 (przykłady), 2026-11-21:** binarka all-off dopisana w `07bdccc` przed przebiegiem. 27/27 programów z `examples/` kompiluje się all-on i all-off w obu trybach (kod 0, stderr puste), stdout `-c -m -q` i `-c -q` bajtowo identyczny ON/OFF dla 27/27; trzy kontrole pozytywne dają różne listingi ON/OFF w obu trybach. Opisowo: źródła (`sources.sha256`) i wszystkie 120 zrzutów (`dumps.sha256`) bajtowo równe R618 na `16c516f9`. Dowody: [`examples/`](examples/) (`census.tsv`, sumy źródeł, sumy zrzutów, tożsamość binarek), narzędzie `results_20261111_R618/tools/examples_census.sh` bez zmian.

Dalej (#632 etap 1): kryteria 5-6 (tryb dowodowy, `doc_drift`) według tego README, bez nowej predeklaracji; potem R631 K18d na pi400 w osobnym katalogu.
