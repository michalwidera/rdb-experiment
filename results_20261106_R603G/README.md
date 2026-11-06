# R603G - koszt sondy życia subskrybentów (D2s) przy długo żyjących subskrybentach, D2s wobec C' (pi400, `--realtime`)

Zgłoszenie: michalwidera/retractordb#603. Decyzja człowieka po R603F (`results_20261106_R603F/wynik.md`, *Decyzje człowieka po wyniku*, punkt 3): przed scaleniem `dev/muro` do `master` trzeba zmierzyć koszt sondy przy długo żyjących subskrybentach. To wariant D3(b) protokołu R603F i otwarta pozycja w komentarzu planu D2s (6688281387). Ten plik zapisano PRZED pomiarem i przed budową aparatury. Po zatwierdzeniu przez człowieka zmiany protokołu trafiają do sekcji *Aneksy* z datą i powodem, nie do treści powyżej.

**Stan: projekt do zatwierdzenia** (decyzje G0-G4 w sekcji *Decyzje*).

Aparatura pochodzi z R603F (`results_20261106_R603F/`, scalenie do `main` `41c3151`), a przez nią z R603E, R603D, R603C i R600. Opis tego, co się nie zmienia, jest w ich README. Poniżej są tylko różnice i nowe kryteria.

## Pytanie

R603F mierzyło sondę przy klientach żyjących ~36 ms, więc lista obserwowanych była prawie zawsze pusta (R603F, *Granice wniosków*). W typowym wdrożeniu subskrybent żyje długo. Wtedy sonda co `kClientLivenessProbeInterval` = 1 s wykonuje `inspectProcess` dla każdego z N obserwowanych klientów w jednym obrocie wątku komunikacyjnego. Pytania:

1. Ile wydłuża się obrót wątku komunikacyjnego z przebiegiem sondy przy N = 1, 8 i 32 subskrybentach i jak ten koszt rośnie z N (K4)?
2. Czy przebieg sondy kosztuje coś wątek slotu na slotach, których dotyka (K3p, kryterium główne)?
3. Czy przy tym samym N strona D2s nie jest gorsza od C' poza przebiegami sondy: w wątku slotu (K3) i w obrocie bezczynnym wątku komunikacyjnego (K3t)?

## Strony porównania

| Strona | Rewizja silnika | Binarka na workerze (bez przebudowy) | Wątek komunikacyjny przy N żywych subskrybentach |
|---|---|---|---|
| C' (`Cp`) | `e0857dc8ba5387929c0e79d172cb8c45a669e3a3` | `~/R376/bin/R603D_Cp`, `xretractor` `e435618b...` | bez sondy: obrót = komendy, `releaseAbandonedQueues` (pusto), sen 1 ms |
| D2s (`D2s`) | `75e7574cf90d7548b1d95c7cef5a80e9b5700f91` | `~/R376/bin/R603F_D2s`, `xretractor` `7c02c52c...` | co 1 s `probeSubscribers`: N razy `inspectProcess` (wpis `/proc/<pid>/task/<pid>/stat`), żywy klient zostaje na liście; w pozostałych obrotach tylko `steady_clock::now()` i porównanie z `nextProbe_` |

Obie binarki mają łatkę P1 (`deadline_ns`), a ich build-info jest identyczne (R603F, *Aparatura i suchy przebieg*). Sumy sprawdza `campaign.sh`, jak w R603F.

## Ustalenia przed pomiarem (2026-11-06, z kodu `75e7574c` i danych R603F)

1. **Klient bez `-m` jest obserwowany przez sondę.**
   - `IpcClient::netClient` wpisuje `db.start` (znacznik startu procesu z `inspectProcess(getpid())`) do każdego żądania (`src/qry/ipcClient.cpp:142`), także do `show`.
   - Handler `show` przekazuje go do `subscribe(..., clientStart)`. Klient trafia do `watched_`, gdy wpis procesu jest znaleziony, nie jest zombie i znacznik się zgadza (`ipcServer.cpp`, `subscribe`).
   - Klient na tym samym workerze i w tej samej przestrzeni PID spełnia ten warunek. Bramka W4 sprawdza to w śladzie: N udanych `openat` w każdym przebiegu sondy.
