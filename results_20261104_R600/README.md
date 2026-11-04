# R600 - zwolnienie porzuconej kolejki klienta poza wątkiem slotu (pi400, `--realtime`)

Zgłoszenie: michalwidera/retractordb#600 (ostatnie otwarte kryterium: pomiar skutku na pi400). Plan zatwierdzony przez człowieka 2026-11-04. Ten plik zapisano PRZED pomiarem; zmiany protokołu po starcie kampanii trafiają do sekcji *Aneksy* z datą i powodem, nie do treści powyżej.

Aparatura pochodzi z R376: `rdb-experiment`, gałąź `experiment/20261104_R376`, katalog `results_20261104_R376/` (protokół `5bb5448`, wynik `d55f3f6`). Opis aparatury, który się nie zmienił, jest tam w README; poniżej są tylko różnice i nowe kryteria.

## Pytanie

Czy po #600 kosztowne zwolnienie porzuconej kolejki odpowiedzi (`munmap` segmentu + `unlinkat` nazwy) przestało biec w wątku slotu i czy jego wykonanie w wątku komunikacyjnym nie wydłuża slotów, które na nie trafią. R376 (metryka 5) pokazało, że przed naprawą zwalnia wątek slotu w 270 z 270 podłączeń każdej rodziny z uc03 i uc05-uc08, a slot trafiony przez zwolnienie trwa p50 0,65-6,98 ms wobec 0,13-0,38 ms w slotach kontrolnych.

## Strony porównania

| Strona | Rewizja | Kto zwalnia porzuconą kolejkę |
|---|---|---|
| A | `42fcaa5db33928fa42fadbc8dd0b91816c0c13c9` | `broadcast()` w wątku slotu: `mqPtr.reset()` (munmap) i `removeOwned` (unlinkat), ~10 s po podłączeniu, gdy kolejka się zapełni |
| B | `221d312b86d42d1b3868fd7aac0703769f64b760` | `broadcast()` tylko przenosi uchwyt na listę `pendingRelease_`; munmap i unlinkat robi wątek komunikacyjny w `releaseAbandonedQueues()`, wołanym w każdym obrocie pętli odbioru (co ~1 ms, `kQueuePollInterval`) |

B jest bezpośrednim potomkiem A; różnica w silniku: `ipcServer.cpp`, `ipcServer.hpp` (plus test jednostkowy). A zawiera poprawkę #599 (`xqry -s -m N` kończy się po N elementach także na strumieniu > 1 kHz), więc obie strony mają ten sam klient.

## Aparatura - różnice wobec R376 i ich uzasadnienie

