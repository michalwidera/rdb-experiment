# R603G - wynik

Badanie: koszt sondy życia subskrybentów (D2s, `75e7574c`) przy długo żyjących subskrybentach wobec C' (`e0857dc8`) z michalwidera/retractordb#603. Ten pomiar jest warunkiem scalenia `dev/muro` do `master` (decyzja z 2026-11-06). Protokół i kryteria w `README.md` (`17f9963`, przed pomiarem), zatwierdzenie i aparatura `c3649d1`, suchy przebieg 1 `86f7235`, aneksy A1-A5 zatwierdzone przez człowieka przed kampanią `9a64d44`, suchy przebieg 2 i start kampanii `e20bf09`.

Kampania trwała 2026-11-06 22:21:31 - 2026-11-07 00:12:26 (ostatni przebieg uruchomiony 00:10:29) na pi400. Rodzina uc05, N = 1 / 8 / 16 długo żyjących klientów `xqry -s` bez `-m`, 9 par C' / D2s w kolejności ABBA z rotacją N, okno pomiaru 60 s: razem 54 przebiegi i 450 klientów. Strony bez przebudowy: C' = `~/R376/bin/R603D_Cp` (`xretractor` `e435618b...`), D2s = `~/R376/bin/R603F_D2s` (`xretractor` `7c02c52c...`), `xqry` `4e8dd234...` z `R603D_Cp` po obu stronach (G3), build-info równe. Wszystkie 54 przebiegi ważne według W1-W4: jeden wątek `SCHED_FIFO` z `VmLck` > 0, wątek komunikacyjny przypięty do rdzenia 0, governor `performance`, `trace_overrun` = 0, kod wyjścia silnika 0, 0 pozostałości w `/dev/shm` po przebiegu. Każdy klient żył na końcu okna i odbierał 800,0 wierszy/s. Log kończy się `CAMPAIGN_COMPLETE`; kopia: `campaign.log`. Od startu kampanii do jej końca sesja nie łączyła się z workerem: pierwsze logowanie po starcie było o 00:21:49.

Surowe dane (korpus pod embargiem) leżą poza tym repozytorium, w prywatnym `paper-arXiv`, w katalogu `rdb-experiment-embargo/R603G/`. Są w trzech częściach po N, każda z indeksem 144 plików (18 przebiegów × 8 plików), razem 432 pliki:

| część | bajty | SHA-256 | indeks |
|---|---|---|---|
| `results_20261106_R603G_raw_N1.tar.gz` | 28 772 976 | `b739fe5df14bb47c918383edcafc193b5907f6c99c5b31ac54dfa3f06298757b` | `results_20261106_R603G_raw_N1.index.tsv` |
| `results_20261106_R603G_raw_N8.tar.gz` | 39 373 069 | `789e5a9a7839deddd03251d1e02bec7d433133c486ed95d885ff6b983877cf20` | `results_20261106_R603G_raw_N8.index.tsv` |
| `results_20261106_R603G_raw_N16.tar.gz` | 54 377 916 | `0f517585ac8d2abf1bba996637bae8d069e95cac967f1c4b7ec0fc38c736b30a` | `results_20261106_R603G_raw_N16.index.tsv` |

Analiza: `analyze.py --raw <raw>` (ziarna domyślne 6034-6036). Pełny wydruk jest niżej, w części *Wydruk analizy*.

## Odpowiedź

**Sonda nie pogarsza wątku slotu poza slotami, na które trafia jej przebieg. Pogarsza natomiast obsługę komend przez wątek komunikacyjny, liniowo z N.**

- **K4 NIEZDANE przy N = 16.** Raz na sekundę przebieg sondy wydłuża obrót wątku komunikacyjnego o p99 1352 µs (p50 1197, max 1920 µs), wobec progu 1 ms. Koszt wynosi 71,5 µs na subskrybenta przy wyrazie wolnym 48 µs, więc p50 przekracza 1 ms przy N ≈ 13.
- **K3 bez regresji przy każdym N.** Dotyczy compute p50, wake p99 i e2e p99 na slotach kontrolnych.
- **K3p, czyli koszt przebiegu sondy na slotach, które dotyka, zależy od N niemonotonicznie.**
  - N = 1: +15,8 µs na przebieg (+10,8..+21,3), **NIEZDANE** (δ_S = 10 µs).
  - N = 8: +12,6 µs (+5,7..+19,9), **NIEROZSTRZYGNIĘTE**.
  - N = 16: -5,5 µs (-13,7..+2,9), **ZDANE**.
  - Miara ma rozdzielczość: półszerokość H0 wynosi 2,1 / 2,9 / 3,5 µs, poniżej 5 µs.
