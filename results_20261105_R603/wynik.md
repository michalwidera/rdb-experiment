# R603 - wynik

Badanie: resztka K2 po #600 (michalwidera/retractordb#603), protokół i kryteria w `README.md` (`fab5036`, przed pomiarem), mikrotest w `microtest/wynik.md` (`b1e673e`), suchy przebieg w README (`2b12660`).

Kampania 2026-11-05 08:31 - 09:29, pi400, uc05 i uc06, 9 par B/B' w kolejności ABBA, 30 podłączeń na przebieg: razem 36 przebiegów i 1080 podłączeń. Każdy przebieg był ważny: wątek slotu `SCHED_FIFO` na rdzeniu 3, `VmLck` > 0, governor `performance`, uruchomiona binarka równa zbudowanej, kolumny P2 bez -1 i bez multipleksowania (`run_one.py` i `analyze.py` przerywają przy każdym z tych warunków). Log kampanii kończy się `CAMPAIGN_COMPLETE`; kopia: `campaign.log`. Surowe dane (korpus pod embargiem) poza tym repozytorium, w prywatnym `paper-arXiv`, katalog `rdb-experiment-embargo/R603/`: `results_20261105_R603_raw.tar.gz` (93 698 387 B), SHA-256 `2e16d0f9ea5c97b9f9ee8caf7e03069208a37a8487978ca11f1b6dec89f8094c`; indeks 216 plików (36 przebiegów × 6 plików): `results_20261105_R603_raw.index.tsv`. Analiza: `analyze.py --raw <raw> --seed 603`; pełny wydruk niżej, w części *Wydruk analizy*.

## Odpowiedź

