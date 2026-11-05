# R603 - resztka K2 po #600: unieważnienie TLB czy zaśmiecenie L2 (pi400, `--realtime`)

Zgłoszenie: michalwidera/retractordb#603. Plan zatwierdzony przez człowieka 2026-11-05 (komentarz w #603 z ustaleniami kroków 1-2 i dwoma uzupełnieniami planu). Ten plik zapisano PRZED pierwszym pomiarem; zmiany protokołu po starcie trafiają do sekcji *Aneksy* z datą i powodem, nie do treści powyżej.

Badanie ma dwie części. Część I to mikrotest bez silnika i bez korpusu; rozstrzyga, czy mechanizm H-a w ogóle działa na tym sprzęcie i jądrze. Część II to kampania na silniku w aparaturze R600 (uc05 i uc06); rozdziela udział H-a i reszty w resztce K2.

## Pytanie

R600 (`results_20261104_R600/wynik.md`) pokazało, że po #600 zwolnienie porzuconej kolejki (`munmap` + `unlinkat`) biegnie już tylko w wątku komunikacyjnym na rdzeniach 0-2, a mimo to sloty obudzone w trakcie zwolnienia są dłuższe od kontrolnych. Różnica median max `e2e_ns` zdarzenia wobec pseudo-zdarzenia wynosi 0,030 ms w uc05 i 0,043 ms w uc06 (Mann-Whitney p = 2,2e-04 i 5,2e-16, n = 270), czyli K2 jest niezdane. Pytanie brzmi: jakim mechanizmem zwolnienie na innym rdzeniu wydłuża slot na izolowanym rdzeniu 3 i jaka część resztki przypada na każdy mechanizm.

## Hipotezy