- **K3t daje regresję D2s według litery przy N = 16.** Średnia obrotu bezczynnego obcięta do p99 jest wyższa o +0,83 µs przy progu 0,82 µs (rozrzut wewnątrz strony), czyli zapas wynosi 0,005 µs. Przy N = 1 / 8 różnica to +0,10 / +0,48 µs, bez regresji. Przesunięcie rośnie z N. p50 i p99 obrotu bezczynnego są równe w granicach kwantu 1 µs.

| N | E_p p50 / p99 / max [µs] | K4 | S_p [µs/przebieg] (95 %); H0 półszerokość | K3p | Δ mediany slotów dotkniętych [µs] | K3 | K3t d [µs] |
|---|---|---|---|---|---|---|---|
| 1 | 124 / 187 / 218 | (opisowo) | +15,81 (+10,83..+21,25); 2,12 | **NIEZDANE** | +5,24 (+4,83..+5,48) | bez regresji | +0,10: bez regresji |
| 8 | 612 / 743 / 765 | (opisowo) | +12,57 (+5,73..+19,86); 2,92 | **NIEROZSTRZYGNIĘTE** | +2,58 (+2,20..+2,85) | bez regresji | +0,48: bez regresji |
| 16 | 1197 / 1352 / 1920 | **NIEZDANE** | -5,46 (-13,69..+2,86); 3,45 | **ZDANE** | -2,58 (-3,39..-1,75) | bez regresji | +0,83: **regresja według litery** |

- **Sonda działa jak w kodzie.** Na D2s każdy przebieg ma 60 przebiegów sondy, każdy z dokładnie N udanymi `openat` i bez nieudanych. Odstęp między nimi wynosi 999,999-1001,127 ms (p50 1000,5-1000,6). Na C' udanych `openat` wątku komunikacyjnego jest 0. W oknie nie ma zwolnień kolejki (W3: 0 `munmap` ≥ 1 MiB i 0 `unlinkat` / `renameat` / `kill` wątku komunikacyjnego).
- **Na co idzie czas sondy** (opisowo, z obrotów z sondą D2s, na podstawie samych zdarzeń śladu):
  - `openat` wpisu procfs zajmuje p50 21 µs (33 µs przy N = 1).
  - Między kolejnymi `openat` mija ~49-50 µs na subskrybenta. W tym czasie są odczyt, zamknięcie i parsowanie wpisu przez `std::ifstream` / `std::istringstream`. Ślad nie zawiera `read` ani `close`, więc tej części nie rozdzielono.
  - ~70 % kosztu na subskrybenta leży więc poza `openat`. To zgadza się z hipotezą z suchego przebiegu (`src/common/osPlatform.cpp:59-91`), ale jej nie dowodzi: nie wiadomo, ile z tych 50 µs to jądro (`read` procfs), a ile przestrzeń użytkownika.
- **Rdzenie i klienci.** Zajętość rdzeni 0-2 wynosiła 0,07 / 0,44 / 0,69 (N = 1 / 8 / 16), jednakowo na obu stronach. Wątek komunikacyjny był sam na rdzeniu 0, więc E_p mierzy koszt sondy, a nie rywalizację o CPU (A4(b)).

## Odstępstwa od protokołu i od przewidywania

