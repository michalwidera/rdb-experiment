# R603C - wynik

Badanie: pomiar potwierdzający naprawę (a) z michalwidera/retractordb#603 (pula kolejek odpowiedzi, drenaż D1a, `rename`). Protokół i kryteria w `README.md` (`add5aae`, przed pomiarem), aparatura i test parsera `2f34d77`, suchy przebieg `b2b1236`.

Kampania 2026-11-05 17:27 - 19:55, pi400, rodziny uc03, uc05, uc06, uc07, uc08, 9 par B/C w kolejności ABBA, 30 podłączeń na przebieg: razem 90 przebiegów i 2700 podłączeń. Strony: B = `10f491b8` (drzewo = `221d312b`), C = `92faf689` (drzewo = `c9e3e80e`), obie z łatką P1. Każdy przebieg był ważny: wątek slotu `SCHED_FIFO` na rdzeniu 3, governor `performance`, uruchomiona binarka równa zbudowanej, `trace_overrun` = 0 (`run_one.py` i `analyze.py` przerywają przy każdym z tych warunków). Wszystkie 2700 klientów zakończyło się kodem -2 (SIGINT) i zostało zebranych (`reaped` = 1). Log kampanii kończy się `CAMPAIGN_COMPLETE`; kopia: `campaign.log`. Surowe dane (korpus pod embargiem) poza tym repozytorium, w prywatnym `paper-arXiv`, katalog `rdb-experiment-embargo/R603C/`: `results_20261105_R603C_raw.tar.gz` (42 792 709 B), SHA-256 `ab8fbc51c261b66d5900ca02af23a2e910ec6abe1ffe9ea4300dca6d3a1daf4b`; indeks 540 plików (90 przebiegów × 6 plików): `results_20261105_R603C_raw.index.tsv`. Analiza: `analyze.py --raw <raw> --seed 6031`; pełny wydruk niżej, w części *Wydruk analizy*.

## Odpowiedź

