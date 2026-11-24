# R648 K18e - kotwica bieżącej rewizji na rewizji silnika R = `7e5659f4`

Powtórzenie R631 K18d (`results_20261122_R631_K18d/`, silnik `dev/muro@758be53b`) na silniku `dev/muro@7e5659f4c070b39f1c1a711217fb98548ca60cf4`, w ramach retractordb #649, etap 1 (przesunięcie pinu silnika artefaktu `758be53b` -> `7e5659f4`, krok A5 z #634). Decyzja człowieka 2026-11-23 (#649, D2): kotwica czasowa 360 Hz jest mierzona na nowo. Ten katalog nie poprawia K18, R593 K18, R593 K18b, R618 K18c ani R631 K18d i nie zastępuje ich liczb: każda zostaje wynikiem swojej rewizji. Wynik porównania korpusu na R wobec `758be53b` (kontrola zgodności, K24e, K24f, przykłady ON/OFF, tryb dowodowy, `doc_drift`) jest w `results_20261124_R648/`.

Powód pomiaru (D2): między `758be53b` a R w `src/` zmieniło się 28 plików (962 wiersze dodane, 243 usunięte), a #640 (`b28b53fe`, `12a518ff`, `1085f44b`) zmienił kod, który kotwica mierzy: oś czasu `TimeLine` (`src/retractor/lib/CRSMath.*`) liczy chwilę slotu na licznikach `int64` zamiast w `rational<int>`, `getNextTimeSlot()` zwraca wynik z błędem horyzontu, `rtSlotDeadlineMs()` (`executor_rt.cpp`) liczy termin slotu w `__int128`, a pętla wykonawcy (`executorsm.cpp`) publikuje stan osi pod `core_mutex` i obsługuje horyzont (`timing.horizon`, restart na horyzoncie). Pozostałe poprawki są w rachunku kompilatora i w mapach odczytu: #635 i #644 (ogony Θ, ~Θ, `-`, `+`, `#`), #636 (mapy odczytu `Hash` / `Div` / `Mod` / `Subtract` / `Add` w `SOperations.hpp`, liczone w czasie pracy), #637 (pojemności historii), #647 (`computeLogicalOrigin()`, `expandIndexWildcards()`). Plany tego pomiaru są tymi samymi tekstami co w R631 K18d; wydruk `-c` trzech planów exactness jest na R bajtowo taki sam jak na `758be53b` (`config/migration.tsv`), a kontrola zgodności R648 pokazała, że R odtwarza replay K18 bajt w bajt. Kotwica jest opisana w artykule jako pomiar rewizji pinu, więc liczb R631 K18d nie przypisuję R bez pomiaru.

## Kryteria - zapisane przed pomiarem

Takie same jak w R631 K18d, R618 K18c i R593 K18b. Wynik jest **POTWIERDZONY**, gdy wszystkie trzy warunki zachodzą jednocześnie:

1. **exactness/replay**: dwa przebiegi potoku 17 strumieni tworzą ten sam zbiór 67 plików artefaktów; dane, deskryptory i cienie są bitowo identyczne, pliki `.meta` identyczne po pominięciu 8-bajtowego czasu utworzenia (reguła K18, część porównawcza `run.sh` bez zmian);
2. **round-trip**: `a2 == a` i `b2 == b` na wspólnych prefiksach, bez rekordu zastępczego, z prefiksami co najmniej `samples - 10`; `c[2i] == b[i]`, `c[2i+1] == a[i]`;
3. **360 Hz**: jeden przebieg (`config/campaign_rate_r648k18e.csv` = wiersz K18 `1,360,1,20000`), sonda z dokładnie 19 999 interwałami (`validate_probe_csv`: żaden rekord nie zaginął), jeden klient `xqry`, harness kończy się sukcesem.

Każdy inny wynik jest niepotwierdzony i idzie do człowieka z surowymi danymi; nie jest powtarzany ani poprawiany po cichu. Czerwony wynik zatrzymuje etap 1 #649 przed przesunięciem pinu w `rdb-artifact` (etapy 2-3); pin `758be53b` i jego kotwica R631 K18d zostają wtedy w mocy.

