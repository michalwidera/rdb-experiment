# R376b - powtórzenie uc05 z R376: opóźnienie slotu przy podłączeniu klienta przed i po #283 (pi400, `--realtime`)

Zgłoszenie: michalwidera/retractordb#376. Decyzja człowieka 2026-11-07: wariant (b) - przed zamknięciem #376 powtórzyć pomiar uc05. Ten plik zapisano PRZED pomiarem. Zmiany protokołu po starcie kampanii trafiają do sekcji *Aneksy* z datą i powodem, nie do treści powyżej.

**Stan: zatwierdzony przez człowieka 2026-11-07** (L1-L3 według rekomendacji, L4 z dopiskiem człowieka: komentarz wyniku zawiera opis badania i wyjaśnienie werdyktu; *Decyzje*).

Aparatura, przypisanie podłączenia do slotu, metryki i kryteria pochodzą z R376 (`results_20261104_R376/`, protokół `5bb5448`, wynik `d55f3f6`, scalenie do `main` `2dd0be8`). Poniżej są tylko różnice.

## Pytanie

Czy w uc05 efekt #283 spełnia kryterium R376 (p99 zdarzeniowe B < A, oba stabilne, Mann-Whitney A > B p < 0,01), gdy z metryki głównej wyłączy się zdarzenia podłączenia, które zbiegły się ze zwolnieniem kolejki wcześniejszego klienta w wątku slotu (#600).

## Dlaczego powtórzenie

W R376 uc05 dostało werdykt NIEPOTWIERDZONY: p99 niestabilne po obu stronach (A 15,40 ms, B 6,89 ms). Przyczyną były nieliczne zdarzenia, których sloty trafiły na okno zwolnienia kolejki (~6 ms w wątku slotu, w A i B jednakowo): 3 w A i 6 w B na 270. W eksploracji po pomiarze, bez tych zdarzeń, p99 było stabilne: A 11,055 [10,880, 11,312] ms, B 1,254 [1,211, 1,434] ms, MW 9,8e-89. Eksploracja powstała po obejrzeniu danych i werdyktu nie zmieniała. R376b ustala tę regułę **przed** pomiarem i sprawdza ją na nowych danych.

Zwolnienie kolejki w wątku slotu istnieje w obu stronach, bo obie są sprzed #600. To cecha rewizji A i B, a nie błąd aparatury. Zbieżność jest losowa: zwolnienie przychodzi ~10 s po podłączeniu (kolejka zapełnia się 10 s danych bez odbiorcy), a podłączenia mają odstępy U(2; 3) s, więc okno zwolnienia klienta k wypada w pobliżu podłączenia k+4.

## Strony porównania

Bez zmian wobec R376 i bez przebudowy. Binarki z kampanii R376 leżą na workerze:

| Strona | Rewizja | Binarki |
|---|---|---|
| A | `96b74dc0` + P1 | `~/R376/bin/A/{xretractor,xqry}` |
| B | `393b24ca` + P1 | `~/R376/bin/B/{xretractor,xqry}` |

`campaign.sh` przed kampanią porównuje sumy SHA-256 obu binarek z wartościami zapisanymi w `meta.json` przebiegów uc05 R376 (archiwum `rdb-experiment-embargo/R376/`). Rozbieżność zatrzymuje kampanię.

## Aparatura

`run_one.py`, `select_streams.sh`, `P1_deadline_ns.patch` i `build_ab.sh` R376 bez zmian, uruchamiane z `~/R376/apparatus`. Ta sama jest też ścieżka `~/R376/exec`, `taskset -c 3`, `setcap`, ftrace i rozgrzewka. Korpus uc05 jest w `/dev/shm/r376/data/uc05`, odtworzony procedurą R600 i sprawdzony skrótem drzewa z README R603C. Strumień subskrybowany pochodzi z `~/R376/apparatus/streams.tsv` (takt 1/800 s, kolejka 8 MiB).

