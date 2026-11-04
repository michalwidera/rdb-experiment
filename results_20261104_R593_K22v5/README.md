# R593 / K22v5 - ponowne przebiegi semantyczne na nowym przypięciu silnika

Ponowne wykonanie części semantycznej K22v5 (`results_20260801_K22v5/`, `tab:k22-constructs`) na silniku `dev/muro@dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb`, w ramach retractordb #593 podpunkt 6c. Pytanie: czy warunek wstępny K22v5 - „all 15 measured cells pass a shared oracle at zero tolerance over 2000 slots” (`paper-arXiv/debs/main-debs.tex`, silnik `dd733e3`, aparatura `3366f13`, werdykt `a9af132`) - zachodzi także na `dfcc42d2`.

Zakres: wyłącznie przebiegi `run_campaign.py` (RQL wobec writerów Pythona i Flinka, `oracle/compare.py`, SPAN = 2000) dla 15 komórek: `base` oraz M1..M4 × F1..F3. D1/D2, kodowanie ręczne, `prepare_review.py`, `analyze.sh` i testy „baza oblewa wariant” (`base_must_fail_rows`) nie zależą od warunku wstępnego i nie są powtarzane (decyzja człowieka 2026-11-04, D3). Zamrożone K22v5 (`REPORT.md`, `PREDECLARATION.md`, `results/`, `evidence/`, `tasks/`) i pilot K22 (`corpus/`, `oracle/`) są tylko czytane. Wynik nie zastępuje K22v5: K22v5 zostaje wynikiem kampanii historycznej na `dd733e3`, a 6c jest nieblokujące.

## Kryteria - zapisane przed pomiarem

Wynik jest **POTWIERDZONY**, gdy w każdej z 15 komórek zachodzi jednocześnie:

1. zmigrowany rdzeń ma dowód migracji (`config/migration.tsv`, niżej) i kompiluje się (`-c`);
2. `emit_rql.py` (zamrożony, pilot K22) zwraca 2000 rekordów bez nulli i luk;
3. `compare.py` (zamrożony) przy zerowej tolerancji i `--span 2000` daje `verdict=PASS` dla trzech modeli razem (`rql`, `python`, `flink`), jak w K22v5;
4. w trzech komórkach M3 kontrola metadanej rate (`check_rate`, bez zmian) daje PASS.

Każdy inny wynik jest **NIEPOTWIERDZONY** i idzie do człowieka z surowymi danymi wszystkich komórek; nic nie jest powtarzane ani poprawiane po cichu. Komórka, która nie przechodzi, dostaje jedną klasę, ustaloną teraz:

- **T** (typ) - emiter odrzuca typ albo wiersz deskryptora artefaktu (np. RATIONAL, którego `emit_rql.py` nie obsługuje);
- **P** (przesunięcie) - porównanie trójstronne FAIL, Python i Flink zgodne ze sobą, a ciąg RQL równy ciągowi Pythona przy stałym przesunięciu indeksu `k != 0`, `|k| <= 10`, na indeksach `[first_index + 10, first_index + 1990)`; `k` jest wpisane w kolumnie;
- **W** (wartość) - każda inna niezgodność porównania;
- **A** (aparatura) - każdy inny błąd: timeout, za mało rekordów, kod wyjścia silnika, brak tokenu rate.

Bez wpływu na werdykt, opisowo: porównania parami (`rql_vs_python`, `rql_vs_flink`, `python_vs_flink`) oraz równość bajtowa nowych `rql.csv`, `python.csv`, `flink.csv` z zamrożonymi plikami K22v5 (`*_eq_k22v5`).

## Mapowanie indeksu (decyzja człowieka 2026-11-04, D1 wariant ii)

K22v5 mapowało rekord artefaktu na indeks logiczny jako `tail + nr_rekordu`, z `tail` odczytanym z `-c` (`PREDECLARATION.md` §11.1 E2). Od `5f310515` (2026-08-06, okno `@` stemplowane końcem przedziału, `origin`) i `34db1a29` / `fcc5a444` (2026-08-07, reguła ogona) wydruk `-c` podaje osobno `tail` i `origin`, każde tylko gdy niezerowe, a pierwszy wyemitowany rekord ma indeks logiczny `origin` po `origin + tail` slotach ciszy (`dataModel.cpp`, `processRows`). Writery Pythona i Flinka są zamrożone i etykietują w konwencji K22v5 (F1: okno kończące się na próbce `n` ma indeks `n + 1`), więc mapowanie `origin + nr_rekordu` dawałoby FAIL z samej zmiany konwencji.