1. **Klienci kończyli się przez SIGKILL, nie przez SIGINT.** Wszystkich 450 klientów kampanii (i obu przebiegów suchego przebiegu 2) nie zakończyło się w 5 s po SIGINT, więc runner dobił je przez `kill` (`client_rc` = `killed` w `meta.json`). W suchym przebiegu 1 kończyli się kodem -2. Sygnał pada po `t1`, po zatrzymaniu śladu, po sprawdzeniu, że klienci żyją, i po policzeniu wierszy. Okno pomiaru i bramki nie są więc nim objęte, a dla silnika śmierć przez SIGINT i SIGKILL jest tym samym zgonem bez zgłoszenia. Przyczyna nieustalona. Hipoteza: kampania i suchy przebieg 2 startowały w tle z nieinteraktywnej powłoki (`...; setsid nohup ... &`), która ustawia SIGINT na ignorowany, a `xqry` polega na domyślnej obsłudze SIGINT i to ustawienie dziedziczy. Każdy przebieg trwał przez to ~5 s dłużej.
2. **Przewidywanie z protokołu (tabela *Przewidywania* przed aneksami):**
   - **K4: chybione.** Przewidywano ~5-15 µs na `inspectProcess` i K4 ZDANE. Zmierzono ~72 µs na subskrybenta, a już przy N = 1 nadwyżkę 124 µs.
   - **K3p: chybione przy N = 1 i 8.** Przewidywano ZDANE przy S_p ~0.
   - **K3t: chybione co do niezależności od N.** Przewidywano d ≈ +0,2 µs bez zależności od N, zmierzono +0,10 → +0,48 → +0,83 µs.
   - **Trafione: K3 bez regresji i bramki.** Wiersz N = 32 tabeli nie ma odpowiednika, bo A4(b) zmieniło N na 16.
3. **Przewidywanie z aneksu A5 (po suchym przebiegu 1):**
   - **K4 NIEZDANE przy N = 16: trafione.** Wielkość była zawyżona: przewidywano E_p p50 ~130 / ~1050 / ~2100 µs, zmierzono 124 / 612 / 1197 µs. Pierwszy `inspectProcess` jest droższy od kolejnych (`openat` 33 wobec 21 µs; po ostatnim `openat` przy N = 1 zostaje 79 µs wobec 41-43 µs przy N = 8 / 16), więc ekstrapolacja z N = 1 przeszacowała nachylenie.
   - **K3p przy N = 1 możliwe NIEZDANE: trafione.**
   - **„S_p rośnie z N": chybione.** S_p maleje i przy N = 16 jest ujemne.
   - **„K3t bez zmian": chybione** (punkt 2).
4. **K3p maleje z N, wbrew mechanizmowi z *Ustaleń*, punkt 3.** Dłuższy przebieg sondy (więcej `inspectProcess`) nie kosztuje wątku slotu więcej. Przy N = 16 sloty dotknięte są nawet szybsze od placebo, a Δ mediany wynosi -2,58 µs przy przedziale z dala od zera. Skutek wynika więc z czegoś, co przebieg sondy robi albo wypiera niezależnie od liczby wywołań. Dwie hipotezy, żadna niesprawdzona:
   - (a) Przebieg trwający ~1,2 ms wypiera zwykłe obroty wątku komunikacyjnego (co ~1 ms), które w kopiach placebo są obecne. Ujemne S_p mierzyłoby wtedy koszt zwykłych obrotów dla wątku slotu.
   - (b) Odczyt wpisu procfs klienta (`do_task_stat` bierze blokadę `siglock` celu, w `PREEMPT_RT` sypiającą) na chwilę wstrzymuje klienta. Klient przestaje wtedy rywalizować z wątkiem slotu o muteks swojej kolejki.
   - Dodatnie S_p przy N = 1 nie ma w tych danych wyjaśnienia.
5. **K3t: przesunięcie rośnie z N, choć obrót bezczynny D2s różni się od C' tylko jednym `steady_clock::now()` i wywołaniem `probeSubscribers` z wczesnym powrotem.** Obrót bezczynny C' też wydłuża się z N (13,42 → 14,68 → 15,98 µs), a D2s nieco szybciej (13,51 → 15,16 → 16,80 µs). Hipoteza, niesprawdzona: większy ślad kodu i danych D2s na obrót płaci więcej przy presji na wspólne L2, która rośnie z N (wątek slotu pisze do N kolejek po ~8,4 MB). Bezwzględnie +0,83 µs na obrót przy ~1000 obrotów/s to ~0,8 ms CPU rdzenia 0 na sekundę.
6. **Wstępne S_p w trybie `--gates` różni się od wyniku głównego** (N = 8: +13,36 wobec +12,57 µs). Tryb `--gates` to diagnostyka suchego przebiegu i liczy S_p inną drogą losowań. Przyczyny różnicy nie sprawdzano. Werdykty pochodzą z analizy głównej.

