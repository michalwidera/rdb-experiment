# Wyniki badania 1 -- kampania rate_r593k18

- data: 2026-11-04T10:06:14+01:00
- commit kodu: `dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb`
- częstosc naplywu: 360 Hz
- liczba klientow xqry: 1 (sink=null)
- liczba probek: 20000

## Compute, wake-up i queue-emission latency

```
plik           : /dev/shm/rdb-experiment/results_20261104_R593_K18_rate_r593k18_study_1/e1_probe.csv
interwałów (N) : 19999
--- E1: rdzeń obliczeń (processRows) ---
mediana        : 885.7 us
p99            : 1105.6 us
max            : 1303.0 us
budżet (1/360s): 2777.8 us
max / budżet   : 46.9 %   (MIEŚCI SIĘ)
przepustowość  : 1,139 próbek/s (unpaced)
--- E2E: krotka wejściowa -> emisja wyniku (deadline -> boradcast) ---
mediana        : 937.2 us
p99            : 1211.1 us
p99,9          : 1291.4 us
max            : 1420.3 us
max / budżet   : 51.1 %   (MIEŚCI SIĘ)
--- jitter pobudki (wake_lag) ---
mediana        : 22.2 us
p99            : 30.8 us
p99,9          : 37.9 us
max            : 71.2 us
```

Metryka kończy się na emisji do kolejki klienta. Nie jest pełnym application E2E.

## Metryki systemowe

```
srednie load1=1.32 mem_used_kb=299491 temp_mC=32200
```