Dlatego rekord 0 artefaktu dostaje zamrożony pierwszy indeks K22v5 (kolumna `tail` w `results_20260801_K22v5/results/semantic.csv`), przekazany jako `--tail` do `emit_rql.py` i `compare.py`; wywołania Pythona i Flinka (`slots = 2000 + first_index + 30`) są identyczne jak w K22v5. PASS znaczy więc: **ciąg 2000 wartości wyemitowanych przez `dfcc42d2` od pierwszego rekordu jest równy ciągowi Pythona i Flinka** - ten sam ciąg wartości, nie ten sam indeks logiczny silnika. `tail` i `origin` z `-c` są zapisane obok (`engine_tail`, `engine_origin`).

| Komórka | pierwszy indeks K22v5 | `dfcc42d2` `tail` / `origin` |
|---|---:|---|
| base, M1, M4 × F1 | 26 | 999 / 25 |
| M2_F1 | 45 | 999 / 44 |
| M3_F1 | 26 | 749 / 25 |
| base, M1 × F2 | 240 | 359 / 236 |
| M2_F2 | 255 | 359 / 251 |
| M3_F2 | 240 | 249 / 236 |
| M4_F2 | 60 | 359 / 57 |
| base_F3 | 35 | 0 / 32 |
| M1_F3 | 35 | 2 / 32 |
| M2_F3 | 50 | 0 / 47 |
| M3_F3 | 51 | 0 / 46 |
| M4_F3 | 5 | 0 / 3 |

(wartości z sondy `-c` przed pomiarem; przebieg zapisuje je ponownie w `results/semantic.csv`)

## Różnice wobec K22v5

| Element | K22v5 | R593 K22v5 | Powód |
|---|---|---|---|
| Silnik | `dd733e3`, `~/.local/bin/xretractor` (SHA-256 `6fe7fd97…`) | `dev/muro:dfcc42d2` Debug, kopia `build/Debug` (`xretractor` `eae9b596…`, `xtrdb` `b7784b05…`, `cmp` z buildem) | przedmiot pomiaru; `~/.local/bin` to inny build, a przebudowa w `build/Debug` po `9471538a` (drzewo równe `dfcc42d2`) zmieniłaby stempel (decyzja D2) |
| Gałąź wyników | `experiment/20260801_K22` | `experiment/20261103_R593` | jedna gałąź powtórki #593 |
| Rdzenie RQL | zamrożone, `DECLARE ... FILE` i postfiksowe `.sumc` / `.avg` | `config/cores/<komórka>.rql` po migracji M1 + S1 + S2 | bieżąca składnia i typ reduktorów; dowód niżej |
| Odczyt `-c` | `tail=N` na końcu wiersza celu | `tail` i `origin`, brak = 0 | format wydruku od `5f310515` |
| Indeks rekordu 0 | `tail` z `-c` | pierwszy indeks K22v5 | decyzja D1 (ii), wyżej |
| `-m` dla F1 / F2 | `2000 + tail + 20` | `2000 + origin + tail + 20` | cisza trwa `origin + tail` slotów; stary wzór dałby 1995 rekordów w F1 |
| `-m` dla F3 | 2850 (M3: 4200) | bez zmian | |
| Plik współczynników F1 | `test/IntegrationTest_parallel/dsp/filterremez.txt` | `test/IntegrationTest/dsp/filterremez.txt` | przeniesiony w `300f23c6`; blob identyczny (`bf58295d`), sprawdza `freeze_check.sh` |
| FAIL komórki | przerywa kampanię | zapisany z klasą, kampania biegnie dalej | surowe dane wszystkich komórek dla człowieka |
| `base_must_fail_rows` | wykonywane | pominięte | decyzja D3 |
| `freeze_check.sh` | przypina `dd733e3`, nadpisuje zamrożone `results/` | kopia: przypina `dfcc42d2` i binarki, czyta zamrożone pliki, pisze tylko do `results/` tego katalogu | zamrożone sumy K22v5 zostają ważne |
| JDK | 17.0.19 | 17.0.20.1 | aktualizacja systemowa linii 17; JAR Flinka bez zmian (SHA-256 `7c51cba8…`) |
| Python | 3.14.4 | 3.14.4 | |

