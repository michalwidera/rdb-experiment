# R607 - wynik

Badanie: sonda życia subskrybentów rozłożona na kolejne obroty wątku komunikacyjnego (D2r, `4daec944`) wobec sondy w jednym obrocie (D2s, `75e7574c`), z michalwidera/retractordb#607. Protokół i kryteria w `README.md`: protokół zatwierdzony przed pomiarem `a2682df` (decyzje J0-J4 według rekomendacji), aparatura i test analizy `2519dba`, budowa D2r i suchy przebieg `a28f158`, aneks A1 zatwierdzony przez człowieka w trakcie kampanii, przed analizą `080cb95`.

Kampania trwała 2026-11-07 09:48:37 - 11:16:50 (ostatni przebieg uruchomiony 11:15:18) na pi400. Rodzina uc05, N = 1 / 8 / 16 długo żyjących klientów `xqry -s` bez `-m`, 9 par D2s / D2r w kolejności ABBA z rotacją N, okno pomiaru 60 s, po oknie faza zgonów (wszyscy klienci zabijani SIGKILL w losowej kolejności co U(1; 2) s): razem 54 przebiegi, 450 klientów i 450 zgonów. Strony: D2s = `~/R376/bin/R603F_D2s` (`xretractor` `7c02c52c...`, bez przebudowy), D2r = `~/R376/bin/R607_D2r` (`4daec944` + P1, `xretractor` `3b944eb00f53928d...`), `xqry` `4e8dd234...` z `R603D_Cp` po obu stronach, build-info równe. Log kończy się `CAMPAIGN_COMPLETE`; kopia: `campaign.log`. Od startu kampanii do jej końca sesja nie łączyła się z workerem: pierwsze logowanie po starcie było po 11:16:50.

**Ważność przebiegów: 53 z 54 według W1-W5.** Nieważny jest jeden przebieg, `uc05/N16/D2r_06`, odrzucony przez W4 (*Odstępstwa*, punkt 1). Zgodnie z protokołem nie był powtarzany. D2r przy N = 16 ma 8 ważnych przebiegów, czyli tyle, ile wymaga minimum liczności. We wszystkich 54 przebiegach:

- 1 wątek `SCHED_FIFO`;
- wątek komunikacyjny przypięty do rdzenia 0;
- governor `performance`;
- `trace_overrun` = 0, a w fazie zgonów `death_trace_overrun` = 0;
- kod wyjścia silnika 0 i 0 pozostałości;
- 0 zwolnień kolejki w oknie (W3);
- każdy klient żył na końcu okna z 799,9-800,0 wierszami/s;
- każdy klient zakończył się w fazie zgonów kodem -9 (W5).

Surowe dane (korpus pod embargiem) leżą poza tym repozytorium, w prywatnym `paper-arXiv`, w katalogu `rdb-experiment-embargo/R607/`. Są w trzech częściach po N. Każda część ma indeks 198 plików (18 przebiegów × 11 plików), razem 594 pliki:

| część | bajty | SHA-256 | indeks |
|---|---|---|---|
| `results_20261107_R607_raw_N1.tar.gz` | 28 580 354 | `ff9a11e83e073010eac8dc7401adda503f0aa2bcefcfeae258d60e0f389f4e37` | `results_20261107_R607_raw_N1.index.tsv` |
| `results_20261107_R607_raw_N8.tar.gz` | 35 680 197 | `c4ef0fae242cb0f5e2527186c7ada6dd13d550cdcb1ab2dac1579888a39fa33f` | `results_20261107_R607_raw_N8.index.tsv` |
| `results_20261107_R607_raw_N16.tar.gz` | 45 493 951 | `d1baaccee3e3481211babed18d8dd03d8f1e11dd22590d09be9afa536f291d6e` | `results_20261107_R607_raw_N16.index.tsv` |

Analiza: `analyze.py --raw <raw>` (ziarna domyślne 6034-6036). Pełny wydruk jest niżej, w części *Wydruk analizy*.

## Odpowiedź

**Rozłożenie sondy na obroty usuwa zależność obrotu wątku komunikacyjnego od N. Wykrycie zgonu mieści się w granicy, a wątek slotu nie traci.**

- **K4 ZDANE przy N = 16.** Obrót z sondą D2r jest dłuższy od mediany obrotu bezczynnego o p99 238 µs (p50 137, max 374 µs). Próg to 1 ms; na D2s ta sama nadwyżka wynosi p99 1371 µs.
- **K4n ZDANE.** Mediana E_p D2r rośnie o +0,81 µs na subskrybenta (95 %: +0,74..+0,88), przy progu 5 µs. Na D2s rośnie o +71,84 µs (+71,57..+72,14). Opisowo nachylenie p99 D2r wynosi +2,66 µs (+1,07..+4,05).
- **K0 ZDANE przy każdym N, na obu stronach.**
  - Każdy z 434 zgonów w ważnych przebiegach jest wykryty przez sondę w granicy: 9 / 72 / 128 na D2r, 9 / 72 / 144 na D2s.
  - L max: D2r 905,8 / 1000,2 / 999,4 ms, D2s 902,5 / 986,5 / 1000,3 ms.
  - Nie ma zwolnień bez puli ani wykryć bez zwolnienia w śladzie.
  - Granica P1 D2r (1,0115 / 1,022 / 1,034 s) ma więc zapas ≥ 21 ms, a granica D2s (1,010 s) zapas ≥ 9,7 ms.
