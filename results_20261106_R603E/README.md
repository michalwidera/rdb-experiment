# R603E - pomiar potwierdzający wyrównanie porcji drenażu do przerwy po slocie (C'') wobec porcji bez wyrównania (C') (pi400, `--realtime`)

Zgłoszenie: michalwidera/retractordb#603, plan C'' z komentarza 6682025945 (zatwierdzony 2026-11-06). Ten plik zapisano PRZED pomiarem i przed budową aparatury; po zatwierdzeniu przez człowieka zmiany protokołu trafiają do sekcji *Aneksy* z datą i powodem, nie do treści powyżej.

**Stan: projekt do zatwierdzenia.** Ustalenia przed pomiarem (punkt 1-3) przewidują, że C'' nie obniży kosztu serii drenażu. D0-D2 rozstrzygnięte przez człowieka 2026-11-06 według rekomendacji (*Decyzje*): skrócona kampania na uc03, uc05, uc06, próg K2s - obniżenie kosztu serii co najmniej o połowę, miara slotów dotkniętych główna także w następnych badaniach #603.

Aparatura pochodzi z R603D (`results_20261105_R603D/`, protokół `2f1d3e6`, aparatura `c39b31d`, wynik `9a55b0a`, scalenie do `main` `7af0ec6`). Opis aparatury, który się nie zmienił, jest w README R603D, R603C i R600; poniżej są tylko różnice i nowe kryteria.

## Pytanie

R603D pokazało, że porcja 256 komunikatów wydłuża liczenie slotu, z którym się nakłada, ~8 razy mniej niż drenaż jednym ciągiem (u' = 0,13), ale ponad próg (K2a NIEZDANE w uc05 i uc06), a rozłożenie drenażu na 8-36 ms nie obniża łącznego kosztu porzucenia (O4). Decyzja człowieka 2026-11-06: wariant C'' - P0 i porcje P1..Pk tylko w przerwie po slocie, nie w trakcie jego liczenia. Pytania:

1. Czy bramka działa: porcje i P0 nie nakładają się z liczeniem slotu (K2e)?
2. Czy C'' obniża łączny koszt serii drenażu na slotach, które seria dotyka - nakładających się z nią i następnych po jej oknach (K2s, kryterium główne)?
3. Czy pula nadal działa (K1'', warunek (b) modelu stanu puli) i czy poza seriami nic się nie pogorszyło (K3)?

## Strony porównania

| Strona | Rewizja silnika | Co robi wątek komunikacyjny z porzuconą kolejką martwego klienta |
|---|---|---|
| C' (`Cp`) | `e0857dc8ba5387929c0e79d172cb8c45a669e3a3` | `kill(pid, 0)` = -ESRCH, porcja 256 komunikatów, `renameat` pod nazwę puli jako wpis niegotowy, potem jedna porcja w każdym obrocie aż do opróżnienia (R603D, strona C') |
| C'' (`Cpp`) | `d105498ae60636403ea1b74a13c0f61a35c8e07d` (`dev/muro`, pierwszy rodzic `e0857dc8`) | to samo co C', ale P0 tylko przy `teraz + 500 µs < termin następnego slotu`, a każda porcja tylko przy `teraz + 200 µs < termin`; po 100 kolejnych obrotach z zamkniętą bramką krok idzie mimo niej |

- **C'' = `d105498a`**: jeden commit na `e0857dc8`, zmienia `src/include/constants.hpp` (`kDrainBatchSlotReserve` 200 µs, `kAbandonedQueueSlotReserve` 500 µs, `kDrainGateMaxDeferrals` 100), `src/retractor/lib/ipcServer.{hpp,cpp}` (bramka w `releaseAbandonedQueues` przed P0 i w `drainPooledStep` przed porcją; zegar `CLOCK_MONOTONIC` czytany tylko, gdy krok czeka i termin ≠ 0), `src/retractor/lib/executorsm.{hpp,cpp}` (zapis atomowy terminu `loop_anchor + deadlineMs` tuż przed `rtAbsoluteSleep`, 0 po wyjściu z pętli slotów, brak publikacji w `--no-clock`), `test/UnitTest/test_ipcServer.cpp`. `src/qry` i `src/rdb/lib/probe.cc` bez zmian.
- Termin publikowany przez wątek slotu jest tym samym `deadline_ns`, który łatka P1 zapisuje w `slots.csv` (kotwica + czas logiczny slotu, ten sam zegar co `trace_clock=mono`). Bramkę da się więc odtworzyć ze śladu i z `slots.csv` (*Okna i zdarzenia*).
- **C'** jest stroną odniesienia K2s i K3 oraz kontrolą dodatnią K2s i K2e.
- Obie strony mają łatkę P1 (`deadline_ns`, `P1_deadline_ns.patch` z R603D bez zmian; C'' nie dotyka `probe.cc`).