2. **Klient bez `-m` czyta aż do SIGINT.**
   - Pętla `qry::select` kończy się na `done` od producenta, na ciszy serwera (`serverNoDataTimeoutMs_`) albo na `_kbhit`.
   - `_kbhit` zwraca false, gdy stdin nie jest terminalem (`src/common/uxSysTermTools.cpp:78`), więc stdin z `/dev/null` nie kończy klienta.
   - Producent odbiera z kolejki odpowiedzi `try_receive` bez snu, dopóki są komunikaty (sen 1 ms tylko przy pustej kolejce). Wątek główny co 1 ms opróżnia kolejkę SPSC i wypisuje wiersze na stdout (domyślnie RAW).
   - Klient, który nie nadąża, zapełnia swoją kolejkę (10 s strumienia). Wtedy `broadcast` porzuca ją na obu stronach jak kolejkę martwego klienta. Bramka W3 wyklucza takie przebiegi.
3. **Sonda w obrocie bez zgonu.** `probeSubscribers` iteruje `watched_`. Dla żywego klienta to jedno `inspectProcess`: w śladzie udany `openat`, bez `kill`, bez zajęcia `clientMapsMutex_`. `read` i `close` nie są śledzone. Przebieg sondy nie dotyka kolejek ani muteksu, który bierze wątek slotu. Na wątek slotu (rdzeń izolowany 3) może więc wpłynąć tylko przez wspólne L2 i pamięć. Obrót bez przebiegu sondy nie zależy od N.
4. **Faza sondy.** `nextProbe_ = now + 1 s` liczone od chwili przebiegu, więc faza przesuwa się o część obrotu (~1,1 ms) na sekundę. Wobec slotów uc05 (takt 1 ms) jest praktycznie jednostajna, bez aliasingu.
5. **Limity N.**
   - Kod nie ogranicza liczby subskrybentów (`watched_` i mapy rejestru to kontenery bez limitu).
   - Pamięć: kolejka uc05 ma 8000 komunikatów po 1048 B + 216 B nagłówka, ~8,4 MB (`responseQueueBytes`; wzór z R603D). Przy N = 32 to ~268 MB. Na workerze 2026-11-06 21:30: `/dev/shm` 1890 MiB wolne, `MemAvailable` ~3150 MiB, uptime 14 h, bezczynny. Silnik ma `cap_ipc_lock`, więc `mlockall` blokuje mapowania kolejek ponad `ulimit -l` (473 MiB).
   - Ograniczenie praktyczne to CPU klientów. Każdy parsuje (`read_info`) i wypisuje ~800 wierszy/s, a N klientów dzieli rdzenie 0-2 z wątkiem komunikacyjnym. N = 32 to ~25 600 wierszy/s. Czy klienci nadążają, sprawdza suchy przebieg (W2). N = 64 (~540 MB kolejek) odrzucono z góry z tego samego powodu.
   - Kolejka komend (`kQueryQueueMaxMessages` = 1000) nie jest granicą, bo podłączenia idą po kolei.
6. **Ta sama binarka klienta po obu stronach.** `xqry` C' (`4e8dd234...`) i D2s (`e5e359e6...`) powstały z tych samych źródeł: między `e0857dc8` a `75e7574c` `src/qry` i `src/common` się nie zmieniają, a `constants.hpp` dostaje tylko `kClientLivenessProbeInterval`. Sumy różnią się przez budowę. Przy N klientach na rdzeniach wątku komunikacyjnego różnica układu binarki klienta działałaby jak różnica obciążenia, więc obie strony używają `xqry` C' (G3).
7. **Wielkość efektu, od której sonda ma znaczenie.**
   - R603F przyjęło koszt wykrycia śmierci: S(D2s) uc05 = +25,8 µs na serię, przy ~0,4 serii/s (30 podłączeń w ~75 s), czyli ~10 µs/s czasu wątku slotu.
   - Przebieg sondy jest raz na sekundę. Próg K3p δ_S = 10 µs na przebieg oznacza więc, że sonda przy N subskrybentach nie kosztuje wątku slotu więcej niż przyjęty już koszt wykrycia śmierci.
   - R603F przyjęło też ~0,2 µs na obrót bezczynny (K3t). Próg K3t δ_t = 0,5 µs to 2,5 raza tyle.
   - Różnice między parami binarek poza seriami sięgały w R603F 2,6 % (compute p50 uc05) i 4,5 % (e2e p99 uc05), w obu kierunkach. Próg K3 δ = 5 % mediany C' leży nad tym poziomem.

## Obciążenie i przebieg

Jedna rodzina **uc05** (takt 1 ms, największa kolejka, najmniejszy zapas slotu; G0), N ∈ {1, 8, 32}, bez krótkich podłączeń (G1). Jeden przebieg (`run_one.py`):