1. **Pinezki A i B** w `build_ab.sh` (powyższa tabela). Ta sama łatka P1 (`P1_deadline_ns.patch`, kolumna `deadline_ns`) na obu stronach; wchodzi czysto na obie rewizje. Budowa jak w R376: jedno drzewo `~/R376/src`, `scripts/buildrdb.sh probe` (Release, `RDB_BENCH_PROBE=ON`), najpierw A, potem B przyrostowo. `checkout -f`, bo drzewo niesie łatkę P1 z R376.
2. **Katalogi binarek i surowych danych**: `~/R376/bin/R600_A`, `~/R376/bin/R600_B` (`BIN_PREFIX` w `run_one.py`, ścieżka zapisana w `meta.json` jako `bin_dir`) i `~/R376/raw_R600`. Powód: binarki i dane R376 zostają nietknięte. Ścieżka uruchomienia `~/R376/exec/xretractor` (ten sam `argv[0]`, `setcap`) i katalog pracy `/dev/shm/r376/run` bez zmian, więc proces silnika widzi to samo co w R376.
3. **Rodziny**: uc03, uc05, uc06, uc07, uc08. uc01 i uc02 są nasycone na pi400 pod `-t` (R376, *Suchy przebieg*, punkt 3); uc04 nie zwalnia kolejki w czasie przebiegu (kolejka zapełnia się po ~500 s; R376, metryka 5).
4. **Korpus odtworzony**: `/dev/shm/r376` nie przetrwało od R376. Generatory rodzin z prywatnego `paper-arXiv` (`usecases/ucNN/generate_data.py` i `rql/query.rql`, HEAD `cc8c9e4`, ostatnia zmiana `usecases` w `7a76922`) nie mają losowości. Generator uruchamiany na workerze z wejścia standardowego ssh (`python3 -I - --out /dev/shm/r376/data/ucNN`), plan przez `cat` do `/dev/shm`; nic z korpusu nie trafia na dysk workera ani hosta. Skrót SHA-256 drzewa każdej rodziny na workerze zgodny z niezależną generacją na hoście.
5. **Strumień subskrybowany**: reguła R376 (`select_streams.sh`, najkrótszy takt wśród strumieni publicznych) powtórzona binarką `R600_A` dla 5 rodzin; wynik porównany ze `streams.tsv` R376 (oba pliki tylko na workerze, embargo). Wynik porównania: *Suchy przebieg*.
6. **SIGINT po pierwszym wierszu zostaje**, choć po #599 `xqry -m 1` kończy się sam: obie strony mają ten sam klient, więc SIGINT trafia najwyżej w kończący się proces, jednakowo w A i B. Serwer nie dowiaduje się o wyjściu klienta w żadnym wariancie, więc kolejka nadal jest porzucana po zapełnieniu.
7. **Bez zmian**: 9 par A/B na rodzinę w kolejności ABBA, 30 podłączeń na przebieg z przerwami z [2 s, 3 s], `taskset -c 3`, `-k -r -t`, `setcap cap_ipc_lock,cap_sys_nice=ep`, governor `performance`, ftrace `trace_clock=mono` (openat/statfs/fstatfs poza wątkiem RT; munmap i unlinkat we wszystkich wątkach), 12 s ogona po serii, unieważnienie przebiegu bez wątku `SCHED_FIFO` lub przy `VmLck = 0`.

## Okno zwolnienia i grupy slotów

- **Okno zwolnienia R** = [wejście w `munmap` adresu zwróconego przez `mmap` kolejki, wyjście z następującego po nim `unlinkat` tego samego wątku], szukane w całym śladzie i w **dowolnym** wątku (jak w R376). Analiza zapisuje TID wątku, który zwalniał: w A oczekiwany wątek slotu, w B wątek komunikacyjny. Okno bierze się więc zawsze z wątku, który zwalniał; R376 brało je z wątku RT tylko dlatego, że tam zwalniano. `removeOwned` między `munmap` a `unlinkat` wykonuje wyłącznie `lstat`/`stat`, których ftrace nie śledzi, więc sekwencja w wątku komunikacyjnym jest rozpoznawana bez zmiany parsera.
- **Slot trafiony przez zwolnienie**: przedział [`deadline_ns`, `deadline_ns + e2e_ns`] ma część wspólną z R. **Zdarzenie zwolnienia** = R, w które trafił co najmniej jeden slot; jego wartość = max `e2e_ns` tych slotów.
- **Sloty kontrolne** i pas ochronny: jak w R376 (dalej niż 0,5 s od każdego klienta i od każdego okna zwolnienia, wewnątrz serii ± 2 s).
- **Pseudo-zdarzenia zwolnienia**: na każde zwolnienie 20 okien tej samej długości co R, położonych losowo w serii, w całości w slotach kontrolnych i z co najmniej jednym slotem; wartość = max `e2e_ns` w oknie. Osobny generator losowy (ziarno 601), żeby nie przesuwać losowań pseudo-zdarzeń podłączenia (ziarno 600).

## Przewidywanie przed pomiarem

W B wątek komunikacyjny zaczyna zwalniać w ciągu ~1 ms po `broadcast()`, który kolejkę porzucił, czyli tuż po końcu slotu. Okno R trafi więc w następny slot tylko wtedy, gdy jest dłuższe niż odstęp do niego. Z długości zwolnień i taktów z R376:

| rodzina | takt slotu | kolejka | zwolnienie p50 (R376) | oczekiwane n zdarzeń zwolnienia w B |
|---|---|---|---|---|
| uc03 | 1/200 s | 2 MiB | 1,63 ms | ~0 |
| uc05 | 1/800 s | 8 MiB | 6,07 ms | ~270 |
| uc06 | 1/500 s | 5 MiB | 3,82 ms | ~270 |
| uc07 | 1/50 s | 0,5 MiB | 0,52 ms | ~0 |
| uc08 | 1/10 s | 0,1 MiB | 0,25 ms | ~0 |

