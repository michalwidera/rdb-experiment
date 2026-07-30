# Wymagania procesu eksperymentalnego RetractorDB

## Zakres

Dokument definiuje wymagania kampanii wykonywanych na fizycznym workerze
Raspberry Pi 400 pod Linuksem PREEMPT_RT. Eksperymenty semantyczne, które nie
mierzą czasu i mają własny `run.sh` w katalogu wyników, nie korzystają z
nadzorcy opisanego poniżej.

Cele poszczególnych kampanii wynikają z:

- `paper-arXiv/debs/main-debs.tex`;
- `paper-arXiv/debs/research_plan.md`;
- README wygenerowanego przed pierwszym badaniem kampanii.

## R1. Dwa niezależne repozytoria

Proces korzysta z dwóch niezależnych repozytoriów na obu maszynach:

| Rola | Nadzorca | Worker | Branch bazowy |
|---|---|---|---|
| kod i build | `/home/michal/github/retractordb` | `/home/michal/retractordb` | `master` |
| skrypty, dziennik i wyniki | `/home/michal/github/rdb-experiment` | `/home/michal/rdb-experiment` | `main` |

Branch kodu i branch wyników mają osobne historie oraz osobne identyfikatory.
Manifest eksperymentu zapisuje pełny commit kodu i bazowy commit repozytorium
wyników.

## R2. Bezwzględny zakaz zapisu wyników do repozytorium kodu

Worker traktuje repozytorium `retractordb` wyłącznie jako źródło kodu, danych
wejściowych i binarki.

W trakcie eksperymentu w repozytorium kodu nie wolno:

- tworzyć katalogów ani plików wynikowych;
- wykonywać `git add`, `git commit`, `git push` ani `commit --amend`;
- zmieniać brancha lub commita po zakończeniu preflight;
- pozostawić jakiejkolwiek zmiany widocznej w `git status --short`.

Wszystkie wyniki, manifesty, README kampanii, wpisy `JOURNAL.md`, commity i
pushe trafiają wyłącznie do brancha repozytorium `rdb-experiment`. Naruszenie
tej zasady unieważnia badanie i zatrzymuje skrypt przed commitem wyników.

## R3. Docelowy katalog wyników bez rotacji

Każdy eksperyment od początku zapisuje dane bezpośrednio do katalogu:

```text
results_YYYYMMDD_typ/
  manifest.md
  kampania/
    README.md
    study_NN/
```

Katalog jest docelowy i niemutowalny w zakresie ukończonych badań. Nie istnieje
katalog przejściowy `results/`, mechanizm `rotated/NN` ani późniejsze
przenoszenie wyników.

Jeżeli eksperyment zostanie przerwany albo zmieni się kod, konfiguracja lub cel,
dotychczasowy katalog pozostaje bez zmian, a kolejna próba otrzymuje nowy
identyfikator i nowy katalog `results_YYYYMMDD_typ`.

## R4. Branch i jeden commit wyników

Wyniki eksperymentu są zapisywane na branchu
`experiment/YYYYMMDD_typ` repozytorium `rdb-experiment`.

Pierwszy commit tworzy manifest i README kampanii. Każde zakończone badanie:

1. dodaje wyłącznie pliki z docelowego katalogu i wpis w `JOURNAL.md`;
2. wykonuje `git commit --amend`;
3. wysyła `git push --force-with-lease`.

Po zakończeniu eksperymentu branch zawiera jeden commit z kompletem wyników.
Merge do `main` wykonuje człowiek po przeglądzie. Branch kodu jest przygotowany
poza procesem pomiarowym; eksperyment nie tworzy na nim żadnych commitów.

## R5. Warunki wejściowe

Przed utworzeniem brancha wyników nadzorca zatrzymuje proces, jeżeli:

- którekolwiek z dwóch lokalnych repozytoriów ma niezacommitowane zmiany;
- na workerze brakuje któregokolwiek repozytorium;
- którekolwiek repozytorium workera ma niezacommitowane zmiany;
- worker nie wskazuje pełnego commita kodu zapisanego w manifeście;
- nie można jednoznacznie odnaleźć i uwierzytelnić workera;
- docelowy katalog kampanii już istnieje;
- `/dev/shm` nie jest systemem plików `tmpfs`;
- build lub środowisko czasu rzeczywistego nie przechodzi walidacji.

## R6. Build pomiarowy

Kod jest budowany profilem `scripts/buildrdb.sh probe` w izolowanym katalogu
`build/Release-Probe`. Instalacja pochodzi z tego samego katalogu.

