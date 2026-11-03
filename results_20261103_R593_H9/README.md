# R593 / H9 - powtórka kontrolna przy Q=8 na nowym przypięciu silnika

Powtórka kontrolna wyniku `tab:h9-primary` (kampania K26v3, `results_20260814_K26v3/`) na silniku `dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb`, w ramach retractordb #593 (wariant C, decyzja człowieka 2026-11-03). Ten katalog nie poprawia K26v3 i nie zastępuje jej liczb: werdykt K26v3 zostaje wynikiem kampanii historycznej z jej rewizją. Powtórka odpowiada na jedno pytanie: czy na silniku, który ma zostać nowym przypięciem artykułu, rozstrzygająca klasa Q=8 daje ten sam wynik progowy.

Część K6c tej samej powtórki jest w `results_20261103_R593_K6c/`; obie biegną na gałęzi `experiment/20261103_R593`.

## Kryteria - zapisane przed pomiarem

Rodzina jest **POTWIERDZONA**, gdy jednocześnie:

1. bramki P6 bez Flinka są czyste: `corpus_validity`, `oracle_mutants`, `public_identity`, `near_miss_controls`, `no_materialization` (funkcje `run_gates.py` K26v3);
2. redukcja metryki pierwotnej (logiczne bajty substratu na rekord publiczny, liczniki LOGICAL z P6) przy Q=8 wobec ablacji minimalnej rodziny równa się predykcji zamrożonej w K26v3 (`verdict.PREDECLARED_RDB`: F9-R2 1/2, F9-R1 1/2, F9-X 7/12) w tolerancji `CURVE_TOLERANCE` = 0,005 i jest nie mniejsza niż 40%;
3. górna granica sparowanego bootstrapu 95% CI ceny czasowej (iloraz median bloków DEFAULT/ablacja, `verdict.paired_bootstrap_ratio`, 10 000 replikacji, to samo ziarno co K26v3) nie przekracza 1,05.

Powtórka jako całość jest potwierdzona, gdy potwierdzone są trzy rodziny z trzech. Wynik niepotwierdzony nie jest naprawiany ani powtarzany po cichu: idzie do człowieka razem z liczbami. Wartości ceny K26v3 (0,917 / 0,980 / 0,740) są raportowane obok, ale nie są kryterium: powtórka sprawdza próg, nie równość punktu.

Ocenę liczy `analyze_r593.py` (kod 0 - 3/3, 1 - mniej, 2 - brak werdyktu z powodu aparatury lub niepełnych danych).

## Zakres i odstępstwa od K26v3

