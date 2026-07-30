# Badanie 1 -- rodzina W2

- data: 2026-07-30T20:55:59+02:00
- commit kodu: `bb3a5216b952432818b23a26365001fe4f7627f5`
- przebiegow: 180 (plan: 180)
- powtorzen na komorke: 15, slotow na przebieg: 720, scale: 6, f_phi: 90 Hz
- komorki wykluczone przez kalibracje: brak

Metryka konczy sie na emisji do kolejki klienta. Nie jest pelnym application E2E.

## Mediany compute_ns na komorke

```
W2_Q01       ALGSTRUCT    n=15 mediana=    136008 ns
W2_Q01       OFF          n=15 mediana=    141100 ns
W2_Q01       STRUCT       n=15 mediana=    140942 ns
W2_Q01       STRUCT_R1    n=15 mediana=    134878 ns
W2_Q08       ALGSTRUCT    n=15 mediana=    639300 ns
W2_Q08       OFF          n=15 mediana=    610708 ns
W2_Q08       STRUCT       n=15 mediana=    612238 ns
W2_Q08       STRUCT_R1    n=15 mediana=    633231 ns
W2_Q32       ALGSTRUCT    n=15 mediana=   2414586 ns
W2_Q32       OFF          n=15 mediana=   2460327 ns
W2_Q32       STRUCT       n=15 mediana=   2448761 ns
W2_Q32       STRUCT_R1    n=15 mediana=   2389592 ns
```
