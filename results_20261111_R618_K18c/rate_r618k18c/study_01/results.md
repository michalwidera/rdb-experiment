# Wyniki badania 1 -- kampania rate_r618k18c

- data: 2026-11-11T12:23:27+01:00
- commit kodu: `16c516f9eb76c473d5ff8510a2a812b8c23a893d`
- częstosc naplywu: 360 Hz
- liczba klientow xqry: 1 (sink=null)
- liczba probek: 20000

## Compute, wake-up i queue-emission latency

```
plik           : /dev/shm/rdb-experiment/results_20261111_R618_K18c_rate_r618k18c_study_1/e1_probe.csv
interwałów (N) : 19999
--- E1: rdzeń obliczeń (processRows) ---
mediana        : 851.6 us
p99            : 1064.8 us
max            : 1225.9 us
budżet (1/360s): 2777.8 us
max / budżet   : 44.1 %   (MIEŚCI SIĘ)
przepustowość  : 1,163 próbek/s (unpaced)
--- E2E: krotka wejściowa -> emisja wyniku (deadline -> boradcast) ---
mediana        : 906.6 us
p99            : 1168.8 us
p99,9          : 1229.4 us
max            : 1351.5 us
max / budżet   : 48.7 %   (MIEŚCI SIĘ)
--- jitter pobudki (wake_lag) ---
mediana        : 22.3 us
p99            : 34.7 us
p99,9          : 48.2 us
max            : 106.0 us
```

Metryka kończy się na emisji do kolejki klienta. Nie jest pełnym application E2E.

## Metryki systemowe

```
srednie load1=0.63 mem_used_kb=341456 temp_mC=33690
```