**Kryterium czasowe jest opisowe**, bez progu: raport podaje E1 (mediana, p99, max), queue-emission latency (mediana, p99, p99,9, max), wake-lag mediana i max oraz udział maksimum w budżecie slotu 2777,8 µs, obok wartości R631 K18d, R618 K18c, R593 K18b, R593 K18 i K18. Liczby nie są korygowane po fakcie. Plan 360 Hz jest tym samym tekstem co w R631 K18d, R618 K18c, R593 K18b i R593 K18 (`examples/ecg/rec205/rec205-detect.rql`, SHA-256 `8c03d0051285ca397e69ea9158e89119f6be52d734b6a2b2e975e6f19e7a35ab` także w R), a dane wejściowe `examples/ecg/rec205/` są bez zmian między `758be53b` a R (pusty `git diff`). Jeden przebieg nie wystarcza do przypisania różnicy silnikowi; raport jej tak nie nazywa, także wtedy, gdy kierunek zgadza się ze zmianą #640.

## Różnice wobec R631 K18d

| Element | R631 K18d | R648 K18e | Powód |
|---|---|---|---|
| Silnik | `dev/muro@758be53b` | `dev/muro@7e5659f4` | przedmiot pomiaru |
| Gałąź wyników | `experiment/20261122_R631` | `experiment/20261124_R648` | gałąź K18e #649 (założona za zgodą człowieka 2026-11-24) |
| Repozytorium kodu na workerze | `/home/michal/R631` | `/home/michal/R648` (świeży klon `dev/muro`) | osobny klon na rewizję |
| Kampania wykonawcza | `config/campaign_rate_r631k18d.csv` | `config/campaign_rate_r648k18e.csv` (ten sam wiersz, ten sam SHA-256 `69f82ada…`) | osobny identyfikator kampanii |

`run.sh` jest kopią `results_20261122_R631_K18d/run.sh`; zmienione są wyłącznie pin (`7e5659f4…`, skrót `7e5659f4`), gałąź wyników i tekst pomocy (komentarz nagłówka i `usage`). Plany `config/exactness-*.rql` są bajtowo równe planom R631 K18d, R618 K18c, R593 K18b i R593 K18. Dowód migracji S1/S2 powtórzony na R jest w `config/migration.tsv`: `paper-arXiv/measurment-tool/migrate_corpus.py` z binarką `build/R648-Release` (R, czyste drzewo, SHA-256 `xretractor` `beab738586af50960a2a5f102e47f8007eb52a9a09e6005db6f964de7169ed93`, ta sama co w `results_20261124_R648/`) jako odniesieniem i silnikiem pod testem, oryginały to zamrożone plany K18 (`config/exactness-*.rql` repozytorium, SHA-256 z `results_20260728_K18/exactness/configuration.sha256`); plik jest bajtowo równy `results_20261122_R631_K18d/config/migration.tsv` (M1 `SAME`, S `MIGRATED` 3+4 / 1 / 2, wydruk `-c` przed i po migracji identyczny, `--verbose` po migracji bez ostrzeżenia `is deprecated`), a plany po migracji są bajtowo równe `config/exactness-*.rql`. Metoda sum wydruku `-c` (stdout i stderr `xretractor p.rql -c` w katalogu tymczasowym, ścieżka binarki zamieniona na `XR`) odtwarza przed użyciem plik R631 K18d bajt w bajt na binarce pinu `758be53b` (`build/R631-Release`, `9d5950c6…`).

## Uruchomienie

Na workerze (`~/R648` na `dev/muro` = R, build ręczny `scripts/buildrdb.sh conan ninja probe`, `cmake --install build/Release-Probe`, bo strażnik buildu nadzorcy nie zna `scripts/buildrdb/research.sh`):

```bash
./results_20261124_R648_K18e/run.sh --code-repo /home/michal/R648 --preflight-only
./results_20261124_R648_K18e/run.sh --code-repo /home/michal/R648
```