## Granice wniosków

- Jedna platforma (Cortex-A72, wspólne L2 1 MiB, jądro `PREEMPT_RT`), jedna rodzina (uc05), N ≤ 16. Większe N tylko przez ekstrapolację K4, bez K3p.
- Wątek komunikacyjny był przypięty sam do rdzenia 0 (A4(b)). We wdrożeniu bez przypięcia dzieli rdzenie z klientami, więc E_p rośnie o udział w CFS (suchy przebieg 1: przy N = 32 na nasyconych rdzeniach przebieg sondy trwał p50 65 ms).
- Sonda tylko na żywych klientach. Ścieżkę wykrycia zgonu zmierzyło R603F.
- K3p nie ma kontroli dodatniej. Efekt mniejszy od półszerokości H0 (2,1-3,5 µs) jest nierozróżnialny od zera. Mechanizm zależności K3p od N jest nieznany (*Odstępstwa*, punkt 4).
- Rozkład czasu sondy opiera się na samych zdarzeniach `openat` i `clock_nanosleep`. Podział między jądro a przestrzeń użytkownika wymaga śladu `read` / `close` albo profilu.

## Skutek dla scalenia (decyzja człowieka)

Bilans D2s z R603F i R603G:

- **Zysk przy zgonie klienta (R603F):** koszt serii na slotach dotkniętych spada do 11-35 % kosztu C'.
- **Stały koszt przy żywych klientach (R603G):**
  - Wątek slotu: +16 µs raz na sekundę na ~1,3 slotu przy N = 1, bez przekroczeń terminu (overrun 0). To ~0,03 % czasu obliczeń slotów uc05.
  - Wątek komunikacyjny: obsługa komend wstrzymana raz na sekundę na ~50 + 72·N µs, czyli > 1 ms od N ≈ 13 (K4 NIEZDANE).

Możliwości:

- **(a) Scalić `dev/muro` do `master` bez zmian.** K4 to znane ograniczenie, zapisane w #603: opóźnienie komendy do ~1,4 ms raz na sekundę przy 16 subskrybentach. Tańsza sonda idzie osobnym zgłoszeniem.
- **(b) Przed scaleniem zmienić silnik i zmierzyć ponownie** (nowe badanie, K4 i K3p, ~4 h z budową). Dwie drogi:
  - rozłożyć sondę na obroty: ograniczona liczba subskrybentów na obrót, wtedy E_p nie zależy od N;
  - tańsze `inspectProcess`: `open` / `read` do bufora na stosie zamiast `std::ifstream` / `std::istringstream`. Zysk niepewny, bo podziału 50 µs między jądro a parsowanie nie zmierzono.
- **(c) Wycofać D2s.** Wraca wtedy koszt serii zmierzony w R603F.

Rekomendacja: **(a)**. Kryteria wątku slotu (K3) są spełnione przy każdym N. Niezdane K3p przy N = 1 to ~16 µs raz na sekundę bez przekroczeń terminu. K4 dotyczy opóźnienia komend, a nie obliczeń, i przy N ≤ 8 mieści się w 1 ms (p99 743 µs). Rozłożenie sondy na obroty jest prostą naprawą K4 na później. Zmiana w silniku to osobna decyzja.

## Decyzje człowieka po wyniku (2026-11-07)

