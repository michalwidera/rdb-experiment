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

Przygotowanie przed pomiarem; exactness/replay i badanie 360 Hz nie biegły.