- **H-a: unieważnienie TLB całego ASID.** `munmap` zakresu od 512 stron wzwyż kończy się `flush_tlb_mm()`, czyli `TLBI ASIDE1IS`: rozgłoszonym unieważnieniem wszystkich wpisów ASID procesu na wszystkich rdzeniach. Wątek slotu należy do tego samego procesu, więc po pobudce uzupełnia TLB przejściami tablic stron. Przy włączonym KPTI dotyczy to także wpisów ścieżki jądra (pobudka, powrót z `clock_nanosleep`).
- **H-b: zaśmiecenie wspólnego L2.** `munmap` (tablice stron, struktury stron) i `unlinkat` (zwalnianie stron tmpfs) wypierają z L2 1 MiB, wspólnego dla 4 rdzeni, dane wątku slotu.
- **H-c (alternatywa, ujawniona przez wariant B'): koszt samych operacji TLBI na stronę.** Zwolnienie w kawałkach zamienia jedno `TLBI ASIDE1IS` na kilka tysięcy rozgłoszonych `TLBI VALE1IS`. Jeśli rdzeń slotu płaci za przyjmowanie każdej z nich, B' może wydłużać slot bardziej niż B.

Hipotezy się nie wykluczają. Część II mierzy udział, a nie wybiera jedną z nich.

## Stan platformy ustalony przed pomiarem (kroki 1-2 planu, 2026-11-05)

- Jądro `6.8.0-2049-raspi-realtime` (`PREEMPT_RT`), `isolcpus=3 nohz_full=3 rcu_nocbs=3`, Cortex-A72 bez TLBI na zakresach (`Features: fp asimd evtstrm crc32 cpuid`).
- Próg z `/usr/src/linux-headers-6.8.0-2049-raspi-realtime/arch/arm64/include/asm/tlbflush.h`: `__flush_tlb_range()` woła `flush_tlb_mm()`, gdy `(end - start) >= MAX_DVM_OPS * stride`, `MAX_DVM_OPS = PTRS_PER_PTE = 512`. Przy stronach 4 KiB próg to 2 MiB włącznie. Poniżej progu unieważnienie idzie po jednej operacji `VALE1IS` na stronę, a przy KPTI drugą operacją dla ASID użytkownika.
- KPTI włączone: `dmesg` zawiera `kernel page table isolation forced ON by KASLR`. `flush_tlb_mm()` wysyła `__tlbi(aside1is, asid)` i `__tlbi_user(aside1is, asid)`, czyli czyści oba ASID procesu.
- PMU `armv8_cortex_a72`: per wątek przez `perf_event_open(pid = 0, cpu = -1)`, z jądrem (`exclude_kernel = 0`), wymaga `cap_perfmon` (`perf_event_paranoid = 4`). Sześć zdarzeń w jednej grupie liczy się bez multipleksowania (`nmi_watchdog = 0`). Brak `L2D_TLB_REFILL` (0x2D) i `DTLB_WALK` (0x34).
- `perf` 6.8.12 zainstalowany za zgodą człowieka (`linux-tools-6.8.0-2049-raspi-realtime`), do kontroli krzyżowej.

**Granica licznika TLB.** A72 ma 32-wpisowy L1 dTLB i 1024-wpisowe L2 TLB. `l1d_tlb_refill` liczy każde uzupełnienie L1, czy to z L2 TLB, czy z przejścia tablic. Gdy zbiór roboczy przekracza 32 strony, chybienia L1 zdarzają się w każdym slocie, a unieważnienie ASID zamienia je głównie w przejścia tablic, które licznik pokazuje tak samo. Przyrost `l1d_tlb_refill` jest wtedy ograniczony do wpisów, które były w L1, a koszt widać w czasie i w dostępach do L2 (`l2d_cache`; przejścia tablic czytają przez L2). Dlatego mikrotest ma dwa zbiory robocze: 16 stron (mechanizm widoczny w liczniku) i 512 stron (koszt widoczny w czasie), a kryteria kampanii opierają się na interwencji B', a liczniki są potwierdzeniem mechanizmu.

## Część I - mikrotest (`microtest/`)

`microtest/tlb_microtest.c` (opis w nagłówku pliku). Dwa wątki jednego procesu:

- **S** (`SCHED_FIFO` 80, rdzeń 3) co 1250 µs (takt uc05) budzi się na termin bezwzględny, czyta grupę sześciu liczników (odcinek „pobudka”), dotyka `--pages` stron prywatnego bufora i czyta liczniki ponownie (odcinek „praca”).
- **R** (`SCHED_OTHER`, rdzeń 0) 80 razy tworzy segment 8 MiB w `/dev/shm` (jak kolejka uc05: `ftruncate` + `posix_fallocate`, mapowanie `MAP_SHARED`, zapis każdej strony), czeka 200 ms i zwalnia go: `munmap` całości (tryb `whole`) albo kawałkami po `--chunk-kib` rosnąco (tryb `chunk`), potem `shm_unlink`. Tryby w kolejności ABBA, 40 zdarzeń na tryb, 300 ms przerwy po każdym.

Zdarzenia: `mlockall`, PMU `INST_RETIRED`, `L1D/L1I_TLB_REFILL`, `L2D_CACHE`, `L2D_CACHE_REFILL`, `L1D_CACHE_REFILL`. Przebieg z jakimkolwiek slotem multipleksowanym (`time_enabled != time_running`) jest nieważny.

Analiza `microtest/analyze_microtest.py` (ziarno 603). Zdarzenie dotyka slotów, których `[deadline, end]` przecina okno `[t_begin, t_end]`, oraz pierwszego slotu po oknie, bo unieważnienie zachodzi na końcu `munmap`. Wartość zdarzenia to max miary po tych slotach; liczniki sumują odcinek pobudki i pracy. Sloty kontrolne leżą dalej niż 50 ms od każdego `[t_create, t_end]`. Pseudo-zdarzenia: 20 na zdarzenie, ta sama długość okna, w całości w slotach kontrolnych. Nadwyżka Δ = mediana zdarzeń - mediana pseudo-zdarzeń; test jednostronny Manna-Whitneya H1: zdarzenia > pseudo (jak R600).

Przebiegi (worker, governor `performance`, binarka z `cap_perfmon,cap_sys_nice,cap_ipc_lock=ep` w `~/R603/microtest`, wyjście w `/dev/shm/r603`):

| przebieg | `--pages` | `--chunk-kib` | po co |
|---|---|---|---|
| m1 | 16 | 1024 | mechanizm widoczny w liczniku TLB |
| m2 | 512 | 1024 | koszt widoczny w czasie pracy |
| m3 | 16 | 2048 | sprawdzenie progu: kawałek 2 MiB spełnia `>=` i powinien zachować się jak `whole` |

### Przewidywanie (H-a prawdziwa)

- m1 `whole`: Δ `l1d_tlb_refill` ≈ 16 (cały zbiór roboczy) plus wpisy ścieżki jądra; m1 `chunk`: Δ ≈ 0.
- m2 `whole`: Δ `work_ns` dodatnie (512 przejść tablic) i Δ `l2d_cache` dodatnie; m2 `chunk`: Δ ≈ 0, chyba że działa H-c.
- m3 `chunk` (2 MiB): jak `whole`.

### Kryteria mikrotestu

- **M1 - mechanizm.** Zdane, gdy w m1 `whole` Δ `l1d_tlb_refill` ≥ 8 (połowa zbioru roboczego) przy p < 0,01, a w m1 `chunk` Δ `l1d_tlb_refill` ≤ 25 % wartości `whole`. Niezdane w `whole` (Δ < 8 albo p ≥ 0,01) znaczy, że `munmap` na rdzeniu 0 nie czyści widocznie TLB wątku na rdzeniu 3; H-a jest wtedy odrzucona na poziomie sprzętu i jądra, a część II rozstrzyga już tylko między H-b a H-c.
- **M2 - koszt.** Zdane, gdy w m2 `whole` Δ `work_ns` > 0 przy p < 0,01, a w m2 `chunk` Δ `work_ns` ≤ 50 % wartości `whole`. Δ `work_ns` w `chunk` większe niż w `whole` = wskazanie H-c.
- **M3 - próg.** Zdane, gdy w m3 `chunk` Δ `l1d_tlb_refill` ≥ 50 % wartości m3 `whole`; potwierdza, że kawałek 2 MiB nie wystarcza, a próg działa tak, jak go odczytano ze źródła.

Pozostałe miary (`wake_lag_ns`, `e2e_ns`, `l1i_tlb_refill`, `l2d_cache`, `l2d_cache_refill`, długość okna) raportuje się opisowo. Mikrotest nie używa korpusu, więc źródło, surowe CSV i wynik mogą być w tym repozytorium w całości.

## Część II - kampania w aparaturze R600

### Strony porównania

| Strona | Rewizja silnika | Łatki aparatury |
|---|---|---|
| B | `221d312b86d42d1b3868fd7aac0703769f64b760` (strona B z R600, #600) | P1 (`deadline_ns`, z R600) + P2 (liczniki PMU w sondzie slotu) |
| B' | ta sama | P1 + P2 + P3 (zwolnienie mapowania kolejki w kawałkach 1 MiB) |

- **P2** (`P2_pmu_counters.patch`, tylko `src/rdb/lib/probe.cc`): wątek slotu przy pierwszej pobudce otwiera grupę sześciu liczników z części I. Grupę czyta po pobudce (`markWake`, za pomiarem czasu pobudki) i na końcu slotu (`writeRow`, za pomiarem czasu emisji). CSV sondy dostaje 12 kolumn: `wake_<zdarzenie>` (od końca poprzedniego slotu do pobudki) i `slot_<zdarzenie>` (od pobudki do końca slotu). Przy nieudanym otwarciu albo multipleksowaniu kolumny mają wartość -1. Koszt dwóch odczytów `read()` na slot jest taki sam w B i B'.
- **P3** (`P3_chunked_unmap.patch`, tylko `src/retractor/lib/ipcServer.cpp`): w `releaseAbandonedQueues()`, przed `queue.reset()`, wątek komunikacyjny odczytuje z `/proc/self/maps` zakresy mapowania pliku kolejki i robi `munmap` po 1 MiB rosnąco. Następujący `queue.reset()` woła `munmap` na pustym już zakresie, a `removeOwned` usuwa nazwę bez zmian. Kawałek 1 MiB (256 stron) jest poniżej progu z zapasem na zaokrąglenie zakresu i na mapowanie niewyrównane do 2 MiB.
- Budowa jak w R600: drzewo `~/R376/src`, `scripts/buildrdb.sh probe` (Release, `RDB_BENCH_PROBE=ON`), najpierw B, potem B' przyrostowo; binarki w `~/R376/bin/R603_B` i `~/R376/bin/R603_Bp`. `setcap cap_ipc_lock,cap_sys_nice,cap_perfmon=ep` na `~/R376/exec/xretractor` (do R600 dochodzi `cap_perfmon`).

### Aparatura - różnice wobec R600

1. Strony B i B' zamiast A i B (`build_ab.sh`, `run_one.py`: `BIN_PREFIX = "R603_"`, strony `B` i `Bp`).
2. Rodziny: uc05 i uc06, jedyne, w których K2 było rozstrzygalne (R600, *Przewidywanie*).
3. Korpus odtworzony w `/dev/shm/r376` procedurą z R600 (README R600, punkt 4), bo worker był restartowany. Skróty SHA-256 drzew rodzin porównane z R600.
4. **Parser okna zwolnienia.** `find_release()` R600 kończy okno na pierwszym wejściu w wywołanie inne niż `unlinkat` po pierwszym `munmap`, więc w B' ucinałby okno do pierwszego kawałka. Nowy parser: okno zaczyna wejście w pierwszy `munmap`, którego adres leży w zakresie `[adres mmap kolejki, adres + długość)`. Następne wejścia i wyjścia `munmap` tego wątku w tym zakresie należą do okna, a koniec wyznacza wyjście z `unlinkat`. Na danych R600 nowy parser musi dać okna identyczne z R600 (sprawdzane przed suchym przebiegiem); różnica = błąd parsera, a nie zmiana protokołu.
5. Bez zmian wobec R600: 9 par na rodzinę w kolejności ABBA (para nieparzysta B, B'; parzysta B', B), 30 podłączeń na przebieg z przerwami z [2 s, 3 s], `taskset -c 3`, `-k -r -t`, governor `performance`, ftrace `trace_clock=mono`, 12 s ogona, unieważnienie przebiegu bez wątku `SCHED_FIFO` albo przy `VmLck = 0`. Dochodzi unieważnienie przebiegu, w którym po pierwszym slocie wystąpi wartość -1 w kolumnach P2.
6. Zdarzenie zwolnienia, sloty trafione, sloty kontrolne i pseudo-zdarzenia zwolnienia jak w R600 (slot trafiony: `[deadline_ns, deadline_ns + e2e_ns]` przecina R); ziarno pseudo-zdarzeń 603. Dla każdej miary wartość zdarzenia to max po slotach trafionych. Licznik slotu = `wake_<zdarzenie> + slot_<zdarzenie>`.

### Miary

Dla strony s i miary X: Δ_X(s) = mediana X po zdarzeniach zwolnienia - mediana X po pseudo-zdarzeniach tej samej strony.

- `e2e` = max `e2e_ns` (miara K2 z R600);
- `T` = max (`l1d_tlb_refill` + `l1i_tlb_refill`);
- `L2A` = max `l2d_cache`;
- `L2R` = max `l2d_cache_refill`.

### Kryteria (ustalone przed pomiarem; osobno w uc05 i uc06)

- **C0 - kontrola dodatnia.** B powtarza R600: n ≥ 100 zdarzeń i test K2 (zdarzenia > pseudo, MW) daje p < 0,01. Bez C0 rodzina jest nierozstrzygnięta: brak resztki w B znaczy, że nie ma czego rozdzielać.
- **C1 - B' zwalnia w kawałkach.** Każde zwolnienie w B' ma w śladzie co najmniej ⌈rozmiar mapowania / 1 MiB⌉ wywołań `munmap` wątku komunikacyjnego w zakresie kolejki, a żadne nie biegnie w wątku `SCHED_FIFO`. Niespełnione C1 unieważnia rodzinę.
- **C2 - H-a.**
  - **Wsparta**, gdy Δ_e2e(B') ≤ 0,5 · Δ_e2e(B), a w B T zdarzeń > T pseudo (MW p < 0,01) i Δ_T(B') ≤ 0,5 · Δ_T(B).
  - **Wsparta tylko interwencyjnie**, gdy warunek na `e2e` jest spełniony, a warunek na T nie (granica licznika TLB, zob. wyżej; wtedy raportuje się L2A jako wskaźnik przejść tablic).
  - **Niewsparta**, gdy Δ_e2e(B') > 0,5 · Δ_e2e(B).
- **C3 - reszta po B' (H-b albo H-c).**
  - Test K2 na B' (zdarzenia > pseudo, MW): p < 0,01 przy n ≥ 100 = resztka po B' istnieje.
  - Jeśli istnieje i w B' L2R zdarzeń > L2R pseudo (MW p < 0,01), raportuje się ją jako zgodną z H-b.
  - Δ_e2e(B') > Δ_e2e(B) = B' gorszy od B, wskazanie H-c.
- **C4 - udział.** u_a = 1 - Δ_e2e(B') / Δ_e2e(B) (udział usunięty przez B', przypisywany H-a), u_r = Δ_e2e(B') / Δ_e2e(B) (reszta), z 95 % przedziałem bootstrap (2000 losowań ze zwracaniem zdarzeń i pseudo-zdarzeń obu stron, ziarno 603). Raportuje się też K2 R600 dla B' (zdane / niezdane / nierozstrzygnięte) i odsetek okien zwolnienia z przekroczeniem taktu, bo to wprost mówi, czy zwolnienie w kawałkach jest kandydatem na naprawę.

Opisowo, bez kryterium: długość okna zwolnienia w B i B', `wake_lag_ns` i `compute_ns` slotów trafionych, wszystkie sześć liczników w odcinkach pobudki i slotu osobno, sloty kontrolne B wobec B' (P3 działa tylko w czasie zwolnienia, więc powinny być zgodne).

### Kolejność

1. Mikrotest m1-m3 i jego wynik w `microtest/wynik.md`.
2. P2, P3, budowa B i B', test parsera na danych R600.
3. Suchy przebieg: uc05, po 1 przebiegu na stronę, 10 podłączeń; sprawdza C1, kolumny P2 i okna. Dane suchego przebiegu nie wchodzą do wyniku.
4. Kampania: uc05 i uc06 × 9 par, ~1 h.
5. `wynik.md`, surowe archiwum w `paper-arXiv/rdb-experiment-embargo/R603/`, tutaj tylko indeks sum.

## Suchy przebieg (część II)

2026-11-05, po zapisaniu kryteriów (`fab5036`), wyniku mikrotestu (`b1e673e`) i analizy (`73c1b95`): uc05, po 1 przebiegu B i B' z 10 podłączeniami (`~/R376/dry_R603`). Dane suchego przebiegu nie wchodzą do wyniku. Ustalenia, bez zmiany kryteriów:

1. **Budowa** 08:16-08:26, B 5 min (przebudowany tylko `probe.cc`), B' przyrostowo 5 min (`ipcServer.cpp`), bez ostrzeżeń kompilatora w obu plikach. `--build-info` B i B' identyczne (wszystkie `RDB_OPT_*` i `RDB_BENCH_PROBE` ON). SHA-256 `xretractor`: B `d828a9dd...`, B' `476e7430...` (pełne sumy w `~/R376/bin/R603_{B,Bp}.sha256` i w `meta.json` każdego przebiegu).
2. **Korpus** uc05 i uc06 odtworzony procedurą R600 (punkt 4 README R600); skrót SHA-256 drzewa każdej rodziny na workerze zgodny z niezależną generacją na hoście (uc05 `ce892219...`, uc06 `cb51496c...`; kopie na hoście usunięte). `streams.tsv` skopiowany z `~/R376/apparatus_R600` (tylko na workerze).
3. **Test parsera** (`analyze.py --parser-check` na surowych danych R600): 2700 okien, 0 różnic wobec parsera R600.
4. **C1 rozpoznawalne.** B: 1 `munmap` na zwolnienie; B': 9 na zwolnienie (8 kawałków 1 MiB i końcowy `munmap` z `queue.reset()` na pustym już zakresie), 10 z 10 zwolnień w wątku komunikacyjnym, 0 w wątku `SCHED_FIFO`.
5. **Kolumny P2** ważne w obu stronach (12 kolumn, 0 wierszy z -1, bez multipleksowania). Takt slotu uc05 (mediana odstępu `deadline_ns`) = 1,000 ms.
6. **Log silnika.** W tym trybie silnik nie zostawia `$TMPDIR/xretractor.log`, więc `engine.log` nie powstaje. Kopia w `run_one.py` jest warunkowa i nic nie psuje. Ostrzeżenie P3 „brak mapowania” byłoby niewidoczne, ale jego skutek (1 `munmap` zamiast 9) wykrywa C1 ze śladu.
7. **Liczby przy n = 10 nie są do wniosków** (C0 z konstrukcji nierozstrzygnięte przy n < 100). Opisowo: sygnatura unieważnienia TLB z mikrotestu jest widoczna także w silniku. Δ `wake_l1i_tlb_refill` wynosi +7 w B i -1 w B', a Δ `wake_l2d_cache` +121 w B i -27 w B'. Nadwyżka `wake_l2d_cache_refill` występuje w obu stronach (+343 i +175).
8. Przebieg trwa ~45 s; kampania (36 przebiegów) ~30 min.

## Embargo

Część II używa korpusu `uc01`..`uc08`, objętego embargiem do publikacji DEBS. W tym katalogu i w komentarzach do zgłoszeń: wyłącznie identyfikatory rodzin i liczby z nich wyprowadzone. Plany, dane, generatory i nazwy strumieni zostają na workerze w `/dev/shm/r376` i w prywatnym `paper-arXiv`. Część I nie używa korpusu.

## Aneksy

(brak)

## Stan

Protokół zapisany przed pomiarem (`fab5036`). Mikrotest zakończony (`b1e673e`, `microtest/wynik.md`). Aparatura części II zbudowana, suchy przebieg zakończony; kampania uruchomiona po tym commicie (`~/R376/campaign_R603.log`, dane `~/R376/raw_R603`).