Na nadzorcy, po zatwierdzeniu exactness/replay:

```bash
./start_supervisor.sh rate_r648k18e \
  --experiment-id 20261124_R648_K18e \
  --experiment-branch experiment/20261124_R648 \
  --code-branch dev/muro \
  --code-repo <świeży klon dev/muro> \
  --worker 192.168.88.13 \
  --worker-code-repo /home/michal/R648 \
  --skip-build
```

## Stan

**POTWIERDZONY 2026-11-24** - wszystkie trzy warunki z kryteriów zachodzą na `dev/muro@7e5659f4`, binarka Release-Probe z `~/R648` (SHA-256 `xretractor` `b49dfbca6da8f93f994ddb859fa37469d3750313a7df570682eb52120942dd51`, `xqry` `d2bfe5f27624f2270634e8de1b80ad3fa8f20cf1ff4681ade9cb0e4192120425`, `xtrdb` `eb0e5b0d470303d7130e4dae9c6219bc8db9dfec9f05afe9f948cc702fbc1c8e`; `xretractor` w `~/.local/bin` bajt w bajt równy buildowi; `--build-info`: 5 × `RDB_OPT_*=ON`, `RDB_BENCH_PROBE=ON`; `--help`: `Branch: dev/muro:7e5659f4`, GCC 14.2.0).

1. exactness/replay (`exactness/`, commit `983192c`): 2 przebiegi, 67 artefaktów, 51 identycznych bitowo, 16 `.meta` identycznych po pominięciu czasu utworzenia; zero różnic. Opisowo, poza kryterium: `replay_artifacts.txt`, `replay_hashes_run1.txt`, `replay_hashes_run2.txt` i `configuration.sha256` są bajt w bajt równe plikom R631 K18d na `758be53b`;
2. round-trip: `a2 == a`, `b2 == b` bez rekordu zastępczego, `c[2i] == b[i]`, `c[2i+1] == a[i]`; rekordy a=19 999, b=19 999, c=39 994, a2=19 996, b2=19 997 (prefiksy >= 19 990), te same liczby co w R631 K18d, R618 K18c, R593 K18b i R593 K18 (`roundtrip_compare.txt` bajtowo równy K18d);
3. 360 Hz (`rate_r648k18e/study_01/`, commit `b61f2c8`): 19 999 interwałów w sondzie (żaden rekord nie zaginął), jeden klient `xqry` (pusty `xqry_1.err`), harness zakończony sukcesem, governor `performance` w czasie badania, `throttled=0x0`.

Liczby czasowe (opisowo, jeden przebieg na każdej rewizji). Plan 360 Hz jest tym samym tekstem co w R631 K18d, R618 K18c, R593 K18b i R593 K18, ale jeden przebieg nie wystarcza, by różnicę wobec nich przypisać silnikowi; w K18 plan był innym tekstem.

| Metryka | K18 `bc37186` | R593 K18 `dfcc42d2` | R593 K18b `e389edd3` | R618 K18c `16c516f9` | R631 K18d `758be53b` | R648 K18e `7e5659f4` |
|---|---|---|---|---|---|---|
| E1 mediana | 1312,4 µs | 885,7 µs | 916,4 µs | 851,6 µs | 870,6 µs | 864,4 µs |
| E1 p99 | 1617,9 µs | 1105,6 µs | 1115,7 µs | 1064,8 µs | 1075,7 µs | 1075,9 µs |
| E1 max | 1838,5 µs | 1303,0 µs | 1284,8 µs | 1225,9 µs | 1257,0 µs | 1200,3 µs |
| max E1 / budżet 2777,8 µs | - | 46,9% | 46,3% | 44,1% | 45,3% | 43,2% |
| queue-emission mediana | 1372,8 µs | 937,2 µs | 970,8 µs | 906,6 µs | 925,6 µs | 919,6 µs |
| queue-emission p99 | 1718,6 µs | 1211,1 µs | 1215,0 µs | 1168,8 µs | 1177,7 µs | 1182,9 µs |
| queue-emission p99,9 | 1832,5 µs | 1291,4 µs | 1276,5 µs | 1229,4 µs | 1240,5 µs | 1243,5 µs |
| queue-emission max | 1944,0 µs | 1420,3 µs | 1426,1 µs | 1351,5 µs | 1372,4 µs | 1363,7 µs |
| max queue-emission / budżet 2777,8 µs | 70,0% | 51,1% | 51,3% | 48,7% | 49,4% | 49,1% |
| wake_lag mediana / max | 20,7 / 54,3 µs | 22,2 / 71,2 µs | 22,3 / 69,6 µs | 22,3 / 106,0 µs | 22,7 / 73,6 µs | 22,7 / 122,9 µs |

