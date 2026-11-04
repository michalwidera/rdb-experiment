# R600 - wynik kampanii

Kampania 2026-11-04 21:56 - 2026-11-05 00:20, pi400, uc03, uc05, uc06, uc07, uc08, 9 par A/B w kolejności ABBA, 30 podłączeń na przebieg: razem 90 przebiegów i 2700 podłączeń. Każdy przebieg był ważny: wątek slotu `SCHED_FIFO` na rdzeniu 3, `VmLck` > 0, governor `performance`, uruchomiona binarka równa zbudowanej (`analyze.py` przerywa przy każdym z tych warunków). Każdy klient dostał wiersz. Log kampanii nie zawiera żadnego błędu i kończy się `CAMPAIGN_COMPLETE`; jego kopia to `campaign.log`. Surowe dane leżą poza git: `results_20261104_R600_raw.tar.gz` (42 010 932 B), SHA-256 `78d7c1060117e0c596f5c453723c7da2044a3a7d9638cf0c4f4fb77c0a8d13e5`. Indeks 540 plików (90 przebiegów × 6 plików) jest w `results_20261104_R600_raw.index.tsv`. Analiza według kryteriów: `analyze.py --raw <raw> --seed 600`; jej pełny wydruk jest niżej, w części *Wydruk analizy*. Eksploracja po pomiarze: `explore_k2.py --raw <raw>`; wydruk w części *Wydruk eksploracji*.

## Odpowiedź

**#600 przeniosło zwolnienie z wątku slotu w każdej mierzonej rodzinie, a koszt, który slot płacił za zwolnienie, spadł o ok. 99 %. Ślad tego kosztu zostaje jednak mierzalny w uc05 i uc06, więc K2 według kryterium ustalonego przed pomiarem jest tam NIEZDANE.** Szczegóły pokazuje tabela i punkty pod nią.

| rodzina | K1: zwolnienia poza wątkiem RT, B (kontrola A w wątku RT) | K2: n trafień B; różnica median zdarzenie - pseudo A → B; p (B) | K3 | werdykt K1 / K2 / K3 |
|---|---|---|---|---|
| uc03 | 270 z 270 (A 270 z 270) | 29; 1,746 → 0,061 ms; 1,5e-06 | w szumie | **ZDANE** / NIEROZSTRZYGNIĘTE (n < 100) / bez regresji |
| uc05 | 270 z 270 (A 270 z 270) | 270; 5,655 → 0,030 ms; 2,2e-04 | w szumie | **ZDANE** / **NIEZDANE** / bez regresji |
| uc06 | 270 z 270 (A 270 z 270) | 270; 3,870 → 0,043 ms; 5,2e-16 | w szumie | **ZDANE** / **NIEZDANE** / bez regresji |
| uc07 | 270 z 270 (A 270 z 270) | 0; 0,618 ms → brak trafień | w szumie | **ZDANE** / NIEROZSTRZYGNIĘTE (n = 0) / bez regresji |
| uc08 | 270 z 270 (A 270 z 270) | 0; 0,343 ms → brak trafień | w szumie | **ZDANE** / NIEROZSTRZYGNIĘTE (n = 0) / bez regresji |

- **K1 - cel #600 osiągnięty.** W B każde z 1350 zwolnień wykonał wątek komunikacyjny, czyli ten, który zbudował kolejkę. W A każde z 1350 wykonał wątek slotu, więc kontrola dodatnia się powtórzyła i aparatura widzi różnicę, o którą pyta #600. W śladzie ftrace każde `munmap` B biegło na rdzeniach 0-2 (573 / 226 / 551), a każde `munmap` A na rdzeniu 3.
- **K2 - wielkość efektu a werdykt.** Kryterium pyta tylko o istnienie różnicy (MW, p ≥ 0,01), a nie o jej wielkość. Dlatego wynik B w uc05 i uc06 jest NIEZDANE, choć różnica median spadła z milisekund do dziesiątek mikrosekund. Kontrola dodatnia mocy testu (A: p = 4,7e-170 w uc05, 2,7e-55 w uc06) była spełniona, więc werdykt jest ważny.
- **K2 - znaczenie dla czasu rzeczywistego (uc05).** Okno zwolnienia B zawiera slot dłuższy od taktu (1,000 ms) w 25,2 % przypadków, a pseudo-okno tej samej długości w 10,2 % (A: 100 % wobec 11,3 %). W uc06 ta miara nic nie rozstrzyga: sloty kontrolne same przekraczają takt w 23,3 % pseudo-okien (rodzina ma okresowy slot ~45 ms), a okna zwolnienia B tylko w 4,8 %.
- **K2 w uc03, uc07, uc08** jest nierozstrzygnięte, tak jak zakładał protokół (decyzja człowieka 2026-11-04). Skutek #600 opisują tam K1 i odsetek zwolnień trafionych w slot: A 100 %, B 10,7 % (uc03), 0 % (uc07, uc08).
- **K3 - brak regresji B w żadnej rodzinie i mierze.** W uc05 i uc06 B ma niższe `wake_lag_ns` p99 i `e2e_ns` p99 niż A (uc06: mediana B-A -0,60 ms, permutacyjny MW p = 4,1e-05), ale różnica mieści się w rozrzucie wewnątrz strony, więc według reguły K3 jest to szum. Poprawy się tu nie ogłasza.