1. **Wariant (a): `dev/muro` scalone z `master` bez zmian w silniku** (michalwidera/retractordb#608, `b0fd0135`) (*Skutek dla scalenia*). Przekroczenie K4 (wydłużenie obrotu wątku komunikacyjnego ~50 + 72·N µs raz na sekundę, > 1 ms od N ≈ 13) jest przyjęte jako znane ograniczenie D2s.
2. **Rozłożenie sondy na kolejne obroty: osobne zgłoszenie michalwidera/retractordb#607**, z planem przed kodem i własnym pomiarem.
3. Werdykty K3p (N = 1 NIEZDANE, N = 8 NIEROZSTRZYGNIĘTE) i K3t (N = 16 regresja według litery) zostają w *Wydruku analizy* bez zmian. Mechanizmów z *Odstępstw*, punkty 4 i 5, nie bada się osobno.
4. R603G scalone do `main`.

## Odtworzenie od zera

Wszystko na workerze `pi400` z katalogu `~/R376/apparatus_R603G` (kopia tego katalogu), poza analizą:

1. Korpus uc05 w `/dev/shm/r376/data/uc05` jak w R600 (`results_20261104_R600/wynik.md`, *Odtworzenie od zera*, punkt 3). `streams.tsv` z `~/R376/apparatus_R600` (tylko na workerze). Sprawdzenie: skrót SHA-256 drzewa z README R603C (*Suchy przebieg*, punkt 2).
2. Binarki: `~/R376/bin/R603D_Cp` (R603D) i `~/R376/bin/R603F_D2s` (R603F). `campaign.sh` sprawdza ich sumy i build-info.
3. Kampania: `cd ~/R376/apparatus_R603G; setsid nohup ./campaign.sh > ~/R376/campaign_R603G.log 2>&1 < /dev/null &` (~1,9 h). Do końca kampanii nie łączyć się z workerem. Przebieg nieważny według W1-W4 jest raportowany i nie jest powtarzany (liczność ≥ 8).
4. Analiza na hoście: `rsync -a <worker>:R376/raw_R603G/ <katalog>/raw/` albo trzy części archiwum rozpakowane do jednego katalogu (`tar xzf <część> -C <katalog>`, każda sprawdzona swoim indeksem jak w README `rdb-experiment-embargo`). Potem Python ≥ 3.10 z NumPy (np. `retractordb/.venv-python/bin/python3`) `-I analyze.py --raw <katalog>/raw --out w.txt` z tego katalogu. Skrypt importuje `../results_20261106_R603F/analyze.py`, a ten kolejno R603E, R603D i R603C. Część *Wydruk analizy* to ten wydruk bez pierwszego wiersza i z nagłówkami obniżonymi o jeden poziom: `sed 's/^#/##/' w.txt | tail -n +2` musi dać ją bajt w bajt. Sprawdzone 2026-11-07 na archiwum rozpakowanym od nowa (3 indeksy zgodne, 432 pliki, drzewo identyczne z danymi z workera, wydruk identyczny). Analiza trwa ~35 s.
5. Bramki per przebieg: `analyze.py --gates --raw <katalog>/raw`. Rozkład czasu sondy (*Odpowiedź*) to mediany z obrotów wątku komunikacyjnego zawierających `openat`, liczone ze zdarzeń całego `trace.txt` (także ~0,4 s po `t1`): czas `openat`, czas od wyjścia ze snu do pierwszego `openat`, czas od ostatniego `openat` do wejścia w sen i reszta na subskrybenta. Skrypt diagnostyczny nie należy do aparatury i wypisuje tylko liczby wyprowadzone, podane wyżej.

## Wydruk analizy


Źródło: `raw`, ziarna: placebo 6034, bootstrap 6035, H0 6036.

### N = 1

| wielkość | C' | D2s |
|---|---|---|
| przebiegi: ważne / wszystkie | 9 / 9 | 9 / 9 |
| przebiegi sondy na przebieg: min / max | 0 / 0 | 60 / 60 |
| odstęp przebiegów sondy [ms] min / p50 / max | - | 1000.004 / 1000.600 / 1001.112 |
| K4: obrót z sondą [µs] p50 / p99 / max | - / - / - | 138.0 / 201.0 / 231.0 |
| K4: nadwyżka E_p [µs] p50 / p99 / max | - / - / - | 124.0 / 187.0 / 218.0 |
| obrót bezczynny [µs] p50 / p99 / max | 13.0 / 23.0 / 3163.0 | 13.0 / 23.0 / 1753.0 |
| obrót bezczynny, średnia obcięta do p99 [µs] (mediana przebiegów) | 13.416 | 13.512 |
| sloty okna / kontrolne (średnio na przebieg) | 60001 / 60001 | 60001 / 59684 |
| compute p50 wszystkich slotów okna [µs] (mediana przebiegów) | 64.56 | 64.89 |
| e2e p99 wszystkich slotów okna [µs] (mediana przebiegów) | 1046.05 | 1055.57 |
| zajętość rdzeni 0-2 (średnio) | 0.068 | 0.070 |
| wiersze/s klienta: min / mediana | 800.0 / 800.0 | 800.0 / 800.0 |
| VmLck po podłączeniu [MiB] (mediana) | 97 | 97 |
| O1: futex wątku RT na przebieg / max [µs] | 63.3 / 84 | 45.1 / 82 |
| K3p: przebiegi sondy z placebo / sloty dotknięte na przebieg | - | 540 / 1.28 |
| K3p: S_p [µs/przebieg] (95 %) | - | +15.81 (+10.83..+21.25) |
| K3p: Δ mediany slotów dotkniętych [µs] (95 %) | - | +5.24 (+4.83..+5.48) |
| H0 K3p (okna syntetyczne na C'): okna / S_H0 [µs] (95 %) / półszerokość [µs] | 2700 / +0.40 (-1.70..+2.55) / 2.12 | - |

- **K3p** (δ_S = 10 µs): S_p +15.81 (+10.83..+21.25) µs, H0 półszerokość 2.12 µs. Werdykt: **NIEZDANE**.
- K4 (opisowo przy N = 1): p99 E_p = 187.0 µs.
- **K3**, compute_ns p50 per przebieg: mediana D2s - C' = 0.333 µs, rozrzut wewnątrz strony do 2.315 µs, δ = 3.228 µs, permutacyjny MW p = 0.796 - **bez regresji**.
- **K3**, wake_lag_ns p99 per przebieg: mediana D2s - C' = 7.678 µs, rozrzut wewnątrz strony do 18.919 µs, δ = 4.968 µs, permutacyjny MW p = 0.00564 - **bez regresji**.
- **K3**, e2e_ns p99 per przebieg: mediana D2s - C' = 9.492 µs, rozrzut wewnątrz strony do 17.041 µs, δ = 52.302 µs, permutacyjny MW p = 0.00276 - **bez regresji**.
- **K3t**, obrót bezczynny, średnia obcięta do p99 per przebieg: mediana D2s - C' = 0.096 µs, rozrzut wewnątrz strony do 0.303 µs, δ = 0.500 µs, permutacyjny MW p = 0.00276 - **bez regresji**.
- **K3t**, obrót bezczynny p50 (opisowo, reguła R603F) per przebieg: mediana D2s - C' = 0.000 µs, rozrzut wewnątrz strony do 1.000 µs, permutacyjny MW p = 1 - **bez regresji**.
- **K3t**, obrót bezczynny p99 (opisowo, reguła R603F) per przebieg: mediana D2s - C' = 0.000 µs, rozrzut wewnątrz strony do 7.000 µs, permutacyjny MW p = 0.911 - **bez regresji**.

Przebiegi nieważne: brak.

### N = 8

| wielkość | C' | D2s |
|---|---|---|
| przebiegi: ważne / wszystkie | 9 / 9 | 9 / 9 |
| przebiegi sondy na przebieg: min / max | 0 / 0 | 60 / 60 |
| odstęp przebiegów sondy [ms] min / p50 / max | - | 999.999 / 1000.535 / 1001.127 |
| K4: obrót z sondą [µs] p50 / p99 / max | - / - / - | 627.0 / 758.0 / 780.0 |
| K4: nadwyżka E_p [µs] p50 / p99 / max | - / - / - | 612.0 / 743.0 / 765.0 |
| obrót bezczynny [µs] p50 / p99 / max | 14.0 / 34.0 / 2592.0 | 15.0 / 33.0 / 992.0 |
| obrót bezczynny, średnia obcięta do p99 [µs] (mediana przebiegów) | 14.682 | 15.160 |
| sloty okna / kontrolne (średnio na przebieg) | 60002 / 60002 | 60001 / 59654 |
| compute p50 wszystkich slotów okna [µs] (mediana przebiegów) | 100.72 | 99.85 |
| e2e p99 wszystkich slotów okna [µs] (mediana przebiegów) | 1252.82 | 1257.63 |
| zajętość rdzeni 0-2 (średnio) | 0.438 | 0.437 |
| wiersze/s klienta: min / mediana | 800.0 / 800.0 | 800.0 / 800.0 |
| VmLck po podłączeniu [MiB] (mediana) | 153 | 153 |
| O1: futex wątku RT na przebieg / max [µs] | 656.0 / 415 | 653.0 / 563 |
| K3p: przebiegi sondy z placebo / sloty dotknięte na przebieg | - | 540 / 1.79 |
| K3p: S_p [µs/przebieg] (95 %) | - | +12.57 (+5.73..+19.86) |
| K3p: Δ mediany slotów dotkniętych [µs] (95 %) | - | +2.58 (+2.20..+2.85) |
| H0 K3p (okna syntetyczne na C'): okna / S_H0 [µs] (95 %) / półszerokość [µs] | 2700 / +0.25 (-2.77..+3.08) / 2.92 | - |

- **K3p** (δ_S = 10 µs): S_p +12.57 (+5.73..+19.86) µs, H0 półszerokość 2.92 µs. Werdykt: **NIEROZSTRZYGNIĘTE**.
- K4 (opisowo przy N = 8): p99 E_p = 743.0 µs.
- **K3**, compute_ns p50 per przebieg: mediana D2s - C' = -0.870 µs, rozrzut wewnątrz strony do 4.074 µs, δ = 5.036 µs, permutacyjny MW p = 0.605 - **bez regresji**.
- **K3**, wake_lag_ns p99 per przebieg: mediana D2s - C' = 6.764 µs, rozrzut wewnątrz strony do 22.956 µs, δ = 15.671 µs, permutacyjny MW p = 0.04 - **bez regresji**.
- **K3**, e2e_ns p99 per przebieg: mediana D2s - C' = 4.674 µs, rozrzut wewnątrz strony do 23.514 µs, δ = 62.641 µs, permutacyjny MW p = 0.0188 - **bez regresji**.
- **K3t**, obrót bezczynny, średnia obcięta do p99 per przebieg: mediana D2s - C' = 0.478 µs, rozrzut wewnątrz strony do 0.659 µs, δ = 0.500 µs, permutacyjny MW p = 4.11e-05 - **bez regresji**.
- **K3t**, obrót bezczynny p50 (opisowo, reguła R603F) per przebieg: mediana D2s - C' = 1.000 µs, rozrzut wewnątrz strony do 1.000 µs, permutacyjny MW p = 0.00226 - **bez regresji**.
- **K3t**, obrót bezczynny p99 (opisowo, reguła R603F) per przebieg: mediana D2s - C' = -1.000 µs, rozrzut wewnątrz strony do 8.000 µs, permutacyjny MW p = 0.918 - **bez regresji**.

Przebiegi nieważne: brak.

### N = 16

| wielkość | C' | D2s |
|---|---|---|
| przebiegi: ważne / wszystkie | 9 / 9 | 9 / 9 |
| przebiegi sondy na przebieg: min / max | 0 / 0 | 60 / 60 |
| odstęp przebiegów sondy [ms] min / p50 / max | - | 999.999 / 1000.587 / 1001.099 |
| K4: obrót z sondą [µs] p50 / p99 / max | - / - / - | 1213.0 / 1369.0 / 1936.0 |
| K4: nadwyżka E_p [µs] p50 / p99 / max | - / - / - | 1197.0 / 1352.0 / 1920.0 |
| obrót bezczynny [µs] p50 / p99 / max | 16.0 / 34.0 / 1098.0 | 16.0 / 34.0 / 5093.0 |
| obrót bezczynny, średnia obcięta do p99 [µs] (mediana przebiegów) | 15.978 | 16.804 |
| sloty okna / kontrolne (średnio na przebieg) | 60014 / 60014 | 60015 / 59631 |
| compute p50 wszystkich slotów okna [µs] (mediana przebiegów) | 128.26 | 127.76 |
| e2e p99 wszystkich slotów okna [µs] (mediana przebiegów) | 1383.22 | 1389.14 |
| zajętość rdzeni 0-2 (średnio) | 0.689 | 0.691 |
| wiersze/s klienta: min / mediana | 800.0 / 800.0 | 800.0 / 800.0 |
| VmLck po podłączeniu [MiB] (mediana) | 217 | 217 |
| O1: futex wątku RT na przebieg / max [µs] | 1778.6 / 2549 | 1757.7 / 2741 |
| K3p: przebiegi sondy z placebo / sloty dotknięte na przebieg | - | 540 / 2.40 |
| K3p: S_p [µs/przebieg] (95 %) | - | -5.46 (-13.69..+2.86) |
| K3p: Δ mediany slotów dotkniętych [µs] (95 %) | - | -2.58 (-3.39..-1.75) |
| H0 K3p (okna syntetyczne na C'): okna / S_H0 [µs] (95 %) / półszerokość [µs] | 2700 / +0.01 (-3.27..+3.64) / 3.45 | - |

- **K3p** (δ_S = 10 µs): S_p -5.46 (-13.69..+2.86) µs, H0 półszerokość 3.45 µs. Werdykt: **ZDANE**.
- **K4** (N = 16): p99 E_p = 1352.0 µs wobec 1000 µs. Werdykt: **NIEZDANE**.
- **K3**, compute_ns p50 per przebieg: mediana D2s - C' = -0.464 µs, rozrzut wewnątrz strony do 4.074 µs, δ = 6.413 µs, permutacyjny MW p = 0.796 - **bez regresji**.
- **K3**, wake_lag_ns p99 per przebieg: mediana D2s - C' = 6.584 µs, rozrzut wewnątrz strony do 22.051 µs, δ = 22.694 µs, permutacyjny MW p = 0.258 - **bez regresji**.
- **K3**, e2e_ns p99 per przebieg: mediana D2s - C' = 5.914 µs, rozrzut wewnątrz strony do 23.237 µs, δ = 69.161 µs, permutacyjny MW p = 0.161 - **bez regresji**.
- **K3t**, obrót bezczynny, średnia obcięta do p99 per przebieg: mediana D2s - C' = 0.826 µs, rozrzut wewnątrz strony do 0.821 µs, δ = 0.500 µs, permutacyjny MW p = 4.11e-05 - **REGRESJA D2s**.
- **K3t**, obrót bezczynny p50 (opisowo, reguła R603F) per przebieg: mediana D2s - C' = 0.000 µs, rozrzut wewnątrz strony do 1.000 µs, permutacyjny MW p = 0.0706 - **bez regresji**.
- **K3t**, obrót bezczynny p99 (opisowo, reguła R603F) per przebieg: mediana D2s - C' = -1.000 µs, rozrzut wewnątrz strony do 8.000 µs, permutacyjny MW p = 0.204 - **bez regresji**.

Przebiegi nieważne: brak.

### Koszt sondy na subskrybenta (K4, opisowo)

Prosta najmniejszych kwadratów median E_p przebiegów D2s względem N: nachylenie 71.51 µs na subskrybenta, wyraz wolny 48.12 µs; p50 E_p = 1 ms przy N ≈ 13 (ekstrapolacja).
K3t: d (średnia obcięta, mediana D2s - mediana C') według N: N = 1: +0.096 µs, N = 8: +0.478 µs, N = 16: +0.826 µs.

### Werdykty

| N | K3p | K4 | K3 compute p50 | K3 wake p99 | K3 e2e p99 | K3t |
|---|---|---|---|---|---|---|
| 1 | NIEZDANE | - | bez regresji | bez regresji | bez regresji | bez regresji |
| 8 | NIEROZSTRZYGNIĘTE | - | bez regresji | bez regresji | bez regresji | bez regresji |
| 16 | ZDANE | NIEZDANE | bez regresji | bez regresji | bez regresji | REGRESJA D2s |