Różnice:

1. **Tylko uc05.**
2. **60 podłączeń na przebieg zamiast 30 (L2).** `run_one.py --conns 60`, odstęp nadal U(2; 3) s. Daje to 540 zdarzeń na stronę zamiast 270. Uzasadnienie: w eksploracji R376 p99 B miało półszerokość 0,112 ms przy granicy stabilności 0,125 ms (10 % z 1,254), czyli zapas 11 %. Przy dwukrotnie większej liczności półszerokość powinna spaść o ~30 %. Na żywe kolejki wystarcza miejsca: co najwyżej ~5 jednocześnie po 8 MiB, przy `/dev/shm` 1,9 GiB.
3. **9 par ABBA** (para nieparzysta AB, parzysta BA), jak R376. Razem 18 przebiegów po ~3,1 min, ~1 h.
4. Surowe dane w `~/R376/raw_R376b/uc05/<strona>_<para>/`, log `~/R376/campaign_R376b.log`.

## Metryki i kryteria (ustalone przed pomiarem)

Definicje okna W, slotu z podłączeniem, slotu kontrolnego, okna zwolnienia i pseudo-zdarzeń są takie jak w R376 (*Przypisanie podłączenia do slotu*, *Metryki i kryteria*). Bootstrap 2000 losowań, ziarno 3762.

- **Zdarzenie na zwolnieniu**: zdarzenie podłączenia, którego co najmniej jeden slot z podłączeniem (przedział [`deadline_ns`, `deadline_ns + e2e_ns`]) ma część wspólną z którymkolwiek oknem zwolnienia w tym przebiegu. To jest reguła `on_release` z eksploracji R376, bez zmian.
- **Metryka główna R376b (G)**: rozkład po zdarzeniach max `e2e_ns` slotów z podłączeniem, **bez zdarzeń na zwolnieniu**. Raportowane są p50, p99 z przedziałem bootstrap, max i liczność, a osobno liczba wyłączonych zdarzeń na stronę.
- **Efekt #283 POTWIERDZONY w uc05**, gdy według G:
  - p99 B < p99 A;
  - oba p99 są stabilne (półszerokość 95 % przedziału ≤ 10 % wartości);
  - Mann-Whitney A > B daje p < 0,01;
  - `n_hit` ≥ 100 na stronę.
- **NIEPOTWIERDZONY**, gdy p99 B ≥ p99 A albo MW p ≥ 0,01.
- **NIEROZSTRZYGNIĘTY**, gdy któreś p99 jest niestabilne albo `n_hit` < 100. Kampanii nie przedłuża się bez decyzji człowieka.
- **Kryterium R376 na wszystkich zdarzeniach (opisowo)**: ta sama tabela co w R376, ze zdarzeniami na zwolnieniu. Pokazuje, czy w nowych danych zbieżności znów psują p99.
- **Kontrola aparatury**: jak R376. `compute_ns` p50 i `wake_lag_ns` p99 w slotach kontrolnych per przebieg, różnica median A-B wobec rozrzutu wewnątrz strony, dokładny permutacyjny MW 9 vs 9. Różnica wyraźnie większa od rozrzutu wstrzymuje wniosek.
- **Opisowo, jak R376**: ryzyko szczątkowe (zdarzenia B wobec pseudo-zdarzeń B, MW i różnica median, liczone bez zdarzeń na zwolnieniu), długość okna W, zwolnienia kolejki (liczba, w wątku RT, długość, max `e2e_ns` slotów na zwolnieniu), skala efektu (p50 zdarzenia minus p50 pseudo-zdarzenia).
- **Odtwarzalność R376 (opisowo)**: G wobec eksploracji R376 (A 11,055 / B 1,254 ms), p50 zdarzeń wobec R376 (A 9,873 / B 1,024 ms), nadmiar w B wobec +0,105 ms.