## Odchylenia od przewidywania

1. **Takt uc05.** W tabeli przewidywania README podaje dla uc05 „takt slotu 1/800 s”. Jest to takt strumienia subskrybowanego, a nie odstęp slotów: mediana odstępu kolejnych `deadline_ns` w uc05 wynosi 1,000 ms. Pozostałe rodziny: uc03 5,000 ms, uc06 2,000 ms, czyli zgodnie z tabelą. Przewidywanie trafień to zmienia tylko liczbowo: zwolnienie ~6 ms jest dłuższe od obu wartości.
2. **uc03: 29 trafień zamiast ~0.** Wszystkie 29 to sloty obudzone w trakcie zwolnienia (*Eksploracja*), a nie slot, który kolejkę porzucił. Przewidywanie zakładało, że wątek komunikacyjny zaczyna zwalniać ~1 ms po porzuceniu i kończy przed następnym slotem (5 ms później, zwolnienie ~1,8 ms). W 10,7 % przypadków tak nie było. Przyczyna nie jest ustalona: ślad nie ma znacznika chwili porzucenia, więc opóźnienia startu zwolnienia nie da się z niego zmierzyć. Pytanie otwarte, zob. *Pytania otwarte*.
3. **Zwolnienie w wątku komunikacyjnym trwa dłużej** niż w wątku slotu, jak pokazał już suchy przebieg: p50 uc03 1,818 wobec 1,715 ms, uc05 6,383 wobec 6,138 ms, uc06 4,109 wobec 3,897 ms. Wątek komunikacyjny jest `SCHED_OTHER` na rdzeniach współdzielonych z systemem. Wielkość opisowa, poza kryteriami.

## Eksploracja po pomiarze (poza kryteriami, werdyktu nie zmienia)

Po co: K2 wyszło NIEZDANE, a człowiek wymaga, żeby błędy silnika identyfikować od razu. Zanim zgłosi się to jako defekt, trzeba wiedzieć, skąd bierze się resztka. `explore_k2.py` dzieli sloty, które zachodzą na okno zwolnienia, na dwie grupy: (a) slot, który już trwał, gdy zwolnienie ruszyło, i (b) sloty obudzone w trakcie zwolnienia. Tylko grupa (b) to sloty, które #600 miało chronić. Grupa (a) to zwykle slot, który sam kolejkę porzucił i ma swój własny koszt porzucenia.

1. **Resztkę niosą sloty obudzone w trakcie zwolnienia (b), a nie slot porzucający (a).** W B: uc05 n = 270, MW wobec pseudo p = 4,7e-05; uc06 n = 270, p = 1,1e-15; uc03 n = 29, p = 8,0e-07. Grupa (a) w B jest mała (uc05 27, uc06 17, uc03 0), bo wątek komunikacyjny zwykle startuje już po końcu slotu.
2. **Nie dzielenie rdzenia.** Zwolnienia B biegną na rdzeniach 0-2 (K1 wyżej), a wątek slotu na izolowanym rdzeniu 3. Jądro workera to `6.8.0-2049-raspi-realtime` (`PREEMPT_RT`).
3. **Nie blokada silnika.** Na `master` `10f491b8` (`src/retractor/lib/ipcServer.cpp`, `releaseAbandonedQueues()`) wątek komunikacyjny trzyma `clientMapsMutex_`, który bierze też `broadcast()` w slocie, tylko na czas `swap` i `reserve` listy. `munmap` i `unlinkat` wykonuje poza muteksem. Także wzrost `compute_ns` (dziesiątki µs) jest o rząd wielkości mniejszy od czasu `munmap` (ms), więc slot nie czeka na samo zwolnienie.
4. **Gdzie widać resztkę.** Wśród slotów obudzonych w trakcie zwolnienia B, wobec slotów kontrolnych:
   - `wake_lag_ns` p50 rośnie o +2,7 µs (uc05), +3,4 µs (uc06) i +3,4 µs (uc03).
   - Ogon `wake_lag_ns` w uc05: p99 281 µs wobec 85 µs.
   - `compute_ns` p50 rośnie o +11 µs (uc05: 74,5 wobec 63,5 µs) i +36 µs (uc06: 258,5 wobec 222,5 µs).
   - W uc03 `compute_ns` ma rozkład dwumodalny (p50 126 µs, p99 2,6 ms), więc porównanie median nic nie daje.
