# K6b — wynik kampanii ablacyjnej

- przebiegów: 780
- przypadków: 13, profili: 5
- metryka główna: `compute_median_ns`, próg istotności praktycznej: 10%
- bootstrap: 10000 replikacji, ziarno 20260730
- kontrola rate'u: 13 przypadków sprawdzonych, 0 niezgodności
- komórek wykluczonych przez kalibrację: 0
- komórek wykluczonych decyzją człowieka: 1

## Metryka główna — wszystkie komórki

| Przypadek | rate | `STRUCT` [µs] | `ALGSTRUCT` [µs] | iloraz | 95% CI | klasa | kontrola |
|---|---|---:|---:|---:|---|:--:|:--:|
| `W2_Q01` | s=12, f_phi generatora=180 Hz, strumień=180 Hz | 125.24 | 133.21 | 1.064 | [1.038; 1.100] | **B** |  |
| `W2_Q08` | s=12, f_phi generatora=180 Hz, strumień=180 Hz | 606.25 | 642.99 | 1.061 | [1.053; 1.066] | **B** |  |
| `W2_Q32` | s=12, f_phi generatora=180 Hz, strumień=180 Hz | 2458.34 | 2437.13 | 0.991 | [0.980; 0.994] | **B** |  |
| `W3_d1` | s=12, f_phi generatora=180 Hz, strumień=180 Hz | 602.33 | 636.34 | 1.056 | [1.023; 1.064] | **B** |  |
| `W3_d3` | s=12, f_phi generatora=180 Hz, strumień=405 Hz | 589.58 | 650.58 | 1.103 | [1.099; 1.106] | **C** |  |
| `W4_Q08` | s=1, f_phi generatora=15 Hz, strumień=15 Hz | 8089.01 | 8109.23 | 1.002 | [0.999; 1.005] | **B** |  |
| `W4_Q32` | s=1, f_phi generatora=15 Hz, strumień=15 Hz | 32512.90 | 32452.39 | 0.998 | [0.994; 1.000] | **B** |  |
| `W5_Q32` | s=12, f_phi generatora=180 Hz, strumień=180 Hz | 2476.39 | 2523.15 | 1.019 | [1.010; 1.025] | **B** | neg |
| `W7_Q32` | s=6, f_phi generatora=90 Hz, strumień=90 Hz | 3047.44 | 3066.58 | 1.006 | [1.001; 1.012] | **B** | neg |
| `W8_Q01` | s=6, f_phi generatora=90 Hz, strumień=720 Hz | 519.56 | 517.30 | 0.996 | [0.934; 1.021] | **B** |  |
| `W8_Q08` | s=6, f_phi generatora=90 Hz, strumień=720 Hz | 1060.77 | 1049.66 | 0.990 | [0.971; 1.001] | **B** |  |
| `W9_Q08` | s=12, f_phi generatora=180 Hz, strumień=120 Hz | 894.93 | 817.42 | 0.913 | [0.899; 0.918] | **B** |  |
| `W9_Q32` | s=12, f_phi generatora=180 Hz, strumień=120 Hz | 3077.53 | 2969.63 | 0.965 | [0.962; 0.971] | **B** |  |

## Komórki wykluczone z Tier B przez kalibrację

Brak.

## Komórki wykluczone z Tier B decyzją człowieka

Wykluczenie decyzją jest rozłączne z kalibracyjnym: komórka mieściła się
w budżecie kalibracji, ale została wyjęta z Tier B osobną decyzją. Jej
nieobecność w tabeli wyżej jest częścią wyniku, nie pominięciem.

| Przypadek | rodzina | powód |
|---|---|---|
| `W8_Q32` | W8 | duty 243% p99 @720Hz - przeciazenie, silnik nie nadaza; decyzja czlowieka 2026-07-31; patrz README K6c |

## Kontrola nasycenia (raportowana, nie unieważniająca)

**23 komórek** przekroczyło budżet `0,5 · slot` w `p99` mimo
rate'u wybranego na profilach `OFF`/`STRUCT`. Kalibracja zakładała, że profile
z przepisywaniem algebraicznym mogą pracę wyłącznie usunąć; poniższe komórki
temu przeczą i ich interpretacja musi to uwzględnić.