- **K3 i K3t bez regresji przy każdym N.**
  - K3 obejmuje compute p50, wake p99 i e2e p99 na slotach kontrolnych.
  - K3t to średnia obrotu bezczynnego obcięta do p99: d = +0,02 / +0,16 / +0,12 µs przy δ_t = 0,5 µs.
  - Suchy przebieg pokazał +0,71 µs przy N = 16 z jednego przebiegu. Kampania tego nie potwierdziła.
- **K3p (opisowo): koszt na obrót z `inspectProcess` jest wykluczony; ryzyko z planu przy progu 10 µs/s jest wykluczone przy N = 1, a przy N = 8 i 16 nierozstrzygnięte.**
  - Hipoteza kosztu na obrót przewidywała ~128 / ~250 µs/s przy N = 8 / 16. Górne granice S(D2r) - S(D2s) wynoszą +40,8 i +22,6 µs/s.
  - Przy N = 8 różnica +23,2 µs/s (+6,8..+40,8) ma dolną granicę powyżej zera i powyżej półszerokości H0 (6,4 µs). Przebieg D2r dotyka ~9,8 slotu wobec ~1,8 na D2s, z mniejszym Δ mediany na slot (+1,09 wobec +2,37 µs). Przy N = 16 różnica wynosi -8,3 µs/s (-40,9..+22,6).
  - W każdym przypadku to < 0,05 ms czasu wątku slotu na sekundę.

| N | E_p p50 / p99 / max D2s [µs] | E_p p50 / p99 / max D2r [µs] | K4 | K0: L max D2s / D2r [ms] | K0 | K3 | K3t d [µs] | S(D2r) - S(D2s) [µs/s] (95 %); H0 półszerokość | K3p: ryzyko |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 124 / 202 / 276 | 125 / 178 / 255 | (opisowo) | 902,5 / 905,8 | **ZDANE** | bez regresji | +0,02 | +0,04 (-7,33..+7,27); 2,08 | wykluczone |
| 8 | 616 / 736 / 784 | 113 / 199 / 305 | (opisowo) | 986,5 / 1000,2 | **ZDANE** | bez regresji | +0,16 | +23,22 (+6,78..+40,77); 6,42 | nierozstrzygnięte |
| 16 | 1202 / 1371 / 1411 | 137 / 238 / 374 | **ZDANE** | 1000,3 / 999,4 | **ZDANE** | bez regresji | +0,12 | -8,29 (-40,93..+22,63); 12,42 | nierozstrzygnięte |

K4n: **ZDANE** (+0,81 µs na subskrybenta, δ_n = 5 µs).

- **Sonda D2r działa jak w kodzie.**
  - Każdy ważny przebieg D2r ma 60 przebiegów sondy, a każdy obrót z sondą ma dokładnie 1 udany `openat` i 0 nieudanych.
  - Przebiegi sondy mają dokładnie N kolejnych obrotów. Wyjątkiem jest jeden przebieg przecięty początkiem okna (`N16/D2r_03`), dopuszczony przez A1.
  - Odstęp początków przebiegów wynosi 1000,000-1001,130 ms.
  - Przebieg sondy trwa p50 0,139 / 8,64 / 18,81 ms przy N = 1 / 8 / 16, czyli ~1,1-1,2 ms na subskrybenta: sen 1 ms plus obrót z jednym `inspectProcess`.
- **Odtwarzalność R603G (strona D2s, opisowo):** E_p p50 / p99 mieści się w ±10 % R603G przy każdym N (124 / 202 wobec 124 / 187, 616 / 736 wobec 612 / 743, 1202 / 1371 wobec 1197 / 1352 µs).

## Odstępstwa od protokołu i od przewidywania

