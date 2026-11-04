# R593 / K18 - ponowny pomiar kotwicy bieżącej rewizji na nowym przypięciu silnika

Ponowny pomiar K18 (`results_20260728_K18/`) na silniku `dev/muro@dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb`, w ramach retractordb #593 krok 6 (decyzja człowieka 2026-11-04, wariant a: pomiar zamiast przeredagowania). Artykuł nazywa K18 kotwicą bieżącej rewizji (`master@bc37186`); po przesunięciu pinu artykułu na `dfcc42d2` kotwica musi pochodzić z tego silnika. Ten katalog nie poprawia K18 i nie zastępuje jej liczb: K18 zostaje wynikiem kampanii historycznej na `bc37186`.

Części K6c i H9 tej samej powtórki są w `results_20261103_R593_K6c/` i `results_20261103_R593_H9/`; wszystkie trzy biegną na gałęzi `experiment/20261103_R593`.

## Kryteria - zapisane przed pomiarem

Pomiar składa się z trzech części, jak K18. Wynik jest **POTWIERDZONY**, gdy wszystkie trzy warunki zachodzą jednocześnie:

1. **exactness/replay**: dwa przebiegi potoku 17 strumieni tworzą ten sam zbiór 67 plików artefaktów; dane, deskryptory i cienie są bitowo identyczne, pliki `.meta` identyczne po pominięciu 8-bajtowego czasu utworzenia (reguła K18, `run.sh` bez zmian w części porównawczej);
2. **round-trip**: `a2 == a` i `b2 == b` na wspólnych prefiksach, bez rekordu zastępczego, z prefiksami co najmniej `samples - 10`; `c[2i] == b[i]`, `c[2i+1] == a[i]`;
3. **360 Hz**: jeden przebieg (`config/campaign_rate_r593k18.csv` = wiersz K18 `1,360,1,20000`), sonda z dokładnie 19 999 interwałami (`validate_probe_csv`: żaden rekord nie zaginął), jeden klient `xqry`, harness kończy się sukcesem.

Każdy inny wynik jest niepotwierdzony i idzie do człowieka z surowymi danymi; nie jest powtarzany ani poprawiany po cichu.

**Kryterium czasowe jest opisowe**, bez progu równości z `bc37186`: raport podaje E1 (mediana, p99, max), queue-emission latency (mediana, p99, p99,9, max) i udział maksimum w budżecie slotu 2777,8 µs, obok wartości K18. Liczby nie są korygowane po fakcie. Porównanie z K18 nie jest porównaniem tego samego obciążenia (plan 360 Hz zmienił się między pinami, niżej).

## Różnice wobec K18

| Element | K18 | R593 K18 | Powód |
|---|---|---|---|
| Silnik | `master@bc37186` | `dev/muro@dfcc42d2` | przedmiot pomiaru |
| Gałąź wyników | `experiment/20260728_K18` | `experiment/20261103_R593` | jedna gałąź powtórki #593 |
| Plany exactness | `config/exactness-*.rql` (formy przestarzałe) | `results_20261104_R593_K18/config/exactness-*.rql` po migracji S1/S2 | bieżąca składnia RQL; dowód niżej |
| Plan 360 Hz | `examples/ecg/rec205/rec205-detect.rql` z drzewa `bc37186` | ten sam plik z drzewa `dfcc42d2` (SHA-256 `8c03d005…`), bez migracji | harness bierze plan z drzewa silnika; tekst różni się: `SUBSTRAT 'memory'`, jawne `int(...)` po `SUMC`/`AVG`, BINFILE/TEXTFILE |
| Przełączniki silnika | 4 × `RDB_OPT_*` + `RDB_BENCH_PROBE` | te same + `RDB_OPT_SIMPLIFY_EXPRESSIONS=ON` | przełącznik powstał po K18; ON = wartość domyślna |
| Weryfikacja binarki | `verify_probe_binary`: dokładnie 5 wierszy `--build-info` | wymaga też `SIMPLIFY=ON`, gdy binarka go wypisuje (`lib/common.sh`, test w `tests/test_orchestration.sh`) | bez tej zmiany nadzorca i `worker/run_study.sh` odrzucają Release-Probe `dfcc42d2`; decyzja człowieka 2026-11-04 |
| Repozytorium kodu na workerze | `/home/michal/retractordb` | `/home/michal/R593` (klon z powtórki R593) | `~/retractordb` na Pi stoi na innej gałęzi |
| Repozytorium kodu nadzorcy | `../retractordb` | świeży klon `dev/muro` poza repozytoriami (`--code-repo`) | `examples/ecg/rec205` na hoście zawiera 32 ignorowane artefakty z 2026-10-28, których `require_input_dirs_pristine` nie przepuszcza; nadzorca bierze z repo tylko `origin/dev/muro` |

`run.sh` jest kopią `results_20260728_K18/run.sh`; zmienione są wyłącznie pin (`dev/muro`, `dfcc42d2…`, skrót `dfcc42d2`, gałąź wyników), tekst pomocy i katalog konfiguracji (`$SCRIPT_DIR/config`). Część porównawcza jest bez zmian.

## Migracja planów exactness (S1, S2)

`paper-arXiv/measurment-tool/migrate_corpus.py` (commit `08bd80f`) z binarką Debug `dev/muro:dfcc42d2` z czystego drzewa jako odniesieniem i silnikiem pod testem. Oryginały są zamrożonymi plikami K18 (sumy równe `results_20260728_K18/exactness/README.md`). Wynik w `config/migration.tsv`:

- M1 `SAME` we wszystkich trzech: odniesienie i silnik pod testem to ta sama binarka, więc typy się nie różnią; plan nie dostaje `to_integer(...)`, a wydruk `-c` zostaje ten sam. Wyniki `SUMC`/`AVG` w planie replay są na `dfcc42d2` typu RATIONAL (w K18 INTEGER); teza replay dotyczy determinizmu dwóch przebiegów tego samego silnika, nie wartości K18;
- S `MIGRATED`: replay 3 deklaracje FILE + 4 formy przyrostkowe, round-trip zapis 1 deklaracja, odczyt 2;
- dowód: wydruk `-c` przed i po migracji identyczny (kolumny `c_orig_sha256` = `c_migrated_sha256`), `--verbose` po migracji bez ostrzeżenia `is deprecated` (3/1/2 -> 0/0/0).

## Uruchomienie

Na workerze (`~/R593` na `dev/muro` = `dfcc42d2`, build `scripts/buildrdb.sh conan ninja probe`):

```bash
./results_20261104_R593_K18/run.sh --code-repo /home/michal/R593 --preflight-only
./results_20261104_R593_K18/run.sh --code-repo /home/michal/R593
```

Na nadzorcy, po zatwierdzeniu exactness/replay:

```bash
./start_supervisor.sh rate_r593k18 \
  --experiment-id 20261104_R593_K18 \
  --experiment-branch experiment/20261103_R593 \
  --code-branch dev/muro \
  --code-repo <świeży klon dev/muro> \
  --worker 192.168.88.13 \
  --worker-code-repo /home/michal/R593
```

## Stan

W toku (kryteria zapisane przed pomiarem).