- W2_Q32/ALGSTRUCT: p99 = 2788.20 µs > budżet 2777.78 µs (50 % slotu 5555.56 µs)
- W2_Q32/OFF: p99 = 3482.32 µs > budżet 2777.78 µs (63 % slotu 5555.56 µs)
- W2_Q32/STRUCT: p99 = 3564.13 µs > budżet 2777.78 µs (64 % slotu 5555.56 µs)
- W2_Q32/STRUCT_R1: p99 = 3404.17 µs > budżet 2777.78 µs (61 % slotu 5555.56 µs)
- W3_d3/ALGSTRUCT: p99 = 1290.02 µs > budżet 1234.57 µs (52 % slotu 2469.14 µs)
- W3_d3/OFF: p99 = 1375.28 µs > budżet 1234.57 µs (56 % slotu 2469.14 µs)
- W4_Q32/ALGSTRUCT: p99 = 38540.47 µs > budżet 33333.33 µs (58 % slotu 66666.67 µs)
- W4_Q32/OFF: p99 = 38154.40 µs > budżet 33333.33 µs (57 % slotu 66666.67 µs)
- W4_Q32/STRUCT: p99 = 44916.00 µs > budżet 33333.33 µs (67 % slotu 66666.67 µs)
- W4_Q32/STRUCT_R1: p99 = 38632.96 µs > budżet 33333.33 µs (58 % slotu 66666.67 µs)
- W5_Q32/ALGSTRUCT: p99 = 3716.32 µs > budżet 2777.78 µs (67 % slotu 5555.56 µs)
- W5_Q32/OFF: p99 = 3500.72 µs > budżet 2777.78 µs (63 % slotu 5555.56 µs)
- W5_Q32/STRUCT: p99 = 3493.07 µs > budżet 2777.78 µs (63 % slotu 5555.56 µs)
- W5_Q32/STRUCT_R1: p99 = 3539.95 µs > budżet 2777.78 µs (64 % slotu 5555.56 µs)
- W8_Q01/ALGSTRUCT: p99 = 1054.72 µs > budżet 694.44 µs (76 % slotu 1388.89 µs)
- W8_Q01/OFF: p99 = 1111.51 µs > budżet 694.44 µs (80 % slotu 1388.89 µs)
- W8_Q01/STRUCT: p99 = 1142.80 µs > budżet 694.44 µs (82 % slotu 1388.89 µs)
- W8_Q01/STRUCT_R1: p99 = 1102.96 µs > budżet 694.44 µs (79 % slotu 1388.89 µs)
- W8_Q08/ALGSTRUCT: p99 = 1558.36 µs > budżet 694.44 µs (112 % slotu 1388.89 µs)
- W8_Q08/OFF: p99 = 2012.42 µs > budżet 694.44 µs (145 % slotu 1388.89 µs)
- W8_Q08/STRUCT: p99 = 1680.19 µs > budżet 694.44 µs (121 % slotu 1388.89 µs)
- W8_Q08/STRUCT_R1: p99 = 1594.93 µs > budżet 694.44 µs (115 % slotu 1388.89 µs)
- W9_Q32/OFF: p99 = 4809.32 µs > budżet 4166.67 µs (58 % slotu 8333.33 µs)

## Atrybucja profilowa (G14)

| Przypadek | `ALGSTRUCT` [µs] | `OFF` [µs] | `STRUCT` [µs] | `STRUCT_R1` [µs] | `STRUCT_R2` [µs] |
|---|---:|---:|---:|---:|---:|
| `W2_Q01` | 133.21 | 124.83 | 125.24 | 132.07 | — |
| `W2_Q08` | 642.99 | 606.66 | 606.25 | 635.22 | — |
| `W2_Q32` | 2437.13 | 2461.26 | 2458.34 | 2414.18 | — |
| `W3_d1` | 636.34 | 602.09 | 602.33 | 630.16 | — |
| `W3_d3` | 650.58 | 588.48 | 589.58 | 642.46 | — |
| `W4_Q08` | 8109.23 | 7968.53 | 8089.01 | 8119.79 | — |
| `W4_Q32` | 32452.39 | 31983.78 | 32512.90 | 32456.89 | — |
| `W5_Q32` | 2523.15 | 2479.99 | 2476.39 | 2482.79 | — |
| `W7_Q32` | 3066.58 | 3035.35 | 3047.44 | 3041.53 | — |
| `W8_Q01` | 517.30 | 513.92 | 519.56 | 523.36 | — |
| `W8_Q08` | 1049.66 | 1049.51 | 1060.77 | 1056.40 | — |
| `W9_Q08` | 817.42 | 827.12 | 894.93 | — | 815.53 |
| `W9_Q32` | 2969.63 | 3264.76 | 3077.53 | — | 2969.79 |

## Werdykt

- komórki (A) poprawa: **0**
- komórki (B) neutralne: **12**
- komórki (C) regresja: **1** — W3_d3

**Brak komórki klasy (A).** Korzyść z R1/R2 nie jest widoczna w czasie obliczeń przy progu 10%. To jest wynik, nie porażka kampanii: korzyść pozostaje strukturalna (plan, tokeny, bufory, materializacje), a artykuł ma tak ją opisać. Zdanie „plan jest mniejszy, ale nie szybszy" jest publikowalne.

## Koszt normalizacji — czas kompilacji (Tier A)