1. **Przebieg `uc05/N16/D2r_06` nieważny według W4.** Pierwszy udany `openat` wątku komunikacyjnego w oknie przypada 46 µs po `t0`, w obrocie, który zaczął się przed `t0`. Analiza odtwarza obroty ze zdarzeń w oknie, więc ten obrót nie jest odtworzony. Pierwsze 4 odtworzone obroty, od 1,22 ms po `t0`, to obroty z sondą. Jest to więc przebieg sondy przecięty początkiem okna, jak w A1, ale w odmianie, której A1 nie obejmuje: przecięty jest sam obrót, a nie tylko przebieg. Jeden `openat` zostaje poza obrotami, a litera W4 (0 `openat` poza obrotami) unieważnia przebieg. Zgodnie z *Kolejnością*, punkt 4, przebieg jest raportowany i nie był powtarzany. Liczność D2r przy N = 16 wynosi 8, czyli minimum; K4n liczono z 26 przebiegów D2r zamiast 27.
   - **Wrażliwość (opisowo, poza protokołem)** z tym przebiegiem uznanym za ważny:
     - werdykty bez zmian;
     - K4 p99 E_p 231 µs;
     - K0 144 / 144 w granicy;
     - K4n nachylenie +0,85 µs (+0,79..+0,92);
     - S(D2r) - S(D2s) przy N = 16: -10,49 (-41,03..+19,50) µs/s;
     - K3t d = +0,12 µs.
   - Wrażliwość policzono skryptem diagnostycznym, który ustawia ważność tego przebiegu i wywołuje `main_report`. Skrypt nie należy do aparatury.
2. **Przewidywanie z protokołu (tabela *Przewidywanie przed pomiarem*):**
   - **K4 ZDANE z zapasem ~4×: trafione.** Przewidywano E_p p50 / p99 D2r ~120-150 / ≤ 250 µs przy N = 8 / 16; zmierzono 113 / 199 i 137 / 238 µs. Przy N = 1 przewidywano ~124 / ~190, zmierzono 125 / 178 µs.
   - **K4n ZDANE z nachyleniem 0-3 µs: trafione** (+0,81 µs).
   - **K0 ZDANE i L max ≤ ~1,002 s na obu stronach: trafione** (max 1000,3 ms). 0 porzuceń z pełnej kolejki.
   - **K3 bez regresji, K3t d ≈ 0: trafione.** Slotów kontrolnych D2r jest przy N = 16 58 574 z 60 016 (97,6 %).
   - **K3p (bez przewidywania, dwie możliwości):**
     - Koszt na obrót (~N · 16 µs/s) jest wykluczony przy N = 8 i 16.
     - Koszt na przebieg (~0) zgadza się z danymi przy N = 1 i 16.
     - Przy N = 8 zostaje dodatni koszt +6,8..+40,8 µs/s, między obiema możliwościami. Jego mechanizm, jak mechanizm K3p w R603G, pozostaje nieznany.
   - **Odtwarzalność R603G w ±10 %: trafione** (największe odchylenie: p99 E_p przy N = 1, +8 %).
3. **Czas kampanii ~1,5 h wobec ~2,1 h w protokole** (po suchym przebiegu oszacowano ~1,6 h). Przebiegi przy N = 16 trwały ~2,0 min, przy N = 1 ~1,3 min.
4. **Obrót z wykryciem zgonu trwa przy N ≥ 8 ~7 ms na obu stronach (opisowo).** Rozkład z czasu wywołań wątku komunikacyjnego w tym obrocie, ze śladu fazy zgonów:
   - W obrotach, w których zawiera się zwolnienie kolejki zmarłego klienta, `munmap` i `unlinkat` zajmują razem p50 6,13-6,25 ms. Tak jest w 54 z 72 zgonów przy N = 8 i w 126 z 144 przy N = 16, czyli we wszystkich poza dwoma zgonami na przebieg; przy N = 1 w żadnym.
   - Reszta obrotu to p50 0,62 / 0,67 ms na D2r i 0,97 / 1,30 ms na D2s przy N = 8 / 16. Na D2s ten obrót zawiera cały przebieg N wywołań `inspectProcess`.
   - Przy N = 1 obrót z wykryciem trwa p50 ~0,47 ms.
   - Koszt zwolnienia kolejki jest taki sam na obu stronach, nie zależy od rozłożenia sondy i jest poza pytaniem R607. Rozkład policzono skryptem diagnostycznym ze zdarzeń `trace_death.txt`; skrypt nie należy do aparatury.
5. **Wstępne S w trybie `--gates` różni się od wyniku głównego** (np. N = 8 D2r: +39,84 wobec +38,89 µs), jak w R603G (*Odstępstwa*, punkt 6). Werdykty pochodzą z analizy głównej.

## Granice wniosków

- Jedna platforma (Cortex-A72, wspólne L2 1 MiB, jądro `PREEMPT_RT`), jedna rodzina (uc05), N ≤ 16. Większe N tylko przez ekstrapolację K4n i granicę P1. Przebieg sondy trwa ~1,1-1,2 ms na subskrybenta (przy N = 16 1,175 ms), więc odstęp 1 s między przebiegami utrzymuje się do N ≈ 850; powyżej wykrycie zgonu opóźnia się liniowo.
- Wątek komunikacyjny był przypięty sam do rdzenia 0 (jak R603G). We wdrożeniu bez przypięcia obrót z sondą płaci udział w CFS, ale za jedno `inspectProcess`, a nie za N.
- Faza zgonów miała same usunięcia z listy obserwowanych. Dopisanie klienta w trakcie przebiegu sondy (przed kursorem i za nim) sprawdza tylko test jednostkowy, a granica P1 dla tego przypadku nie jest zmierzona.
- Zgon tylko przez SIGKILL klienta na tym samym workerze i w tej samej przestrzeni PID.
- K3p nie ma kontroli dodatniej; rozdzielczość jest równa półszerokości H0 (2,1 / 6,4 / 12,4 µs). Mechanizm dodatniego K3p przy N = 8 jest nieznany.
- Tańszy `inspectProcess` jest poza zakresem: obrót z sondą nadal kosztuje ~110-140 µs.