1. Świeży katalog pracy `/dev/shm/r376/run` z korpusu, `xretractor` strony i `xqry` C' do `~/R376/exec` (ten sam argv[0]), `setcap`, start `taskset -c 3 xretractor query.rql -k -r -t`, rozgrzewka 5 s. Bez zmian wobec R603F.
2. **Podłączenia N subskrybentów po kolei:** `xqry -s <strumień>` bez `-m`, stdin `/dev/null`, stdout do pliku w `/dev/shm/r376/run/temp/` (dane korpusu zostają na workerze i są kasowane po przebiegu). Następny klient startuje po pierwszym wierszu poprzedniego (limit 15 s) i przerwie 0,25 s. Strumień z `streams.tsv` R600 (tylko na workerze), wszyscy N subskrybują ten sam.
3. **Ustalenie 5 s**: okna podłączeń i tworzenia kolejek (~10 ms każde w uc05) kończą się przed oknem pomiaru.
4. **Okno pomiaru W = 60 s** (G4). Przed startem śladu liczba wierszy każdego klienta, potem ftrace (zbiór wywołań, filtry i bufor 65 536 kB jak R603F), 60 s, stop śladu, ponownie liczba wierszy, żywotność klientów (`poll()`), `/proc/stat` rdzeni 0-2 na obu końcach okna.
5. Koniec: SIGINT do wszystkich klientów, zebranie ich, skasowanie wyjść, SIGTERM silnika, przeniesienie `slots.csv`. Przed następnym przebiegiem runner sprawdza, że w `/dev/shm` nie został żaden obiekt kolejki odpowiedzi. Pozostałość przerywa kampanię.

Przebieg trwa ~85 s (N = 32) i ma ~60 przebiegów sondy, czyli ~540 na stronę i N.

**Kampania** (`campaign.sh`): 9 par ABBA na każde N, 54 przebiegi, ~1,4 h. W parze p kolejność N jest rotowana ({1, 8, 32} przesunięte o p), a strony idą C', D2s w parze nieparzystej i D2s, C' w parzystej. Dryf w czasie rozkłada się więc na strony i na N.

## Okna i zdarzenia