Kryterium 2 jest zatem rozstrzygalne tylko w uc05 i uc06; w uc03, uc07 i uc08 wynik kryterium 2 będzie nierozstrzygnięty (decyzja człowieka 2026-11-04: przyjąć bez zmiany aparatury), a skutek #600 opisują tam kryterium 1 i odsetek zwolnień trafionych w slot (w A 100 % z konstrukcji).

## Kryteria (ustalone przed pomiarem)

Dla każdej rodziny i strony, sumarycznie po 9 przebiegach:

1. **K1 - kto zwalnia.** Liczba zwolnień, liczba i odsetek w wątku `SCHED_FIFO`, liczba w wątku, który zbudował kolejkę (`mmap` w `subscribe()`, wątek komunikacyjny), liczba podłączeń bez wykrytego zwolnienia.
   - **A - kontrola dodatnia**: każde zwolnienie w wątku slotu, jak w R376. Brak powtórzenia unieważnia porównanie w tej rodzinie.
   - **B zdane**, gdy każde zwolnienie wykonuje wątek inny niż wątek slotu `SCHED_FIFO`; niezdane przy choćby jednym zwolnieniu w wątku slotu. Brak zwolnień w B = nierozstrzygnięte. Podłączenia bez zwolnienia raportuje się osobno.
2. **K2 - wpływ zwolnienia na slot.** W B: max `e2e_ns` zdarzeń zwolnienia wobec pseudo-zdarzeń zwolnienia tej samej strony, jednostronny test Manna-Whitneya H1: zdarzenia > pseudo-zdarzenia. Raportuje się p50, p99, max obu rozkładów (p99 tylko przy n ≥ 100), różnicę median i odsetek zwolnień trafionych w slot.
   - **Zdane**: n ≥ 100 zdarzeń w B, kontrola dodatnia A spełniona i p ≥ 0,01.
   - **Niezdane**: n ≥ 100, kontrola dodatnia A spełniona i p < 0,01.
   - **Nierozstrzygnięte**: n < 100 w B (wynik i p podane, ale nie jako zdany), albo kontrola dodatnia A niespełniona.
   - **Kontrola dodatnia mocy testu** (rekomendacja przyjęta przez człowieka 2026-11-04): ten sam test na A (A-zdarzenia > A-pseudo) musi dać p < 0,01 przy n ≥ 100. Bez niej „p ≥ 0,01” w B mogłoby znaczyć tylko brak mocy testu.