## Skutek dla zgłoszenia (decyzja człowieka)

Wszystkie kryteria akceptacji pomiaru z michalwidera/retractordb#607 są spełnione: obrót z sondą nie zależy od N i ma p99 ≤ 1 ms przy N = 16, K3 jest bez regresji, a opóźnienie wykrycia zgonu mieści się w granicy P1. Kod D2r (`4daec944`) jest na `dev/muro`. Testy z P5 (`ninja test`, `ninja test-valgrind`, `ninja test_gate`, wiązanie Python) są zielone.

Możliwości:

- **(a) Przyjąć D2r.** `dev/muro` idzie do `master` pull requestem człowieka, a #607 zostaje zamknięte. K3p przy N = 8 (≤ ~41 µs/s, nierozstrzygnięte) jest zapisane jako znane i opisowe.
- **(b) Przed przyjęciem zbadać K3p przy N = 8** (nowe badanie z kontrolą dodatnią). Koszt to ≤ 0,05 ms czasu wątku slotu na sekundę, bez kryterium.

Rekomendacja: **(a)**. Kryteria rozstrzygające (K4, K4n, K0, K3, K3t) są spełnione przy każdym N. K3p z protokołu jest opisowe, a hipoteza kosztu na obrót, która mogła je zawyżyć N-krotnie, jest wykluczona.

## Decyzje człowieka po wyniku (2026-11-07)

1. **Wariant (a): D2r przyjęte.** `dev/muro` scalone z `master` pull requestem michalwidera/retractordb#609 (`3d83d4fe`), michalwidera/retractordb#607 zamknięte (*Skutek dla zgłoszenia*).
2. K3p przy N = 8 (+23,2 µs/s, +6,8..+40,8, nierozstrzygnięte) zostaje opisowe i znane, bez osobnego badania. Werdykty zostają w *Wydruku analizy* bez zmian.
3. R607 scalone do `main`.

## Odtworzenie od zera

Wszystko na workerze `pi400` z katalogu `~/R376/apparatus_R607` (kopia tego katalogu), poza analizą:

1. Korpus uc05 w `/dev/shm/r376/data/uc05` jak w R600 (`results_20261104_R600/wynik.md`, *Odtworzenie od zera*, punkt 3). `streams.tsv` z `~/R376/apparatus_R600` (tylko na workerze). Sprawdzenie: skrót SHA-256 drzewa z README R603C (*Suchy przebieg*, punkt 2).
2. Binarki: `~/R376/bin/R603F_D2s` (R603F) i `~/R376/bin/R607_D2r` (`build_ab.sh`: `4daec944` + `apparatus_R603F/P1_deadline_ns.patch`, sumy w `R607_D2r.sha256`). `campaign.sh` sprawdza sumy obu stron, sumę `xqry` z `R603D_Cp` i równość build-info.
3. Kampania: `cd ~/R376/apparatus_R607; setsid nohup ./campaign.sh > ~/R376/campaign_R607.log 2>&1 < /dev/null &` (~1,5 h). Do końca kampanii nie łączyć się z workerem. Przebieg nieważny według W1-W5 jest raportowany i nie jest powtarzany (liczność ≥ 8).
4. Analiza na hoście. Dane: `rsync -a <worker>:R376/raw_R607/ <katalog>/raw/` albo trzy części archiwum rozpakowane do jednego katalogu (`tar xzf <część> -C <katalog>`, każda sprawdzona swoim indeksem jak w README `rdb-experiment-embargo`). Potem z tego katalogu: Python ≥ 3.10 z NumPy (np. `retractordb/.venv-python/bin/python3`) `-I analyze.py --raw <katalog>/raw --out w.txt`. Skrypt importuje `../results_20261106_R603G/analyze.py`, a przez niego R603F i wcześniejsze. Część *Wydruk analizy* to ten wydruk bez pierwszego wiersza i z nagłówkami obniżonymi o jeden poziom: `sed 's/^#/##/' w.txt | tail -n +2` musi dać ją bajt w bajt. Sprawdzone 2026-11-07 na archiwum rozpakowanym od nowa: 3 indeksy zgodne, 594 pliki, drzewo identyczne z danymi z workera, wydruk identyczny poza nazwą katalogu źródła. Analiza trwa ~85 s.
5. Bramki per przebieg: `analyze.py --gates --raw <katalog>/raw`.