5. **Hipotezy mechanizmu (NIESPRAWDZONE).** Oba źródła działają między rdzeniami i oba wynikają z tego, że zwolnienie biegnie w tej samej przestrzeni adresowej, co wątek slotu:
   - **(H-a) unieważnienie TLB całej przestrzeni adresowej.** Cortex-A72 (ARMv8.0, bez operacji TLBI na zakresach) przy `munmap` dużego zakresu (kolejka uc05 ma 8 MiB, czyli 2048 stron 4 KiB) może unieważniać wpisy TLB całego ASID procesu na wszystkich rdzeniach, także na rdzeniu 3. Slot po takim unieważnieniu płaci chybieniami TLB. Opis progu w jądrze arm64 wymaga sprawdzenia w źródle 6.8; nie został sprawdzony.
   - **(H-b) zaśmiecenie wspólnego L2.** Cztery rdzenie dzielą 1 MiB L2, a `munmap` (tablice stron) i `unlinkat` (zwalnianie stron tmpfs) przechodzą po pamięci, która wypiera dane slotu.
   Obie hipotezy pasują do wzrostu `compute_ns`. Ogon `wake_lag_ns` lepiej pasuje do (H-a) albo do pracy jądra na rdzeniu 3 wywołanej przez zwolnienie, ale to nie jest rozstrzygnięte.

## Znalezisko

**Zwolnienie porzuconej kolejki w wątku komunikacyjnym wciąż wydłuża sloty obudzone w jego trakcie.** Widać to w uc05 i uc06 (p ≤ 2,2e-04 przy n = 270), z wielkością ok. 1 % kosztu sprzed #600. W uc05 podnosi to odsetek okien z przekroczeniem taktu z 10,2 % do 25,2 %.

- Kod silnika nie zatrzymuje slotu na zwolnieniu (punkt 3 eksploracji). Najbardziej prawdopodobne źródło to samo zwalnianie dużego mapowania w procesie, w którym biegnie slot: wpływa ono na rdzeń slotu przez TLB albo wspólne L2 (hipotezy H-a i H-b, niesprawdzone).
- Skutek dla użytkownika: przy takcie 1 ms mniej więcej co siódme zwolnienie porzuconej kolejki dokłada przekroczenie taktu ponad poziom tła (25,2 % wobec 10,2 %).

**Propozycja następnego zadania** (do decyzji człowieka):

1. Pomiar rozstrzygający H-a i H-b na pi400, w aparaturze R600, na uc05:
   - wariant B, w którym kolejka jest zwalniana `munmap` w kawałkach ≤ 2 MiB (512 stron, czyli unieważnianie TLB po zakresie zamiast całego ASID);
   - oraz `perf stat` chybień dTLB i L2 wątku slotu w oknach zwolnienia.
2. Zależnie od wyniku naprawa w silniku. Kandydaci:
   - zwalnianie w kawałkach z przerwą między nimi;
   - ponowne użycie segmentów kolejek zamiast `munmap` w trakcie pracy;
   - mniejszy zapas kolejki (dziś 10 s, `maxElements = 10 s / takt`).

## Granice wniosków

- Jedna maszyna: pi400 (Cortex-A72, wspólne L2, jądro `PREEMPT_RT` 6.8). Na procesorze z TLBI na zakresach albo z prywatnym L2 resztka K2 może być inna. Liczby nie przenoszą się na inne platformy bez pomiaru.
- Tryb `-k -r -t` z `taskset -c 3`: wątek slotu na izolowanym rdzeniu, wątek komunikacyjny na 0-2. Bez izolacji rdzenia wynik K1 by się nie zmienił, a K2 mógłby.
- Klienci podłączani kolejno, po jednym naraz, i porzucający kolejkę bez wyrejestrowania (SIGINT po pierwszym wierszu). Inny wzór porzucania (wielu klientów naraz) nie był mierzony.
- K3 opiera się na 9 przebiegach na stronę. Mniejsze regresje niż rozrzut między przebiegami są niewidoczne.
- Eksploracja jest po pomiarze. Jej p-wartości opisują, a nie rozstrzygają, i nie zmieniają werdyktu K2.

## Pytania otwarte

1. Dlaczego w uc03 B 10,7 % zwolnień trafia w następny slot, skoro takt (5 ms) jest prawie trzy razy dłuższy od zwolnienia (~1,8 ms)? Do rozstrzygnięcia potrzebny jest znacznik chwili porzucenia (np. wpis ftrace z `broadcast()`), którego aparatura R600 nie ma.
2. Który mechanizm (H-a, H-b, inny) niesie resztkę K2? Zob. *Propozycja następnego zadania*.
3. Czy przyjąć #600 jako wykonane z resztką zgłoszoną osobno, czy zostawić #600 otwarte do naprawy resztki? Decyzja człowieka.