Wobec R631 K18d kwantyle E1 i queue-emission różnią się o -0,7% do +0,4% (mediany -0,7%, p99 E1 +0,02%, p99 i p99,9 queue-emission +0,4% i +0,2%, max queue-emission -0,6%), z wyjątkiem max E1 niższego o 4,5% (najniższy w serii, 43,2% budżetu slotu). Maksimum wake_lag (122,9 µs) jest najwyższe w serii, przy medianie bez zmian (22,7 µs) i p99,9 48,4 µs; dotyczy pojedynczej pobudki (kolejne wartości 89,9, 77,2 i 70,7 µs) i przypada na ten sam interwał co max queue-emission (iteracja 15156 w `e1_probe.csv`: wake_lag 122,9 µs, E1 1162,1 µs, queue-emission 1363,7 µs), który mimo to jest niższy niż w R631 K18d. Zmiana #640 dotyczy osi czasu i terminu slotu w pętli wykonawcy, ale pomiar to jeden przebieg na każdej rewizji, więc żadnej z tych różnic, także maksimum wake_lag, nie przypisuję silnikowi.

Stan workera: start 07:19 (2026-11-24, po włączeniu przez człowieka), potem build Release-Probe w `~/R648` (`~/R648-build.sh`, 07:29-08:41), exactness 08:51-08:57 i badanie 360 Hz 09:04-09:05. Kampania ma jedno badanie, więc nadzorca nie restartował workera. W trakcie exactness i badania nikt poza nadzorcą nie łączył się z workerem: start `run.sh` przez `timeout 30 ssh` z procesem odczepionym, oczekiwanie lokalnym `sleep`, jedno logowanie po końcu (09:01), potem kopia wyników, kontrola kopii i synchronizacja gałęzi (do 09:04) i tylko sesje nadzorcy. Logowania w trakcie buildu (sprawdzenie `~/R648-build.done` co 10 min) były przed oboma pomiarami. Kolejność jak w R631 K18d (build, exactness, badanie).

Odstępstwa w przebiegu, oba znane z R631 K18d: (a) strażnik buildu nadzorcy nie zna `scripts/buildrdb/research.sh`, więc build był ręczny (`scripts/buildrdb.sh conan ninja probe`, `cmake --install build/Release-Probe`), a nadzorca szedł z `--skip-build` i weryfikacją zainstalowanej binarki; (b) pierwsze uruchomienie nadzorcy (09:03:13) zatrzymało się na wstępnym preflighcie (`repozytorium wynikow workera nie jest czyste`), zanim cokolwiek uruchomiło na workerze: w klonie `~/rdb-experiment` zostały nieśledzone kopie 15 plików `exactness/`. Wszystkie 15 porównano sumami SHA-256 z plikami commitu `983192c` (zero różnic), usunięto (`git clean` tylko w `exactness/`) i przewinięto gałąź (`--ff-only`); drugie uruchomienie dało badanie z tego katalogu. Pomiaru nie powtarzano. Wyniki exactness skopiowane z workera na nadzorcę i zacommitowane tam (`983192c`). Nadzorca wypchnął najpierw commit z samym manifestem (`7e7c6b6`), a potem zastąpił go wymuszonym pushem commitu badania `b61f2c8` (rodzic `983192c`); żaden commit spoza nadzorcy nie został nadpisany.
