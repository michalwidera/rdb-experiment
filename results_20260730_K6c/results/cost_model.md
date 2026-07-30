# K6b — model kosztu slotu (K20 etap 1)

**To jest produkt uboczny, nie reguła kampanii.** Rate został wybrany empirycznie,
przez pełne przemiecenie drabiny. Model dopasowano **po** kalibracji, na danych,
które i tak powstały: zero dodatkowych przebiegów pomiarowych, zero zmian w silniku.

- postać: `koszt_slotu ~ a·tokeny + b·bajty_trwale_na_slot + c·bajty_pamieciowe_na_slot`
- dopasowanie na rodzinach: W2, W3, W5, W7 (22 punktów)
- predykcja na rodzinach: W4, W9 (18 punktów)
- obserwacji bez liczników (pominięte): 0
- kontrola liczników planu wobec Tier A: 14 przypadków, 0 niezgodności

Podział rodzin był zamrożony w predeklaracji **przed** dopasowaniem. `W4` jest
w zbiorze testowym celowo: to ona łamie model liczący same tokeny.

**Odstępstwo od dosłownego zapisu predeklaracji.** README v2 mówi
`a·tokeny + b·materializacje + c·bajty`. Liczniki, które silnik udostępnia
w jednym przebiegu, mierzą materializację **w bajtach** (`MATERIALIZED ... bajty=`),
rozdzielnie dla ścieżki trwałej i pamięciowej; osobnej liczby materializacji
instrument nie zachowuje. Trzecim wymiarem jest więc podział bajtów na trwałe
i pamięciowe, a nie liczba obok bajtów. Wymóg predeklaracji — żeby praca zapisu
miała własny współczynnik, niezależny od tokenów — jest spełniony, i to
mocniej: ścieżka trwała i pamięciowa mają współczynniki osobne, więc
przepowiednia „koszt `W4` siedzi w zapisach przez `storage`" jest sprawdzalna
wprost na znaku i wielkości `b` względem `c`.

## Współczynniki

| Cecha | Współczynnik |
|---|---:|
| `tokeny` | 32674.6 ns |
| `bajty_trwale_na_slot` | -14046.6 ns |
| `bajty_pamieciowe_na_slot` | -62868.7 ns |

**Ostrzeżenie: współczynnik ujemny przy `bajty_trwale_na_slot`, `bajty_pamieciowe_na_slot`.** Koszt nie bywa ujemny, więc to nie jest wielkość fizyczna, tylko objaw współliniowości cech: dopasowanie kompensuje jedną cechę drugą. Model może przez to pasować na rodzinach uczących i nie znaczyć nic poza nimi. Liczby niżej należy czytać z tym zastrzeżeniem.

## Dopasowanie (rodziny uczące)

| Przypadek | `s` | przewidziane | zmierzone | błąd względny |
|---|---:|---:|---:|---:|
| `W2_Q01` | 12 | 97.11 µs | 399.68 µs | -75.7% |
| `W2_Q01` | 24 | 96.55 µs | 387.37 µs | -75.1% |
| `W2_Q01` | 36 | 96.37 µs | 198.33 µs | -51.4% |
| `W2_Q08` | 12 | 718.66 µs | 733.38 µs | -2.0% |
| `W2_Q08` | 24 | 717.29 µs | 704.14 µs | +1.9% |
| `W2_Q08` | 36 | 716.83 µs | 1015.03 µs | -29.4% |
| `W2_Q32` | 12 | 2849.69 µs | 2603.25 µs | +9.5% |
| `W2_Q32` | 24 | 2845.51 µs | 2607.47 µs | +9.1% |
| `W2_Q32` | 36 | 2844.11 µs | 2651.08 µs | +7.3% |
| `W3_d1` | 12 | 718.66 µs | 733.46 µs | -2.0% |
| `W3_d1` | 24 | 717.29 µs | 703.27 µs | +2.0% |
| `W3_d1` | 36 | 716.83 µs | 730.53 µs | -1.9% |
| `W3_d3` | 12 | 1162.27 µs | 1114.32 µs | +4.3% |
| `W3_d3` | 24 | 1159.24 µs | 1117.99 µs | +3.7% |
| `W3_d3` | 36 | 1159.24 µs | 1116.34 µs | +3.8% |
| `W5_Q32` | 12 | 2837.63 µs | 2716.47 µs | +4.5% |
| `W5_Q32` | 24 | 2835.76 µs | 2661.71 µs | +6.5% |
| `W5_Q32` | 36 | 2835.13 µs | 2686.04 µs | +5.6% |
| `W7_Q32` | 6 | 3003.16 µs | 3266.51 µs | -8.1% |
| `W7_Q32` | 12 | 2995.48 µs | 3237.78 µs | -7.5% |
| `W7_Q32` | 24 | 2991.63 µs | 3239.09 µs | -7.6% |
| `W7_Q32` | 36 | 2990.35 µs | 3255.33 µs | -8.1% |

