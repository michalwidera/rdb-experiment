# R607 - sonda życia subskrybentów rozłożona na obroty wątku komunikacyjnego (D2r) wobec sondy w jednym obrocie (D2s) (pi400, `--realtime`)

Zgłoszenie: michalwidera/retractordb#607, plan z komentarza 6703950024 (zatwierdzony 2026-11-07), punkt P6. Ten plik zapisano PRZED pomiarem i przed budową aparatury. Po zatwierdzeniu przez człowieka zmiany protokołu trafiają do sekcji *Aneksy* z datą i powodem, nie do treści powyżej.

**Stan: zatwierdzony przez człowieka 2026-11-07** (decyzje J0-J4 według rekomendacji, *Decyzje*).

Aparatura pochodzi z R603G (`results_20261106_R603G/`, scalenie do `main` `d0f81eb`), a przez nią z R603F, R603E, R603D, R603C i R600. Opis tego, co się nie zmienia, jest w ich README, łącznie z aneksami A1-A5 R603G (przypięcie wątku komunikacyjnego, granice okna, bramki W3 i W4). Poniżej są tylko różnice i nowe kryteria.

## Pytanie

R603G zmierzyło, że przebieg sondy D2s wykonuje N razy `inspectProcess` w jednym obrocie wątku komunikacyjnego i wydłuża ten obrót o ~48 + 72·N µs (K4 NIEZDANE przy N = 16: p99 1352 µs). D2r (#607) w jednym obrocie wywołuje najwyżej jedno `inspectProcess` i przechodzi listę obserwowanych przez N kolejnych obrotów. Pytania:

1. Czy wydłużenie obrotu z sondą nie zależy od N i ma p99 ≤ 1 ms przy N = 16 (K4, K4n)?
2. Czy śmierć klienta jest nadal wykrywana przez sondę w granicy z planu P1, L ≤ interwał + N · T_obrotu (K0)?
3. Czy przy tym samym N strona D2r nie jest gorsza od D2s poza przebiegami sondy: w wątku slotu (K3) i w obrocie bezczynnym wątku komunikacyjnego (K3t)?
4. Opisowo, ryzyko nazwane w planie (P6): sonda dotyka teraz N obrotów na sekundę zamiast jednego. Czy koszt przebiegu sondy na slotach, które dotyka (K3p z R603G), rośnie przez to ~N razy?

## Strony porównania

| Strona | Rewizja silnika | Binarka na workerze | Wątek komunikacyjny przy N żywych subskrybentach |
|---|---|---|---|
| D2s (`D2s`) | `75e7574cf90d7548b1d95c7cef5a80e9b5700f91` | `~/R376/bin/R603F_D2s`, `xretractor` `7c02c52c...`, bez przebudowy | co 1 s jeden obrót z N wywołaniami `inspectProcess`; w pozostałych obrotach `steady_clock::now()` i porównanie z `nextProbe_` |
| D2r (`D2r`) | `4daec944e8d76c9e95ccdea8f0e43074c5460613` (`dev/muro`, na `origin`) | `~/R376/bin/R607_D2r`, budowa jak R603F (`build_ab.sh`) | co 1 s początek przebiegu; w nim N kolejnych obrotów z jednym `inspectProcess` każdy i jeden obrót zamykający (`upper_bound` daje koniec listy, bez wywołania systemowego); między przebiegami jak D2s |

- **D2r = `4daec944`** zmienia wobec `75e7574c` tylko `src/retractor/lib/ipcServer.{hpp,cpp}` (`probeSubscribers`, pola `probeRunning_` i `probeLast_`), komentarz w `src/include/constants.hpp` i `test/UnitTest/test_ipcServer.cpp`. Wątek slotu, `src/qry`, `src/common` i `src/rdb/lib/probe.cc` są bez zmian, a `kClientLivenessProbeInterval` zostaje równe 1 s.
- Obie strony mają łatkę P1 (`deadline_ns`, `results_20261106_R603F/P1_deadline_ns.patch` bez zmian). Build-info D2r ma być równe D2s. Sumy sprawdza `campaign.sh`.
- **Klient:** `xqry` C' (`~/R376/bin/R603D_Cp`, `4e8dd234...`) po obu stronach, jak G3 R603G. Między `e0857dc8` a `4daec944` źródła klienta się nie zmieniają.
- **Strony C' nie ma.** Odniesieniem wszystkich kryteriów jest D2s. Strona D2s powtarza przy okazji stronę D2s R603G (ta sama binarka, ta sama aparatura), co daje kontrolę odtwarzalności (opisowo).

## Ustalenia przed pomiarem (2026-11-07, z kodu `4daec944` i danych R603G)

1. **Przebieg sondy D2r.** Pierwszy obrót z `now ≥ nextProbe_` ustawia `nextProbe_ = now + 1 s`, zaczyna przebieg i sprawdza pierwszego klienta. Każdy następny obrót sprawdza klienta o najmniejszym identyfikatorze (PID) większym od ostatnio sprawdzonego. Obrót, w którym za ostatnim nie ma wpisu, kończy przebieg bez `inspectProcess`. Przebieg przy N klientach to więc N obrotów z jednym udanym `openat` każdy, a po nich jeden obrót zamykający. W śladzie: N kolejnych obrotów wątku komunikacyjnego z dokładnie jednym udanym `openat`, a między przebiegami obroty bez `openat`. W oknie pomiaru nie ma podłączeń ani zgonów, więc innych `openat` nie ma (R603G, *Okna i zdarzenia*).
2. **Przy N = 1 strony różnią się tylko obrotem zamykającym.** Obrót z sondą wykonuje w obu ten sam kod (`inspectProcess` jednego klienta). N = 1 jest więc kontrolą wewnętrzną: E_p D2r ≈ E_p D2s.
3. **Granica wykrycia zgonu.**
   - Plan P1 deklaruje L ≤ interwał + N · T_obrotu. To granica z najgorszego przypadku: klient dopisany przed kursorem przesuwa pozostałych o jeden obrót w następnym przebiegu.
   - Przy samych usunięciach (faza zgonów tego badania, *Obciążenie i przebieg*) pozycja klienta w przebiegu może tylko zmaleć. Odstęp między dwoma sprawdzeniami jednego klienta wynosi wtedy co najwyżej interwał + jeden obrót, tak jak w D2s. Przewidywane L max jest więc takie jak w D2s (R603F: ≤ 998,8 ms), mimo że kryterium K0 bierze granicę z P1.
   - Przypadek z dopisaniem klienta przed kursorem w trakcie przebiegu sprawdza tylko test jednostkowy `probe_round_survives_removal_and_insertion_of_watched_clients` (*Granice wniosków*).
4. **Wzorzec wykrycia w śladzie bez zmian wobec R603F** (*Ustalenia*, punkt 1 R603F): `openat` -ENOENT i `kill(pid, 0)` -ESRCH z `probeSubscribers`, w tym samym obrocie druga taka para z `poolAbandonedQueue`, potem P0 i `renameat`. W D2s w tym samym obrocie są jeszcze udane `openat` pozostałych N - 1 klientów, a w D2r nie ma ich wcale.
5. **K3p dotyka teraz innej jednostki.** W R603G jednostką był przebieg sondy, czyli jeden obrót. W D2r przebieg to N kolejnych obrotów (~N · 1,1 ms, przy N = 16 ~18 slotów uc05). Koszt na przebieg jest w obu stronach kosztem na sekundę, więc porównanie na przebieg odpowiada na pytanie 4 bez przeliczeń.
   - Przy N = 1 R603G zmierzyło S_p = +15,8 µs, przy N = 16 -5,5 µs, a mechanizm jest nieznany (R603G, *Odstępstwa*, punkt 4).
   - Jeśli koszt jest związany z obrotem, w którym jest `inspectProcess`, to w D2r przy N = 16 wyniesie ~16 · 16 = ~250 µs na sekundę. Jeśli z przebiegiem jako całością (hipoteza (a) R603G: wyparcie zwykłych obrotów), zostanie rzędu R603G.
6. **Koszt fazy zgonów.** Kolejka martwego klienta ma ≤ ~1 s wierszy (~800 komunikatów uc05), więc zwolnienie to P0 i 2-3 porcje, jak w R603F. Faza leży poza oknem pomiaru i nie wchodzi do K4, K3, K3t ani K3p.

## Obciążenie i przebieg

Rodzina **uc05**, N ∈ {1, 8, 16}, aparatura R603G po aneksach A1-A4 (J0). Jeden przebieg (`run_one.py`):

1. Rozgrzewka, przypięcie wątku komunikacyjnego do rdzenia 0 (`sudo -n taskset -pc 0`), N podłączeń `xqry -s` bez `-m` na rdzeniach 1-2, ustalenie 5 s. Bez zmian wobec R603G.
2. **Okno pomiaru W = 60 s** jak R603G: ślad (ten sam zbiór wywołań, filtry i bufor), wiersze klientów na obu końcach, `/proc/stat` rdzeni 0-2, `t0` po `tracing_on=1`, `t1` przed `tracing_on=0`.
3. **Faza zgonów** (nowa, J1). Po zatrzymaniu śladu okna i policzeniu wierszy runner zapisuje bufor, włącza ślad ponownie (ten sam zbiór wywołań, osobny plik `trace_death.txt`) i zabija klientów po kolei w losowej kolejności (ziarno z numeru pary i N). Przed każdym zabiciem czeka U(1,0; 2,0) s, potem SIGKILL i `wait`. Koniec klienta `end_ns` to CLOCK_MONOTONIC po `wait`, jak w `conns.tsv` R603F. Po ostatnim zabiciu czeka 2 s i zatrzymuje ślad. Wynik: `deaths.tsv` (i, pid, kill_ns, end_ns, liczba żywych klientów przed zabiciem). Trwa ~1,5 · N + 2 s.
4. Koniec: SIGTERM silnika, przeniesienie `slots.csv`, sprawdzenie pozostałości w `/dev/shm` (pozostałość przerywa kampanię). SIGINT do klientów odpada, bo wszyscy zginęli w fazie zgonów (R603G, *Odstępstwa*, punkt 1).

Przebieg trwa ~2,9 min przy N = 16 (R603G) plus ~26 s fazy zgonów.

**Kampania** (`campaign.sh`): 9 par ABBA na każde N, 54 przebiegi. W parze p kolejność N jest rotowana jak w R603G, strony idą D2s, D2r w parze nieparzystej i D2r, D2s w parzystej. Czas ~2,1 h (R603G 1,85 h plus ~13 min faz zgonów).

## Okna i zdarzenia

- **Obrót wątku komunikacyjnego**, **obrót bezczynny**, **nadwyżka E_p** = długość obrotu - mediana obrotu bezczynnego tego przebiegu: jak R603G.
- **Obrót z sondą**: obrót z co najmniej jednym udanym `openat` wątku komunikacyjnego w oknie pomiaru. Na D2s ma ich N, na D2r jeden (*Ustalenia*, punkt 1). Obrót zamykający D2r nie ma `openat` i jest obrotem bezczynnym.
- **Przebieg sondy**: na D2s obrót z sondą, na D2r ciąg kolejnych obrotów z sondą. Okno przebiegu = [początek pierwszego, koniec ostatniego obrotu z sondą].
- **Sloty dotknięte przez przebieg**, placebo i model klasy slotu (H = 40): jak R603G, z oknem przebiegu z punktu wyżej.
- **Sloty kontrolne**: sloty okna pomiaru bez slotów dotkniętych przez którykolwiek przebieg sondy i bez 2 slotów przed i po każdym z nich (aneks A1 R603G), na obu stronach.
- **Wykrycie zgonu** (faza zgonów, obie strony): wzorzec z *Ustaleń*, punkt 4, dla PID-u zabitego klienta. t_det = wyjście z pierwszego `kill(pid, 0)`, jak R603F. **L** = t_det - `end_ns`. Porzucenie z pełnej kolejki: zwolnienie kolejki zabitego klienta bez wykrycia przez sondę.

## Kryteria (ustalone przed pomiarem)

Dla każdego N osobno, sumarycznie po 9 przebiegach strony. Bootstrap: 95 % percentylowy, 2000 losowań, ziarna jak R603G (placebo 6034, bootstrap 6035, H0 6036), dla K4n klaster = przebieg. Ważność przebiegu: bramki W1-W5 (*Kolejność*). **Liczność**: ≥ 8 ważnych przebiegów na stronę i N, inaczej NIEROZSTRZYGNIĘTE (liczność).

### K4 - obrót z sondą przy N = 16 (kryterium główne, D2r)

**ZDANE**, gdy przy N = 16 p99 nadwyżki E_p obrotów z sondą D2r ≤ 1 ms (`kQueuePollInterval`, jak R603G). **NIEZDANE** w przeciwnym przypadku. Opisowo dla każdego N i obu stron: E_p p50 / p99 / max, liczba obrotów z sondą i przebiegów na przebieg (oczekiwane D2r: N · W ± N i W ± 1), odstęp początków przebiegów.

### K4n - niezależność od N (D2r)

Nachylenie prostej najmniejszych kwadratów median E_p przebiegów D2r (27 przebiegów, po 9 przy każdym N) względem N, przedział bootstrap po przebiegach losowanych wewnątrz N. **ZDANE**, gdy górna granica < δ_n = 5 µs na subskrybenta. **NIEZDANE**, gdy dolna granica > δ_n. **NIEROZSTRZYGNIĘTE** w pozostałych przypadkach. δ_n to 7 % nachylenia D2s z R603G (71,5 µs): przy N = 16 dopuszcza ~75 µs wzrostu wobec ~1070 µs w D2s. Opisowo: to samo nachylenie dla p99 i dla strony D2s tej kampanii.

### K0 - wykrycie zgonu w granicy P1 (faza zgonów, obie strony)

**ZDANE**, gdy na D2r każdy klient zabity w fazie zgonów ma wykrycie przez sondę z -5 ms ≤ L ≤ 1,010 s + N · 1,5 ms (1,0115 / 1,022 / 1,034 s przy N = 1 / 8 / 16), nie ma porzuceń z pełnej kolejki, a na D2s każdy zabity klient ma wykrycie z -5 ms ≤ L ≤ 1,010 s (granica K0 R603F; kontrola, że faza zgonów mierzy to samo co R603F). **NIEZDANE** w każdym innym przypadku.

- 1,010 s to granica K0 R603F (interwał + obrót + margines odczytu `end_ns`). 1,5 ms to górna granica obrotu: sen 1 ms plus obrót z sondą (R603G przy N = 1: p99 201 µs).
- Opisowo: rozkład L obu stron (min / p50 / p99 / max), L max wobec 1,010 s (*Ustalenia*, punkt 3), L wobec pozycji zabitego klienta w przebiegu (ranga PID-u wśród obserwowanych), czas obrotu z wykryciem, liczba komunikatów w zwolnionej kolejce i porcje.

### K3 - wątek slotu poza przebiegami sondy, D2r wobec D2s przy tym samym N

Jak K3 R603G ze stroną D2s w miejscu C': sloty kontrolne, per przebieg `compute_ns` p50, `wake_lag_ns` p99, `e2e_ns` p99. d = mediana D2r - mediana D2s, rozrzut = większy z zakresów wewnątrz strony, dokładny permutacyjny MW 9 vs 9 (opisowo). **REGRESJA D2r**, gdy d > max(rozrzut, δ), δ = 5 % mediany D2s tej miary i tego N. Poza tym bez regresji.

### K3t - obrót bezczynny, D2r wobec D2s przy tym samym N

Jak K3t R603G: per przebieg średnia obrotu bezczynnego obcięta do p99, **REGRESJA D2r**, gdy d > max(rozrzut, δ_t), δ_t = 0,5 µs. p50 i p99 opisowo regułą R603F.

### Opisowo (bez kryterium)

- **K3p na przebieg sondy (pytanie 4, J3).** S = średnia po przebiegach sondy z (suma odchyleń `compute_ns` slotów dotkniętych od mediany klasy) - (średnia tej sumy po kopiach placebo), jak S_p R603G, osobno dla D2r (przebieg = N obrotów) i D2s, oraz różnica S(D2r) - S(D2s) z przedziałem (strony losowane niezależnie). Kontrola miary H0: okna syntetyczne o długościach przebiegów D2r tego samego N na przebiegach D2s, z początkiem nie bliżej niż 3 sloty od przebiegu sondy D2s, 5 zestawów na przebieg, półszerokość raportowana. Reguła odczytu ustalona przed pomiarem: **ryzyko z planu potwierdzone**, gdy dolna granica S(D2r) - S(D2s) > 10 µs na sekundę (δ_S R603G); **wykluczone**, gdy górna granica < 10 µs; inaczej nierozstrzygnięte. Opisowo także Δ mediany slotów dotkniętych i sloty dotknięte na przebieg.
- **Odtwarzalność R603G** na stronie D2s: E_p p50 / p99, S_p i obrót bezczynny wobec kolumny D2s *Wydruku analizy* R603G.
- Obciążenie jak R603G: `compute_ns` p50 i e2e p99 wszystkich slotów okna, zajętość rdzeni 0-2, `VmLck`, wiersze/s klientów, O1.

## Przewidywanie przed pomiarem

| N | E_p p50 / p99 D2s [µs] | E_p p50 / p99 D2r [µs] | K4 | K4n | K0: L max D2s / D2r [s] | K3 | K3t d [µs] | S(D2r) - S(D2s) [µs/s] |
|---|---|---|---|---|---|---|---|---|
| 1 | ~124 / ~187 | ~124 / ~190 | - | - | ≤ 1,002 / ≤ 1,002 | bez regresji | ~0 | ~0 |
| 8 | ~612 / ~743 | ~120-150 / ≤ 250 | - | - | ≤ 1,002 / ≤ 1,002 | bez regresji | ~0 | nieprzewidywane: ~0..+120 |
| 16 | ~1197 / ~1352 | ~120-150 / ≤ 250 | ZDANE | ZDANE (nachylenie ~0-3 µs) | ≤ 1,002 / ≤ 1,002 | bez regresji | ~0 | nieprzewidywane: ~0..+250 |

1. **K4: ZDANE z zapasem ~4×.** Każdy obrót z sondą D2r wykonuje jedno `inspectProcess` po śnie 1 ms, czyli to samo co obrót z sondą D2s przy N = 1 (R603G: 124 / 187 µs). Przy większym N może dojść kilka-kilkanaście µs z presji na wspólne L2 (obrót bezczynny w R603G wydłużał się z N o ~2,5 µs).
2. **K4n: ZDANE.** Przewidywane nachylenie 0-3 µs na subskrybenta.
3. **K0: ZDANE.** Na obu stronach L ~U(0; 1 s), p50 ~0,5 s. L max ≤ ~1,002 s także na D2r, bo w fazie zgonów są same usunięcia (*Ustalenia*, punkt 3). Granica P1 (1,034 s przy N = 16) ma więc zapas ~30 ms. 0 porzuceń z pełnej kolejki.
4. **K3: bez regresji.** Wątek slotu bez zmian w kodzie. Na D2r slotów kontrolnych jest mniej (przy N = 16 ~22 sloty na sekundę wyłączone zamiast ~6), ale nadal ~97 %.
5. **K3t: bez regresji, d ≈ 0.** Między przebiegami obrót jest w obu stronach ten sam. Obrót zamykający D2r (raz na sekundę) nie przesuwa średniej obciętej.
6. **K3p: przewidywania brak.** Wynik rozstrzyga między dwiema możliwościami z *Ustaleń*, punkt 5: koszt na obrót z `inspectProcess` (wtedy ~N · 16 µs na sekundę, przy N = 16 ~250 µs, ryzyko potwierdzone) albo na przebieg (wtedy ~0, ryzyko wykluczone). W obu przypadkach to ≤ ~0,25 ms czasu wątku slotu na sekundę.
7. **Odtwarzalność R603G:** E_p D2s w ±10 % wartości R603G.

## Kolejność

1. Zatwierdzenie protokołu przez człowieka; commit i push na gałęzi `experiment/20261107_R607`.
2. **Aparatura** (*Aparatura*). Test analizy:
   - (1) na danych R603G (archiwum `rdb-experiment-embargo/R603G/` rozpakowane od nowa, 3 indeksy zgodne) ścieżka strony D2s daje kolumnę D2s *Wydruku analizy* R603G bez różnic (E_p, obrót bezczynny, sloty kontrolne, S_p, H0 tylko w wierszach, które nie zależą od strony C');
   - (2) na danych R603F (archiwum `rdb-experiment-embargo/R603F/`) rozpoznanie wykrycia z fazy zgonów daje wiersze K0 D2s *Wydruku analizy* R603F (270 / 270 / 266 wykryć, L min / p50 / p99 / max);
   - (3) rozpoznanie przebiegu D2r na danych D2s R603G przy N = 1 daje 60 przebiegów po jednym obrocie, a przy N = 8 i 16 0 przebiegów D2r (obrót z N udanymi `openat` nie jest obrotem D2r).
3. **Budowa D2r** (`4daec944` + P1, przyrostowo w `~/R376/src`, ~22 min, odczepiona, bez łączenia się z workerem w trakcie), sumy do `R607_D2r.sha256`, build-info równe D2s. **Suchy przebieg** uc05: po 1 przebiegu D2s i D2r przy N = 16 i N = 1 (4 przebiegi, ~13 min, `~/R376/dry_R607`), odczepiony. Bramki (każda niespełniona = decyzja człowieka przed kampanią; w kampanii decydują o ważności przebiegu):
   - **W1-W3** jak R603G po aneksach A3 i A4;
   - **W4** - identyfikacja sondy: na D2s jak R603G (przebieg = obrót z dokładnie N udanymi `openat`, W ± 1 przebiegów, odstęp 1,000-1,010 s); na D2r każdy obrót z sondą ma dokładnie 1 udany `openat` i 0 nieudanych, obroty z sondą tworzą przebiegi po dokładnie N kolejnych obrotów, przebiegów jest W ± 1, odstęp ich początków 1,000-1,010 s;
   - **W5** - faza zgonów: wszyscy N klienci zabici i zebrani, `trace_overrun` = 0 w `trace_death.txt`, silnik żyje do SIGTERM i kończy się kodem 0;
   - opisowo: E_p, L, wstępna półszerokość H0 K3p.
4. Kampania: 54 przebiegi, ~2,1 h, `setsid nohup ./campaign.sh > ~/R376/campaign_R607.log 2>&1 < /dev/null &`. **Do jej oczekiwanego końca nie łączyć się z workerem**; oczekiwanie liczy lokalny zegar, log sprawdza jedno logowanie po ~2,2 h. Przebieg nieważny wg W1-W5 jest raportowany i nie jest powtarzany (liczność ≥ 8).
5. `wynik.md`, surowe dane do `paper-arXiv/rdb-experiment-embargo/R607/` (części po N, wiersz w obu tabelach README), tutaj tylko indeksy sum; komentarz w #607, odznaczenie punktów P6 w komentarzu planu 6703950024.

## Aparatura - różnice wobec R603G

1. **`build_ab.sh`** z R603F: rewizja `4daec944` z `origin`, ta sama łatka P1, wyjście `~/R376/bin/R607_D2r`, `setcap cap_ipc_lock,cap_sys_nice=ep`. Binarka D2s bez przebudowy, suma sprawdzana przed kampanią.
2. **`run_one.py`** (na bazie R603G): strony `D2s` / `D2r` (`R603F_D2s` / `R607_D2r`), `xqry` z `R603D_Cp` po obu stronach, faza zgonów zamiast SIGINT (punkt 3 *Obciążenia i przebiegu*), nowe pliki `trace_death.txt` i `deaths.tsv`.
3. **`campaign.sh`**: jak R603G, zmienne `R607_PAIRS`, `R607_NS`, `R607_RAW`, katalog `~/R376/raw_R607/uc05/N<n>/<strona>_<para>`.
4. **`analyze.py`**: importuje `results_20261106_R603G/analyze.py` (a przez niego R603F i wcześniejsze) bez zmian. Dochodzi: przebieg sondy D2r jako ciąg obrotów, K4n, K0 z fazy zgonów (rozpoznanie wykrycia z `kill_windows_f` R603F), K3 i K3t ze stroną D2s jako odniesieniem, K3p na przebieg z H0 na D2s i regułą odczytu ryzyka, bramki W4 i W5 (`--gates`).
5. **Archiwum** jak R603G: `rdb-experiment-embargo/R607/`, części po N, każda z indeksem; tutaj tylko indeksy.

## Decyzje (zatwierdzone przez człowieka 2026-11-07: J0-J4 według rekomendacji)

- **J0 - rodzina, N, liczba par, aparatura.** Rekomendacja: uc05, N ∈ {1, 8, 16}, 9 par ABBA na N (54 przebiegi), aparatura R603G po aneksach A1-A4 (wątek komunikacyjny sam na rdzeniu 0). Tak mówi kryterium #607 i tylko tak wynik jest porównywalny z R603G. Alternatywa: dołożyć N = 32 bez przypięcia jako opis wdrożenia na nasyconym workerze (+~0,5 h; R603G, suchy przebieg 1: przebieg sondy D2s 65 ms przy N = 32).
- **J1 - pomiar K0.** Rekomendacja: faza zgonów po oknie pomiaru, wszyscy N klienci zabici po kolei (SIGKILL, przerwy U(1; 2) s). Daje 9 / 72 / 144 wykryć na stronę przy N = 1 / 8 / 16 i nie zakłóca okna pomiaru. Alternatywy: (b) krótkie podłączenia jak R603F na tle N długo żyjących klientów w osobnych przebiegach (+~1,5 h; obejmuje też dopisanie przed kursorem, ale miesza podłączenia z przebiegami sondy); (c) zabicie tylko min(N, 4) klientów (krótsza kampania, mniej wykryć przy N = 16).
- **J2 - progi.** Rekomendacja: K4 p99 E_p ≤ 1 ms przy N = 16 (z #607), K4n δ_n = 5 µs na subskrybenta, K0 1,010 s + N · 1,5 ms (granica P1 z marginesem) i 1,010 s na D2s, K3 δ = 5 % mediany D2s, K3t δ_t = 0,5 µs (jak R603G). Alternatywy: K4n jako stosunek median E_p(16) / E_p(1) ≤ 1,25; K0 na D2r z granicą 1,010 s (tę przewiduje *Ustalenie* 3, ale kod jej nie gwarantuje).
- **J3 - K3p.** Rekomendacja: opisowo z regułą odczytu ryzyka ustaloną przed pomiarem (*Opisowo*). Kryterium #607 to K3, a mechanizm K3p jest nieznany (R603G, *Odstępstwa*, punkt 4). Alternatywa: K3p jako kryterium (S(D2r) - S(D2s) < 10 µs na sekundę), którego niezdanie wymagałoby decyzji przed scaleniem.
- **J4 - binarki.** Rekomendacja: D2s bez przebudowy (`R603F_D2s`), D2r budowana z `4daec944` + P1, `xqry` C' po obu stronach. Alternatywa: przebudować obie strony w jednym `build_ab.sh` (takie same warunki budowy, +~22 min; R603F i R603G pokazały równe build-info bez tego).

## Granice wniosków (znane przed pomiarem)

- Jedna platforma (Cortex-A72, wspólne L2 1 MiB, jądro `PREEMPT_RT`), jedna rodzina (uc05), N ≤ 16. Większe N tylko przez ekstrapolację K4n i granicę P1.
- Wątek komunikacyjny przypięty sam do rdzenia 0. We wdrożeniu bez przypięcia każdy obrót z sondą płaci udział w CFS, ale jeden `inspectProcess`, a nie N.
- Faza zgonów ma same usunięcia z listy obserwowanych. Dopisanie klienta w trakcie przebiegu (przed i za kursorem) sprawdza tylko test jednostkowy, a granica P1 dla tego przypadku nie jest zmierzona.
- Zgon tylko przez SIGKILL klienta na tym samym workerze i w tej samej przestrzeni PID. Klient w innej przestrzeni PID nie jest obserwowany (R603G, *Ustalenia*, punkt 1).
- K3p bez kontroli dodatniej; rozdzielczość = półszerokość H0. Mechanizm K3p nadal nieznany; to badanie rozróżnia tylko koszt na obrót od kosztu na przebieg.
- Tańszy `inspectProcess` (P4) jest poza zakresem: koszt jednego obrotu z sondą zostaje ~120 µs.

## Embargo

Korpus `uc01`..`uc08` jest objęty embargiem do publikacji DEBS. W tym katalogu i w komentarzach do zgłoszeń są wyłącznie identyfikatory rodzin i liczby z nich wyprowadzone. Plany, dane, generatory, nazwy strumieni i wyjście klientów zostają na workerze w `/dev/shm/r376`, a surowe CSV i ślady w prywatnym `paper-arXiv` (`rdb-experiment-embargo/R607/`). Tutaj zostaje indeks sum.

## Aparatura i suchy przebieg (2026-11-07)

- **Aparatura** (`2519dba`): `build_ab.sh`, `run_one.py`, `campaign.sh`, `analyze.py` (importuje `results_20261106_R603G/analyze.py` bez zmian). Łatka P1 nakłada się na `4daec944` bez zmian (`git apply --check`); `src/qry`, `src/common` i `src/rdb` są między `75e7574c` a `4daec944` identyczne.
  - Przebieg D2r przecięty granicą okna (zaczęty przed `t0` albo kończony po `t1`) ma mniej niż N obrotów. W4 dopuszcza taki przebieg tylko na granicy okna, a K3p go pomija. Odstęp W4 liczy się od początków przebiegów bez przebiegu przeciętego na początku okna. To doprecyzowanie W4 z *Kolejności*, punkt 3, bez zmiany kryterium.
  - Klient zabity w fazie zgonów, którego kolejkę zwolniono bez wykrycia przez sondę (np. martwy muteks, R603F), albo którego zwolnienia nie ma w śladzie, jest w K0 liczony jako niezgodny z kryterium i raportowany osobno.
- **Test analizy ZDANY** (`analyze.py --raw <R603G>/raw --r603f <R603F>/raw --parser-check`, ~24 s; archiwa `rdb-experiment-embargo/R603G/` i `R603F/` rozpakowane od nowa, 6 indeksów zgodnych, 432 + 324 pliki):
  - (1) `analyze_run` R607 na przebiegach D2s R603G daje te same pola (obroty z sondą, E_p, obroty bezczynne, odstępy, sloty kontrolne, średnia obcięta, K3, bramki) i te same klastry placebo co `analyze_run` R603G. E_p 124,0 / 187,0 / 218,0, 612,0 / 743,0 / 765,0 i 1197,0 / 1352,0 / 1920,0 µs, obrót bezczynny i S_p przy N = 1 (+15,81 (+10,83..+21,25) µs) są równe *Wydrukowi analizy* R603G;
  - (2) rozpoznanie wykrycia na przebiegach D2s R603F daje 270 / 270 / 266 wykryć, 0 / 0 / 1 samotnych i L min / p50 / p99 / max równe *Wydrukowi analizy* R603F w uc03, uc05 i uc06;
  - (3) przebieg D2r wymuszony na danych D2s R603G: przy N = 1 po 60 przebiegów z jednym obrotem, przy N = 8 i 16 0 obrotów z jednym udanym `openat`.
- **Korpus**: worker po restarcie (uptime 55 min o 09:18), `/dev/shm` pusty. uc05 odtworzony procedurą R600 (`paper-arXiv` HEAD `3929c57`, ostatnia zmiana `usecases` w `7a76922`); skrót drzewa `ce892219...`, równy README R603C.
- **Budowa D2r** 09:19-09:40, odczepiona (`~/R376/build_R607.log`): `xretractor` `3b944eb00f53928d...`, `xqry` `ddd7288e9b9e3250...`, build-info równe D2s. W trakcie budowy jedno logowanie na worker (lista plików aparatury), poza pomiarem.
- **Suchy przebieg** 09:40-09:47 (`~/R376/dry_R607`, `campaign.sh` z `R607_PAIRS=1`, `R607_NS="16 1"`; uc05, po 1 przebiegu D2s i D2r przy N = 16 i N = 1, okno 60 s), odczepiony, bez łączenia się z workerem w trakcie. **W1-W5 spełnione we wszystkich 4 przebiegach.** Po przebiegu w `/dev/shm` tylko korpus.
  - D2r: 60 przebiegów sondy, przy N = 16 każdy z dokładnie 16 kolejnych obrotów z jednym udanym `openat`, 0 przeciętych granicą okna, odstęp początków 1000,4-1001,1 ms. Przebieg sondy trwa p50 18,8 ms.
  - E_p p50 / p99 / max: N = 1 D2s 125 / 185 / 185, D2r 124 / 178 / 178 µs; N = 16 D2s 1209 / 1370 / 1370, **D2r 136 / 229 / 299 µs**.
  - Obrót bezczynny p50 / p99 / p99,9: N = 16 D2s 17 / 20 / 77, D2r 17 / 25 / 94 µs; średnia obcięta 16,82 / 17,53 µs (jeden przebieg na stronę, bez wniosku). Zajętość rdzeni 0-2 0,68 przy N = 16.
  - K0: wszyscy zabici klienci wykryci przez sondę w granicy, kody wyjścia -9, `trace_overrun` faz zgonów 0, silnik kończy się kodem 0. L min / p50 / max przy N = 16: D2s 91 / 510 / 966 ms, D2r 30 / 472 / 951 ms; przy N = 1 920 ms (D2s) i 890 ms (D2r).
  - Sloty kontrolne przy N = 16: D2s 59 632, D2r 58 570 z ~60 014 (97,6 %, *Przewidywanie*, punkt 4).
  - Wstępnie K3p (jeden przebieg na stronę): N = 1 S D2s +11,7, D2r +16,5 µs, półszerokość H0 6,7 µs; N = 16 S D2s -3,0, D2r -56,8 (-137,8..+24,8) µs, półszerokość H0 34,8 µs. Przy 9 przebiegach oczekiwana półszerokość H0 przy N = 16 to ~12 µs, więc reguła odczytu ryzyka (10 µs na sekundę) może dać „nierozstrzygnięte” z rozdzielczości.
  - Przebieg trwał ~2,0 min przy N = 16 i ~1,3 min przy N = 1, więc kampania potrwa ~1,6 h, a nie ~2,1 h.

### Do decyzji człowieka przed analizą (kampania uruchomiona, dane od niej nie zależą; rozstrzygnięte: *Aneksy*)

- **A1 - przebieg D2r przecięty granicą okna** (punkt pierwszy tej sekcji). Litera W4 („przebiegi po dokładnie N kolejnych obrotów”) unieważniłaby przebieg, w którym okno zaczyna się albo kończy w trakcie przebiegu sondy. Przy N = 16 przebieg sondy trwa ~19 ms, więc dotyczy to ~4 % przebiegów D2r (w suchym przebiegu 0). Rekomendacja: przebieg przecięty dopuszczalny tylko na granicy okna, pominięty w K3p i w odstępach W4, jego obroty liczone w E_p. Alternatywa: litera W4, przebieg nieważny (liczność ≥ 8 zostaje przy jednym takim przebiegu na N). Raport podaje liczbę przebiegów przeciętych.

## Aneksy

1. **A1 - przebieg D2r przecięty granicą okna** (zatwierdzony przez człowieka 2026-11-07, w trakcie kampanii, przed analizą; dane kampanii od tej decyzji nie zależą). W4 na D2r dopuszcza przebieg sondy krótszy niż N obrotów wyłącznie wtedy, gdy zaczyna się na pierwszym albo kończy na ostatnim obrocie okna pomiaru. Taki przebieg jest pomijany w K3p i w odstępach W4, a jego obroty wchodzą do E_p (K4, K4n). Raport podaje liczbę przebiegów przeciętych. Powód: okno pomiaru zaczyna się i kończy w chwilach niezależnych od fazy sondy, a przebieg D2r przy N = 16 trwa ~19 ms, więc litera W4 unieważniałaby ~4 % przebiegów D2r bez związku z działaniem sondy (*Aparatura i suchy przebieg*).
