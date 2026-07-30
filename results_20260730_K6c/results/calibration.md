# K6c.0 — kalibracja rate'u pomiarowego (per rodzina)

Reguła zamrożona w README v3: dla każdej rodziny największe `s`, przy którym
**każda niewykluczona** komórka spełnia `p99(compute_ns) <= 0.5 * slot`
w najgorszym zmierzonym profilu. Komórka niemieszcząca się przy `s = 1` wypada
z Tier B i nie ogranicza rate'u swojej rodziny.

`slot` pochodzi z **silnika** (`xqry -t`), dla strumienia, który kampania
faktycznie mierzy. To jest zmiana v3 wobec v2 i jedyny powód istnienia K6c.

- drabina: [36, 24, 12, 6, 3, 1]
- profile kalibracyjne: OFF, STRUCT — bez przepisywania algebraicznego, więc górne oszacowanie kosztu
- powtórzeń na komórkę i profil: 3
- komórek kalibrowanych: 11, przebiegów: 258

## Przemiecenie drabiny

Rodzina nieobecna na niższym szczeblu jest rodziną **rozstrzygniętą** wyżej —
kalibracja nie mierzy jej dalej. Rodziny „ze źródła” mają w kolumnie `s`
mnożnik generatora, którego dla nich nie używa; ich rate jest deklaracją źródła.

| `s` | slot (silnik) | budżet | slotów | rodzina | przypadek | `p99` (najgorszy profil) | mieści się |
|---:|---:|---:|---:|---|---|---:|:--:|
| 36 | 1851.85 µs | 925.93 µs | 4320 | W2 | `W2_Q01` | 198.33 µs | tak |
| 36 | 1851.85 µs | 925.93 µs | 4320 | W2 | `W2_Q08` | 1015.03 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | 4320 | W2 | `W2_Q32` | 2651.08 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | 4320 | W3 | `W3_d1` | 730.53 µs | tak |
| 36 | 823.05 µs | 411.52 µs | 6000 | W3 | `W3_d3` | 1116.34 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | 4320 | W4 | `W4_Q08` | 8142.36 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | 4320 | W4 | `W4_Q32` | 34521.61 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | 4320 | W5 | `W5_Q32` | 2686.04 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | 4320 | W7 | `W7_Q32` | 3255.33 µs | **nie** |
| 36 | 2777.78 µs | 1388.89 µs | 2880 | W9 | `W9_Q08` | 1250.04 µs | tak |
| 36 | 2777.78 µs | 1388.89 µs | 2880 | W9 | `W9_Q32` | 3332.57 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W2 | `W2_Q01` | 387.37 µs | tak |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W2 | `W2_Q08` | 704.14 µs | tak |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W2 | `W2_Q32` | 2607.47 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W3 | `W3_d1` | 703.27 µs | tak |
| 24 | 1234.57 µs | 617.28 µs | 6000 | W3 | `W3_d3` | 1117.99 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W4 | `W4_Q08` | 8098.85 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W4 | `W4_Q32` | 34727.75 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W5 | `W5_Q32` | 2661.71 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W7 | `W7_Q32` | 3239.09 µs | **nie** |
| 24 | 4166.67 µs | 2083.33 µs | 1920 | W9 | `W9_Q08` | 883.23 µs | tak |
| 24 | 4166.67 µs | 2083.33 µs | 1920 | W9 | `W9_Q32` | 3349.59 µs | **nie** |
| 12 | 5555.56 µs | 2777.78 µs | 1440 | W2 | `W2_Q01` | 399.68 µs | tak |
| 12 | 5555.56 µs | 2777.78 µs | 1440 | W2 | `W2_Q08` | 733.38 µs | tak |
| 12 | 5555.56 µs | 2777.78 µs | 1440 | W2 | `W2_Q32` | 2603.25 µs | tak |
| 12 | 5555.56 µs | 2777.78 µs | 1440 | W3 | `W3_d1` | 733.46 µs | tak |
| 12 | 2469.14 µs | 1234.57 µs | 3240 | W3 | `W3_d3` | 1114.32 µs | tak |
| 12 | 5555.56 µs | 2777.78 µs | 1440 | W4 | `W4_Q08` | 9916.22 µs | **nie** |
| 12 | 5555.56 µs | 2777.78 µs | 1440 | W4 | `W4_Q32` | 35153.23 µs | **nie** |
| 12 | 5555.56 µs | 2777.78 µs | 1440 | W5 | `W5_Q32` | 2716.47 µs | tak |
| 12 | 5555.56 µs | 2777.78 µs | 1440 | W7 | `W7_Q32` | 3237.78 µs | **nie** |
| 12 | 8333.33 µs | 4166.67 µs | 960 | W9 | `W9_Q08` | 885.80 µs | tak |
| 12 | 8333.33 µs | 4166.67 µs | 960 | W9 | `W9_Q32` | 3369.52 µs | tak |
| 6 | 11111.11 µs | 5555.56 µs | 720 | W4 | `W4_Q08` | 10387.09 µs | **nie** |
| 6 | 11111.11 µs | 5555.56 µs | 720 | W4 | `W4_Q32` | 33290.36 µs | **nie** |
| 6 | 11111.11 µs | 5555.56 µs | 720 | W7 | `W7_Q32` | 3266.51 µs | tak |
| 3 | 22222.22 µs | 11111.11 µs | 400 | W4 | `W4_Q08` | 9165.47 µs | tak |
| 3 | 22222.22 µs | 11111.11 µs | 400 | W4 | `W4_Q32` | 32948.62 µs | **nie** |
| 1 | 66666.67 µs | 33333.33 µs | 400 | W4 | `W4_Q08` | 9535.86 µs | tak |
| 1 | 66666.67 µs | 33333.33 µs | 400 | W4 | `W4_Q32` | 33021.96 µs | tak |
| 6 | 1388.89 µs | 694.44 µs | 5760 | W8 | `W8_Q01` | 840.42 µs | **nie** |
| 6 | 1388.89 µs | 694.44 µs | 5760 | W8 | `W8_Q08` | 1841.15 µs | **nie** |
| 6 | 1388.89 µs | 694.44 µs | 5760 | W8 | `W8_Q32` | 3376.02 µs | **nie** |

