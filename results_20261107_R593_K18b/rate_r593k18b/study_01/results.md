# Wyniki badania 1 -- kampania rate_r593k18b

- data: 2026-11-07T21:14:14+01:00
- commit kodu: `e389edd3596e4b83b6f3f4a9e238905a91c667b4`
- częstosc naplywu: 360 Hz
- liczba klientow xqry: 1 (sink=null)
- liczba probek: 20000

## Compute, wake-up i queue-emission latency

```
plik           : /dev/shm/rdb-experiment/results_20261107_R593_K18b_rate_r593k18b_study_1/e1_probe.csv
interwałów (N) : 19999
--- E1: rdzeń obliczeń (processRows) ---
mediana        : 916.4 us
p99            : 1115.7 us
max            : 1284.8 us
budżet (1/360s): 2777.8 us
max / budżet   : 46.3 %   (MIEŚCI SIĘ)
przepustowość  : 1,106 próbek/s (unpaced)
--- E2E: krotka wejściowa -> emisja wyniku (deadline -> boradcast) ---
mediana        : 970.8 us
p99            : 1215.0 us
p99,9          : 1276.5 us
max            : 1426.1 us
max / budżet   : 51.3 %   (MIEŚCI SIĘ)
--- jitter pobudki (wake_lag) ---
mediana        : 22.3 us
p99            : 30.0 us
p99,9          : 36.0 us
max            : 69.6 us
```

Metryka kończy się na emisji do kolejki klienta. Nie jest pełnym application E2E.

## Metryki systemowe

```
srednie load1=0.65 mem_used_kb=341894 temp_mC=32707
```
