# K6b — ablation campaign result

- runs: 780
- cases: 13, profiles: 5
- primary metric: `compute_median_ns`, practical significance threshold: 10%
- bootstrap: 10000 replicates, seed 20260730
- rate control: 13 cases checked, 0 mismatches
- cells excluded by calibration: 0
- cells excluded by human decision: 1

## Primary metric — all cells

| Case | rate | `STRUCT` [µs] | `ALGSTRUCT` [µs] | ratio | 95% CI | class | control |
|---|---|---:|---:|---:|---|:--:|:--:|
| `W2_Q01` | s=12, generator f_phi=180 Hz, stream=180 Hz | 92.67 | 95.67 | 1.032 | [1.021; 1.069] | **B** |  |
| `W2_Q08` | s=12, generator f_phi=180 Hz, stream=180 Hz | 405.77 | 433.52 | 1.068 | [1.063; 1.072] | **B** |  |
| `W2_Q32` | s=12, generator f_phi=180 Hz, stream=180 Hz | 1628.85 | 1616.55 | 0.992 | [0.974; 0.996] | **B** |  |
| `W3_d1` | s=12, generator f_phi=180 Hz, stream=180 Hz | 406.23 | 433.13 | 1.066 | [1.059; 1.070] | **B** |  |
| `W3_d3` | s=12, generator f_phi=180 Hz, stream=405 Hz | 396.88 | 441.54 | 1.113 | [1.110; 1.115] | **C** |  |
| `W4_Q08` | s=1, generator f_phi=15 Hz, stream=15 Hz | 4571.86 | 4616.19 | 1.010 | [1.006; 1.014] | **B** |  |
| `W4_Q32` | s=1, generator f_phi=15 Hz, stream=15 Hz | 18160.65 | 18179.15 | 1.001 | [0.997; 1.004] | **B** |  |
| `W5_Q32` | s=12, generator f_phi=180 Hz, stream=180 Hz | 1685.14 | 1684.03 | 0.999 | [0.996; 1.003] | **B** | neg |
| `W7_Q32` | s=6, generator f_phi=90 Hz, stream=90 Hz | 1960.86 | 1957.20 | 0.998 | [0.994; 1.001] | **B** | neg |
| `W8_Q01` | s=6, generator f_phi=90 Hz, stream=720 Hz | 142.34 | 143.00 | 1.005 | [0.987; 1.010] | **B** |  |
| `W8_Q08` | s=6, generator f_phi=90 Hz, stream=720 Hz | 458.92 | 494.51 | 1.078 | [1.072; 1.086] | **B** |  |
| `W9_Q08` | s=12, generator f_phi=180 Hz, stream=120 Hz | 616.92 | 558.85 | 0.906 | [0.900; 0.910] | **B** |  |
| `W9_Q32` | s=12, generator f_phi=180 Hz, stream=120 Hz | 2073.55 | 2038.75 | 0.983 | [0.977; 0.988] | **B** |  |

## Cells excluded from Tier B by calibration

None.

## Cells excluded from Tier B by human decision

Exclusion by decision is disjoint from calibration exclusion: the cell did
fit the calibration budget but was taken out of Tier B by a separate
decision. Its absence from the table above is part of the result, not an
omission.

| Case | family | reason |
|---|---|---|
| `W8_Q32` | W8 | duty 243% p99 @720Hz - przeciazenie, silnik nie nadaza; decyzja czlowieka 2026-07-31; patrz README K6c |

## Saturation control (reported, not invalidating)

**8 cells** exceeded the `0.5 · slot` budget in `p99` despite
a rate chosen on the `OFF`/`STRUCT` profiles. Calibration assumed that profiles
with algebraic rewriting can only remove work; the cells below contradict that,
and their interpretation must take it into account.

- W8_Q01/ALGSTRUCT: p99 = 775.55 µs > budget 694.44 µs (56 % of slot 1388.89 µs)
- W8_Q01/OFF: p99 = 783.99 µs > budget 694.44 µs (56 % of slot 1388.89 µs)
- W8_Q01/STRUCT: p99 = 810.43 µs > budget 694.44 µs (58 % of slot 1388.89 µs)
- W8_Q01/STRUCT_R1: p99 = 787.92 µs > budget 694.44 µs (57 % of slot 1388.89 µs)
- W8_Q08/ALGSTRUCT: p99 = 1111.71 µs > budget 694.44 µs (80 % of slot 1388.89 µs)
- W8_Q08/OFF: p99 = 1191.86 µs > budget 694.44 µs (86 % of slot 1388.89 µs)
- W8_Q08/STRUCT: p99 = 1193.58 µs > budget 694.44 µs (86 % of slot 1388.89 µs)
- W8_Q08/STRUCT_R1: p99 = 1107.54 µs > budget 694.44 µs (80 % of slot 1388.89 µs)

## Per-profile attribution (G14)

| Case | `ALGSTRUCT` [µs] | `OFF` [µs] | `STRUCT` [µs] | `STRUCT_R1` [µs] | `STRUCT_R2` [µs] |
|---|---:|---:|---:|---:|---:|
| `W2_Q01` | 95.67 | 92.62 | 92.67 | 95.54 | — |
| `W2_Q08` | 433.52 | 405.53 | 405.77 | 433.75 | — |
| `W2_Q32` | 1616.55 | 1621.90 | 1628.85 | 1620.61 | — |
| `W3_d1` | 433.13 | 406.25 | 406.23 | 433.63 | — |
| `W3_d3` | 441.54 | 394.96 | 396.88 | 442.54 | — |
| `W4_Q08` | 4616.19 | 4606.02 | 4571.86 | 4613.13 | — |
| `W4_Q32` | 18179.15 | 18369.99 | 18160.65 | 18183.74 | — |
| `W5_Q32` | 1684.03 | 1679.87 | 1685.14 | 1686.42 | — |
| `W7_Q32` | 1957.20 | 1963.95 | 1960.86 | 1971.70 | — |
| `W8_Q01` | 143.00 | 141.28 | 142.34 | 142.54 | — |
| `W8_Q08` | 494.51 | 455.94 | 458.92 | 492.99 | — |
| `W9_Q08` | 558.85 | 531.55 | 616.92 | — | 560.32 |
| `W9_Q32` | 2038.75 | 2090.47 | 2073.55 | — | 2023.76 |

## Verdict

- cells (A) improvement: **0**
- cells (B) neutral: **12**
- cells (C) regression: **1** — W3_d3

**CAMPAIGN INVALID.** The result is not preserved across profiles: W2_Q01: 2 different artifact checksums; W2_Q08: 2 different artifact checksums; W2_Q32: 2 different artifact checksums; W3_d1: 2 different artifact checksums; W3_d3: 2 different artifact checksums; W4_Q08: 2 different artifact checksums; W4_Q32: 2 different artifact checksums. A speed-up with a different result is not a speed-up.

## Secondary metrics

- `compute_p99_ns`: A=1, B=12, C=0
- `compute_sum_ns`: A=0, B=13, C=0
- `e2e_p50_ns`: A=0, B=12, C=1
- `e2e_p999_ns`: A=3, B=10, C=0
- `vmhwm_kb`: A=0, B=13, C=0
- `cpu_ticks`: A=0, B=13, C=0
- `capacity_sum`: A=5, B=8, C=0
- `mat_bytes`: A=0, B=13, C=0
- `mat_mem_bytes`: A=2, B=9, C=0