| Element | K26v3 | R593 | Powód |
|---|---|---|---|
| Silnik | `856ee54b` | `dfcc42d2` | przedmiot powtórki |
| Siatka Q | 1, 2, 4, 8, 16, 32 | tylko 8 | rozstrzygająca klasa; 240 z 1440 przebiegów |
| Bloki i kolejność | `blocks.tsv` (20 bloków, ziarno K26v3) | wiersze Q=8 tego samego pliku | ta sama randomizacja; `freeze_check.sh` sprawdza podzbiór |
| Rate | kalibracja P7 -> ANEKS-1 | zamrożony ANEKS-1 K26v3 (`rate_scale=4`, suma `fc6e549a…` z `WERDYKT.md`) | to samo obciążenie co w kampanii; szybszy silnik tylko obniża zajętość slotu |
| Plany | `DECLARE ... FILE` | `TEXTFILE` (migracja S1, niżej) | bieżąca składnia (#346); wydruk `-c` identyczny |
| Flink | natural/manual, oracle wartości | pominięty | port Flinka się nie zmienił; redukcja wobec Flinka i `oracle_values` zostają wynikiem K26v3 |
| Kalibracja, pilot | wykonane | brak | rate zamrożony; pilot dotyczył konstrukcji aparatury |
| Profile | `build/K26v3-*` w `~/K26v3` | `build/R593-*` w `~/R593` | brak mieszania binariów kampanii |
| Usługa workera | `k26v3-p8.service` | `r593-p8.service` | jw. |

Warm-up (jeden przebieg Q=32 na profil poza wynikiem) zostaje jak w K26v3.

## Migracja planów (S1)

Plany K26v3 (`migration/orig/`) przeszły `paper-arXiv/measurment-tool/migrate_corpus.py` (commit `08bd80f`) z binarką pinu `40c28dbe` jako odniesieniem i Release `dfcc42d2` jako silnikiem pod testem. Wszystkie 21: M1 `SAME`, S `MIGRATED` (S1 2-9 podstawień, S2 0); statusy i sumy SHA-256 obu wersji są w `migration/migration.tsv`. Dowód narzędzia: ten sam wydruk `-c` przed i po podstawieniu, `--verbose` bez ostrzeżenia o `FILE`, każdy zmieniony wiersz po cofnięciu podstawienia jest wierszem oryginału. Plany są bajt w bajt równe planom z przebiegu kontroli zgodności z 2026-11-02 (komentarz w #593).

`gen_corpus.py` w tym katalogu wypisuje `TEXTFILE` zamiast `FILE` (jedyna zmiana generatora) i `gen_corpus.py --check` potwierdza, że odtwarza 37 plików korpusu (21 planów + dane) bajt w bajt. Dane `data/` są identyczne z K26v3. `validate_corpus.py` ma tę samą zamianę w historycznym mutancie.

## Zmiany w skopiowanej aparaturze

Pliki skopiowane z `results_20260814_K26v3/`; poza zamianą nazw (`K26v3-` -> `R593-`, `~/K26v3` -> `~/R593`, `k26v3_*` -> `r593_*`, `k26v3-p8` -> `r593-p8`) zmienia się tylko:

- `run_matrix_worker.py`: 80 przebiegów na rodzinę (Q=8) zamiast 480; ANEKS-1 czytany z tego katalogu (śledzony w git);
- `calib/gen_calib.py`: wyrażenie deklaracji przyjmuje `TEXTFILE`/`BINFILE`/`DEVICE` obok `FILE`. Bez tego `scale_plan` odrzuciłby każdy plan po migracji i macierz padłaby na pierwszej komórce. Równoważność: dla 21 planów `scale_plan(po migracji, 4)` równa się `scale_plan(oryginał, 4)` z `FILE` -> `TEXTFILE`, a przy skali 1 plan zostaje bez zmian (`gen_calib.py --check`);
- `mechanism_table.py`: bramka `--gate` czyta zrzuty planu i wiersze sondy z dowodu korpusu powtórki (`corpus_validation/plans/<profil>/<plan>.{plan,stderr}`, silnik `dfcc42d2`) zamiast z pilota K26v3 (`pilot/out`, silnik `856ee54`), którego powtórka nie kopiuje. Plik `.stderr` niesie te same wiersze co dawne `.probe`; zrzuty planu różnią się od pilota wyłącznie nazwami substratów kompilatora (nowy silnik dopisuje wielkość przesunięcia, np. `STREAM_TIMEMOVE_2_A`). Bramka przechodzi: (a) 12 komórek planów głównych bez zmian, (b) różnica wobec wersji obalonej dokładnie z1/z2/`STREAM_HASH_CA_CB`, (c), (d);
- `oracle_values.py`: usunięty jeden znak `U+00AD` (miękki dywiz) w komentarzu, wiersz 321 - obecny także w zamrożonym oryginale K26v3, który zostaje bez zmian;
- `collect_p8_archives.sh`: komplet 240/240;
- `freeze_check.sh`: napisany od nowa na wzór K26v3, bez Flinka, pilota i kalibracji; dodatkowo sprawdza przypięcie silnika, podzbiór bloków Q=8 i sumę ANEKS-1;
- `test_apparatus.py`, `test_pipeline.py`: liczby 480/1440 -> 80/240, cytaty § czytane z predeklaracji K26v3, cztery testy pominięte z podanym powodem (pilot, eksport z Flinkiem, analizator kalibracji);
- nowy `analyze_r593.py` - ocena kryteriów, wyłącznie funkcjami aparatury K26v3.

## Znane ograniczenie odziedziczone po K26v3

Historyczny mutant F9-X w `validate_corpus.py` ma `FROM` w osobnym wierszu, więc silnik odrzuca go błędem składni (`mismatched input '<EOF>' expecting ... FROM`), a nie błędem odwołania do składnika przeplotu `#`. Tak samo było w zamrożonym dowodzie K26v3 (`corpus_validation/plans/*/historical_invalid_F9_X.stderr`). Wynik „4/4 odrzucone" dowodzi więc odrzucenia, nie granicy języka. Kopia zostaje wierna oryginałowi; granicę `#` dokumentuje osobno 31 planów F9-X w kontroli zgodności #593.

## Przebieg

```bash
# host: dowód korpusu na profilach hosta (build/R593-* w retractordb @ dfcc42d2)
./build_profiles.sh && ./validate_corpus.py && ./freeze_check.sh preflight
# worker: profile R593-* (K6_CCACHE=1 K6_SETCAP=1), potem z hosta:
./capture_worker.py                      # ANEKS-2/3, commit i push
./bind_campaign.py                       # ANEKS-0 - od tej chwili rewizje są związane
# worker: P6
CODE_REPO=/home/michal/R593 OUT=/home/michal/r593_gates_rdb ./run_main_rdb.sh
# host: start łańcucha P8 pod systemd; potem host może być wyłączony
./start_matrix_p8.sh
./collect_p8_archives.sh                 # kiedykolwiek; po komplecie COLLECT_COMPLETE
./analyze_r593.py --p6 <kopia P6> --raw <rozpakowane archiwa> --out results/R593_H9.md
```

Kolejność wobec K6c: harness K6c dopisuje wyniki do gałęzi przez `commit --amend`, a ANEKS-0 wiąże SHA eksperymentu, więc wiązanie H9 następuje dopiero po zakończeniu siedmiu badań K6c.

## Stan

Przygotowanie (2026-11-03): korpus, migracja, aparatura, dowód korpusu 84/84 + 4/4 na hoście. Pomiar nie rozpoczęty.