3. **K3 - kontrola i regresja poza oknami zwolnienia.** W slotach kontrolnych A i B p50, p99, max `e2e_ns`, `compute_ns`, `wake_lag_ns`. Per przebieg `compute_ns` p50, `wake_lag_ns` p99 i `e2e_ns` p99; różnica median B-A porównana z rozrzutem między przebiegami tej samej strony (max..min po 9 przebiegach, reguła R376) i dokładny test permutacyjny Manna-Whitneya 9 vs 9. Różnica B-A dodatnia i większa od rozrzutu = **regresja B, osobne znalezisko** (nie zmienia werdyktu K1/K2, ale trafia do wyniku i do komentarza w #600).

Pomocniczo (opisowo, bez kryterium): okno budowy kolejki W, `mmap` kolejki i zdarzenie podłączenia jak w R376 - #600 ich nie dotyka, więc A i B powinny być w nich zgodne.

Analiza: `analyze.py --raw <raw> --seed 600`. Zmiany wobec `analyze.py` R376: zapis TID zwalniającego wątku i zgodności z wątkiem budującym kolejkę, licznik podłączeń bez zwolnienia, pseudo-zdarzenia zwolnienia, werdykty K1-K3 zamiast werdyktu #283 i eksploracji po pomiarze R376, `e2e_ns` p99 per przebieg w K3; usunięty bootstrap p99 (kryteria R600 go nie używają).

**Test analizy na danych R376** (przed kampanią, host): `analyze.py` R600 na surowych danych R376, gdzie obie strony zwalniają w wątku slotu, daje dla każdej rodziny z uc03 i uc05-uc08 K1 = NIEZDANE (0 z 270 poza wątkiem RT), K2 = NIEZDANE (B p ≤ 1,7e-28 przy n = 270, kontrola dodatnia A p ≤ 5,0e-31), K3 w szumie we wszystkich trzech miarach, przy czym `compute_ns` p50 i `wake_lag_ns` p99 równe wydrukowi R376 (z przeciwnym znakiem, bo B-A zamiast A-B). Analiza rozpoznaje więc zwolnienie w wątku slotu i wpływ zwolnienia na slot.

## Embargo

Korpus `uc01`..`uc08` jest objęty embargiem do publikacji DEBS. W tym katalogu i w komentarzach do zgłoszeń: wyłącznie identyfikatory rodzin i liczby z nich wyprowadzone. Plany, dane, generatory i nazwy strumieni zostają na workerze w `/dev/shm/r376` i w prywatnym `paper-arXiv`. Surowe CSV i ślady ftrace poza git; zostaje indeks sum (`results_20261104_R600_raw.index.tsv`).

## Suchy przebieg

2026-11-04, po zapisaniu kryteriów (`a44288e`): uc05 i uc03, po 1 przebiegu A i B z 10 podłączeniami (`~/R376/dry_R600`). Dane suchego przebiegu nie wchodzą do wyniku. Ustalenia, bez zmiany kryteriów:

1. **Budowa.** A 20:38-21:44 (66 min, prawie pełna budowa), B przyrostowo 21:44-21:51. `--build-info` A i B identyczne (wszystkie `RDB_OPT_*` i `RDB_BENCH_PROBE` ON). `xqry` A i B ma ten sam rozmiar i różni się tylko wbudowanym napisem rewizji i czasu budowy (`qryLauncher.cpp` kompiluje się przy każdej zmianie rewizji); tak samo było w R376. SHA-256: A `xretractor` `16ad8829...`, `xqry` `9db950f2...`; B `xretractor` `9eaccd49...`, `xqry` `c4e8f486...` (pełne sumy w `~/R376/bin/R600_{A,B}.sha256` i w `meta.json` każdego przebiegu).
2. **Strumień subskrybowany** wybrany regułą R376 binarką `R600_A` jest w 5 z 5 rodzin ten sam co w R376 (takty uc03 1/200 s, uc05 1/800 s, uc06 1/500 s, uc07 1/50 s, uc08 1/10 s). Plik porównania leżał przez chwilę w `/tmp` workera zamiast w `/dev/shm` i został od razu usunięty.
3. **K1 rozpoznawalne.** B: 10 z 10 zwolnień w uc03 i w uc05 wykonał wątek, który zbudował kolejkę (`SCHED_OTHER`, rdzenie 0-2), 0 w wątku `SCHED_FIFO`. A: 10 z 10 w wątku slotu. Każde podłączenie miało wykryte zwolnienie.
4. **Przewidywanie trafień potwierdzone.** uc03 B: 0 z 10 zwolnień trafiło w slot (A: 10 z 10). uc05 B: 10 z 10 trafiło; max `e2e_ns` zdarzenia p50 0,77 ms wobec 0,83 ms pseudo-zdarzeń (A: 5,93 ms wobec 0,74 ms), n = 10, nie do wniosków.
5. **Zwolnienie w wątku komunikacyjnym trwa dłużej** niż w wątku slotu: uc05 p50 6,45 ms (B) wobec 5,74 ms (A), uc03 1,84 wobec 1,68 ms, po 1 przebiegu. Wątek komunikacyjny jest `SCHED_OTHER` na rdzeniach współdzielonych z systemem. Wielkość opisowa, raportowana w wierszu „zwolnienie (munmap+unlinkat)”.
6. **K3 przy 1 przebiegu na stronę** ma rozrzut wewnątrz strony 0, więc każda różnica wychodzi „poza szumem”. To skutek liczności suchego przebiegu, nie aparatury; w kampanii 9 przebiegów na stronę, reguła bez zmian.

## Aneksy

(brak)

## Stan

Kryteria zapisane (`a44288e`), suchy przebieg zakończony (`6d6f81e`). Kampania 2026-11-04 21:56 - 2026-11-05 00:20, 90 z 90 przebiegów ważnych, bez zdarzeń wymagających aneksu. Wynik: `wynik.md`.