Przed badaniem `xretractor --build-info` musi dokładnie potwierdzić wszystkie
optymalizacje produkcyjne oraz:

```text
RDB_BENCH_PROBE=ON
```

Brak lub niezgodność sondy jest błędem, a nie ostrzeżeniem.

## R7. Środowisko czasu rzeczywistego

Badanie czasowe wymaga:

- jądra PREEMPT_RT;
- governora `performance`;
- przypięcia `xretractor` do izolowanego rdzenia 3;
- procesów tła na rdzeniach 0–2;
- aktywnego wątku `SCHED_FIFO` o priorytecie 50;
- capabilities `cap_sys_nice` i `cap_ipc_lock`;
- danych roboczych i sondy w zweryfikowanym `/dev/shm`.

Brak któregokolwiek warunku zatrzymuje badanie. Skrypt nie może kontynuować
w trybie zdegradowanym.

## R8. Przebieg pojedynczego badania

Pojedyncze badanie wykonuje kolejno:

1. zapis pełnego stanu maszyny przed pomiarem;
2. uruchomienie algorytmu i klientów;
3. rejestrację sondy oraz metryk systemowych;
4. sprawdzenie kodu zakończenia procesu i kompletności danych;
5. zatrzymanie procesów i przywrócenie zmienionej konfiguracji;
6. zapis stanu maszyny po pomiarze;
7. utworzenie raportu i wpisu w `JOURNAL.md`;
8. ponowną kontrolę, że repozytorium kodu pozostało czyste;
9. amend i push wyłącznie w `rdb-experiment`.

Pomiędzy badaniami nadzorca wykonuje `sync`, restartuje workera i czeka na jego
powrót z ograniczonym czasem oczekiwania.

## R9. Rejestrowane dane

Każde `study_NN` zawiera co najmniej:

- `state_before.md` i `state_after.md`;
- `e1_probe.csv`;
- `metrics.csv`;
- `xretractor.log`;
- `results.md`.

Stan maszyny obejmuje datę, parametry badania, commit kodu, konfigurację builda,
jądro, dystrybucję, CPU, pamięć, fragmentację, obciążenie, temperaturę,
kernel cmdline, governor i częstotliwości CPU.

`metrics.csv` rejestruje w trakcie pomiaru temperaturę, obciążenie i pamięć.
Źródła, pliki robocze oraz artefakty tworzone przez silnik pozostają w
`/dev/shm`; wynik jest kopiowany do repozytorium dopiero po zakończeniu
mierzonej pętli.

## R10. Znaczenie metryk

Sonda `RDB_BENCH_CSV` mierzy:

- czas `processRows`;
- opóźnienie pobudki względem deadline'u;
- `queue-emission latency`, czyli czas od deadline'u do emisji wyniku do
  kolejki klienta.

Ostatnia metryka nie obejmuje pobrania przez klienta, transportu ani
potwierdzenia ujścia i nie może być nazywana pełnym application end-to-end.
Pełny E2E wymaga osobnej sondy `source -> engine -> client -> transport ->
sink acknowledgement`.

## R11. Walidacja i fałszywy sukces

Badanie nie może zostać zatwierdzone, jeżeli:

- `xretractor`, klient lub wymagany sampler kończy się błędem;
- zadziała timeout;
- sonda jest pusta, ma zły nagłówek albo nieoczekiwaną liczbę rekordów;
- brakuje któregokolwiek obowiązkowego pliku;
- nie udało się posprzątać procesów;
- repozytorium kodu zmieniło stan lub commit.

Każdy taki przypadek kończy się niezerowym kodem i bez commita wyników.

Monitor procesów pomocniczych nie może opierać decyzji wyłącznie na ostatnim
sprawdzeniu wykonanym przed zakończeniem `xretractor`. Po zakończeniu procesu
głównego worker zbiera status każdego klienta, samplera i ujścia. Proces
zakończony wcześniej kodem niezerowym unieważnia badanie; proces nadal aktywny
jest zatrzymywany kontrolowanie i musi zostać zebrany. Ignorowanie `SIGTERM`
nie może zawiesić sprzątania: po ograniczonym czasie worker używa `SIGKILL`,
zbiera proces i unieważnia badanie.

Regresje w `tests/test_orchestration.sh` muszą wymuszać co najmniej:

- rzeczywisty timeout zawieszonej sondy SSH wraz z kontrolą, że proces zniknął;
- błąd procesu potomnego, również w oknie zakończenia procesu głównego;
- pustą listę badań;
- sprzątnięcie procesów po ścieżkach negatywnych, również gdy proces ignoruje
  `SIGTERM`.

