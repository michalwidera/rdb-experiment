# R376 - wynik kampanii

Kampania 2026-11-04 15:12-18:31, pi400, uc03-uc08, 9 par A/B w kolejności ABBA, 30 podłączeń na przebieg: razem 108 przebiegów i 3240 podłączeń. Każdy przebieg był ważny: wątek slotu `SCHED_FIFO` na rdzeniu 3, `VmLck` > 0, governor `performance`. Żadna binarka nie różniła się od zbudowanej. Każdy klient dostał wiersz. Surowe dane leżą poza git: `results_20261104_R376_raw.tar.gz`, SHA-256 `1dafcb7ab809f30761c14a550a6802852479a8a51e9e33086c1d706da461d1be`. Indeks plików jest w `results_20261104_R376_raw.index.tsv`, a przebieg kampanii w `campaign.log`. Analiza: `analyze.py --raw <raw> --seed 376`; jej pełny wydruk jest niżej, w części *Wydruk analizy*.

## Odpowiedź

**Efekt #283 według kryterium ustalonego przed pomiarem:**

| rodzina | zdarzenie A p50 / p99 [ms] | zdarzenie B p50 / p99 [ms] | pseudo-zdarzenie B p50 [ms] | MW A > B | werdykt |
|---|---|---|---|---|---|
| uc03 | 1,910 / 5,643 | 0,324 / 3,018 | 0,212 | 1,1e-44 | **POTWIERDZONY** |
| uc05 | 9,873 / 15,403 (niestabilne) | 1,024 / 6,890 (niestabilne) | 0,920 | 3,3e-90 | NIEPOTWIERDZONY: p99 niestabilne |
| uc06 | 6,132 / 56,640 | 0,531 / 47,551 | 0,485 | 1,2e-35 | **POTWIERDZONY** |
| uc04 | 0 trafień | 0 trafień | - | - | nie do oceny |
| uc07 | n = 9, max 1,156 | n = 10, max 0,439 | 0,133 | 4,7e-4 | n_hit < 100: tylko max i liczność |
| uc08 | n = 1, max 1,425 | n = 1, max 0,055 | 0,395 | - | n_hit < 100: tylko max i liczność |

- **uc05.** Mediany różnią się prawie dziesięciokrotnie, mimo to p99 obu stron nie spełnia kryterium stabilności. Przyczyną są nieliczne zdarzenia, których sloty trafiły na okno zwolnienia kolejki: zwolnienie trwa ~6 ms i biegnie w wątku slotu (metryka 5 niżej). Takich zdarzeń jest 3 w A i 6 w B. Po ich odrzuceniu p99 jest stabilne: A 11,055 [10,880, 11,312] ms, B 1,254 [1,211, 1,434] ms, MW 9,8e-89. To jest **eksploracja po pomiarze**, poza kryteriami, i werdyktu nie zmienia. README nie pozwala dokładać przebiegów bez decyzji człowieka; czy tę eksplorację przyjąć, rozstrzyga człowiek.
- **uc06.** Rodzina ma własne przestoje ~47 ms, także bez podłączeń: pseudo-zdarzenia mają p99 48 ms. Dlatego p99 mierzy głównie te przestoje, a efekt podłączenia lepiej widać w p50.
- **uc04.** Takt wynosi 5 s, okno W ~0,4 ms, a klient czeka na pierwszy wiersz do 5 s. Żaden slot nie trafił w okno i nie został żaden slot kontrolny. W tej aparaturze rodzina jest niemierzalna.
- **Skala efektu.** W A podłączenie dokłada do slotu (p50 zdarzenia minus p50 pseudo-zdarzenia) 1,70 ms w uc03, 8,95 ms w uc05 i 5,65 ms w uc06. W B dokłada 0,11, 0,10 i 0,05 ms. #283 usuwa więc z wątku slotu 93-99 % kosztu budowy kolejki.