## Odtworzenie od zera

Po co: wynik ma dać się sprawdzić i powtórzyć bez rozmowy, w której powstał. Są dwie drogi.

**Ponowna analiza z archiwum** (bez workera, ~15 s):

1. Pobrać `results_20261104_R600_raw.tar.gz` z miejsca przechowywania archiwów i sprawdzić sumę: `sha256sum` musi dać wartość z nagłówka tego pliku.
2. `tar xzf results_20261104_R600_raw.tar.gz -C <katalog>`, co daje `<katalog>/raw/ucNN/{A,B}_PP/`. Każdy plik da się sprawdzić z `results_20261104_R600_raw.index.tsv` (ścieżka względem `raw/`, rozmiar, SHA-256).
3. W tym katalogu (Python ≥ 3.10 z NumPy, np. `retractordb/.venv-python`):
   - `python3 -I analyze.py --raw <katalog>/raw --seed 600` musi dać wydruk identyczny z częścią *Wydruk analizy*;
   - `python3 -I explore_k2.py --raw <katalog>/raw` musi dać wydruk identyczny z częścią *Wydruk eksploracji*.

**Powtórzenie pomiaru** (worker pi400, ~1 h budowy i ~2,5 h kampanii):

1. **Worker** przygotowany jak w R376 (README R376, część *Aparatura*):
   - `isolcpus=3` w cmdline jądra;
   - Conan i `~/.venv`;
   - klon `~/retractordb` i drzewo pomiarowe `~/R376/src`;
   - katalog `~/R376/exec` poza `/dev/shm` (`setcap` nie działa na montowaniu `nosuid`).
2. **Aparatura**: skopiować ten katalog na worker jako `~/R376/apparatus_R600/`.
3. **Korpus** (prywatny `paper-arXiv`; użyty HEAD `cc8c9e4`, ostatnia zmiana `usecases` w `7a76922`). Na hoście, dla każdej rodziny `f` z uc03, uc05, uc06, uc07, uc08:
   ```bash
   ssh pi400 "mkdir -p /dev/shm/r376/data/$f && python3 -I - --out /dev/shm/r376/data/$f" < paper-arXiv/usecases/$f/generate_data.py
   ssh pi400 "cat > /dev/shm/r376/data/$f/query.rql" < paper-arXiv/usecases/$f/rql/query.rql
   ```
   Generatory nie mają losowości. Korpus leży tylko w `/dev/shm`, więc po reboocie workera trzeba go odtworzyć.
4. **Budowa**: `setsid nohup ./build_ab.sh > ~/R376/build_R600.log 2>&1 < /dev/null &`. Koniec: `BUILD_COMPLETE` w logu. SHA-256 binarek muszą równać się tym z `meta.json` przebiegów w archiwum (`xretractor` A `16ad8829...`, B `9eaccd49...`).
5. **Strumień**: `./select_streams.sh`. Zapisuje `streams.tsv` tylko na workerze (embargo).
6. **Kampania**: `setsid nohup ./campaign.sh > ~/R376/campaign_R600.log 2>&1 < /dev/null &`. Koniec: `CAMPAIGN_COMPLETE`, dane w `~/R376/raw_R600/`. Rodzinę przerwaną w połowie powtarza się w całości, żeby zachować kolejność ABBA.
7. **Analiza**: na hoście `rsync -a pi400:R376/raw_R600/ <katalog>/raw/`, potem kroki 3 z poprzedniej drogi. Nowy pomiar da inne liczby; porównuje się werdykty i rzędy wielkości, a nie wydruk bajt w bajt.

## Wydruk analizy


Źródło: `raw`, ziarno 600 (pseudo-zdarzenia zwolnień: 601).

### uc03

