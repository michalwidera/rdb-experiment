# R603F - pomiar potwierdzający wcześniejsze rozpoznanie śmierci klienta przez sondę życia subskrybentów (D2s) wobec porcji bez wyrównania (C') (pi400, `--realtime`)

Zgłoszenie: michalwidera/retractordb#603, plan D2s z komentarza 6688281387 (zatwierdzony 2026-11-06), kierunek 4 z *Skutku* R603E i decyzja człowieka po R603E (`results_20261106_R603E/wynik.md`, *Decyzje człowieka po wyniku*, punkt 2). Ten plik zapisano PRZED pomiarem i przed budową aparatury; po zatwierdzeniu przez człowieka zmiany protokołu trafiają do sekcji *Aneksy* z datą i powodem, nie do treści powyżej.

**Stan: projekt do zatwierdzenia.** Plan aparatury i decyzje D0-D4 zatwierdzone przez człowieka 2026-11-06 według rekomendacji (*Decyzje*).

Aparatura pochodzi z R603E (`results_20261106_R603E/`, protokół `d41cb82`, aparatura `9d750cd`, aneksy `cbd285e`, scalenie do `main` `3b1b50b`), a przez nią z R603D, R603C i R600. Opis aparatury, który się nie zmienił, jest w ich README; poniżej są tylko różnice i nowe kryteria.

## Pytanie

R603E pokazało, że koszt porzucenia idzie za ilością przeczytanej kolejki, a nie za chwilą odczytu: wyrównanie porcji do przerwy po slocie (C'') usunęło nakładanie, ale nie obniżyło kosztu serii (K2s NIEZDANE w uc03 i uc05). Kolejka martwego klienta ma dziś zawsze komplet komunikatów, bo jedynym sygnałem śmierci klienta jest pełna kolejka po zapasie 10 s. D2s rozpoznaje śmierć sondą życia co 1 s, więc kolejka idzie do puli z co najwyżej ~1 s komunikatów. Pytania:

1. Czy mechanizm działa: każde porzucenie zaczyna się od wykrycia przez sondę, ≤ ~1 s po zebraniu klienta przez rodzica, a nie od pełnej kolejki (K0)?
2. Czy D2s obniża łączny koszt serii drenażu na slotach dotkniętych co najmniej o połowę (K2s, kryterium główne, miara z decyzji D2 R603E)?
3. Czy pula nadal działa (K1'') i czy sonda nie kosztuje nic poza seriami, ani w wątku slotu, ani w obrocie bezczynnym wątku komunikacyjnego (K3, K3t)?

## Strony porównania

| Strona | Rewizja silnika | Co robi wątek komunikacyjny z kolejką martwego klienta |
|---|---|---|
| C' (`Cp`) | `e0857dc8ba5387929c0e79d172cb8c45a669e3a3` | rozpoznanie przy pełnej kolejce (`broadcast`, ~10 s po śmierci), potem `kill(pid, 0)` = -ESRCH, P0 (porcja 256 komunikatów), `renameat` pod nazwę puli jako wpis niegotowy, potem jedna porcja w każdym obrocie aż do opróżnienia (R603D i R603E, strona C') |
| D2s (`D2s`) | `75e7574cf90d7548b1d95c7cef5a80e9b5700f91` (`dev/muro`; drzewo = `e0857dc8` + sonda, C'' wycofany w `71272b8f`) | co `kClientLivenessProbeInterval` = 1 s `inspectProcess` dla każdego obserwowanego klienta; martwy (ESRCH albo inny `startTime`) jest wypisywany z rejestru pod jednym zajęciem `clientMapsMutex_`, a jego kolejka idzie tą samą drogą co w C' (`poolAbandonedQueue`: `kill(pid, 0)`, P0, `renameat`, dalej porcje), tylko z ≤ ~1 s komunikatów |