**Ryzyko szczątkowe (`mmap_lock` lub inny wspólny zasób).** W B zdarzenia przewyższają pseudo-zdarzenia tej samej strony istotnie (p < 0,01) w uc03, uc05, uc06 i uc07. Nadmiar liczony różnicą median:

| rodzina | kolejka | okno W p50 | `mmap` p50 / max | nadmiar w B | MW B > pseudo B |
|---|---|---|---|---|---|
| uc03 | 2 MiB | 2,68 ms | 0,031 / 0,531 ms | +0,112 ms | 4,1e-37 |
| uc05 | 8 MiB | 9,76 ms | 0,041 / 0,084 ms | +0,105 ms | 3,6e-50 |
| uc06 | 5 MiB | 6,23 ms | 0,038 / 0,152 ms | +0,046 ms | 2,9e-07 |
| uc07 | 0,5 MiB | 0,90 ms | 0,026 / 0,079 ms | +0,080 ms (n = 10) | 1,0e-03 |

W B wątek slotu nadal płaci za podłączenie, choć 15-120 razy mniej niż w A. Nadmiar nie rośnie z rozmiarem kolejki, czyli z ilością pracy `fallocate` na rdzeniach 0-2. To pasuje do kosztu stałego na podłączenie, a nie do rywalizacji o pasmo pamięci przy zerowaniu stron. Mediana nadmiaru jest przy tym 1,2-3,6 razy większa niż mediana czasu `mmap`, w którym wątek komunikacyjny trzyma `mmap_lock` do zapisu. Samo `mmap_lock` przy `mmap` kolejki nie wyjaśnia więc całości. Kandydaci: `mmap_lock` (także przy `fallocate`/`ftruncate` segmentu), `clientMapsMutex_` przy rejestracji klienta w `subscribe()` i odczyt w `broadcast()`. Rozstrzygnięcie wymaga śledzenia blokad w jądrze (`lock:contention_begin`) albo pomiaru z wyłączoną rejestracją. Wynik wskazuje kandydatów, nie dowodzi przyczyny.

**Kontrola aparatury.** Różnice A-B `compute_ns` p50 i `wake_lag_ns` p99 per przebieg mieszczą się w rozrzucie wewnątrz strony we wszystkich ocenialnych rodzinach (uc04: brak slotów kontrolnych). Jedna uwaga: w uc06 `wake_lag_ns` p99 różni się o 0,27 ms przy rozrzucie 0,57 ms. Kryterium jest więc spełnione, ale test permutacyjny daje p = 0,0078. To odpowiada własnym przestojom rodziny z punktu 3 suchego przebiegu.