## Migracja rdzeni (M1, S1, S2)

`migrate_cores.sh` woła `paper-arXiv/measurment-tool/migrate_corpus.py` (commit `08bd80f`, `paper-arXiv` HEAD `cc8c9e4`) z binarką pinu `40c28dbe` (Release, `measurment-tool/run/bin/40c28dbe…/xretractor`, SHA-256 `5afa0435…`) jako odniesieniem typów i kopią Debug `dfcc42d2` jako silnikiem pod testem. Binarki `dd733e3` nie ma; `dd733e3` jest przodkiem `40c28dbe` i oba są sprzed zmiany typu reduktorów z 2026-09-14. Oryginały to zamrożone pliki (sumy baz równe `results_20260801_K22v5/manifest.md`). Wynik w `config/migration.tsv`:

- **M1 `MIGRATED` w 15/15**: od 2026-09-14 `SUMC`/`AVG` nad polem całkowitym dają RATIONAL, a `emit_rql.py` RATIONAL nie obsługuje, więc przebieg bez M1 kończyłby się klasą T, nie porównaniem wartości. F1 i F3 zawijają 1 strumień (cel), F2 cztery (`bp_out`, `d_out`, `mwi`, `mwi_thr`). Dowód: wydruk `-c` pinu na planie po M1 to wydruk pinu na oryginale z dokładnie tyloma dodanymi wierszami `CALL(to_integer)`, ilu jest zawiniętych strumieni, i bez innych różnic (kolumna `m1_proof`). Czy `to_integer` na wyniku RATIONAL daje te same wartości co obcięcie w `dd733e3`, rozstrzyga oracle;
- **S `MIGRATED` w 15/15**: F1 i F3 2-3 deklaracje FILE i 1 forma postfiksowa, F2 3 i 4. Dowód: ten sam wydruk `-c` silnika pod testem przed i po S1/S2 (`c_eng_m1_sha256 = c_eng_migrated_sha256`), `--verbose` po migracji bez `is deprecated` (2-3 -> 0), zero form postfiksowych w wierszach kodu.

## Uruchomienie

```bash
XRETRACTOR=<katalog z kopiami xretractor i xtrdb>/xretractor ./freeze_check.sh
XRETRACTOR=<katalog z kopiami xretractor i xtrdb>/xretractor ./run_campaign.sh
```

Pomiar na hoście x86-64 (K22v5: „Worker RT nieużywany”); przebieg RQL w czasie rzeczywistym jak w K22v5 (`-m <cykle> -k -r`, bez `-f`), na maszynie bez innej instancji `xretractor`. Timeouty chronią przed zawieszeniem aparatury i nie są obserwacją wydajnościową.

## Stan

**NIEPOTWIERDZONY 2026-11-04 - 9/15 komórek PASS, 6 FAIL klasy W** (`results/semantic.csv`, wydruki `compare.py` w `evidence/raw/<komórka>/oracle*.log`). Kryteria zapisane i wypchnięte przed pomiarem (`07c634c`); jeden przebieg, bez powtórek i poprawek. Bramka `freeze_check.sh` czysta (`results/environment.tsv`). Wynik idzie do człowieka.

| Komórka | Werdykt | Klasa | `rql_vs_python` | `rql_vs_flink` | `python_vs_flink` | `rql.csv` = K22v5 |
|---|---|---|---|---|---|---|
| base_F1, M2_F1, M3_F1, M4_F1 | PASS | | PASS | PASS | PASS | tak |
| base_F3, M2_F3, M3_F3, M4_F3 | PASS | | PASS | PASS | PASS | tak |
| M4_F2 | PASS | | PASS | PASS | PASS | tak |
| base_F2, M1_F2, M2_F2, M3_F2 | FAIL | W | FAIL | FAIL | PASS | nie |
| M1_F1, M1_F3 | FAIL | W | FAIL | FAIL | PASS | nie |

Kontrola rate w trzech komórkach M3: PASS. Wszystkie 15 emisji dało 2000 rekordów bez nulli, bez błędu aparatury i bez klasy T (M1 usunęło RATIONAL z celów). `python.csv` i `flink.csv` są we wszystkich 15 komórkach bajtowo równe zamrożonym plikom K22v5, więc writery i JDK 17.0.20.1 nie zmieniły odniesienia; każda różnica leży po stronie RQL. W dziewięciu komórkach PASS `rql.csv` z `dfcc42d2` jest bajtowo równy `rql.csv` z `dd733e3`.