| wielkość [ms] | A | B |
|---|---|---|
| przebiegi / podłączenia / bez przypisania / klient bez wiersza lub zabity | 9 / 270 / 0 / 0 | 9 / 270 / 0 / 0 |
| okno W p50 / max | 2.757 / 3.440 | 2.766 / 5.789 |
| mmap kolejki p50 / max | 0.032 / 0.739 | 0.032 / 0.090 |
| zdarzenie podłączenia (opisowo): n_hit / p50 / p99 / max e2e | 154 / 0.277 / 2.898 / 3.043 | 167 / 0.270 / 2.847 / 2.858 |
| **K1** zwolnienia: liczba / w wątku RT / w wątku, który zbudował kolejkę / podłączenia bez zwolnienia | 270 / 270 / 0 / 0 | 270 / 0 / 270 / 0 |
| zwolnienie (munmap+unlinkat) p50 / max | 1.715 / 1.868 | 1.818 / 2.051 |
| **K2** zwolnienia trafione w slot: n / odsetek | 270 / 100.0 % | 29 / 10.7 % |
| **K2** zdarzenie zwolnienia: max e2e p50 / p99 / max | 1.930 / 4.526 / 4.599 | 0.243 / - / 0.300 |
| **K2** pseudo-zdarzenie zwolnienia: liczba / p50 / p99 / max | 5400 / 0.184 / 2.875 / 2.956 | 5400 / 0.182 / 2.839 / 2.983 |
| slot z podłączeniem: liczba / p99 / max | 154 / 2.898 / 3.043 | 167 / 2.847 / 2.858 |
| **K3** kontrola e2e: p50 / p99 / max | 0.179 / 2.724 / 2.979 | 0.179 / 2.696 / 2.983 |
| **K3** kontrola compute: p50 / p99 / max | 0.127 / 2.656 / 2.906 | 0.126 / 2.623 / 2.873 |
| **K3** kontrola wake_lag: p50 / p99 / max | 0.023 / 0.025 / 0.043 | 0.023 / 0.025 / 0.062 |

- K1, zwolnienie poza wątkiem slotu: B 270 z 270 poza wątkiem RT (270 w wątku komunikacyjnym); A 270 z 270 w wątku RT (kontrola dodatnia powtórzona). Werdykt: ZDANE.
- K2, Mann-Whitney zdarzenia zwolnienia > pseudo-zdarzenia: B p = 1.5e-06 (n = 29); kontrola dodatnia A p = 4e-62 (n = 270); różnica median zdarzenie - pseudo: A 1.746 ms, B 0.061 ms. Werdykt: NIEROZSTRZYGNIĘTE (n = 29 < 100).
- K3, compute_ns p50 per przebieg: mediana B-A = -0.22 µs, rozrzut wewnątrz strony do 2.70 µs, permutacyjny MW p = 0.605 - w szumie.
- K3, wake_lag_ns p99 per przebieg: mediana B-A = 0.11 µs, rozrzut wewnątrz strony do 0.74 µs, permutacyjny MW p = 0.912 - w szumie.
- K3, e2e_ns p99 per przebieg: mediana B-A = -58.74 µs, rozrzut wewnątrz strony do 154.86 µs, permutacyjny MW p = 0.161 - w szumie.

### uc05

| wielkość [ms] | A | B |
|---|---|---|
| przebiegi / podłączenia / bez przypisania / klient bez wiersza lub zabity | 9 / 270 / 0 / 0 | 9 / 270 / 0 / 0 |
| okno W p50 / max | 9.789 / 10.173 | 9.785 / 10.419 |
| mmap kolejki p50 / max | 0.041 / 0.119 | 0.040 / 0.083 |
| zdarzenie podłączenia (opisowo): n_hit / p50 / p99 / max e2e | 270 / 0.921 / 1.193 / 6.051 | 270 / 0.921 / 1.204 / 1.262 |
| **K1** zwolnienia: liczba / w wątku RT / w wątku, który zbudował kolejkę / podłączenia bez zwolnienia | 270 / 270 / 0 / 0 | 270 / 0 / 270 / 0 |
| zwolnienie (munmap+unlinkat) p50 / max | 6.138 / 6.789 | 6.383 / 7.196 |
| **K2** zwolnienia trafione w slot: n / odsetek | 270 / 100.0 % | 270 / 100.0 % |
| **K2** zdarzenie zwolnienia: max e2e p50 / p99 / max | 6.401 / 7.387 / 7.415 | 0.773 / 1.389 / 1.517 |
| **K2** pseudo-zdarzenie zwolnienia: liczba / p50 / p99 / max | 5400 / 0.746 / 1.079 / 1.146 | 5400 / 0.744 / 1.072 / 1.166 |
| slot z podłączeniem: liczba / p99 / max | 2702 / 1.157 / 6.051 | 2700 / 1.142 / 1.262 |
| **K3** kontrola e2e: p50 / p99 / max | 0.121 / 1.044 / 1.208 | 0.121 / 1.032 / 1.432 |
| **K3** kontrola compute: p50 / p99 / max | 0.063 / 0.978 / 1.110 | 0.063 / 0.967 / 1.283 |
| **K3** kontrola wake_lag: p50 / p99 / max | 0.023 / 0.096 / 0.267 | 0.023 / 0.085 / 0.516 |

