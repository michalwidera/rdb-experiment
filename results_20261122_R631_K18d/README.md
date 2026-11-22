# R631 K18d - kotwica bieżącej rewizji na rewizji silnika R = `758be53b`

Powtórzenie R618 K18c (`results_20261111_R618_K18c/`, silnik `dev/muro@16c516f9`) na silniku `dev/muro@758be53b3b8339d176dc678f9a75a259b8926925`, w ramach retractordb #632, etap 1 (przesunięcie pinu silnika artefaktu `16c516f9` -> `758be53b`). Decyzja człowieka 2026-11-21: kotwica czasowa 360 Hz jest mierzona na nowo (wariant a). Ten katalog nie poprawia K18, R593 K18, R593 K18b ani R618 K18c i nie zastępuje ich liczb: każda zostaje wynikiem swojej rewizji. Wynik porównania korpusu na R wobec `16c516f9` (kontrola zgodności, K24e, K24f, przykłady ON/OFF, tryb dowodowy, `doc_drift`) jest w `results_20261121_R631/` (R631 POTWIERDZONY).

Powód pomiaru: między `16c516f9` a R w `src/` zmieniło się 9 plików (62 wiersze dodane, 33 usunięte). Zmiany semantyczne są dwie, obie w rachunku kompilatora: #626 (`a9e66032`, w planie z choćby jedną zmienną `VAR` faktoryzacja przesunięć przez przeplot nie jest stosowana) i `ce2c65eb` (walidacja interwału rozplotu `&` / `%` w `compiler.cpp`). Trzecia zmiana zachowania jest poza silnikiem i poza ścieżką pomiaru: #621 (`754ea631`, `xtrdbLauncher.cpp`, nieznana opcja `xtrdb`). Pozostałe to komentarz w `src/retractor/lib/CLAUDE.md` (`86ad8f53`) i poprawki CTidy bez zmiany zachowania: `e7621f2f` (`qry.cpp` buduje wiersz wektora w miejscu zamiast z `initializer_list`; `payload.cc` bierze napis przez referencję zamiast kopii), `39b59c69` (`ipcServer.hpp`: typ bazowy `DrainStep`, `nextProbe_` bez jawnego `{}` - domyślny konstruktor `time_point` i tak daje epokę; nawiasy w `processLimits.hpp`; rzutowanie w `qTree.cpp`). Żaden z planów tego pomiaru nie deklaruje `VAR`. `&` i `%` występują w `config/exactness-roundtrip-read.rql`; wydruk `-c` tych trzech planów jest na R bajtowo taki sam jak na `16c516f9` (`config/migration.tsv`). Kotwica jest opisana w artykule jako pomiar rewizji pinu, więc liczb R618 K18c nie przypisuję R bez pomiaru.

## Kryteria - zapisane przed pomiarem

Takie same jak w R618 K18c i R593 K18b. Wynik jest **POTWIERDZONY**, gdy wszystkie trzy warunki zachodzą jednocześnie:

1. **exactness/replay**: dwa przebiegi potoku 17 strumieni tworzą ten sam zbiór 67 plików artefaktów; dane, deskryptory i cienie są bitowo identyczne, pliki `.meta` identyczne po pominięciu 8-bajtowego czasu utworzenia (reguła K18, część porównawcza `run.sh` bez zmian);
2. **round-trip**: `a2 == a` i `b2 == b` na wspólnych prefiksach, bez rekordu zastępczego, z prefiksami co najmniej `samples - 10`; `c[2i] == b[i]`, `c[2i+1] == a[i]`;
3. **360 Hz**: jeden przebieg (`config/campaign_rate_r631k18d.csv` = wiersz K18 `1,360,1,20000`), sonda z dokładnie 19 999 interwałami (`validate_probe_csv`: żaden rekord nie zaginął), jeden klient `xqry`, harness kończy się sukcesem.

Każdy inny wynik jest niepotwierdzony i idzie do człowieka z surowymi danymi; nie jest powtarzany ani poprawiany po cichu. Czerwony wynik zatrzymuje etap 1 #632 przed przesunięciem pinu w `rdb-artifact` (etap 3); pin `16c516f9` i jego kotwica R618 K18c zostają wtedy w mocy.

**Kryterium czasowe jest opisowe**, bez progu: raport podaje E1 (mediana, p99, max), queue-emission latency (mediana, p99, p99,9, max), wake-lag mediana i max oraz udział maksimum w budżecie slotu 2777,8 µs, obok wartości R618 K18c, R593 K18b, R593 K18 i K18. Liczby nie są korygowane po fakcie. Plan 360 Hz jest tym samym tekstem co w R618 K18c, R593 K18b i R593 K18 (`examples/ecg/rec205/rec205-detect.rql`, SHA-256 `8c03d0051285ca397e69ea9158e89119f6be52d734b6a2b2e975e6f19e7a35ab` także w R), a dane wejściowe `examples/ecg/rec205/` są bez zmian między `16c516f9` a R (pusty `git diff`). Jeden przebieg nie wystarcza do przypisania różnicy silnikowi; raport jej tak nie nazywa.