| Przypadek | `STRUCT` [µs] | `ALGSTRUCT` [µs] | iloraz | 95% CI | klasa |
|---|---:|---:|---:|---|:--:|
| `W1` | 261.76 | 276.61 | 1.057 | [1.049; 1.068] | B |
| `W2_Q01` | 260.83 | 276.79 | 1.061 | [1.055; 1.072] | B |
| `W2_Q02` | 311.55 | 325.44 | 1.045 | [1.037; 1.056] | B |
| `W2_Q04` | 402.11 | 413.31 | 1.028 | [1.015; 1.038] | B |
| `W2_Q08` | 570.20 | 587.03 | 1.030 | [1.023; 1.038] | B |
| `W2_Q16` | 985.12 | 1054.62 | 1.071 | [1.058; 1.075] | B |
| `W2_Q32` | 1842.26 | 2241.40 | 1.217 | [1.208; 1.222] | C |
| `W3_d1` | 571.75 | 584.72 | 1.023 | [1.018; 1.033] | B |
| `W3_d2` | 959.73 | 977.42 | 1.018 | [1.013; 1.024] | B |
| `W3_d3` | 1401.86 | 1411.43 | 1.007 | [1.001; 1.013] | B |
| `W4_Q01` | 445.94 | 492.55 | 1.105 | [1.091; 1.116] | C |
| `W4_Q02` | 687.94 | 783.55 | 1.139 | [1.134; 1.144] | C |
| `W4_Q04` | 1236.84 | 1464.91 | 1.184 | [1.179; 1.188] | C |
| `W4_Q08` | 2311.12 | 2964.78 | 1.283 | [1.275; 1.292] | C |
| `W4_Q16` | 4731.69 | 7093.35 | 1.499 | [1.490; 1.507] | C |
| `W4_Q32` | 9739.64 | 18450.82 | 1.894 | [1.880; 1.909] | C |
| `W5_Q01` | 181.70 | 185.26 | 1.020 | [1.011; 1.028] | B |
| `W5_Q02` | 222.81 | 226.70 | 1.017 | [1.000; 1.027] | B |
| `W5_Q04` | 313.35 | 321.65 | 1.026 | [1.019; 1.033] | B |
| `W5_Q08` | 527.07 | 539.33 | 1.023 | [1.015; 1.032] | B |
| `W5_Q16` | 979.15 | 1011.25 | 1.033 | [1.028; 1.039] | B |
| `W5_Q32` | 1992.87 | 2088.64 | 1.048 | [1.042; 1.058] | B |
| `W6_Q01` | 259.64 | 267.42 | 1.030 | [1.022; 1.037] | B |
| `W6_Q02` | 311.63 | 320.61 | 1.029 | [1.025; 1.046] | B |
| `W6_Q04` | 398.85 | 414.87 | 1.040 | [1.030; 1.043] | B |
| `W6_Q08` | 571.36 | 594.97 | 1.041 | [1.034; 1.048] | B |
| `W6_Q16` | 970.28 | 1017.64 | 1.049 | [1.043; 1.055] | B |
| `W6_Q32` | 1872.11 | 1951.55 | 1.042 | [1.033; 1.049] | B |
| `W7_Q01` | 220.79 | 227.04 | 1.028 | [1.023; 1.039] | B |
| `W7_Q02` | 245.33 | 252.28 | 1.028 | [1.018; 1.035] | B |
| `W7_Q04` | 290.61 | 299.64 | 1.031 | [1.020; 1.037] | B |
| `W7_Q08` | 401.16 | 416.01 | 1.037 | [1.028; 1.044] | B |
| `W7_Q16` | 608.42 | 633.16 | 1.041 | [1.035; 1.050] | B |
| `W7_Q32` | 1115.32 | 1164.86 | 1.044 | [1.031; 1.051] | B |
| `W8_Q01` | 996.60 | 1095.21 | 1.099 | [1.089; 1.103] | B |
| `W8_Q02` | 1050.16 | 1155.73 | 1.101 | [1.095; 1.107] | C |
| `W8_Q04` | 1176.19 | 1302.69 | 1.108 | [1.100; 1.114] | C |
| `W8_Q08` | 1440.02 | 1637.22 | 1.137 | [1.128; 1.142] | C |
| `W8_Q16` | 1840.48 | 2192.72 | 1.191 | [1.182; 1.197] | C |
| `W8_Q32` | 2811.64 | 3852.31 | 1.370 | [1.360; 1.380] | C |
| `W9_Q01` | 342.01 | 343.48 | 1.004 | [0.988; 1.015] | B |
| `W9_Q02` | 479.36 | 636.60 | 1.328 | [1.315; 1.338] | C |
| `W9_Q04` | 1106.12 | 982.54 | 0.888 | [0.883; 0.893] | A |
| `W9_Q08` | 1567.65 | 1461.37 | 0.932 | [0.929; 0.935] | B |
| `W9_Q16` | 2746.88 | 2627.16 | 0.956 | [0.951; 0.960] | B |
| `W9_Q32` | 5186.54 | 5057.41 | 0.975 | [0.967; 0.979] | B |

Klasa (C) w tej tabeli jest **ceną** normalizacji, nie korzyścią.

## Metryki drugorzędne

- `compute_p99_ns`: A=1, B=12, C=0
- `compute_sum_ns`: A=0, B=13, C=0
- `e2e_p50_ns`: A=0, B=12, C=1
- `e2e_p999_ns`: A=2, B=11, C=0
- `vmhwm_kb`: A=0, B=13, C=0
- `cpu_ticks`: A=0, B=13, C=0
- `capacity_sum`: A=0, B=13, C=0
- `mat_bytes`: A=0, B=13, C=0
- `mat_mem_bytes`: A=2, B=9, C=0