## Wydruk analizy

Źródło: `raw`, ziarna: placebo 6034, bootstrap 6035, H0 6036.

### N = 1

| wielkość | D2s | D2r |
|---|---|---|
| przebiegi: ważne / wszystkie | 9 / 9 | 9 / 9 |
| obroty z sondą na przebieg: min / max | 60 / 60 | 60 / 60 |
| przebiegi sondy na przebieg: min / max (w tym przecięte granicą okna) | 60 / 60 (0) | 60 / 60 (0) |
| odstęp początków przebiegów [ms] min / p50 / max | 1000.001 / 1000.544 / 1001.089 | 1000.001 / 1000.549 / 1001.089 |
| przebieg sondy [µs] p50 / p99 / max | 138.0 / 216.0 / 290.0 | 139.0 / 192.0 / 269.0 |
| K4: obrót z sondą [µs] p50 / p99 / max | 138.0 / 216.0 / 290.0 | 139.0 / 192.0 / 269.0 |
| K4: nadwyżka E_p [µs] p50 / p99 / max | 124.0 / 202.0 / 276.0 | 125.0 / 178.0 / 255.0 |
| obrót bezczynny [µs] p50 / p99 / max | 14.0 / 21.0 / 1341.0 | 14.0 / 22.0 / 297.0 |
| obrót bezczynny, średnia obcięta do p99 [µs] (mediana przebiegów) | 14.229 | 14.251 |
| sloty okna / kontrolne (średnio na przebieg) | 60001 / 59685 | 60001 / 59686 |
| compute p50 wszystkich slotów okna [µs] (mediana przebiegów) | 66.44 | 66.80 |
| e2e p99 wszystkich slotów okna [µs] (mediana przebiegów) | 1084.20 | 1084.18 |
| zajętość rdzeni 0-2 (średnio) | 0.068 | 0.071 |
| wiersze/s klienta: min / mediana | 800.0 / 800.0 | 800.0 / 800.0 |
| VmLck po podłączeniu [MiB] (mediana) | 97 | 97 |
| O1: futex wątku RT na przebieg / max [µs] | 49.4 / 65 | 42.2 / 67 |
| K3p: przebiegi sondy z placebo / sloty dotknięte na przebieg | 540 / 1.27 | 540 / 1.25 |
| K3p: S [µs/przebieg = µs/s] (95 %) | +16.81 (+11.45..+22.32) | +16.85 (+11.95..+22.06) |
| K3p: Δ mediany slotów dotkniętych [µs] (95 %) | +5.18 (+4.79..+5.67) | +5.39 (+5.07..+5.77) |
| H0 K3p (okna o długości przebiegów D2r na D2s): okna / S_H0 [µs] (95 %) / półszerokość [µs] | 2684 / +1.03 (-1.02..+3.14) / 2.08 | - |
| K0: zabici / w granicy / poza granicą / bez wykrycia (zwolnieni) / niewykryci | 9 / 9 / 0 / 0 / 0 | 9 / 9 / 0 / 0 / 0 |
| K0: granica L [s] | 1.0100 | 1.0115 |
| K0: L [ms] min / p50 / p99 / max | 98.7 / 416.7 / 902.5 / 902.5 | 71.8 / 469.7 / 905.8 / 905.8 |
| K0: wykryte, zwolnione bez puli / bez zwolnienia w śladzie / samotne wykrycia | 0 / 0 / 0 | 0 / 0 / 0 |
| K0: obrót z wykryciem [µs] p50 / p99 / max | 471.0 / 558.0 / 558.0 | 474.0 / 554.0 / 554.0 |
| K0: nachylenie L wobec pozycji w przebiegu [ms na pozycję] | - | - |