**Zwolnienie kolejki (metryka 5, #600).** Kolejkę zwalnia wątek slotu w 270 z 270 podłączeń w każdej rodzinie z uc03 i uc05-uc08, w A i w B. W uc04 nie było żadnego zwolnienia: kolejka ma 0,1 MiB, czyli tyle co w uc08 przy takcie 50 razy dłuższym, i zapełnia się po ~500 s, później niż kończy się przebieg.

| rodzina | takt | kolejka | `munmap`+`unlinkat` p50 / max (A; B) | max `e2e_ns` slotu w oknie zwolnienia p50 / max (A; B) | kontrola `e2e_ns` p50 / p99 (B) |
|---|---|---|---|---|---|
| uc03 | 1/200 s | 2 MiB | 1,63 / 1,90; 1,63 / 1,76 ms | 1,87 / 4,69; 1,88 / 4,95 ms | 0,21 / 2,84 ms |
| uc05 | 1/800 s | 8 MiB | 6,07 / 6,62; 6,07 / 6,68 ms | 6,98 / 16,87; 6,92 / 7,73 ms | 0,13 / 1,04 ms |
| uc06 | 1/500 s | 5 MiB | 3,82 / 4,15; 3,80 / 4,30 ms | 4,25 / 57,23; 4,22 / 51,69 ms | 0,34 / 45,93 ms |
| uc07 | 1/50 s | 0,5 MiB | 0,52 / 0,59; 0,52 / 0,56 ms | 0,67 / 3,15; 0,67 / 2,96 ms | 0,13 / 2,29 ms |
| uc08 | 1/10 s | 0,1 MiB | 0,25 / 0,29; 0,25 / 0,29 ms | 0,65 / 1,81; 0,65 / 1,74 ms | 0,38 / 1,36 ms |

Koszt zwolnienia rośnie z rozmiarem kolejki: w uc03-uc06 ~0,8 ms na MiB, w małych kolejkach (uc07, uc08) przeważa koszt stały. W A max 16,9 ms w uc05 to zwolnienie, które trafiło na okno W podłączenia.

## Zmiany w `analyze.py` po pomiarze

Żadna z nich nie zmienia wielkości objętych kryteriami: poprzedni i obecny wydruk różnią się tylko liniami wymienionymi niżej.

1. Licznik „klient bez wiersza lub zabity” uznawał za błąd każdy kod różny od -2. Poniżej ~1 kHz `xqry -m 1` zwykle kończy się sam (kod 0), zanim dojdzie do niego SIGINT. Teraz za błąd uchodzi tylko `no_row` i `killed`, i wychodzi 0 z 3240.
2. W rodzinie bez slotów kontrolnych (uc04) kontrola aparatury pisała `nan` i „POZA SZUMEM”. Teraz pisze „nie do oceny”.
3. Dopisana wielkość ryzyka szczątkowego, czyli różnica median, którą kryteria README każą raportować, a której wydruk nie zawierał.
4. Dopisana eksploracja po pomiarze: zdarzenia bez slotu w oknie zwolnienia. Bootstrap tej eksploracji ma osobny generator, żeby nie przesuwać losowań kryteriów.

## Wydruk analizy

## uc03

| wielkość [ms] | A | B |
|---|---|---|
| przebiegi / podłączenia / bez przypisania / klient bez wiersza lub zabity | 9 / 270 / 0 / 0 | 9 / 270 / 0 / 0 |
| okno W p50 / max | 2.678 / 3.115 | 2.679 / 3.208 |
| mmap kolejki p50 / max | 0.029 / 0.181 | 0.031 / 0.531 |
| zwolnienie kolejki: liczba / w wątku RT | 270 / 270 | 270 / 270 |
| zwolnienie kolejki (munmap+unlinkat) p50 / max | 1.628 / 1.899 | 1.631 / 1.764 |
| zwolnienie: max e2e slotu p50 / p99 / max | 1.872 / 4.601 / 4.692 | 1.878 / 4.643 / 4.948 |
| zdarzenie: n_hit | 186 | 160 |
| zdarzenie: p50 / max e2e | 1.910 / 5.785 | 0.324 / 3.043 |
| zdarzenie: p99 e2e [CI 95 %] | 5.643 [5.101, 5.785] stabilne | 3.018 [3.007, 3.043] stabilne |
| pseudo-zdarzenie (kontrola): liczba / p50 / p99 / max | 5400 / 0.211 / 2.928 / 3.544 | 5400 / 0.212 / 2.897 / 3.205 |
| slot z podłączeniem: liczba / p99 / max | 186 / 5.643 / 5.785 | 160 / 3.018 / 3.043 |
| kontrola e2e: p50 / p99 / max | 0.209 / 2.863 / 3.787 | 0.210 / 2.840 / 3.642 |
| kontrola compute: p50 / p99 / max | 0.156 / 2.804 / 3.634 | 0.156 / 2.773 / 3.485 |
| kontrola wake_lag: p50 / p99 / max | 0.023 / 0.027 / 0.106 | 0.023 / 0.025 / 0.076 |

- Mann-Whitney zdarzenia A > B: p = 1.07e-44; zdarzenia A > pseudo-zdarzenia A: p = 1.04e-54; zdarzenia B > pseudo-zdarzenia B (ryzyko szczątkowe): p = 4.09e-37.
- Efekt #283 wg kryterium README: POTWIERDZONY.
- Ryzyko szczątkowe, wielkość: mediana zdarzeń B - mediana pseudo-zdarzeń B = 0.112 ms.
- Eksploracja po pomiarze (poza kryteriami), zdarzenia bez slotu w oknie zwolnienia: A: n = 186 (odrzucone 0), p50 / max 1.910 / 5.785, p99 5.643 [5.101, 5.785] stabilne; B: n = 159 (odrzucone 1), p50 / max 0.324 / 3.043, p99 3.018 [3.007, 3.043] stabilne; MW A > B p = 4.26e-45, B > pseudo B p = 6.41e-37.
- Kontrola aparatury, compute_ns p50 per przebieg: mediana A-B = -0.33 µs, rozrzut wewnątrz strony do 2.48 µs, permutacyjny MW p = 0.589 - w szumie.
- Kontrola aparatury, wake_lag_ns p99 per przebieg: mediana A-B = 0.15 µs, rozrzut wewnątrz strony do 21.01 µs, permutacyjny MW p = 0.34 - w szumie.

## uc04

| wielkość [ms] | A | B |
|---|---|---|
| przebiegi / podłączenia / bez przypisania / klient bez wiersza lub zabity | 9 / 270 / 0 / 0 | 9 / 270 / 0 / 0 |
| okno W p50 / max | 0.393 / 0.487 | 0.387 / 0.480 |
| mmap kolejki p50 / max | 0.027 / 0.087 | 0.028 / 0.095 |
| zwolnienie kolejki: liczba / w wątku RT | 0 / 0 | 0 / 0 |
| zwolnienie kolejki (munmap+unlinkat) p50 / max | - / - | - / - |
| zwolnienie: max e2e slotu p50 / p99 / max | - / - / - | - / - / - |
| zdarzenie: n_hit | 0 | 0 |
| zdarzenie: p50 / max e2e | - / - | - / - |
| zdarzenie: p99 e2e [CI 95 %] | n_hit < 100 | n_hit < 100 |
| pseudo-zdarzenie (kontrola): liczba / p50 / p99 / max | 0 / - / - / - | 0 / - / - / - |
| slot z podłączeniem: liczba / p99 / max | 0 / - / - | 0 / - / - |
| kontrola e2e: p50 / p99 / max | - / - / - | - / - / - |
| kontrola compute: p50 / p99 / max | - / - / - | - / - / - |
| kontrola wake_lag: p50 / p99 / max | - / - / - | - / - / - |

- Mann-Whitney zdarzenia A > B: p = nan; zdarzenia A > pseudo-zdarzenia A: p = nan; zdarzenia B > pseudo-zdarzenia B (ryzyko szczątkowe): p = nan.
- Efekt #283 wg kryterium README: NIEPOTWIERDZONY (p99 nieraportowane przy n_hit < 100).
- Eksploracja po pomiarze (poza kryteriami), zdarzenia bez slotu w oknie zwolnienia: A: n = 0 (odrzucone 0), p50 / max - / -; B: n = 0 (odrzucone 0), p50 / max - / -; MW A > B p = nan, B > pseudo B p = nan.
- Kontrola aparatury, compute_ns p50 per przebieg: brak slotów kontrolnych - nie do oceny.
- Kontrola aparatury, wake_lag_ns p99 per przebieg: brak slotów kontrolnych - nie do oceny.

## uc05

| wielkość [ms] | A | B |
|---|---|---|
| przebiegi / podłączenia / bez przypisania / klient bez wiersza lub zabity | 9 / 270 / 0 / 0 | 9 / 270 / 0 / 0 |
| okno W p50 / max | 9.739 / 10.889 | 9.756 / 10.602 |
| mmap kolejki p50 / max | 0.037 / 0.090 | 0.041 / 0.084 |
| zwolnienie kolejki: liczba / w wątku RT | 270 / 270 | 270 / 270 |
| zwolnienie kolejki (munmap+unlinkat) p50 / max | 6.071 / 6.624 | 6.068 / 6.684 |
| zwolnienie: max e2e slotu p50 / p99 / max | 6.984 / 15.403 / 16.867 | 6.920 / 7.602 / 7.726 |
| zdarzenie: n_hit | 270 | 270 |
| zdarzenie: p50 / max e2e | 9.873 / 16.867 | 1.024 / 7.409 |
| zdarzenie: p99 e2e [CI 95 %] | 15.403 [11.027, 16.867] NIESTABILNE | 6.890 [1.265, 7.409] NIESTABILNE |
| pseudo-zdarzenie (kontrola): liczba / p50 / p99 / max | 5400 / 0.918 / 1.086 / 1.519 | 5400 / 0.920 / 1.096 / 1.793 |
| slot z podłączeniem: liczba / p99 / max | 2688 / 10.899 / 16.867 | 2706 / 3.258 / 7.409 |
| kontrola e2e: p50 / p99 / max | 0.131 / 1.041 / 1.854 | 0.132 / 1.041 / 1.838 |
| kontrola compute: p50 / p99 / max | 0.074 / 0.981 / 1.611 | 0.074 / 0.981 / 1.696 |
| kontrola wake_lag: p50 / p99 / max | 0.023 / 0.091 / 0.952 | 0.023 / 0.092 / 0.924 |

- Mann-Whitney zdarzenia A > B: p = 3.29e-90; zdarzenia A > pseudo-zdarzenia A: p = 4.71e-170; zdarzenia B > pseudo-zdarzenia B (ryzyko szczątkowe): p = 3.61e-50.
- Efekt #283 wg kryterium README: NIEPOTWIERDZONY.
- Ryzyko szczątkowe, wielkość: mediana zdarzeń B - mediana pseudo-zdarzeń B = 0.105 ms.
- Eksploracja po pomiarze (poza kryteriami), zdarzenia bez slotu w oknie zwolnienia: A: n = 267 (odrzucone 3), p50 / max 9.871 / 11.312, p99 11.055 [10.880, 11.312] stabilne; B: n = 264 (odrzucone 6), p50 / max 1.023 / 1.434, p99 1.254 [1.211, 1.434] stabilne; MW A > B p = 9.75e-89, B > pseudo B p = 2.63e-47.
- Kontrola aparatury, compute_ns p50 per przebieg: mediana A-B = -0.02 µs, rozrzut wewnątrz strony do 1.46 µs, permutacyjny MW p = 0.931 - w szumie.
- Kontrola aparatury, wake_lag_ns p99 per przebieg: mediana A-B = -0.05 µs, rozrzut wewnątrz strony do 25.65 µs, permutacyjny MW p = 0.605 - w szumie.

## uc06

| wielkość [ms] | A | B |
|---|---|---|
| przebiegi / podłączenia / bez przypisania / klient bez wiersza lub zabity | 9 / 270 / 0 / 0 | 9 / 270 / 0 / 0 |
| okno W p50 / max | 6.233 / 7.021 | 6.234 / 6.804 |
| mmap kolejki p50 / max | 0.035 / 0.073 | 0.038 / 0.152 |
| zwolnienie kolejki: liczba / w wątku RT | 270 / 270 | 270 / 270 |
| zwolnienie kolejki (munmap+unlinkat) p50 / max | 3.820 / 4.153 | 3.804 / 4.304 |
| zwolnienie: max e2e slotu p50 / p99 / max | 4.245 / 56.640 / 57.226 | 4.220 / 51.522 / 51.686 |
| zdarzenie: n_hit | 270 | 270 |
| zdarzenie: p50 / max e2e | 6.132 / 57.226 | 0.531 / 47.855 |
| zdarzenie: p99 e2e [CI 95 %] | 56.640 [53.210, 57.226] stabilne | 47.551 [47.379, 47.855] stabilne |
| pseudo-zdarzenie (kontrola): liczba / p50 / p99 / max | 5400 / 0.482 / 48.023 / 49.928 | 5400 / 0.485 / 47.658 / 49.325 |
| slot z podłączeniem: liczba / p99 / max | 2350 / 52.963 / 57.226 | 2136 / 46.296 / 47.855 |
| kontrola e2e: p50 / p99 / max | 0.335 / 46.135 / 50.813 | 0.335 / 45.927 / 49.325 |
| kontrola compute: p50 / p99 / max | 0.263 / 0.544 / 50.608 | 0.264 / 0.459 / 49.168 |
| kontrola wake_lag: p50 / p99 / max | 0.023 / 44.179 / 48.891 | 0.023 / 43.973 / 47.397 |

- Mann-Whitney zdarzenia A > B: p = 1.22e-35; zdarzenia A > pseudo-zdarzenia A: p = 6.66e-64; zdarzenia B > pseudo-zdarzenia B (ryzyko szczątkowe): p = 2.91e-07.
- Efekt #283 wg kryterium README: POTWIERDZONY.
- Ryzyko szczątkowe, wielkość: mediana zdarzeń B - mediana pseudo-zdarzeń B = 0.046 ms.
- Eksploracja po pomiarze (poza kryteriami), zdarzenia bez slotu w oknie zwolnienia: A: n = 262 (odrzucone 8), p50 / max 6.094 / 53.659, p99 53.279 [53.013, 53.659] stabilne; B: n = 270 (odrzucone 0), p50 / max 0.531 / 47.855, p99 47.551 [47.424, 47.855] stabilne; MW A > B p = 1.71e-34, B > pseudo B p = 2.91e-07.
- Kontrola aparatury, compute_ns p50 per przebieg: mediana A-B = -0.67 µs, rozrzut wewnątrz strony do 2.76 µs, permutacyjny MW p = 0.0592 - w szumie.
- Kontrola aparatury, wake_lag_ns p99 per przebieg: mediana A-B = 266.54 µs, rozrzut wewnątrz strony do 573.16 µs, permutacyjny MW p = 0.00777 - w szumie.

## uc07

| wielkość [ms] | A | B |
|---|---|---|
| przebiegi / podłączenia / bez przypisania / klient bez wiersza lub zabity | 9 / 270 / 0 / 0 | 9 / 270 / 0 / 0 |
| okno W p50 / max | 0.897 / 1.588 | 0.900 / 1.072 |
| mmap kolejki p50 / max | 0.027 / 0.090 | 0.026 / 0.079 |
| zwolnienie kolejki: liczba / w wątku RT | 270 / 270 | 270 / 270 |
| zwolnienie kolejki (munmap+unlinkat) p50 / max | 0.523 / 0.585 | 0.523 / 0.559 |
| zwolnienie: max e2e slotu p50 / p99 / max | 0.669 / 2.851 / 3.151 | 0.669 / 2.895 / 2.959 |
| zdarzenie: n_hit | 9 | 10 |
| zdarzenie: p50 / max e2e | 0.766 / 1.156 | 0.213 / 0.439 |
| zdarzenie: p99 e2e [CI 95 %] | n_hit < 100 | n_hit < 100 |
| pseudo-zdarzenie (kontrola): liczba / p50 / p99 / max | 5400 / 0.132 / 2.443 / 2.557 | 5400 / 0.133 / 2.440 / 2.514 |
| slot z podłączeniem: liczba / p99 / max | 9 / 1.156 / 1.156 | 10 / 0.439 / 0.439 |
| kontrola e2e: p50 / p99 / max | 0.129 / 2.295 / 2.671 | 0.130 / 2.285 / 2.583 |
| kontrola compute: p50 / p99 / max | 0.074 / 2.225 / 2.558 | 0.074 / 2.213 / 2.494 |
| kontrola wake_lag: p50 / p99 / max | 0.023 / 0.026 / 0.078 | 0.023 / 0.025 / 0.066 |

- Mann-Whitney zdarzenia A > B: p = 0.000472; zdarzenia A > pseudo-zdarzenia A: p = 4.08e-06; zdarzenia B > pseudo-zdarzenia B (ryzyko szczątkowe): p = 0.00101.
- Efekt #283 wg kryterium README: NIEPOTWIERDZONY (p99 nieraportowane przy n_hit < 100).
- Ryzyko szczątkowe, wielkość: mediana zdarzeń B - mediana pseudo-zdarzeń B = 0.080 ms.
- Eksploracja po pomiarze (poza kryteriami), zdarzenia bez slotu w oknie zwolnienia: A: n = 8 (odrzucone 1), p50 / max 0.626 / 1.049; B: n = 10 (odrzucone 0), p50 / max 0.213 / 0.439; MW A > B p = 0.000805, B > pseudo B p = 0.00101.
- Kontrola aparatury, compute_ns p50 per przebieg: mediana A-B = -0.11 µs, rozrzut wewnątrz strony do 2.39 µs, permutacyjny MW p = 0.863 - w szumie.
- Kontrola aparatury, wake_lag_ns p99 per przebieg: mediana A-B = 0.09 µs, rozrzut wewnątrz strony do 9.05 µs, permutacyjny MW p = 0.387 - w szumie.

## uc08

| wielkość [ms] | A | B |
|---|---|---|
| przebiegi / podłączenia / bez przypisania / klient bez wiersza lub zabity | 9 / 270 / 0 / 0 | 9 / 270 / 0 / 0 |
| okno W p50 / max | 0.384 / 0.485 | 0.384 / 0.504 |
| mmap kolejki p50 / max | 0.026 / 0.105 | 0.024 / 0.087 |
| zwolnienie kolejki: liczba / w wątku RT | 270 / 270 | 270 / 270 |
| zwolnienie kolejki (munmap+unlinkat) p50 / max | 0.250 / 0.290 | 0.250 / 0.292 |
| zwolnienie: max e2e slotu p50 / p99 / max | 0.652 / 1.694 / 1.810 | 0.649 / 1.685 / 1.742 |
| zdarzenie: n_hit | 1 | 1 |
| zdarzenie: p50 / max e2e | 1.425 / 1.425 | 0.055 / 0.055 |
| zdarzenie: p99 e2e [CI 95 %] | n_hit < 100 | n_hit < 100 |
| pseudo-zdarzenie (kontrola): liczba / p50 / p99 / max | 2551 / 0.388 / 1.383 / 1.653 | 2454 / 0.395 / 1.390 / 1.540 |
| slot z podłączeniem: liczba / p99 / max | 1 / 1.425 / 1.425 | 1 / 0.055 / 0.055 |
| kontrola e2e: p50 / p99 / max | 0.375 / 1.362 / 1.653 | 0.379 / 1.358 / 1.540 |
| kontrola compute: p50 / p99 / max | 0.314 / 1.286 / 1.535 | 0.316 / 1.281 / 1.435 |
| kontrola wake_lag: p50 / p99 / max | 0.024 / 0.027 / 0.064 | 0.023 / 0.029 / 0.061 |

- Mann-Whitney zdarzenia A > B: p = 0.5; zdarzenia A > pseudo-zdarzenia A: p = 0.0427; zdarzenia B > pseudo-zdarzenia B (ryzyko szczątkowe): p = 0.926.
- Efekt #283 wg kryterium README: NIEPOTWIERDZONY (p99 nieraportowane przy n_hit < 100).
- Ryzyko szczątkowe, wielkość: mediana zdarzeń B - mediana pseudo-zdarzeń B = -0.340 ms.
- Eksploracja po pomiarze (poza kryteriami), zdarzenia bez slotu w oknie zwolnienia: A: n = 1 (odrzucone 0), p50 / max 1.425 / 1.425; B: n = 1 (odrzucone 0), p50 / max 0.055 / 0.055; MW A > B p = 0.5, B > pseudo B p = 0.926.
- Kontrola aparatury, compute_ns p50 per przebieg: mediana A-B = -1.37 µs, rozrzut wewnątrz strony do 8.74 µs, permutacyjny MW p = 0.077 - w szumie.
- Kontrola aparatury, wake_lag_ns p99 per przebieg: mediana A-B = -0.52 µs, rozrzut wewnątrz strony do 10.03 µs, permutacyjny MW p = 0.73 - w szumie.

