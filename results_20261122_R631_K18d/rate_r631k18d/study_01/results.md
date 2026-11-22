# Wyniki badania 1 -- kampania rate_r631k18d

- data: 2026-11-22T08:36:31+01:00
- commit kodu: `758be53b3b8339d176dc678f9a75a259b8926925`
- częstosc naplywu: 360 Hz
- liczba klientow xqry: 1 (sink=null)
- liczba probek: 20000

## Compute, wake-up i queue-emission latency

```
plik           : /dev/shm/rdb-experiment/results_20261122_R631_K18d_rate_r631k18d_study_1/e1_probe.csv
interwałów (N) : 19999
--- E1: rdzeń obliczeń (processRows) ---
mediana        : 870.6 us
p99            : 1075.7 us
max            : 1257.0 us
budżet (1/360s): 2777.8 us
max / budżet   : 45.3 %   (MIEŚCI SIĘ)
przepustowość  : 1,139 próbek/s (unpaced)
--- E2E: krotka wejściowa -> emisja wyniku (deadline -> boradcast) ---
mediana        : 925.6 us
p99            : 1177.7 us
p99,9          : 1240.5 us
max            : 1372.4 us
max / budżet   : 49.4 %   (MIEŚCI SIĘ)
--- jitter pobudki (wake_lag) ---
mediana        : 22.7 us
p99            : 30.7 us
p99,9          : 36.9 us
max            : 73.6 us
```

Metryka kończy się na emisji do kolejki klienta. Nie jest pełnym application E2E.

## Metryki systemowe

```
srednie load1=0.51 mem_used_kb=342506 temp_mC=31025
```