**Diagnoza po pomiarze (opisowa, nie zmienia klasy):** `diagnose_shift.py` -> `results/diagnosis.txt`. W każdej komórce FAIL **każde pole z osobna** jest ciągiem Pythona przesuniętym o stałą liczbę indeksów, ale pola tego samego rekordu przesuwają się o różne wartości, więc żadne mapowanie rekordu (a więc i klasa P z kryteriów) nie daje zgodności:

| Komórka | Rekordy różne | Pola zgodne bez przesunięcia | Pola przesunięte (k) |
|---|---:|---|---|
| M1_F1 | 2000/2000 | `f1_out_0` (FIR) | `f1_out_1` (k=1) |
| M1_F3 | 667/2000 | `f3_out_0` | `f3_out_1` (k=1) |
| base_F2, M3_F2 | 1871/2000 | - | `qrs_out_0` (k=4), `qrs_out_1`, `qrs_out_2` (k=1) |
| M1_F2 | 1994/2000 | - | `qrs_out_0`, `qrs_out_3` (k=4), `qrs_out_1`, `qrs_out_2` (k=1) |
| M2_F2 | 1869/2000 | - | `qrs_out_0` (k=4), `qrs_out_1`, `qrs_out_2` (k=1) |

(k: wartość RQL w indeksie `i + k` równa wartości Pythona w indeksie `i`)

Najprostsza komórka pokazuje mechanizm. W M1_F1 zamrożony writer Pythona emituje dla okna FIR po próbkach `n-25..n` parę `(n + 1, [y, samples2[n + 1]])`, czyli łączy okno z próbką drugiego kanału o jeden slot późniejszą; tak liczył `dd733e3`. Na `dfcc42d2` złączenie `fir+channel2` daje próbkę z tej samej chwili co koniec okna (`samples2[n]`), zgodnie ze zmianą `5f310515` (okno `@` stemplowane końcem przedziału, `SOperations.hpp`: „złączenie okna z jego własnym źródłem (potok FIR) nie wyprzedza sygnału”). Pole FIR jest identyczne. Komórki PASS mają jeden strumień wyjściowy z jednej ścieżki okien (F1, F3 bez drugiego kanału, cel `mwi_q` w M4_F2), więc przesunięcie wspólne dla całego rekordu znosi mapowanie D1 (ii). Komórki FAIL łączą w jednym rekordzie ścieżki o różnej liczbie okien (F2 `qrs_out`: łańcuch czterech okien wobec ścieżek z jednym; M1: okno wobec surowego drugiego kanału). Wniosek z danych: różnica dotyczy wyrównania pól w złączeniu, nie arytmetyki - żadna wartość nie powstaje poza ciągiem odniesienia. To, że zmiana `5f310515` jest zamierzona, wynika z dokumentacji silnika, nie z tego pomiaru.

Dla artykułu: warunek wstępny K22v5 w obecnym brzmieniu („all 15 measured cells pass a shared oracle at zero tolerance over 2000 slots”) **nie zachodzi** na `dfcc42d2` z zamrożonymi writerami K22v5; zostaje wynikiem historycznym na `dd733e3`. Czy i jak to opisać (np. writery w konwencji sprzed `5f310515`), decyduje człowiek.

**Decyzja człowieka 2026-11-04 (wariant D):** bez naprawy. Silnik zostaje przy semantyce `5f310515`, bez trybu zgodności z `dd733e3`: stary tryb przywracałby udokumentowany defekt (FIR wyprzedzający sygnał), zmieniałby `Val` i podwajał macierz testów, a nie wzmocniłby artykułu ponad istniejący wynik na `dd733e3`. Rdzenie RQL i writery K22v5 bez zmian; K22v5 zostaje wynikiem historycznym. Gdyby artykuł miał kiedyś twierdzić zgodność K22 na bieżącym silniku, drogą są nowe writery w konwencji `5f310515` jako osobne badanie z predeklaracją. Komentarz: retractordb #593 issuecomment-6630769374; podpunkt 6c odznaczony z wynikiem niepotwierdzonym.