Ważność przebiegu jak w R376: wątek `SCHED_FIFO` na rdzeniu 3, `VmLck` > 0, governor `performance`, binarki zgodne z sumami, każdy klient z wierszem. **Liczność**: co najmniej 8 ważnych przebiegów na stronę. Przebieg nieważny jest raportowany i nie jest powtarzany.

## Przewidywanie przed pomiarem

| wielkość | A | B |
|---|---|---|
| G: p50 / p99 [ms] | ~9,9 / ~11,1 (stabilne) | ~1,0 / ~1,25 (stabilne) |
| zdarzenia na zwolnieniu (na 540) | ~5-15 | ~5-15 |
| wszystkie zdarzenia: p99 | możliwe niestabilne | możliwe niestabilne |
| MW A > B (G) | p ≪ 0,01 | |
| nadmiar B nad pseudo B | | ~+0,1 ms, istotny |

Werdykt przewidywany: **POTWIERDZONY**. Główne ryzyko to niestabilne p99 B mimo wyłączenia zdarzeń na zwolnieniu. Taki wynik oznaczałby, że ogon B tworzy jeszcze inne zjawisko niż zwolnienie kolejki.

## Kolejność

1. **Protokół** (ten plik) zatwierdzony przez człowieka; gałąź `experiment/20261107_R376b`, commit i push.
2. **Aparatura**:
   - `campaign.sh`: kopia kampanii R376 dla samego uc05, z `--conns 60`, sprawdzeniem sum binarek i katalogiem `raw_R376b`;
   - `analyze.py`: importuje `../results_20261104_R376/analyze.py` bez zmian i dokłada G z werdyktem.
   - Test analizy: na surowych danych uc05 R376 G musi odtworzyć liczby eksploracji R376 (A 11,055 [10,880, 11,312], B 1,254 [1,211, 1,434] ms przy ziarnie 376), a tabela na wszystkich zdarzeniach - wydruk R376.
3. **Suchy przebieg**: po 1 przebiegu A i B z 60 podłączeniami (~6 min, `~/R376/dry_R376b`), odczepiony. Sprawdzenie ważności, długości przebiegu i zajętości `/dev/shm`. Dane nie wchodzą do wyniku.
4. **Kampania** (~1 h): `setsid nohup ./campaign.sh > ~/R376/campaign_R376b.log 2>&1 < /dev/null &`. Do jej oczekiwanego końca sesja nie łączy się z workerem.
5. **Wynik**: `wynik.md`, archiwum w `paper-arXiv/rdb-experiment-embargo/R376b/`, komentarz w #376.

## Decyzje (zatwierdzone przez człowieka 2026-11-07)

- **L1 - strony.** Te same binarki A i B co w R376, bez przebudowy (rekomendacja). Alternatywa: rewizje na obecnym `master`, gdzie zwolnienie kolejki nie biegnie już w wątku slotu. Wymagałaby jednak łatki przywracającej `subscribe()` pod blokadę epoki, czyli zmiany kodu współbieżnego tylko na potrzeby pomiaru, i nie byłaby powtórzeniem R376.
- **L2 - 60 podłączeń na przebieg** (rekomendacja; 30 jak w R376 daje zapas stabilności p99 B ~11 %).
- **L3 - zdarzenia na zwolnieniu wyłączone z metryki głównej, regułą z eksploracji R376** (rekomendacja). Kryterium na wszystkich zdarzeniach zostaje opisowe. Alternatywa: zapobiegać zbieżnościom w aparaturze, przez dobór chwil podłączeń z dala od przewidywanych zwolnień. To jednak zmienia losową fazę podłączeń względem slotu i aparaturę R376.
- **L4 - zamknięcie #376**: przy werdykcie POTWIERDZONY albo NIEPOTWIERDZONY wynik idzie do #376, a zgłoszenie zamyka człowiek. Przy NIEROZSTRZYGNIĘTYM decyzja wraca do człowieka. Dopisek człowieka: komentarz wyniku w #376 zawiera **opis badania** (dlaczego powtórzenie, co się zmieniło wobec R376: tylko uc05, 60 podłączeń, reguła wyłączenia ustalona przed pomiarem; strony i aparatura bez zmian) i **wyjaśnienie werdyktu** (co znaczy dla #283 i dla werdyktu uc05 z R376, czym jest zdarzenie na zwolnieniu i dlaczego jego wyłączenie nie faworyzuje żadnej strony, granice wniosków). Komentarz zawiera tylko identyfikator rodziny i liczby wyprowadzone.