- K1, zwolnienie poza wątkiem slotu: B 270 z 270 poza wątkiem RT (270 w wątku komunikacyjnym); A 270 z 270 w wątku RT (kontrola dodatnia powtórzona). Werdykt: ZDANE.
- K2, Mann-Whitney zdarzenia zwolnienia > pseudo-zdarzenia: B p = 0.000217 (n = 270); kontrola dodatnia A p = 4.71e-170 (n = 270); różnica median zdarzenie - pseudo: A 5.655 ms, B 0.030 ms. Werdykt: NIEZDANE.
- K3, compute_ns p50 per przebieg: mediana B-A = 0.22 µs, rozrzut wewnątrz strony do 1.28 µs, permutacyjny MW p = 0.287 - w szumie.
- K3, wake_lag_ns p99 per przebieg: mediana B-A = -10.59 µs, rozrzut wewnątrz strony do 20.22 µs, permutacyjny MW p = 0.00777 - w szumie.
- K3, e2e_ns p99 per przebieg: mediana B-A = -12.39 µs, rozrzut wewnątrz strony do 81.43 µs, permutacyjny MW p = 0.00777 - w szumie.

### uc06

| wielkość [ms] | A | B |
|---|---|---|
| przebiegi / podłączenia / bez przypisania / klient bez wiersza lub zabity | 9 / 270 / 0 / 0 | 9 / 270 / 0 / 0 |
| okno W p50 / max | 6.282 / 6.925 | 6.305 / 6.697 |
| mmap kolejki p50 / max | 0.038 / 0.093 | 0.039 / 0.062 |
| zdarzenie podłączenia (opisowo): n_hit / p50 / p99 / max e2e | 270 / 0.442 / 46.580 / 48.676 | 270 / 0.435 / 46.082 / 46.347 |
| **K1** zwolnienia: liczba / w wątku RT / w wątku, który zbudował kolejkę / podłączenia bez zwolnienia | 270 / 270 / 0 / 0 | 270 / 0 / 270 / 0 |
| zwolnienie (munmap+unlinkat) p50 / max | 3.897 / 4.198 | 4.109 / 5.453 |
| **K2** zwolnienia trafione w slot: n / odsetek | 270 / 100.0 % | 270 / 100.0 % |
| **K2** zdarzenie zwolnienia: max e2e p50 / p99 / max | 4.242 / 50.547 / 50.616 | 0.415 / 42.616 / 42.682 |
| **K2** pseudo-zdarzenie zwolnienia: liczba / p50 / p99 / max | 5400 / 0.372 / 46.920 / 47.179 | 5400 / 0.373 / 46.193 / 47.494 |
| slot z podłączeniem: liczba / p99 / max | 2086 / 45.140 / 48.676 | 2271 / 44.652 / 46.347 |
| **K3** kontrola e2e: p50 / p99 / max | 0.292 / 44.948 / 47.179 | 0.291 / 44.350 / 47.494 |
| **K3** kontrola compute: p50 / p99 / max | 0.222 / 0.349 / 47.106 | 0.223 / 0.355 / 47.303 |
| **K3** kontrola wake_lag: p50 / p99 / max | 0.023 / 42.990 / 45.251 | 0.023 / 42.391 / 45.577 |

- K1, zwolnienie poza wątkiem slotu: B 270 z 270 poza wątkiem RT (270 w wątku komunikacyjnym); A 270 z 270 w wątku RT (kontrola dodatnia powtórzona). Werdykt: ZDANE.
- K2, Mann-Whitney zdarzenia zwolnienia > pseudo-zdarzenia: B p = 5.18e-16 (n = 270); kontrola dodatnia A p = 2.66e-55 (n = 270); różnica median zdarzenie - pseudo: A 3.870 ms, B 0.043 ms. Werdykt: NIEZDANE.
- K3, compute_ns p50 per przebieg: mediana B-A = 0.26 µs, rozrzut wewnątrz strony do 1.55 µs, permutacyjny MW p = 0.53 - w szumie.
- K3, wake_lag_ns p99 per przebieg: mediana B-A = -595.63 µs, rozrzut wewnątrz strony do 658.41 µs, permutacyjny MW p = 4.11e-05 - w szumie.
- K3, e2e_ns p99 per przebieg: mediana B-A = -594.98 µs, rozrzut wewnątrz strony do 669.19 µs, permutacyjny MW p = 4.11e-05 - w szumie.

### uc07

