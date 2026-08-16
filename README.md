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

## Artefakty kampanii — gdzie mają mieszkać

Dwie reguły, obie z 2026-08-16, obie wymuszone tym samym bałaganem: cztery
kampanie zostawiły 1,9 GB luzem w `~` na hoście i 8,9 GB na workerze.

**1. Aparatura nie pisze do katalogu domowego.** Katalog domowy jest miejscem
przejściowym, nie magazynem dowodów.

**2. Artefakty badań przechowuje repozytorium, nie maszyna.** Dowód, który
istnieje wyłącznie w `~` jednego komputera, znika przy zmianie maszyny i nie da
się go odtworzyć — kampanie kosztują doby pomiaru. Docelowe miejsce:

```text
rdb-experiment/artifacts/<KAMPANIA>/     # np. artifacts/K26v3/
```

Katalog ma własny [`README.md`](artifacts/README.md) z mapą kampanii,
`MANIFEST.sha256` obejmujący każdą pozycję oraz opis, czego nie wolno z niego
cytować.

Postać przechowywania: **drzewa katalogów pakuje się do `.tar.gz`** — bramki i
kalibracje kompresują się dwudziestokrotnie (27 MB → 1,3 MB), a repozytorium
nie ma powodu wozić dziesiątek tysięcy drobnych plików. Rozpakowywać poza
repozytorium (`tar xzf … -C /tmp`). Rozpakowanych kopii archiwów sond nie
przechowuje się w ogóle — są bajtowo tym samym co archiwum, co sprawdza się
sumą sum przed usunięciem.

Granica wobec polityki z 2026-07-31 (`.gitignore`, wzorzec `*raw.tar.gz`):
**ta reguła jej nie uchyla, tylko zawęża.** Poza gitem zostaje wyłącznie to,
czego git unieść nie może — pojedynczy plik powyżej limitu 100 MB GitHuba, jak
155-megabajtowy `raw.tar.gz` rodziny W8 w K6c. Wszystko poniżej limitu wchodzi
do repozytorium; audyt integralności w obu przypadkach prowadzi indeks SHA-256.

Aparatura klasy K26v3 czyta ścieżki wyłącznie ze zmiennych środowiska, więc
korzeń wymusza się bez zmiany skryptów:

| Zmienna | Skrypt | Domyślna wartość, której **nie** używać |
|---|---|---|
| `OUT` | `run_main_rdb.sh` | `$HOME/k26v3_gates_rdb` |
| `OUT` | `run_main_flink.sh` | `$HOME/k26v3_gates_flink` |
| `OUT` | `dump_control_plans.sh` | `$HOME/k26v3_gates_plans` |
| `OUT` | `calib/run_calib_rdb.sh` | `$HOME/k26v3_calib` |
| `OUT` | `run_rehearsal.sh` | `$HOME/k26v3_rehearsal` |
| `CODE_REPO` | `calib/run_calib_rdb.sh` | `$HOME/K26v3` |
| `HOST_ARCHIVES` | `collect_p8_archives.sh` | `$HOME/k26v3_archives` |
| `REMOTE_P6_RDB`, `REMOTE_P8_OUT`, `REMOTE_ARCHIVES`, `REMOTE_CONTROL` | `start_matrix_p8.sh`, `collect_p8_archives.sh` | `/home/michal/k26v3_*` na workerze |
| `P6_RDB`, `P8_OUT`, `ARCHIVES`, `CONTROL` | `install_worker_service.sh`, `run_matrix_chain.sh` | j.w., trafiają do unitu systemd |

**Katalogów zamkniętych kampanii nie wolno poprawiać.**
`results_20260814_K26v3/` jest objęty `manifest.sha256` (438 pozycji,
weryfikuje się w całości) i te skrypty są w manifeście; zmiana domyślnej
ścieżki po fakcie wywróciłaby `freeze_check.sh` i unieważniła dowód kampanii,
która wydała werdykt. Domyślne wartości poprawia się **w kopii, przy zakładaniu
następnej kampanii**, przed wygenerowaniem manifestu:

```bash
REPO=$(git rev-parse --show-toplevel)          # katalog repozytorium, nie ~
cd results_<NOWA_KAMPANIA>

# host: wyniki lądują w repozytorium
sed -i "s#\$HOME/k26v3_#$REPO/artifacts/<NOWA>/#g" \
  run_main_rdb.sh run_main_flink.sh dump_control_plans.sh \
  run_rehearsal.sh collect_p8_archives.sh calib/run_calib_rdb.sh

# worker: katalog roboczy pomiaru, sprzątany po odbiorze archiwów
sed -i "s#/home/michal/k26v3_#/home/michal/scratch-<NOWA>/#g" \
  start_matrix_p8.sh collect_p8_archives.sh install_worker_service.sh \
  run_matrix_chain.sh

grep -rn 'HOME/k26\|/home/michal/k26' *.sh calib/*.sh   # musi być pusto
./gen_manifest.sh
```

Rozdział jest celowy: **worker liczy, host archiwizuje.** Na workerze zostaje
katalog roboczy poza repozytorium, bo jego treść i tak wraca archiwami przez
`collect_p8_archives.sh`; do repozytorium wchodzi wyłącznie to, co host odebrał
i sprawdził sumami. Katalog roboczy workera kasuje się po zamknięciu kampanii —
razem z jednostką systemd i klonem aparatury.

Dopóki to nie zostanie zrobione, uruchamianie aparatury K26v3 wymaga podania
zmiennych jawnie — inaczej znowu zapisze do `~`.

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

## Higiena artefaktów surowych

Wymaganie `REQUIREMENTS.md` R14: katalog wyników zostaje przeglądalny. Surowe
drzewa artefaktów silnika powstają w `/dev/shm`, a w repozytorium zostaje
dowód porażki jako plik, skrót `SHA-256` dla przebiegów udanych i jedno
archiwum na katalog surowy.

`run.sh` kampanii pakuje przez pułapkę `EXIT` — również po porażce:

```bash
source "$experiment_repo/lib/artifacts.sh"
artifacts_pack_on_exit results/raw results/workloads
```

Kolektor w Pythonie nie zapisuje zrzutów udanego przebiegu i kopiuje wyłącznie
artefakty wskazane w werdykcie:

```python
sys.path.insert(0, f"{experiment_repo}/lib")
import artifacts

record = artifacts.keep_output(raw_base, stdout, stderr, evidence=returncode != 0)
artifacts.keep_evidence(differing, work / "temp", output / "evidence" / case)
```

Katalog, który już rozrósł się do tysięcy plików:

```bash
./compact_results.sh results_20260729_K5 \
  --evidence results/raw/semantic/W8_Q01/STRUCT/mlii.desc
```

Narzędzie kopiuje dowody do `results/evidence/`, pakuje `results/raw`
i `results/workloads` do `tar.gz` z indeksem `SHA-256` i wypisuje tabelę do
przypięcia w manifeście. Pojedynczy plik odzyskuje się bez rozpakowywania
całości:

```bash
grep mwi.desc results_20260729_K5/results/raw.index.tsv
tar -xzOf results_20260729_K5/results/raw.tar.gz raw/semantic/W8_Q01/STRUCT/mwi.desc
```

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
./tests/test_artifacts.sh
```

Testy wymuszają między innymi:

- zawieszoną sondę SSH, rzeczywiste zadziałanie `timeout` i usunięcie procesu;
- pustą listę badań;
- błąd dziecka podczas pracy oraz w chwili zakończenia procesu głównego;
- kontrolowane zatrzymanie pozostałych procesów.

Każda negatywna ścieżka musi zwrócić kod niezerowy, a test kończy się błędem,
jeżeli pozostawi monitorowany proces.

Drugi zestaw pilnuje higieny artefaktów (R14): determinizmu archiwum, zgodności
rozpakowanego drzewa z indeksem, pakowania po porażce z zachowaniem kodu wyjścia
oraz limitu luźnych plików w każdym katalogu `results_*`. Kampania, która zaleje
katalog wyników tysiącami plików, nie przejdzie tego testu.