- K4 (opisowo przy N = 1): p99 E_p D2r = 178.0 µs, D2s = 202.0 µs.
- **K0** (-5 ms ≤ L ≤ 1.0115 s na D2r, ≤ 1.0100 s na D2s): D2r 9 z 9 w granicy, D2s 9 z 9. Werdykt: **ZDANE**.
- K3p (opisowo, J3): S(D2r) - S(D2s) = +0.04 (-7.33..+7.27) µs na sekundę, H0 półszerokość 2.08 µs. Ryzyko z planu (próg 10 µs/s): **wykluczone**.
- **K3**, compute_ns p50 per przebieg: mediana D2r - D2s = 0.369 µs, rozrzut wewnątrz strony do 1.648 µs, δ = 3.321 µs, permutacyjny MW p = 0.796 - **bez regresji**.
- **K3**, wake_lag_ns p99 per przebieg: mediana D2r - D2s = -1.737 µs, rozrzut wewnątrz strony do 13.165 µs, δ = 6.847 µs, permutacyjny MW p = 0.34 - **bez regresji**.
- **K3**, e2e_ns p99 per przebieg: mediana D2r - D2s = -0.041 µs, rozrzut wewnątrz strony do 12.798 µs, δ = 54.208 µs, permutacyjny MW p = 0.546 - **bez regresji**.
- **K3t**, obrót bezczynny, średnia obcięta do p99 per przebieg: mediana D2r - D2s = 0.023 µs, rozrzut wewnątrz strony do 0.539 µs, δ = 0.500 µs, permutacyjny MW p = 0.863 - **bez regresji**.
- **K3t**, obrót bezczynny p50 (opisowo, reguła R603F) per przebieg: mediana D2r - D2s = 0.000 µs, rozrzut wewnątrz strony do 0.000 µs, permutacyjny MW p = 1 - **bez regresji**.
- **K3t**, obrót bezczynny p99 (opisowo, reguła R603F) per przebieg: mediana D2r - D2s = 5.000 µs, rozrzut wewnątrz strony do 12.000 µs, permutacyjny MW p = 0.547 - **bez regresji**.
- Odtwarzalność R603G (strona D2s, opisowo): E_p p50 / p99 / max 124.0 / 202.0 / 276.0 µs wobec 124.0 / 187.0 / 218.0 µs; obrót bezczynny 14.0 / 21.0 / 1341.0 µs wobec 13.0 / 23.0 / 1753.0 µs.

Przebiegi nieważne: brak.

### N = 8

| wielkość | D2s | D2r |
|---|---|---|
| przebiegi: ważne / wszystkie | 9 / 9 | 9 / 9 |
| obroty z sondą na przebieg: min / max | 60 / 60 | 480 / 480 |
| przebiegi sondy na przebieg: min / max (w tym przecięte granicą okna) | 60 / 60 (0) | 60 / 60 (0) |
| odstęp początków przebiegów [ms] min / p50 / max | 1000.001 / 1000.552 / 1001.092 | 1000.002 / 1000.534 / 1001.130 |
| przebieg sondy [µs] p50 / p99 / max | 632.0 / 752.0 / 800.0 | 8641.0 / 8831.0 / 11221.0 |
| K4: obrót z sondą [µs] p50 / p99 / max | 632.0 / 752.0 / 800.0 | 129.0 / 215.0 / 321.0 |
| K4: nadwyżka E_p [µs] p50 / p99 / max | 616.0 / 736.0 / 784.0 | 113.0 / 199.0 / 305.0 |
| obrót bezczynny [µs] p50 / p99 / max | 16.0 / 32.0 / 462.0 | 16.0 / 34.0 / 1074.0 |
| obrót bezczynny, średnia obcięta do p99 [µs] (mediana przebiegów) | 15.805 | 15.962 |
| sloty okna / kontrolne (średnio na przebieg) | 60001 / 59652 | 60002 / 59172 |
| compute p50 wszystkich slotów okna [µs] (mediana przebiegów) | 101.83 | 101.67 |
| e2e p99 wszystkich slotów okna [µs] (mediana przebiegów) | 1286.20 | 1287.50 |
| zajętość rdzeni 0-2 (średnio) | 0.453 | 0.454 |
| wiersze/s klienta: min / mediana | 800.0 / 800.0 | 800.0 / 800.0 |
| VmLck po podłączeniu [MiB] (mediana) | 153 | 153 |
| O1: futex wątku RT na przebieg / max [µs] | 630.2 / 620 | 625.1 / 538 |
| K3p: przebiegi sondy z placebo / sloty dotknięte na przebieg | 540 / 1.83 | 540 / 9.84 |
| K3p: S [µs/przebieg = µs/s] (95 %) | +15.67 (+8.07..+22.98) | +38.89 (+24.04..+54.83) |
| K3p: Δ mediany slotów dotkniętych [µs] (95 %) | +2.37 (+2.01..+2.68) | +1.09 (+0.94..+1.26) |
| H0 K3p (okna o długości przebiegów D2r na D2s): okna / S_H0 [µs] (95 %) / półszerokość [µs] | 2657 / -0.97 (-7.46..+5.38) / 6.42 | - |
| K0: zabici / w granicy / poza granicą / bez wykrycia (zwolnieni) / niewykryci | 72 / 72 / 0 / 0 / 0 | 72 / 72 / 0 / 0 / 0 |
| K0: granica L [s] | 1.0100 | 1.0220 |
| K0: L [ms] min / p50 / p99 / max | 19.3 / 493.2 / 986.5 / 986.5 | 0.1 / 498.3 / 1000.2 / 1000.2 |
| K0: wykryte, zwolnione bez puli / bez zwolnienia w śladzie / samotne wykrycia | 0 / 0 / 0 | 0 / 0 / 0 |
| K0: obrót z wykryciem [µs] p50 / p99 / max | 6913.0 / 7738.0 / 7738.0 | 6699.0 / 7406.0 / 7406.0 |
| K0: nachylenie L wobec pozycji w przebiegu [ms na pozycję] | +17.07 | +10.28 |