**Unieważnienie TLB całego ASID (H-a) działa w silniku i znika przy zwalnianiu w kawałkach 1 MiB, ale nie jest głównym składnikiem resztki: B' zmniejsza różnicę median o 46 % w uc05 i 27 % w uc06, a nie o połowę, której wymaga C2. H-a jest więc według kryterium NIEWSPARTA w obu rodzinach. Resztka po B' istnieje (K2 na B' niezdane) i towarzyszy jej nadwyżka chybień L2 w obu stronach, co jest zgodne z H-b.**

| rodzina | C0 (B, K2 R600) | C1 (B' w kawałkach) | Δ_e2e B → B' | C2 (H-a) | C3 (resztka po B') | C4: u_a / u_r (95 % bootstrap u_r) | K2 R600 dla B' |
|---|---|---|---|---|---|---|---|
| uc05 | spełniona, n = 270, p = 2,2e-04 | 270 z 270 (9 `munmap`) | 55,76 → 29,84 µs | **NIEWSPARTA** | istnieje, p = 5,6e-05; L2R p = 8,9e-105: zgodna z H-b | 0,46 / 0,54 (0,15..3,30) | NIEZDANE |
| uc06 | spełniona, n = 270, p = 2,8e-16 | 270 z 270 (6 `munmap`) | 48,40 → 35,56 µs | **NIEWSPARTA** | istnieje, p = 8,1e-09; L2R p = 1,1e-50: zgodna z H-b | 0,27 / 0,73 (0,42..1,29) | NIEZDANE |

- **Mechanizm H-a jest obecny w silniku i B' go usuwa.** Licznik, który w mikroteście niósł sygnaturę przejść tablic stron po unieważnieniu ASID, czyli dostępy do L2 w odcinku pobudki (Δ `wake_l2d_cache`), wynosi w B +123 (uc05) i +128 (uc06) przy p ≤ 3e-47, a w B' -37 i -16 (p ≈ 1). W uc05 dochodzi Δ `wake_l1i_tlb_refill` +2 w B (p = 3,5e-05) wobec +1 w B' (p = 0,20). Stąd C1 i ten wynik razem: kawałkowanie robi dokładnie to, co miało zrobić.
- **Usunięcie mechanizmu H-a zmniejsza resztkę za mało, żeby przesądzić o naprawie.** u_a = 0,46 i 0,27 to oszacowania punktowe. Przedział bootstrap u_r jest szeroki: w uc06 obejmuje 1 (0,42..1,29), więc nie wyklucza, że B' nie zmienia niczego; w uc05 też sięga powyżej 1 (0,15..3,30). Mediana max `e2e_ns` z okien jest miarą zaszumioną; wynik mówi, że udział H-a jest najwyżej umiarkowany, a nie, ile dokładnie wynosi.
- **Resztka po B' wiąże się z chybieniami L2.** Δ `l2d_cache_refill` (L2R) w slotach okna wynosi +1970 / +2065 (uc05, B / B') i +1901 / +1656 (uc06), a w samym odcinku pobudki +285 / +266 i +183 / +210, wszystkie przy p ≤ 1e-44. Nadwyżka jest praktycznie taka sama w B i B', czyli niezależna od tego, czy TLB jest unieważniane. Mikrotest pokazał to samo bez silnika: część nadwyżki czasu powstaje także w fazie `shm_unlink`, w której nie ma żadnego `munmap` (`microtest/wynik.md`, *Eksploracja*).
- **Miara T (`l1d_tlb_refill` + `l1i_tlb_refill`) nic nie rozstrzyga**, jak przewidział wynik mikrotestu: Δ_T jest ujemne w obu stronach i obu rodzinach (MW p = 1). Tło `l1d_tlb_refill` z jądra i duży zbiór roboczy silnika zasłaniają efekt. C2 rozstrzyga warunek na `e2e`, więc zmiana miary T, o której decyzję prosi `microtest/wynik.md`, nie zmieniłaby werdyktu „niewsparta”.
- **Znaczenie dla czasu rzeczywistego (uc05, takt 1,000 ms).** Okno zwolnienia zawiera slot dłuższy od taktu w 30,4 % przypadków w B i 33,0 % w B', a pseudo-okno w 17,5 % i 22,8 %. B' nie poprawia tej miary. W uc06 miara nic nie rozstrzyga, bo rodzina ma okresowy slot ~45 ms, który przekracza takt także w slotach kontrolnych (jak w R600).

## Odchylenia od przewidywania i od R600

1. **Przewidywanie z mikrotestu sprawdziło się** (`microtest/wynik.md`, *Skutek dla części II*, zapisane przed kampanią): u_a wyraźnie poniżej 1, C2 niewsparta, resztka po B' istnieje.
2. **Koszt aparatury P2.** Dwa odczyty grupy PMU na slot i liczniki per wątek (przełączanie stanu PMU przy wywłaszczeniu) podnoszą czasy slotu. W uc05 mediana `e2e_ns` slotów kontrolnych wynosi 0,143 ms wobec 0,121 ms w R600 (strona B, ta sama rewizja bez P2), a `wake_lag_ns` 0,029 wobec 0,023 ms. W uc06 `e2e_ns` 0,327 wobec 0,291 ms. Δ_e2e B w uc05 jest prawie dwa razy większe niż w R600 (55,76 wobec 30 µs), w uc06 zbliżone (48,40 wobec 43 µs). **Liczby bezwzględne tej kampanii nie są więc wprost porównywalne z R600.** Porównanie B z B' jest ważne, bo obie strony mają P2 w tej samej postaci.
3. **Długość okna zwolnienia** w B' jest nieco większa niż w B: p50 6,84 wobec 6,55 ms (uc05) i 4,36 wobec 4,16 ms (uc06). Pseudo-okna mają tę samą długość co okna, więc porównanie Δ to uwzględnia.

## Granice wniosków

- Jedna platforma: Cortex-A72 bez TLBI na zakresach, wspólne L2 1 MiB, jądro 6.8 `PREEMPT_RT` z KPTI wymuszonym przez KASLR. Na procesorze z TLBI na zakresach albo z prywatnym L2 udziały mogą wyglądać inaczej. Udziału KPTI (wpisy jądra tracone razem z ASID) nie mierzono osobno; wymagałoby to `nokaslr`, czyli zmiany platformy.
- „Zgodna z H-b” znaczy, że resztce towarzyszy nadwyżka chybień L2, a nie, że chybienia L2 są jej jedyną przyczyną. Mikrotest sugeruje, że wydłużenie bywa większe, niż tłumaczy sama liczba chybień, czyli możliwy jest też wzrost opóźnienia każdego chybienia przy zajętej magistrali pamięci. Liczniki zdarzeń A72 tego nie odróżnią.
- B' nie wstrzymuje się między kawałkami. Nie wiadomo, czy rozłożenie zwolnienia w czasie zmniejszyłoby udział H-b.

## Skutek dla naprawy (do decyzji człowieka)

Wynik wyklucza samo zwalnianie w kawałkach jako naprawę, która da K2 zdane: B' ma K2 niezdane w obu rodzinach, a większa część resztki nie zależy od unieważnienia TLB. Kandydaci z planu w świetle wyniku:

1. **Ponowne użycie segmentów kolejek zamiast `munmap` i `unlinkat` w trakcie pracy.** Jako jedyna usuwa oba mechanizmy, bo w czasie pracy nie zwalnia ani stron, ani mapowania (przy okazji odpada też koszt `fallocate` przy podłączeniu). Zmienia rdzeń współbieżny (`ipcServer.cpp`), wymaga ograniczonej puli (magazyny nie mogą rosnąć bez końca) i decyzji, jak nazwa kolejki ma się do segmentu.
2. **Mniejszy zapas kolejki** (dziś 10 s, `maxElements = 10 s / takt`). Zmniejsza oba efekty proporcjonalnie do liczby stron, ale zmienia zachowanie wolnego klienta (wcześniejsze porzucenie kolejki). To decyzja semantyczna, nie tylko wydajnościowa.
3. **Zwalnianie w kawałkach z przerwami** (także `ftruncate` w krokach przed `unlinkat`). Tanie i możliwe do zmierzenia tą samą aparaturą (strona B''), ale rozkłada ten sam ruch pamięci na więcej slotów. K2 pyta o istnienie różnicy, więc prawdopodobnie nadal byłoby niezdane, tylko przy mniejszym efekcie na slot.
4. **Udokumentowana granica platformy.** Przy wspólnym L2 każde zwalnianie ~2000 stron w procesie wpływa na rdzeń izolowany; resztka (dziesiątki µs przy takcie 1-2 ms) zostaje opisana jako znana właściwość pi400.

## Odtworzenie od zera

Wszystko na workerze `pi400` z katalogu `~/R376/apparatus_R603` (kopia tego katalogu), poza analizą:

1. Korpus uc05 i uc06 jak w R600 (`results_20261104_R600/wynik.md`, *Odtworzenie od zera*, punkt 3): generator z prywatnego `paper-arXiv` przez wejście standardowe ssh do `/dev/shm/r376/data/<rodzina>`, plan przez `cat`; `streams.tsv` z `~/R376/apparatus_R600` (tylko na workerze).
2. Budowa: `setsid nohup ./build_ab.sh > ~/R376/build_R603.log 2>&1 < /dev/null &` (drzewo `~/R376/src`, pinezka `221d312b`, łatki P1+P2 i P1+P2+P3; ~10 min przyrostowo po R600, pełna budowa ~1 h).
3. Kampania: `setsid nohup ./campaign.sh > ~/R376/campaign_R603.log 2>&1 < /dev/null &` (~1 h; governor ustawia skrypt).
4. Analiza na hoście: `rsync -a pi400:R376/raw_R603/ <katalog>/raw/`, potem `retractordb/.venv-python/bin/python3 -I analyze.py --raw <katalog>/raw --seed 603`.
5. Mikrotest: `microtest/wynik.md` (bez korpusu, ~2 min).

## Wydruk analizy


### uc05

Takt slotu (mediana odstępu deadline_ns): 1.000 ms.

| wielkość | B | B' |
|---|---|---|
| przebiegi / zwolnienia / w wątku RT / podłączenia bez zwolnienia | 9 / 270 / 0 / 0 | 9 / 270 / 0 / 0 |
| munmap na zwolnienie: min / p50 / max | 1 / 1 / 1 | 9 / 9 / 9 |
| zwolnienie (okno R) [ms] p50 / max | 6.549 / 8.503 | 6.836 / 7.578 |
| zwolnienia trafione w slot: n / odsetek | 270 / 100.0 % | 270 / 100.0 % |
| zdarzenie: max e2e [ms] p50 / p99 / max | 0.867 / 1.481 / 1.607 | 0.907 / 1.392 / 1.492 |
| pseudo-zdarzenie: liczba / max e2e [ms] p50 / p99 / max | 5400 / 0.811 / 1.179 / 1.620 | 5400 / 0.877 / 1.383 / 2.052 |
| okna z max e2e > takt: zdarzenia / pseudo | 30.4 % / 17.5 % | 33.0 % / 22.8 % |
| Δ_e2e [µs]; MW p | 55.76; 0.00022 | 29.84; 5.59e-05 |
| Δ_T (l1d+l1i TLB refill); MW p | -319.00; 1 | -970.00; 1 |
| Δ_L2A (l2d_cache); MW p | -930.00; 0.564 | -3056.00; 0.998 |
| Δ_L2R (l2d_cache_refill); MW p | 1970.00; 4.52e-111 | 2065.00; 8.93e-105 |
| Δ wake_l1i_tlb_refill (opisowo); MW p | 2.00; 3.45e-05 | 1.00; 0.195 |
| Δ wake_l2d_cache (opisowo); MW p | 123.00; 2.05e-50 | -37.00; 1 |
| Δ wake_l2d_cache_refill (opisowo); MW p | 285.00; 7.3e-123 | 266.00; 1.02e-122 |
| sloty obudzone w zwolnieniu: wake_lag / compute p50 [µs] (mediana po zdarzeniach) | 34.5 / 78.6 | 33.8 / 80.1 |
| kontrola e2e [ms] p50 / p99 / max | 0.143 / 1.104 / 2.039 | 0.142 / 1.121 / 4.378 |
| kontrola compute [ms] p50 / p99 / max | 0.067 / 1.018 / 1.822 | 0.067 / 1.033 / 3.601 |
| kontrola wake [ms] p50 / p99 / max | 0.029 / 0.187 / 1.165 | 0.029 / 0.204 / 3.555 |

- **C0** kontrola dodatnia (K2 R600 na B): n = 270, p = 0.00022 - spełniona.
- **C1** B' zwalnia w kawałkach: 270 z 270 zwolnień ma ≥ ⌈mapowanie / 1 MiB⌉ munmap, w wątku RT 0 - spełnione.
- **C2** H-a: Δ_e2e B = 55.76 µs, B' = 29.84 µs (warunek B' ≤ 0,5 · B: nie); Δ_T B = -319.0 (MW p = 1), B' = -970.0 - NIEWSPARTA.
- **C3** resztka po B': K2 na B' p = 5.59e-05 (n = 270) - istnieje; L2R zdarzeń > pseudo w B' (MW p = 8.93e-105): zgodna z H-b.
- **C4** udział: u_a = 0.46, u_r = 0.54 (95 % bootstrap u_r: 0.15..3.30); K2 R600 dla B': NIEZDANE.

### uc06

Takt slotu (mediana odstępu deadline_ns): 2.000 ms.

| wielkość | B | B' |
|---|---|---|
| przebiegi / zwolnienia / w wątku RT / podłączenia bez zwolnienia | 9 / 270 / 0 / 0 | 9 / 270 / 0 / 0 |
| munmap na zwolnienie: min / p50 / max | 1 / 1 / 1 | 6 / 6 / 6 |
| zwolnienie (okno R) [ms] p50 / max | 4.163 / 4.835 | 4.355 / 5.333 |
| zwolnienia trafione w slot: n / odsetek | 270 / 100.0 % | 270 / 100.0 % |
| zdarzenie: max e2e [ms] p50 / p99 / max | 0.462 / 47.968 / 48.185 | 0.449 / 48.515 / 48.845 |
| pseudo-zdarzenie: liczba / max e2e [ms] p50 / p99 / max | 5400 / 0.414 / 48.212 / 49.764 | 5400 / 0.414 / 48.951 / 50.598 |
| okna z max e2e > takt: zdarzenia / pseudo | 8.9 % / 24.3 % | 9.6 % / 25.2 % |
| Δ_e2e [µs]; MW p | 48.40; 2.81e-16 | 35.56; 8.07e-09 |
| Δ_T (l1d+l1i TLB refill); MW p | -557.00; 1 | -588.00; 1 |
| Δ_L2A (l2d_cache); MW p | -1671.00; 0.0177 | -2648.00; 0.999 |
| Δ_L2R (l2d_cache_refill); MW p | 1901.00; 5.36e-52 | 1656.00; 1.13e-50 |
| Δ wake_l1i_tlb_refill (opisowo); MW p | 0.00; 0.611 | 0.00; 0.401 |
| Δ wake_l2d_cache (opisowo); MW p | 128.00; 2.64e-47 | -16.00; 0.992 |
| Δ wake_l2d_cache_refill (opisowo); MW p | 183.00; 1.82e-44 | 210.00; 8.04e-45 |
| sloty obudzone w zwolnieniu: wake_lag / compute p50 [µs] (mediana po zdarzeniach) | 37.5 / 291.9 | 36.3 / 282.6 |
| kontrola e2e [ms] p50 / p99 / max | 0.327 / 46.373 / 49.764 | 0.325 / 47.004 / 50.598 |
| kontrola compute [ms] p50 / p99 / max | 0.238 / 0.478 / 49.566 | 0.236 / 0.472 / 50.419 |
| kontrola wake [ms] p50 / p99 / max | 0.030 / 44.451 / 47.896 | 0.029 / 45.072 / 48.709 |

- **C0** kontrola dodatnia (K2 R600 na B): n = 270, p = 2.81e-16 - spełniona.
- **C1** B' zwalnia w kawałkach: 270 z 270 zwolnień ma ≥ ⌈mapowanie / 1 MiB⌉ munmap, w wątku RT 0 - spełnione.
- **C2** H-a: Δ_e2e B = 48.40 µs, B' = 35.56 µs (warunek B' ≤ 0,5 · B: nie); Δ_T B = -557.0 (MW p = 1), B' = -588.0 - NIEWSPARTA.
- **C3** resztka po B': K2 na B' p = 8.07e-09 (n = 270) - istnieje; L2R zdarzeń > pseudo w B' (MW p = 1.13e-50): zgodna z H-b.
- **C4** udział: u_a = 0.27, u_r = 0.73 (95 % bootstrap u_r: 0.42..1.29); K2 R600 dla B': NIEZDANE.

