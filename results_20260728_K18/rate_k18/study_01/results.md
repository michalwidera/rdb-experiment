# Wyniki badania 1 -- kampania rate_k18

- data: 2026-07-28T15:06:54+02:00
- commit kodu: `bc37186ac87cb944d76cf74c7be92706a4a3a87f`
- częstosc naplywu: 360 Hz
- liczba klientow xqry: 1 (sink=null)
- liczba probek: 20000

## Compute, wake-up i queue-emission latency

```
plik           : /dev/shm/rdb-experiment/results_20260728_K18_rate_k18_study_1/e1_probe.csv
interwałów (N) : 19999
--- E1: rdzeń obliczeń (processRows) ---
mediana        : 1312.4 us
p99            : 1617.9 us
max            : 1838.5 us
budżet (1/360s): 2777.8 us
max / budżet   : 66.2 %   (MIEŚCI SIĘ)
przepustowość  : 746 próbek/s (unpaced)
--- E2E: krotka wejściowa -> emisja wyniku (deadline -> boradcast) ---
mediana        : 1372.8 us
p99            : 1718.6 us
p99,9          : 1832.5 us
max            : 1944.0 us
max / budżet   : 70.0 %   (MIEŚCI SIĘ)
--- jitter pobudki (wake_lag) ---
mediana        : 20.7 us
p99            : 27.1 us
p99,9          : 32.7 us
max            : 54.3 us
```

Metryka kończy się na emisji do kolejki klienta. Nie jest pełnym application E2E.

## Metryki systemowe

```
srednie load1=0.63 mem_used_kb=296983 temp_mC=39658
```