- K4 (opisowo przy N = 8): p99 E_p D2r = 199.0 µs, D2s = 736.0 µs.
- **K0** (-5 ms ≤ L ≤ 1.0220 s na D2r, ≤ 1.0100 s na D2s): D2r 72 z 72 w granicy, D2s 72 z 72. Werdykt: **ZDANE**.
- K3p (opisowo, J3): S(D2r) - S(D2s) = +23.22 (+6.78..+40.77) µs na sekundę, H0 półszerokość 6.42 µs. Ryzyko z planu (próg 10 µs/s): **nierozstrzygnięte**.
- **K3**, compute_ns p50 per przebieg: mediana D2r - D2s = -0.167 µs, rozrzut wewnątrz strony do 4.390 µs, δ = 5.092 µs, permutacyjny MW p = 0.19 - **bez regresji**.
- **K3**, wake_lag_ns p99 per przebieg: mediana D2r - D2s = 0.119 µs, rozrzut wewnątrz strony do 20.072 µs, δ = 17.471 µs, permutacyjny MW p = 0.931 - **bez regresji**.
- **K3**, e2e_ns p99 per przebieg: mediana D2r - D2s = 1.241 µs, rozrzut wewnątrz strony do 18.755 µs, δ = 64.310 µs, permutacyjny MW p = 0.931 - **bez regresji**.
- **K3t**, obrót bezczynny, średnia obcięta do p99 per przebieg: mediana D2r - D2s = 0.157 µs, rozrzut wewnątrz strony do 0.709 µs, δ = 0.500 µs, permutacyjny MW p = 0.19 - **bez regresji**.
- **K3t**, obrót bezczynny p50 (opisowo, reguła R603F) per przebieg: mediana D2r - D2s = 0.000 µs, rozrzut wewnątrz strony do 1.000 µs, permutacyjny MW p = 0.576 - **bez regresji**.
- **K3t**, obrót bezczynny p99 (opisowo, reguła R603F) per przebieg: mediana D2r - D2s = 6.000 µs, rozrzut wewnątrz strony do 11.000 µs, permutacyjny MW p = 0.137 - **bez regresji**.
- Odtwarzalność R603G (strona D2s, opisowo): E_p p50 / p99 / max 616.0 / 736.0 / 784.0 µs wobec 612.0 / 743.0 / 765.0 µs; obrót bezczynny 16.0 / 32.0 / 462.0 µs wobec 15.0 / 33.0 / 992.0 µs.

Przebiegi nieważne: brak.

### N = 16

| wielkość | D2s | D2r |
|---|---|---|
| przebiegi: ważne / wszystkie | 9 / 9 | 8 / 9 |
| obroty z sondą na przebieg: min / max | 60 / 60 | 956 / 960 |
| przebiegi sondy na przebieg: min / max (w tym przecięte granicą okna) | 60 / 60 (0) | 60 / 60 (1) |
| odstęp początków przebiegów [ms] min / p50 / max | 1000.000 / 1000.333 / 1001.099 | 1000.000 / 1000.404 / 1001.118 |
| przebieg sondy [µs] p50 / p99 / max | 1219.0 / 1388.0 / 1428.0 | 18808.0 / 19217.0 / 20982.0 |
| K4: obrót z sondą [µs] p50 / p99 / max | 1219.0 / 1388.0 / 1428.0 | 154.0 / 255.0 / 391.0 |
| K4: nadwyżka E_p [µs] p50 / p99 / max | 1202.0 / 1371.0 / 1411.0 | 137.0 / 238.0 / 374.0 |
| obrót bezczynny [µs] p50 / p99 / max | 17.0 / 26.0 / 6701.0 | 17.0 / 27.0 / 1621.0 |
| obrót bezczynny, średnia obcięta do p99 [µs] (mediana przebiegów) | 17.069 | 17.189 |
| sloty okna / kontrolne (średnio na przebieg) | 60015 / 59630 | 60016 / 58574 |
| compute p50 wszystkich slotów okna [µs] (mediana przebiegów) | 126.70 | 125.61 |
| e2e p99 wszystkich slotów okna [µs] (mediana przebiegów) | 1407.14 | 1406.88 |
| zajętość rdzeni 0-2 (średnio) | 0.681 | 0.680 |
| wiersze/s klienta: min / mediana | 799.9 / 800.0 | 799.9 / 800.0 |
| VmLck po podłączeniu [MiB] (mediana) | 217 | 217 |
| O1: futex wątku RT na przebieg / max [µs] | 1580.1 / 2491 | 1565.8 / 2514 |
| K3p: przebiegi sondy z placebo / sloty dotknięte na przebieg | 540 / 2.41 | 479 / 20.04 |
| K3p: S [µs/przebieg = µs/s] (95 %) | -3.70 (-11.97..+4.80) | -11.99 (-43.42..+17.78) |
| K3p: Δ mediany slotów dotkniętych [µs] (95 %) | -2.79 (-3.69..-1.96) | -1.80 (-2.06..-1.54) |
| H0 K3p (okna o długości przebiegów D2r na D2s): okna / S_H0 [µs] (95 %) / półszerokość [µs] | 2625 / +2.13 (-10.31..+14.53) / 12.42 | - |
| K0: zabici / w granicy / poza granicą / bez wykrycia (zwolnieni) / niewykryci | 144 / 144 / 0 / 0 / 0 | 128 / 128 / 0 / 0 / 0 |
| K0: granica L [s] | 1.0100 | 1.0340 |
| K0: L [ms] min / p50 / p99 / max | 0.9 / 487.9 / 994.8 / 1000.3 | 7.2 / 553.0 / 998.4 / 999.4 |
| K0: wykryte, zwolnione bez puli / bez zwolnienia w śladzie / samotne wykrycia | 0 / 0 / 0 | 0 / 0 / 0 |
| K0: obrót z wykryciem [µs] p50 / p99 / max | 7436.0 / 8429.0 / 8483.0 | 6874.0 / 7560.0 / 7580.0 |
| K0: nachylenie L wobec pozycji w przebiegu [ms na pozycję] | -2.93 | -5.04 |

