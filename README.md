# Eksperymenty RetractorDB

Repozytorium przechowuje skrypty, dziennik i wyniki eksperymentów. Kod silnika
pozostaje w osobnym repozytorium `retractordb`.

| Rodzina | Sposób uruchomienia | Protokół |
|---|---|---|
| kampanie czasowe na Raspberry Pi 400 | `start_supervisor.sh` + worker PREEMPT_RT | `REQUIREMENTS.md` |
| eksperymenty semantyczne | lokalny `run.sh` w katalogu danego eksperymentu | README danego katalogu |

## Architektura

Na nadzorcy:

```text
/home/michal/github/retractordb      # kod i build
/home/michal/github/rdb-experiment   # skrypty, JOURNAL.md i wyniki
```

Na workerze:

```text
/home/michal/retractordb             # kod i build; bez wyników i commitów
/home/michal/rdb-experiment          # skrypty, JOURNAL.md i wyniki
```

Repozytoria mają oddzielne historie. Worker nigdy nie zapisuje wyników ani
commitów do brancha kodu.

## Warunki wstępne

1. Oba repozytoria istnieją i są czyste na nadzorcy oraz workerze.
2. Wybrany branch kodu jest dostępny w `origin` obu klonów.
3. Worker odpowiada przez SSH i ma bezhasłowe uprawnienia do:

   ```text
   reboot
   setcap
   zapisu governorów CPU przez tee
   ```

4. `examples/ecg/build.sh` w repozytorium kodu utworzył `rec205` i
   `rec205.desc`.
5. `/dev/shm` na workerze jest zamontowane jako `tmpfs`.
6. Nadzorca ma programy `nc`, `ssh-keyscan` i `ssh-keygen`. Klucz hosta
   workera jest już zapisany w `~/.ssh/known_hosts` pod dotychczasowym adresem.

## Uruchomienie

Z katalogu `rdb-experiment` na nadzorcy:

```bash
./start_supervisor.sh rate \
  --worker 192.168.88.21 \
  --worker-port 22 \
  --worker-name pi400 \
  --worker-subnet 192.168.88.0/24 \
  --code-branch master \
  --experiment-id 20260728_performance
```

Kampania klientów na tym samym branchu i w tym samym katalogu wyników:

```bash
./start_supervisor.sh clients \
  --worker 192.168.88.21 \
  --worker-port 22 \
  --code-branch master \
  --experiment-id 20260728_performance \
  --rate-hz 480
```

Domyślne ścieżki można zmienić opcjami:

```text
--code-repo
--worker-code-repo
--worker-experiment-repo
--worker-name
--worker-subnet
--worker-host-key
--no-worker-discovery
```

Opcja `--skip-build` pomija kompilację, ale nie omija walidacji zainstalowanej
binarki. Musi ona nadal zgłosić przez `--build-info` build `Release-Probe` z
`RDB_BENCH_PROBE=ON`.

## Zmienny adres IP workera

Nadzorca najpierw używa adresu z `--worker`. Jeżeli połączenie lub kontrola
tożsamości nie powiedzie się, skanuje wskazaną sieć `/24` na skonfigurowanym
porcie SSH. Gdy `--worker-subnet` nie podano, sieć jest wyprowadzana z
numerycznego adresu workera.

Nowy adres jest akceptowany tylko wtedy, gdy:

1. fingerprint klucza hosta zgadza się z wpisem `known_hosts` starego adresu;
2. `hostname` jest równy wartości `--worker-name`;
3. istnieją repozytoria kodu i wyników.

Jeżeli starego wpisu `known_hosts` nie ma, fingerprint można przekazać jawnie:

```bash
--worker-host-key SHA256:...
```

Skan można wyłączyć przez `--no-worker-discovery`. Nadzorca nie używa
`StrictHostKeyChecking=no` i zatrzymuje się, jeśli nie może jednoznacznie
uwierzytelnić workera.

## Układ wyników

Wyniki od początku trafiają do katalogu docelowego:

```text
results_20260728_performance/
  manifest.md
  rate/
    README.md
    study_01/
      state_before.md
      state_after.md
      e1_probe.csv
      metrics.csv
      xretractor.log
      xqry_1.err
      results.md
```

Nie istnieje rotacja. Skrypt nie nadpisze istniejącego katalogu kampanii ani
badania. Zmiana kodu, konfiguracji lub celu wymaga nowego `experiment-id`.

## Metryki

`e1_probe.csv` zawiera:

```text
iter,compute_ns,wake_lag_ns,e2e_ns
```

Historyczna nazwa kolumny `e2e_ns` oznacza w aktualnej interpretacji
`queue-emission latency`: deadline slotu do emisji do kolejki klienta. Nie jest
to pełny application E2E, ponieważ nie obejmuje odebrania przez `xqry`,
transportu ani potwierdzenia ujścia.

`metrics.csv` próbkuje co sekundę obciążenie, pamięć i temperaturę. Migawki
stanu zapisują również commit kodu i pełne `xretractor --build-info`.

## Zachowanie przy błędzie

Timeout, błąd procesu, brak RT, niezgodny build, pusty lub niekompletny CSV,
brak pliku albo zmiana repozytorium kodu kończą badanie niezerowym kodem.
Niepełny wynik nie jest commitowany.

Procesy pomocnicze są monitorowane podczas pracy `xretractor`, a po jego
zakończeniu ich statusy są zbierane ponownie. Domyka to okno między ostatnim
sprawdzeniem monitora a końcem procesu głównego: klient, sampler albo ujście,
które zakończyło się wtedy błędem, nadal unieważnia badanie. Proces działający
poprawnie do końca pomiaru jest zatrzymywany kontrolowanym `SIGTERM`.
Jeżeli nie zakończy się w ograniczonym czasie, worker używa `SIGKILL`, zbiera
proces i unieważnia badanie zamiast czekać bezterminowo.

Po każdym udanym badaniu worker:

1. sprawdza, że repozytorium kodu nadal jest czyste i wskazuje ten sam commit;
2. dodaje wynik i wpis w `JOURNAL.md` wyłącznie w `rdb-experiment`;
3. wykonuje `commit --amend` i `push --force-with-lease`.

Po zakończeniu człowiek przegląda pojedynczy commit brancha eksperymentalnego
i decyduje o merge do `main`.

## Testy orkiestracji

```bash
./tests/test_orchestration.sh
```

Testy wymuszają między innymi:

- zawieszoną sondę SSH, rzeczywiste zadziałanie `timeout` i usunięcie procesu;
- pustą listę badań;
- błąd dziecka podczas pracy oraz w chwili zakończenia procesu głównego;
- kontrolowane zatrzymanie pozostałych procesów.

Każda negatywna ścieżka musi zwrócić kod niezerowy, a test kończy się błędem,
jeżeli pozostawi monitorowany proces.
