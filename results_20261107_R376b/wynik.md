# R376b - wynik

Badanie: powtórzenie pomiaru uc05 z R376 (michalwidera/retractordb#376): opóźnienie slotu przy podłączeniu klienta przed #283 (A = `96b74dc0` + P1) i po nim (B = `393b24ca` + P1). Protokół i kryteria w `README.md`. Commity: protokół zatwierdzony przed pomiarem `d14430e` (decyzje L1-L4), aparatura, test analizy i aneks A1 `2d1912b`, suchy przebieg `a3a37da`.

Kampania trwała 2026-11-07 12:07:04 - 12:58:59 na pi400: rodzina uc05, 9 par A/B w kolejności ABBA, 60 podłączeń `xqry -s <strumień> -m 1` na przebieg w odstępach U(2; 3) s. Razem 18 przebiegów i 1080 podłączeń. Binarki to te same pliki co w R376, bez przebudowy (`~/R376/bin/A`, `~/R376/bin/B`). `campaign.sh` sprawdził przed startem sumy SHA-256 `xretractor` i `xqry` obu stron wobec `meta.json` przebiegów uc05 R376 i wszystkie cztery się zgadzały. Log kończy się `CAMPAIGN_COMPLETE`, a jego kopia to `campaign.log`. Od startu kampanii do 13:02:55 sesja nie łączyła się z workerem. Polecenie startu przerwał po 30 s `timeout`, bo `ssh` nie zamknął kanału przy odczepionym procesie, tak jak w suchym przebiegu. Kampanii to nie dotknęło.

**Ważność przebiegów: 18 z 18.** W każdym przebiegu:

- 1 wątek `SCHED_FIFO` na rdzeniu 3 i `VmLck` > 0;
- governor `performance`;
- sumy obu binarek zgodne z R376;
- 60 z 60 klientów z wierszem i 0 podłączeń bez przypisanego okna W;
- 60 z 60 zwolnień kolejki w wątku slotu.

`/dev/shm` przed każdym przebiegiem zajmował 1,38-1,41 MB.

Surowe dane leżą poza tym repozytorium, w prywatnym `paper-arXiv`, w katalogu `rdb-experiment-embargo/R376b/`, bo pochodzą z korpusu objętego embargiem. Archiwum `results_20261107_R376b_raw.tar.gz` ma 40 466 715 B i SHA-256 `f3da5bf50d57e48b25f34a8ec7b5adbdeea5d593c68493f08a558f0c780c3e3b`. Indeks 108 plików jest tutaj, w `results_20261107_R376b_raw.index.tsv`. Analiza: `analyze.py --raw <raw>` (ziarno domyślne 3762). Jej pełny wydruk jest w części *Wydruk analizy*.

## Odpowiedź

**Efekt #283 w uc05 jest POTWIERDZONY według metryki głównej G, ustalonej przed pomiarem.** G pomija zdarzenia podłączenia, których slot zbiegł się ze zwolnieniem kolejki wcześniejszego klienta.

| wielkość | A | B | kryterium |
|---|---|---|---|
| zdarzenia z przypisanym slotem / na zwolnieniu (wyłączone) | 540 / 13 | 540 / 13 | - |
| G: n_hit | 527 | 527 | ≥ 100: spełnione |
| G: p50 / max [ms] | 10,205 / 11,943 | 1,066 / 1,305 | - |
| G: p99 [95 % CI] [ms] | 11,491 [11,396, 11,526] | 1,283 [1,263, 1,296] | B < A: spełnione |
| półszerokość CI / p99 | 0,6 % | 1,3 % | ≤ 10 %: oba stabilne |
| MW G A > B | p = 4,6e-174 | | < 0,01: spełnione |
| kontrola aparatury: `compute_ns` p50, `wake_lag_ns` p99 per przebieg | | | w szumie (permutacyjny MW p = 0,34 i 0,86) |
| **werdykt** | | | **POTWIERDZONY** |

- **Co to znaczy dla #283.** Po #283 budowa kolejki nowego klienta prawie znika z wątku slotu. W A podłączenie wydłuża slot (p50 zdarzenia minus p50 pseudo-zdarzenia tej strony) o 9,24 ms, a w B o 0,10 ms, czyli o 98,9 % mniej. Typowy slot z podłączeniem kosztuje w B ~1,07 ms zamiast ~10,2 ms, a p99 spada z 11,5 do 1,28 ms.
- **Co to znaczy dla werdyktu uc05 z R376.** W R376 uc05 dostało NIEPOTWIERDZONY, bo p99 obu stron było niestabilne. Reguła wyłączenia zastosowana tam po fakcie, w eksploracji, dawała stabilne p99 i ten sam kierunek. R376b ustaliło ją przed pomiarem i sprawdziło na nowych, dwukrotnie liczniejszych danych. Wynik eksploracji się powtórzył: p99 stabilne z zapasem 8-17 razy większym niż granica stabilności. Werdykt uc05 z R376 pozostaje formalnie zapisany. R376b zastępuje go wnioskiem dla uc05: efekt #283 jest potwierdzony w metryce bez zdarzeń na zwolnieniu, a na wszystkich zdarzeniach p99 nadal jest niestabilne (niżej).
- **Zdarzenie na zwolnieniu.** Zdarzenie podłączenia, którego slot z podłączeniem ma część wspólną z oknem zwolnienia kolejki (`munmap` + `unlinkat`) dowolnego wcześniejszego klienta w tym samym przebiegu. Obie rewizje są sprzed #600, więc kolejkę porzuconą przez klienta zwalnia wątek slotu. Trwa to ~5,9 ms (p50 5,93 ms w A, 5,91 ms w B). Zwolnienie przychodzi ~10 s po podłączeniu, gdy kolejka zapełni się danymi bez odbiorcy. Jego zbieżność z podłączeniem kolejnego klienta jest losowa.
- **Dlaczego wyłączenie nie faworyzuje żadnej strony.**
  - Reguła jest ta sama w A i B i zależy tylko od położenia slotu względem okna zwolnienia, nie od jego `e2e_ns`.
  - Zwolnienie jest w obu rewizjach jednakowe: ten sam kod, ~5,9 ms w wątku slotu.
  - Wyłączono tyle samo zdarzeń, po 13 z 540 w każdej stronie, rozłożonych po 6 z 9 przebiegów A i 7 z 9 przebiegów B.
  - Reguła usuwa z ogona obu stron zjawisko, którego #283 nie dotyczy. Bez niej p99 mierzy zbieżność ze zwolnieniem (max `e2e_ns` zdarzeń na zwolnieniu: A 10,8-17,3 ms, B 5,3-7,4 ms), a nie koszt podłączenia.
- **Kryterium R376 na wszystkich zdarzeniach (opisowo): NIEPOTWIERDZONY, jak w R376.** p99 A 15,568 [11,943, 16,406] ms, p99 B 6,401 [5,438, 6,875] ms, oba niestabilne. Przy 13 zdarzeniach na zwolnieniu na 540 (2,4 %) p99 wypada wśród nich, w obu stronach. Liczniejsza kampania tego nie zmienia: zbieżności występują w tej samej proporcji, a w R376 było ich 3 i 6 na 270. MW A > B na wszystkich zdarzeniach p = 2,6e-178.
- **Ryzyko szczątkowe (opisowo).** Zdarzenia G w B przewyższają pseudo-zdarzenia B o 0,099 ms (mediana), MW p = 1,6e-70. Na wszystkich zdarzeniach nadmiar wynosi 0,100 ms, w R376 0,105 ms. Wątek slotu w B nadal płaci za podłączenie stały, mały koszt. Jego przyczyny (`mmap_lock`, `clientMapsMutex_`) badanie nie rozstrzyga, tak jak R376.

| przewidywanie (README) | A | B | wynik A | wynik B |
|---|---|---|---|---|
| G: p50 / p99 [ms] | ~9,9 / ~11,1 stabilne | ~1,0 / ~1,25 stabilne | 10,205 / 11,491 stabilne | 1,066 / 1,283 stabilne |
| zdarzenia na zwolnieniu (na 540) | ~5-15 | ~5-15 | 13 | 13 |
| wszystkie zdarzenia: p99 | możliwe niestabilne | możliwe niestabilne | niestabilne | niestabilne |
| MW A > B (G) | p ≪ 0,01 | | 4,6e-174 | |
| nadmiar B nad pseudo B | | ~+0,1 ms, istotny | | +0,099 ms, p = 1,6e-70 |
| werdykt | POTWIERDZONY | | POTWIERDZONY | |

## Odstępstwa od protokołu i od przewidywania

1. **Protokół: bez odstępstw po starcie kampanii.** Aneks A1 (kolejność rozstrzygnięć werdyktu, nieważny przebieg nie przerywa kampanii, sprawdzenie ważności w `analyze.py`) zapisano przed suchym przebiegiem. Żaden warunek z A1 nie zadziałał: nie było nieważnych przebiegów ani nakładających się rozstrzygnięć.
2. **Cały worker jest ~4-5 % wolniejszy niż w R376, po obu stronach i także bez podłączeń.** G p50 jest wyższe niż w R376 o 3,4 % w A i 4,2 % w B, p99 o 3,9 % i 2,3 %. O tyle samo wzrosły jednak wielkości, w których podłączenia nie ma: pseudo-zdarzenia p50 0,964 / 0,967 ms wobec 0,918 / 0,920 ms (+5,0 %), `e2e_ns` slotów kontrolnych p50 0,138 ms wobec 0,131 ms (+5,3 %), `compute_ns` p50 0,077 wobec 0,074 ms, okno W p50 10,12 / 10,19 ms wobec 9,74 / 9,76 ms. Przesunięcie dotyczy więc platformy, a nie efektu: kontrola aparatury A-B jest w szumie, a skala efektu w A wynosi 9,24 wobec 8,95 ms w R376. Suchy przebieg pokazał to samo. Przyczyna jest nieustalona: worker restartowano od R376 co najmniej dwukrotnie (przed R603D i przed R607, rano 2026-11-07), a R376b biegło na tym samym uruchomieniu co R607. Wartości przewidywane na podstawie R376 są przez to w punktach p50/p99 G zaniżone o te kilka procent. Zwolnienie kolejki nie urosło (5,93 ms wobec 6,07 ms).
3. **Dwa długie `mmap` kolejki w B (2,73 ms i 0,56 ms, wobec p50 0,042 ms) wypadły w zdarzeniach na zwolnieniu** (`B_07` podłączenie 48 i `B_08` podłączenie 6). W tych chwilach wątek slotu wykonywał `munmap` kolejki wcześniejszego klienta. Wydłużają one okno W do 12,7 ms, ale nie slot (max `e2e_ns` tych zdarzeń 6,27 i 6,23 ms, czyli tyle, ile samo zwolnienie). To pasuje do rywalizacji o `mmap_lock` między `munmap` w wątku slotu a `mmap` w wątku komunikacyjnym, ale tego nie dowodzi. Te zdarzenia nie wchodzą do G z mocy reguły, nie z powodu tej obserwacji.

## Granice wniosków

- Jedna rodzina (uc05, takt 1/800 s, kolejka 8 MiB) i jedna platforma (pi400, Cortex-A72, jądro `PREEMPT_RT`, wątek slotu na izolowanym rdzeniu 3).
- Obie strony są sprzed #600. Wynik mówi o #283 w kodzie z tamtego czasu. Na obecnym `master` zwolnienie kolejki nie biegnie już w wątku slotu, więc zdarzeń na zwolnieniu w tej postaci tam nie ma. Tej rewizji R376b nie mierzyło.
- Wyłączenie zdarzeń na zwolnieniu usuwa z ogona jedno znane zjawisko. Nie dowodzi, że innych nie ma. W G nie widać jednak innego: max B 1,305 ms przy p99 1,283 ms.
- Przyczyny nadmiaru ~0,1 ms w B to badanie nie rozstrzyga (R376, *Ryzyko szczątkowe*).
- Przesunięcie platformy o ~4-5 % wobec R376 (*Odstępstwa*, punkt 2) jest wspólne dla obu stron i nie wpływa na werdykt. Uniemożliwia jednak porównanie wartości bezwzględnych R376b z R376 z dokładnością większą niż kilka procent.

## Skutek dla zgłoszenia (decyzja człowieka)

Według L4 werdykt POTWIERDZONY idzie do #376, a zgłoszenie zamyka człowiek. Komentarz wyniku w #376 zawiera opis badania i wyjaśnienie werdyktu, z samym identyfikatorem rodziny i liczbami wyprowadzonymi.

## Odtworzenie od zera

Wszystko na workerze `pi400` z katalogu `~/R376/apparatus_R376b` (kopia `campaign.sh` z tego katalogu, `run_one.py` z `results_20261104_R376/` i `streams.tsv` z `~/R376/apparatus`, ten ostatni tylko na workerze), poza analizą:

1. Korpus uc05 w `/dev/shm/r376/data/uc05` jak w R600 (`results_20261104_R600/wynik.md`, *Odtworzenie od zera*, punkt 3). Sprawdzenie: skrót SHA-256 drzewa (`find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum` w katalogu rodziny) równy `ce892219...` z README R603C (*Suchy przebieg*, punkt 2).
2. Binarki: `~/R376/bin/A` i `~/R376/bin/B` z R376 (`results_20261104_R376/build_ab.sh` z `P1_deadline_ns.patch`). `campaign.sh` sprawdza ich sumy.
3. Kampania: `cd ~/R376/apparatus_R376b; setsid nohup ./campaign.sh > ~/R376/campaign_R376b.log 2>&1 < /dev/null &` (~52 min). Do końca kampanii nie łączyć się z workerem. Przebieg nieważny jest raportowany i nie jest powtarzany (liczność ≥ 8 na stronę).
4. Analiza na hoście. Dane: `rsync -a <worker>:R376/raw_R376b/ <katalog>/raw/` albo archiwum rozpakowane do katalogu (`tar xzf results_20261107_R376b_raw.tar.gz -C <katalog>`, sprawdzone indeksem jak w README `rdb-experiment-embargo`). Potem z tego katalogu: Python ≥ 3.10 z NumPy (np. `retractordb/.venv-python/bin/python3`) `-I analyze.py --raw <katalog>/raw --out w.txt`. Skrypt importuje `../results_20261104_R376/analyze.py`. Część *Wydruk analizy* to ten wydruk bez pierwszego wiersza i z nagłówkami obniżonymi o jeden poziom: `sed 's/^#/##/' w.txt | tail -n +2` musi dać ją bajt w bajt. Sprawdzone 2026-11-07 na archiwum rozpakowanym od nowa: indeks zgodny, 108 plików, drzewo identyczne z danymi z workera, wydruk identyczny. Analiza trwa ~3 s.
5. Test analizy na danych R376: `analyze.py --raw <raw R376> --seed 376 --conns 30` (README, aneks A1).

## Wydruk analizy


Źródło: `raw`, bootstrap 2000 losowań, ziarno 3762, 60 podłączeń na przebieg.

### uc05

| wielkość [ms] | A | B |
|---|---|---|
| przebiegi / podłączenia / bez przypisania / klient bez wiersza lub zabity | 9 / 540 / 0 / 0 | 9 / 540 / 0 / 0 |
| okno W p50 / max | 10.119 / 10.669 | 10.191 / 12.707 |
| mmap kolejki p50 / max | 0.040 / 0.098 | 0.042 / 2.731 |
| zwolnienie kolejki: liczba / w wątku RT | 540 / 540 | 540 / 540 |
| zwolnienie kolejki (munmap+unlinkat) p50 / max | 5.926 / 6.523 | 5.913 / 6.625 |
| zwolnienie: max e2e slotu p50 / p99 / max | 6.208 / 15.568 / 17.328 | 6.170 / 7.222 / 7.388 |
| zdarzenie: n_hit | 540 | 540 |
| zdarzenie: p50 / max e2e | 10.231 / 17.328 | 1.068 / 7.388 |
| zdarzenie: p99 e2e [CI 95 %] | 15.568 [11.943, 16.406] NIESTABILNE | 6.401 [5.438, 6.875] NIESTABILNE |
| pseudo-zdarzenie (kontrola): liczba / p50 / p99 / max | 10800 / 0.964 / 1.126 / 1.298 | 10800 / 0.967 / 1.125 / 1.419 |
| slot z podłączeniem: liczba / p99 / max | 5599 / 11.758 / 17.328 | 5608 / 3.307 / 7.388 |
| kontrola e2e: p50 / p99 / max | 0.138 / 1.089 / 1.491 | 0.138 / 1.090 / 1.433 |
| kontrola compute: p50 / p99 / max | 0.077 / 1.027 / 1.337 | 0.077 / 1.029 / 1.306 |
| kontrola wake_lag: p50 / p99 / max | 0.024 / 0.135 / 0.559 | 0.024 / 0.136 / 0.499 |

- Mann-Whitney zdarzenia A > B: p = 2.64e-178; zdarzenia A > pseudo-zdarzenia A: p = 0; zdarzenia B > pseudo-zdarzenia B (ryzyko szczątkowe): p = 3.3e-76.
- Efekt #283 wg kryterium README: NIEPOTWIERDZONY.
- Ryzyko szczątkowe, wielkość: mediana zdarzeń B - mediana pseudo-zdarzeń B = 0.100 ms.
- Eksploracja po pomiarze (poza kryteriami), zdarzenia bez slotu w oknie zwolnienia: A: n = 527 (odrzucone 13), p50 / max 10.205 / 11.943, p99 11.491 [11.396, 11.526] stabilne; B: n = 527 (odrzucone 13), p50 / max 1.066 / 1.305, p99 1.283 [1.264, 1.296] stabilne; MW A > B p = 4.58e-174, B > pseudo B p = 1.57e-70.
- Kontrola aparatury, compute_ns p50 per przebieg: mediana A-B = 0.06 µs, rozrzut wewnątrz strony do 1.24 µs, permutacyjny MW p = 0.34 - w szumie.
- Kontrola aparatury, wake_lag_ns p99 per przebieg: mediana A-B = 1.55 µs, rozrzut wewnątrz strony do 33.37 µs, permutacyjny MW p = 0.863 - w szumie.

- Przebiegi nieważne (wyłączone, bez powtórzenia): brak.

#### Metryka główna G (bez zdarzeń na zwolnieniu)

| wielkość [ms] | A | B |
|---|---|---|
| zdarzenia z przypisanym slotem / na zwolnieniu (wyłączone) | 540 / 13 | 540 / 13 |
| G: n_hit | 527 | 527 |
| G: p50 / max | 10.205 / 11.943 | 1.066 / 1.305 |
| G: p99 [CI 95 %] | 11.491 [11.396, 11.526] stabilne | 1.283 [1.263, 1.296] stabilne |
| G: p50 - p50 pseudo-zdarzeń tej strony (skala efektu) | 9.241 | 0.099 |

- Mann-Whitney G A > B: p = 4.58e-174; G B > pseudo-zdarzenia B (ryzyko szczątkowe): p = 1.57e-70, mediana G B - mediana pseudo B = 0.099 ms.
- Kontrola aparatury (z wydruku R376 wyżej): compute_ns p50: w szumie; wake_lag_ns p99: w szumie.
- **Efekt #283 w uc05 według G: POTWIERDZONY** (p99 B < p99 A, MW p < 0.01).
- Odtwarzalność R376 (opisowo): G p99 A / B = 11.491 / 1.283 wobec 11.055 / 1.254; p50 wszystkich zdarzeń A / B = 10.231 / 1.068 wobec 9.873 / 1.024; nadmiar B (wszystkie zdarzenia) = 0.100 wobec 0.105 ms.

