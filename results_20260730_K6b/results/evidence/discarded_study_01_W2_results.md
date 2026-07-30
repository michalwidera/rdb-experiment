# Badanie 1 -- rodzina W2

- data: 2026-07-30T20:04:26+02:00
- commit kodu: `bb3a5216b952432818b23a26365001fe4f7627f5`
- przebiegow: 180 (plan: 180)
- powtorzen na komorke: 15, slotow na przebieg: 720, scale: 6, f_phi: 90 Hz
- komorki wykluczone przez kalibracje: brak

Metryka konczy sie na emisji do kolejki klienta. Nie jest pelnym application E2E.

## Mediany compute_ns na komorke

```
W2_Q01       ALGSTRUCT    n=15 mediana=    137331 ns
W2_Q01       OFF          n=15 mediana=    143794 ns
W2_Q01       STRUCT       n=15 mediana=    144146 ns
W2_Q01       STRUCT_R1    n=15 mediana=    137498 ns
W2_Q08       ALGSTRUCT    n=15 mediana=    651826 ns
W2_Q08       OFF          n=15 mediana=    623206 ns
W2_Q08       STRUCT       n=15 mediana=    622669 ns
W2_Q08       STRUCT_R1    n=15 mediana=    642429 ns
W2_Q32       ALGSTRUCT    n=15 mediana=   2451818 ns
W2_Q32       OFF          n=15 mediana=   2492391 ns
W2_Q32       STRUCT       n=15 mediana=   2485491 ns
W2_Q32       STRUCT_R1    n=15 mediana=   2430243 ns
```
