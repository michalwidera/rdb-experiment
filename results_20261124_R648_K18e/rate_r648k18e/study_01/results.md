# Wyniki badania 1 -- kampania rate_r648k18e

- data: 2026-11-24T09:05:07+01:00
- commit kodu: `7e5659f4c070b39f1c1a711217fb98548ca60cf4`
- częstosc naplywu: 360 Hz
- liczba klientow xqry: 1 (sink=null)
- liczba probek: 20000

## Compute, wake-up i queue-emission latency

```
plik           : /dev/shm/rdb-experiment/results_20261124_R648_K18e_rate_r648k18e_study_1/e1_probe.csv
interwałów (N) : 19999
--- E1: rdzeń obliczeń (processRows) ---
mediana        : 864.4 us
p99            : 1075.9 us
max            : 1200.3 us
budżet (1/360s): 2777.8 us
max / budżet   : 43.2 %   (MIEŚCI SIĘ)
przepustowość  : 1,145 próbek/s (unpaced)
--- E2E: krotka wejściowa -> emisja wyniku (deadline -> boradcast) ---
mediana        : 919.6 us
p99            : 1182.9 us
p99,9          : 1243.5 us
max            : 1363.7 us
max / budżet   : 49.1 %   (MIEŚCI SIĘ)
--- jitter pobudki (wake_lag) ---
mediana        : 22.7 us
p99            : 33.9 us
p99,9          : 48.4 us
max            : 122.9 us
```

Metryka kończy się na emisji do kolejki klienta. Nie jest pełnym application E2E.

## Metryki systemowe

```
srednie load1=0.57 mem_used_kb=348716 temp_mC=31659
```
