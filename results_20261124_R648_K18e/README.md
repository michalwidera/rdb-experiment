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

Predeklaracja zapisana przed pomiarem; ani exactness, ani badanie 360 Hz na R jeszcze nie ruszyły.