Średni bezwzględny błąd względny: **14.9%**.

## Predykcja (rodziny testowe, niewidziane przy dopasowaniu)

| Przypadek | `s` | przewidziane | zmierzone | błąd względny |
|---|---:|---:|---:|---:|
| `W4_Q08` | 1 | 870.54 µs | 9535.86 µs | -90.9% |
| `W4_Q08` | 3 | 870.54 µs | 9165.47 µs | -90.5% |
| `W4_Q08` | 6 | 305.79 µs | 10387.09 µs | -97.1% |
| `W4_Q08` | 12 | -47.19 µs | 9916.22 µs | -100.5% |
| `W4_Q08` | 24 | -223.67 µs | 8098.85 µs | -102.8% |
| `W4_Q08` | 36 | -282.50 µs | 8142.36 µs | -103.5% |
| `W4_Q32` | 1 | 3450.42 µs | 33021.96 µs | -89.6% |
| `W4_Q32` | 3 | 3450.42 µs | 32948.62 µs | -89.5% |
| `W4_Q32` | 6 | 1195.58 µs | 33290.36 µs | -96.4% |
| `W4_Q32` | 12 | -213.70 µs | 35153.23 µs | -100.6% |
| `W4_Q32` | 24 | -918.33 µs | 34727.75 µs | -102.6% |
| `W4_Q32` | 36 | -1153.21 µs | 34521.61 µs | -103.3% |
| `W9_Q08` | 12 | 6146.90 µs | 885.80 µs | +593.9% |
| `W9_Q08` | 24 | 6143.15 µs | 883.23 µs | +595.5% |
| `W9_Q08` | 36 | 6141.91 µs | 1250.04 µs | +391.3% |
| `W9_Q32` | 12 | 24587.60 µs | 3369.52 µs | +629.7% |
| `W9_Q32` | 24 | 24572.62 µs | 3349.59 µs | +633.6% |
| `W9_Q32` | 36 | 24567.62 µs | 3332.57 µs | +637.2% |

Średni bezwzględny błąd względny: **258.3%**.

## Walidacja na medianach Tier B

Przewidywanie dotyczy `p99` z kalibracji, a porównanie — mediany Tier B, więc
systematyczne przeszacowanie jest oczekiwane. Interesuje nas rząd wielkości
i to, czy błąd nie eksploduje na rodzinie zdominowanej przez materializacje.

| Przypadek | przewidziane | mediana Tier B | błąd względny |
|---|---:|---:|---:|
| `W2_Q01` | 97.11 µs | 131.91 µs | -26.4% |
| `W2_Q08` | 718.66 µs | 633.63 µs | +13.4% |
| `W2_Q32` | 2849.69 µs | 2450.93 µs | +16.3% |
| `W3_d1` | 718.66 µs | 629.34 µs | +14.2% |
| `W3_d3` | 1162.27 µs | 623.52 µs | +86.4% |
| `W4_Q08` | 870.54 µs | 8093.58 µs | -89.2% |
| `W4_Q32` | 3450.42 µs | 32427.08 µs | -89.4% |
| `W5_Q32` | 2837.63 µs | 2484.98 µs | +14.2% |
| `W7_Q32` | 3003.16 µs | 3048.35 µs | -1.5% |
| `W8_Q01` | -5848.13 µs | 517.28 µs | -1230.6% |
| `W8_Q08` | -5314.26 µs | 1053.70 µs | -604.3% |
| `W9_Q08` | 6146.90 µs | 824.90 µs | +645.2% |
| `W9_Q32` | 24587.60 µs | 3059.14 µs | +703.7% |

Średni bezwzględny błąd względny: **271.9%**.

## Sprawdzalna przepowiednia

Zapisana **przed** dopasowaniem: `W4_Q32` na `SUBSTRAT memory` powinna być
radykalnie tańsza, bo jej koszt siedzi w zapisach przez `storage`, nie
w arytmetyce. Sprawdzenie tej przepowiedni nie należy do K6b.

Etap drugi K20 — kontrola dopuszczenia planu wewnątrz `xretractor` — jest zmianą
w silniku i nie należy do tej kampanii.