**Naprawa (a) robi to, co miała zrobić w mechanice puli: w żadnej z pięciu rodzin nie ma w czasie pracy zwolnienia kolejki `munmap` + `unlinkat` poza przypadkami martwego muteksu (K1' ZDANE wszędzie), podłączenie z puli skraca okno budowy kolejki 9-200 razy (O2), a poza oknami nic się nie pogorszyło (K3). Wpływu na sloty jednak nie usuwa: drenaż D1a w wątku komunikacyjnym wydłuża sloty obudzone w jego trakcie tak samo (uc05, u = 1,11) albo bardziej (uc06, u = 4,29) niż zwolnienie w B. K2 dla C jest NIEZDANE w uc05 i uc06, zgodnie z przewidywaniem zapisanym przed pomiarem (*Przewidywanie*, punkt 2), a w uc03, uc07 i uc08 NIEROZSTRZYGNIĘTE (n = 0 zdarzeń w C).**

| rodzina | takt | K1' (C) | okno R_B → R_C p50 [ms] | okna trafione B → C | K2: kontrola B | K2: C | Δ_e2e B → C [µs] | u (95 % bootstrap) | K3 |
|---|---|---|---|---|---|---|---|---|---|
| uc03 | 5 ms | **ZDANE**, 270/270 do puli | 1,866 → 0,791 | 35 → 0 | niespełniona (n = 35) | **NIEROZSTRZYGNIĘTE** (n = 0) | 58,14 → - | - | bez regresji |
| uc05 | 1 ms | **ZDANE**, 270/270 | 6,486 → 2,381 | 270 → 243 | spełniona, p = 4,2e-08 | **NIEZDANE**, n = 243, p = 7,4e-30 | 88,44 → 98,19 | 1,11 (0,69..1,63) | bez regresji |
| uc06 | 2 ms | **ZDANE**, 265/270, 5 wyłączeń (1,9 %) | 4,191 → 1,608 | 270 → 239 | spełniona, p = 8,0e-13 | **NIEZDANE**, n = 239, p = 1,6e-38 | 35,61 → 152,78 | 4,29 (3,12..6,66) | bez regresji |
| uc07 | 20 ms | **ZDANE**, 270/270 | 0,658 → 0,377 | 0 → 0 | niespełniona (n = 0) | **NIEROZSTRZYGNIĘTE** (n = 0) | - | - | bez regresji |
| uc08 | 100 ms | **ZDANE**, 270/270 | 0,337 → 0,278 | 0 → 0 | niespełniona (n = 0) | **NIEROZSTRZYGNIĘTE** (n = 0) | - | - | bez regresji |

- **K1': pula działa zgodnie z kodem.** Kontrola dodatnia B powtórzona w każdej rodzinie (270 par `munmap` + `unlinkat` na 270 porzuceń, 0 `kill` klienta). W C każde porzucenie przechodzi przez `kill(pid, 0)` = -ESRCH, a w 1345 z 1350 kończy się `renameat` pod nazwę puli. Na przebieg przypada 5-6 kolejek utworzonych i 24-25 oddanych z puli. W ogonie (po starcie ostatniego klienta) liczba okien przepełnienia zgadza się w każdym przebiegu z N_utw - N_skasowanych - 2 (razem 133). Pozostałe 5 porzuceń (wszystkie w uc06, po jednym w C_02, C_03, C_04, C_07, C_08) to zwolnienia `munmap` + `unlinkat` w fazie pracy, rozpoznane regułą martwego muteksu z protokołu: `kill` = -ESRCH przychodzi 1,4-2,6 ms po pierwszym wierszu klienta i 0,0-1,2 ms po jego śmierci, a nie po ~10 s zapełnienia, czyli `broadcast()` porzucił kolejkę od razu, jak przewidziały *Ustalenia*, punkt 3. 5 z 270 to 1,9 %, poniżej progu 5 % dla NIEROZSTRZYGNIĘTE. W przebiegu C_03 rozpoznanie wymagało poprawki parsera po kampanii (*Odstępstwa*, punkt 1).
- **K2: drenaż przenosi wpływ, a nie go usuwa.** Okno R_C jest 1,2-2,7 razy krótsze niż R_B (bez `munmap`, `unlinkat` i unieważnienia TLB), ale w uc05 i uc06 nadal obejmuje slot w 99,6-100 % przypadków. Max `e2e_ns` slotów z okna przewyższa pseudo-zdarzenia tej samej długości o 98 µs (uc05) i 153 µs (uc06) wobec 88 µs i 36 µs w B. Sloty obudzone w oknie liczą dłużej: mediana `compute_ns` 111,0 wobec 76,9 µs (uc05) i 337,2 wobec 285,3 µs (uc06), przy `wake_lag_ns` 33,4 wobec 27,2 µs i 35,1 wobec 28,1 µs. Wydłużone jest więc liczenie slotu, a nie jego pobudka, co pasuje do rywalizacji o wspólne L2 i pamięć (H-b z R603): drenaż czyta całą pełną kolejkę (uc05 ~8000 komunikatów, uc06 ~5000) w 1,6-2,4 ms, czyli ten sam albo większy ruch pamięci w krótszym czasie. Ślad nie rozdziela drenażu i `renameat`, bo drenaż nie robi wywołań systemowych.
- **K2 w ujęciu czasu rzeczywistego (uc05, takt 1 ms).** Okno zawiera slot dłuższy od taktu w 13,2 % przypadków w C wobec 28,1 % w B, a pseudo-okno w 5,2 % wobec 12,1 %. Nadwyżka nad tłem spada z 16 do 8 punktów procentowych, bo okno jest krótsze. Na pojedynczy slot w oknie C nie jest lepsze, ale okno rzadziej obejmuje kilka slotów. W uc06 ta miara nic nie rozstrzyga (okresowy slot ~48 ms, który przekracza takt także w slotach kontrolnych, jak w R600 i R603).
- **Faza okna (opisowo, poza protokołem).** W obu stronach i we wszystkich rodzinach okno startuje 0,04-1,1 ms (p5..p95) po końcu poprzedniego slotu: wątek komunikacyjny zwalnia kolejkę zaraz po rozesłaniu wyniku slotu. Okno obejmuje więc slot tylko wtedy, gdy jest dłuższe niż czas do następnego terminu (p50 ~0,6 ms w uc05, ~1,1 ms w uc06, ~4,1 ms w uc03). Stąd 0 trafień C w uc03, uc07 i uc08 przy oknach 0,28-0,79 ms. Procedura: *Odtworzenie od zera*, punkt 5.
- **K3: bez regresji.** We wszystkich rodzinach różnice median C - B dla `compute_ns` p50, `wake_lag_ns` p99 i `e2e_ns` p99 per przebieg mieszczą się w rozrzucie wewnątrz strony. Wszystkie permutacyjne p < 0,01 dotyczą różnic ujemnych, czyli C szybszego (uc03 `compute_ns` p50 -1,5 µs, uc05 `wake_lag_ns` p99 -21 µs i `e2e_ns` p99 -22 µs, uc07 i uc08 `e2e_ns` p99 -22 µs), więc kryterium regresji (różnica dodatnia i większa od rozrzutu) nie jest spełnione nigdzie.
- **O1: inwersja priorytetów na muteksie kolejki istnieje, ale jest mała.** Wątek slotu woła `futex` w 0,034-0,129 % slotów (bramka 1 % spełniona). `FUTEX_WAIT` na muteksie kolejki odpowiedzi (slot czeka na klienta): uc05 6 (B) / 12 (C), uc06 4 / 9, uc07 1 / 0, uc03 i uc08 0, na 9 przebiegów. Czekanie p50 9-15 µs, max 84 µs (uc06 C). Żadne nie leży w oknie K2. Slot dłuższy od taktu z takim czekaniem: uc06 1 (B) i 2 (C), w rodzinie, która ma okresowe sloty ~48 ms. Więcej `FUTEX_WAIT` w C to opisowo nie więcej niż 2 razy więcej przy liczbach jednocyfrowych; nie testowano.
- **O2: podłączenie z puli usuwa zdarzenie podłączenia (#283).** Okno budowy kolejki utworzonej (`shm_open`, `fallocate`, `mmap`) wynosi p50 10,4 ms (uc05), 6,7 ms (uc06), 2,9 ms (uc03), 1,0 ms (uc07), 0,5 ms (uc08), a okno oddania z puli (`renameat`) 0,052-0,053 ms we wszystkich rodzinach. W uc05 okno budowy obejmuje slot w 270 z 270 przypadków z max `e2e_ns` p50 0,953 ms, a okno z puli w 47 z 225 przypadków z p50 0,181 ms. W uc06 70 z 222 okien z puli trafia w slot z max `e2e_ns` p50 46,5 ms: to okresowy długi slot tej rodziny, który występuje też w slotach kontrolnych; z tych danych nie wynika, że okno go wydłuża.
- **O3: okna przepełnienia są dłuższe niż R_B.** Przepełnienie (drenaż, potem `munmap` + `unlinkat` najstarszego wpisu, potem `renameat`) trwa p50 8,9 ms w uc05 wobec 6,5 ms R_B, 5,8 ms w uc06 wobec 4,2 ms. W tej kampanii przepełnienia leżą tylko w ogonie, ale w pracy wystąpią przy każdej serii więcej niż dwóch porzuceń bez nowych podłączeń o tej samej pojemności.

## Odstępstwa od protokołu i od przewidywania

1. **Poprawka parsera po kampanii (`analyze.py`, `kill_windows`).** Parser zatwierdzony przed pomiarem kończył okno R_C na pierwszym udanym `renameat` wątku komunikacyjnego. Oddanie z puli nowemu klientowi robi jednak `renameat` bez innego śledzonego wywołania przed nim (`lstat` to `newfstatat`, poza śladem), więc po skasowaniu kolejki (`munmap` + `unlinkat` bez `renameat`) okno sięgało do oddania z puli dla następnego klienta. Tak było w jednym przypadku: uc06 C_03, podłączenie 13, `kill` 31,788 s, `unlinkat` 31,792 s, a następny `renameat` dopiero 34,131 s, w trakcie podłączenia 14 (start 34,118 s), które nie budowało kolejki. Parser zaliczył je jako przepełnienie o długości 2343,6 ms. Poprawka: `renameat` później niż 10 ms po `unlinkat` nie należy do okna (`RENAME_AFTER_UNLINK_MAX_NS`). Uzasadnienie progu z tej kampanii: w 133 pozostałych oknach przepełnienia odstęp `unlinkat` → `renameat` wynosi p50 187 µs i max 314 µs. Skutek: uc06 K1' zmienia się z NIEZDANE (1 niewyjaśniona para w fazie pracy, 4 wyłączenia) na ZDANE (0 niewyjaśnionych, 5 wyłączeń). Spójność ogona C_03 wynosi teraz 3 = 6 - 1 - 2, a wcześniej 4 = 6 - 0 - 2, przy czym jedno z tych 4 „przepełnień” leżało w fazie pracy. uc06 K2 C: p = 4,44e-39 → 1,61e-38, Δ_e2e 152,69 → 152,78 µs; inne rodziny i strona B bez zmian. Test parsera na danych R600 po poprawce: 1350 okien, 0 różnic.
2. **Martwy muteks nie jest tylko artefaktem aparatury.** Protokół przypisał go aparaturze (SIGINT w trakcie `try_receive`), ale ta sama ścieżka zadziała przy każdym kliencie zabitym w trakcie odbioru. Naprawa (a) zostawia więc w czasie pracy `munmap` + `unlinkat` dla takich śmierci: w tej aparaturze 1,9 % porzuceń w uc06 i 0 % w pozostałych rodzinach. Przyczyny różnicy między rodzinami nie badano.
3. **Kontrola dodatnia B w uc05 jest silniejsza niż w R600.** Δ_e2e B wynosi 88,44 µs w uc05 i 35,61 µs w uc06, wobec ~30 i ~43 µs w R600 (`results_20261105_R603/wynik.md`, *Odchylenia*, punkt 2). Kod B jest ten sam co strony B R600, a binarka różni się w 25 821 bajtach (*Suchy przebieg*, punkt 1). Bezwzględne Δ nie przenosi się więc między kampaniami. Porównanie B z C w tej kampanii jest ważne, bo strony idą na przemian (ABBA).
4. **Przewidywanie K2 sprawdziło się co do werdyktów** (NIEZDANE w uc05 i uc06, n < 100 w uc03, uc07, uc08). W uc03 C ma n = 0, a nie „raczej n < 100”: okno 0,79 ms mieści się w przerwie po slocie (*Faza okna*).

## Granice wniosków

- Jedna platforma: Cortex-A72, wspólne L2 1 MiB, jądro 6.8 `PREEMPT_RT`. Na procesorze z większym albo prywatnym L2 drenaż kolejki 5-8 MiB może wyglądać inaczej.
- W tej aparaturze kolejka jest przy porzuceniu zawsze pełna: klient ginie ~2 ms po pierwszym wierszu, a serwer porzuca kolejkę dopiero po zapełnieniu (~10 s). Tak samo jest w pracy, bo porzucenie przy martwym kliencie następuje tylko po zapełnieniu (poza martwym muteksem). Koszt drenażu D1a jest więc tu taki, jaki będzie w pracy dla każdej rodziny.
- „Pasuje do H-b” znaczy, że w oknie C rośnie `compute_ns`, a nie `wake_lag_ns`. Liczników PMU w tej kampanii nie było (bez P2, zgodnie z protokołem), więc chybień L2 nie zmierzono.
- Faza okna względem slotu to obserwacja spoza protokołu, policzona po kampanii.

## Skutek dla naprawy (do decyzji człowieka)

Naprawa (a) jest poprawna i usuwa dwa koszty: zwolnienie w czasie pracy (K1') i budowę kolejki przy podłączeniu (O2, #283). Nie spełnia K2, bo drenaż D1a sam jest strumieniem pamięci rozmiaru kolejki. Możliwe kierunki, według obserwacji fazy okna:

1. **Drenaż w porcjach mieszczących się w przerwie po slocie** (wariant D1c z planu). Okno startuje zaraz po rozesłaniu wyniku slotu i nie trafia w slot, gdy kończy się przed następnym terminem (uc03, uc07, uc08: 0 trafień). Porcja ograniczona czasem albo liczbą komunikatów (w uc05 przerwa ~0,6 ms, czyli mniej niż 1/4 obecnego drenażu) rozkłada drenaż na kolejne obroty wątku komunikacyjnego. Kolejka trafia do puli później, ale pula i tak czeka ~10 s na następnego klienta. Mierzalne tą samą aparaturą (strona C').
2. **Wcześniejsze rozpoznanie śmierci klienta.** Dziś kolejka martwego klienta zapełnia się przez 10 s i dopiero wtedy jest opróżniana. Sprawdzenie `inspectProcess` subskrybentów w krótszym rytmie (np. co 1 s) zmniejszyłoby drenaż proporcjonalnie do czasu rozpoznania i skróciło trzymanie pamięci. Żywego wolnego klienta to nie zmienia. Koszt: `openat` + `kill` na subskrybenta na sprawdzenie w wątku komunikacyjnym.
3. **Własny pierścień SPSC zamiast `message_queue`** (opcja z komentarza w #603). Reset w O(1), brak muteksu robust (znika O1 i ścieżka martwego muteksu). Największa zmiana: protokół klienta i rdzeń współbieżny.

Rekomendacja: 1, bo jako jedyna celuje w mechanizm widoczny w danych (okno dłuższe od przerwy po slocie), nie zmienia semantyki ani protokołu i daje się zweryfikować tą samą aparaturą. 2 można dołożyć niezależnie, bo zmniejsza ruch pamięci także w oknach przepełnienia. 3 dopiero, jeśli 1 nie da K2 albo inwersja O1 okaże się istotna.

## Odtworzenie od zera

Wszystko na workerze `pi400` z katalogu `~/R376/apparatus_R603C` (kopia tego katalogu), poza analizą:

1. Korpus uc03, uc05-uc08 jak w R600 (`results_20261104_R600/wynik.md`, *Odtworzenie od zera*, punkt 3): generator z prywatnego `paper-arXiv` przez wejście standardowe ssh do `/dev/shm/r376/data/<rodzina>`, plan przez `cat`; `streams.tsv` z `~/R376/apparatus_R600` (tylko na workerze). Sprawdzenie: skróty SHA-256 drzew z *Suchy przebieg*, punkt 2 w `README.md`.
2. Budowa: `setsid nohup ./build_ab.sh > ~/R376/build_R603C.log 2>&1 < /dev/null &` (drzewo `~/R376/src`, pinezki B `10f491b8` i C `92faf689`, łatka P1; pełna budowa C ~21 min, B przyrostowo ~5 min).
3. Kampania: `setsid nohup ./campaign.sh > ~/R376/campaign_R603C.log 2>&1 < /dev/null &` (~2,5 h; governor ustawia skrypt). Przerwana rodzina = powtórzyć całą (ABBA).
4. Analiza na hoście: `rsync -a pi400:R376/raw_R603C/ <katalog>/raw/`, potem Python ≥ 3.10 z NumPy (np. `retractordb/.venv-python/bin/python3`) `-I analyze.py --raw <katalog>/raw --seed 6031`. Wydruk musi być identyczny z częścią *Wydruk analizy*. Test parsera: `analyze.py --parser-check --raw <rozpakowane archiwum R600>/raw --seed 6031` (1350 okien, 0 różnic).
5. Faza okna (punkt opisowy w *Odpowiedź*): dla każdego okna R_B (`find_release`) i R_C (`kill_windows`, bez przepełnień) różnica między `t0` a końcem (`deadline_ns + e2e_ns`) ostatniego slotu z `deadline_ns` ≤ `t0`; p5, p50, p95 po 9 przebiegach strony.

## Wydruk analizy

### uc03

Takt slotu (mediana odstępu deadline_ns): 5.000 ms.

| wielkość | B | C |
|---|---|---|
| przebiegi / podłączenia | 9 / 270 | 9 / 270 |
| K1': pary munmap+unlinkat kolejki (wszystkie) | 270 | 27 |
| K1': kill(pid_klienta, 0) / do puli (ESRCH → renameat) | 0 / 0 | 270 / 270 |
| K1': kolejki utworzone / oddane z puli | 270 / 0 | 45 / 225 |
| K1': pary w fazie pracy / przed nią / w ogonie (poza przepełnieniem) | - | 0 / 0 / 27 (0) |
| K1': przepełnienia puli / oczekiwane (utworzone - zwolnione bez puli - 2) | - | 27 / 27 |
| K1': wyłączenia: martwy muteks / klient niezebrany; inne zwolnienia bez puli | - | 0 / 0; 0 |
| wartości powrotu kill | - | -3 |
| rdzenie par munmap+unlinkat | 0, 1, 2 | 0, 1, 2 |
| okna K2 (R_B / R_C): liczba / w wątku RT | 270 / 0 | 243 / 0 |
| okno K2 [ms] p50 / max | 1.866 / 2.088 | 0.791 / 1.182 |
| okno przepełnienia [ms] p50 / max (liczba) | - / - (0) | 2.666 / 2.785 (27) |
| okna trafione w slot: n / odsetek | 35 / 13.0 % | 0 / 0.0 % |
| zdarzenie: max e2e [ms] p50 / p99 / max | 0.249 / - / 0.434 | - / - / - |
| pseudo-zdarzenie: liczba / max e2e [ms] p50 / p99 / max | 5400 / 0.191 / 3.012 / 3.461 | 4860 / 0.181 / 3.049 / 3.451 |
| Δ_e2e [µs]; MW p | 58.14; 3.07e-07 | - |
| okna z max e2e > takt: zdarzenia / pseudo | 0.0 % / 0.0 % | - |
| sloty obudzone w oknie: wake_lag / compute p50 [µs] (mediana po zdarzeniach) | 28.6 / 170.2 | - |
| kontrola e2e [ms] p50 / p99 / max | 0.187 / 2.915 / 3.676 | 0.175 / 2.907 / 3.555 |
| kontrola compute [ms] p50 / p99 / max | 0.133 / 2.869 / 3.597 | 0.131 / 2.870 / 3.436 |
| kontrola wake [ms] p50 / p99 / max | 0.024 / 0.039 / 0.124 | 0.024 / 0.043 / 0.114 |
| O1: futex wątku RT: wejścia / sloty z futex / sloty w serii | 189 / 107 / 139670 (0.077 %) | 169 / 91 / 139978 (0.065 %) |
| O1: futex na muteksie kolejki według op / poza kolejkami | WAKE 5 / 184 | WAKE 3 / 166 |
| O1: czekanie na muteks kolejki [ms] p50 / max; w oknie K2; slot > takt | brak | brak |
| O2: podłączenie, kolejka utworzona: liczba / okno p50 [ms] / trafione / max e2e p50 / max [ms] | 270 / 2.938 / 166 / 0.285 / 3.142 | 45 / 2.943 / 31 / 0.269 / 2.979 |
| O2: podłączenie, kolejka z puli: liczba / okno p50 [ms] / trafione / max e2e p50 / max [ms] | 0 / - / 0 / - / - | 225 / 0.053 / 9 / 0.273 / 2.936 |

- **K1'**: kontrola dodatnia B (270 zwolnień munmap+unlinkat na 270 podłączeń, kill klienta 0) powtórzona; C: do puli 270 z 270 (wyłączenia 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, spójność ogona tak. Werdykt: ZDANE.
- **K2**: kontrola dodatnia mocy B: n = 35, p = 3.07e-07 - NIESPEŁNIONA; C: n = 0, p = nan, Δ_e2e B = 58.14 µs, C = nan µs. Werdykt C: NIEROZSTRZYGNIĘTE (n = 0 < 100).
- K2 opisowo: u = Δ_e2e(C) / Δ_e2e(B) = nan (95 % bootstrap nan..nan).
- **K3**, compute_ns p50 per przebieg: mediana C-B = -1.52 µs, rozrzut wewnątrz strony do 1.55 µs, permutacyjny MW p = 0.000494 - w szumie.
- **K3**, wake_lag_ns p99 per przebieg: mediana C-B = 4.94 µs, rozrzut wewnątrz strony do 18.43 µs, permutacyjny MW p = 0.113 - w szumie.
- **K3**, e2e_ns p99 per przebieg: mediana C-B = 30.59 µs, rozrzut wewnątrz strony do 212.34 µs, permutacyjny MW p = 0.666 - w szumie.

### uc05

Takt slotu (mediana odstępu deadline_ns): 1.000 ms.

| wielkość | B | C |
|---|---|---|
| przebiegi / podłączenia | 9 / 270 | 9 / 270 |
| K1': pary munmap+unlinkat kolejki (wszystkie) | 270 | 27 |
| K1': kill(pid_klienta, 0) / do puli (ESRCH → renameat) | 0 / 0 | 270 / 270 |
| K1': kolejki utworzone / oddane z puli | 270 / 0 | 45 / 225 |
| K1': pary w fazie pracy / przed nią / w ogonie (poza przepełnieniem) | - | 0 / 0 / 27 (0) |
| K1': przepełnienia puli / oczekiwane (utworzone - zwolnione bez puli - 2) | - | 27 / 27 |
| K1': wyłączenia: martwy muteks / klient niezebrany; inne zwolnienia bez puli | - | 0 / 0; 0 |
| wartości powrotu kill | - | -3 |
| rdzenie par munmap+unlinkat | 0, 1, 2 | 0, 1, 2 |
| okna K2 (R_B / R_C): liczba / w wątku RT | 270 / 0 | 243 / 0 |
| okno K2 [ms] p50 / max | 6.486 / 7.683 | 2.381 / 3.001 |
| okno przepełnienia [ms] p50 / max (liczba) | - / - (0) | 8.900 / 9.459 (27) |
| okna trafione w slot: n / odsetek | 270 / 100.0 % | 243 / 100.0 % |
| zdarzenie: max e2e [ms] p50 / p99 / max | 0.869 / 1.410 / 2.065 | 0.255 / 1.360 / 1.453 |
| pseudo-zdarzenie: liczba / max e2e [ms] p50 / p99 / max | 5400 / 0.780 / 1.148 / 1.899 | 4860 / 0.157 / 1.091 / 1.556 |
| Δ_e2e [µs]; MW p | 88.44; 4.19e-08 | 98.19; 7.42e-30 |
| okna z max e2e > takt: zdarzenia / pseudo | 28.1 % / 12.1 % | 13.2 % / 5.2 % |
| sloty obudzone w oknie: wake_lag / compute p50 [µs] (mediana po zdarzeniach) | 27.2 / 76.9 | 33.4 / 111.0 |
| kontrola e2e [ms] p50 / p99 / max | 0.125 / 1.081 / 2.062 | 0.114 / 1.059 / 2.005 |
| kontrola compute [ms] p50 / p99 / max | 0.066 / 1.013 / 1.863 | 0.066 / 1.000 / 1.798 |
| kontrola wake [ms] p50 / p99 / max | 0.024 / 0.134 / 1.153 | 0.024 / 0.114 / 1.099 |
| O1: futex wątku RT: wejścia / sloty z futex / sloty w serii | 605 / 306 / 705731 (0.043 %) | 456 / 238 / 701357 (0.034 %) |
| O1: futex na muteksie kolejki według op / poza kolejkami | WAIT 6, WAKE 7 / 592 | WAIT 12, WAKE 12 / 432 |
| O1: czekanie na muteks kolejki [ms] p50 / max; w oknie K2; slot > takt | 0.009 / 0.036; 0; 0 | 0.013 / 0.047; 0; 0 |
| O2: podłączenie, kolejka utworzona: liczba / okno p50 [ms] / trafione / max e2e p50 / max [ms] | 270 / 10.401 / 270 / 0.953 / 1.749 | 45 / 10.421 / 45 / 0.955 / 1.207 |
| O2: podłączenie, kolejka z puli: liczba / okno p50 [ms] / trafione / max e2e p50 / max [ms] | 0 / - / 0 / - / - | 225 / 0.052 / 47 / 0.181 / 1.241 |

- **K1'**: kontrola dodatnia B (270 zwolnień munmap+unlinkat na 270 podłączeń, kill klienta 0) powtórzona; C: do puli 270 z 270 (wyłączenia 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, spójność ogona tak. Werdykt: ZDANE.
- **K2**: kontrola dodatnia mocy B: n = 270, p = 4.19e-08 - spełniona; C: n = 243, p = 7.42e-30, Δ_e2e B = 88.44 µs, C = 98.19 µs. Werdykt C: NIEZDANE.
- K2 opisowo: u = Δ_e2e(C) / Δ_e2e(B) = 1.11 (95 % bootstrap 0.69..1.63).
- **K3**, compute_ns p50 per przebieg: mediana C-B = -0.39 µs, rozrzut wewnątrz strony do 0.74 µs, permutacyjny MW p = 0.011 - w szumie.
- **K3**, wake_lag_ns p99 per przebieg: mediana C-B = -20.79 µs, rozrzut wewnątrz strony do 43.25 µs, permutacyjny MW p = 0.00564 - w szumie.
- **K3**, e2e_ns p99 per przebieg: mediana C-B = -21.89 µs, rozrzut wewnątrz strony do 77.10 µs, permutacyjny MW p = 0.00564 - w szumie.

### uc06

Takt slotu (mediana odstępu deadline_ns): 2.000 ms.

| wielkość | B | C |
|---|---|---|
| przebiegi / podłączenia | 9 / 270 | 9 / 270 |
| K1': pary munmap+unlinkat kolejki (wszystkie) | 270 | 30 |
| K1': kill(pid_klienta, 0) / do puli (ESRCH → renameat) | 0 / 0 | 270 / 265 |
| K1': kolejki utworzone / oddane z puli | 270 / 0 | 48 / 222 |
| K1': pary w fazie pracy / przed nią / w ogonie (poza przepełnieniem) | - | 5 / 0 / 25 (0) |
| K1': przepełnienia puli / oczekiwane (utworzone - zwolnione bez puli - 2) | - | 25 / 25 |
| K1': wyłączenia: martwy muteks / klient niezebrany; inne zwolnienia bez puli | - | 5 / 0; 0 |
| wartości powrotu kill | - | -3 |
| rdzenie par munmap+unlinkat | 0, 1, 2 | 0, 1, 2 |
| okna K2 (R_B / R_C): liczba / w wątku RT | 270 / 0 | 240 / 0 |
| okno K2 [ms] p50 / max | 4.191 / 4.915 | 1.608 / 2.467 |
| okno przepełnienia [ms] p50 / max (liczba) | - / - (0) | 5.792 / 6.181 (25) |
| okna trafione w slot: n / odsetek | 270 / 100.0 % | 239 / 99.6 % |
| zdarzenie: max e2e [ms] p50 / p99 / max | 0.428 / 48.155 / 48.269 | 0.448 / 48.215 / 48.540 |
| pseudo-zdarzenie: liczba / max e2e [ms] p50 / p99 / max | 5400 / 0.392 / 48.417 / 49.977 | 4800 / 0.295 / 48.701 / 50.399 |
| Δ_e2e [µs]; MW p | 35.61; 7.96e-13 | 152.78; 1.61e-38 |
| okna z max e2e > takt: zdarzenia / pseudo | 7.8 % / 24.1 % | 10.9 % / 23.6 % |
| sloty obudzone w oknie: wake_lag / compute p50 [µs] (mediana po zdarzeniach) | 28.1 / 285.3 | 35.1 / 337.2 |
| kontrola e2e [ms] p50 / p99 / max | 0.307 / 46.585 / 49.977 | 0.295 / 46.783 / 50.399 |
| kontrola compute [ms] p50 / p99 / max | 0.234 / 0.469 / 49.798 | 0.233 / 0.475 / 50.224 |
| kontrola wake [ms] p50 / p99 / max | 0.024 / 44.628 / 48.046 | 0.024 / 44.830 / 48.496 |
| O1: futex wątku RT: wejścia / sloty z futex / sloty w serii | 669 / 348 / 353073 (0.099 %) | 791 / 371 / 349048 (0.106 %) |
| O1: futex na muteksie kolejki według op / poza kolejkami | WAIT 4, WAKE 6 / 659 | WAIT 9, WAKE 12 / 770 |
| O1: czekanie na muteks kolejki [ms] p50 / max; w oknie K2; slot > takt | 0.011 / 0.016; 0; 1 | 0.015 / 0.084; 0; 2 |
| O2: podłączenie, kolejka utworzona: liczba / okno p50 [ms] / trafione / max e2e p50 / max [ms] | 270 / 6.692 / 270 / 0.450 / 48.287 | 48 / 6.675 / 48 / 0.452 / 48.911 |
| O2: podłączenie, kolejka z puli: liczba / okno p50 [ms] / trafione / max e2e p50 / max [ms] | 0 / - / 0 / - / - | 222 / 0.052 / 70 / 46.496 / 48.525 |

- **K1'**: kontrola dodatnia B (270 zwolnień munmap+unlinkat na 270 podłączeń, kill klienta 0) powtórzona; C: do puli 265 z 270 (wyłączenia 5), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, spójność ogona tak. Werdykt: ZDANE.
- **K2**: kontrola dodatnia mocy B: n = 270, p = 7.96e-13 - spełniona; C: n = 239, p = 1.61e-38, Δ_e2e B = 35.61 µs, C = 152.78 µs. Werdykt C: NIEZDANE.
- K2 opisowo: u = Δ_e2e(C) / Δ_e2e(B) = 4.29 (95 % bootstrap 3.12..6.66).
- **K3**, compute_ns p50 per przebieg: mediana C-B = -1.54 µs, rozrzut wewnątrz strony do 4.26 µs, permutacyjny MW p = 0.0425 - w szumie.
- **K3**, wake_lag_ns p99 per przebieg: mediana C-B = 116.95 µs, rozrzut wewnątrz strony do 572.16 µs, permutacyjny MW p = 0.0939 - w szumie.
- **K3**, e2e_ns p99 per przebieg: mediana C-B = 119.32 µs, rozrzut wewnątrz strony do 573.12 µs, permutacyjny MW p = 0.0939 - w szumie.

### uc07

Takt slotu (mediana odstępu deadline_ns): 20.000 ms.

| wielkość | B | C |
|---|---|---|
| przebiegi / podłączenia | 9 / 270 | 9 / 270 |
| K1': pary munmap+unlinkat kolejki (wszystkie) | 270 | 27 |
| K1': kill(pid_klienta, 0) / do puli (ESRCH → renameat) | 0 / 0 | 270 / 270 |
| K1': kolejki utworzone / oddane z puli | 270 / 0 | 45 / 225 |
| K1': pary w fazie pracy / przed nią / w ogonie (poza przepełnieniem) | - | 0 / 0 / 27 (0) |
| K1': przepełnienia puli / oczekiwane (utworzone - zwolnione bez puli - 2) | - | 27 / 27 |
| K1': wyłączenia: martwy muteks / klient niezebrany; inne zwolnienia bez puli | - | 0 / 0; 0 |
| wartości powrotu kill | - | -3 |
| rdzenie par munmap+unlinkat | 0, 1, 2 | 0, 1, 2 |
| okna K2 (R_B / R_C): liczba / w wątku RT | 270 / 0 | 243 / 0 |
| okno K2 [ms] p50 / max | 0.658 / 0.856 | 0.377 / 0.605 |
| okno przepełnienia [ms] p50 / max (liczba) | - / - (0) | 1.031 / 1.157 (27) |
| okna trafione w slot: n / odsetek | 0 / 0.0 % | 0 / 0.0 % |
| zdarzenie: max e2e [ms] p50 / p99 / max | - / - / - | - / - / - |
| pseudo-zdarzenie: liczba / max e2e [ms] p50 / p99 / max | 5396 / 0.127 / 2.374 / 3.136 | 4761 / 0.112 / 2.388 / 2.939 |
| Δ_e2e [µs]; MW p | - | - |
| okna z max e2e > takt: zdarzenia / pseudo | - | - |
| sloty obudzone w oknie: wake_lag / compute p50 [µs] (mediana po zdarzeniach) | - | - |
| kontrola e2e [ms] p50 / p99 / max | 0.123 / 2.163 / 3.136 | 0.109 / 2.141 / 2.939 |
| kontrola compute [ms] p50 / p99 / max | 0.067 / 2.092 / 2.956 | 0.066 / 2.085 / 2.804 |
| kontrola wake [ms] p50 / p99 / max | 0.024 / 0.036 / 0.096 | 0.024 / 0.038 / 0.114 |
| O1: futex wątku RT: wejścia / sloty z futex / sloty w serii | 41 / 21 / 34661 (0.061 %) | 28 / 14 / 34745 (0.040 %) |
| O1: futex na muteksie kolejki według op / poza kolejkami | WAIT 1, WAKE 1 / 39 | 0 / 28 |
| O1: czekanie na muteks kolejki [ms] p50 / max; w oknie K2; slot > takt | 0.009 / 0.009; 0; 0 | brak |
| O2: podłączenie, kolejka utworzona: liczba / okno p50 [ms] / trafione / max e2e p50 / max [ms] | 270 / 1.023 / 12 / 0.209 / 0.395 | 45 / 1.023 / 0 / - / - |
| O2: podłączenie, kolejka z puli: liczba / okno p50 [ms] / trafione / max e2e p50 / max [ms] | 0 / - / 0 / - / - | 225 / 0.053 / 1 / 0.382 / 0.382 |

- **K1'**: kontrola dodatnia B (270 zwolnień munmap+unlinkat na 270 podłączeń, kill klienta 0) powtórzona; C: do puli 270 z 270 (wyłączenia 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, spójność ogona tak. Werdykt: ZDANE.
- **K2**: kontrola dodatnia mocy B: n = 0, p = nan - NIESPEŁNIONA; C: n = 0, p = nan, Δ_e2e B = nan µs, C = nan µs. Werdykt C: NIEROZSTRZYGNIĘTE (n = 0 < 100).
- K2 opisowo: u = Δ_e2e(C) / Δ_e2e(B) = nan (95 % bootstrap nan..nan).
- **K3**, compute_ns p50 per przebieg: mediana C-B = -1.19 µs, rozrzut wewnątrz strony do 2.54 µs, permutacyjny MW p = 0.0244 - w szumie.
- **K3**, wake_lag_ns p99 per przebieg: mediana C-B = 0.27 µs, rozrzut wewnątrz strony do 21.90 µs, permutacyjny MW p = 0.931 - w szumie.
- **K3**, e2e_ns p99 per przebieg: mediana C-B = -22.27 µs, rozrzut wewnątrz strony do 29.65 µs, permutacyjny MW p = 0.000494 - w szumie.

### uc08

Takt slotu (mediana odstępu deadline_ns): 100.000 ms.

| wielkość | B | C |
|---|---|---|
| przebiegi / podłączenia | 9 / 270 | 9 / 270 |
| K1': pary munmap+unlinkat kolejki (wszystkie) | 270 | 27 |
| K1': kill(pid_klienta, 0) / do puli (ESRCH → renameat) | 0 / 0 | 270 / 270 |
| K1': kolejki utworzone / oddane z puli | 270 / 0 | 45 / 225 |
| K1': pary w fazie pracy / przed nią / w ogonie (poza przepełnieniem) | - | 0 / 0 / 27 (0) |
| K1': przepełnienia puli / oczekiwane (utworzone - zwolnione bez puli - 2) | - | 27 / 27 |
| K1': wyłączenia: martwy muteks / klient niezebrany; inne zwolnienia bez puli | - | 0 / 0; 0 |
| wartości powrotu kill | - | -3 |
| rdzenie par munmap+unlinkat | 0, 1, 2 | 0, 1, 2 |
| okna K2 (R_B / R_C): liczba / w wątku RT | 270 / 0 | 243 / 0 |
| okno K2 [ms] p50 / max | 0.337 / 0.440 | 0.278 / 0.533 |
| okno przepełnienia [ms] p50 / max (liczba) | - / - (0) | 0.579 / 0.646 (27) |
| okna trafione w slot: n / odsetek | 0 / 0.0 % | 0 / 0.0 % |
| zdarzenie: max e2e [ms] p50 / p99 / max | - / - / - | - / - / - |
| pseudo-zdarzenie: liczba / max e2e [ms] p50 / p99 / max | 2269 / 0.353 / 1.350 / 1.666 | 1884 / 0.341 / 1.293 / 1.495 |
| Δ_e2e [µs]; MW p | - | - |
| okna z max e2e > takt: zdarzenia / pseudo | - | - |
| sloty obudzone w oknie: wake_lag / compute p50 [µs] (mediana po zdarzeniach) | - | - |
| kontrola e2e [ms] p50 / p99 / max | 0.338 / 1.297 / 1.666 | 0.325 / 1.276 / 1.506 |
| kontrola compute [ms] p50 / p99 / max | 0.274 / 1.216 / 1.551 | 0.274 / 1.209 / 1.394 |
| kontrola wake [ms] p50 / p99 / max | 0.025 / 0.037 / 0.080 | 0.025 / 0.036 / 0.072 |
| O1: futex wątku RT: wejścia / sloty z futex / sloty w serii | 12 / 10 / 8459 (0.118 %) | 21 / 11 / 8515 (0.129 %) |
| O1: futex na muteksie kolejki według op / poza kolejkami | WAKE 3 / 9 | WAKE 2 / 19 |
| O1: czekanie na muteks kolejki [ms] p50 / max; w oknie K2; slot > takt | brak | brak |
| O2: podłączenie, kolejka utworzona: liczba / okno p50 [ms] / trafione / max e2e p50 / max [ms] | 270 / 0.482 / 1 / 1.342 / 1.342 | 45 / 0.515 / 0 / - / - |
| O2: podłączenie, kolejka z puli: liczba / okno p50 [ms] / trafione / max e2e p50 / max [ms] | 0 / - / 0 / - / - | 225 / 0.053 / 1 / 0.428 / 0.428 |

- **K1'**: kontrola dodatnia B (270 zwolnień munmap+unlinkat na 270 podłączeń, kill klienta 0) powtórzona; C: do puli 270 z 270 (wyłączenia 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, spójność ogona tak. Werdykt: ZDANE.
- **K2**: kontrola dodatnia mocy B: n = 0, p = nan - NIESPEŁNIONA; C: n = 0, p = nan, Δ_e2e B = nan µs, C = nan µs. Werdykt C: NIEROZSTRZYGNIĘTE (n = 0 < 100).
- K2 opisowo: u = Δ_e2e(C) / Δ_e2e(B) = nan (95 % bootstrap nan..nan).
- **K3**, compute_ns p50 per przebieg: mediana C-B = -0.20 µs, rozrzut wewnątrz strony do 7.02 µs, permutacyjny MW p = 0.73 - w szumie.
- **K3**, wake_lag_ns p99 per przebieg: mediana C-B = -1.60 µs, rozrzut wewnątrz strony do 17.03 µs, permutacyjny MW p = 0.489 - w szumie.
- **K3**, e2e_ns p99 per przebieg: mediana C-B = -22.19 µs, rozrzut wewnątrz strony do 74.52 µs, permutacyjny MW p = 0.00399 - w szumie.