| wielkość [ms] | A | B |
|---|---|---|
| przebiegi / podłączenia / bez przypisania / klient bez wiersza lub zabity | 9 / 270 / 0 / 0 | 9 / 270 / 0 / 0 |
| okno W p50 / max | 0.973 / 1.064 | 0.971 / 1.137 |
| mmap kolejki p50 / max | 0.028 / 0.080 | 0.027 / 0.075 |
| zdarzenie podłączenia (opisowo): n_hit / p50 / p99 / max e2e | 17 / 0.200 / - / 0.421 | 12 / 0.213 / - / 0.409 |
| **K1** zwolnienia: liczba / w wątku RT / w wątku, który zbudował kolejkę / podłączenia bez zwolnienia | 270 / 270 / 0 / 0 | 270 / 0 / 270 / 0 |
| zwolnienie (munmap+unlinkat) p50 / max | 0.607 / 0.716 | 0.637 / 0.743 |
| **K2** zwolnienia trafione w slot: n / odsetek | 270 / 100.0 % | 0 / 0.0 % |
| **K2** zdarzenie zwolnienia: max e2e p50 / p99 / max | 0.739 / 2.628 / 2.687 | - / - / - |
| **K2** pseudo-zdarzenie zwolnienia: liczba / p50 / p99 / max | 5393 / 0.121 / 2.275 / 2.354 | 5396 / 0.122 / 2.267 / 2.380 |
| slot z podłączeniem: liczba / p99 / max | 17 / 0.421 / 0.421 | 12 / 0.409 / 0.409 |
| **K3** kontrola e2e: p50 / p99 / max | 0.117 / 2.080 / 2.354 | 0.119 / 2.070 / 2.380 |
| **K3** kontrola compute: p50 / p99 / max | 0.063 / 2.010 / 2.259 | 0.065 / 1.998 / 2.271 |
| **K3** kontrola wake_lag: p50 / p99 / max | 0.023 / 0.025 / 0.030 | 0.023 / 0.026 / 0.127 |

- K1, zwolnienie poza wątkiem slotu: B 270 z 270 poza wątkiem RT (270 w wątku komunikacyjnym); A 270 z 270 w wątku RT (kontrola dodatnia powtórzona). Werdykt: ZDANE.
- K2, Mann-Whitney zdarzenia zwolnienia > pseudo-zdarzenia: B p = nan (n = 0); kontrola dodatnia A p = 4.86e-128 (n = 270); różnica median zdarzenie - pseudo: A 0.618 ms. Werdykt: NIEROZSTRZYGNIĘTE (n = 0 < 100).
- K3, compute_ns p50 per przebieg: mediana B-A = 1.13 µs, rozrzut wewnątrz strony do 3.56 µs, permutacyjny MW p = 0.0188 - w szumie.
- K3, wake_lag_ns p99 per przebieg: mediana B-A = -0.07 µs, rozrzut wewnątrz strony do 18.23 µs, permutacyjny MW p = 0.931 - w szumie.
- K3, e2e_ns p99 per przebieg: mediana B-A = -19.28 µs, rozrzut wewnątrz strony do 62.94 µs, permutacyjny MW p = 0.297 - w szumie.

### uc08

| wielkość [ms] | A | B |
|---|---|---|
| przebiegi / podłączenia / bez przypisania / klient bez wiersza lub zabity | 9 / 270 / 0 / 0 | 9 / 270 / 0 / 0 |
| okno W p50 / max | 0.466 / 0.583 | 0.467 / 0.566 |
| mmap kolejki p50 / max | 0.026 / 0.082 | 0.026 / 0.092 |
| zdarzenie podłączenia (opisowo): n_hit / p50 / p99 / max e2e | 5 / 0.404 / - / 0.727 | 2 / 0.419 / - / 1.122 |
| **K1** zwolnienia: liczba / w wątku RT / w wątku, który zbudował kolejkę / podłączenia bez zwolnienia | 270 / 270 / 0 / 0 | 270 / 0 / 270 / 0 |
| zwolnienie (munmap+unlinkat) p50 / max | 0.331 / 0.390 | 0.322 / 0.495 |
| **K2** zwolnienia trafione w slot: n / odsetek | 270 / 100.0 % | 0 / 0.0 % |
| **K2** zdarzenie zwolnienia: max e2e p50 / p99 / max | 0.677 / 1.616 / 1.673 | - / - / - |
| **K2** pseudo-zdarzenie zwolnienia: liczba / p50 / p99 / max | 2019 / 0.334 / 1.260 / 1.473 | 2119 / 0.336 / 1.254 / 1.418 |
| slot z podłączeniem: liczba / p99 / max | 5 / 0.727 / 0.727 | 2 / 1.122 / 1.122 |
| **K3** kontrola e2e: p50 / p99 / max | 0.324 / 1.236 / 1.473 | 0.322 / 1.230 / 1.418 |
| **K3** kontrola compute: p50 / p99 / max | 0.263 / 1.153 / 1.310 | 0.261 / 1.148 / 1.283 |
| **K3** kontrola wake_lag: p50 / p99 / max | 0.023 / 0.027 / 0.058 | 0.023 / 0.026 / 0.029 |