## Rate wybrany per rodzina

`f_phi` generatora to rate przeplotu **dwóch źródeł**, który generator wytwarza.
Nie jest częstotliwością strumienia mierzonego — ta jest w tabeli niżej, per komórka.
Pomylenie tych dwóch wielkości było błędem v2.

| Rodzina | `s` | `f_phi` generatora | źródło rate'u |
|---|---:|---:|---|
| W2 | 12 | 180.0 Hz | kalibracja |
| W3 | 12 | 180.0 Hz | kalibracja |
| W4 | 1 | 15.0 Hz | kalibracja |
| W5 | 12 | 180.0 Hz | kalibracja |
| W7 | 6 | 90.0 Hz | kalibracja |
| W8 | 6 | 90.0 Hz | deklaracja zrodla |
| W9 | 12 | 180.0 Hz | kalibracja |

## Slot per komórka — wartość z silnika wobec wyliczenia v2

Slot jest własnością **komórki**, nie rodziny: `W3_d1` i `W3_d3` mają go różny
przy tym samym `s`, bo przeplot sumuje częstotliwości. Kolumna „v2” pokazuje,
co wstawiłaby poprzednia predeklaracja; kolumna „rozjazd” jest miarą jej błędu.
Budżet slotów liczony jest z wartości zmierzonej.

| Przypadek | strumień | `s` | slot (silnik) | slot wg v2 | rozjazd | częstotliwość | slotów | `p99` | wykorzystanie |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `W2_Q01` | `w2_out_000` | 12 | 5555.56 µs | 5555.56 µs | 1.00× | 180.0 Hz | 1440 | 399.68 µs | 7 % |
| `W2_Q08` | `w2_out_000` | 12 | 5555.56 µs | 5555.56 µs | 1.00× | 180.0 Hz | 1440 | 733.38 µs | 13 % |
| `W2_Q32` | `w2_out_000` | 12 | 5555.56 µs | 5555.56 µs | 1.00× | 180.0 Hz | 1440 | 2603.25 µs | 47 % |
| `W3_d1` | `w3_out_000` | 12 | 5555.56 µs | 5555.56 µs | 1.00× | 180.0 Hz | 1440 | 733.46 µs | 13 % |
| `W3_d3` | `w3_out_000` | 12 | 2469.14 µs | 5555.56 µs | 2.25× | 405.0 Hz | 3240 | 1114.32 µs | 45 % |
| `W4_Q08` | `w4_avg_000` | 1 | 66666.67 µs | 66666.67 µs | 1.00× | 15.0 Hz | 400 | 9535.86 µs | 14 % |
| `W4_Q32` | `w4_avg_000` | 1 | 66666.67 µs | 66666.67 µs | 1.00× | 15.0 Hz | 400 | 33021.96 µs | 50 % |
| `W5_Q32` | `w5_out_000` | 12 | 5555.56 µs | 5555.56 µs | 1.00× | 180.0 Hz | 1440 | 2716.47 µs | 49 % |
| `W7_Q32` | `w7_out_000` | 6 | 11111.11 µs | 11111.11 µs | 1.00× | 90.0 Hz | 720 | 3266.51 µs | 29 % |
| `W8_Q01` | `mon_000` | 6 | 1388.89 µs | 2777.78 µs | 2.00× | 720.0 Hz | 5760 | 840.42 µs | **61 %** |
| `W8_Q08` | `mon_000` | 6 | 1388.89 µs | 2777.78 µs | 2.00× | 720.0 Hz | 5760 | 1841.15 µs | **133 %** |
| `W8_Q32` | `mon_000` | 6 | 1388.89 µs | 2777.78 µs | 2.00× | 720.0 Hz | 5760 | 3376.02 µs | **243 %** |
| `W9_Q08` | `w9_out_000` | 12 | 8333.33 µs | 5555.56 µs | 0.67× | 120.0 Hz | 960 | 885.80 µs | 11 % |
| `W9_Q32` | `w9_out_000` | 12 | 8333.33 µs | 5555.56 µs | 0.67× | 120.0 Hz | 960 | 3369.52 µs | 40 % |

## Komórki wykluczone z Tier B

Brak — każda komórka Tier B zmieściła się w budżecie na którymś szczeblu drabiny.

## Rodziny ze źródła poza budżetem 50 %

Komórki: `W8_Q01`, `W8_Q08`, `W8_Q32`.
Ich rate należy do deklaracji źródła, więc kalibracja go nie zmienia i nie
wyklucza tych komórek. Fakt jest raportowany **przed** kampanią; decyzja,
czy mierzyć rodzinę w tym reżimie, należy do człowieka.

## Uwaga o statusie tych liczb

Wyniki kalibracji **nie są wynikami kampanii** i nie wchodzą do żadnej tabeli
artykułu. Wchodzą natomiast — jako pary (komórka, rate, `p99`) — do modelu
kosztu slotu (`cost_model.md`, K20 etap 1), który jest produktem ubocznym
i nie zmienia reguły wyboru rate'u.