- **D2s = `75e7574c`**: zmienia `src/include/constants.hpp` (`kClientLivenessProbeInterval`), `src/retractor/lib/ipcServer.{hpp,cpp}` (poświadczenie tożsamości w `subscribe`, `probeSubscribers` w każdym obrocie `commandLoop` przed `releaseAbandonedQueues`, wspólne `releaseQueue`), `src/retractor/lib/executorsmCommands.cpp` (`db.start` do `subscribe`), `test/UnitTest/test_ipcServer.cpp`. Wątek slotu, `src/qry` i `src/rdb/lib/probe.cc` bez zmian. `xqry` obu stron wysyła `db.start` (od #569), więc klient jest obserwowany po obu stronach protokołu, a działa to tylko w D2s.
- **C'** jest stroną odniesienia K2s, K3 i K3t oraz kontrolą dodatnią K2s i K1''.
- Obie strony mają łatkę P1 (`deadline_ns`, `P1_deadline_ns.patch` z R603D bez zmian).

## Ustalenia przed pomiarem (2026-11-06)

**Z kodu i śladu R603E** (archiwum `rdb-experiment-embargo/R603E/`, trzy części, sumy jak w `results_20261106_R603E/wynik.md`):

1. **Ślad sondy.** ftrace nie niesie nazw plików (`filename` to wskaźnik), więc wpisu `/proc/<pid>/task/<pid>/stat` nie da się rozpoznać po nazwie, tylko po wzorcu. `inspectProcess` dla PID-u bez procesu to `openat` = -ENOENT, a po nim `kill(pid, 0)` = -ESRCH. Dla procesu żywego albo zombie to `openat` z sukcesem (`read` i `close` nie są śledzone), bez `kill`. Wykrycie śmierci przez sondę to więc **dwie pary `openat` -ENOENT + `kill(pid, 0)` -ESRCH dla tego samego PID-u w jednym obrocie wątku komunikacyjnego**: pierwsza z `probeSubscribers`, druga z `poolAbandonedQueue`. Po drugiej idzie P0 i `renameat`, tak jak w C'. Parser R603C bierze pierwszy `kill(pid_klienta, 0)` po starcie klienta i zrywa okno na następnym `openat`, więc w D2s zgubiłby każde P0 (*Aparatura*, punkt 4).
2. **Klient żyje krótko.** W R603E od startu do zebrania mija p50 ~36 ms (uc03 35,5, uc05 35,6, uc06 35,8 ms), od pierwszego wiersza do zebrania p50 1,33 ms. Następny klient startuje 2,0-3,0 s po zebraniu poprzedniego. Sonda trafia więc na żywego klienta w ~3,6 % podłączeń (~1 raz na przebieg). Przy pustej liście obserwowanych obrót płaci tylko odczyt zegara (`steady_clock`, vDSO, bez wywołania systemowego). **Kosztu sondy przy długo żyjących subskrybentach ta kampania nie mierzy** (D3).
3. **Pula prawie nie tworzy kolejek.** Kolejka wraca do puli ≤ ~1 s po zebraniu klienta, a następny klient startuje ≥ 2 s po nim. W każdym przebiegu kolejkę tworzy tylko pierwszy klient (pula po starcie silnika jest pusta) oraz klient po zwolnieniu bez puli (martwy muteks). Pula ma najwyżej 1 wpis, więc **przepełnienie nie występuje**. Kontrola dodatnia K1' z R603D („przepełnienie w ogonie w każdym przebiegu”) jest na D2s z konstrukcji nieosiągalna (D4).
4. **Martwy muteks przy znalezionym procesie** (R603E, `Cpp_03` uc06, klient 16): `openat` z sukcesem, potem `munmap` i `unlinkat` kolejki, 0,9 ms po pierwszym wierszu klienta i przed jego zebraniem, bez `kill`. Ta sama ścieżka (`broadcast` trafia na martwy muteks w następnym slocie, `releaseAbandonedQueues`, `poolAbandonedQueue` widzi niezebrany proces) jest w D2s bez zmian. Sonda zobaczy potem tego klienta już wypisanego: samotna para `openat` -ENOENT + `kill` -ESRCH bez zwolnienia przed następnym snem.
5. **Log silnika nie pomoże.** Release-Probe loguje tylko błędy (`SPDLOG_ACTIVE_LEVEL`), więc wpisy `queue pooled on client death` nie powstają i nie mogą służyć do kontroli krzyżowej parsera.

**Liczby z danych C' R603E** (`est_d2s.py`; analiza `results_20261106_R603E/analyze.py` bez zmian, tylko strona C', ziarna placebo 6034, bootstrap 6035, H0 6036, Monte Carlo 6040; uruchomienie: `retractordb/.venv-python/bin/python3 -I est_d2s.py <katalog z rozpakowanymi częściami>/raw`, ~45 s):