## Ustalenia przed pomiarem (2026-11-06, z surowych danych R603D)

Liczone na surowym archiwum R603D (części uc03, uc05, uc06, sumy SHA-256 zgodne z `results_20261105_R603D/wynik.md`) skryptami z tego katalogu, które importują `analyze.py` R603D bez zmian i wypisują tylko liczby wyprowadzone. Ziarna jak w R603D (placebo 6034, bootstrap 6035). Uruchomienie: `retractordb/.venv-python/bin/python3 -I <skrypt> <katalog z rozpakowanymi częściami>/raw`, ~1 min każdy.

1. **Slot następny po porcji, która go nie nakłada, liczy dłużej prawie tyle samo, co slot nakładający się z porcją** (`est_gate.py`). Bramkę C'' odtworzono na oknach C' z R603D: porcja „przeszłaby bramkę”, gdy w chwili startu jej obrotu poprzedni slot już się skończył (`deadline_ns + e2e_ns`) i do następnego terminu zostało więcej niż 200 µs. Żadna z takich porcji nie nakładała się z następnym slotem (porcja p99 127-134 µs < 200 µs). Odchylenie `compute_ns` od mediany klasy slotu NASTĘPNEGO po tych porcjach (każdy slot raz na serię), wobec tego samego w 20 kopiach placebo serii (przesunięcie o m · H · takt, sloty kontrolne):

| rodzina | bramka otwarta: porcja / P0 | slotów następnych | Δ mediany slotu następnego [µs] (95 %) | dla porównania R603D, K2a C' (sloty nakładające się) | suma na serię ponad placebo [µs] (95 %) |
|---|---|---|---|---|---|
| uc03 | 0,902 / 1,000 | 519 | +27,15 (+25,68..+28,40) | +33,70 (+30,72..+38,60) | +67,6 (+63,2..+72,9) |
| uc05 | 0,654 / 0,502 | 4245 | +4,30 (+4,11..+4,50) | +5,98 (+5,52..+6,48) | +201,9 (+148,4..+256,5) |
| uc06 | 0,699 / 0,919 | 2426 | +11,74 (+11,39..+12,09) | +12,00 (+11,02..+12,82) | +900,9 (-650,8..+2633,2) |

2. **Estymator nie jest obciążony** (`est_gate_h0.py`): syntetyczne serie porcji o parametrach C' (`h0_params` R603D) na tle strony C w czasie kontrolnym, ta sama bramka i ten sam slot następny: Δ mediany -0,02 (-0,13..+0,15) µs w uc03, -0,00 (-0,04..+0,04) w uc05, +0,15 (+0,04..+0,22) w uc06; suma na serię -0,8 (-3,9..+2,2), -16,5 (-49,5..+15,7) i -418 (-1926..+1248) µs. Efekt z punktu 1 nie bierze się więc z miary. Suma na serię w uc06 jest pod H0 tak szeroka, jak sam efekt (okresowy slot ~48 ms; R603D, *Granice wniosków*).
3. **Koszt serii na slotach „dotkniętych”** (`est_affected.py`): sloty nakładające się z oknami serii (definicja narażenia R603D) razem ze slotem następnym po każdym oknie, każdy raz na serię, minus to samo w placebo:

| rodzina | C: slotów dotkniętych na serię / Δ mediany [µs] / suma na serię [µs] | C': to samo |
|---|---|---|
| uc03 | 1,0 / +48,00 (+47,37..+48,80) / +51,1 (+48,9..+53,3) | 2,2 / +26,43 (+25,06..+28,00) / +69,7 (+65,3..+74,6) |
| uc05 | 3,4 / +39,80 (+37,58..+42,68) / +161,0 (+151,4..+171,7) | 32,0 / +3,57 (+3,37..+3,78) / +240,8 (+180,4..+305,5) |
| uc06 | 2,3 / +40,27 (+36,55..+45,89) / +127,3 (-522,4..+903,9) | 12,2 / +11,94 (+11,53..+12,43) / +312,6 (-1436,9..+2092,3) |

   - W uc03 drenaż C (0,79 ms) mieści się w przerwie po slocie i w R603D „nie trafia w żaden slot” (O4 C = 0,0), a mimo to slot następny liczy dłużej o +48 µs. **Miara narażenia R603D (K2a, O4) nie widzi skutku po oknie**, więc O4 R603D zaniża koszt C i C' (najbardziej C w uc03). Wyniki R603D na mierze narażenia pozostają poprawne w swojej definicji; ten punkt zmienia tylko ich interpretację jako „kosztu porzucenia”.
4. **Wniosek dla C''.** Skutek porcji to w przeważającej części wyparcie zbioru roboczego slotu ze wspólnego L2 (1 MiB) przez ~256 KiB przeczytanej kolejki, nie rywalizacja w czasie nakładania. Wyrównanie do przerwy po slocie usuwa nakładanie (punkt 1: 0 nakładań), ale nie wyparcie: składnik nakładania to w punkcie 1 różnica ~1,7 µs (uc05), ~0,3 µs (uc06) i ~6,5 µs (uc03) na slot. Jednocześnie bramka wydłuża serię (punkt 5 *Przewidywania*). **Przewidywanie: C'' nie obniży kosztu serii w uc03 i uc05**, a w uc06 miara sumy nie ma rozdzielczości. Granica tego ustalenia: to symulacja kontrfaktyczna na pozycjach porcji C'; w C'' porcje odroczone przez bramkę pójdą w pierwszym obrocie po końcu slotu, więc rozkład ich fazy będzie inny niż w C'. Tę różnicę rozstrzyga dopiero pomiar.

## Aparatura - różnice wobec R603D

