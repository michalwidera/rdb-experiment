# R593 / K6c - powtórka kontrolna Tier B na nowym przypięciu silnika

Powtórka kontrolna wyniku `tab:k6-primary` (kampania K6c, `results_20260730_K6c/`) na silniku `dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb`, w ramach retractordb #593 (wariant C, decyzja człowieka 2026-11-03). Ten katalog nie poprawia K6c i nie zastępuje jej liczb: werdykt K6c zostaje wynikiem kampanii historycznej z jej rewizjami (`e1e5181`, `1bb2d2c`). Powtórka odpowiada na pytanie, czy na silniku, który ma zostać nowym przypięciem artykułu, rozkład klas komórek jest ten sam.

Część H9 tej samej powtórki jest w `results_20261103_R593_H9/`; obie biegną na gałęzi `experiment/20261103_R593`.

## Kryteria - zapisane przed pomiarem

Reguła klasyfikacji komórki jest regułą K6c bez zmian (`analyze.py`, README K6c „Reguła decyzyjna"): metryka pierwotna to iloraz median `compute_ns` ALGSTRUCT/STRUCT, próg poprawy 10% (iloraz <= 0,90), bootstrap 10 000 replikacji. Powtórka jest **POTWIERDZONA**, gdy rozkład klas jest taki sam jak w K6c: **A=0, B=12, C=1**, z regresją w tej samej komórce (`W3_d3`) i bez naruszenia kontroli (`control_violations` puste). Każda inna liczebność klas jest wynikiem niepotwierdzonym i idzie do człowieka razem z ilorazami; nie jest naprawiana ani powtarzana po cichu. Dla każdej z 13 komórek raport podaje iloraz i CI obok wartości K6c (`results_20260730_K6c/results/analysis.json`).

Sprawdzian analizatora: `analyze.py` z tego katalogu uruchomiony na zamrożonych `runs.csv` K6c bez danych Tier A daje A=0, B=12, C=1, regresja `W3_d3` - tak jak zamrożony werdykt.

## Zakres i odstępstwa od K6c

| Element | K6c | R593 | Powód |
|---|---|---|---|
| Silnik | `e1e5181` (W2-W7), `1bb2d2c` (W8-W9) | `dfcc42d2` dla wszystkich | przedmiot powtórki |
| Zakres | K6c.0 kalibracja, K6c.3 Tier A, K6c.4 Tier B, K6c.5 saturacja | tylko Tier B | tabela artykułu pochodzi z Tier B |
| Macierz | 13 komórek × 4 profile × 15 powtórzeń = 780 przebiegów | ta sama (`matrix.tsv`, `W8_Q32` wykluczona decyzją) | |
| Rate i budżet slotów | kalibracja -> `results/rate.json` | zamrożony `rate.json` K6c (suma `bbe54920…`) | to samo obciążenie co w kampanii |
| Profile | 5 profili, `RDB_OPT_SIMPLIFY_EXPRESSIONS` nie istniał | te same 5 profili + jawne `SIMPLIFY=ON` we wszystkich | przełącznik powstał po K6c, `--build-info` go wypisuje; ON = wartość domyślna silnika, wspólna dla profili |
| Plany | generator K6c, formy przestarzałe | ten sam generator + plany po migracji M1/S1/S2 | bieżąca składnia; ta sama praca (niżej) |
| Harness | `worker/run_ablation_study.sh` | ten sam plik, bez zmian | |
| Binarki profili na workerze | 5 osobnych buildów `build/K6-*` | `K6-OFF` zbudowany przez `build_profiles.sh`; cztery pozostałe to kopie binarek H9 o identycznych flagach (niżej) | ten sam commit źródła i te same `RDB_OPT_*`; oszczędność ok. 1 h 45 min budowy na Pi (decyzja człowieka 2026-11-03) |

## Migracja planów (M1, S1, S2)

`generate.py` w tym katalogu nie generuje niczego sam: uruchamia zamrożony `results_20260730_K6c/generate.py` z argumentami harnessu, a potem podmienia każdy `query.rql` na plan z `plans/s<skala>/<przypadek>/query.rql` - wyłącznie wtedy, gdy wygenerowany plan ma sumę `orig_sha256`, a podmieniony `migrated_sha256` z `migration/migration.tsv`. Dane (`*.txt`, `external_data.txt`) zostają z generatora.

Migracja: `paper-arXiv/measurment-tool/migrate_corpus.py` (commit `08bd80f`), odniesienie - binarka pinu `40c28dbe`, silnik pod testem - Release `dfcc42d2`, skale 1, 6 i 12 (wszystkie skale z `rate.json`), po 46 przypadków. Wynik: 138/138 S `MIGRATED`; M1 `MIGRATED` w 36 planach (W4 i W8 w trzech skalach: `to_integer(...)` na wyniku `AVG`/`SUMC` nad polem całkowitym, gdzie pin typował INTEGER, a silnik daje RATIONAL), `SAME` w pozostałych 102. M1 sprawia, że silnik pod testem liczy to samo, co liczył silnik kampanii; oba profile porównania dostają ten sam plan. Plany są bajt w bajt równe planom z przebiegu kontroli zgodności z 2026-11-02.

Dane zewnętrzne W8 (`examples/ecg/rec205/{rec205,bp_coef.txt,d_coef.txt}`) są identyczne w `e1e5181` i `dfcc42d2`.

## Zmiany w skopiowanych plikach

`matrix.tsv`, `profiles.tsv`, `results/rate.json`, `analyze.py` - bez zmian. Zmienione:

- `build_profiles.sh`: jawne `-DRDB_OPT_SIMPLIFY_EXPRESSIONS=ON` i jego weryfikacja w `--build-info`;
- `summarize_run.py`: wiersz `REWRITE_APPLIED` silnika `dfcc42d2` kończy się licznikiem `r3`; wyrażenie przyjmuje go opcjonalnie, a `r3` nie wchodzi do `runs.csv`, więc schemat (35 kolumn) i `analyze.py` są jak w K6c. Bez tej zmiany każdy przebieg kończyłby się błędem podsumowania;
- `generate.py`: nakładka opisana wyżej.

Próba na hoście (x86, `-f`, `-m 600`, profile DEFAULT i NO_R1_NO_R2 hosta = ALGSTRUCT i STRUCT): 13/13 komórek z kodem 0 i kompletnym podsumowaniem; R1 odpala w W2/W3/W4/W8, R2 w W8/W9, kontrole W5 i W7 mają 0/0 i identyczne artefakty w obu profilach.

## Binarki profili na workerze

Wszystkie z `~/R593` @ `dfcc42d2`, Release, `RDB_BENCH_PROBE=ON`, `RDB_OPT_SIMPLIFY_EXPRESSIONS=ON`, `cap_ipc_lock,cap_sys_nice=ep`. Cztery profile K6c mają dokładnie te same przełączniki co profile H9 (`results_20261103_R593_H9/profiles.tsv`), więc ich binarki są kopiami tamtych; `--build-info` każdej kopii zweryfikowano wobec flag profilu K6c (`verify_probe_binary_profile`), a capabilities nadano kopii osobno.

| Profil K6c | Źródło binarki | SHA-256 (16 znaków) |
|---|---|---|
| `OFF` | `build_profiles.sh` -> `build/K6-OFF` | `665524df193153e2` |
| `STRUCT` | kopia `build/R593-NO_R1_NO_R2` | `3911eaacc9ac803a` |
| `STRUCT_R1` | kopia `build/R593-NO_R2_CANON` | `486e7b10604f48eb` |
| `STRUCT_R2` | kopia `build/R593-NO_R1_FACTOR` | `9f60838771a1c76c` |
| `ALGSTRUCT` | kopia `build/R593-DEFAULT` | `4e8420e4ee9016bf` |

Klient `xqry` (część aparatury, harness sprawdza jego commit) zbudowany w `build/R593-DEFAULT` i zainstalowany w `~/.local/bin`.

## Przebieg (worker)

```bash
# profile K6-* w ~/R593 (K6_CCACHE=1 K6_SETCAP=1), xqry z dfcc42d2 w ~/.local/bin
worker/run_ablation_study.sh --code-repo /home/michal/R593 --code-commit dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb \
  --experiment-branch experiment/20261103_R593 --results-root results_20261103_R593_K6c \
  --study-id N --family WN --reps 15
# restart workera między badaniami; siedem badań: W2, W3, W4, W5, W7, W8, W9
python3 analyze.py --runs ablation/study_*/runs.csv --rate-json results/rate.json --output results
```

## Stan

Pomiar zakończony 2026-11-03: 7 badań (W2, W3, W4, W5, W7, W8, W9), 780 przebiegów, `ablation/study_*/runs.csv`. Analiza: `analyze.py --runs ablation/study_*/runs.csv --rate-json results/rate.json --output results` -> `results/summary.md`, `results/analysis.json`.

Wynik: rozkład klas A=0, B=12, C=1, jak w K6c; regresja w tej samej komórce, `W3_d3` 1.113 [1.110; 1.115]; kontrole negatywne W5_Q32 i W7_Q32 czyste. Kryterium potwierdzenia z sekcji *Kryteria* spełnione (`control_violations` puste). Zestawienie z K6c (`results_20260730_K6c/results/analysis.json`):

| Komórka | K6c iloraz [95% CI] | klasa | R593 iloraz [95% CI] | klasa |
|---|---|:--:|---|:--:|
| `W2_Q01` | 1.064 [1.038; 1.100] | B | 1.032 [1.021; 1.069] | B |
| `W2_Q08` | 1.061 [1.053; 1.066] | B | 1.068 [1.063; 1.072] | B |
| `W2_Q32` | 0.991 [0.980; 0.994] | B | 0.992 [0.974; 0.996] | B |
| `W3_d1` | 1.056 [1.023; 1.064] | B | 1.066 [1.059; 1.070] | B |
| `W3_d3` | 1.103 [1.099; 1.106] | C | 1.113 [1.110; 1.115] | C |
| `W4_Q08` | 1.002 [0.999; 1.005] | B | 1.010 [1.006; 1.014] | B |
| `W4_Q32` | 0.998 [0.994; 1.000] | B | 1.001 [0.997; 1.004] | B |
| `W5_Q32` | 1.019 [1.010; 1.025] | B | 0.999 [0.996; 1.003] | B |
| `W7_Q32` | 1.006 [1.001; 1.012] | B | 0.998 [0.994; 1.001] | B |
| `W8_Q01` | 0.996 [0.934; 1.021] | B | 1.005 [0.987; 1.010] | B |
| `W8_Q08` | 0.990 [0.971; 1.001] | B | 1.078 [1.072; 1.086] | B |
| `W9_Q08` | 0.913 [0.899; 0.918] | B | 0.906 [0.900; 0.910] | B |
| `W9_Q32` | 0.965 [0.962; 0.971] | B | 0.983 [0.977; 0.988] | B |

Największa zmiana ilorazu: `W8_Q08` 0.990 -> 1.078 (klasa B bez zmian; rodzina W8 niesie ostrzeżenia nasycenia w `analysis.json`). Czasy bezwzględne niższe niż w K6c (~34%), co nie jest przedmiotem powtórki.

Flaga `CAMPAIGN INVALID` z `analyze.py`: w siedmiu komórkach z R1 (W2_Q01, W2_Q08, W2_Q32, W3_d1, W3_d3, W4_Q08, W4_Q32) sumy artefaktów rozdzielają się według R1 (ALGSTRUCT, STRUCT_R1 wobec OFF, STRUCT). Kontrola `check_obs_r1.py` (raport `results/check_obs_r1.md`) odtwarza te komórki na hoście binarkami o tych samych flagach: sumy hosta równe sumom workera 14/14, deskryptory, wartości i kolejność identyczne na wspólnym prefiksie, bez NULL i luk, R1-ON o 2 rekordy dłuższy - relacja Obs 7/7. Przyczyna: od `fcc5a444` R1 skraca ogon (cor:shift-tail-gap), co def:observable dopuszcza (Val równe, Lat nierosnące). Warunek sum w `analyze.py` pochodzi z K6c, gdzie R1 nie zmieniał ogona, i zakłada równość bajtową.

Decyzja człowieka 2026-11-03: wynik uznany za potwierdzony wg def:observable; flaga `CAMPAIGN INVALID` zostaje w `summary.md` jako wynik zamrożonego analizatora, a to zastrzeżenie wraz z raportem `check_obs_r1.md` jest częścią wyniku. Komórka `W9_Q08` 0.906 [0.900; 0.910] leży blisko progu 10% i pozostaje w klasie B.