6. **Ile komunikatów zastanie D2s.** Tempo strumienia r = pojemność / mediana(`kill` - pierwszy wiersz) w C' wynosi dokładnie pojemność / 10 s: 200,0 / 799,9 / 500,0 na sekundę (uc03 / uc05 / uc06; mediana zapełnienia 10,001-10,002 s). Faza sondy względem śmierci klienta jest jednostajna (sonda co 1 s, starty losowe), więc n ≈ r · (czas od pierwszego wiersza do zebrania + U(0; 1 s + obrót)), a k = ⌈(n - 256) / 256⌉ porcji po P0:

| rodzina | pojemność | n p50 / średnio / max | średnie n / pojemność | P(k = 0 / 1 / 2 / 3) | średnie k (C': k stałe) | seria P0 + k obrotów p50 / max (C' p50 R603E) |
|---|---|---|---|---|---|---|
| uc03 | 2000 | 100 / 100 / 200 | 0,050 | 1,000 | 0,00 (7) | 0,31 / 0,31 ms (8,43 ms) |
| uc05 | 8000 | 401 / 402 / 802 | 0,050 | 0,319 / 0,320 / 0,320 / 0,042 | 1,08 (31) | 1,47 / 3,78 ms (36,26 ms) |
| uc06 | 5000 | 250 / 250 / 501 | 0,050 | 0,512 / 0,488 | 0,49 (19) | 0,31 / 1,47 ms (22,36 ms) |

   Średnio ~20 razy mniej komunikatów niż w C'. „~10 razy” z planu D2s to granica dla n maksymalnego. Długość serii to górna granica: P0 z mniejszą liczbą komunikatów trwa krócej niż P0 C' (309-314 µs).