- **Obrót wątku komunikacyjnego** jak R603D (`comm_turns`): od wyjścia z `clock_nanosleep`/`nanosleep` do następnego wejścia w sen, wątek inny niż RT.
- **Przebieg sondy (D2s)**: obrót z co najmniej jednym udanym `openat` wątku komunikacyjnego w oknie pomiaru. W oknie nie ma podłączeń, więc innego źródła takich `openat` nie ma: C' miało w R603F 0 udanych `openat` poza oknami podłączeń. **Nadwyżka przebiegu** E_p = długość obrotu - mediana obrotu bezczynnego tego przebiegu.
- **Obrót bezczynny**: każdy inny obrót w oknie pomiaru (na C' wszystkie obroty okna).
- **Sloty dotknięte przez przebieg sondy**: sloty narażone na okno [początek, koniec obrotu z sondą] plus pierwszy slot z pobudką po jego końcu. Definicja i model klasy slotu (H = 40) jak w R603E (`affected_idx`, `SlotModel`). Placebo to to samo okno przesunięte o m · H · takt na sloty kontrolne (`affected_cluster`, do 20 kopii).
- **Sloty kontrolne**: sloty okna pomiaru. Na D2s bez slotów dotkniętych przez którykolwiek przebieg sondy (± `GUARD`, jak sloty podłączeń w R603F).

## Kryteria (ustalone przed pomiarem)

Dla każdego N osobno, sumarycznie po 9 przebiegach strony. Bootstrap: 95 % percentylowy, klaster = przebieg sondy z jego kopiami placebo, 2000 losowań, ziarna jak R603F (placebo 6034, bootstrap 6035, H0 6036). Ważność przebiegu: bramki W1-W4 (*Kolejność*). **Liczność**: ≥ 8 ważnych przebiegów na stronę i N, inaczej NIEROZSTRZYGNIĘTE (liczność).

### K3p - koszt przebiegu sondy na slotach dotkniętych (kryterium główne, D2s)

S_p = średnia po przebiegach sondy z (suma odchyleń `compute_ns` slotów dotkniętych od mediany ich klasy) - (średnia tej sumy po kopiach placebo), jak S w K2s R603E. **ZDANE**, gdy górna granica S_p < δ_S = 10 µs. **NIEZDANE**, gdy dolna granica S_p > δ_S. **NIEROZSTRZYGNIĘTE** w pozostałych przypadkach.

- **Ważność miary (H0):** okna syntetyczne na przebiegach C' tego samego N. Na każdą sekundę okna pomiaru jedno okno zaczyna się na początku obrotu najbliższego fazie jednostajnej w tej sekundzie, a jego długość jest losowana z przebiegów sondy D2s tego samego N. 5 zestawów na przebieg C', analiza jak S_p. Półszerokość przedziału S_H0 ≤ δ_S / 2 = 5 µs. Niespełnione = NIEROZSTRZYGNIĘTE (miara).
- **Bez kontroli dodatniej:** w oknie pomiaru nie ma zdarzenia o znanym koszcie. Rozdzielczość miary to półszerokość H0 (*Granice wniosków*).
- Opisowo: Δ mediany slotów dotkniętych wobec placebo, sloty dotknięte na przebieg, S_H0.

### K4 - obrót wątku komunikacyjnego z przebiegiem sondy (D2s)

**ZDANE**, gdy przy N = 32 p99 nadwyżki E_p ≤ 1 ms (`kQueuePollInterval`: przebieg sondy nie opóźnia obsługi komend o więcej niż jeden sen pętli). **NIEZDANE** w przeciwnym przypadku. Opisowo dla każdego N: E_p p50 / p99 / max, liczba przebiegów sondy na przebieg (oczekiwane W ± 1) i odstęp między nimi. Koszt na subskrybenta to nachylenie prostej najmniejszych kwadratów median E_p przebiegów względem N. Z niego N, przy którym p50 E_p osiągnęłoby 1 ms (ekstrapolacja, tylko opisowo).

### K3 - wątek slotu poza przebiegami sondy, D2s wobec C' przy tym samym N

Sloty kontrolne, per przebieg `compute_ns` p50, `wake_lag_ns` p99, `e2e_ns` p99. Różnica d = mediana D2s - mediana C', rozrzut = większy z zakresów wewnątrz strony, dokładny permutacyjny MW 9 vs 9 (opisowo). **REGRESJA D2s**, gdy d > max(rozrzut, δ), δ = 5 % mediany C' tej miary i tego N. Poza tym bez regresji (*Ustalenia*, punkt 7).

### K3t - obrót bezczynny wątku komunikacyjnego, D2s wobec C' przy tym samym N

Per przebieg **średnia obrotu bezczynnego obcięta do p99** (wzór diagnostyki R603F, *Odstępstwa*, punkt 2). **REGRESJA D2s**, gdy d > max(rozrzut, δ_t), δ_t = 0,5 µs. Poza tym bez regresji. p50 (skwantowane do 1 µs) i p99 obrotu bezczynnego raportowane opisowo regułą R603F. Opisowo także zależność d od N: kod przewiduje d niezależne od N.

### Opisowo (bez kryterium)

- Obciążenie: `compute_ns` p50 i e2e p99 wobec N na obu stronach (wysyłka do N kolejek w `broadcast`), zajętość rdzeni 0-2 z `/proc/stat`, `VmLck`, wiersze odebrane przez klientów wobec 799,9/s · W.
- O1 jak R603F: futex wątku RT, FUTEX_WAIT na muteksie kolejki.

## Przewidywanie przed pomiarem

| N | E_p p50 [µs] | E_p p99 [µs] | K4 | S_p [µs/przebieg] | K3p | K3 | K3t d (średnia obcięta) [µs] |
|---|---|---|---|---|---|---|---|
| 1 | ~5-15 | ≤ ~60 | - | ~0 (w H0) | ZDANE | bez regresji | ~+0,2 |
| 8 | ~40-120 | ≤ ~200 | - | ~0..+3 | ZDANE | bez regresji | ~+0,2 |
| 32 | ~160-480 | ≤ ~700 | ZDANE | ~0..+5 | ZDANE, przy S_p bliżej +5 możliwe NIEROZSTRZYGNIĘTE | bez regresji | ~+0,2 |

1. **K4: ZDANE.** Jedno `inspectProcess` (otwarcie, odczyt i zamknięcie wpisu procfs) to ~5-15 µs na Cortex-A72 z `PREEMPT_RT`, więc koszt rośnie liniowo, ~5-15 µs na subskrybenta. Ogon p99 przy N = 32 wynika z wywłaszczeń przez klientów na tych samych rdzeniach. Ekstrapolowane N dla 1 ms: ~70-200.
2. **K3p: ZDANE przy N = 1 i 8.** Przebieg sondy dotyka ~1-2 slotów uc05, a jego jedyny kanał wpływu to L2 i pamięć (*Ustalenia*, punkt 3). Przy N = 32 okno ~0,2-0,5 ms dotyka ~1,5 slotu. Przewidywane S_p to kilka µs, poniżej δ_S. Ryzyko NIEROZSTRZYGNIĘTEGO, gdy przedział sięgnie 10 µs.
3. **K3: bez regresji.** Przebiegi sondy dotykają ~0,15-0,5 % slotów, a sloty kontrolne ich nie zawierają. Bezwzględne `compute_ns` rośnie z N na obu stronach (wysyłka do N kolejek), jednakowo.
4. **K3t: bez regresji**, d ≈ +0,2 µs jak w R603F, niezależne od N.
5. **Bramki:** klienci nadążają przy N = 32 (W2), zero porzuceń w oknie (W3), N udanych `openat` w każdym przebiegu sondy (W4).

## Kolejność

1. Zatwierdzenie protokołu przez człowieka; commit i push na gałęzi `experiment/20261106_R603G`.
2. **Aparatura** (`run_one.py`, `campaign.sh`, `analyze.py`, *Aparatura*). Test analizy: na danych R603F (archiwum `rdb-experiment-embargo/R603F/` rozpakowane od nowa) funkcje wspólne z R603F dają ten sam obrót bezczynny p50 / p99 / max co *Wydruk analizy* R603F dla uc05 na obu stronach, a C' ma 0 przebiegów sondy poza oknami podłączeń.
3. **Suchy przebieg** uc05: po 1 przebiegu C' i D2s przy N = 32 i N = 1 (4 przebiegi, ~6 min, `~/R376/dry_R603G`), odczepiony, bez połączeń z workerem w trakcie. Bramki (każda niespełniona = decyzja człowieka przed kampanią; w kampanii te same bramki decydują o ważności przebiegu):
   - **W1** - `rt_ok` (wątek SCHED_FIFO, VmLck > 0), `trace_overrun` = 0, governor `performance`;
   - **W2** - każdy klient żyje na końcu okna i odebrał w oknie ≥ 95 % z 799,9 · W wierszy;
   - **W3** - w oknie pomiaru brak zwolnienia kolejki: 0 `munmap` kolejki, `unlinkat`, `renameat` i `kill` z wątków silnika;
   - **W4** - identyfikacja sondy: na D2s każdy przebieg sondy ma dokładnie N udanych `openat` i 0 nieudanych, przebiegów jest W ± 1, odstęp 1,000-1,010 s; na C' 0 udanych `openat` wątku komunikacyjnego w oknie;
   - opisowo: zajętość rdzeni 0-2 przy N = 32, E_p, wstępna półszerokość H0.
4. Kampania: 54 przebiegi, ~1,4 h, `setsid nohup ./campaign.sh > ~/R376/campaign_R603G.log 2>&1 < /dev/null &`. **Do jej oczekiwanego końca nie łączyć się z workerem.** Sesja nie uruchamia żadnej pętli przez ssh. Oczekiwanie liczy lokalny zegar bez kontaktu z workerem, a log sprawdza jedno logowanie po ~1,5 h (aneks A3 R603F). Przebieg nieważny wg W1-W4 jest raportowany i nie jest powtarzany w kampanii (liczność ≥ 8).
5. `wynik.md`, surowe dane do `paper-arXiv/rdb-experiment-embargo/R603G/` (wiersz w obu tabelach README), tutaj tylko indeks sum; komentarz w #603.

## Aparatura - różnice wobec R603F

1. **Bez budowy.** Binarki `R603D_Cp` i `R603F_D2s` z sumami z R603F; `build_ab.sh` niepotrzebny.
2. **`run_one.py`** (nowy, na bazie R603F): `--n N` zamiast serii krótkich podłączeń, klienci bez `-m` (punkt 2 *Obciążenia i przebiegu*), `xqry` z `R603D_Cp` po obu stronach (G3), ślad tylko w oknie pomiaru. Zapisuje `clients.tsv` (i, pid, start, pierwszy wiersz, wiersze na początku i końcu okna, żywy na końcu okna), `window.json` (granice okna CLOCK_MONOTONIC), `cpu.txt` (`/proc/stat` rdzeni 0-2), `slots.csv`, `trace.txt`, `rt.txt`, `meta.json` (strona, N, sumy, governor, overrun). Wyjście klientów nie trafia do `raw`.
3. **`campaign.sh`**: uc05, N z rotacją, 9 par ABBA, sprawdzenie sum obu binarek i build-info jak R603F, zmienne `R603G_PAIRS`, `R603G_NS`, `R603G_RAW`, katalog `~/R376/raw_R603G/uc05/N<n>/<strona>_<para>`.
4. **`analyze.py`**: importuje `results_20261106_R603F/analyze.py` (a przez niego R603E, R603D, R603C) bez zmian: `parse_trace`, `comm_turns`, `SlotModel`, `affected_idx`/`affected_cluster`/`aff_boot`, permutacyjny MW. Dochodzi: rozpoznanie przebiegów sondy i E_p, sloty kontrolne bez slotów dotkniętych, K3p z H0 na C', K4, K3 i K3t z progami δ (reguła `regress_lines` R603F rozszerzona o δ), bramki W1-W4 (`--gates`).
5. **Archiwum** jak R603F: `rdb-experiment-embargo/R603G/`, części po N, każda z indeksem; tutaj tylko indeksy.

## Decyzje (do zatwierdzenia przez człowieka)

- **G0 - rodzina, N i liczba par.** Rekomendacja: uc05, N ∈ {1, 8, 32}, 9 par ABBA na N (54 przebiegi, ~1,4 h). Koszt `inspectProcess` nie zależy od rodziny, a uc05 ma najkrótszy takt i największe kolejki. Alternatywy: (b) dołożyć uc03 (takt 5 ms, +~1,4 h); (c) N = 16 zamiast 32, gdyby suchy przebieg pokazał, że klienci nie nadążają.
- **G1 - krótkie podłączenia.** Rekomendacja: bez. Ścieżkę śmierci klienta zmierzyło R603F, a serie drenażu w oknie pomiaru mieszałyby się z przebiegami sondy (argument D3(c) R603F). Alternatywa: 30 krótkich podłączeń jak R603F na tle N subskrybentów (obraz bliższy wdrożeniu, ale serie trzeba wyłączać ze slotów kontrolnych i z obrotów bezczynnych).
- **G2 - progi.** Rekomendacja: K3p δ_S = 10 µs na przebieg sondy, K4 p99 E_p ≤ 1 ms przy N = 32, K3 δ = 5 % mediany C', K3t δ_t = 0,5 µs na średniej obciętej (uzasadnienie: *Ustalenia*, punkt 7). Alternatywa: δ_S = 5 µs (połowa przyjętego kosztu wykrycia śmierci), wtedy ważność H0 wymaga półszerokości ≤ 2,5 µs.
- **G3 - binarka klienta.** Rekomendacja: `xqry` C' (`4e8dd234...`) po obu stronach (*Ustalenia*, punkt 6). Alternatywa: każda strona z własnym `xqry`, jak R603F.
- **G4 - okno pomiaru.** Rekomendacja: 60 s, ~540 przebiegów sondy na stronę i N. R603F miało ~270 serii na stronę przy półszerokości H0 3,4 µs w uc05. Alternatywa: 120 s (~2,4 h kampanii).

## Granice wniosków (znane przed pomiarem)

- Jedna platforma: Cortex-A72, wspólne L2 1 MiB, jądro 6.8 `PREEMPT_RT`; jedna rodzina (uc05).
- N ≤ 32. Większe N tylko przez ekstrapolację K4 i bez K3p.
- Klienci dzielą rdzenie 0-2 z wątkiem komunikacyjnym, tak jak we wdrożeniu na jednej maszynie. Ogon E_p i obrotu bezczynnego zależy od ich obciążenia, jednakowo po obu stronach.
- Sonda na kliencie żywym. Ścieżkę wykrycia zgonu zmierzyło R603F. Klient z innej przestrzeni PID albo przy `hidepid` nie jest obserwowany i nie płaci sondy (*Ustalenia*, punkt 1).
- K3p nie ma kontroli dodatniej. Efekt mniejszy od półszerokości H0 jest nierozróżnialny od zera.

## Embargo

Korpus `uc01`..`uc08` jest objęty embargiem do publikacji DEBS. W tym katalogu i w komentarzach do zgłoszeń są wyłącznie identyfikatory rodzin i liczby z nich wyprowadzone. Plany, dane, generatory, nazwy strumieni i wyjście klientów zostają na workerze w `/dev/shm/r376`, a surowe CSV i ślady w prywatnym `paper-arXiv` (`rdb-experiment-embargo/R603G/`). Tutaj zostaje indeks sum.
