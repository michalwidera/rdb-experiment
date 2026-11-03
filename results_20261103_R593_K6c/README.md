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

Przygotowanie (2026-11-03): plany, migracja, próba na hoście. Pomiar nie rozpoczęty.
