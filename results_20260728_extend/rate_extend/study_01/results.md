# Wyniki badania 1 -- kampania rate_extend

- data: 2026-07-28T21:00:04+02:00
- commit kodu: `3db781711a84c08ce794c3924aab533dba6fcbd1`
- częstosc naplywu: 360 Hz
- liczba klientow xqry: 1 (sink=null)
- liczba probek: 20000

## Compute, wake-up i queue-emission latency

```
plik           : /dev/shm/rdb-experiment/results_20260728_extend_rate_extend_study_1/e1_probe.csv
interwałów (N) : 19999
--- E1: rdzeń obliczeń (processRows) ---
mediana        : 1292.8 us
p99            : 1598.8 us
max            : 1816.5 us
budżet (1/360s): 2777.8 us
max / budżet   : 65.4 %   (MIEŚCI SIĘ)
przepustowość  : 757 próbek/s (unpaced)
--- E2E: krotka wejściowa -> emisja wyniku (deadline -> boradcast) ---
mediana        : 1352.7 us
p99            : 1697.9 us
p99,9          : 1803.3 us
max            : 1976.6 us
max / budżet   : 71.2 %   (MIEŚCI SIĘ)
--- jitter pobudki (wake_lag) ---
mediana        : 20.9 us
p99            : 29.0 us
p99,9          : 37.0 us
max            : 73.1 us
```

Metryka kończy się na emisji do kolejki klienta. Nie jest pełnym application E2E.

## Metryki systemowe

```
srednie load1=2.55 mem_used_kb=307316 temp_mC=39240
```