## Różnice wobec R618 K18c

| Element | R618 K18c | R631 K18d | Powód |
|---|---|---|---|
| Silnik | `dev/muro@16c516f9` | `dev/muro@758be53b` | przedmiot pomiaru |
| Gałąź wyników | `experiment/20261111_R618` | `experiment/20261122_R631` | gałąź K18d #632 (założona za zgodą człowieka 2026-11-22) |
| Repozytorium kodu na workerze | `/home/michal/R618` | `/home/michal/R631` (świeży klon `dev/muro`) | osobny klon na rewizję |
| Kampania wykonawcza | `config/campaign_rate_r618k18c.csv` | `config/campaign_rate_r631k18d.csv` (ten sam wiersz, ten sam SHA-256 `69f82ada…`) | osobny identyfikator kampanii |

`run.sh` jest kopią `results_20261111_R618_K18c/run.sh`; zmienione są wyłącznie pin (`758be53b…`, skrót `758be53b`), gałąź wyników i tekst pomocy (komentarz nagłówka i `usage`). Plany `config/exactness-*.rql` są bajtowo równe planom R618 K18c, R593 K18b i R593 K18. Dowód migracji S1/S2 powtórzony na R jest w `config/migration.tsv`: `paper-arXiv/measurment-tool/migrate_corpus.py` z binarką `build/R631-Release` (R, czyste drzewo, SHA-256 `xretractor` `9d5950c6c5ad5d173389fdd9256d8988461dc340aa8a153eb8f1ef28e27f2f9b`) jako odniesieniem i silnikiem pod testem, oryginały to zamrożone plany K18 (SHA-256 z `results_20260728_K18/exactness/README.md`); plik jest bajtowo równy `results_20261111_R618_K18c/config/migration.tsv` (M1 `SAME`, S `MIGRATED` 3+4 / 1 / 2, wydruk `-c` przed i po migracji identyczny, `--verbose` po migracji bez ostrzeżenia `is deprecated`), a plany po migracji są bajtowo równe `config/exactness-*.rql`. Metoda sum wydruku `-c` (stdout i stderr `xretractor p.rql -c` w katalogu tymczasowym, ścieżka binarki zamieniona na `XR`) odtwarza przed użyciem plik R618 K18c bajt w bajt na binarce pinu `16c516f9` (`build/R618-Release`, `955fdc71…`).

## Uruchomienie

Na workerze (`~/R631` na `dev/muro` = R, build ręczny `scripts/buildrdb.sh conan ninja probe`, `cmake --install build/Release-Probe`, bo strażnik buildu nadzorcy nie zna `scripts/buildrdb/research.sh`):

```bash
./results_20261122_R631_K18d/run.sh --code-repo /home/michal/R631 --preflight-only
./results_20261122_R631_K18d/run.sh --code-repo /home/michal/R631
```

Na nadzorcy, po zatwierdzeniu exactness/replay:

```bash
./start_supervisor.sh rate_r631k18d \
  --experiment-id 20261122_R631_K18d \
  --experiment-branch experiment/20261122_R631 \
  --code-branch dev/muro \
  --code-repo <świeży klon dev/muro> \
  --worker 192.168.88.13 \
  --worker-code-repo /home/michal/R631 \
  --skip-build
```

## Stan

**POTWIERDZONY 2026-11-22** - wszystkie trzy warunki z kryteriów zachodzą na `dev/muro@758be53b`, binarka Release-Probe z `~/R631` (SHA-256 `xretractor` `d452c07f242933a74812f89c4950a0bb148b051134683740852d8350e78556ae`, `xqry` `4f8b4d48f6ce655acda3345e93ce3876ecf51f69e77504be993721cf5bcd457e`, `xtrdb` `e137fc43843ba853a54b5eaa3eb39ea6a2f6c4c30a8ce00701f964ba5f323947`; binarki w `~/.local/bin` bajt w bajt równe buildowi; `--build-info`: 5 × `RDB_OPT_*=ON`, `RDB_BENCH_PROBE=ON`; `--help`: `Branch: dev/muro:758be53b`, GCC 14.2.0).

1. exactness/replay (`exactness/`, commit `f918b4d`): 2 przebiegi, 67 artefaktów, 51 identycznych bitowo, 16 `.meta` identycznych po pominięciu czasu utworzenia; zero różnic. Opisowo, poza kryterium: lista artefaktów i artefakty bez `.meta` są bajt w bajt równe artefaktom R618 K18c na `16c516f9`, a `configuration.sha256` jest ten sam;
2. round-trip: `a2 == a`, `b2 == b` bez rekordu zastępczego, `c[2i] == b[i]`, `c[2i+1] == a[i]`; rekordy a=19 999, b=19 999, c=39 994, a2=19 996, b2=19 997 (prefiksy >= 19 990), te same liczby co w R618 K18c, R593 K18b i R593 K18 (`roundtrip_compare.txt` bajtowo równy K18c);
3. 360 Hz (`rate_r631k18d/study_01/`, commit `913147d`): 19 999 interwałów w sondzie (żaden rekord nie zaginął), jeden klient `xqry` (pusty `xqry_1.err`), harness zakończony sukcesem, governor `performance` w czasie badania, `throttled=0x0`.