7. **Koszt samotnego okna P0** (256 komunikatów; sloty dotknięte przez samo P0 w seriach C', w których wszystkie te sloty kończą się przed startem P1, z placebo jak R603E):

| rodzina | serii | slotów na serię | Δ mediany [µs] (95 %) | S1 = koszt na serię [µs] (95 %) | S(C') w tym przeliczeniu [µs] (95 %) | przewidywane S(D2s): (1 + k̄) · S1 / n̄ / 256 · S1 [µs] | próg 0,5 · S(C') [µs] |
|---|---|---|---|---|---|---|---|
| uc03 | 2 | 1,00 | +17,56 (+15,52..+19,51) | +16,0 (+13,2..+18,7) | +75,4 (+68,3..+84,0) | +16,0 / +6,2 | 37,7 |
| uc05 | 195 | 1,37 | +5,87 (+5,19..+7,28) | +9,9 (+7,9..+13,4) | +268,0 (+186,1..+349,8) | +20,7 / +15,5 | 134,0 |
| uc06 | 145 | 1,22 | +17,24 (+16,37..+19,12) | +156,3 (-234,6..+833,7) | +2227,3 (+186,4..+4404,6) | +232,6 / +152,9 | 1113,7 |

   - S(C') liczone tu tylko na stronie C' różni się od wydruku R603E (uc05 +264,9, uc06 +2583,9 µs), bo kolejność losowań placebo jest inna (bez stron C'' między przebiegami C'). W uc03 identyczne.
   - W uc03 tylko 2 serie C' mają slot następny po P0 przed P1 (takt 5 ms, P1 po ~1,15 ms), więc S1 uc03 nie ma liczności. Górne granice z wcześniejszych badań: slot następny po porcji 256 komunikatów przy otwartej bramce +27,15 µs Δ mediany (R603E, *Ustalenia*, punkt 1) i cała kolejka 2000 komunikatów jednym ciągiem +51,1 µs na serię (R603E, *Ustalenia*, punkt 3, strona C). D2s czyta w uc03 ≤ 200 komunikatów, więc przewidywane S(D2s) w uc03 to ~+6..+27 µs.
8. **Moc kontroli H0 K2s dla serii o kształcie D2s** (P0 + k porcji, k losowane z punktu 6, parametry P0, porcji, obrotu i fazy z C', 5 serii syntetycznych na serię C' jak aneks A2 R603E, na tle slotów kontrolnych C'):

| rodzina | serii H0 | S [µs] (95 %) | półszerokość [µs] | 0,25 · S(C') [µs] |
|---|---|---|---|---|
| uc03 | 1192 | -0,1 (-1,4..+1,4) | 1,4 | 18,9 |
| uc05 | 1166 | +2,2 (-1,5..+6,1) | 3,8 | 67,0 |
| uc06 | 1189 | -136,3 (-349,2..+122,2) | 235,7 | 556,8 |

   Seria D2s dotyka 1-2 slotów zamiast 2-32, więc kontrola H0 jest w progu we wszystkich trzech rodzinach, także w uc06, gdzie w R603E nie była (824 µs przy seriach C'').

## Okna i zdarzenia

- **Okna R_C** (obie strony): [wyjście z `kill(pid_klienta, 0)` = -ESRCH, wyjście z `renameat` = 0] jak w R603C, z jedną zmianą w D2s: bierzemy `kill` z `poolAbandonedQueue`, czyli ostatni `kill(pid_klienta, 0)` przed zwolnieniem.
- **Wykrycie przez sondę** (D2s): `kill(pid_klienta, 0)` = -ESRCH poprzedzony `openat` = -ENOENT, po którym w tym samym obrocie wątku komunikacyjnego (bez snu pomiędzy) jest drugi `openat` = -ENOENT i drugi `kill(pid_klienta, 0)` = -ESRCH. Chwila wykrycia t_det = wyjście z pierwszego `kill`.
- **Samotne wykrycie** (D2s): para `openat` -ENOENT + `kill(pid_klienta, 0)` -ESRCH, po której przed następnym snem nie ma ani drugiego `kill`, ani `renameat`, ani `munmap` + `unlinkat`. Sonda zobaczyła klienta już wypisanego (*Ustalenia*, punkt 4). Nie jest oknem ani porzuceniem.
- **Opóźnienie wykrycia** L = t_det - koniec klienta (`end_ns` w `conns.tsv` = po `wait` i po sprawdzeniu ESRCH, ten sam zegar `CLOCK_MONOTONIC`).
- **Porzucenie z pełnej kolejki** (obie strony): okno R_C bez wykrycia przez sondę w tym samym obrocie i bez martwego muteksu. Na C' to każde porzucenie, na D2s przewidywane 0.
- **Martwy muteks** (obie strony, poprawka z decyzji człowieka po R603E, punkt 1):
  - (a) jak w R603C: zwolnienie bez puli po `kill` = -ESRCH, ≤ 9,5 s po pierwszym wierszu. Na D2s również zwolnienie bez puli po wykryciu przez sondę (P0 zgłosiło błąd; innej przyczyny ślad nie odróżnia, liczba podawana osobno);
  - (b) **proces znaleziony**: para `munmap` + `unlinkat` kolejki odpowiedzi w wątku spoza RT, poza oknami R_C, poprzedzona w tym samym wątku `openat` z sukcesem bez `kill` pomiędzy, z `munmap` w [pierwszy wiersz klienta, jego koniec + 10 ms] dla klienta bez okna R_C. Przypisana temu klientowi;
  - para martwego muteksu jest wyjaśniona także **po ostatnim starcie (w ogonie)**, a nie tylko w fazie pracy.
- **Seria D2s** = P0 i k kolejnych obrotów wątku komunikacyjnego, gdzie k = ⌈(n̂ - 256) / 256⌉, n̂ = round(r · (t_det - pierwszy wiersz klienta)), r = pojemność kolejki z `mmap` / 10 s. **Seria graniczna**: |n̂ - 256 · j| ≤ 4 dla pewnego j ≥ 1 (k niepewne o 1). Seria graniczna wchodzi do K2s z k z n̂, a do G2f nie. Serie zakłócone (wywołanie w P1..Pk) jak w R603D.
- **Seria C'** jak w R603D (P0 + k obrotów, k z pojemności).
- **Sloty dotknięte**, **koszt serii S**, sloty kontrolne, placebo, klasy `iter mod H` jak w R603E (*Okna i zdarzenia*).
- **Obrót bezczynny** jak w R603D: obrót wątku komunikacyjnego bez żadnego śledzonego wywołania, poza seriami (od `kill` do końca Pk), podłączeniami i oknami R_C. Na D2s dodatkowo poza wykryciami (od pierwszego `openat` wykrycia do końca jego obrotu).

## Przewidywanie przed pomiarem

| rodzina | takt | seria p50 C' → D2s | S C' → D2s [µs/serię] (*Ustalenia*, 7) | K2s | sloty dotknięte na serię C' → D2s | kolejki utworzone / z puli / przepełnienia na rodzinę C' → D2s |
|---|---|---|---|---|---|---|
| uc03 | 5 ms | 8,4 → ≤ 0,31 ms | +75 → ~+6..+27 | ZDANE (zapas mniejszy) | 2,2 → 1,0 | 45 / 225 / 27 → 9 / 261 / 0 |
| uc05 | 1 ms | 36,3 → ~1,5 ms | +265 → ~+15..+21 | ZDANE | 31,8 → ~2 | 45 / 225 / 27 → 9 / 261 / 0 |
| uc06 | 2 ms | 22,4 → ≤ ~0,3..1,5 ms | +2584 → ~+150..+230 | NIEROZSTRZYGNIĘTE (przedział T) albo ZDANE | 12,1 → ~1,5 | 48 / 222 / 25 → 9 / 261 / 0 |

1. **K0: ZDANE.** L ma rozkład ~U(0; 1 s): p50 ~0,5 s, max ≤ 1,002 s. Na D2s 0 porzuceń z pełnej kolejki; na C' 0 wykryć przez sondę.
2. **K2s: ZDANE w uc05** (T ≈ +20 - 134 ≈ -114 µs, przedział S(C') ±80 µs) **i w uc03** (T ≈ +6..+27 - 37,7 µs; przy S(D2s) bliżej górnej granicy zapas to kilka µs). **W uc06 T ≈ +200 - 1100 µs**, ale przedział S(C') jest szeroki (±2100 µs), więc T prawdopodobnie obejmie 0: NIEROZSTRZYGNIĘTE z przedziału, nie z miary (*Ustalenia*, punkt 8).
3. **Δ mediany slotów dotkniętych** (opisowo): uc05 ~+6 µs, uc06 ~+17 µs (samotne P0, *Ustalenia*, punkt 7), uc03 ≤ ~+27 µs.
4. **K1'': ZDANE.** 1 kolejka utworzona na przebieg (+1 na każdy martwy muteks), 0 przepełnień, warunek (a) 0 (seria ≤ 4 ms, następny start ≥ 2 s po zebraniu), O6 0. Martwych muteksów tyle co w C' (R603E: 0 / 0 / 4-5 na rodzinę).
5. **K3: bez regresji.** Wątek slotu bez zmian w kodzie; jedyna różnica poza seriami to jedno `inspectProcess` przy subskrypcji (wątek komunikacyjny, w oknie podłączenia).
6. **K3t: bez regresji**, różnica p50 obrotu bezczynnego ≤ 1 µs (rozdzielczość znacznika ftrace), p99 w szumie.
7. **Opisowo.** E (sloty narażone na serię) w uc05 ~0,2-0,4 wobec 6,3 w C'. Okno podłączenia z puli (~0,05 ms) zamiast utworzonej kolejki (2,8-9,9 ms) w 29 z 30 podłączeń, a w D2s dłuższe o jedno `inspectProcess`. Sonda widoczna na żywym albo zombie kliencie ~1 raz na przebieg.

## Kryteria (ustalone przed pomiarem)

Dla każdej rodziny i strony, sumarycznie po 9 przebiegach. Bootstrap: 95 % percentylowy po seriach (klaster = seria z jej kopiami placebo), 2000 losowań, ziarno jak R603E; strony losowane niezależnie.

### K0 - mechanizm: wykrycie przez sondę (D2s)

**ZDANE**, gdy na D2s każde porzucenie (okno R_C) poza wyłączeniami K1'' zaczyna się od wykrycia przez sondę z -5 ms ≤ L ≤ 1,010 s (okres sondy + obrót + margines odczytu `end_ns`), nie ma porzuceń z pełnej kolejki, a na C' nie ma ani jednego wykrycia przez sondę (kontrola ujemna rozpoznania). **NIEZDANE** w każdym innym przypadku. Opisowo: rozkład L, rozkład n̂ i k wobec *Ustaleń*, punkt 6, samotne wykrycia, zwolnienia bez puli po wykryciu.

### K1'' - pula bez regresji (D2s)

Jak K1'' R603E (warunek (b) modelu stanu puli jako werdykt, do puli = podłączenia - wyłączenia, zero niewyjaśnionych par i zwolnień bez puli, spójność ogona, wyłączenia ≤ 5 %), z dwiema zmianami:

- **klasyfikacja martwego muteksu** z *Okien i zdarzeń* (punkty (a), (b) i ogon) na obu stronach;
- **kontrola dodatnia (D4)**: strona C' tej samej rodziny ma przepełnienie w ogonie w każdym przebiegu (parser widzi zwolnienie najstarszego wpisu), a strona D2s ma w każdym przebiegu co najmniej jedno oddanie z puli. Wzór spójności ogona bez zmian (przepełnienia = max(0, utworzone - zwolnione bez puli - 2), na D2s przewidywane 0 = 0).

Warunek (a) i O6 opisowo. Werdykt C' opisowo (powtórzenie R603E z poprawioną klasyfikacją).

### K2s - koszt serii na slotach dotkniętych (kryterium główne)

Jak K2s R603E ze stroną D2s w miejscu C'': T = średnie S(D2s) - 0,5 · średnie S(C') (D1). **ZDANE**, gdy górna granica T < 0; **NIEZDANE**, gdy dolna granica T > 0; **NIEROZSTRZYGNIĘTE**, gdy przedział zawiera 0. Opisowo: S obu stron, S(D2s) - S(C'), u_S, Δ mediany slotów dotkniętych i slotów następnych.

- **Ważność miary**: kontrola dodatnia (dolna granica S(C') > 0); kontrola H0 - serie syntetyczne o kształcie D2s (P0 + k porcji, k losowane z empirycznego rozkładu k strony D2s tej kampanii, parametry P0, porcji, obrotu i fazy z D2s) na tle slotów kontrolnych C' tej kampanii, 5 na każdą niezakłóconą serię C', półszerokość przedziału S ≤ 0,25 · S(C'). Niespełniona = NIEROZSTRZYGNIĘTE (miara).
- **Liczność**: ≥ 50 niezakłóconych serii na stronę.

### K3 - bez regresji poza seriami (wątek slotu)

Jak R603E (D2s wobec C'): sloty kontrolne, per przebieg `compute_ns` p50, `wake_lag_ns` p99, `e2e_ns` p99; różnica median wobec rozrzutu wewnątrz strony i dokładny permutacyjny MW 9 vs 9. Różnica dodatnia i większa od rozrzutu = regresja D2s, osobne znalezisko.

### K3t - obrót bezczynny wątku komunikacyjnego (D2)

Per przebieg p50 i p99 długości obrotu bezczynnego (*Okna i zdarzenia*), D2s wobec C', ta sama reguła i ten sam test co K3.

### Opisowo (bez kryterium)

- **E** - sloty narażone na serię (definicja R603D); K2e R603E nie jest kryterium, bo D2s nie ma bramki.
- **Sonda**: liczba wykryć, samotnych wykryć, `openat` z sukcesem w wątku komunikacyjnym w oknach podłączeń ponad jedno na podłączenie (sonda na żywym albo zombie kliencie; w D2s jedno to poświadczenie przy subskrypcji), czas obrotu z wykryciem.
- **O1-O6** jak R603E (O3 z rozkładem n̂, k i serii granicznych; O2 z liczbą kolejek utworzonych i z puli); **O4** R603D dla ciągłości.

## Aparatura - różnice wobec R603E

1. **`build_ab.sh`**: tylko D2s (`75e7574c` + P1), przyrostowo w `~/R376/src` (dziś `d105498a` + P1), binarki do `~/R376/bin/R603F_D2s`, `setcap cap_ipc_lock,cap_sys_nice=ep` jak dotąd. Źródła z `origin` (`75e7574c` jest wypchnięty). Build-info równe C', sumy do `R603F_D2s.sha256`. **Binarka C'** z R603D bez przebudowy (`~/R376/bin/R603D_Cp`, `xretractor` `e435618b...`, `xqry` `4e8dd234...`), suma sprawdzana przed kampanią.
2. **`run_one.py`, `campaign.sh`**: strony `Cp` i `D2s` (`BIN_DIR`: `R603D_Cp`, `R603F_D2s`); katalogi `~/R376/raw_R603F`, `~/R376/apparatus_R603F`, `~/R376/dry_R603F`; zmienne `R603F_PAIRS`, `R603F_CONNS`, `R603F_RAW`. Śledzone wywołania (w tym `openat` i `kill` wątków spoza RT), bufor ftrace 65 536 kB, `RELEASE_TAIL_S` 12 s (ogon obejmuje porzucenie z pełnej kolejki, gdyby sonda klienta nie objęła), reguły unieważnienia bez zmian.
3. **Rodziny i liczba par** (D0): uc03, uc05, uc06, po 9 par ABBA, 30 podłączeń; para nieparzysta C', D2s; parzysta D2s, C'. Razem 54 przebiegi (~1,5 h).
4. **`analyze.py`**: importuje `results_20261106_R603E/analyze.py` bez zmian (a przez niego R603D i R603C). Dochodzi:
   - `kill_windows_f`: rozpoznanie wykrycia przez sondę i samotnego wykrycia, okno R_C od `kill` z `poolAbandonedQueue`; na danych z jednym `kill` na porzucenie daje te same okna co `kill_windows` R603C;
   - poprawka klasyfikacji martwego muteksu (punkty (a), (b), ogon) dla obu stron;
   - `analyze_run_f`: kopia `analyze_run` R603D z k osobno dla każdej serii (z n̂) i z `kill_windows_f`; strona C' przez R603E/R603D bez zmian poza poprawką klasyfikacji;
   - K0, K1'' z D4, K2s z H0 o kształcie D2s, K3t, bramki G2f i G6.
5. **`est_d2s.py`** zostaje jako zapis *Ustaleń*, punkty 6-8.
6. **Archiwum** surowych danych jak R603E: prywatne `paper-arXiv`, `rdb-experiment-embargo/R603F/`, części po rodzinach, każda z indeksem; tutaj tylko indeksy.

## Kolejność

1. Zatwierdzenie tego protokołu przez człowieka; commit i push na gałęzi `experiment/20261106_R603F`.
2. Aparatura (punkt 4 *Aparatury*). **Test parsera** na surowych danych R603E (archiwum rozpakowane od nowa, 3 indeksy zgodne):
   - (1) raport R603E z poprawką klasyfikacji różni się od części *Wydruk analizy* `results_20261106_R603E/wynik.md` wyłącznie wierszami K1'' C'' i K1' C' w uc06 oraz wierszem uc06 tabeli *Werdykty*, i daje tam to, co zapisano w *Decyzjach człowieka po wyniku* R603E, punkt 1: C'' 5 wyłączeń z 270, do puli 265, niewyjaśnione 0, spójność ogona tak, ZDANE; C' 5 wyłączeń, spójność ogona tak, ZDANE. Każda inna różnica = błąd parsera;
   - (2) kontrola ujemna: `kill_windows_f` na wszystkich 54 przebiegach R603E nie znajduje ani jednego wykrycia przez sondę, a jego okna R_C są równe oknom `kill_windows` R603C.
3. Budowa D2s (~22 min, odczepiona), sprawdzenie korpusu (skróty drzew z README R603C) i binarki C'. Suchy przebieg uc05 i uc03, po 1 przebiegu C' i D2s z 10 podłączeniami (`~/R376/dry_R603F`). **Bramki** (każda niespełniona = decyzja człowieka przed kampanią):
   - **G1, G3, G4, G5, H** jak w R603E;
   - **G2f** - porcje zgodne ze śladem: w niezakłóconych, niegranicznych seriach co najmniej 99 % pełnych porcji (P1..Pk-1) jest dłuższych niż p99,9 obrotu bezczynnego, a co najmniej 99 % obrotów Pk+1 nie jest dłuższych niż p99 obrotu bezczynnego (C' jak G2 R603D);
   - **G6** - rozpoznanie sondy: na D2s każde porzucenie poza martwym muteksem ma wykrycie przez sondę z L w granicach K0, a na C' nie ma wykryć.
4. Kampania: 3 rodziny × 9 par = 54 przebiegi, ~1,5 h, odczepiona (`setsid nohup`). Przerwana rodzina = powtórzyć całą (ABBA).
5. `wynik.md`, surowe archiwum w `paper-arXiv/rdb-experiment-embargo/R603F/` (wiersz w obu tabelach README), tutaj tylko indeksy sum; komentarz w #603.

## Decyzje (zatwierdzone przez człowieka 2026-11-06: D0-D4 według rekomendacji)

- **D0 - rodziny i liczba par.** Wybrane: uc03, uc05, uc06 × 9 par ABBA, 30 podłączeń (54 przebiegi, ~1,5 h): rodziny, w których K2s ma moc. Alternatywa: dołożyć uc07 i uc08 dla K0 i K1'' (+~1 h).
- **D1 - próg K2s.** Wybrane: 0,5 (T = S(D2s) - 0,5 · S(C')), jak D1 R603E. Alternatywa: 0,25, ostrzej, bo D2s czyta średnio ~20 razy mniej komunikatów.
- **D2 - koszt sondy.** Wybrane: K3 jak w R603E (wątek slotu) i K3t (p50 i p99 obrotu bezczynnego wątku komunikacyjnego na przebieg, ta sama reguła regresji). Alternatywa: K3t tylko opisowo.
- **D3 - sonda przy żywym kliencie** (*Ustalenia*, punkt 2). Wybrane (a): granica wniosków, opisowo czas przebiegów sondy widocznych w śladzie. Alternatywy: (b) osobna krótka kampania tylko K3 z długo żyjącymi subskrybentami; (c) długo żyjący subskrybent w tej kampanii (zmienia obciążenie wobec R603E i miesza skutki).
- **D4 - kontrola dodatnia K1'' na D2s** (*Ustalenia*, punkt 3). Wybrane: kontrola dodatnia ze strony C' tej samej rodziny (przepełnienie w ogonie w każdym przebiegu) i co najmniej jedno oddanie z puli w każdym przebiegu D2s; wzór spójności ogona bez zmian.

## Granice wniosków (znane przed pomiarem)

- Jedna platforma: Cortex-A72, wspólne L2 1 MiB, jądro 6.8 `PREEMPT_RT`, jak R603D/R603E.
- Koszt sondy mierzony tylko przy krótko żyjących klientach (D3); dla N długo żyjących subskrybentów to N odczytów wpisu procesu na sekundę w wątku komunikacyjnym, nieuwzględnione w K3t.
- Kolejka w D2s była zapisywana do chwili wykrycia, a w C' ~10 s wcześniej niż jej odczyt; ciepło jej stron w L2 może się różnić. To część skutku D2s, nie błąd miary.
- Liczba podłączeń z puli i warunek (a) zależą od rytmu aparatury (start co ~2,5 s, klient ~36 ms).

## Embargo

Korpus `uc01`..`uc08` jest objęty embargiem do publikacji DEBS. W tym katalogu i w komentarzach do zgłoszeń: wyłącznie identyfikatory rodzin i liczby z nich wyprowadzone (pojemności kolejek, tempa, H, liczby slotów, czasy). Plany, dane, generatory i nazwy strumieni zostają na workerze w `/dev/shm/r376` i w prywatnym `paper-arXiv`. Surowe CSV i ślady ftrace poza git; zostaje indeks sum. `est_d2s.py` czyta surowe dane R603E z prywatnego archiwum i wypisuje tylko liczby wyprowadzone.

## Aneksy

(brak)
