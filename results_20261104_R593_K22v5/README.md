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

Kryteria zapisane; pomiar nie wykonany.