Liczby czasowe (opisowo, jeden przebieg na każdej rewizji). Plan 360 Hz jest tym samym tekstem co w R618 K18c, R593 K18b i R593 K18, ale jeden przebieg nie wystarcza, by różnicę wobec nich przypisać silnikowi; w K18 plan był innym tekstem.

| Metryka | K18 `bc37186` | R593 K18 `dfcc42d2` | R593 K18b `e389edd3` | R618 K18c `16c516f9` | R631 K18d `758be53b` |
|---|---|---|---|---|---|
| E1 mediana | 1312,4 µs | 885,7 µs | 916,4 µs | 851,6 µs | 870,6 µs |
| E1 p99 | 1617,9 µs | 1105,6 µs | 1115,7 µs | 1064,8 µs | 1075,7 µs |
| E1 max | 1838,5 µs | 1303,0 µs | 1284,8 µs | 1225,9 µs | 1257,0 µs |
| max E1 / budżet 2777,8 µs | - | 46,9% | 46,3% | 44,1% | 45,3% |
| queue-emission mediana | 1372,8 µs | 937,2 µs | 970,8 µs | 906,6 µs | 925,6 µs |
| queue-emission p99 | 1718,6 µs | 1211,1 µs | 1215,0 µs | 1168,8 µs | 1177,7 µs |
| queue-emission p99,9 | 1832,5 µs | 1291,4 µs | 1276,5 µs | 1229,4 µs | 1240,5 µs |
| queue-emission max | 1944,0 µs | 1420,3 µs | 1426,1 µs | 1351,5 µs | 1372,4 µs |
| max queue-emission / budżet 2777,8 µs | 70,0% | 51,1% | 51,3% | 48,7% | 49,4% |
| wake_lag mediana / max | 20,7 / 54,3 µs | 22,2 / 71,2 µs | 22,3 / 69,6 µs | 22,3 / 106,0 µs | 22,7 / 73,6 µs |

Wobec R618 K18c wszystkie podane kwantyle E1 i queue-emission są wyższe o 0,8-2,5%, wobec R593 K18b niższe o 2,2-5,0%; każda z tych wartości leży między R618 K18c a R593 K18b. Maksimum wake_lag wróciło do poziomu R593 K18 i K18b (73,6 µs). Delta silnika (#626, `ce2c65eb`) dotyczy rachunku kompilatora, nie ścieżki wykonania ani IPC, a pomiar to jeden przebieg na każdej rewizji, więc tych różnic nie przypisuję silnikowi.

Stan workera: start ok. 07:07 (2026-11-22, po włączeniu przez człowieka), potem build Release-Probe w `~/R631` (07:12-08:20), exactness 08:23-08:29 i badanie 360 Hz 08:35-08:36. Kampania ma jedno badanie, więc nadzorca nie restartował workera. W trakcie exactness i badania nikt poza nadzorcą nie łączył się z workerem: start `run.sh` przez `timeout 30 ssh` z procesem odczepionym, oczekiwanie lokalnym `sleep`, jedno logowanie po końcu (08:33), potem kontrola kopii i synchronizacja gałęzi (do 08:35) i tylko sesje nadzorcy. Logowania w trakcie buildu (jedno o 07:17, potem co 5 min od ok. 08:12 do 08:22) były przed oboma pomiarami. Kolejność jak w R618 K18c (build, exactness, badanie).

Odstępstwa w przebiegu: (a) znane z R593 K18, K18b i R618 K18c - strażnik buildu nadzorcy nie zna `scripts/buildrdb/research.sh`, więc build był ręczny (`scripts/buildrdb.sh conan ninja probe`, `cmake --install build/Release-Probe`), a nadzorca szedł z `--skip-build` i weryfikacją zainstalowanej binarki; (b) pierwsze uruchomienie nadzorcy (08:34:53) zatrzymało się na wstępnym preflighcie (`repozytorium wynikow workera nie jest czyste`), zanim cokolwiek uruchomiło na workerze: w klonie `~/rdb-experiment` zostały nieśledzone kopie 15 plików `exactness/`. Wszystkie 15 porównano bajtowo z `origin/experiment/20261122_R631` (`f918b4d`, zero różnic), usunięto i zsynchronizowano gałąź; drugie uruchomienie dało badanie z tego katalogu. Pomiaru nie powtarzano. Wyniki exactness skopiowane z workera na nadzorcę i zacommitowane tam (`f918b4d`); sumy kopii na workerze porównane z plikami commitu przed wypchnięciem.