- **K4** (N = 16): p99 E_p D2r = 238.0 µs wobec 1000 µs (D2s: 1371.0 µs). Werdykt: **ZDANE**.
- **K0** (-5 ms ≤ L ≤ 1.0340 s na D2r, ≤ 1.0100 s na D2s): D2r 128 z 128 w granicy, D2s 144 z 144. Werdykt: **ZDANE**.
- K3p (opisowo, J3): S(D2r) - S(D2s) = -8.29 (-40.93..+22.63) µs na sekundę, H0 półszerokość 12.42 µs. Ryzyko z planu (próg 10 µs/s): **nierozstrzygnięte**.
- **K3**, compute_ns p50 per przebieg: mediana D2r - D2s = -1.008 µs, rozrzut wewnątrz strony do 4.073 µs, δ = 6.336 µs, permutacyjny MW p = 0.2 - **bez regresji**.
- **K3**, wake_lag_ns p99 per przebieg: mediana D2r - D2s = 1.623 µs, rozrzut wewnątrz strony do 14.183 µs, δ = 23.885 µs, permutacyjny MW p = 0.888 - **bez regresji**.
- **K3**, e2e_ns p99 per przebieg: mediana D2r - D2s = -0.253 µs, rozrzut wewnątrz strony do 14.190 µs, δ = 70.357 µs, permutacyjny MW p = 0.743 - **bez regresji**.
- **K3t**, obrót bezczynny, średnia obcięta do p99 per przebieg: mediana D2r - D2s = 0.120 µs, rozrzut wewnątrz strony do 0.486 µs, δ = 0.500 µs, permutacyjny MW p = 0.167 - **bez regresji**.
- **K3t**, obrót bezczynny p50 (opisowo, reguła R603F) per przebieg: mediana D2r - D2s = 0.000 µs, rozrzut wewnątrz strony do 0.000 µs, permutacyjny MW p = 1 - **bez regresji**.
- **K3t**, obrót bezczynny p99 (opisowo, reguła R603F) per przebieg: mediana D2r - D2s = -3.500 µs, rozrzut wewnątrz strony do 14.000 µs, permutacyjny MW p = 0.65 - **bez regresji**.
- Odtwarzalność R603G (strona D2s, opisowo): E_p p50 / p99 / max 1202.0 / 1371.0 / 1411.0 µs wobec 1197.0 / 1352.0 / 1920.0 µs; obrót bezczynny 17.0 / 26.0 / 6701.0 µs wobec 16.0 / 34.0 / 5093.0 µs.

Przebiegi nieważne: D2r_06 (W4).

### Niezależność od N (K4n)

- D2s: nachylenie median E_p przebiegów względem N +71.84 (+71.57..+72.14) µs na subskrybenta; nachylenie p99 (opisowo) +76.57 (+74.45..+78.55) µs.
- D2r: nachylenie median E_p przebiegów względem N +0.81 (+0.74..+0.88) µs na subskrybenta; nachylenie p99 (opisowo) +2.66 (+1.07..+4.05) µs.
- **K4n** (δ_n = 5 µs na subskrybenta, strona D2r). Werdykt: **ZDANE**.

### Werdykty

K4n: ZDANE.

| N | K4 | K0 | K3 compute p50 | K3 wake p99 | K3 e2e p99 | K3t | K3p: ryzyko (opisowo) |
|---|---|---|---|---|---|---|---|
| 1 | - | ZDANE | bez regresji | bez regresji | bez regresji | bez regresji | wykluczone |
| 8 | - | ZDANE | bez regresji | bez regresji | bez regresji | bez regresji | nierozstrzygnięte |
| 16 | ZDANE | ZDANE | bez regresji | bez regresji | bez regresji | bez regresji | nierozstrzygnięte |
