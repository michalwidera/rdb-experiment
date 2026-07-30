# K6.0 — kalibracja rate'u pomiarowego

Reguła zamrożona w README: największe `s`, dla którego **każda** komórka
kalibracyjna spełnia `p99(compute_ns) <= 0.5 * slot(phi)`.

- komórki: W2_Q32, W3_d3, W4_Q32, W9_Q32 × OFF, STRUCT
- powtórzeń na komórkę: 3, slotów na przebieg: 1200

| `s` | slot `phi` | budżet | przypadek | profil | p99 `compute_ns` | mieści się |
|---:|---:|---:|---|---|---:|:--:|
| 36 | 1851.85 µs | 925.93 µs | `W2_Q32` | OFF | 2550.07 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | `W2_Q32` | STRUCT | 2513.45 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | `W3_d3` | OFF | 1067.27 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | `W3_d3` | STRUCT | 1069.16 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | `W4_Q32` | OFF | 32658.57 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | `W4_Q32` | STRUCT | 35621.32 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | `W9_Q32` | OFF | 3424.36 µs | **nie** |
| 36 | 1851.85 µs | 925.93 µs | `W9_Q32` | STRUCT | 3754.86 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | `W2_Q32` | OFF | 2527.05 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | `W2_Q32` | STRUCT | 2516.87 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | `W3_d3` | OFF | 1114.03 µs | tak |
| 24 | 2777.78 µs | 1388.89 µs | `W3_d3` | STRUCT | 1067.71 µs | tak |
| 24 | 2777.78 µs | 1388.89 µs | `W4_Q32` | OFF | 34923.66 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | `W4_Q32` | STRUCT | 35497.68 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | `W9_Q32` | OFF | 3345.55 µs | **nie** |
| 24 | 2777.78 µs | 1388.89 µs | `W9_Q32` | STRUCT | 3124.68 µs | **nie** |
| 12 | 5555.56 µs | 2777.78 µs | `W2_Q32` | OFF | 3254.55 µs | **nie** |
| 12 | 5555.56 µs | 2777.78 µs | `W2_Q32` | STRUCT | 2549.92 µs | tak |
| 12 | 5555.56 µs | 2777.78 µs | `W3_d3` | OFF | 1072.86 µs | tak |
| 12 | 5555.56 µs | 2777.78 µs | `W3_d3` | STRUCT | 1077.86 µs | tak |
| 12 | 5555.56 µs | 2777.78 µs | `W4_Q32` | OFF | 34766.77 µs | **nie** |
| 12 | 5555.56 µs | 2777.78 µs | `W4_Q32` | STRUCT | 35587.30 µs | **nie** |
| 12 | 5555.56 µs | 2777.78 µs | `W9_Q32` | OFF | 3347.03 µs | **nie** |
| 12 | 5555.56 µs | 2777.78 µs | `W9_Q32` | STRUCT | 3943.82 µs | **nie** |
| 6 | 11111.11 µs | 5555.56 µs | `W2_Q32` | OFF | 2638.01 µs | tak |
| 6 | 11111.11 µs | 5555.56 µs | `W2_Q32` | STRUCT | 3322.66 µs | tak |
| 6 | 11111.11 µs | 5555.56 µs | `W3_d3` | OFF | 1080.97 µs | tak |
| 6 | 11111.11 µs | 5555.56 µs | `W3_d3` | STRUCT | 1076.62 µs | tak |
| 6 | 11111.11 µs | 5555.56 µs | `W4_Q32` | OFF | 35297.57 µs | **nie** |
| 6 | 11111.11 µs | 5555.56 µs | `W4_Q32` | STRUCT | 35483.60 µs | **nie** |
| 6 | 11111.11 µs | 5555.56 µs | `W9_Q32` | OFF | 3980.06 µs | tak |
| 6 | 11111.11 µs | 5555.56 µs | `W9_Q32` | STRUCT | 3587.15 µs | tak |

## Wynik

**Żadne `s` z drabiny nie spełnia reguły.** Kampania nie może wystartować:

drabina jest zamrożona, więc nie wolno dopisać do niej wolniejszego rate'u bez
nowego katalogu wyników (R3). Decyzja należy do człowieka.