Zestaw uruchamia się poleceniem:

```bash
./tests/test_orchestration.sh
```

## R12. Odtwarzalność i dziennik

`manifest.md` zapisuje co najmniej: identyfikator eksperymentu, pełny commit
kodu, branch kodu, bazowy commit wyników, branch wyników, żądany i rzeczywisty
adres workera, jego hostname, sieć wykrywania oraz datę.
README kampanii zapisuje cel, konfigurację i jej SHA-256.

`JOURNAL.md` jest uzupełniany chronologicznie na branchu wyników. Zachowuje
również wyniki negatywne, decyzje i zmiany hipotez; historii nie przepisuje się
po fakcie.

## R13. Wykrywanie zmienionego adresu workera

Nadzorca najpierw próbuje połączyć się z adresem podanym przez `--worker`.
Krótki skan sieci jest uruchamiany wyłącznie wtedy, gdy ten adres nie odpowiada
albo nie wskazuje oczekiwanego workera.

Skan:

- obejmuje wyłącznie jedną wskazaną lub wywnioskowaną sieć IPv4 `/24`;
- sprawdza wyłącznie skonfigurowany port SSH;
- wymaga zgodności fingerprintu klucza hosta SSH z wcześniej zaufanym wpisem
  `known_hosts` albo wartością `--worker-host-key`;
- wymaga oczekiwanego hostname oraz obecności obu repozytoriów;
- akceptuje dokładnie jednego kandydata.

Brak zaufanego fingerprintu, brak kandydata albo wielu pasujących kandydatów
zatrzymuje proces. Wykrywanie nie może używać `StrictHostKeyChecking=no` ani
traktować samego otwartego portu jako potwierdzenia tożsamości.

## R14. Higiena artefaktów surowych

Katalog wyników jest przeznaczony do przeglądu przez człowieka i przez IDE.
Kampania nie może zostawić w nim tysięcy luźnych plików: taki katalog nie da się
przejrzeć, a merytorycznie wnosi tyle, co jego indeks.

Surowe artefakty silnika — `.desc`, `.meta`, `.shadow`, dane strumieni, zrzuty
`stdout`/`stderr` pojedynczych kompilacji — powstają w `/dev/shm` i tam są
porównywane. Do repozytorium trafiają według trzech reguł:

1. **Dowód porażki jest plikiem.** Artefakt imiennie wskazany w werdykcie
   negatywnym (różnica bajtowa, nieoczekiwane odrzucenie, timeout) jest
   kopiowany do `results/evidence/` z zachowaniem nazwy z werdyktu.
2. **Sukces jest skrótem.** Zrzuty i drzewa udanych przebiegów nie stają się
   plikami; ich `SHA-256` i rozmiar zapisuje raport kampanii.
3. **Reszta jest jednym archiwum.** Katalog surowy jest pakowany do
   deterministycznego `tar.gz` z indeksem `SHA-256` obok — na koniec badania,
   **również gdy badanie zawiodło**, bo dowód porażki nie może być zachowany
   w gorszej formie niż dowód sukcesu.

Mechanizm współdzielony: `lib/artifacts.py` i `lib/artifacts.sh`. Skrypt
kampanii pakuje przez pułapkę `EXIT`, która zachowuje kod wyjścia badania:

```bash
source "$experiment_repo/lib/artifacts.sh"
artifacts_pack_on_exit results/raw results/workloads
```

Kompaktowanie zmienia formę zapisu, nie treść. Indeks dowodzi tożsamości bajtów
i pozwala odnaleźć plik bez rozpakowywania, więc nie narusza niemutowalności
ukończonego badania z R3. Katalog już istniejący porządkuje
`./compact_results.sh <katalog_wynikow>`.

Manifest badania przypina, w części „Artefakty surowe": commit repozytorium
kodu, commit repozytorium wyników, `SHA-256` każdego archiwum oraz dosłowny ciąg
poleceń odtwarzających artefakty od zera. Odtwarzalność wyniku nie może zależeć
od przechowywania samych artefaktów.

Regresja wymusza: zastąpienie drzewa archiwum, zgodność rozpakowanego archiwum
z indeksem, determinizm archiwum, pakowanie po porażce z zachowaniem kodu
wyjścia, brak plików dla przebiegów udanych oraz limit luźnych plików w każdym
katalogu `results_*`:

```bash
./tests/test_artifacts.sh
```
