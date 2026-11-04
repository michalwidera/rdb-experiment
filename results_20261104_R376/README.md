# R376 - opóźnienie slotu przy podłączeniu klienta przed i po #283 (pi400, `--realtime`)

Zgłoszenie: michalwidera/retractordb#376 (wydzielone z #283, punkt 4). Plan zatwierdzony przez człowieka 2026-11-04. Ten plik zapisano PRZED pomiarem; zmiany protokołu po starcie kampanii trafiają do sekcji *Aneksy* z datą i powodem, nie do treści powyżej.

## Pytanie

Czy przeniesienie `subscribe()` poza `plan_epoch_mutex` (#283) usuwa skok `e2e_ns` w slotach, w które trafia budowa kolejki nowego subskrybenta, i czy zostaje skok przypisywalny do `mmap_lock` procesu.

## Strony porównania

| Strona | Rewizja | Co robi handler `show` |
|---|---|---|
| A | `96b74dc0ad66df3c645d239145b8821eaceacb8d` | `subscribe()` (budżet `/dev/shm`, `shm_open`, konstrukcja `message_queue`) pod `plan_epoch_mutex`; slot czeka na muteksie przed `beginCompute`, więc czekanie wpada do `e2e_ns` |
| B | `393b24ca08bbd1692079a97e6ee107115814789f` | blokada epoki zdjęta przed `subscribe()`; pod `clientMapsMutex_` tylko porównanie epoki rejestru i wpis do map |

B jest bezpośrednim potomkiem A (squash #377); różnica w silniku: `executorsmCommands.cpp`, `ipcServer.cpp`, `ipcServer.hpp`. `probe.cc`, `xqry` i pętla slotu są w A i B identyczne.

## Aparatura

- **P1** (`P1_deadline_ns.patch`): ta sama łatka na A i B, tylko w drzewie pomiarowym na workerze, nie w `retractordb`. Dopisuje do CSV sondy slotu kolumnę `deadline_ns` - bezwzględny termin slotu w `CLOCK_MONOTONIC` (wartość `deadlineNs_`, którą sonda już liczy). Koszt: jedno pole więcej w formatowaniu wiersza, jednakowo w A i B. Test jednostkowy nagłówka CSV (`probeSlot.csv_has_header_and_one_row_per_slot`) przy łatce nie przechodzi - w drzewie pomiarowym testów się nie uruchamia.
- **Budowa** (`build_ab.sh`): jedno drzewo `~/R376/src`, `scripts/buildrdb.sh probe` (Release, `RDB_BENCH_PROBE=ON`); najpierw A, kopia `xretractor` i `xqry` do `~/R376/bin/A`, potem B przyrostowo w tym samym drzewie i kopia do `~/R376/bin/B`. Obie binarki mają więc te same ścieżki źródeł i budowy. Sumy SHA-256 i `--build-info` obok binarek (`--build-info` A i B identyczne: wszystkie `RDB_OPT_*` i `RDB_BENCH_PROBE` ON).
- **Przebieg** (`run_one.py`): świeży katalog pracy `/dev/shm/r376/run` (ta sama ścieżka dla obu stron), binarki kopiowane pod `~/R376/exec/xretractor` i `~/R376/exec/xqry` (ta sama ścieżka i `argv[0]`; nie w `/dev/shm`, bo montowanie `nosuid` unieważnia `setcap`), `setcap cap_ipc_lock,cap_sys_nice=ep`, start `taskset -c 3 ~/R376/exec/xretractor query.rql -k -r -t` z `RDB_BENCH_CSV`. `taskset -c 3` jak w K23v2..K26v3: silnik z `-t` bierze rdzenie RT z maski procesu, więc wątek slotu trafia na izolowany rdzeń 3, a wątek komunikacyjny na 0-2. `sched_rt_runtime_us` zostaje domyślne (950000), jak w poprzednich kampaniach; wartość w `meta.json`. Po 5 s rozgrzewki: raport każdego wątku (`chrt -p`, `taskset -cp`) i `VmLck` procesu; brak wątku `SCHED_FIFO` albo `VmLck = 0` unieważnia przebieg. Potem ftrace (`trace_clock=mono`, `set_event_pid` = wątki silnika) wywołań `openat`, `statfs`, `fstatfs`, `ftruncate`, `fallocate`, `mmap`, `munmap`, `unlinkat` i seria 30 podłączeń `xqry -s <strumień> -m 1`, każde po przerwie losowanej jednostajnie z [2 s, 3 s] (losowa faza względem slotu; ziarno w `meta.json`), z czasem `CLOCK_MONOTONIC` startu, pierwszego wiersza i końca klienta. Klient jest zamykany `SIGINT` zaraz po pierwszym wierszu (patrz *Suchy przebieg*, punkt 1). `openat`, `statfs` i `fstatfs` wątku RT są odfiltrowane (wątek slotu otwiera pliki źródeł w każdym slocie); `munmap` i `unlinkat` śledzone są we wszystkich wątkach. Po serii 12 s ogona śladu na zwolnienie ostatniej kolejki. Koniec: `SIGTERM`, kod wyjścia silnika w `meta.json`. Governor `performance` na wszystkich rdzeniach, wymagany przez runner.
- **Kampania** (`campaign.sh`): rodziny z `paper-arXiv/usecases`, które przeszły test nasycenia (*Suchy przebieg*, punkt 3), 9 par A/B na rodzinę, para nieparzysta AB, parzysta BA. Strumień subskrybowany w rodzinie (`select_streams.sh`): ten o najkrótszym takcie wśród strumieni publicznych (bez `$` i prefiksu `STREAM_`), bo `maxElements = 10 s / takt`, czyli największa kolejka; wybór w `streams.tsv` istnieje tylko na workerze (embargo), tu zapisany jest wyłącznie takt.

## Przypisanie podłączenia do slotu

Czas startu klienta nie wyznacza chwili pracy handlera `show`, więc okno podłączenia bierze się z ftrace wątku, który zbudował kolejkę:

- **okno W** = [pierwsze z `statfs`/`fstatfs`/`openat` tego wątku w przedziale klienta poprzedzające mmap kolejki, wyjście z `mmap` kolejki], gdzie mmap kolejki to `mmap` z `MAP_SHARED` i deskryptorem różnym od -1, wykonany w przedziale [start, koniec] klienta przez wątek inny niż wątek `SCHED_FIFO`. Sekwencja potwierdzona w suchym przebiegu: `openat` (sonda budżetu) → `fstatfs` → `unlinkat` → `openat` (segment kolejki) → `fallocate` → `ftruncate` → `mmap`. Podłączenie bez mmap kolejki jest raportowane jako bez przypisania.
- **slot z podłączeniem**: przedział [`deadline_ns`, `deadline_ns + e2e_ns`] ma część wspólną z którymkolwiek oknem W.
- **slot kontrolny**: `deadline_ns` dalej niż 0,5 s od przedziału [start, koniec] każdego klienta i wewnątrz przedziału serii [start pierwszego klienta - 2 s, koniec ostatniego + 2 s].
- **okno zwolnienia** = [wejście w `munmap` adresu zwróconego przez mmap kolejki, wyjście z następującego po nim `unlinkat` tego samego wątku], szukane w całym śladzie i w dowolnym wątku. `broadcast()` kasuje kolejkę dopiero po jej zapełnieniu (10 s danych bez odbiorcy), w wątku slotu, w A i B jednakowo. Sloty w odległości do 0,5 s od okna zwolnienia też nie są kontrolne.
- Pozostałe sloty (pas ochronny) nie wchodzą do żadnej grupy.

## Metryki i kryteria (ustalone przed pomiarem)

Dla każdej rodziny i strony, sumarycznie po 9 przebiegach:

1. **Główna - zdarzenie podłączenia**: dla każdego okna W największe `e2e_ns` w jego slotach z podłączeniem. Rozkład po zdarzeniach: p50, p99, max, liczność (`n_hit` = zdarzenia, w które trafił co najmniej jeden slot). Prawdopodobieństwo trafienia slotu w okno rośnie jak |W| / takt slotu, więc rodziny o długim takcie mogą mieć `n_hit` bliskie zeru - to jest wynik, nie błąd aparatury.
2. **Pomocnicza - slot**: p99 i max `e2e_ns` po wszystkich slotach z podłączeniem.
3. **Kontrola**: w slotach kontrolnych p50, p99, max `e2e_ns`, `compute_ns` i `wake_lag_ns`. Dla metryki zdarzeniowej kontrolą są **pseudo-zdarzenia**: na każde zdarzenie 20 okien tej samej długości co jego W, położonych losowo w serii, w całości w slotach kontrolnych i z co najmniej jednym slotem; wartość = max `e2e_ns` w oknie. Bez tego maksimum z kilku slotów okna porównywane byłoby z pojedynczymi slotami.
4. **Długość okna W** (p50, max) - koszt budowy kolejki po stronie wątku komunikacyjnego.
5. **Zwolnienie kolejki**: liczba, odsetek w wątku RT, długość okna zwolnienia i max `e2e_ns` slotów, które na nie trafiły (p50, p99, max).

Kryteria:

- **p99 stabilne**, gdy połowa szerokości 95 % przedziału bootstrap (2000 losowań po zdarzeniach) nie przekracza 10 % wartości. p99 raportuje się tylko przy `n_hit ≥ 100`; przy mniejszym `n_hit` tylko max i liczność, z adnotacją. Niespełnione kryterium = wynik niestabilny, bez dokładania przebiegów bez decyzji człowieka.
- **Efekt #283 potwierdzony** w rodzinie, gdy p99 zdarzeniowe B < p99 zdarzeniowe A, oba stabilne, i test Manna-Whitneya (A > B, po zdarzeniach) daje p < 0,01.
- **Ryzyko szczątkowe**: w B porównanie zdarzeń z pseudo-zdarzeniami tej samej strony (Mann-Whitney, B-zdarzenia > B-pseudo, p < 0,01). Istotny nadmiar w B jest kandydatem na `mmap_lock` (lub inny wspólny zasób), nie dowodem; wielkość nadmiaru raportuje się różnicą median.
- **Kontrola aparatury**: `compute_ns` (p50) i `wake_lag_ns` (p99) w slotach kontrolnych liczone per przebieg; różnica median A-B porównana z rozrzutem między przebiegami tej samej strony (min..max po 9 przebiegach), plus dokładny test permutacyjny Manna-Whitneya 9 vs 9. Nie wymaga się identycznych rozkładów; różnica wyraźnie większa od rozrzutu wewnątrz strony oznacza błąd aparatury i wstrzymuje wniosek dla tej rodziny.

## Embargo

Korpus `uc01`..`uc08` jest objęty embargiem do publikacji DEBS. W tym katalogu i w komentarzach do zgłoszeń: wyłącznie identyfikatory rodzin i liczby z nich wyprowadzone (czasy, takty, liczności, p-wartości). Plany, dane, generatory i nazwy strumieni zostają na workerze w `/dev/shm/r376` i w prywatnym `paper-arXiv`. Surowe CSV i ślady ftrace nie trafiają do git (rozmiar); zostają poza repozytorium z indeksem sum.

## Suchy przebieg

2026-11-04, uc01 i uc05, po 1 przebiegu A i B z 10 podłączeniami, oraz test nasycenia wszystkich rodzin. Dane suchego przebiegu nie wchodzą do wyniku. Ustalenia, wprowadzone do protokołu powyżej przed startem kampanii:

1. **`xqry -s S -m 1` nie kończy się na strumieniu szybszym niż ~1 kHz.** Po osiągnięciu limitu pętla `while (transport_->popQueue(e_value) && !transport_->done) sleep(kQueuePollInterval)` w `src/qry/qry.cpp` zdejmuje jeden element na 1 ms, a producent dokłada szybciej (uc01: 6400/s). Klient wisiał do `timeout`. Ten sam kod jest w A, B i na `HEAD` silnika (do zgłoszenia osobno). Obejście w aparaturze: `SIGINT` po pierwszym wierszu, jednakowo w obu stronach i we wszystkich rodzinach. Serwer i tak nie dowiaduje się o wyjściu klienta, więc obejście nie zmienia jego zachowania.
2. **Binarka w `/dev/shm` traci `setcap`** (montowanie `nosuid`): bez `SCHED_FIFO` i `mlockall` runner unieważnił oba przebiegi. Binarki przeniesione do `~/R376/exec`. Bez `taskset` silnik z `-t` dawał wątkowi slotu rdzenie 0-2, a komunikacyjnemu izolowany rdzeń 3; stąd `taskset -c 3`.
3. **Nasycenie.** Test: strona A, 0 podłączeń, ~17 s pod `-t`, rdzeń 3. Reguła: rodzina jest nasycona, gdy mediana `wake_lag_ns` w ostatnich 4 s przekracza 1 ms - `e2e_ns` mierzy wtedy narastającą zaległość, nie podłączenie. Wynik: uc01 (takt slotu 1/6400 s, `compute_ns` p50 133 µs, `wake_lag` p50 6,8 s w ostatnich 4 s) i uc02 (1/4000 s, 213 µs, 6,1 s) **nasycone** - na pi400 pod `--realtime` niemierzalne, poza kampanią. Pozostałe: mediana `wake_lag` 21-24 µs. uc06 ma bez podłączeń `wake_lag` p99 = 44 ms (własne przestoje rodziny, jednakowe w A i B; widoczne w kontroli). uc04 ma takt 5 s, więc slot trafia w okno W rzadko; raportuje się liczność.
4. **Koszt budowy kolejki to `fallocate`**, nie `mmap`: uc01 (kolejka 64 MiB) `fallocate` ~73 ms, `mmap` ~70 µs; uc05 (8 MiB) okno W ~9,7 ms. Wcześniejszy opis „42 ms przy populacji stron mapowania” dotyczył leniwego otwarcia w `broadcast()` sprzed lipca 2026.
5. **Zwolnienie kolejki odbywa się w wątku slotu** (`mqPtr.reset()` + `message_queue::remove` w `broadcast()`), ~10 s po podłączeniu: uc01 `munmap`+`unlinkat` ~47 ms, uc05 ~6 ms, w A i B jednakowo. Stąd okno zwolnienia i metryka 5.
6. **Metryka zdarzeniowa wymaga pseudo-zdarzeń** jako kontroli (punkt 3 metryk): w uc05 sloty kontrolne mają p50 0,13 ms, a max z ~10 slotów okna ~0,92 ms.

Wynik orientacyjny uc05 (1 przebieg na stronę, nie do wniosków): max `e2e_ns` zdarzenia p50 A 9,99 ms, B 1,03 ms, pseudo-zdarzenia 0,92 ms.

## Aneksy

(brak)

## Stan

Kampania zakończona 2026-11-04 (108/108 przebiegów ważnych). Wynik: `wynik.md`. Efekt #283 potwierdzony według kryterium w uc03 i uc06; w uc05 p99 niestabilne (eksploracja po pomiarze w `wynik.md`, do decyzji człowieka); uc04 nie do oceny; uc07 i uc08 poniżej 100 trafień.