## Granice wniosków (znane przed pomiarem)

- Jedna rodzina (uc05) i jedna platforma. Obie strony są sprzed #600, więc wynik mówi o #283 w kodzie z tamtego czasu, nie o obecnym `master`.
- Wyłączenie zdarzeń na zwolnieniu usuwa znane zjawisko z ogona. Nie dowodzi, że innych zjawisk w ogonie nie ma.
- Przyczyny nadmiaru w B (`mmap_lock`, `clientMapsMutex_`) to badanie nie rozstrzyga (R376, *Ryzyko szczątkowe*).

## Embargo

Jak R376: w tym katalogu i w komentarzach do zgłoszeń wyłącznie identyfikator rodziny (uc05) i liczby wyprowadzone. Plany, dane, generatory i nazwy strumieni zostają na workerze w `/dev/shm/r376` i w prywatnym `paper-arXiv`, w katalogu `rdb-experiment-embargo/R376b/`. Tutaj zostaje indeks sum.

## Aneksy

- **A1 (2026-11-07, przed suchym przebiegiem i kampanią) - doprecyzowanie aparatury i werdyktu, bez zmiany metryk.**
  - Kolejność rozstrzygnięć G, gdy warunki się nakładają: najpierw NIEPOTWIERDZONY (p99 B ≥ p99 A albo MW p ≥ 0,01), potem NIEROZSTRZYGNIĘTY (mniej niż 8 ważnych przebiegów na stronę, `n_hit` < 100 albo któreś p99 niestabilne), potem kontrola aparatury: różnica poza rozrzutem daje NIEROZSTRZYGNIĘTY z dopiskiem „kontrola aparatury wstrzymuje wniosek”. W przeciwnym razie POTWIERDZONY. Powód: protokół nie mówi, co przeważa przy jednoczesnym braku kierunku i niestabilnym p99.
  - `campaign.sh` nie przerywa kampanii po nieważnym przebiegu (R376 przerywało przez `set -e`). Zapisuje go w logu, a `analyze.py` wyłącza go i wypisuje z powodem. Tak każe *Ważność przebiegu*: przebieg nieważny jest raportowany i nie jest powtarzany.
  - `analyze.py` sprawdza ważność przed analizą: `rt_ok`, governor, liczbę podłączeń, sumy obu binarek wobec R376, wątek `SCHED_FIFO` na rdzeniu 3 (`rt.txt`) i wiersz dla każdego klienta.
  - Bootstrap G ma osobny generator z ziarnem `--seed`, jak eksploracja R376. Raport R376 drukowany przed G (kryterium na wszystkich zdarzeniach) zawiera też linię eksploracji R376, liczoną bez zmian, z ziarnem 376.
  - **Test analizy (Kolejność, punkt 2) zdany** na archiwum R376 rozpakowanym od nowa (indeks zgodny): `analyze.py --raw <raw R376> --seed 376 --conns 30` daje część R376 bajt w bajt równą wydrukowi `../results_20261104_R376/analyze.py --seed 376`, który jest równy *Wydrukowi analizy* w `wynik.md` R376. G w uc05: A 11,055 [10,880, 11,312] ms, n = 267 (3 wyłączone), B 1,254 [1,211, 1,434] ms, n = 264 (6 wyłączonych), MW 9,75e-89. To liczby eksploracji R376.
