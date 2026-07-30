# K6b.0 — kalibracja rate'u pomiarowego (per rodzina)

Reguła zamrożona w README v2: dla każdej rodziny największe `s`, przy którym
**każda niewykluczona** komórka spełnia `p99(compute_ns) <= 0.5 * slot(phi)`
w najgorszym zmierzonym profilu. Komórka niemieszcząca się przy `s = 1` wypada
z Tier B i nie ogranicza rate'u swojej rodziny.

- drabina: [36, 24, 12, 6, 3, 1]
- profile kalibracyjne: OFF, STRUCT — bez przepisywania algebraicznego, więc górne oszacowanie kosztu
- powtórzeń na komórkę i profil: 3
- komórek kalibrowanych: 11, przebiegów: 264

## Przemiecenie drabiny

Rodzina nieobecna na niższym szczeblu jest rodziną **rozstrzygniętą** wyżej —
kalibracja nie mierzy jej dalej.

| `s` | slot `phi` | budżet | slotów | rodzina | przypadek | `p99` (najgorszy profil) | mieści się |
|---:|---:|---:|---:|---|---|---:|:--:|
| 36 | 1851.85 µs | 925.93 µs | 4320 | W2 | `W2_Q01` | 194.31 µs | tak |
| 36 | 1851.85 µs | 925.93 µs | 4320 | W2 | `W2_Q08` | 833.55 µs | tak |
| 36 | 1851.85 µs | 925.93 µs | 4320 | W2 | `W2_Q32` | 3028.21 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | 4320 | W3 | `W3_d1` | 733.38 µs | tak |
| 36 | 1851.85 µs | 925.93 µs | 4320 | W3 | `W3_d3` | 1159.21 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | 4320 | W4 | `W4_Q08` | 8899.92 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | 4320 | W4 | `W4_Q32` | 34917.90 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | 4320 | W5 | `W5_Q32` | 3159.95 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | 4320 | W7 | `W7_Q32` | 3661.36 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | 4320 | W9 | `W9_Q08` | 1318.97 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | 4320 | W9 | `W9_Q32` | 3810.79 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W2 | `W2_Q01` | 381.11 µs | tak |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W2 | `W2_Q08` | 734.75 µs | tak |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W2 | `W2_Q32` | 3037.91 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W3 | `W3_d1` | 885.90 µs | tak |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W3 | `W3_d3` | 1122.28 µs | tak |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W4 | `W4_Q08` | 9147.03 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W4 | `W4_Q32` | 35553.57 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W5 | `W5_Q32` | 2683.05 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W7 | `W7_Q32` | 3731.74 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W9 | `W9_Q08` | 1300.45 µs | tak |
| 24 | 2777.78 µs | 1388.89 µs | 2880 | W9 | `W9_Q32` | 3892.62 µs | **nie** |
| 12 | 5555.56 µs | 2777.78 µs | 1440 | W2 | `W2_Q01` | 392.62 µs | tak |
| 12 | 5555.56 µs | 2777.78 µs | 1440 | W2 | `W2_Q08` | 731.36 µs | tak |
| 12 | 5555.56 µs | 2777.78 µs | 1440 | W2 | `W2_Q32` | 3224.13 µs | **nie** |
| 12 | 5555.56 µs | 2777.78 µs | 1440 | W4 | `W4_Q08` | 9898.41 µs | **nie** |
| 12 | 5555.56 µs | 2777.78 µs | 1440 | W4 | `W4_Q32` | 35198.72 µs | **nie** |
| 12 | 5555.56 µs | 2777.78 µs | 1440 | W5 | `W5_Q32` | 3493.46 µs | **nie** |
| 12 | 5555.56 µs | 2777.78 µs | 1440 | W7 | `W7_Q32` | 3980.88 µs | **nie** |
| 12 | 5555.56 µs | 2777.78 µs | 1440 | W9 | `W9_Q08` | 1262.12 µs | tak |
| 12 | 5555.56 µs | 2777.78 µs | 1440 | W9 | `W9_Q32` | 3855.68 µs | **nie** |
| 6 | 11111.11 µs | 5555.56 µs | 720 | W2 | `W2_Q01` | 203.76 µs | tak |
| 6 | 11111.11 µs | 5555.56 µs | 720 | W2 | `W2_Q08` | 1039.12 µs | tak |
| 6 | 11111.11 µs | 5555.56 µs | 720 | W2 | `W2_Q32` | 3267.76 µs | tak |
| 6 | 11111.11 µs | 5555.56 µs | 720 | W4 | `W4_Q08` | 8146.63 µs | **nie** |
| 6 | 11111.11 µs | 5555.56 µs | 720 | W4 | `W4_Q32` | 38270.47 µs | **nie** |
| 6 | 11111.11 µs | 5555.56 µs | 720 | W5 | `W5_Q32` | 3313.11 µs | tak |
| 6 | 11111.11 µs | 5555.56 µs | 720 | W7 | `W7_Q32` | 3252.68 µs | tak |
| 6 | 11111.11 µs | 5555.56 µs | 720 | W9 | `W9_Q08` | 1145.56 µs | tak |
| 6 | 11111.11 µs | 5555.56 µs | 720 | W9 | `W9_Q32` | 3989.33 µs | tak |
| 3 | 22222.22 µs | 11111.11 µs | 400 | W4 | `W4_Q08` | 10209.73 µs | tak |
| 3 | 22222.22 µs | 11111.11 µs | 400 | W4 | `W4_Q32` | 39277.99 µs | **nie** |
| 1 | 66666.67 µs | 33333.33 µs | 400 | W4 | `W4_Q08` | 10559.21 µs | tak |
| 1 | 66666.67 µs | 33333.33 µs | 400 | W4 | `W4_Q32` | 35290.81 µs | **nie** |

## Rate wybrany per rodzina

| Rodzina | `s` | `f_phi` | slot | slotów | źródło |
|---|---:|---:|---:|---:|---|
| W2 | 6 | 90.0 Hz | 11111.11 µs | 720 | kalibracja |
| W3 | 24 | 360.0 Hz | 2777.78 µs | 2880 | kalibracja |
| W4 | 3 | 45.0 Hz | 22222.22 µs | 400 | kalibracja |
| W5 | 6 | 90.0 Hz | 11111.11 µs | 720 | kalibracja |
| W7 | 6 | 90.0 Hz | 11111.11 µs | 720 | kalibracja |
| W8 | — | 360.0 Hz | 2777.78 µs | 2880 | deklaracja zrodla |
| W9 | 6 | 90.0 Hz | 11111.11 µs | 720 | kalibracja |

## Komórki wykluczone z Tier B

Komórka nie mieści się w budżecie nawet przy `s = 1` (`f_phi = 15 Hz`).
Wykluczenie jest **wynikiem**, nie zamiataniem: wymagany rate jest podany.

| Przypadek | `p99` przy `s=1` | budżet | wymagane `f_phi` |
|---|---:|---:|---:|
| `W4_Q32` | 35290.81 µs | 33333.33 µs | 14.17 Hz |

## Uwaga o statusie tych liczb

Wyniki kalibracji **nie są wynikami kampanii** i nie wchodzą do żadnej tabeli
artykułu. Wchodzą natomiast — jako pary (komórka, rate, `p99`) — do modelu
kosztu slotu (`cost_model.md`, K20 etap 1), który jest produktem ubocznym
i nie zmienia reguły wyboru rate'u.
