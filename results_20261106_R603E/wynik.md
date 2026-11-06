# R603E - wynik

Badanie: pomiar potwierdzający wyrównanie porcji drenażu i P0 do przerwy po slocie (C'', `d105498a`) wobec porcji bez wyrównania (C', `e0857dc8`) z michalwidera/retractordb#603. Protokół i kryteria w `README.md` (`d41cb82`, przed pomiarem), aparatura i test parsera `9d750cd`, suchy przebieg `aefb241`, aneksy A1 i A2 zatwierdzone przez człowieka przed kampanią (`cbd285e`).

Kampania 2026-11-06 13:07:48 - ok. 14:38 (ostatni przebieg uruchomiony 14:36:34), pi400 bez restartu w trakcie, rodziny uc03, uc05, uc06, 9 par C' / C'' w kolejności ABBA, 30 podłączeń na przebieg: razem 54 przebiegi i 1620 podłączeń. Strony: C' = binarka R603D bez przebudowy (`xretractor` `e435618b...`, `xqry` `4e8dd234...`), C'' = `d105498a` + P1 (`xretractor` `81430762...`, `xqry` `da29c97b...`, build-info równe C'). Każdy przebieg był ważny: jeden wątek `SCHED_FIFO` z `VmLck` > 0, governor `performance`, uruchomiona binarka równa zbudowanej, `trace_overrun` = 0 przy buforze 65 536 kB, kod wyjścia silnika 0. Wszystkie 1620 klientów zakończyło się kodem -2 (SIGINT) i zostało zebranych (`reaped` = 1). Log kampanii kończy się `CAMPAIGN_COMPLETE`; kopia: `campaign.log`.

Surowe dane (korpus pod embargiem) poza tym repozytorium, w prywatnym `paper-arXiv`, katalog `rdb-experiment-embargo/R603E/`, w trzech częściach po rodzinach, każda z indeksem 108 plików (18 przebiegów × 6 plików), razem 324 pliki i 88 993 081 B:

| część | bajty | SHA-256 | indeks |
|---|---|---|---|
| `results_20261106_R603E_raw_uc03.tar.gz` | 20 591 965 | `1ff21555ba610d8eb162829ac2f5ed3d6ad96d5a3c3b80b517f8becafb41e681` | `results_20261106_R603E_raw_uc03.index.tsv` |
| `results_20261106_R603E_raw_uc05.tar.gz` | 39 780 072 | `0185534917e6579ba00d1c2a4a16a5573c87e9ae0f82676dfb72da4760e827c1` | `results_20261106_R603E_raw_uc05.index.tsv` |
| `results_20261106_R603E_raw_uc06.tar.gz` | 28 621 044 | `16f518a87bb191d9d79a4ba73760a25d7d7a55fe1d7bfd1250cfeaf55359d7b5` | `results_20261106_R603E_raw_uc06.index.tsv` |

Analiza: `analyze.py --raw <raw> --seed 6034`; pełny wydruk niżej, w części *Wydruk analizy*.

## Odpowiedź

**Bramka działa, ale nie obniża kosztu serii - zgodnie z przewidywaniem.** C'' praktycznie usuwa nakładanie porcji i P0 z liczeniem slotu: średnio 0,000 slotu narażonego na serię w uc03 i uc05 i 0,009 w uc06, wobec 0,28, 6,3 i 3,4 w C'. **K2e ZDANE w uc05 i uc06.** Łączny koszt serii na slotach dotkniętych (narażonych i następnych po oknach) się jednak nie zmienia. W uc03 wynosi +69,3 wobec +75,4 µs na serię, w uc05 +394,7 wobec +264,9 µs, a przedziały różnicy obejmują 0 w obu rodzinach. Do progu D1 (obniżenie o połowę) jest daleko, więc **K2s NIEZDANE w uc03 i uc05**. W uc06 **K2s NIEROZSTRZYGNIĘTE (miara)**: kontrola H0 ma półszerokość 824 µs wobec dopuszczalnych 646 µs. Seria wydłuża się w uc05 z 36 do 59 ms, a w uc06 z 22 do 30 ms. **K1'' ZDANE w uc03 i uc05.** W uc06 jest NIEZDANE według litery protokołu z powodu jednego zdarzenia martwego muteksu, którego parser nie klasyfikuje (*Odstępstwa*, punkt 1). Model stanu puli nie ma przy tym ani jednego naruszenia. Poza seriami nic się nie pogorszyło według kryterium K3.

| rodzina | takt | k | K1'' C'' (b) | K2e: E C' → C'' (95 %) | K2s: S C' → C'' [µs/serię]; T (95 %) | seria p50 C' → C'' [ms] | Δ mediany slotów dotkniętych C' → C'' [µs] | K3 |
|---|---|---|---|---|---|---|---|---|
| uc03 | 5 ms | 7 | **ZDANE** | 0,283 → 0,000 (0,000..0,000): opisowo (E(C') < 1) | +75,4 → +69,3; T +31,6 (+22,7..+41,4): **NIEZDANE** | 8,43 → 8,50 | +29,43 → +23,66 | bez regresji |
| uc05 | 1 ms | 31 | **ZDANE** | 6,321 → 0,000 (0,000..0,000): **ZDANE** | +264,9 → +394,7; T +262,2 (+132,8..+402,8): **NIEZDANE** | 36,26 → 59,27 | +2,70 → +2,82 | bez regresji |
| uc06 | 2 ms | 19 | **NIEZDANE** (1 zdarzenie poza klasyfikacją parsera) | 3,366 → 0,009 (0,000..0,022): **ZDANE** | +2583,9 → -75,5; T -1367,4 (-3512,1..+835,2): **NIEROZSTRZYGNIĘTE (miara)** | 22,36 → 30,10 | +11,30 → +7,89 | bez regresji wg kryterium (punkt K3) |

- **K2e: bramka robi to, co miała.** W 710 niezakłóconych seriach C'' są tylko 2 sloty narażone (uc06, 2 serie, +69,7 µs każdy); ich przyczyny nie badano. W uc03 kontrola dodatnia C' ma E = 0,28 (R603D 0,30), poniżej progu ważności 1, więc K2e jest tam opisowe, jak przewidziano. Limit 100 odroczeń nie zadziałał ani razu (0 kroków wymuszonych). Najdłuższe oczekiwanie P0 to 52 obroty w uc06 (okresowy slot ~48 ms), a obrotów z zamkniętą bramką w serii jest p50 21 (uc05) i 7 (uc06).
- **K2s: usunięcie nakładania nie zmienia kosztu.** Ważność miary jest spełniona w uc03 i uc05: dolna granica S(C') wynosi +67,9 i +189,1 µs, a półszerokość H0 3,8 µs wobec 18,9 µs i 34,0 µs wobec 66,2 µs (aneks A2). S(C'') - S(C') wynosi -6,1 µs (-17,7..+4,9) w uc03 i +129,7 µs (-23,9..+286,1) w uc05, u_S = 0,92 (0,78..1,07) i 1,49 (0,92..2,34). Na pojedynczym slocie dotkniętym nakładanie widać tylko w uc03 i uc06. Δ mediany spada tam o 5,8 i 3,4 µs, a w uc05 zostaje bez zmian (+2,70 → +2,82 µs). Wartości C'' leżą bliżej slotu następnego z *Ustaleń*, punkt 1 (+27, +4,3, +11,7 µs), niż zera, zgodnie z *Przewidywaniem*, punkt 4. Seria jest dłuższa, ale dotyka podobnej liczby slotów (uc05 31,8 → 28,8, uc03 2,2 → 2,5, uc06 12,1 → 16,0). Koszt porzucenia pozostaje więc kosztem przeczytania kolejki, gdziekolwiek w takcie wypadnie porcja.
- **uc06: miara bez rozdzielczości i z obciążeniem pod H0.** Syntetyczne serie C'' na tle C' dają S = -1225,5 µs (-2042,2..-394,2). Przedział nie obejmuje 0, a półszerokość 824 µs przekracza 0,25 · S(C') = 646 µs. Wartości S w uc06 (C' +2584, C'' -76 µs) nie nadają się do interpretacji. W *Ustaleniach*, punkt 2, H0 na danych R603D dało -418 (-1926..+1248) µs.
- **K1'': mechanizm puli bez naruszeń.** We wszystkich rodzinach i na obu stronach model stanu puli ma 0 naruszeń, a O6 (kolejka utworzona przy jedynym wpisie niegotowym) wynosi w C'' 0 wszędzie, wobec 2 w C' w uc05. Warunek (a) opisowo: serii niegotowych przed startem następnego klienta jest w C'' 1 / 8 / 6 (uc03 / uc05 / uc06) przy oczekiwanych 0,9 / 6,3 / 3,1, a w C' 2 / 7 / 1 przy oczekiwanych 0,9 / 3,8 / 2,4. Liczba rośnie z długością serii, zgodnie z *Przewidywaniem*, punkt 6.
- **K3: bez regresji według kryterium; ogon uc06 do odnotowania.** W uc06 `wake_lag_ns` p99 i `e2e_ns` p99 per przebieg są w C'' wyższe o +358,2 i +358,5 µs przy rozrzucie wewnątrz strony do 484 i 477 µs. Kryterium regresji (różnica dodatnia i większa od rozrzutu) nie jest spełnione, ale permutacyjny MW daje p = 0,000494, więc przesunięcie jest systematyczne. Ogon tej rodziny to okresowy slot ~48 ms (p99 ~43-45 ms), a sloty kontrolne leżą poza seriami. W R603D ta sama wielkość dała C' - C = -377 µs (C' niżej, p = 8,2e-05). Obie kampanie są zgodne z tym, że niższy ogon uc06 ma binarka C' (`e0857dc8`), a nie że C'' go podnosi; przyczyny nie ustalono (*Granice wniosków*). W uc03 `compute_ns` p50 wynosi -0,54 µs (p = 0,0487, C'' szybszy), poza tym brak różnic.
- **O1, O2 bez zmian wobec C'.** `futex` wątku slotu występuje w 0,032-0,104 % slotów, a `FUTEX_WAIT` na muteksie kolejki 1-7 razy na rodzinę i stronę, max 42 µs, nigdy w oknie P0. Okno podłączenia z puli ma p50 0,049-0,050 ms, a kolejki utworzonej 2,8 / 9,9 / 6,4 ms (uc03 / uc05 / uc06), jak w R603D.

## Odstępstwa od protokołu i od przewidywania

1. **K1'' uc06: martwy muteks w dwóch położeniach, których parser R603C nie klasyfikuje.** Werdykt podano według litery protokołu (NIEZDANE na obu stronach w uc06), bez zmiany `analyze.py` po obejrzeniu danych. Oba zdarzenia rozpoznano w śladzie:
   - **C'' `Cpp_03`, klient 16** (kolejka wzięta z puli): 0,9 ms po pierwszym wierszu klienta wątek komunikacyjny wykonuje `openat` z sukcesem, a zaraz potem `munmap` i `unlinkat` kolejki, bez `kill(pid, 0)`. `inspectProcess` znalazł jeszcze proces klienta, bo rodzic zebrał go 0,5 ms później. Według kodu (`poolAbandonedQueue`: zombie oznacza „nie wiem”) kolejka idzie wtedy do zwolnienia, nie do puli. Porzucenie wpadło ~1 ms po śmierci klienta, a kolejka z puli była pusta, więc mogła się nie zmieścić tylko z powodu martwego muteksu (klient zabity w trakcie odbioru). Parser uznaje martwy muteks tylko na ścieżce `kill` = -ESRCH, więc liczy to zdarzenie jako niewyjaśnioną parę w fazie pracy i zwolnienie bez puli. Po zaliczeniu go do wyłączeń C'' ma w uc06 5 z 270 wyłączeń (1,9 % ≤ 5 %) i pozostałe warunki K1'' spełnione.
   - **C' `Cp_09`, ostatni klient**: martwy muteks na ścieżce `kill` = -ESRCH (parser go rozpoznaje i wyłącza), ale para `munmap` + `unlinkat` wypada po ostatnim starcie, czyli w ogonie. Parser odejmuje pary martwego muteksu tylko w fazie pracy, więc w ogonie liczy ją jako parę poza przepełnieniem (spójność ogona NIE).

   Oba przypadki dotyczą klasyfikacji w aparaturze, nie działania puli. Czy przyjąć je jako wyłączenia (wtedy K1'' uc06 ZDANE na obu stronach), rozstrzyga człowiek (*Skutek*, punkt 3).
2. **Model bramki a obrót graniczny: Pk+1 w C''.** Obrót Pk+1 w C'' ma p99 64 / 94 / 63 µs (uc03 / uc05 / uc06), wobec 20 / 31 / 21 µs w C'. Pk+1 dłuższe od p99 obrotu bezczynnego swojego przebiegu ma 7 z 243, 30 z 235 i 30 z 232 serii. W 2, 28 i 27 z nich wśród P1..Pk jest obrót graniczny (≤ 20 µs od granicy bramki), który model uznał za otwarty. Wyjaśnienie zgodne z danymi: w takim obrocie kod odroczył porcję, więc ostatnia rzeczywista porcja przesunęła się na obrót, który model nazywa Pk+1. Aneks A1 wyłącza z warunku Pk+1 tylko serie z obrotem granicznym w Pk lub Pk+1. Dlatego G2' liczone per przebieg na danych kampanii nie jest spełnione na warunku Pk+1 we wszystkich 9 przebiegach C'' uc05 i uc06 oraz w 3 uc03. W uc05 w 7 z 9 przebiegów nie jest spełniony także pierwszy warunek: dłuższych od p99,9 obrotu bezczynnego jest 98,0-98,9 % pełnych porcji modelu. Razem to 90 z 6634 obrotów (1,4 %), najkrótszy 13 µs, czyli obroty, które model uznał za porcję, choć wyglądają na bezczynne; przyczyny nie ustalono. W uc03 i uc06 pierwszy warunek jest spełniony w każdym przebiegu. Obroty zamknięte w modelu (drugi warunek) są we wszystkich przebiegach w ≥ 99,2 % nie dłuższe niż p99,9 obrotu bezczynnego. Bramki G dotyczą suchego przebiegu (*Kolejność*, punkt 4), w którym były spełnione. Skutek dla kryteriów:
   - porcja przesunięta na Pk+1 nie jest oknem serii, więc slot następny po niej może nie wejść do slotów dotkniętych. S(C'') jest wtedy zaniżone, czyli NIEZDANE K2s jest wnioskiem ostrożnym;
   - okno modelu bez porcji (1,4 % w uc05) dokłada najwyżej slot następny, który rzeczywista porcja w kolejnym obrocie i tak zwykle dotyka. Żeby T w uc05 zeszło z dolnej granicy +132,8 µs do 0, S(C'') musiałoby spaść o ~1/3, więc błąd tego rzędu nie zmienia werdyktu;
   - na K2e przesunięcie wpływa tylko przez porcję dłuższą od rezerwy, bo kod puścił przesuniętą porcję przy otwartej bramce.
3. **G1 na danych kampanii w uc06.** W 7 z 18 przebiegów uc06 (4 C', 3 C'') najdłuższy odstęp obrotów poza podłączeniami i seriami wynosi 5,27-5,61 ms przy progu G1 5 ms. Pozostałe warunki G1 są spełnione (`trace_overrun` 0, pełne pokrycie śladu, odstęp p50 1092 µs). To samo jest w uc06 R603D (6 z 18 przebiegów, 5,21-5,32 ms, obie strony), więc to własność rodziny, nie tej kampanii. Odstęp leży poza oknami serii i nie wchodzi do K2. G3 i G4 są spełnione we wszystkich 54 przebiegach, a H na obu stronach we wszystkich rodzinach.
4. **K2e uc03 opisowo.** Warunek ważności „E(C') > 1” liczono na dolnej granicy przedziału. Tutaj również wartość punktowa (0,283) jest < 1, więc werdykt nie zależy od tej interpretacji.
5. **Aneksy A1 i A2** (G2': obroty zamknięte do p99,9, Pk+1 bez obrotu granicznego w Pk/Pk+1; H0 K2s: 5 serii syntetycznych na serię C') zapisano po suchym przebiegu i zatwierdzono przed kampanią.
6. **Przewidywanie wobec wyniku.**
   - Sprawdziło się:
     - K2e ZDANE w uc05 i uc06;
     - K2s NIEZDANE w uc03 i uc05, NIEROZSTRZYGNIĘTE (miara) w uc06;
     - Δ mediany bliżej slotu następnego niż zera;
     - limit odroczeń nie zadziałał;
     - K3 według kryterium bez regresji;
     - warunek (a) rośnie z długością serii.
   - Długość serii: uc05 59,3 ms wobec przewidywanych ~55 ms, uc06 30,1 wobec ~31 ms, uc03 8,50 wobec ~9,0 ms.
   - Nie sprawdziło się:
     - oczekiwanie P0 w uc05 ma p50 3 obroty wobec przewidywanego średnio ~1;
     - K1'' w uc06 (punkt 1).

## Granice wniosków

- Jedna platforma: Cortex-A72, wspólne L2 1 MiB, jądro 6.8 `PREEMPT_RT`. Ustalenie, że koszt to wyparcie z L2, a nie nakładanie w czasie, dotyczy tej hierarchii pamięci.
- Okna serii C'' wyznacza model bramki ze śladu i `slots.csv`, a nie zapis decyzji kodu. Obroty graniczne (≤ 20 µs od granicy) są niepewne w obie strony. Kierunek błędu dla K2s opisano w *Odstępstwach*, punkt 2.
- S to średnia sum odchyleń, czuła na długi ogon. W uc05 S(C'') > S(C') o +130 µs, ale przedział różnicy obejmuje 0, więc nie wykazano ani poprawy, ani pogorszenia. Δ mediany (odporna na ogon) jest na obu stronach równa.
- W uc06 miara S jest pod H0 obciążona (-1,2 ms) i nie ma rozdzielczości. Wynik w tej rodzinie nie rozstrzyga K2s w żadną stronę.
- Ogon K3 w uc06 (+358 µs) i jego odwrotność w R603D (-377 µs) to porównania różnych par binarek w różnych kampaniach. Kandydatka na przyczynę - inny układ kodu binarki C' - jest hipotezą, której nie sprawdzono.
- Liczba naruszeń warunku (a) zależy od rytmu podłączeń aparatury (start co ~2,5 s), jak w R603D.

## Skutek dla naprawy (do decyzji człowieka)

C'' (`d105498a`) jest tylko na `dev/muro` (w `origin/dev/muro`, poza `master`). Pomiar pokazał, że wyrównanie do przerwy po slocie usuwa nakładanie, ale nie obniża kosztu serii, a wydłuża ją o 63 % w uc05 i 35 % w uc06. Możliwe kierunki:

1. **Wycofać C'' z `dev/muro`** (`git revert d105498a` przed następnym pull requestem do `master`). Według uzasadnienia D1 C'' przyjęłoby tylko wyraźne obniżenie kosztu, a tego nie ma. C'' dokłada 3 stałe, publikację terminu przez wątek slotu i bramkę w dwóch miejscach wątku komunikacyjnego, bez zysku na kryterium głównym. Wyraźny zysk jest tylko w K2e i w O6 (uc05 2 → 0, przy małej liczności).
2. **Zostawić C''**, jeśli brak nakładania z liczeniem slotu ma wartość sam w sobie, np. jako gwarancja czasu dla przyszłych rodzin z dłuższymi porcjami. Koszt: dłuższa seria i częstsze naruszenie (a).
3. **Klasyfikacja martwego muteksu w parserze** (*Odstępstwa*, punkt 1): w następnej aparaturze #603 uznawać martwy muteks także przy znalezionym procesie (zwolnienie bez `kill`, ~1 ms po śmierci klienta) i w ogonie. Zmiana z testem parsera na danych R603E.
4. **Następny krok #603: mniej danych do przeczytania.** Koszt idzie za ilością przeczytanej kolejki, nie za chwilą odczytu. Jedyna dźwignia, która zostaje, to kierunek 2 z R603D: wcześniejsze rozpoznanie śmierci klienta, ~10 razy mniej komunikatów. Mierzony miarą slotów dotkniętych (D2), względem C'.

Rekomendacja: 1 (wycofać C'') i 4 jako następny wariant mierzony tą samą aparaturą po poprawce z punktu 3; ogon K3 uc06 sprawdzić tylko wtedy, gdy kierunek 4 trafi do pomiaru tych samych binarek.

## Odtworzenie od zera

Wszystko na workerze `pi400` z katalogu `~/R376/apparatus_R603E` (kopia tego katalogu), poza analizą:

1. Korpus uc03, uc05, uc06 jak w R600 (`results_20261104_R600/wynik.md`, *Odtworzenie od zera*, punkt 3) do `/dev/shm/r376/data/<rodzina>`; `streams.tsv` z `~/R376/apparatus_R600` (tylko na workerze). Sprawdzenie: skróty SHA-256 drzew z README R603C (*Suchy przebieg*, punkt 2).
2. Binarka C': `~/R376/bin/R603D_Cp` z R603D (`results_20261105_R603D/wynik.md`, *Odtworzenie od zera*, punkt 2), suma sprawdzana przez `build_ab.sh` i `campaign.sh`. Budowa C'': `setsid nohup ./build_ab.sh > ~/R376/build_R603E.log 2>&1 < /dev/null &` (przyrostowo po C', ~22 min; źródła z `origin`, `d105498a` musi być wypchnięty).
3. Kampania: `setsid nohup ./campaign.sh > ~/R376/campaign_R603E.log 2>&1 < /dev/null &` (~1,5 h). Przerwana rodzina = powtórzyć całą (ABBA).
4. Analiza na hoście: `rsync -a <worker>:R376/raw_R603E/ <katalog>/raw/` albo trzy części archiwum rozpakowane do jednego katalogu (`tar xzf <część> -C <katalog>`, sprawdzenie każdej z jej indeksem jak w README `rdb-experiment-embargo`), potem Python ≥ 3.10 z NumPy (np. `retractordb/.venv-python/bin/python3`) `-I analyze.py --raw <katalog>/raw --seed 6034` z tego katalogu (importuje `../results_20261105_R603D/analyze.py`, a ten `../results_20261105_R603C/analyze.py`). Część *Wydruk analizy* to ten wydruk bez pierwszego wiersza i z nagłówkami obniżonymi o jeden poziom: `analyze.py ... --out w.txt && sed 's/^#/##/' w.txt | tail -n +2` musi dać ją bajt w bajt. Sprawdzone 2026-11-06 na archiwum rozpakowanym od nowa (3 indeksy zgodne, 324 pliki, drzewo identyczne z danymi z workera, wydruk identyczny); czas analizy ~6 min.
5. Diagnostyka *Odstępstw* (punkty 1-3) to odczyt śladu i pól `base.k1`, `gate.boundary`, `after` wyniku `analyze()` z tego katalogu (`analyze_run_e` dla C'') oraz `analyze.py --gates` (bramki per przebieg, także na danych kampanii; w R603D: `--gates` na samej części uc06). Skrypty diagnostyczne nie należą do aparatury: wypisują tylko liczby wyprowadzone, podane wyżej.

## Wydruk analizy

Źródło: `raw`, ziarna: placebo 6034, bootstrap 6035, H0 6036, pseudo-zdarzenia 6037.

Parametry H0 K2s uc03 (z C''): P0 312.0 µs, porcja 77.0 µs, obrót 1156.0 µs, faza 120..1122 µs, rozrzut 60 µs.

### uc03

Takt slotu: 5.000 ms, H = 8, k = 7 (z pojemności mmap: [7], pojemność [2000]).

| wielkość | C' | C'' |
|---|---|---|
| przebiegi / podłączenia | 9 / 270 | 9 / 270 |
| serie: niezakłócone / przepełnienia / zakłócone | 240 / 27 / 3 | 243 / 27 / 0 |
| O5: powody zakłóceń | wywolanie w P1..Pk: renameat | - |
| O3: P0 [µs] p50 / p99 / max | 313.0 / 391.0 / 400.0 | 312.0 / 396.0 / 452.0 |
| O3: faza P0 po końcu slotu [µs] p5 / p50 / p95 | 114.5 / 609.5 / 1103.3 | 119.8 / 606.9 / 1121.9 |
| O3: faza porcji P1..Pk po końcu slotu [µs] p5 / p50 / p95 | -152.4 / 2287.4 / 4450.5 | 306.8 / 2305.1 / 4358.9 |
| O3: pełna porcja P1..Pk-1 [µs] p50 / p99 / max | 76.0 / 125.0 / 553.0 | 77.0 / 132.0 / 560.0 |
| O3: ostatnia porcja Pk [µs] p50 / p99 / max | 64.0 / 129.0 / 131.0 | 65.0 / 117.0 / 120.0 |
| O3: obrót Pk+1 [µs] p50 / p99 / max | 14.0 / 20.0 / 53.0 | 14.0 / 64.0 / 90.0 |
| O3: obrót bezczynny [µs] p50 / p99 / max | 13.0 / 25.0 / 1003.0 | 13.0 / 25.0 / 1020.0 |
| O3: odstęp obrotów w serii [µs] p50 / p99 / max | 1154.0 / 1208.0 / 1635.0 | 1156.0 / 1214.0 / 1640.0 |
| O3: seria P0..Pk [ms] p50 / max | 8.430 / 8.923 | 8.496 / 12.874 |
| O3: oczekiwanie P0 [obroty, górna granica] p50 / p99 / max | - | 1 / 3 / 4 |
| O3: P0 w obrocie z zamkniętą bramką modelu (z tego graniczne) | - | 2 (2) z 243 |
| O3: obroty z zamkniętą bramką w serii p50 / max | - | 0 / 4 |
| O3: kroki wymuszone limitem odroczeń / obroty graniczne w seriach | - | 0 / 24 |
| K2e: sloty narażone na serię E (95 % bootstrap) | 0.283 (0.233..0.342) | 0.000 (0.000..0.000) |
| K2s: serie z placebo / sloty dotknięte na serię | 240 / 2.2 | 243 / 2.5 |
| K2s: S = suma odchyleń slotów dotkniętych na serię ponad placebo [µs] (95 %) | +75.4 (+67.9..+83.7) | +69.3 (+61.8..+78.4) |
| K2s: Δ mediany slotów dotkniętych [µs] (95 %) | +29.43 (+26.48..+31.37) | +23.66 (+22.84..+24.88) |
| opisowo: Δ mediany slotów następnych po oknach [µs] (95 %) | +29.43 (+26.38..+31.31) | +23.66 (+22.84..+24.77) |
| H0 K2s (syntetyczne serie C'' na tle C'): serie / S [µs] / Δ mediany [µs] | - | 1181 / +3.0 (-0.5..+7.2) / +0.04 (-0.04..+0.11) |
| opisowo K2a R603D Δ_c [µs]; n slotów; serie z narażeniem | +42.31 µs (+34.98..+82.54); n = 68, serie 68/240 | 0 slotów (243 serii) |
| opisowo O4 R603D: sloty narażone / suma odchyleń na serię ponad placebo [µs] (średnie) | -0.00 / 17.8 | 0.00 / 0.0 |
| kontrola e2e [µs] p50 / p99 / max | 170.2 / 2771.6 / 3530.5 | 169.1 / 2800.8 / 3431.4 |
| kontrola compute [µs] p50 / p99 / max | 127.2 / 2741.3 / 3387.8 | 126.6 / 2765.0 / 3208.0 |
| kontrola wake [µs] p50 / p99 / max | 23.9 / 29.6 / 101.4 | 23.7 / 33.5 / 107.3 |
| O1: futex wątku RT: sloty z futex / sloty w serii | 109 / 138315 (0.079 %) | 98 / 138761 (0.071 %) |
| O1: FUTEX_WAIT na muteksie kolejki: liczba / max [µs] / w oknie P0 / slot > takt | 2 / 40.0 / 0 / 0 | 1 / 13.0 / 0 / 0 |
| O2: podłączenie, kolejka utworzona: liczba / okno p50 [ms] | 45 / 2.791 | 45 / 2.807 |
| O2: podłączenie, kolejka z puli: liczba / okno p50 [ms] | 225 / 0.050 | 225 / 0.050 |
| O6: kolejka utworzona, gdy pula miała tylko wpisy niegotowe | 0 | 0 |

- **K1''** C'': do puli 270 z 270 (wyłączenia 0: martwy muteks 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 45 / 225, przepełnienia 27 (w ogonie: każdy przebieg ≥ 1 - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 1. Werdykt C'' (warunek (b)): **ZDANE**. Warunek (a) opisowo: serii niegotowych przed startem następnego klienta 1, oczekiwanych 0.9; O6 0.
- K1' C' (opisowo, powtórzenie R603D, werdykt z (b)): do puli 270 z 270 (wyłączenia 0: martwy muteks 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 45 / 225, przepełnienia 27 (w ogonie: każdy przebieg ≥ 1 - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 2. Werdykt C': ZDANE. Warunek (a): 2, oczekiwanych 0.9; O6 0.
- **K2e** (próg 0.2 slotu na serię): E(C'') 0.000 (0.000..0.000), kontrola dodatnia E(C') 0.283 (0.233..0.342). Werdykt C'': **opisowo (kontrola dodatnia C': dolna granica E(C') 0.23 ≤ 1)**.
- **K2s** (T = S(C'') - 0.5 · S(C')): T +31.6 (+22.7..+41.4) µs; S(C'') +69.3 (+61.8..+78.4), S(C') +75.4 (+67.9..+83.7) µs; S(C'') - S(C') -6.1 (-17.7..+4.9) µs; u_S 0.92 (0.78..1.07). Ważność: kontrola dodatnia tak, H0 półszerokość 3.8 µs wobec 18.9 µs. Werdykt: **NIEZDANE**.
- K2a R603D opisowo (δ_c = 5 µs): C'' 0 slotów (243 serii) - NIEROZSTRZYGNIĘTE (n = 0 slotów, 0 serii z narażeniem); C' +42.31 µs (+34.98..+82.54); n = 68, serie 68/240 - NIEROZSTRZYGNIĘTE (n = 68 slotów, 68 serii z narażeniem).
- **K3**, compute_ns p50 per przebieg: mediana C'' - C' = -0.54 µs, rozrzut wewnątrz strony do 2.19 µs, permutacyjny MW p = 0.0487 - w szumie.
- **K3**, wake_lag_ns p99 per przebieg: mediana C'' - C' = 7.59 µs, rozrzut wewnątrz strony do 25.92 µs, permutacyjny MW p = 0.34 - w szumie.
- **K3**, e2e_ns p99 per przebieg: mediana C'' - C' = 9.80 µs, rozrzut wewnątrz strony do 142.23 µs, permutacyjny MW p = 0.136 - w szumie.

Parametry H0 K2s uc05 (z C''): P0 299.0 µs, porcja 79.0 µs, obrót 1158.0 µs, faza 94..1128 µs, rozrzut 60 µs.

### uc05

Takt slotu: 1.000 ms, H = 40, k = 31 (z pojemności mmap: [31], pojemność [8000]).

| wielkość | C' | C'' |
|---|---|---|
| przebiegi / podłączenia | 9 / 270 | 9 / 270 |
| serie: niezakłócone / przepełnienia / zakłócone | 234 / 27 / 9 | 235 / 27 / 8 |
| O5: powody zakłóceń | wywolanie w P1..Pk: fallocate, fstatfs, ftruncate, mmap, openat, unlinkat; wywolanie w P1..Pk: renameat | wywolanie w P1..Pk: renameat |
| O3: P0 [µs] p50 / p99 / max | 309.0 / 410.0 / 506.0 | 299.0 / 394.0 / 400.0 |
| O3: faza P0 po końcu slotu [µs] p5 / p50 / p95 | -75.3 / 361.7 / 854.2 | 94.0 / 443.5 / 1127.7 |
| O3: faza porcji P1..Pk po końcu slotu [µs] p5 / p50 / p95 | -407.5 / 405.2 / 1532.2 | 27.8 / 432.9 / 1426.1 |
| O3: pełna porcja P1..Pk-1 [µs] p50 / p99 / max | 77.0 / 132.0 / 641.0 | 79.0 / 131.0 / 637.0 |
| O3: ostatnia porcja Pk [µs] p50 / p99 / max | 30.0 / 80.0 / 117.0 | 31.0 / 93.0 / 187.0 |
| O3: obrót Pk+1 [µs] p50 / p99 / max | 14.0 / 31.0 / 59.0 | 14.0 / 94.0 / 114.0 |
| O3: obrót bezczynny [µs] p50 / p99 / max | 13.0 / 28.0 / 3528.0 | 13.0 / 27.0 / 3582.0 |
| O3: odstęp obrotów w serii [µs] p50 / p99 / max | 1157.0 / 1228.0 / 1725.0 | 1158.0 / 1219.0 / 1722.0 |
| O3: seria P0..Pk [ms] p50 / max | 36.256 / 40.242 | 59.267 / 98.179 |
| O3: oczekiwanie P0 [obroty, górna granica] p50 / p99 / max | - | 3 / 8 / 8 |
| O3: P0 w obrocie z zamkniętą bramką modelu (z tego graniczne) | - | 6 (6) z 235 |
| O3: obroty z zamkniętą bramką w serii p50 / max | - | 21 / 51 |
| O3: kroki wymuszone limitem odroczeń / obroty graniczne w seriach | - | 0 / 924 |
| K2e: sloty narażone na serię E (95 % bootstrap) | 6.321 (6.150..6.487) | 0.000 (0.000..0.000) |
| K2s: serie z placebo / sloty dotknięte na serię | 234 / 31.8 | 235 / 28.8 |
| K2s: S = suma odchyleń slotów dotkniętych na serię ponad placebo [µs] (95 %) | +264.9 (+189.1..+350.3) | +394.7 (+275.9..+527.8) |
| K2s: Δ mediany slotów dotkniętych [µs] (95 %) | +2.70 (+2.57..+2.88) | +2.82 (+2.65..+2.98) |
| opisowo: Δ mediany slotów następnych po oknach [µs] (95 %) | +2.78 (+2.61..+2.96) | +2.82 (+2.65..+3.00) |
| H0 K2s (syntetyczne serie C'' na tle C'): serie / S [µs] / Δ mediany [µs] | - | 1106 / -10.1 (-42.7..+25.4) / -0.02 (-0.04..+0.02) |
| opisowo K2a R603D Δ_c [µs]; n slotów; serie z narażeniem | +6.26 µs (+5.61..+6.91); n = 1479, serie 234/234 | 0 slotów (235 serii) |
| opisowo O4 R603D: sloty narażone / suma odchyleń na serię ponad placebo [µs] (średnie) | -0.04 / 125.5 | -0.01 / -0.3 |
| kontrola e2e [µs] p50 / p99 / max | 111.4 / 1025.6 / 1960.5 | 111.6 / 1022.2 / 1965.9 |
| kontrola compute [µs] p50 / p99 / max | 63.5 / 967.9 / 1714.7 | 63.5 / 966.0 / 1811.7 |
| kontrola wake [µs] p50 / p99 / max | 23.8 / 89.4 / 1073.3 | 23.6 / 87.5 / 1044.4 |
| O1: futex wątku RT: sloty z futex / sloty w serii | 245 / 700499 (0.035 %) | 224 / 700045 (0.032 %) |
| O1: FUTEX_WAIT na muteksie kolejki: liczba / max [µs] / w oknie P0 / slot > takt | 6 / 42.0 / 0 / 0 | 7 / 36.0 / 0 / 0 |
| O2: podłączenie, kolejka utworzona: liczba / okno p50 [ms] | 45 / 9.912 | 45 / 9.913 |
| O2: podłączenie, kolejka z puli: liczba / okno p50 [ms] | 225 / 0.050 | 225 / 0.049 |
| O6: kolejka utworzona, gdy pula miała tylko wpisy niegotowe | 2 | 0 |

- **K1''** C'': do puli 270 z 270 (wyłączenia 0: martwy muteks 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 45 / 225, przepełnienia 27 (w ogonie: każdy przebieg ≥ 1 - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 8. Werdykt C'' (warunek (b)): **ZDANE**. Warunek (a) opisowo: serii niegotowych przed startem następnego klienta 8, oczekiwanych 6.3; O6 0.
- K1' C' (opisowo, powtórzenie R603D, werdykt z (b)): do puli 270 z 270 (wyłączenia 0: martwy muteks 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 45 / 225, przepełnienia 27 (w ogonie: każdy przebieg ≥ 1 - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 7. Werdykt C': ZDANE. Warunek (a): 7, oczekiwanych 3.8; O6 2.
- **K2e** (próg 0.2 slotu na serię): E(C'') 0.000 (0.000..0.000), kontrola dodatnia E(C') 6.321 (6.150..6.487). Werdykt C'': **ZDANE**.
- **K2s** (T = S(C'') - 0.5 · S(C')): T +262.2 (+132.8..+402.8) µs; S(C'') +394.7 (+275.9..+527.8), S(C') +264.9 (+189.1..+350.3) µs; S(C'') - S(C') +129.7 (-23.9..+286.1) µs; u_S 1.49 (0.92..2.34). Ważność: kontrola dodatnia tak, H0 półszerokość 34.0 µs wobec 66.2 µs. Werdykt: **NIEZDANE**.
- K2a R603D opisowo (δ_c = 5 µs): C'' 0 slotów (235 serii) - NIEROZSTRZYGNIĘTE (n = 0 slotów, 0 serii z narażeniem); C' +6.26 µs (+5.61..+6.91); n = 1479, serie 234/234 - NIEZDANE.
- **K3**, compute_ns p50 per przebieg: mediana C'' - C' = 0.06 µs, rozrzut wewnątrz strony do 0.83 µs, permutacyjny MW p = 0.847 - w szumie.
- **K3**, wake_lag_ns p99 per przebieg: mediana C'' - C' = 7.19 µs, rozrzut wewnątrz strony do 40.24 µs, permutacyjny MW p = 1 - w szumie.
- **K3**, e2e_ns p99 per przebieg: mediana C'' - C' = 0.15 µs, rozrzut wewnątrz strony do 109.62 µs, permutacyjny MW p = 0.796 - w szumie.

Parametry H0 K2s uc06 (z C''): P0 313.0 µs, porcja 79.0 µs, obrót 1159.0 µs, faza 125..1100 µs, rozrzut 60 µs.

### uc06

Takt slotu: 2.000 ms, H = 5, k = 19 (z pojemności mmap: [19], pojemność [5000]).

| wielkość | C' | C'' |
|---|---|---|
| przebiegi / podłączenia | 9 / 270 | 9 / 270 |
| serie: niezakłócone / przepełnienia / zakłócone | 238 / 25 / 2 | 232 / 25 / 8 |
| O5: powody zakłóceń | wywolanie w P1..Pk: renameat | wywolanie w P1..Pk: fallocate, fstatfs, ftruncate, mmap, openat, unlinkat; wywolanie w P1..Pk: renameat |
| O3: P0 [µs] p50 / p99 / max | 314.0 / 410.0 / 440.0 | 313.0 / 414.0 / 434.0 |
| O3: faza P0 po końcu slotu [µs] p5 / p50 / p95 | -6442.1 / 603.0 / 1119.6 | 125.0 / 544.3 / 1100.1 |
| O3: faza porcji P1..Pk po końcu slotu [µs] p5 / p50 / p95 | -37453.9 / 593.4 / 1579.9 | 55.8 / 709.7 / 1374.2 |
| O3: pełna porcja P1..Pk-1 [µs] p50 / p99 / max | 78.0 / 131.0 / 1667.0 | 79.0 / 130.0 / 1456.0 |
| O3: ostatnia porcja Pk [µs] p50 / p99 / max | 48.0 / 91.0 / 104.0 | 49.0 / 97.0 / 102.0 |
| O3: obrót Pk+1 [µs] p50 / p99 / max | 14.0 / 21.0 / 80.0 | 14.0 / 63.0 / 81.0 |
| O3: obrót bezczynny [µs] p50 / p99 / max | 13.0 / 26.0 / 2344.0 | 13.0 / 27.0 / 3226.0 |
| O3: odstęp obrotów w serii [µs] p50 / p99 / max | 1157.0 / 1211.0 / 2751.0 | 1159.0 / 1215.0 / 2536.0 |
| O3: seria P0..Pk [ms] p50 / max | 22.359 / 23.999 | 30.099 / 90.135 |
| O3: oczekiwanie P0 [obroty, górna granica] p50 / p99 / max | - | 1 / 52 / 52 |
| O3: P0 w obrocie z zamkniętą bramką modelu (z tego graniczne) | - | 2 (1) z 232 |
| O3: obroty z zamkniętą bramką w serii p50 / max | - | 7 / 61 |
| O3: kroki wymuszone limitem odroczeń / obroty graniczne w seriach | - | 0 / 262 |
| K2e: sloty narażone na serię E (95 % bootstrap) | 3.366 (3.139..3.605) | 0.009 (0.000..0.022) |
| K2s: serie z placebo / sloty dotknięte na serię | 238 / 12.1 | 232 / 16.0 |
| K2s: S = suma odchyleń slotów dotkniętych na serię ponad placebo [µs] (95 %) | +2583.9 (+546.0..+4734.2) | -75.5 (-2083.8..+1934.6) |
| K2s: Δ mediany slotów dotkniętych [µs] (95 %) | +11.30 (+10.52..+12.28) | +7.89 (+7.31..+8.65) |
| opisowo: Δ mediany slotów następnych po oknach [µs] (95 %) | +11.50 (+10.89..+12.48) | +7.87 (+7.30..+8.62) |
| H0 K2s (syntetyczne serie C'' na tle C'): serie / S [µs] / Δ mediany [µs] | - | 1130 / -1225.5 (-2042.2..-394.2) / +0.00 (-0.04..+0.09) |
| opisowo K2a R603D Δ_c [µs]; n slotów; serie z narażeniem | +11.02 µs (+10.10..+12.28); n = 801, serie 237/238 | +69.71 µs (+65.54..+73.96); n = 2, serie 2/232 |
| opisowo O4 R603D: sloty narażone / suma odchyleń na serię ponad placebo [µs] (średnie) | 0.65 / 2019.6 | -0.28 / -0.5 |
| kontrola e2e [µs] p50 / p99 / max | 285.5 / 44642.4 / 47374.6 | 286.4 / 45007.8 / 48614.4 |
| kontrola compute [µs] p50 / p99 / max | 224.1 / 428.6 / 47256.9 | 224.4 / 464.8 / 48354.6 |
| kontrola wake [µs] p50 / p99 / max | 23.9 / 42686.1 / 45469.7 | 23.8 / 43049.3 / 46700.7 |
| O1: futex wątku RT: sloty z futex / sloty w serii | 353 / 346849 (0.102 %) | 363 / 350614 (0.104 %) |
| O1: FUTEX_WAIT na muteksie kolejki: liczba / max [µs] / w oknie P0 / slot > takt | 6 / 38.0 / 0 / 1 | 6 / 41.0 / 0 / 3 |
| O2: podłączenie, kolejka utworzona: liczba / okno p50 [ms] | 48 / 6.339 | 48 / 6.366 |
| O2: podłączenie, kolejka z puli: liczba / okno p50 [ms] | 222 / 0.050 | 222 / 0.050 |
| O6: kolejka utworzona, gdy pula miała tylko wpisy niegotowe | 0 | 0 |

- **K1''** C'': do puli 265 z 270 (wyłączenia 4: martwy muteks 4, niezebrany 0), pary w fazie pracy niewyjaśnione 1, zwolnienia bez puli niewyjaśnione 1, kolejki utworzone / z puli 48 / 222, przepełnienia 25 (w ogonie: każdy przebieg ≥ 1 - tak), spójność ogona NIE, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 6. Werdykt C'' (warunek (b)): **NIEZDANE**. Warunek (a) opisowo: serii niegotowych przed startem następnego klienta 6, oczekiwanych 3.1; O6 0.
- K1' C' (opisowo, powtórzenie R603D, werdykt z (b)): do puli 265 z 270 (wyłączenia 5: martwy muteks 5, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 48 / 222, przepełnienia 25 (w ogonie: każdy przebieg ≥ 1 - tak), spójność ogona NIE, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 1. Werdykt C': NIEZDANE. Warunek (a): 1, oczekiwanych 2.4; O6 0.
- **K2e** (próg 0.2 slotu na serię): E(C'') 0.009 (0.000..0.022), kontrola dodatnia E(C') 3.366 (3.139..3.605). Werdykt C'': **ZDANE**.
- **K2s** (T = S(C'') - 0.5 · S(C')): T -1367.4 (-3512.1..+835.2) µs; S(C'') -75.5 (-2083.8..+1934.6), S(C') +2583.9 (+546.0..+4734.2) µs; S(C'') - S(C') -2659.4 (-5528.1..+141.6) µs; u_S -0.03 (-1.05..1.10). Ważność: kontrola dodatnia tak, H0 półszerokość 824.0 µs wobec 646.0 µs. Werdykt: **NIEROZSTRZYGNIĘTE (miara: H0: półszerokość 824.0 µs > 0.25 · S(C') = 646.0 µs)**.
- K2a R603D opisowo (δ_c = 5 µs): C'' +69.71 µs (+65.54..+73.96); n = 2, serie 2/232 - NIEROZSTRZYGNIĘTE (n = 2 slotów, 2 serii z narażeniem); C' +11.02 µs (+10.10..+12.28); n = 801, serie 237/238 - NIEZDANE.
- **K3**, compute_ns p50 per przebieg: mediana C'' - C' = 0.07 µs, rozrzut wewnątrz strony do 11.46 µs, permutacyjny MW p = 0.328 - w szumie.
- **K3**, wake_lag_ns p99 per przebieg: mediana C'' - C' = 358.20 µs, rozrzut wewnątrz strony do 484.26 µs, permutacyjny MW p = 0.000494 - w szumie.
- **K3**, e2e_ns p99 per przebieg: mediana C'' - C' = 358.48 µs, rozrzut wewnątrz strony do 477.01 µs, permutacyjny MW p = 0.000494 - w szumie.

### Werdykty

| rodzina | K1'' C'' (b) | K2e C'' | K2s | K1' C' (b, opisowo) |
|---|---|---|---|---|
| uc03 | ZDANE | opisowo (kontrola dodatnia C': dolna granica E(C') 0.23 ≤ 1) | NIEZDANE | ZDANE |
| uc05 | ZDANE | ZDANE | NIEZDANE | ZDANE |
| uc06 | NIEZDANE | ZDANE | NIEROZSTRZYGNIĘTE (miara: H0: półszerokość 824.0 µs > 0.25 · S(C') = 646.0 µs) | NIEZDANE |
