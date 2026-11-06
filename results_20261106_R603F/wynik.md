# R603F - wynik

Badanie: pomiar potwierdzający wcześniejsze rozpoznanie śmierci klienta przez sondę życia subskrybentów (D2s, `75e7574c`) wobec porcji bez wyrównania (C', `e0857dc8`) z michalwidera/retractordb#603. Protokół i kryteria w `README.md` (`1d6e2b9`, przed pomiarem), aparatura i test parsera `9aec324`, suchy przebieg `65874e9`, aneksy A1-A3 zatwierdzone przez człowieka przed kampanią (`7c42e0e`).

Kampania 2026-11-06 18:51:14 - ok. 20:22 (ostatni przebieg uruchomiony 20:20:22), pi400 bez restartu w trakcie (czas pracy od 07:27), rodziny uc03, uc05, uc06, 9 par C' / D2s w kolejności ABBA, 30 podłączeń na przebieg: razem 54 przebiegi i 1620 podłączeń. Strony: C' = binarka R603D bez przebudowy (`xretractor` `e435618b...`, `xqry` `4e8dd234...`), D2s = `75e7574c` + P1 (`xretractor` `7c02c52c...`, `xqry` `e5e359e6...`, build-info równe C'). Każdy przebieg był ważny: jeden wątek `SCHED_FIFO` z `VmLck` > 0, governor `performance`, uruchomiona binarka równa zbudowanej, `trace_overrun` = 0 przy buforze 65 536 kB, kod wyjścia silnika 0. Wszystkie 1620 klientów zakończyło się kodem -2 (SIGINT) i zostało zebranych (`reaped` = 1). Log kampanii kończy się `CAMPAIGN_COMPLETE`; kopia: `campaign.log`. W trakcie kampanii worker był odpytywany przez ssh co 30 s wbrew aneksowi A3 (*Odstępstwa*, punkt 1).

Surowe dane (korpus pod embargiem) poza tym repozytorium, w prywatnym `paper-arXiv`, katalog `rdb-experiment-embargo/R603F/`, w trzech częściach po rodzinach, każda z indeksem 108 plików (18 przebiegów × 6 plików), razem 324 pliki i 89 282 975 B:

| część | bajty | SHA-256 | indeks |
|---|---|---|---|
| `results_20261106_R603F_raw_uc03.tar.gz` | 20 760 214 | `96d2dfe2e9356a927b15cc564e9a6d1197fa18afbba03fc30d0313144f90dbd2` | `results_20261106_R603F_raw_uc03.index.tsv` |
| `results_20261106_R603F_raw_uc05.tar.gz` | 39 698 665 | `137b65a52630664409a998d75c1caa43825a9691b63bda112c8f6f05c2dfae2e` | `results_20261106_R603F_raw_uc05.index.tsv` |
| `results_20261106_R603F_raw_uc06.tar.gz` | 28 824 096 | `17309377ea3b4a6b24750c68d827d4e239aced8c86de193af90f3feeb5ac540c` | `results_20261106_R603F_raw_uc06.index.tsv` |

Analiza: `analyze.py --raw <raw> --seed 6034`; pełny wydruk niżej, w części *Wydruk analizy*.

## Odpowiedź

**D2s działa i obniża koszt serii zgodnie z przewidywaniem.** Każde porzucenie na D2s zaczyna się od wykrycia przez sondę, a na C' sonda nie wykrywa nic: **K0 ZDANE we wszystkich trzech rodzinach**. Wykrycie następuje 1,5-999 ms po zebraniu klienta (p50 0,50-0,55 s), przy 0 porzuceń z pełnej kolejki. D2s czyta średnio 105 / 403 / 258 komunikatów (uc03 / uc05 / uc06) zamiast pełnej kolejki 2000 / 8000 / 5000. Seria skraca się z 8,4 / 36,2 / 22,4 ms do 0,26 / 0,35 / 0,32 ms (p50). Łączny koszt serii na slotach dotkniętych spada z +65,9 do +23,0 µs w uc03 i z +226,8 do +25,8 µs w uc05, do 35 % i 11 % kosztu C'. **K2s ZDANE w uc03 i uc05.** W uc03 zapas jest mały: górna granica T to -1,9 µs. W uc06 **K2s NIEROZSTRZYGNIĘTE (miara)**: S(C') wyszło ujemne (-2103 µs), więc kontrola dodatnia nie jest spełniona. **K1'' ZDANE we wszystkich rodzinach.** W uc03 i uc05 pula tworzy 9 kolejek i oddaje 261, w uc06 13 i 257, przy 0 przepełnień. Poza seriami wątek slotu się nie pogorszył (K3). **K3t według litery kryterium daje regresję D2s w uc03**: p50 obrotu bezczynnego jest wyższe o 1 µs przy rozrzucie 0. Średnia pokazuje przesunięcie o +0,19..+0,26 µs na obrót we wszystkich trzech rodzinach (*Odstępstwa*, punkt 2).

| rodzina | takt | K0: wykrycia / z pełnej kolejki; L p50 / max [ms] | K1'' D2s (b) | K2s: S C' → D2s [µs/serię]; T (95 %) | seria p50 C' → D2s [ms] | sloty dotknięte na serię C' → D2s | Δ mediany slotów dotkniętych C' → D2s [µs] | K3 | K3t |
|---|---|---|---|---|---|---|---|---|---|
| uc03 | 5 ms | 270 / 0; 554 / 995: **ZDANE** | **ZDANE** | +65,9 → +23,0; T -10,0 (-17,6..-1,9): **ZDANE** | 8,43 → 0,26 | 2,2 → 1,2 | +26,89 → +17,10 | bez regresji | p50 +1 µs przy rozrzucie 0: **regresja według litery**; p99 w szumie |
| uc05 | 1 ms | 270 / 0; 502 / 998: **ZDANE** | **ZDANE** | +226,8 → +25,8; T -87,6 (-134,6..-43,9): **ZDANE** | 36,24 → 0,35 | 31,7 → 1,8 | +2,96 → +7,60 | bez regresji (compute p50 i e2e p99 D2s niżej poza szumem) | w szumie |
| uc06 | 2 ms | 266 / 0; 532 / 999: **ZDANE** | **ZDANE** | -2103,2 → -539,2; T +512,4 (-175,3..+1161,8): **NIEROZSTRZYGNIĘTE (miara)** | 22,35 → 0,32 | 12,6 → 1,3 | +10,72 → +16,04 | bez regresji według kryterium (ogon, punkt K3) | w szumie |

- **K0: mechanizm jak w kodzie.**
  - Opóźnienie wykrycia L ma rozkład zgodny z U(0; 1 s): p50 554 / 502 / 532 ms, p99 983-996 ms, max 995-999 ms, przy granicy 1,010 s.
  - Rozkład porcji po P0 zgadza się z *Ustaleniami*, punkt 6. n̂ średnio 105 / 403 / 258 wobec przewidywanych 100 / 402 / 250. P(k) w uc05 0,337 / 0,300 / 0,319 / 0,044 wobec 0,319 / 0,320 / 0,320 / 0,042, a w uc06 0,474 / 0,526 wobec 0,512 / 0,488. W uc03 zawsze k = 0. Serii granicznych jest 0 / 4 / 6.
  - Jedyne samotne wykrycie (uc06) towarzyszy martwemu muteksowi przy znalezionym procesie (*Ustalenia*, punkt 4).
  - Poświadczenie tożsamości przy subskrypcji jest widoczne w każdym podłączeniu: `openat` z sukcesem w oknach podłączeń to 1,12-1,16 na podłączenie w D2s i 0,50-0,55 w C', 0 poza oknami. Ponad liczbę wynikającą z poświadczeń (4 w podłączeniu z kolejką utworzoną, 1 z puli, z suchego przebiegu) zostaje ~5-6 na rodzinę. To zgodne z sondą na żywym kliencie (przewidywane ~10 na rodzinę), ale ślad tych przypadków nie rozróżnia.
- **K2s: koszt idzie za ilością przeczytanej kolejki.**
  - Ważność miary jest spełniona w uc03 i uc05. Dolna granica S(C') wynosi +57,4 i +142,5 µs. Półszerokość H0 dla serii o kształcie D2s to 2,3 µs wobec 16,5 µs i 3,4 µs wobec 56,7 µs.
  - S(D2s) - S(C') wynosi -42,9 µs (-53,8..-32,4) w uc03 i -201,0 µs (-290,7..-114,8) w uc05, przy u_S = 0,35 (0,25..0,47) i 0,11 (0,07..0,20).
  - S(D2s) jest bliskie przewidywaniu (*Ustalenia*, punkt 7): w uc03 +23,0 wobec ~+6..+27 µs, w uc05 +25,8 wobec ~+15..+21 µs.
  - Δ mediany pojedynczego slotu dotkniętego jest w D2s wyższa w uc05 i uc06, zgodnie z przewidywaniem (~+6 i ~+17 µs), bo seria D2s dotyka głównie slotu następnego po P0. Koszt spada, bo seria dotyka 1,2-1,8 slotu zamiast 2,2-31,7.
  - Slotów narażonych na serię (E) jest 0,16 / 0,47 / 0,34 wobec 0,34 / 6,40 / 3,57 w C'.
- **uc06: miara S bez znaku i rozdzielczości.** S(C') wynosi -2103 µs (-3348..-742), a w R603E dla tej samej binarki +2584 µs (+186..+4405). To dwie kampanie z przeciwnym znakiem. Miarę w tej rodzinie wyznacza ogon okresowego slotu ~48 ms (kontrola e2e p99 ~45 ms), a nie seria. Półszerokość H0 dla serii D2s (227 µs) zmieściłaby się w progu przy S(C') z R603E (646 µs), ale tutaj próg jest ujemny. Opisowo, poza kryterium, iloczyn slotów dotkniętych na serię i Δ mediany (miara odporna na ogon, nie suma odchyleń) daje 12,6 × 10,72 ≈ 135 µs w C' i 1,3 × 16,04 ≈ 21 µs w D2s. Ten kierunek zgadza się z uc03 i uc05.
- **K1'': pula bez naruszeń.**
  - D2s: do puli 270 / 270 / 266 z 270, a wyłączeń 0 / 0 / 4. Wszystkie 4 to martwy muteks, z tego 1 przy znalezionym procesie. Niewyjaśnionych par i zwolnień 0, spójność ogona tak, model puli 0 naruszeń.
  - Kontrola dodatnia (D4) jest spełniona: każdy przebieg C' ma przepełnienie w ogonie, a każdy przebieg D2s oddanie z puli.
  - Warunek (a) i O6 wynoszą w D2s 0 wszędzie. W C' warunek (a) to 0 / 5 / 1 (oczekiwane 0,9 / 3,9 / 2,3), a O6 1 w uc05.
  - C' (opisowo, poprawiona klasyfikacja martwego muteksu): ZDANE we wszystkich rodzinach, w uc06 z 6 wyłączeniami.
- **K3: bez regresji według kryterium; ogon uc06 do odnotowania.**
  - W uc05 D2s jest lepsze poza szumem: `compute_ns` p50 -1,65 µs, `e2e_ns` p99 -46,7 µs, p = 4,1e-05. Sloty kontrolne leżą poza seriami. Kandydatka na przyczynę - mniejsze wyparcie L2 przy ~20 razy mniejszym odczycie - to hipoteza, której nie sprawdzono.
  - W uc06 `wake_lag_ns` p99 i `e2e_ns` p99 są w D2s wyższe o +601 i +596 µs przy rozrzucie wewnątrz strony do 766 i 764 µs. Kryterium regresji nie jest spełnione, ale p = 4,1e-05. To trzecia para binarek z tym samym obrazem: C'' wobec C' w R603E +358 µs, C' wobec C w R603D -377 µs. Niższy ogon uc06 ma binarka C'. Zgodnie z decyzją po R603E (punkt 2) ogona nie badano osobno.
  - W uc03 `compute_ns` p50 jest niższe o -1,91 µs (p = 4,1e-05) przy rozrzucie 2,30 µs, czyli w szumie.
- **O1, O2 bez zmian wobec C'.**
  - `futex` wątku slotu występuje w 0,036-0,117 % slotów. `FUTEX_WAIT` na muteksie kolejki pojawia się 2-13 razy na rodzinę i stronę, max 84 µs, nigdy w oknie P0.
  - Okno podłączenia z puli ma p50 0,049-0,051 ms, a kolejki utworzonej 2,8 / 9,9 / 6,4 ms. D2s ma kolejkę z puli w 261 / 261 / 257 z 270 podłączeń, C' w 225 / 225 / 221.
  - P0 w D2s trwa krócej (p50 264 / 291 / 293 µs wobec 314 / 308 / 315 µs), bo kolejka ma mniej niż 256 komunikatów (uc03) albo jest chłodniejsza o ~10 s zapisu.

## Odstępstwa od protokołu i od przewidywania

1. **A3 naruszony: worker odpytywany przez ssh co 30 s przez całą kampanię.**
   - Przyczyna: pętla sesji oczekująca na koniec budowy D2s, uruchomiona 18:09, nie skończyła się po budowie. Jej warunek `! pgrep -f build_ab.sh` w poleceniu `ssh worker '...'` dopasowywał linię poleceń zdalnej powłoki tej samej pętli. Wykryto ją i zatrzymano dopiero po kampanii.
   - Skala: dziennik `sshd` workera ma 175 logowań w oknie kampanii 18:51-20:21, czyli ~1 na 30 s, i 92 w oknie 17:41-18:45, które obejmuje suchy przebieg.
   - Skutek dla aneksu A3. Suchy przebieg 1 (18:35-18:38) szedł przy dwóch pętlach odpytujących (co 20 s i co 30 s), a suchy przebieg 2 (18:41-18:44) przy jednej, tej samej co kampania. Uzasadnienie A3 („bez odpytywania” 64-68 µs wobec 80-81 µs) porównuje więc dwie pętle z jedną, a nie odpytywanie z jego brakiem. Wpływu braku odpytywania nie zmierzono.
   - Skutek dla kryteriów. Odpytywanie trwało przez wszystkie 54 przebiegi, więc w porównaniu ABBA dotyczy obu stron jednakowo. Bramki suchego przebiegu 2 sprawdzono w tych samych warunkach. Obrót bezczynny ma w kampanii p99,9 61-79 µs na przebieg (suchy przebieg 2: 64 / 68 µs, R603E: 71 µs). Wartości bezwzględne ogona obrotu bezczynnego, K3t p99 i G2 dotyczą workera z jednym odpytywaniem co 30 s.
2. **K3t uc03: „regresja D2s” według litery to kwantyzacja przesunięcia ~0,2 µs.**
   - Znacznik ftrace ma rozdzielczość 1 µs, więc p50 obrotu bezczynnego to 13 albo 14 µs. W uc03 wszystkie przebiegi C' mają p50 13 µs, a wszystkie przebiegi D2s 14 µs. Różnica 1 µs przy rozrzucie 0 spełnia kryterium regresji, a permutacyjny MW daje p = 4,1e-05. W uc05 i uc06 ta sama różnica 1 µs jest w szumie, bo w obu jedna ze stron ma rozrzut 1 µs.
   - Diagnostyka poza aparaturą (średnia długości obrotu bezczynnego per przebieg, obcięta do p99): D2s - C' = +0,263 / +0,185 / +0,221 µs (uc03 / uc05 / uc06). Zakresy przebiegów stron prawie się nie nakładają: uc03 C' 13,51-13,71, D2s 13,75-14,00 µs. Udział obrotów ≤ 13 µs spada z 0,645 / 0,511 / 0,578 do 0,456 / 0,381 / 0,433.
   - Przesunięcie jest więc rzeczywiste, małe (~1,5 % obrotu bezczynnego, ~0,02 % czasu wątku komunikacyjnego przy obrocie co ~1,1 ms) i jednakowe we wszystkich rodzinach. W obrocie bez zgonu D2s dokłada wywołanie `probeSubscribers` z `steady_clock::now()` i porównaniem z `nextProbe_` (`ipcServer.cpp`, `commandLoop`). Czy to ono daje ~0,2 µs, nie sprawdzono.
   - Przewidywanie („różnica p50 ≤ 1 µs, rozdzielczość znacznika”) się sprawdziło, ale kryterium K3t nie rozróżnia przesunięcia o ułamek rozdzielczości od regresji. Werdykt podano według litery. Czy przyjąć ten koszt, rozstrzyga człowiek (*Skutek*, punkt 2).
3. **K2s uc06: NIEROZSTRZYGNIĘTE z ważności, nie z przedziału T.** Przewidywano niepewność z szerokiego przedziału S(C'), a w wyniku S(C') ma ujemny znak (punkt uc06 w *Odpowiedzi*). Werdykt jest ten sam, ale z innej przyczyny.
4. **Bramki na danych kampanii (opisowo; bramki dotyczą suchego przebiegu, w którym po aneksach były spełnione).**
   - G3, G4, G6 i H są spełnione we wszystkich 54 przebiegach.
   - G1 nie jest spełnione w 4 przebiegach uc06 (3 C', 1 D2s). Najdłuższy odstęp obrotów poza podłączeniami i seriami wynosi tam 5,25-5,69 ms przy progu 5 ms. To własność rodziny, jak w R603E i R603D.
   - G2 C' (wszystkie serie przebiegu spełniają oba warunki) nie jest spełnione w 2 / 5 / 2 przebiegach z 9. Oba warunki spełnia 241 z 243, 185 z 237 i 233 z 235 serii. W uc05 wystarcza do tego ogon obrotu bezczynnego: p99,9 66-76 µs przy pełnej porcji min 73-74 µs.
   - G2f D2s nie jest spełnione w 0 / 4 / 3 przebiegach z 9 (próg 99 % przy ~20 seriach z k ≥ 1 na przebieg oznacza, że wystarczy jedno chybienie). Obrót Pk+1 ≤ p99 obrotu bezczynnego ma 171 z 176 serii z k ≥ 1 w uc05 i 135 z 139 w uc06. Pełne porcje w osobnych obrotach (P2..Pk-1, tylko uc05, k = 3) są dłuższe od p99,9 obrotu bezczynnego w 9 z 10. Osobno, w seriach z k = 0 obrót po P0 > p99 ma 2 z 270 (uc03), 0 z 90 (uc05) i 2 z 121 (uc06).
   - Skutek dla K2s: Pk+1 dłuższe od p99 może być niepoliczoną porcją (k zaniżone o 1). S(D2s) jest wtedy zaniżone najwyżej o slot następny po tej porcji w ~3 % serii z k ≥ 1. Żeby górna granica T w uc05 (-43,9 µs) doszła do 0, S(D2s) musiałoby wzrosnąć o ~44 µs na serię, czyli ~2,7 raza. Błąd tego rzędu nie zmienia werdyktu. W uc03 nie ma serii z k ≥ 1.
5. **Przewidywanie wobec wyniku.**
   - Sprawdziło się:
     - K0 ZDANE, z L ~U(0; 1 s);
     - K2s ZDANE w uc03 (z małym zapasem) i w uc05, NIEROZSTRZYGNIĘTE w uc06;
     - rozkłady n̂ i k;
     - S(D2s) i Δ mediany w przewidywanym rzędzie;
     - K1'' ZDANE, z 9 kolejkami utworzonymi i 261 z puli oraz +1 na każdy martwy muteks (uc06: 13 / 257);
     - 0 przepełnień;
     - K3 bez regresji.
   - Nie sprawdziło się albo inaczej:
     - przyczyna NIEROZSTRZYGNIĘTEGO w uc06 (punkt 3);
     - K3t uc03 według litery (punkt 2);
     - E w uc05 0,47 wobec ~0,2-0,4;
     - seria p50 w uc05 0,35 ms wobec przewidywanych ~1,5 ms, bo według aneksu A1 P1 leży w obrocie P0, więc seria z k = 1 to jeden obrót;
     - sonda na żywym kliencie ~5-6 razy na rodzinę wobec ~10 (punkt K0 w *Odpowiedzi*; liczba przybliżona).

## Granice wniosków

- Jedna platforma: Cortex-A72, wspólne L2 1 MiB, jądro 6.8 `PREEMPT_RT`, jak R603D/R603E.
- **Kosztu sondy przy długo żyjących subskrybentach ta kampania nie mierzy** (D3(a)). Klienci żyli ~36 ms, więc lista obserwowanych była prawie zawsze pusta. Przy N długo żyjących subskrybentach sonda wykonuje co 1 s N odczytów wpisu procesu w wątku komunikacyjnym. Tego nie objęły ani K3, ani K3t.
- Worker był w trakcie kampanii odpytywany co 30 s (*Odstępstwa*, punkt 1). Porównanie stron jest symetryczne, ale wartości bezwzględne ogona obrotu bezczynnego nie opisują workera bez połączeń.
- W uc06 miara S nie ma znaku ani rozdzielczości w dwóch kampaniach z rzędu. Wynik w tej rodzinie nie rozstrzyga K2s w żadną stronę. Iloczyn slotów dotkniętych i Δ mediany jest tylko opisowy.
- Kolejka w D2s była zapisywana do chwili wykrycia, a w C' ~10 s wcześniej niż jej odczyt. Ciepło jej stron w L2 może się różnić. To część skutku D2s, nie błąd miary.
- Liczba podłączeń z puli i warunek (a) zależą od rytmu aparatury (start co ~2,5 s, klient ~36 ms).

## Skutek dla naprawy (decyzja człowieka)

D2s (`75e7574c`) jest na `dev/muro`. Pomiar pokazał, że wcześniejsze rozpoznanie śmierci klienta obniża koszt serii do 35 % (uc03) i 11 % (uc05) kosztu C', usuwa przepełnienia puli i skraca serię 30-100 razy, bez regresji w wątku slotu. Do decyzji:

1. **Przyjąć D2s jako naprawę #603 w części „koszt porzucenia”.** Kryterium główne jest spełnione w obu rodzinach, w których miara ma moc. uc06 jest nierozstrzygnięte z powodu miary, a kierunek opisowy jest zgodny.
2. **K3t: ~0,2 µs na obrót bezczynny wątku komunikacyjnego** (*Odstępstwa*, punkt 2). Kierunki:
   - (a) przyjąć jako koszt sondy (~0,02 % czasu wątku komunikacyjnego);
   - (b) sprawdzić przyczynę osobno, np. mikropomiarem obrotu z wywołaniem `probeSubscribers` i bez niego;
   - (c) zmiana w silniku ograniczająca odczyt zegara (osobna decyzja i osobny pomiar).
3. **Koszt sondy przy długo żyjących subskrybentach (D3).** Przed uznaniem naprawy za kompletną krótka kampania tylko K3 i K3t z N długo żyjącymi subskrybentami (wariant D3(b) z protokołu). Bez niej koszt w typowym wdrożeniu, w którym subskrybent żyje długo, pozostaje niezmierzony.
4. **uc06:** nie mierzyć dalej miarą S. Jeśli potrzebny jest werdykt w tej rodzinie, to miarą odporną na ogon okresowego slotu (np. bez klasy `iter mod H` slotu okresowego), z protokołem przed pomiarem.
5. **Aparatura:** pętle oczekujące na workerze nie mogą używać `pgrep -f` z nazwą w poleceniu ssh. Przed startem kampanii wylistować zadania sesji łączące się z workerem i zatrzymać je.

Rekomendacja: 1, 2(a) i 3 jako następny pomiar #603 przed scaleniem `dev/muro` do `master`; 4 tylko wtedy, gdy werdykt w uc06 będzie potrzebny do publikacji.

## Odtworzenie od zera

Wszystko na workerze `pi400` z katalogu `~/R376/apparatus_R603F` (kopia tego katalogu), poza analizą:

1. Korpus uc03, uc05, uc06 jak w R600 (`results_20261104_R600/wynik.md`, *Odtworzenie od zera*, punkt 3) do `/dev/shm/r376/data/<rodzina>`; `streams.tsv` z `~/R376/apparatus_R600` (tylko na workerze). Sprawdzenie: skróty SHA-256 drzew z README R603C (*Suchy przebieg*, punkt 2).
2. Binarka C': `~/R376/bin/R603D_Cp` z R603D (`results_20261105_R603D/wynik.md`, *Odtworzenie od zera*, punkt 2), suma sprawdzana przez `build_ab.sh` i `campaign.sh`. Budowa D2s: `setsid nohup ./build_ab.sh > ~/R376/build_R603F.log 2>&1 < /dev/null &` (przyrostowo, ~20 min; źródła z `origin`, `75e7574c` musi być wypchnięty).
3. Kampania: `setsid nohup ./campaign.sh > ~/R376/campaign_R603F.log 2>&1 < /dev/null &` (~1,5 h). Przerwana rodzina = powtórzyć całą (ABBA). Do końca kampanii nie łączyć się z workerem (aneks A3, *Odstępstwa*, punkt 1).
4. Analiza na hoście: `rsync -a <worker>:R376/raw_R603F/ <katalog>/raw/` albo trzy części archiwum rozpakowane do jednego katalogu (`tar xzf <część> -C <katalog>`, sprawdzenie każdej z jej indeksem jak w README `rdb-experiment-embargo`), potem Python ≥ 3.10 z NumPy (np. `retractordb/.venv-python/bin/python3`) `-I analyze.py --raw <katalog>/raw --seed 6034` z tego katalogu (importuje `../results_20261106_R603E/analyze.py`, a ten `../results_20261105_R603D/analyze.py` i `../results_20261105_R603C/analyze.py`). Część *Wydruk analizy* to ten wydruk bez pierwszego wiersza i z nagłówkami obniżonymi o jeden poziom: `analyze.py ... --out w.txt && sed 's/^#/##/' w.txt | tail -n +2` musi dać ją bajt w bajt. Sprawdzone 2026-11-06 na archiwum rozpakowanym od nowa (3 indeksy zgodne, 324 pliki, drzewo identyczne z danymi z workera, wydruk identyczny); czas analizy ~6 min.
5. Diagnostyka *Odstępstw* (punkty 2 i 4): `analyze.py --gates --raw <katalog>/raw` (bramki per przebieg na danych kampanii) i średnia obcięta obrotu bezczynnego per przebieg z pola `idle_len` wyniku `analyze()` z tego katalogu. Skrypt diagnostyczny nie należy do aparatury: wypisuje tylko liczby wyprowadzone, podane wyżej.

## Wydruk analizy

Źródło: `raw`, ziarna: placebo 6034, bootstrap 6035, H0 6036, pseudo-zdarzenia 6037.

Parametry H0 K2s uc03 (z D2s): P0 264.0 µs, porcja 75.0 µs, obrót 1070.0 µs, faza 0..4568 µs, rozrzut 60 µs, P1 w obrocie P0 75.0 µs, k z 270 serii D2s.

### uc03

Takt slotu: 5.000 ms, H = 8, k C' = 7 (z pojemności mmap: [7], pojemność [2000]).

| wielkość | C' | D2s |
|---|---|---|
| przebiegi / podłączenia | 9 / 270 | 9 / 270 |
| K0: wykrycia przez sondę / samotne wykrycia | 0 / 0 | 270 / 0 |
| K0: porzucenia poza wyłączeniami: z wykryciem / z pełnej kolejki / poza granicami L | 0 / 270 / 0 | 270 / 0 / 0 |
| K0: opóźnienie wykrycia L po końcu klienta [ms] min / p50 / p99 / max | - | 1.5 / 554.0 / 983.2 / 994.8 |
| sonda: openat z sukcesem w wątku komunikacyjnym w oknach podłączeń na podłączenie / poza oknami | 0.500 / 0 | 1.122 / 0 |
| serie: niezakłócone / przepełnienia / zakłócone | 243 / 27 / 0 | 270 / 0 / 0 |
| O5: powody zakłóceń | - | - |
| O3: n^ komunikatów w chwili wykrycia p50 / średnio / max | - | 111 / 105 / 199 |
| O3: k porcji po P0: rozkład (k = 0, 1, ...) / średnio / serie graniczne | - | 1.000; 0.00; 0 |
| O3: P0 [µs] p50 / p99 / max | 314.0 / 409.0 / 412.0 | 264.0 / 358.0 / 387.0 |
| O3: faza P0 po końcu slotu [µs] p5 / p50 / p95 | 156.4 / 646.3 / 1102.8 | -782.5 / 1981.7 / 4567.7 |
| O3: P1 w obrocie P0, od wyjścia z renameat [µs] p50 / p99 / max (aneks A1) | - | - / - / - |
| O3: pełna porcja w osobnym obrocie (C' P1..Pk-1, D2s P2..Pk-1) [µs] p50 / p99 / max | 76.0 / 124.0 / 182.0 | - / - / - |
| O3: ostatnia porcja Pk [µs] p50 / p99 / max | 64.0 / 128.0 / 131.0 | - / - / - |
| O3: obrót Pk+1 [µs] p50 / p99 / max | 14.0 / 22.0 / 62.0 | 14.0 / 31.0 / 63.0 |
| O3: obrót bezczynny [µs] p50 / p99 / max | 13.0 / 27.0 / 1580.0 | 14.0 / 30.0 / 1114.0 |
| O3: odstęp obrotów w serii [µs] p50 / p99 / max | 1154.0 / 1215.0 / 2538.0 | - / - / - |
| O3: seria P0..Pk [ms] p50 / max | 8.431 / 9.119 | 0.264 / 0.387 |
| opisowo E: sloty narażone na serię (95 % bootstrap) | 0.337 (0.276..0.399) | 0.163 (0.122..0.207) |
| K2s: serie z placebo / sloty dotknięte na serię | 243 / 2.2 | 270 / 1.2 |
| K2s: S = suma odchyleń slotów dotkniętych na serię ponad placebo [µs] (95 %) | +65.9 (+57.4..+75.4) | +23.0 (+17.0..+29.9) |
| K2s: Δ mediany slotów dotkniętych [µs] (95 %) | +26.89 (+25.19..+30.07) | +17.10 (+16.74..+17.79) |
| opisowo: Δ mediany slotów następnych po oknach [µs] (95 %) | +26.89 (+25.24..+30.08) | +17.03 (+16.73..+17.68) |
| H0 K2s (syntetyczne serie D2s na tle C'): serie / S [µs] / Δ mediany [µs] | - | 1202 / +1.4 (-0.9..+3.8) / +0.04 (-0.07..+0.16) |
| opisowo K2a R603D Δ_c [µs]; n slotów; serie z narażeniem | +44.11 µs (+35.08..+77.28); n = 82, serie 80/243 | +27.68 µs (+14.54..+36.77); n = 44, serie 44/270 |
| opisowo O4 R603D: sloty narażone / suma odchyleń na serię ponad placebo [µs] (średnie) | 0.01 / 20.6 | 0.00 / 5.0 |
| kontrola e2e [µs] p50 / p99 / max | 170.3 / 2833.2 / 3735.5 | 149.7 / 2823.3 / 3532.8 |
| kontrola compute [µs] p50 / p99 / max | 127.2 / 2775.6 / 3591.5 | 125.2 / 2796.6 / 3474.1 |
| kontrola wake [µs] p50 / p99 / max | 23.8 / 39.9 / 120.2 | 23.4 / 39.0 / 126.4 |
| O1: futex wątku RT: sloty z futex / sloty w serii | 100 / 138601 (0.072 %) | 94 / 141658 (0.066 %) |
| O1: FUTEX_WAIT na muteksie kolejki: liczba / max [µs] / w oknie P0 / slot > takt | 2 / 17.0 / 0 / 0 | 2 / 69.0 / 0 / 0 |
| O2: podłączenie, kolejka utworzona: liczba / okno p50 [ms] | 45 / 2.804 | 9 / 2.838 |
| O2: podłączenie, kolejka z puli: liczba / okno p50 [ms] | 225 / 0.050 | 261 / 0.049 |
| O6: kolejka utworzona, gdy pula miała tylko wpisy niegotowe | 0 | 0 |

- **K0** (wykrycie przez sondę, -5 ms ≤ L ≤ 1.010 s): D2s porzuceń z wykryciem 270, z pełnej kolejki 0; C' wykryć 0. Werdykt: **ZDANE**.
- **K1''** D2s: do puli 270 z 270 (wyłączenia 0: martwy muteks 0, z tego przy znalezionym procesie 0 i po wykryciu przez sondę 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 9 / 261, przepełnienia 0 (kontrola dodatnia: przepełnienie w ogonie każdego przebiegu C' - tak, oddanie z puli w każdym przebiegu - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 0. Werdykt D2s (warunek (b)): **ZDANE**. Warunek (a) opisowo: serii niegotowych przed startem następnego klienta 0, oczekiwanych 0.0; O6 0.
- K1'' C' (opisowo, poprawiona klasyfikacja): do puli 270 z 270 (wyłączenia 0: martwy muteks 0, z tego przy znalezionym procesie 0 i po wykryciu przez sondę 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 45 / 225, przepełnienia 27 (kontrola dodatnia: przepełnienie w ogonie każdego przebiegu C' - tak, oddanie z puli w każdym przebiegu - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 0. Werdykt C': ZDANE. Warunek (a): 0, oczekiwanych 0.9; O6 0.
- **K2s** (T = S(D2s) - 0.5 · S(C')): T -10.0 (-17.6..-1.9) µs; S(D2s) +23.0 (+17.0..+29.9), S(C') +65.9 (+57.4..+75.4) µs; S(D2s) - S(C') -42.9 (-53.8..-32.4) µs; u_S 0.35 (0.25..0.47). Ważność: kontrola dodatnia tak, H0 półszerokość 2.3 µs wobec 16.5 µs. Werdykt: **ZDANE**.
- **K3**, compute_ns p50 per przebieg: mediana D2s - C' = -1.91 µs, rozrzut wewnątrz strony do 2.30 µs, permutacyjny MW p = 4.11e-05 - w szumie.
- **K3**, wake_lag_ns p99 per przebieg: mediana D2s - C' = -0.83 µs, rozrzut wewnątrz strony do 25.96 µs, permutacyjny MW p = 0.605 - w szumie.
- **K3**, e2e_ns p99 per przebieg: mediana D2s - C' = -4.65 µs, rozrzut wewnątrz strony do 173.51 µs, permutacyjny MW p = 0.546 - w szumie.
- **K3t**, obrót bezczynny p50 per przebieg: mediana D2s - C' = 1.00 µs, rozrzut wewnątrz strony do 0.00 µs, permutacyjny MW p = 4.11e-05 - REGRESJA D2s - osobne znalezisko.
- **K3t**, obrót bezczynny p99 per przebieg: mediana D2s - C' = 3.00 µs, rozrzut wewnątrz strony do 7.00 µs, permutacyjny MW p = 0.00527 - w szumie.

Parametry H0 K2s uc05 (z D2s): P0 291.0 µs, porcja 76.0 µs, obrót 1127.0 µs, faza 0..1531 µs, rozrzut 60 µs, P1 w obrocie P0 65.0 µs, k z 270 serii D2s.

### uc05

Takt slotu: 1.000 ms, H = 40, k C' = 31 (z pojemności mmap: [31], pojemność [8000]).

| wielkość | C' | D2s |
|---|---|---|
| przebiegi / podłączenia | 9 / 270 | 9 / 270 |
| K0: wykrycia przez sondę / samotne wykrycia | 0 / 0 | 270 / 0 |
| K0: porzucenia poza wyłączeniami: z wykryciem / z pełnej kolejki / poza granicami L | 0 / 270 / 0 | 270 / 0 / 0 |
| K0: opóźnienie wykrycia L po końcu klienta [ms] min / p50 / p99 / max | - | 1.9 / 501.8 / 996.3 / 997.7 |
| sonda: openat z sukcesem w wątku komunikacyjnym w oknach podłączeń na podłączenie / poza oknami | 0.500 / 0 | 1.122 / 0 |
| serie: niezakłócone / przepełnienia / zakłócone | 237 / 27 / 6 | 270 / 0 / 0 |
| O5: powody zakłóceń | wywolanie w P1..Pk: fallocate, fstatfs, ftruncate, mmap, openat, unlinkat; wywolanie w P1..Pk: renameat | - |
| O3: n^ komunikatów w chwili wykrycia p50 / średnio / max | - | 402 / 403 / 800 |
| O3: k porcji po P0: rozkład (k = 0, 1, ...) / średnio / serie graniczne | - | 0.337 / 0.300 / 0.319 / 0.044; 1.07; 4 |
| O3: P0 [µs] p50 / p99 / max | 308.0 / 409.0 / 425.0 | 291.0 / 384.0 / 410.0 |
| O3: faza P0 po końcu slotu [µs] p5 / p50 / p95 | -92.1 / 357.1 / 829.5 | -187.2 / 389.8 / 1531.4 |
| O3: P1 w obrocie P0, od wyjścia z renameat [µs] p50 / p99 / max (aneks A1) | - | 65.0 / 142.0 / 145.0 |
| O3: pełna porcja w osobnym obrocie (C' P1..Pk-1, D2s P2..Pk-1) [µs] p50 / p99 / max | 77.0 / 135.0 / 706.0 | 76.0 / 116.0 / 116.0 |
| O3: ostatnia porcja Pk [µs] p50 / p99 / max | 30.0 / 86.0 / 99.0 | 44.0 / 107.0 / 107.0 |
| O3: obrót Pk+1 [µs] p50 / p99 / max | 14.0 / 38.0 / 318.0 | 14.0 / 68.0 / 150.0 |
| O3: obrót bezczynny [µs] p50 / p99 / max | 13.0 / 31.0 / 1410.0 | 14.0 / 34.0 / 1303.0 |
| O3: odstęp obrotów w serii [µs] p50 / p99 / max | 1157.0 / 1231.0 / 1969.0 | 1127.0 / 1193.0 / 1213.0 |
| O3: seria P0..Pk [ms] p50 / max | 36.240 / 39.436 | 0.348 / 2.833 |
| opisowo E: sloty narażone na serię (95 % bootstrap) | 6.397 (6.211..6.578) | 0.467 (0.400..0.533) |
| K2s: serie z placebo / sloty dotknięte na serię | 237 / 31.7 | 270 / 1.8 |
| K2s: S = suma odchyleń slotów dotkniętych na serię ponad placebo [µs] (95 %) | +226.8 (+142.5..+313.7) | +25.8 (+17.6..+34.7) |
| K2s: Δ mediany slotów dotkniętych [µs] (95 %) | +2.96 (+2.76..+3.17) | +7.60 (+6.15..+8.63) |
| opisowo: Δ mediany slotów następnych po oknach [µs] (95 %) | +3.02 (+2.82..+3.24) | +7.48 (+4.83..+8.86) |
| H0 K2s (syntetyczne serie D2s na tle C'): serie / S [µs] / Δ mediany [µs] | - | 1183 / +1.5 (-1.8..+4.9) / -0.02 (-0.07..+0.04) |
| opisowo K2a R603D Δ_c [µs]; n slotów; serie z narażeniem | +6.62 µs (+5.78..+7.59); n = 1516, serie 237/237 | +9.17 µs (+7.55..+11.08); n = 126, serie 113/270 |
| opisowo O4 R603D: sloty narażone / suma odchyleń na serię ponad placebo [µs] (średnie) | -0.05 / 121.1 | 0.01 / 7.0 |
| kontrola e2e [µs] p50 / p99 / max | 111.4 / 1032.5 / 1915.7 | 86.8 / 984.3 / 1880.9 |
| kontrola compute [µs] p50 / p99 / max | 63.6 / 972.5 / 1737.0 | 62.1 / 959.0 / 1792.5 |
| kontrola wake [µs] p50 / p99 / max | 23.8 / 103.1 / 1002.3 | 23.4 / 81.5 / 987.1 |
| O1: futex wątku RT: sloty z futex / sloty w serii | 274 / 697169 (0.039 %) | 252 / 698193 (0.036 %) |
| O1: FUTEX_WAIT na muteksie kolejki: liczba / max [µs] / w oknie P0 / slot > takt | 11 / 84.0 / 0 / 0 | 13 / 59.0 / 0 / 0 |
| O2: podłączenie, kolejka utworzona: liczba / okno p50 [ms] | 45 / 9.945 | 9 / 9.924 |
| O2: podłączenie, kolejka z puli: liczba / okno p50 [ms] | 225 / 0.050 | 261 / 0.049 |
| O6: kolejka utworzona, gdy pula miała tylko wpisy niegotowe | 1 | 0 |

- **K0** (wykrycie przez sondę, -5 ms ≤ L ≤ 1.010 s): D2s porzuceń z wykryciem 270, z pełnej kolejki 0; C' wykryć 0. Werdykt: **ZDANE**.
- **K1''** D2s: do puli 270 z 270 (wyłączenia 0: martwy muteks 0, z tego przy znalezionym procesie 0 i po wykryciu przez sondę 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 9 / 261, przepełnienia 0 (kontrola dodatnia: przepełnienie w ogonie każdego przebiegu C' - tak, oddanie z puli w każdym przebiegu - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 0. Werdykt D2s (warunek (b)): **ZDANE**. Warunek (a) opisowo: serii niegotowych przed startem następnego klienta 0, oczekiwanych 0.0; O6 0.
- K1'' C' (opisowo, poprawiona klasyfikacja): do puli 270 z 270 (wyłączenia 0: martwy muteks 0, z tego przy znalezionym procesie 0 i po wykryciu przez sondę 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 45 / 225, przepełnienia 27 (kontrola dodatnia: przepełnienie w ogonie każdego przebiegu C' - tak, oddanie z puli w każdym przebiegu - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 5. Werdykt C': ZDANE. Warunek (a): 5, oczekiwanych 3.9; O6 1.
- **K2s** (T = S(D2s) - 0.5 · S(C')): T -87.6 (-134.6..-43.9) µs; S(D2s) +25.8 (+17.6..+34.7), S(C') +226.8 (+142.5..+313.7) µs; S(D2s) - S(C') -201.0 (-290.7..-114.8) µs; u_S 0.11 (0.07..0.20). Ważność: kontrola dodatnia tak, H0 półszerokość 3.4 µs wobec 56.7 µs. Werdykt: **ZDANE**.
- **K3**, compute_ns p50 per przebieg: mediana D2s - C' = -1.65 µs, rozrzut wewnątrz strony do 0.59 µs, permutacyjny MW p = 4.11e-05 - D2s lepsze poza szumem.
- **K3**, wake_lag_ns p99 per przebieg: mediana D2s - C' = -22.52 µs, rozrzut wewnątrz strony do 42.54 µs, permutacyjny MW p = 0.000165 - w szumie.
- **K3**, e2e_ns p99 per przebieg: mediana D2s - C' = -46.68 µs, rozrzut wewnątrz strony do 30.09 µs, permutacyjny MW p = 4.11e-05 - D2s lepsze poza szumem.
- **K3t**, obrót bezczynny p50 per przebieg: mediana D2s - C' = 1.00 µs, rozrzut wewnątrz strony do 1.00 µs, permutacyjny MW p = 0.00226 - w szumie.
- **K3t**, obrót bezczynny p99 per przebieg: mediana D2s - C' = 2.00 µs, rozrzut wewnątrz strony do 8.00 µs, permutacyjny MW p = 0.126 - w szumie.

Parametry H0 K2s uc06 (z D2s): P0 293.0 µs, porcja 75.0 µs, obrót 1070.0 µs, faza 0..1587 µs, rozrzut 60 µs, P1 w obrocie P0 34.0 µs, k z 266 serii D2s.

### uc06

Takt slotu: 2.000 ms, H = 5, k C' = 19 (z pojemności mmap: [19], pojemność [5000]).

| wielkość | C' | D2s |
|---|---|---|
| przebiegi / podłączenia | 9 / 270 | 9 / 270 |
| K0: wykrycia przez sondę / samotne wykrycia | 0 / 0 | 266 / 1 |
| K0: porzucenia poza wyłączeniami: z wykryciem / z pełnej kolejki / poza granicami L | 0 / 264 / 0 | 266 / 0 / 0 |
| K0: opóźnienie wykrycia L po końcu klienta [ms] min / p50 / p99 / max | - | 10.9 / 532.4 / 991.9 / 998.8 |
| sonda: openat z sukcesem w wątku komunikacyjnym w oknach podłączeń na podłączenie / poza oknami | 0.548 / 0 | 1.163 / 0 |
| serie: niezakłócone / przepełnienia / zakłócone | 235 / 25 / 4 | 266 / 0 / 0 |
| O5: powody zakłóceń | wywolanie w P1..Pk: renameat | - |
| O3: n^ komunikatów w chwili wykrycia p50 / średnio / max | - | 267 / 258 / 500 |
| O3: k porcji po P0: rozkład (k = 0, 1, ...) / średnio / serie graniczne | - | 0.474 / 0.526; 0.53; 6 |
| O3: P0 [µs] p50 / p99 / max | 315.0 / 404.0 / 500.0 | 293.0 / 386.0 / 467.0 |
| O3: faza P0 po końcu slotu [µs] p5 / p50 / p95 | -6565.0 / 533.1 / 1099.9 | -202.9 / 696.3 / 1587.4 |
| O3: P1 w obrocie P0, od wyjścia z renameat [µs] p50 / p99 / max (aneks A1) | - | 34.0 / 99.0 / 102.0 |
| O3: pełna porcja w osobnym obrocie (C' P1..Pk-1, D2s P2..Pk-1) [µs] p50 / p99 / max | 77.0 / 131.0 / 1445.0 | - / - / - |
| O3: ostatnia porcja Pk [µs] p50 / p99 / max | 48.0 / 102.0 / 104.0 | - / - / - |
| O3: obrót Pk+1 [µs] p50 / p99 / max | 14.0 / 21.0 / 325.0 | 14.0 / 52.0 / 69.0 |
| O3: obrót bezczynny [µs] p50 / p99 / max | 13.0 / 28.0 / 783.0 | 14.0 / 29.0 / 2091.0 |
| O3: odstęp obrotów w serii [µs] p50 / p99 / max | 1157.0 / 1221.0 / 2531.0 | - / - / - |
| O3: seria P0..Pk [ms] p50 / max | 22.353 / 24.384 | 0.315 / 0.478 |
| opisowo E: sloty narażone na serię (95 % bootstrap) | 3.570 (3.332..3.821) | 0.342 (0.286..0.398) |
| K2s: serie z placebo / sloty dotknięte na serię | 235 / 12.6 | 266 / 1.3 |
| K2s: S = suma odchyleń slotów dotkniętych na serię ponad placebo [µs] (95 %) | -2103.2 (-3348.3..-742.1) | -539.2 (-704.9..-374.9) |
| K2s: Δ mediany slotów dotkniętych [µs] (95 %) | +10.72 (+10.04..+11.67) | +16.04 (+15.35..+17.00) |
| opisowo: Δ mediany slotów następnych po oknach [µs] (95 %) | +11.11 (+10.46..+12.02) | +16.46 (+15.72..+17.85) |
| H0 K2s (syntetyczne serie D2s na tle C'): serie / S [µs] / Δ mediany [µs] | - | 1173 / -89.6 (-301.2..+152.7) / -0.72 (-0.85..-0.57) |
| opisowo K2a R603D Δ_c [µs]; n slotów; serie z narażeniem | +10.63 µs (+9.29..+11.74); n = 839, serie 233/235 | +14.96 µs (+12.06..+16.37); n = 91, serie 91/266 |
| opisowo O4 R603D: sloty narażone / suma odchyleń na serię ponad placebo [µs] (średnie) | 0.96 / -150.1 | 0.13 / -38.7 |
| kontrola e2e [µs] p50 / p99 / max | 286.7 / 44842.8 / 48244.6 | 250.9 / 45399.8 / 49085.9 |
| kontrola compute [µs] p50 / p99 / max | 225.2 / 476.0 / 48086.8 | 222.9 / 488.5 / 49023.2 |
| kontrola wake [µs] p50 / p99 / max | 23.9 / 42886.1 / 46334.6 | 23.5 / 43440.7 / 47151.4 |
| O1: futex wątku RT: sloty z futex / sloty w serii | 387 / 350937 (0.110 %) | 410 / 350909 (0.117 %) |
| O1: FUTEX_WAIT na muteksie kolejki: liczba / max [µs] / w oknie P0 / slot > takt | 13 / 79.0 / 0 / 2 | 8 / 55.0 / 0 / 2 |
| O2: podłączenie, kolejka utworzona: liczba / okno p50 [ms] | 49 / 6.359 | 13 / 6.438 |
| O2: podłączenie, kolejka z puli: liczba / okno p50 [ms] | 221 / 0.051 | 257 / 0.050 |
| O6: kolejka utworzona, gdy pula miała tylko wpisy niegotowe | 0 | 0 |

- **K0** (wykrycie przez sondę, -5 ms ≤ L ≤ 1.010 s): D2s porzuceń z wykryciem 266, z pełnej kolejki 0; C' wykryć 0. Werdykt: **ZDANE**.
- **K1''** D2s: do puli 266 z 270 (wyłączenia 4: martwy muteks 4, z tego przy znalezionym procesie 1 i po wykryciu przez sondę 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 13 / 257, przepełnienia 0 (kontrola dodatnia: przepełnienie w ogonie każdego przebiegu C' - tak, oddanie z puli w każdym przebiegu - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 0. Werdykt D2s (warunek (b)): **ZDANE**. Warunek (a) opisowo: serii niegotowych przed startem następnego klienta 0, oczekiwanych 0.0; O6 0.
- K1'' C' (opisowo, poprawiona klasyfikacja): do puli 264 z 270 (wyłączenia 6: martwy muteks 6, z tego przy znalezionym procesie 0 i po wykryciu przez sondę 0, niezebrany 0), pary w fazie pracy niewyjaśnione 0, zwolnienia bez puli niewyjaśnione 0, kolejki utworzone / z puli 49 / 221, przepełnienia 25 (kontrola dodatnia: przepełnienie w ogonie każdego przebiegu C' - tak, oddanie z puli w każdym przebiegu - tak), spójność ogona tak, model puli: naruszeń 0, serii niegotowych przed następnym podłączeniem 1. Werdykt C': ZDANE. Warunek (a): 1, oczekiwanych 2.3; O6 0.
- **K2s** (T = S(D2s) - 0.5 · S(C')): T +512.4 (-175.3..+1161.8) µs; S(D2s) -539.2 (-704.9..-374.9), S(C') -2103.2 (-3348.3..-742.1) µs; S(D2s) - S(C') +1564.0 (+232.2..+2805.2) µs; u_S 0.26 (0.14..0.69). Ważność: kontrola dodatnia NIE, H0 półszerokość 227.0 µs wobec -525.8 µs. Werdykt: **NIEROZSTRZYGNIĘTE (miara: kontrola dodatnia: dolna granica S(C') -3348.3 µs ≤ 0; H0: półszerokość 227.0 µs > 0.25 · S(C') = -525.8 µs)**.
- **K3**, compute_ns p50 per przebieg: mediana D2s - C' = -2.15 µs, rozrzut wewnątrz strony do 8.81 µs, permutacyjny MW p = 0.00074 - w szumie.
- **K3**, wake_lag_ns p99 per przebieg: mediana D2s - C' = 600.96 µs, rozrzut wewnątrz strony do 766.04 µs, permutacyjny MW p = 4.11e-05 - w szumie.
- **K3**, e2e_ns p99 per przebieg: mediana D2s - C' = 596.27 µs, rozrzut wewnątrz strony do 764.40 µs, permutacyjny MW p = 4.11e-05 - w szumie.
- **K3t**, obrót bezczynny p50 per przebieg: mediana D2s - C' = 1.00 µs, rozrzut wewnątrz strony do 1.00 µs, permutacyjny MW p = 0.000411 - w szumie.
- **K3t**, obrót bezczynny p99 per przebieg: mediana D2s - C' = 1.00 µs, rozrzut wewnątrz strony do 3.00 µs, permutacyjny MW p = 0.0312 - w szumie.

### Werdykty

| rodzina | K0 | K1'' D2s (b) | K2s | K1'' C' (b, opisowo) |
|---|---|---|---|---|
| uc03 | ZDANE | ZDANE | ZDANE | ZDANE |
| uc05 | ZDANE | ZDANE | ZDANE | ZDANE |
| uc06 | ZDANE | ZDANE | NIEROZSTRZYGNIĘTE (miara: kontrola dodatnia: dolna granica S(C') -3348.3 µs ≤ 0; H0: półszerokość 227.0 µs > 0.25 · S(C') = -525.8 µs) | ZDANE |