1. **`build_ab.sh`**: tylko C'' (`d105498a` + P1), przyrostowo w `~/R376/src` po C', binarki do `~/R376/bin/R603E_Cpp`, `setcap cap_ipc_lock,cap_sys_nice=ep` jak w R603D. **Binarka C'** z R603D bez przebudowy: `~/R376/bin/R603D_Cp` (`xretractor` `e435618b...`, `xqry` `4e8dd234...`), suma sprawdzana przed kampanią. `xqry` C'' będzie się różnić od C' (wspólny `constants.hpp`), protokół klienta bez zmian.
2. **Strony** `Cp` i `Cpp` w `run_one.py` i `campaign.sh` (`BIN_PREFIX`: `R603D_Cp`, `R603E_Cpp`). Katalogi: surowe dane `~/R376/raw_R603E`, aparatura `~/R376/apparatus_R603E`, suchy przebieg `~/R376/dry_R603E`. Śledzone wywołania, bufor ftrace 65 536 kB (aneks 2 R603D) i reguły unieważnienia bez zmian.
3. **Rodziny i liczba par** (D0): uc03, uc05, uc06, po 9 par ABBA, 30 podłączeń; para nieparzysta C', C''; parzysta C'', C'. Razem 54 przebiegi. uc07 i uc08 poza kampanią.
4. **`analyze.py`**: parser R603D importowany bez zmian (okna R_C, pary, oddania z puli, obroty, serie C', model stanu puli, K3, O1-O3, O5) + model bramki, serie C'', miara slotów dotkniętych, K2e, K2s, G2'. Skrypty `est_gate.py`, `est_gate_h0.py`, `est_affected.py` zostają jako zapis *Ustaleń*; `analyze.py` liczy miarę slotów dotkniętych tym samym kodem co `est_affected.py`.
5. **Archiwum** surowych danych jak R603D: w prywatnym `paper-arXiv`, `rdb-experiment-embargo/R603E/`, części po rodzinach, każda z indeksem.

## Okna i zdarzenia

- **Model bramki** (dla obu stron, ze śladu i `slots.csv`): w chwili t opublikowany jest termin `deadline_ns` slotu j = pierwszego slotu z `deadline_ns` > t, o ile slot j-1 skończył się przed t (`deadline_ns + e2e_ns` ≤ t); inaczej opublikowany termin jest w przeszłości. Bramka z rezerwą r jest otwarta w t, gdy termin opublikowany jest w przyszłości i t + r < termin. Chwila decyzji w kodzie wypada kilka µs po wyjściu z `clock_nanosleep` (odbiór kolejki komend, wyszukanie wpisu); obrót, którego start leży w odległości ≤ 20 µs od granicy bramki, jest **obrotem granicznym**, liczonym osobno.
- **Seria drenażu w C''**:
  - **P0** = okno R_C jak w R603D ([wyjście z `kill(pid_klienta, 0)` = -ESRCH, wyjście z `renameat` = 0]). Od rozpoznania porzucenia do P0 mijają obroty z zamkniętą bramką P0 (rezerwa 500 µs); ich liczba to **oczekiwanie P0** (O3).
  - **P1..Pk** = pierwsze k obrotów po obrocie z P0, w których model bramki (rezerwa 200 µs) jest otwarty albo które są setnym kolejnym odroczeniem (limit), z k z pojemności `mmap` (uc03 7, uc05 31, uc06 19, uc07 1, uc08 0). Obroty z zamkniętą bramką między nimi należą do serii, ale nie są oknami.
  - **Koniec serii** = koniec Pk. Serie przepełnienia i zakłócone jak w R603D.
- **Seria w C'** jak w R603D (P0 + k kolejnych obrotów).
- **Slot narażony** jak w R603D: [`deadline_ns` + `wake_lag_ns`, + mediana klasy] przecina okno.
- **Slot następny po oknie** = pierwszy slot z `deadline_ns + wake_lag_ns` > koniec okna.
- **Sloty dotknięte serią** = sloty narażone na którekolwiek okno serii ∪ sloty następne po jej oknach, każdy raz.
- **Koszt serii** S = suma odchyleń (`compute_ns` - mediana klasy) slotów dotkniętych serią minus średnia tej sumy w 20 kopiach placebo serii (przesunięcie o m · H · takt, wszystkie sloty dotknięte kontrolne, ziarno 6034). Klasa `iter mod H` z H z R603D (uc03 8, uc05 40, uc06 5, uc07 10, uc08 12). Sloty kontrolne jak w R603D.

## Przewidywanie przed pomiarem

| rodzina | takt | k | bramka otwarta: porcja / P0 (*Ustalenia*, 1) | seria C' p50 (R603D) | seria C'' (≈ k / f · 1,155 ms) | sloty narażone na serię C' → C'' | S C' (*Ustalenia*, 3) → S C'' |
|---|---|---|---|---|---|---|---|
| uc03 | 5 ms | 7 | 0,90 / 1,00 | 8,42 ms | ~9,0 ms | 0,30 → ~0 | +70 → ~+68 µs |
| uc05 | 1 ms | 31 | 0,65 / 0,50 | 36,25 ms | ~55 ms | 6,5 → ~0 | +241 → ~+200..+300 µs |
| uc06 | 2 ms | 19 | 0,70 / 0,92 | 22,37 ms | ~31 ms (dłużej, gdy seria zastanie okresowy slot ~48 ms) | 3,4 → ~0 | +313 → nierozdzielczo |

1. **Bramka działa jak zaprojektowana**: sloty narażone na serię C'' ~0; nakłada się tylko porcja dłuższa niż rezerwa (p99 127-134 µs, max 556-1347 µs w R603D, czyli < 1 % porcji). Limit odroczeń (100 obrotów ≈ 115 ms) nie zadziała w żadnej rodzinie: najdłuższe zamknięcie to okresowy slot uc06 (~48 ms ≈ 42 obroty).
2. **K2e: ZDANE** w uc05 i uc06.
3. **K2s: NIEZDANE** w uc03 i uc05 (S C'' bliskie S C', daleko od połowy), **NIEROZSTRZYGNIĘTE (miara)** w uc06 (*Ustalenia*, 2).
4. **Δ mediany slotów dotkniętych** (opisowo): C'' bliżej wartości slotu następnego z *Ustaleń*, punkt 1 (uc03 ~+27, uc05 ~+4,3, uc06 ~+11,7 µs) niż zera.
5. **Seria dłuższa**: uc05 ~55 ms zamiast 36 ms (bramka porcji otwarta w ~65 % obrotów), uc06 ~31 ms zamiast 22 ms, uc03 ~9 ms zamiast 8,4 ms. Oczekiwanie P0 w uc05 średnio ~1 obrót (bramka P0 otwarta w ~50 % obrotów).
6. **K1'': ZDANE z warunku (b)**; warunek (a) naruszony częściej niż w C', w proporcji do długości serii: oczekiwane 270 · seria / 2,55 s ≈ 1,0 (uc03), 5,8 (uc05), 3,3 (uc06) na rodzinę, wobec zaobserwowanych w C' 1, 5, 4.
7. **K3: bez regresji.** Bezczynny obrót C'' różni się od C' jednym odczytem atomowym; zegar jest czytany tylko, gdy krok czeka.

## Kryteria (ustalone przed pomiarem)

Dla każdej rodziny i strony, sumarycznie po 9 przebiegach. Bootstrap: 95 % percentylowy po seriach (klaster = seria z jej kopiami placebo), 2000 losowań, ziarno 6035; strony losowane niezależnie.

### K1'' - pula bez regresji (C'')

Jak K1' R603D (kontrola dodatnia, do puli, zero niewyjaśnionych par w fazie pracy, spójność ogona, wyłączenia ≤ 5 %), z jedną zmianą (decyzja człowieka 2026-11-06): **gotowość oceniana warunkiem (b)** - model stanu puli ze śladu (wejście = koniec P0, gotowość = koniec serii, wyjście = oddanie z puli, przepełnienie zwalnia najstarszy wpis, pojemność 2) nie ma ani jednego podłączenia, które utworzyło kolejkę, choć pula miała wpis gotowy, ani oddania z puli bez wpisu gotowego. **Warunek (a) opisowo**: liczba serii niegotowych przed startem następnego klienta wobec liczby oczekiwanej (270 · p50 serii / średni odstęp startów), osobno liczba podłączeń, które utworzyły kolejkę, bo jedyny wpis puli był niegotowy (zdarzenie podłączenia #283, O6). Werdykt C'': ZDANE / NIEZDANE / NIEROZSTRZYGNIĘTE (aparatura) jak w R603D; C' opisowo (powtórzenie R603D, z (b) jako werdyktem).

### K2e - bramka: brak nakładania (C'')

E = średnia liczba slotów narażonych na serię (definicja R603D) w niezakłóconych seriach. **ZDANE**, gdy górna granica E(C'') ≤ 0,2 slotu na serię; **NIEZDANE**, gdy dolna granica > 0,2. Werdykt tylko w rodzinach, w których kontrola dodatnia C' ma E(C') > 1 (z R603D: uc05 6,5, uc06 3,4); w pozostałych opisowo. Uzasadnienie progu: 0,2 to ~1/30 wartości C' w uc05 i ~1/17 w uc06; dopuszcza porcje dłuższe od rezerwy (< 1 %, ~0,3 na serię uc05 przy 31 porcjach) bez dopuszczania braku działania bramki.

### K2s - koszt serii na slotach dotkniętych (kryterium główne)

- Statystyka: T = średnie S(C'') - 0,5 · średnie S(C'), z S z *Okien i zdarzeń*. **ZDANE**, gdy górna granica T < 0 (C'' obniża koszt serii co najmniej o połowę); **NIEZDANE**, gdy dolna granica T > 0; **NIEROZSTRZYGNIĘTE**, gdy przedział zawiera 0. Opisowo: średnie S obu stron, ich różnica i u_S = S(C'') / S(C') z przedziałami.
- **Ważność miary** w rodzinie: kontrola dodatnia - dolna granica S(C') > 0; kontrola H0 - `est_gate_h0.py` w postaci z `analyze.py` (syntetyczne serie C'' na tle slotów kontrolnych C' tej kampanii), półszerokość przedziału sumy na serię ≤ 0,25 · S(C'). Niespełniona = K2s NIEROZSTRZYGNIĘTE (miara) w tej rodzinie (z *Ustaleń*, punkt 2 i 3, przewidywane w uc06).
- **Liczność**: ≥ 50 niezakłóconych serii na stronę.
- Uzasadnienie progu 0,5 (D1): C'' wydłuża serię i zwiększa liczbę naruszeń warunku (a), więc przyjęcie go uzasadnia tylko wyraźne obniżenie kosztu; „jakakolwiek poprawa” (górna granica S(C'') - S(C') < 0) jest alternatywą w D1.

### Opisowo (bez kryterium)

- **K2a R603D** (sloty narażone, δ_c = 5 µs) na obu stronach: przy E(C'') ~0 wynik C'' będzie NIEROZSTRZYGNIĘTY z liczności; podany dla ciągłości z R603D, nie jako kryterium.
- **Δ mediany** odchyleń slotów dotkniętych (C', C'') i osobno slotów następnych po oknach, z placebo.
- **O3** - jak R603D, plus oczekiwanie P0 (obroty od rozpoznania do P0), liczba obrotów z zamkniętą bramką w serii, faza porcji po końcu slotu, liczba kroków wymuszonych limitem odroczeń, obroty graniczne.
- **O4** w postaci R603D (tylko sloty narażone), dla ciągłości.
- **O1, O2, O5** jak R603D; **O6** - podłączenia z kolejką utworzoną przy jedynym wpisie niegotowym.

### K3 - bez regresji poza seriami

Jak R603D (C'' wobec C'): sloty kontrolne, per przebieg `compute_ns` p50, `wake_lag_ns` p99, `e2e_ns` p99; różnica median wobec rozrzutu wewnątrz strony i dokładny permutacyjny MW 9 vs 9. Różnica dodatnia i większa od rozrzutu = regresja C'', osobne znalezisko.

## Kolejność

1. Zatwierdzenie tego protokołu i decyzji D0-D2 przez człowieka; commit i push na gałęzi `experiment/20261106_R603E`.
2. Commit C'' w `retractordb`: `d105498a` na `dev/muro` (2026-11-06, za zgodą człowieka). `build_ab.sh` pobiera źródła z `origin` na GitHubie, więc przed budową człowiek wypycha `dev/muro`.
3. Aparatura (punkt 4 *Aparatury*). **Test parsera**: `analyze.py` na surowych danych R603D daje dla strony C' serie, K1', O3 i K3 identyczne z `results_20261105_R603D/wynik.md`, a miarę slotów dotkniętych identyczną z *Ustaleniami*, punkt 3 (różnica = błąd parsera).
4. Budowa C'', sprawdzenie korpusu (skróty drzew z README R603C) i binarki C', suchy przebieg uc05 i uc03, po 1 przebiegu C' i C'' z 10 podłączeniami (`~/R376/dry_R603E`). **Bramki** (każda niespełniona = decyzja człowieka przed kampanią):
   - **G1** jak R603D (obroty widoczne, `trace_overrun` = 0);
   - **G2'** - model bramki zgodny ze śladem: w niezakłóconych seriach C'' co najmniej 99 % pełnych porcji (obroty P1..Pk-1 wyznaczone modelem, bez granicznych) jest dłuższych niż p99,9 obrotu bezczynnego, i co najmniej 99 % obrotów serii z bramką zamkniętą w modelu nie jest dłuższych niż p99 obrotu bezczynnego; obrót Pk+1 jak G2 R603D. Raport: liczba obrotów granicznych i niezgodnych;
   - **G3** jak R603D (K1'' rozpoznawalne, model stanu puli);
   - **G4** jak R603D (`futex` wątku slotu w ≤ 1 % slotów);
   - **G5** - rozmiar `trace.txt` i archiwum;
   - **H** w postaci z aneksu 1 R603D.
5. Kampania: 3 rodziny × 9 par = 54 przebiegi, ~1,5 h, odczepiona (`setsid nohup`). Przerwana rodzina = powtórzyć całą (ABBA).
6. `wynik.md`, surowe archiwum w `paper-arXiv/rdb-experiment-embargo/R603E/` (wiersz w obu tabelach README), tutaj tylko indeksy sum; komentarz w #603.

## Decyzje (zatwierdzone przez człowieka 2026-11-06: D0-D2 według rekomendacji)

- **D0 - czy i co mierzyć.** Ustalenia przewidują wynik negatywny dla celu C''. Rekomendacja (wybrana): **skrócona kampania na uc03, uc05, uc06** (3 × 9 par = 54 przebiegi, ~1,5 h, plus ~22 min budowy C''): to rodziny, w których K2e i K2s mają moc; sprawdza przewidywanie tam, gdzie da się je obalić, i daje pierwszy bezpośredni pomiar skutku po oknie. uc07 i uc08 (seria mieści się w przerwie po slocie, K2 bez slotów) nie wnoszą nic do K2. Alternatywy: (b) pełne 5 rodzin jak R603D (~2,5 h), dla porównywalności K1'' i K3 we wszystkich rodzinach; (c) bez pomiaru - C'' nie scalać i przejść do zmiany, która zmniejsza ilość danych drenowanych (kierunek 2 z R603D: wcześniejsze rozpoznanie śmierci klienta, ~10 razy mniej komunikatów), mierzonej od razu miarą slotów dotkniętych.
- **D1 - próg K2s.** Rekomendacja (wybrana): obniżenie kosztu serii co najmniej o połowę (T z K2s). Alternatywa: jakakolwiek wykazana poprawa (górna granica S(C'') - S(C') < 0) - łagodniej, ale przy dłuższej serii i większej liczbie naruszeń (a) poprawa o kilka procent nie uzasadniałaby zmiany.
- **D2 - miara „slotów dotkniętych” jako miara główna również w następnych badaniach #603.** Rekomendacja (wybrana): tak; miara narażenia R603D zostaje opisowo dla ciągłości. Uzasadnienie: *Ustalenia*, punkt 3 - bez slotu następnego koszt drenażu jednym ciągiem w uc03 wychodzi 0 zamiast +51 µs na serię.

## Embargo

Korpus `uc01`..`uc08` jest objęty embargiem do publikacji DEBS. W tym katalogu i w komentarzach do zgłoszeń: wyłącznie identyfikatory rodzin i liczby z nich wyprowadzone (pojemności kolejek, H, liczby slotów, czasy). Plany, dane, generatory i nazwy strumieni zostają na workerze w `/dev/shm/r376` i w prywatnym `paper-arXiv`. Surowe CSV i ślady ftrace poza git; zostaje indeks sum. Skrypty `est_*.py` czytają surowe dane R603D z prywatnego archiwum i wypisują tylko liczby wyprowadzone.

## Aparatura i suchy przebieg (2026-11-06)

- **Aparatura** `9d750cd`: `build_ab.sh`, `run_one.py`, `campaign.sh`, `analyze.py`, `P1_deadline_ns.patch` (kopia R603D). Strona C'' przechodzi przez `analyze_run_e`, kopię `analyze_run` R603D, w której zmienia się tylko wybór obrotów P1..Pk; strona C' przez `analyze_run` R603D bez zmian.
- **Test parsera ZDANY** (`analyze.py --raw <R603D>/raw --parser-check`, ~4 min; archiwum R603D rozpakowane od nowa, 5 indeksów zgodnych): (1) wydruk R603D z `analyze_run_e` (wybór C') w miejscu `analyze_run` dla 45 przebiegów C' równy części *Wydruk analizy* `results_20261105_R603D/wynik.md` bajt w bajt (233 wiersze, 0 różnic); (2) miara slotów dotkniętych dla C i C' równa *Ustaleniom*, punkt 3, co do cyfry; (3) odsetki otwartej bramki (porcja / P0) równe *Ustaleniom*, punkt 1.
- **Budowa C''**: `xretractor` `81430762e8cea690...`, `xqry` `da29c97b8666e8e1...`, build-info identyczne z C'. Binarka C' `R603D_Cp` zgodna z sumami R603D. Korpus w `/dev/shm/r376` bez restartu workera; skróty drzew uc03, uc05, uc06 równe README R603C.
- **Suchy przebieg** 11:57-12:01, uc05 i uc03, po 1 przebiegu C' i C'' z 10 podłączeniami (`~/R376/dry_R603E`, `R603E_PAIRS=1 R603E_CONNS=10`). Raport pełny na tych danych przechodzi bez błędu (wartości K2 nieoglądane). Bramki G1, G3, G4, G5 i H spełnione w obu rodzinach; G2 (C') spełnione; **G2' spełnione w uc03, NIESPEŁNIONE w uc05**:
  - uc03: pełne porcje 41/41, obroty zamknięte 6/6, Pk+1 7/7;
  - uc05: pełne porcje > p99,9 bezczynnego 198/199 (0,995), **obroty zamknięte ≤ p99 bezczynnego 157/165 (0,952)**, **Pk+1 ≤ p99 6/7**; P0 zawsze w obrocie z otwartą bramką P0 modelu, 0 kroków wymuszonych, oczekiwanie P0 do 4 obrotów.
  - Rozpoznanie: 8 zamkniętych obrotów ponad p99 (36-53 µs) to nie porcje - pełna porcja trwa ≥ 73 µs, a wszystkie 8 mieści się w p99,9 bezczynnego (71 µs). Bramka w uc05 zamyka się głównie na czas ciężkiego slotu (~1 ms liczenia co 40 ms), kiedy wątek komunikacyjny chodzi wolniej, więc obroty zamknięte są z konstrukcji wzbogacone o ogon rozkładu bezczynnego. Pk+1 = 79 µs w jednej serii to skutek obrotu granicznego: model uznał bramkę za otwartą przy marginesie 0,3-7 µs od `termin - 200 µs`, kod decyduje kilka µs po wyjściu ze snu i zastał ją zamkniętą, więc model kończy serię o obrót za wcześnie (ta sama seria daje jedyną „pełną porcję” 14 µs). Obroty zamknięte na 6 µs przed końcem `e2e` poprzedniego slotu, a mimo to z porcją, to obroty graniczne (termin publikowany kilka µs przed końcem `e2e` w sondzie).
- **Moc kontroli H0 K2s** (przed kampanią, na danych C' R603D, 9 przebiegów na rodzinę, parametry serii H0 z C'): półszerokość przedziału sumy na serię uc03 3,7 µs wobec progu 0,25 · S(C') = 17,4 µs; **uc05 80,3 µs wobec 60,2 µs**; uc06 1918 µs wobec 78,2 µs. Przy kryterium z protokołu K2s wyjdzie więc NIEROZSTRZYGNIĘTE (miara) nie tylko w uc06 (przewidziane), ale prawdopodobnie także w uc05; rozstrzygnięcie zostaje tylko w uc03. Seria C'' (~55 ms, ~28 slotów dotkniętych) zbiera ciężkie sloty klasy, stąd szerzej niż w `est_gate_h0.py` (sam slot następny).

### Do decyzji człowieka przed kampanią

- **A1 - G2' w uc05.** Rekomendacja: aneks zmieniający drugi warunek G2' na „≥ 99 % obrotów zamkniętych (bez granicznych) nie dłuższych niż p99,9 obrotu bezczynnego” (pełna porcja jest powyżej p99,9, więc warunek nadal wykrywa porcję w obrocie zamkniętym), a warunek Pk+1 liczony w seriach bez obrotu granicznego wśród Pk i Pk+1, z serią z granicznym raportowaną osobno; uznanie suchego przebiegu za spełniający po tej zmianie (sprawdzone na suchym przebiegu uc05: obroty zamknięte 165/165; Pk+1 6/6 serii, w siódmej obrót graniczny to sam Pk). Alternatywy: (b) model z chwilą decyzji przesuniętą o stałe δ po wyjściu ze snu, wycenione na suchym przebiegu; (c) G2' bez zmian - kampania nie startuje.
- **A2 - ważność K2s w uc05.** Rekomendacja: aneks - kontrola H0 z pięcioma syntetycznymi seriami na każdą serię C' (zamiast jednej), próg 0,25 · S(C') bez zmian; H0 sprawdza obciążenie estymatora, a jego przedział zwęża się z liczbą losowań (sprawdzone na danych C' R603D: uc05 1108 serii H0, półszerokość 36,3 µs < 60,2 µs; uc06 nadal poza progiem). Alternatywy: (b) bez zmian - K2s rozstrzyga tylko uc03; (c) 18 par w uc05 (+~30 min; półszerokość ~57 µs, na granicy).

## Aneksy

(brak)
