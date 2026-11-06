# R603D - pomiar potwierdzający drenaż w porcjach (C') wobec drenażu jednym ciągiem (C) (pi400, `--realtime`)

Zgłoszenie: michalwidera/retractordb#603. Drenaż w porcjach w `a33b584c`, scalony do `master` przez #605 (`e0857dc8`). Ten plik zapisano PRZED pomiarem i przed budową aparatury; po zatwierdzeniu przez człowieka zmiany protokołu trafiają do sekcji *Aneksy* z datą i powodem, nie do treści powyżej.

Protokół zatwierdzony przez człowieka 2026-11-05 wraz z decyzjami D1-D3 według rekomendacji (sekcja *Decyzje*), przed budową aparatury i przed jakimkolwiek pomiarem.

Aparatura pochodzi z R603C (`results_20261105_R603C/`, protokół `add5aae`, aparatura `2f34d77`, wynik `a58d2c3`, scalenie do `main` `8ee5d59`), BEZ łatki P2 z R603. Opis aparatury, który się nie zmienił, jest w README R603C i R600; poniżej są tylko różnice i nowe kryteria.

## Pytanie

R603C pokazało, że pula kolejek (naprawa (a)) usuwa z czasu pracy `munmap` + `unlinkat` (K1' zdane), ale drenaż porzuconej kolejki jednym ciągiem (D1a: w uc05 ~8000 komunikatów w ~2,4 ms) wydłuża liczenie slotów obudzonych w jego trakcie tak samo jak zwolnienie albo bardziej (K2 niezdane w uc05 i uc06; rośnie `compute_ns`, nie `wake_lag_ns`). Decyzja człowieka 2026-11-05: drenaż w porcjach (D1c), D1 = `kResponseQueueDrainBatch` 256, D2 = bez wyrównania fazy do slotu. Pierwsza porcja idzie jeszcze pod nazwą klienta, reszta po jednej w każdym obrocie wątku komunikacyjnego (co ~1 ms), a kolejka staje się gotowa do ponownego użycia dopiero po opróżnieniu. Pytania:

1. Czy porcja wydłuża slot, z którym się nakłada, o mniej niż ustalony próg (K2a), i czy zwiększa odsetek slotów dłuższych od taktu o mniej niż ustalony próg (K2b)?
2. Czy pula nadal działa: porzucenia trafiają do puli, wpis gotowy dostaje następny klient, a drenaż kończy się przed następnym podłączeniem (K1')?
3. Czy poza oknami nic się nie pogorszyło (K3)?

## Strony porównania

| Strona | Rewizja silnika | Co robi wątek komunikacyjny z porzuconą kolejką martwego klienta |
|---|---|---|
| C | `92faf6896cad8d55ad8afbe35918f44218850758` | `kill(pid, 0)` = -ESRCH, drenaż całej kolejki `try_receive`, `renameat` pod nazwę puli (R603C, strona C) |
| C' (`Cp`) | `e0857dc8ba5387929c0e79d172cb8c45a669e3a3` | `kill(pid, 0)` = -ESRCH, porcja 256 komunikatów, `renameat` pod nazwę puli jako wpis niegotowy, potem jedna porcja w każdym obrocie aż do opróżnienia |

- **C' = `e0857dc8`**: scalenie #605. Drzewo `d1aa1bd2...` jest identyczne z drzewem `a33b584c`, a pierwszym rodzicem jest C. Różnica C → C' to dokładnie drenaż w porcjach: `constants.hpp`, `ipcServer.cpp`, `ipcServer.hpp`, `test_ipcServer.cpp`. `src/qry` bez zmian.
- **C** jest kontrolą dodatnią K2 (R603C: K2 niezdane w uc05 i uc06) i stroną odniesienia K3.
- Obie strony mają łatkę P1 (`deadline_ns`); `src/rdb/lib/probe.cc` jest w `92faf689` i `e0857dc8` identyczny.

## Ustalenia przed pomiarem (2026-11-05, z kodu i z surowych danych R603C)

1. **Pojemność kolejki i liczba porcji.** Długość `mmap` kolejki odpowiedzi w śladzie R603C wynosi 216 + 1048 · N bajtów: N = 2000 (uc03), 8000 (uc05), 5000 (uc06), 500 (uc07), 100 (uc08). Kolejka jest przy porzuceniu pełna (R603C, *Granice wniosków*), więc po pierwszej porcji zostaje k = ⌈(N - 256) / 256⌉ obrotów drenażu: **uc03 7, uc05 31, uc06 19, uc07 1, uc08 0**. Ostatnia porcja jest niepełna: 208, 64, 136, 244 komunikatów. W uc08 C' opróżnia kolejkę już w pierwszej porcji, więc zachowuje się jak C z kolejką 100 komunikatów.
2. **Obrót wątku komunikacyjnego** (`commandLoop`): `try_receive` kolejki komend (bez wywołania systemowego bez rywalizacji), obsługa komend, `releaseAbandonedQueues()` (na początku `drainPooledStep()`: jedna porcja najstarszego wpisu niegotowego), potem `std::this_thread::sleep_for(1 ms)`, czyli w glibc `clock_nanosleep`. Silnik ma dokładnie dwa wątki (R603C, `rt.txt`): wątek slotu `SCHED_FIFO` na rdzeniu 3 i wątek komunikacyjny na rdzeniach 0-2. Ślad `clock_nanosleep` (i dla pewności `nanosleep`) z filtrem „poza wątkiem RT”, takim jak dla `openat`, obejmuje więc wyłącznie wątek komunikacyjny. Tracepointy `sys_{enter,exit}_{clock_nanosleep,nanosleep}` istnieją na workerze.
3. **Porcja nie ma własnego wywołania systemowego**, więc widać ją tylko jako obrót: odstęp od wyjścia z `clock_nanosleep` do następnego wejścia w `clock_nanosleep` tego wątku. Pierwsza porcja leży w oknie R_C (od `kill` do `renameat`), tak jak cały drenaż w C.
4. **Miara K2 R603C nie nadaje się do okien porcji.** Sprawdzone na surowych danych R603C (strona C jako tło, okna syntetyczne o długości 75 µs, co ~1,07 ms, pierwsze 0,04-1,1 ms po końcu slotu; skrypt `k2_resolution.py`, ziarno 6034):
   - pseudo-okna o jednostajnej fazie (R600, R603C) mają inną fazę względem slotu niż okna porcji, a czasy slotów są wielomodalne (okresowe sloty 2,9 ms w uc03, 0,3-1,2 ms w uc05, 48 ms w uc06). Różnica median wychodzi przez to pod H0 obciążona o -0,2 do -730 µs albo niestabilna (półszerokość przedziału do 24 ms w uc06);
   - czas slotu ma okres w numerze slotu (`iter mod H`): najmniejsza mediana |`compute`(k) - `compute`(k - h)| przy **H = 8 (uc03), 40 (uc05), 5 (uc06), 10 (uc07), 12 (uc08)**. Terminy slotów są ściśle okresowe, więc przesunięcie serii okien o m · H · takt zachowuje i fazę, i klasę każdego slotu;
   - miara klasowa z tłem placebo (definicje w *Kryteriach*, K2) daje wyniki z tabeli niżej. Pod H0 K2a ma obciążenie |Δ| ≤ 0,26 µs i półszerokość przedziału ≤ 0,33 µs, a na prawdziwych oknach R603C wykrywa obie strony z dużym zapasem. K2b ma moc tylko w uc05: w uc06 sloty obudzone na czas liczą ~0,23 ms przy takcie 2 ms i nawet drenaż C (+94 µs) nie przepycha ich ponad takt.

| rodzina | seria | slotów narażonych / serii | K2a Δ compute [µs] (95 % bootstrap) | K2b Δ odsetka > takt [pp] (95 % bootstrap) |
|---|---|---|---|---|
| uc03 | R603C B, okna R_B | 34 / 270 | +34,99 (+29,77..+40,82) | 0,00 |
| uc03 | R603C C, okna R_C | 0 / 243 | - | - |
| uc03 | H0, serie porcji | 80 / 242 | -0,17 (-0,50..+0,16) | 0,00 |
| uc05 | R603C B | 1760 / 270 | +11,09 (+10,39..+11,85) | +2,70 (+1,94..+3,47) |
| uc05 | R603C C | 599 / 243 | +47,26 (+39,72..+52,13) | +3,94 (+2,55..+5,33) |
| uc05 | H0, serie porcji | 1440 / 230 | +0,06 (-0,06..+0,18) | +0,93 (-0,75..+2,65) |
| uc06 | R603C B | 716 / 270 | +28,38 (+25,61..+31,61) | -0,26 (-0,97..+0,57) |
| uc06 | R603C C | 330 / 240 | +94,07 (+77,74..+100,42) | +0,11 (-1,16..+1,90) |
| uc06 | H0, serie porcji | 893 / 229 | -0,26 (-0,46..-0,11) | -0,47 (-1,02..+0,19) |
| uc07, uc08 | wszystkie | 0 | - | - |

5. **Faza pierwszej porcji.** W R603C okno startuje 0,04-1,1 ms po końcu slotu (wątek komunikacyjny rozpoznaje porzucenie zaraz po rozesłaniu wyniku). Kolejne porcje przesuwają się względem terminu o różnicę między obrotem (~1,07 ms) a taktem: w uc05 o ~70 µs na obrót, więc 31 porcji obiega całą fazę slotu; w uc07 (20 ms) obie porcje mieszczą się w przerwie po slocie, w uc08 jest tylko pierwsza.
6. **Korpus** jest na workerze w `/dev/shm/r376/data` (uptime 6 h 27 min w chwili sprawdzenia, bez restartu od odtworzenia w R603C). Przed kampanią: skróty SHA-256 drzew rodzin wobec wartości z README R603C (*Suchy przebieg*, punkt 2); przy niezgodności odtworzenie procedurą R600.
7. **Binarka C** z R603C zostaje: `~/R376/bin/R603C_C`, `xretractor` `3458ed99...`, `xqry` `a7b7dcbd...` (te same sumy co w `meta.json` przebiegów R603C). Budowana jest tylko strona C'.

## Aparatura - różnice wobec R603C

1. **`build_ab.sh`**: tylko C' (`e0857dc8` + P1), przyrostowo w `~/R376/src` po C, binarki do `~/R376/bin/R603D_Cp`. `setcap cap_ipc_lock,cap_sys_nice=ep` jak w R603C. Suma binarki C sprawdzana przed kampanią wobec `~/R376/bin/R603C_C.sha256`.
2. **Śledzone wywołania** (`run_one.py`, `SYSCALLS`): do listy R603C dochodzą `clock_nanosleep` i `nanosleep` poza wątkiem RT (filtr jak `openat`). Ślad jest jednakowy w C i C'. Koszt dotyczy tylko wątku komunikacyjnego (dwa zdarzenia na obrót, ~2000/s); wątek slotu nie dostaje nowych zdarzeń. Przepełnienie bufora ftrace unieważnia przebieg (`trace_overrun`, aneks 1 R603C).
3. **Strony** `C` i `Cp` w `run_one.py` i `campaign.sh` (`BIN_PREFIX` per strona: `R603C_C`, `R603D_Cp`). Katalogi: surowe dane `~/R376/raw_R603D`, aparatura `~/R376/apparatus_R603D`, suchy przebieg `~/R376/dry_R603D`.
4. **Bez zmian wobec R603C**: rodziny uc03, uc05, uc06, uc07, uc08; 9 par na rodzinę w kolejności ABBA (para nieparzysta C, C'; parzysta C', C); 30 podłączeń z przerwami z [2 s, 3 s]; SIGINT po pierwszym wierszu; `taskset -c 3`, `-k -r -t`, governor `performance`, `trace_clock=mono`, 12 s ogona; unieważnienie przebiegu bez wątku `SCHED_FIFO`, przy `VmLck = 0`, przy różnicy binarki uruchomionej i zbudowanej i przy `trace_overrun` ≠ 0.
5. **`analyze.py`**: parser R603C bez zmian (okna R_C, przepełnienia, pary, oddania z puli, O1, O2) + obroty wątku komunikacyjnego, serie porcji, miara klasowa K2 z placebo, model stanu puli (K1'), O3-O5.
6. **Archiwum** surowych danych: jak R603C, w prywatnym `paper-arXiv`, `rdb-experiment-embargo/R603D/`. Ślad obrotów zwiększa `trace.txt` (oszacowanie w suchym przebiegu); jeśli archiwum przekroczy 95 MB, dzielone jest na części po rodzinach (limit GitHub 100 MB), każda z własnym indeksem.

## Okna i zdarzenia

- **Obrót** wątku komunikacyjnego = [wyjście z `clock_nanosleep`, następne wejście w `clock_nanosleep`] w wątku, który robi `kill(pid_klienta, 0)`. **Obrót bezczynny**: obrót poza seriami drenażu, poza oknami R_C i poza podłączeniami klientów.
- **Seria drenażu** jednego porzucenia w C':
  - **P0** = okno R_C z R603C: [wyjście z `kill(pid_klienta, 0)` = -ESRCH, wyjście z `renameat` = 0]. Obejmuje pierwszą porcję i `renameat` pod nazwę puli. Okno z parą `munmap` + `unlinkat` przed `renameat` to nadal okno przepełnienia; cała jego seria (P0..Pk) jest wtedy **serią przepełnienia**, raportowaną osobno i wyłączoną z K2, tak jak w R603C wyłączono okna przepełnienia (w tej aparaturze leżą tylko w ogonie, ~3 na przebieg).
  - **P1..Pk** = k kolejnych obrotów po obrocie, w którym leży P0, z k z *Ustaleń*, punkt 1 (uc03 7, uc05 31, uc06 19, uc07 1, uc08 0).
  - **Koniec serii** = koniec Pk; od tej chwili wpis jest gotowy.
  - Seria, w której jeden z obrotów P1..Pk obejmuje obsługę podłączenia (wejście `openat`/`mmap`/`renameat` oddania z puli) albo P0 innego porzucenia, jest **seria zakłócona**: raportowana osobno i wyłączona z K2.
- **Seria w C** = samo P0 (okno R_C), jak w R603C.
- **Klasa slotu** = `iter mod H` z H z *Ustaleń*, punkt 4. **Mediana klasy** = mediana `compute_ns` slotów kontrolnych tej klasy w tym przebiegu.
- **Slot narażony na okno** = slot, którego przedział [`deadline_ns` + `wake_lag_ns`, ten sam początek + mediana klasy] przecina okno. Przedział nie zależy od zrealizowanego `compute_ns` tego slotu, więc dłuższy slot nie jest częściej narażony (brak obciążenia długością). Skutek uboczny: porcja, która trafia tylko w wydłużony ogon slotu, nie liczy się jako narażenie (miara zachowawcza). Slot narażony przez kilka okien serii liczy się raz.
- **Odchylenie slotu** = `compute_ns` - mediana klasy.
- **Placebo serii** = 20 kopii całej serii okien przesuniętych o m · H · takt (m losowe ≠ 0), w których wszystkie sloty narażone są kontrolne. Ziarno 6034 (osobne od 600, 601, 603, 6031).
- **Sloty kontrolne** (K3, mediany klas, placebo): jak w R603C, dalej niż 0,5 s od każdego klienta, każdego okna R_C, każdej pary `munmap` + `unlinkat` i każdej serii drenażu (od P0 do końca Pk), wewnątrz serii podłączeń ± 2 s.

## Przewidywanie przed pomiarem

| rodzina | takt | P1..Pk | seria drenażu C' (≈ k · 1,07 ms) | P0 w C (R603C, p50) |
|---|---|---|---|---|
| uc03 | 5 ms | 7 | ~7,5 ms | 0,79 ms |
| uc05 | 1 ms | 31 | ~33 ms | 2,38 ms |
| uc06 | 2 ms | 19 | ~20 ms | 1,61 ms |
| uc07 | 20 ms | 1 | ~1,1 ms | 0,38 ms |
| uc08 | 100 ms | 0 | (tylko P0) | 0,28 ms |

1. **Porcja trwa ~75 µs** (R603C: 8000 komunikatów w ~2,4 ms, ~0,3 µs na komunikat), obrót bezczynny kilka µs. Pełne porcje dają się więc odróżnić od obrotów bezczynnych po długości (sprawdza suchy przebieg, bramka G2).
2. **K1': ZDANE we wszystkich rodzinach.** C' zmienia tylko drenaż. Seria trwa najwyżej ~33 ms, a następne podłączenie przychodzi po 2-3 s, więc wpis jest gotowy przed każdym podłączeniem, a liczba kolejek utworzonych i oddanych z puli jest taka jak w C (5-6 i 24-25 na przebieg). Martwy muteks wychodzi w P0, tak jak w C (R603C: 1,9 % porzuceń w uc06).
3. **K2a: raczej NIEZDANE w uc05 i uc06, z Δ mniejszym niż w C.** Porcja czyta ~256 KiB pamięci dzielonej (plus zapis nagłówków), czyli mniej niż wspólne L2 (1 MiB), więc na mikrosekundę nałożenia powinna wypierać mniej zbioru roboczego slotu niż strumień 5-8 MiB w C. Porcja trwa jednak tyle, ile typowy slot uc05 liczy (mediana `compute` ~66 µs), więc slot narażony nakłada się z nią na znacznej części liczenia. Spodziewane Δ: uc05 +5..+25 µs (C: +47 µs), uc06 +10..+50 µs (C: +94 µs), czyli bliżej progu, ale nad nim. uc03: n ≈ 80 narażonych slotów (symulacja H0), więc raczej NIEROZSTRZYGNIĘTE (n < 100); uc07 i uc08: n ≈ 0, NIEROZSTRZYGNIĘTE.
4. **K2b: w uc05 raczej NIEROZSTRZYGNIĘTE** (półszerokość przedziału pod H0 ~1,7 pp przy progu 2 pp), w pozostałych rodzinach bez mocy (opisowo).
5. **Koszt łączny na porzucenie (O4) może nie spaść.** Bez wyrównania fazy (D2) porcje obiegają fazę slotu: w symulacji H0 seria uc05 naraża ~6 slotów, a P0 w C ~2,5. Suma odchyleń na porzucenie może więc w C' być podobna do C, mimo mniejszego Δ na slot. Jeśli tak wyjdzie, kolejnym krokiem jest wyrównanie porcji do przerwy po slocie (alternatywa D2 z planu), a nie mniejsza porcja.
6. **K3: bez regresji.** Obroty bezczynne C' różnią się od C tylko wyszukaniem wpisu niegotowego w puli (2 wpisy).

## Kryteria (ustalone przed pomiarem)

Dla każdej rodziny i strony, sumarycznie po 9 przebiegach. Progi i przedziały ustalono na danych R603C (*Ustalenia*, punkt 4), przed jakimkolwiek przebiegiem C'.

### K1' - pula bez regresji (C')

- **Kontrola dodatnia (obie strony)**: w każdym przebiegu co najmniej jedno okno przepełnienia w ogonie z parą `munmap` + `unlinkat` (ślad widzi pary). Brak unieważnia K1' w tej rodzinie.
- **Do puli**: każde porzucenie z `kill` = -ESRCH kończy się `renameat` = 0 albo wyłączeniem martwego muteksu (reguła R603C: para `munmap` + `unlinkat` po `kill` = -ESRCH, zaczęta wcześniej niż 9,5 s po pierwszym wierszu klienta). Wymagane: liczba do puli = porzucenia - wyłączenia.
- **Zero niewyjaśnionych par w fazie pracy** (faza pracy jak w R603C). W C' dotyczy to także zwolnienia wpisu niegotowego (`drainPooledStep`: błąd odbioru albo wyczerpany budżet), które w śladzie jest parą `munmap` + `unlinkat` bez `kill` przed nią: każda taka para w fazie pracy = NIEZDANE.
- **Gotowość przed podłączeniem**: (a) każda seria drenażu kończy się przed startem następnego klienta; (b) model stanu puli ze śladu (wejście = koniec serii, wyjście = oddanie z puli, przepełnienie zwalnia najstarszy wpis, pojemność 2) nie ma ani jednego podłączenia, które utworzyło kolejkę (`mmap`), choć pula miała wpis gotowy, ani oddania z puli bez wpisu gotowego.
- **Spójność ogona**: przepełnienia = N_utw - skasowane - 2 w każdym przebiegu (jak R603C).
- **Werdykt C'**: **ZDANE**, gdy wszystkie powyższe są spełnione. **NIEZDANE** przy choćby jednej niewyjaśnionej parze w fazie pracy, porzuceniu bez puli bez wyłączenia albo naruszeniu gotowości. **NIEROZSTRZYGNIĘTE (aparatura)**, gdy wyłączenia obejmą więcej niż 5 % porzuceń rodziny albo kontrola dodatnia zawiedzie. Strona C dostaje ten sam werdykt opisowo (powtórzenie R603C).

### K2 - wpływ porcji na slot (miara klasowa z tłem placebo)

Okna: w C' P0..Pk niezakłóconych serii, w C okna R_C bez przepełnień. Klaster = seria (jedno porzucenie) razem z jej 20 kopiami placebo. Przedział: 95 % percentylowy bootstrap po klastrach, 2000 losowań, ziarno 6034. Klastry, a nie okna: okien w C' będzie ~30 razy więcej, ale okna jednej serii nie są niezależne, więc sama liczba okien nie zwęża przedziału.

- **K2a (wydłużenie liczenia)**: Δ_c = mediana odchyleń slotów narażonych w seriach - mediana odchyleń slotów narażonych w ich placebo. **Próg δ_c = 5 µs.** Uzasadnienie: połowa najmniejszego efektu, który poprzednie warianty dały w tej mierze i który uznano za niezdany (B uc05 +11,1 µs), ponad 15 razy więcej niż półszerokość przedziału pod H0 (≤ 0,33 µs), 0,5 % taktu uc05.
- **K2b (przekroczenie taktu)**: Δ_m = odsetek slotów z `e2e_ns` > takt wśród slotów narażonych obudzonych na czas (`wake_lag_ns` < takt/2) - to samo w placebo. Sloty obudzone z opóźnieniem są pominięte, bo ich przekroczenie przesądza zaległość sprzed okna (uc06: zaległość po okresowym slocie 48 ms). **Próg δ_m = 2 punkty procentowe.** Uzasadnienie: poniżej efektu C w uc05 (+3,9 pp, dolna granica +2,6) i B (+2,7 pp). Werdykt K2b liczony tylko w rodzinach, w których kontrola dodatnia C ma dolną granicę Δ_m > δ_m; w pozostałych K2b jest opisowe (z danych R603C wynika, że tylko uc05).
- **Liczność**: werdykt wymaga ≥ 100 slotów narażonych i ≥ 50 serii z narażeniem; inaczej NIEROZSTRZYGNIĘTE (n podane).
- **Ważność miary** (w danych R603D):
  - kontrola dodatnia C: dolna granica Δ_c > δ_c w uc05 i w uc06. Niespełniona = K2a NIEROZSTRZYGNIĘTE (miara) we wszystkich rodzinach;
  - kontrola H0: `k2_resolution.py` na tle strony C tej kampanii (syntetyczne serie porcji o fazie i długościach z C'); przedział Δ_c pod H0 musi leżeć w ±1 µs (δ_c / 5). Niespełniona w rodzinie = K2a NIEROZSTRZYGNIĘTE (miara) w tej rodzinie.
- **Werdykt (osobno K2a i K2b, dla C')**: **ZDANE**, gdy górna granica przedziału < próg; **NIEZDANE**, gdy dolna granica > próg; **NIEROZSTRZYGNIĘTE**, gdy przedział zawiera próg. Ta sama reguła dla C opisowo (oczekiwane NIEZDANE K2a w uc05 i uc06).
- **Opisowo**: u' = Δ_c(C') / Δ_c(C) z przedziałem bootstrap; Δ_e2e i jednostronny Mann-Whitney w postaci R603C (max `e2e_ns` okna wobec pseudo-okien R600), z zaznaczeniem, że przy ~30 razy większej liczbie okien p nie jest kryterium; osobno P0 i P1..Pk; serie zakłócone i okna przepełnienia osobno.

### K3 - bez regresji poza oknami

Jak R603C (C' wobec C): sloty kontrolne, per przebieg `compute_ns` p50, `wake_lag_ns` p99, `e2e_ns` p99; różnica median C' - C wobec rozrzutu wewnątrz strony i dokładny permutacyjny MW 9 vs 9. Różnica dodatnia i większa od rozrzutu = **regresja C', osobne znalezisko**.

### Obserwacje (bez kryterium)

- **O1** - `futex` wątku slotu na muteksie kolejki odpowiedzi, jak w R603C.
- **O2** - zdarzenie podłączenia (kolejka utworzona / z puli), jak w R603C.
- **O3** - długość P0, pełnych porcji, ostatniej porcji, obrotów bezczynnych (p50, p99, max), okres obrotu, czas całej serii; faza P0 względem końca slotu.
- **O4** - koszt łączny na porzucenie: liczba slotów narażonych na serię i suma odchyleń slotów narażonych na serię minus to samo w placebo, C' wobec C, z przedziałem bootstrap. To ta miara pokazuje, czy rozłożenie drenażu na ~30 obrotów zmniejsza wpływ na sloty w ogóle, czy tylko rozprasza go na więcej slotów (*Przewidywanie*, punkt 5).
- **O5** - liczba serii zakłóconych i powód.

## Kolejność

1. Zatwierdzenie tego protokołu przez człowieka, commit i push gałęzi `experiment/20261105_R603D`.
2. Aparatura: `build_ab.sh` (tylko C'), `run_one.py` (strony C / Cp, `clock_nanosleep`, `nanosleep`), `campaign.sh`, `analyze.py` (punkt 5 *Aparatury*). Test parsera: `analyze.py` na surowych danych R603C strony C musi dać okna R_C, liczniki K1' i O1/O2 identyczne z `results_20261105_R603C/wynik.md` (różnica = błąd parsera), a K2 klasowe identyczne z tabelą w *Ustaleniach*, punkt 4.
3. Budowa C', sprawdzenie korpusu i binarki C, suchy przebieg: uc05 i uc03, po 1 przebiegu C i C' z 10 podłączeniami (`~/R376/dry_R603D`). Dane suchego przebiegu nie wchodzą do wyniku. **Bramki** (każda niespełniona = decyzja człowieka przed kampanią):
   - **G1**: obroty widoczne: `clock_nanosleep` albo `nanosleep` wątku komunikacyjnego ~1 na ms przez cały przebieg, `trace_overrun` = 0;
   - **G2**: serie wyznaczalne: w każdej niezakłóconej serii C' każda pełna porcja P1..Pk-1 jest dłuższa niż p99,9 obrotów bezczynnych tego przebiegu, a obrót Pk+1 nie jest dłuższy niż p99 obrotów bezczynnych (drenaż skończył się w przewidzianym obrocie). Raport: długości porcji i obrotów bezczynnych, liczba serii spełniających oba warunki;
   - **G3**: K1' rozpoznawalne w C' (liczniki do puli, z puli, N_utw, model stanu puli, spójność ogona);
   - **G4**: bramka `futex` z R603C (wątek slotu woła `futex` w ≤ 1 % slotów);
   - **G5**: oszacowanie rozmiaru `trace.txt` na przebieg i archiwum całej kampanii;
   - **H**: H z *Ustaleń*, punkt 4 nadal najmniejsza mediana |Δ compute| w danych suchego przebiegu.
4. Kampania: 5 rodzin × 9 par = 90 przebiegów, ~2,5 h, odczepiona (`setsid nohup`).
5. `wynik.md`, surowe archiwum w `paper-arXiv/rdb-experiment-embargo/R603D/` (wiersz w obu tabelach README), tutaj tylko indeks sum; komentarz w #603.

## Decyzje (zatwierdzone przez człowieka 2026-11-05: D1 dwa werdykty K2a i K2b, D2 δ_c = 5 µs, D3 binarka C z R603C)

- **D1 - postać K2.** Rekomendacja: K2a i K2b jako dwa osobne werdykty z progami jak wyżej, K2b tylko tam, gdzie kontrola dodatnia C ma moc (z R603C wynika: uc05). Alternatywa: K2a jako jedyne kryterium, K2b opisowo; prostsze, ale przekroczenie taktu (to, co liczy się dla czasu rzeczywistego) nie miałoby wtedy werdyktu nawet w uc05.
- **D2 - próg δ_c.** Rekomendacja 5 µs (uzasadnienie w K2a). Alternatywy: 3 µs (ostrzej; przy rozdzielczości ≤ 0,33 µs nadal rozstrzygalne) albo 10 µs (łagodniej, ale tuż pod efektem B uc05 11,1 µs, który uznano za niezdany).
- **D3 - binarka C.** Rekomendacja: ponownie binarka z R603C (sumy w *Ustaleniach*, punkt 7), bez przebudowy: C jest wtedy bit w bit stroną C R603C, a budowa tylko C' oszczędza ~20 min. Alternatywa: przebudowa C razem z C' w jednym przebiegu `build_ab.sh`.

## Embargo

Korpus `uc01`..`uc08` jest objęty embargiem do publikacji DEBS. W tym katalogu i w komentarzach do zgłoszeń: wyłącznie identyfikatory rodzin i liczby z nich wyprowadzone (pojemności kolejek, H, liczby slotów, czasy). Plany, dane, generatory i nazwy strumieni zostają na workerze w `/dev/shm/r376` i w prywatnym `paper-arXiv`. Surowe CSV i ślady ftrace poza git; zostaje indeks sum. `k2_resolution.py` czyta surowe dane R603C z prywatnego archiwum i wypisuje tylko liczby wyprowadzone.

## Aneksy

Aneksy 1 i 2 przejrzane i zatwierdzone przez człowieka 2026-11-06, w trakcie kampanii, przed analizą jej danych.

1. **2026-11-06, bramka H - postać operacyjna (zapisana przed suchym przebiegiem, przed obejrzeniem jego danych).** Dosłowne „H nadal najmniejszą medianą |Δ compute|” nie zachodzi nawet na danych R603C, z których H wyznaczono: najmniejsza mediana |`compute`(i) - `compute`(i - h)| po h = 1..64, liczona razem po 9 przebiegach strony C, wypada przy h = 8 (uc03), 20 (uc05; przy 40 ta sama 0,481 µs), 5 (uc06), 10 (uc07; strona B 5), 6 (uc08; przy 12 o 0,19 µs, czyli 1,5 %, więcej). Każde H z *Ustaleń*, punkt 4, jest wielokrotnością tego argminu, więc klasa `iter mod H` rozdrabnia okres i przesunięcie placebo o m · H · takt dalej zachowuje fazę i klasę. Bramka H w `analyze.py --gates`: dla każdej strony suchego przebiegu argmin h* po h = 1..2H (wszystkie sloty strony razem) dzieli H, a mediana przy H jest najwyżej 5 % nad medianą przy h*. Wydruk podaje też dosłowny argmin (`argmin = H` albo `≠ H`). Kryteria K1'-K3 bez zmian.
2. **2026-11-06, bufor ftrace 65 536 kB na rdzeń zamiast 16 384 kB (`run_one.py`).** Ślad obrotów dodaje ~2000 zdarzeń/s jednego wątku na rdzeniach 0-2, czyli przy ~100 s przebiegu ~10 MB w buforze jednego rdzenia, blisko starego limitu. Przepełnienie nadal unieważnia przebieg (`trace_overrun` ≠ 0); bramka G1 to sprawdza. Na workerze to 256 MB z 3,7 GB RAM. Jednakowo w C i C'.

## Stan

Protokół zapisany przed pomiarem i przed budową aparatury, zatwierdzony 2026-11-05 (D1-D3 według rekomendacji). Następny krok: *Kolejność*, punkt 2 (aparatura i test parsera).

2026-11-06, *Kolejność*, punkt 2: aparatura w tym katalogu - `build_ab.sh` (tylko C'), `run_one.py` (strony C i Cp, `clock_nanosleep` i `nanosleep` poza wątkiem RT, aneks 2), `campaign.sh` (sprawdza sumy binarek C i C' przed startem), `analyze.py` (parser R603C importowany bez zmian z `../results_20261105_R603C/analyze.py`; obroty, serie P0..Pk, K2 klasowe z placebo, model stanu puli, O3-O5; tryby `--gates` i `--parser-check`), `P1_deadline_ns.patch` (kopia z R603C, bez zmian). **Test parsera zdany** na surowych danych R603C (archiwum `ab8fbc51...`, suma zgodna): `analyze.py --parser-check --raw <R603C>/raw` daje wydruk parsera R603C identyczny z częścią *Wydruk analizy* w `results_20261105_R603C/wynik.md` (199 wierszy, 0 różnic: okna R_C, liczniki K1', O1, O2); serie R603D strony C równe oknom R_C (243 / 243 / 240 / 243 / 243), model stanu puli bez naruszeń, pojemności kolejek z `mmap` 2000 / 8000 / 5000 / 500 / 100, czyli k = 7 / 31 / 19 / 1 / 0; K2 klasowe (B, C, H0) co do cyfry równe tabeli z *Ustaleń*, punkt 4.

## Suchy przebieg

2026-11-06 07:56-07:59, po zapisaniu aparatury (`c39b31d`): uc05 i uc03, po 1 przebiegu C i C' z 10 podłączeniami (`~/R376/dry_R603D`, `R603D_PAIRS=1 R603D_CONNS=10`). Dane suchego przebiegu nie wchodzą do wyniku; z raportu pełnego na tych danych sprawdzono tylko, że przechodzi bez błędu (wartości K2 nieoglądane). Ustalenia, bez zmiany kryteriów:

1. **Worker po restarcie** (uptime 5 min o 07:33), więc `/dev/shm/r376` zniknęło. Korpus uc03, uc05-uc08 odtworzony procedurą R600 (`paper-arXiv` HEAD `5925540`, ostatnia zmiana `usecases` w `7a76922`). Skróty SHA-256 drzew (suma sum `find . -type f | sort | xargs sha256sum | sha256sum`) równe wartościom z README R603C: uc03 `a2681d9b...`, uc05 `ce892219...`, uc06 `cb51496c...`, uc07 `5a86cd94...`, uc08 `71639a56...`.
2. **Binarki.** C: `~/R376/bin/R603C_C` zgodna z `R603C_C.sha256` (`xretractor` `3458ed99...`, `xqry` `a7b7dcbd...`). C': budowa przyrostowa 07:34-07:56 (22 min, 170 kroków, bo zmiana `constants.hpp` dotyka wielu jednostek), `xretractor` `e435618b...`, `xqry` `4e8dd234...`; `--build-info` identyczne z C (wszystkie `RDB_OPT_*` i `RDB_BENCH_PROBE` ON). `xqry` C' różni się od C mimo `src/qry` bez zmian, bo `constants.hpp` jest wspólny; protokół klienta bez zmian.
3. **G1 spełniona** we wszystkich 4 przebiegach: `trace_overrun` = 0 przy buforze 65 536 kB (aneks 2), 33 532-34 590 obrotów na 36,8-37,9 s śladu (0,912-0,914 na ms), odstęp p50 1092-1093 µs, najdłuższy odstęp poza podłączeniami i seriami 1,2-2,7 ms, żaden inny wątek spoza RT nie śpi w śladzie.
4. **G2 spełniona**: w C' 7 z 7 niezakłóconych serii w uc05 i 7 z 7 w uc03 (pozostałe 3 porzucenia w każdym przebiegu to przepełnienia w ogonie). Pełna porcja p50 77 µs (uc05) i 75 µs (uc03), najkrótsza 74 / 73 µs, wobec p99,9 obrotu bezczynnego 70 / 61 µs; ostatnia porcja p50 30 µs (64 komunikaty) i 64 µs (208 komunikatów); obrót Pk+1 13-17 µs wobec p99 obrotu bezczynnego 26 / 20 µs. Zakłóconych serii 0. P0 w C' p50 ~0,30 ms (`kill`, pierwsza porcja, `renameat`), w C 2,37 ms (uc05) i 0,79 ms (uc03), jak w R603C. Seria P0..Pk p50 36,3 ms (uc05) i 8,4 ms (uc03), wobec ~33 i ~7,5 ms w *Przewidywaniu* (obrót 1,092 ms zamiast 1,07 ms).
5. **G3 spełniona**: w każdym przebiegu do puli 10 z 10 (`kill` = -ESRCH), 5 kolejek utworzonych i 5 oddanych z puli, 3 przepełnienia w ogonie, spójność ogona, model stanu puli bez naruszeń, każda seria gotowa przed następnym podłączeniem; k z długości `mmap` = 31 (pojemność 8000) i 7 (2000).
6. **G4 spełniona**: `futex` wątku slotu w 0,029-0,075 % slotów; jedno `FUTEX_WAIT` na muteksie kolejki (uc03 C').
7. **G5**: `trace.txt` 7,3-7,7 MB na przebieg z 10 podłączeniami (~37 s śladu), po gzip 0,4 MB; cały przebieg po gzip 1,0 MB (uc05) i 0,5 MB (uc03). Przy 30 podłączeniach (~87 s śladu) to ~2,4 i ~1,2 MB, a cała kampania ~130 MB, więcej niż 95 MB: archiwum zostanie podzielone na części po rodzinach, każda z własnym indeksem (*Aparatura*, punkt 6).
8. **H spełniona** w postaci z aneksu 1: uc03 argmin = H = 8 w obu stronach; uc05 argmin 20, H = 40 jego wielokrotnością, mediana przy 40 o 2,8 % (C) i 0,2 % (C') nad medianą przy 20.

## Kampania

Uruchomiona 2026-11-06 08:00:53 na pi400 (`setsid nohup ./campaign.sh`, log `~/R376/campaign_R603D.log`, dane `~/R376/raw_R603D`), 5 rodzin × 9 par = 90 przebiegów, ~2,5 h. Przerwana rodzina = powtórzyć całą (ABBA).


Zakończona: ostatni przebieg uruchomiony 10:30:40, log kończy się `CAMPAIGN_COMPLETE` (kopia `campaign.log`), 90 z 90 przebiegów ważnych. Wynik: `wynik.md` (K1' NIEZDANE w uc03, uc05, uc06 z warunku gotowości (a), ZDANE w uc07, uc08; K2a NIEZDANE w uc05 i uc06, NIEROZSTRZYGNIĘTE w uc03, uc07, uc08; K2b opisowe; K3 bez regresji). Surowe archiwum w pięciu częściach po rodzinach w prywatnym `paper-arXiv`, `rdb-experiment-embargo/R603D/`; tu tylko indeksy `results_20261105_R603D_raw_ucNN.index.tsv`. Następny krok: decyzja człowieka (`wynik.md`, *Skutek dla naprawy*).