- K1, zwolnienie poza wątkiem slotu: B 270 z 270 poza wątkiem RT (270 w wątku komunikacyjnym); A 270 z 270 w wątku RT (kontrola dodatnia powtórzona). Werdykt: ZDANE.
- K2, Mann-Whitney zdarzenia zwolnienia > pseudo-zdarzenia: B p = nan (n = 0); kontrola dodatnia A p = 1.38e-41 (n = 270); różnica median zdarzenie - pseudo: A 0.343 ms. Werdykt: NIEROZSTRZYGNIĘTE (n = 0 < 100).
- K3, compute_ns p50 per przebieg: mediana B-A = -0.63 µs, rozrzut wewnątrz strony do 4.70 µs, permutacyjny MW p = 0.161 - w szumie.
- K3, wake_lag_ns p99 per przebieg: mediana B-A = -0.13 µs, rozrzut wewnątrz strony do 6.90 µs, permutacyjny MW p = 0.297 - w szumie.
- K3, e2e_ns p99 per przebieg: mediana B-A = -2.01 µs, rozrzut wewnątrz strony do 49.64 µs, permutacyjny MW p = 0.489 - w szumie.



## Wydruk eksploracji

### uc03 A (takt 5.000 ms)
- slot trwajacy przy starcie zwolnienia: n=270 p50=1.932 p99=4.517 max=4.599 ms
- sloty obudzone w trakcie zwolnienia:   n=0; > takt -; MW > pseudo p = nan
- pseudo-zdarzenia zwolnienia:           n=5400 p50=0.184 p99=2.875 max=2.956 ms; > takt 0.0 %

### uc03 B (takt 5.000 ms)
- slot trwajacy przy starcie zwolnienia: n=0
- sloty obudzone w trakcie zwolnienia:   n=29 p50=0.243 p99=- max=0.300 ms; > takt 0.0 %; MW > pseudo p = 7.98e-07
- pseudo-zdarzenia zwolnienia:           n=5400 p50=0.182 p99=2.828 max=2.956 ms; > takt 0.0 %
- wake obudzonych p50 / p99: 26.3 / 30.0 us (kontrola 22.9 / 24.6 us)
- compute obudzonych p50 / p99: 166.6 / 190.0 us (kontrola 126.4 / 2623.4 us)

### uc05 A (takt 1.000 ms)
- slot trwajacy przy starcie zwolnienia: n=270 p50=6.401 p99=7.374 max=7.415 ms
- sloty obudzone w trakcie zwolnienia:   n=270 p50=5.651 p99=6.678 max=6.723 ms; > takt 100.0 %; MW > pseudo p = 4.71e-170
- pseudo-zdarzenia zwolnienia:           n=5400 p50=0.749 p99=1.082 max=1.173 ms; > takt 11.3 %
- wake obudzonych p50 / p99: 3643.2 / 6193.4 us (kontrola 22.7 / 95.7 us)
- compute obudzonych p50 / p99: 64.9 / 1045.9 us (kontrola 63.4 / 978.3 us)

### uc05 B (takt 1.000 ms)
- slot trwajacy przy starcie zwolnienia: n=27 p50=0.129 p99=- max=0.405 ms
- sloty obudzone w trakcie zwolnienia:   n=270 p50=0.776 p99=1.386 max=1.517 ms; > takt 25.2 %; MW > pseudo p = 4.71e-05
- pseudo-zdarzenia zwolnienia:           n=5400 p50=0.741 p99=1.075 max=1.245 ms; > takt 10.2 %
- wake obudzonych p50 / p99: 25.4 / 280.6 us (kontrola 22.7 / 85.1 us)
- compute obudzonych p50 / p99: 74.5 / 1127.1 us (kontrola 63.5 / 966.7 us)

### uc06 A (takt 2.000 ms)
- slot trwajacy przy starcie zwolnienia: n=270 p50=4.236 p99=50.532 max=50.616 ms
- sloty obudzone w trakcie zwolnienia:   n=270 p50=2.736 p99=47.288 max=48.889 ms; > takt 100.0 %; MW > pseudo p = 1.24e-48
- pseudo-zdarzenia zwolnienia:           n=5400 p50=0.372 p99=46.908 max=47.165 ms; > takt 24.1 %
- wake obudzonych p50 / p99: 2075.8 / 9991.3 us (kontrola 22.8 / 42989.2 us)
- compute obudzonych p50 / p99: 302.1 / 467.6 us (kontrola 222.4 / 348.5 us)

### uc06 B (takt 2.000 ms)
- slot trwajacy przy starcie zwolnienia: n=17 p50=40.982 p99=- max=42.682 ms
- sloty obudzone w trakcie zwolnienia:   n=270 p50=0.414 p99=5.966 max=6.031 ms; > takt 4.8 %; MW > pseudo p = 1.11e-15
- pseudo-zdarzenia zwolnienia:           n=5400 p50=0.372 p99=46.176 max=47.494 ms; > takt 23.3 %
- wake obudzonych p50 / p99: 26.2 / 5612.2 us (kontrola 22.8 / 42391.4 us)
- compute obudzonych p50 / p99: 258.5 / 426.9 us (kontrola 222.5 / 354.6 us)

