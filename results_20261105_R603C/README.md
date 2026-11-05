# R603C - pomiar potwierdzający naprawę (a): pula kolejek odpowiedzi zamiast `munmap` + `unlinkat` w pracy (pi400, `--realtime`)

Zgłoszenie: michalwidera/retractordb#603. Naprawa (a) w `c9e3e80e`, scalona do `master` przez #604. Ten plik zapisano PRZED pomiarem; po zatwierdzeniu przez człowieka zmiany protokołu trafiają do sekcji *Aneksy* z datą i powodem, nie do treści powyżej.

Protokół zatwierdzony przez człowieka 2026-11-05 wraz z decyzjami D1-D3 według rekomendacji (sekcja *Decyzje*), przed budową aparatury i przed jakimkolwiek pomiarem.

Aparatura pochodzi z R600 (`results_20261104_R600/`, protokół `a44288e`, wynik `61b2ef9`), BEZ łatki P2 z R603: P2 sama podnosi `e2e_ns` p50 slotów kontrolnych uc05 z 0,121 do 0,143 ms (`results_20261105_R603/wynik.md`, *Odchylenia*, punkt 2). Opis aparatury, który się nie zmienił, jest w README R600; poniżej są tylko różnice i nowe kryteria.

## Pytanie

R600 i R603 pokazały, że zwolnienie porzuconej kolejki w wątku komunikacyjnym (`munmap` całego segmentu + `unlinkat`) wydłuża sloty obudzone w jego trakcie (K2 niezdane w uc05 i uc06), a za resztkę odpowiadają unieważnienie TLB całego ASID (udział 27-46 %) i nadwyżka chybień wspólnego L2. Naprawa (a) w ogóle nie zwalnia kolejki w czasie pracy: kolejkę martwego klienta opróżnia (`try_receive` na uchwycie serwera, wariant D1a), przenosi pod nazwę puli (`rename`) i oddaje następnemu klientowi o tej samej pojemności (`rename` z powrotem), bez `munmap`, `unlinkat`, `shm_open`, `fallocate` i `mmap`. Pytania:

1. Czy w czasie pracy nie ma już żadnej pary `munmap` + `unlinkat` kolejki odpowiedzi (K1')?
2. Czy nowa praca w wątku komunikacyjnym (drenaż + `renameat`) wydłuża sloty obudzone w jej trakcie (K2)?
3. Czy poza tymi oknami nic się nie pogorszyło (K3)?

## Strony porównania

| Strona | Rewizja silnika | Co robi wątek komunikacyjny z porzuconą kolejką |
|---|---|---|
| B | `10f491b8197108611e22ef822acdd45b1644282f` | `munmap` + `unlinkat` (#600; drzewo identyczne z `221d312b`, czyli ze stroną B R600 i R603) |
| C | `92faf6896cad8d55ad8afbe35918f44218850758` | `inspectProcess` (`openat` /proc + `kill(pid, 0)`), drenaż `try_receive`, `renameat` pod nazwę puli; przy pełnej puli najpierw `munmap` + `unlinkat` najstarszego wpisu |

- **C = `92faf689`**: scalenie #604 na `master`. Jego drzewo jest identyczne z drzewem `c9e3e80e` (`d6e26845...`), a pierwszym rodzicem jest B, więc różnica B → C to dokładnie naprawa (a): `ipcServer.cpp/.hpp`, `ipcSecurity.cpp/.hpp`, `constants.hpp` (plus testy jednostkowe). `src/qry` bez zmian: klient różni się tylko wbudowanym napisem rewizji.
- **B = `10f491b8`** (zgodnie z poleceniem). `git diff 221d312b 10f491b8` jest puste, więc B powtarza kod strony B z R600 bit w bit poza napisem rewizji. Dzięki temu B jest jednocześnie kontrolą dodatnią i powtórzeniem R600.
- Obie strony dostają tylko łatkę P1 (`deadline_ns`, z R600); `src/rdb/lib/probe.cc` jest w `221d312b` i `92faf689` identyczny, więc P1 wchodzi czysto.

## Ustalenia przed pomiarem (2026-11-05, z kodu i z surowych danych R600)

1. **Licznik trafień puli nie może pochodzić z logu.** `queue pooled on timeout` i `queue erased on timeout` to `SPDLOG_WARN`, a build Release (także `Release-Probe`) ma `SPDLOG_ACTIVE_LEVEL=SPDLOG_LEVEL_ERROR` (`retractordb/CMakeLists.txt:69`): obie linie są wycięte w czasie kompilacji. R603 zanotowało to samo od drugiej strony (*Suchy przebieg*, punkt 6: `engine.log` nie powstaje). Propozycja: licznik ze śladu ftrace, zob. K1' i *Do zatwierdzenia*, D1.
2. **xqry jest zbierany przez rodzica.** `run_one.py`, `client()`: po pierwszym wierszu SIGINT, potem `p.wait(timeout=5)`, a przy przekroczeniu `p.kill()` i `p.wait()`. Proces jest więc zawsze zebrany przed następnym podłączeniem, a kolejka zostaje porzucona dopiero po ~10 s (zapełnienie). W chwili zwolnienia `inspectProcess` powinien dostać ESRCH, a nie zombie. W R600 wszystkie 2700 klientów skończyło się kodem -2 (zabity przez SIGINT, zebrany przez `wait`), żaden `killed` (90 z 90 `conns.tsv` z archiwum `rdb-experiment-embargo/R600/`). Kontrola w danych tego badania: kolumna `pid` i `reaped` w `conns.tsv` (zob. *Aparatura*, punkt 3) i wartość powrotu `kill` w śladzie.
3. **Ryzyko od strony aparatury: martwy muteks kolejki.** Kod -2 znaczy, że klient ginie od sygnału, czyli może zginąć w trakcie `try_receive` z zajętym muteksem kolejki. Boost 1.91 zostawia wtedy kolejkę trwale `not_recoverable`: `broadcast()` porzuca ją od razu, a drenaż w C się nie uda i kolejka idzie do zwolnienia jak w B. Prawdopodobieństwo jest małe (muteks zajęty przez µs na 1 ms odpytywania), ale nie zerowe. Rozpoznanie: zwolnienie z `munmap` + `unlinkat` po `kill` = -ESRCH, które zaczyna się wcześniej niż 9,5 s po pierwszym wierszu klienta (zwykłe porzucenie przychodzi po zapełnieniu, ~10 s).
4. **Ślad drenażu.** `inspectProcess` martwego klienta robi w wątku komunikacyjnym `openat("/proc/<pid>/task/<pid>/stat")` = -ENOENT, a potem `kill(pid, 0)` = -ESRCH. Drenaż nie robi wywołań systemowych (muteks bez rywalizacji), `lstat` w `renameOwned` to `newfstatat`, którego ślad nie obejmuje, a `rename(3)` na aarch64 to `renameat`. Sekwencja `kill(pid_klienta, 0)` → `renameat` jest więc jednoznaczna, a `pid` klienta = `clientId` = pid procesu `xqry` (`ipcClient.cpp`, `getpid()`).
5. **Korpus** zniknął z `/dev/shm/r376` (worker restartowany, uptime 1 h 13 min w chwili sprawdzenia). Do odtworzenia procedurą R600.
6. **Na workerze** tracepointy `sys_{enter,exit}_{renameat,renameat2,kill,futex}` istnieją. `sys_enter_futex` niesie `uaddr` i `op`, `sys_enter_kill` - `pid` i `sig`.

## Aparatura - różnice wobec R600 i ich uzasadnienie

1. **Pinezki B i C** w `build_ab.sh`, łatka P1 na obu. Budowa jak w R600: drzewo `~/R376/src`, `scripts/buildrdb.sh probe` (Release, `RDB_BENCH_PROBE=ON`), najpierw B, potem C przyrostowo; binarki w `~/R376/bin/R603C_B` i `~/R376/bin/R603C_C`. `setcap cap_ipc_lock,cap_sys_nice=ep` (bez `cap_perfmon`, bo bez P2). Opisowo: suma `xretractor` B porównana z `~/R376/bin/R600_B` (ta sama treść kodu).
2. **Śledzone wywołania** (`run_one.py`, `SYSCALLS`): do listy R600 dochodzą
   - `renameat` i `renameat2` we wszystkich wątkach (który z nich wybiera glibc, ustala suchy przebieg);
   - `kill` poza wątkiem RT (filtr jak `openat`), żeby znaleźć start drenażu;
   - `futex` WYŁĄCZNIE w wątku RT (filtr `common_pid == <tid RT>`), do obserwacji inwersji (O1).
   Ślad jest jednakowy w B i C. Koszt `futex` w wątku slotu pojawia się tylko, gdy wątek slotu sam woła `futex`; częstość mierzy suchy przebieg (bramka w *Kolejność*, punkt 3).
3. **`conns.tsv`** dostaje kolumny `pid` (pid `xqry` = `clientId` serwera) i `reaped` (po `wait`: `os.kill(pid, 0)` daje `ProcessLookupError` = 1, inaczej 0).
4. **Katalogi**: binarki `~/R376/bin/R603C_{B,C}`, surowe dane `~/R376/raw_R603C`, aparatura `~/R376/apparatus_R603C`. Ścieżka uruchomienia `~/R376/exec/xretractor` i katalog pracy `/dev/shm/r376/run` bez zmian.
5. **Rodziny**: uc03, uc05, uc06, uc07, uc08 (jak R600). Strumień subskrybowany ze `streams.tsv` z `~/R376/apparatus_R600` (tylko na workerze).
6. **Korpus odtworzony** procedurą R600 (README R600, punkt 4); skrót SHA-256 drzewa każdej rodziny porównany z niezależną generacją na hoście (i dla uc05, uc06 z wartościami z R603).
7. **Bez zmian wobec R600**: 9 par na rodzinę w kolejności ABBA (para nieparzysta B, C; parzysta C, B), 30 podłączeń na przebieg z przerwami z [2 s, 3 s], SIGINT po pierwszym wierszu (ta sama postać w obu stronach; zob. *Ustalenia*, punkt 3), `taskset -c 3`, `-k -r -t`, governor `performance`, ftrace `trace_clock=mono`, 12 s ogona, unieważnienie przebiegu bez wątku `SCHED_FIFO` albo przy `VmLck = 0`.

## Okna i zdarzenia

- **Okno zwolnienia B** (R_B): jak w R600 i R603 (parser R603: od wejścia w pierwszy `munmap` w zakresie mapowania kolejki do wyjścia z następnego `unlinkat` tego wątku).
- **Okno drenażu C** (R_C) = [wyjście z `kill(pid_klienta, 0)` w wątku komunikacyjnym, wyjście z następnego `renameat` tego wątku]. Obejmuje drenaż, dwa `lstat` i `renameat` pod nazwę puli. `pid_klienta` z `conns.tsv`.
  - Okno R_C, w którym między `kill` a `renameat` jest para `munmap` + `unlinkat` (pełna pula zwalnia najstarszy wpis), to **okno przepełnienia**: raportowane osobno i wyłączone z K2, bo mierzy zwolnienie, a nie drenaż.
- **Oddanie z puli**: `renameat` w wątku komunikacyjnym niepoprzedzone `kill`, między startem klienta a jego pierwszym wierszem, bez `mmap` nowej kolejki. Podłączenie z `mmap` = kolejka utworzona.
- **Mapowania kolejek**: zakres `[adres, adres + długość)` z `mmap` okna budowy każdej utworzonej kolejki, żywy do jej `munmap`. W C kolejka z puli zachowuje mapowanie, więc jeden zakres obsługuje kolejnych klientów.
- **Slot trafiony, zdarzenie, sloty kontrolne, pseudo-zdarzenia**: jak w R600, dla okna R_B w B i R_C w C. Ziarno pseudo-zdarzeń 6031 (osobne od 600, 601, 603).

## Przewidywanie przed pomiarem

| rodzina | takt slotu | `maxElements` (≈ kolejka) | B: n zdarzeń w R600 | C: drenaż czyta |
|---|---|---|---|---|
| uc03 | 5 ms | ~2000 (2 MiB) | 29 | ~2 MiB |
| uc05 | 1 ms | ~8000 (8 MiB) | 270 | ~8 MiB |
| uc06 | 2 ms | ~5000 (5 MiB) | 270 | ~5 MiB |
| uc07 | 20 ms | ~500 (0,5 MiB) | 0 | ~0,5 MiB |
| uc08 | 100 ms | ~100 (0,1 MiB) | 0 | ~0,1 MiB |

1. **K1'**: w C każde porzucenie idzie do puli. Pula ma w stanie ustalonym 0-2 wpisy (napływ = porzucenia, odpływ = podłączenia przesunięte o ~10 s; w oknie 10 s mieści się 3-5 podłączeń), więc przepełnienie w fazie pracy nie powinno wystąpić. W ogonie, po ostatnim podłączeniu, wszystkie N_utw utworzonych kolejek wracają do puli, która trzyma 2, więc spodziewane jest dokładnie N_utw - 2 okien przepełnienia na przebieg (N_utw ≈ 4-6).
2. **K2: wynik niepewny, możliwe NIEZDANE w uc05 i uc06.** C usuwa oba wywołania, które R603 powiązało z resztką (`munmap`: unieważnienie TLB; `unlinkat`: zwalnianie stron), ale drenaż D1a czyta wszystkie `maxElements` komunikatów pełnej kolejki, czyli w uc05 ~8 MiB pamięci dzielonej przez wspólne L2 1 MiB, i zapisuje nagłówek każdego komunikatu. To strumień pamięci większy niż ten, który B przepuszcza przez `munmap` + `unlinkat` (tablice stron i struktury stron, bez treści). Mechanizm H-b może więc w C pozostać albo urosnąć. Okno R_C w uc05 będzie miało rząd milisekund (8000 × zajęcie muteksu + kopia 1 KiB), więc n ≥ 100 jest prawdopodobne w uc05 i uc06; w uc03 raczej n < 100, w uc07 i uc08 n ≈ 0 (nierozstrzygnięte, jak w R600).
3. **Podłączenie** (opisowo, O2): w C większość podłączeń bierze kolejkę z puli bez `fallocate` (zerowanie całego segmentu) i bez `mmap`, więc zdarzenie podłączenia (#283) powinno być w C mniejsze niż w B.

## Kryteria (ustalone przed pomiarem)

Dla każdej rodziny i strony, sumarycznie po 9 przebiegach.

### K1' - brak zwolnień kolejki w czasie pracy

- **Kontrola dodatnia (B)**: 30 z 30 porzuceń na przebieg kończy się parą `munmap` + `unlinkat` kolejki w wątku komunikacyjnym, 0 `kill(pid_klienta, 0)`. Brak powtórzenia unieważnia K1' w tej rodzinie (ślad nie widzi par).
- **Licznik do puli (C)**: liczba okien R_C z `kill` = -ESRCH i `renameat` = 0. Wymagane 270 z 270 (po wyłączeniach niżej).
- **Licznik z puli (C)**: liczba oddań z puli i liczba utworzonych kolejek N_utw; opisowo, oczekiwane 30 - N_utw oddań na przebieg.
- **Zero par w fazie pracy (C)**: faza pracy = od pierwszego okna R_C do startu ostatniego klienta przebiegu. W tej fazie 0 par `munmap` + `unlinkat` na mapowaniu kolejki odpowiedzi, w każdym przebiegu. W ogonie każda para musi leżeć wewnątrz okna przepełnienia, a ich liczba musi wynosić N_utw - 2 (spójność licznika: każda utworzona kolejka kończy w puli albo w przepełnieniu).
- **Wyłączenia przypisane aparaturze** (każde z dowodem w wyniku, osobna tabela):
  - klient nie zebrany: `reaped = 0` albo `openat` /proc udane bez `kill` przed zwolnieniem;
  - martwy muteks po SIGINT: zwolnienie `munmap` + `unlinkat` po `kill` = -ESRCH, zaczęte wcześniej niż 9,5 s po pierwszym wierszu klienta.
- **Werdykt C**: **ZDANE**, gdy kontrola dodatnia B spełniona, licznik do puli = liczba porzuceń po wyłączeniach, zero par w fazie pracy i spójność ogona w każdym przebiegu. **NIEZDANE** przy choćby jednej parze `munmap` + `unlinkat` w fazie pracy albo zwolnieniu bez puli, którego nie wyjaśnia wyłączenie. **NIEROZSTRZYGNIĘTE (aparatura)**, gdy wyłączenia obejmą więcej niż 5 % porzuceń rodziny.

### K2 - wpływ okna na slot

W każdej stronie: max `e2e_ns` zdarzeń wobec pseudo-zdarzeń tej samej strony, jednostronny Mann-Whitney H1: zdarzenia > pseudo (jak R600). Raport: p50, p99 (przy n ≥ 100), max obu rozkładów, różnica median Δ_e2e, odsetek okien trafionych w slot, długość okna p50 / max, odsetek okien z max `e2e_ns` > takt (zdarzenia i pseudo).

- **Kontrola dodatnia mocy (B)**: n ≥ 100 i p < 0,01, czyli powtórzenie R600 (uc05 p = 2,2e-04, uc06 p = 5,2e-16).
- **C zdane**: n ≥ 100 zdarzeń w C, kontrola B spełniona, p ≥ 0,01.
- **C niezdane**: n ≥ 100, kontrola B spełniona, p < 0,01.
- **Nierozstrzygnięte**: n < 100 w C (liczby podane) albo kontrola B niespełniona.
- **Opisowo**: u = Δ_e2e(C) / Δ_e2e(B) z 95 % przedziałem bootstrap (2000 losowań, ziarno 6031), jak C4 w R603. Okna przepełnienia (ogon) osobno.

### K3 - bez regresji poza oknami

Jak R600: w slotach kontrolnych (dalej niż 0,5 s od każdego klienta, okna R_B / R_C i okna przepełnienia, wewnątrz serii ± 2 s) p50, p99, max `e2e_ns`, `compute_ns`, `wake_lag_ns`; per przebieg `compute_ns` p50, `wake_lag_ns` p99, `e2e_ns` p99. Różnica median C - B wobec rozrzutu wewnątrz strony (max..min po 9 przebiegach) i dokładny permutacyjny MW 9 vs 9. Różnica dodatnia i większa od rozrzutu = **regresja C, osobne znalezisko** (nie zmienia K1' ani K2, trafia do wyniku i do komentarza w #603).

### Obserwacje (bez kryterium)

- **O1 - inwersja priorytetów na muteksie kolejki.** Muteks `message_queue` Boost 1.91 jest robust, bez `PTHREAD_PRIO_INHERIT`, a `try_send` bierze go blokująco (`scoped_lock`). W obu stronach: liczba wywołań `futex` wątku slotu z `uaddr` w zakresie żywego mapowania kolejki odpowiedzi, według `op & 0x7f` (`FUTEX_WAIT` = slot czeka na muteks trzymany przez klienta, czyli kandydat inwersji; `FUTEX_WAKE` = slot budzi klienta). Dla `FUTEX_WAIT`: czas wejście → wyjście (p50, max), czy slot przekroczył takt, i czy zdarzenie leży w oknie R_B / R_C. Wywołania `futex` wątku slotu poza zakresami kolejek: tylko liczba na slot.
- **O2 - zdarzenie podłączenia** (miara R376, #283): okno budowy kolejki i max `e2e_ns` slotów, które w nie trafiły, osobno dla podłączeń z kolejką utworzoną i oddaną z puli.
- **O3** - długość okien R_B, R_C i okien przepełnienia; `wake_lag_ns` i `compute_ns` slotów trafionych.

## Kolejność

1. Zatwierdzenie tego protokołu przez człowieka (2026-11-05), commit.
2. Aparatura: `build_ab.sh`, `run_one.py` (różnice z punktów 1-4), `campaign.sh` (strony B, C), `analyze.py` (parser R603 + okna R_C, oddania z puli, K1', O1, O2). Test parsera: `analyze.py` na surowych danych R600 strony B musi dać okna R_B i werdykt K2 strony B identyczne z R600 (różnica = błąd parsera, nie zmiana protokołu).
3. Korpus, budowa, suchy przebieg: uc05 i uc03, po 1 przebiegu B i C z 10 podłączeniami. Sprawdza: `renameat` czy `renameat2`, rozpoznanie R_C, liczniki do puli / z puli / N_utw i spójność ogona, kolumny `pid` i `reaped`, częstość `futex` wątku slotu. **Bramka**: jeżeli wątek slotu woła `futex` w więcej niż 1 % slotów, kampania nie rusza, a decyzja (śledzenie `futex` tylko w osobnych przebiegach albo z filtrem) idzie do człowieka. Dane suchego przebiegu nie wchodzą do wyniku.
4. Kampania: 5 rodzin × 9 par = 90 przebiegów, ~2,5 h (R600: 90 przebiegów w 2 h 24 min), odczepiona (`setsid nohup`).
5. `wynik.md`, surowe archiwum w `paper-arXiv/rdb-experiment-embargo/R603C/` (wiersz w obu tabelach README), tutaj tylko indeks sum; komentarz w #603.

## Decyzje (zatwierdzone przez człowieka 2026-11-05: D1 (a), D2 SIGINT zostaje, D3 gałąź)

- **D1 - licznik trafień puli.** Log `queue pooled on timeout` nie istnieje w mierzonej binarce (*Ustalenia*, punkt 1). Rekomendacja: (a) licznik ze śladu (`kill` = -ESRCH → `renameat` = 0), sprawdzany krzyżowo przez spójność ogona (N_utw - 2 przepełnień) i liczbę oddań z puli; kod silnika bez zmian. Alternatywa (b): łatka aparatury P4 podnosząca obie linie (`pooled` i `erased`) do `SPDLOG_ERROR` w B i C; daje niezależny licznik, ale dodaje zapis do pliku i `flush` w wątku komunikacyjnym tuż za oknem R_C.
- **D2 - SIGINT zostaje** mimo ryzyka martwego muteksu (*Ustalenia*, punkt 3). Rekomendacja: zostawić (porównywalność z R600, ta sama postać w B i C) i rozpoznawać takie przypadki jako wyłączenie aparatury. Alternatywa: bez SIGINT (`xqry -m 1` po #599 kończy się sam), co usuwa ryzyko, ale zmienia chwilę wyjścia klienta wobec R600.
- **D3 - gałąź w `rdb-experiment`.** Rekomendacja: `experiment/20261105_R603C`, scalana do `main` po wyniku, jak R600 i R603.

## Embargo

Korpus `uc01`..`uc08` jest objęty embargiem do publikacji DEBS. W tym katalogu i w komentarzach do zgłoszeń: wyłącznie identyfikatory rodzin i liczby z nich wyprowadzone. Plany, dane, generatory i nazwy strumieni zostają na workerze w `/dev/shm/r376` i w prywatnym `paper-arXiv`. Surowe CSV i ślady ftrace poza git; zostaje indeks sum.

## Aneksy

1. **2026-11-05, przed budową i pomiarem: kontrola przepełnienia bufora ftrace.** `run_one.py` zapisuje w `meta.json` sumę pól `overrun` z `per_cpu/cpu*/stats` (`trace_overrun`), a `analyze.py` unieważnia przebieg przy wartości różnej od 0. Powód: śledzenie `futex` w wątku slotu zwiększa liczbę zdarzeń w śladzie, a utrata zdarzeń mogłaby ukryć parę `munmap` + `unlinkat` i fałszywie dać K1' = 0. Kryteria bez zmian.

## Stan

Protokół zatwierdzony i zapisany przed pomiarem (`add5aae`). Aparatura gotowa: `build_ab.sh`, `run_one.py`, `campaign.sh`, `analyze.py`. Test parsera (`analyze.py --raw <surowe R600> --parser-check`, strona B R600): 1350 okien, 0 różnic wobec parsera R600; liczby trafień strony B 29 / 270 / 270 / 0 / 0 (uc03, uc05, uc06, uc07, uc08) i werdykty K2 strony B jak w R600 (uc05 i uc06 NIEZDANE, p = 2,2e-04 i 1,3e-16; uc03, uc07, uc08 n < 100); p różni się od R600 tylko losowaniem pseudo-zdarzeń (ziarno 6031). Następny krok: korpus, budowa, suchy przebieg (*Kolejność*, punkt 3).
