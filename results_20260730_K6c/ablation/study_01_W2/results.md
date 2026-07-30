# Badanie 1 -- rodzina W2

- data: 2026-07-31T10:51:56+02:00
- commit kodu: `e1e5181141f96965da4a092f7e7191f8cb0b2748`
- przebiegow: 180 (plan: 180)
- powtorzen na komorke: 15, scale: 12, f_phi generatora: 180 Hz
- budzet slotow per komorka (slot z silnika): W2_Q01=1440 slotow@180 Hz; W2_Q08=1440 slotow@180 Hz; W2_Q32=1440 slotow@180 Hz
- komorki wykluczone przez kalibracje: brak

Metryka konczy sie na emisji do kolejki klienta. Nie jest pelnym application E2E.

## Mediany compute_ns na komorke

```
W2_Q01       ALGSTRUCT    n=15 mediana=    133212 ns
W2_Q01       OFF          n=15 mediana=    124832 ns
W2_Q01       STRUCT       n=15 mediana=    125239 ns
W2_Q01       STRUCT_R1    n=15 mediana=    132073 ns
W2_Q08       ALGSTRUCT    n=15 mediana=    642985 ns
W2_Q08       OFF          n=15 mediana=    606661 ns
W2_Q08       STRUCT       n=15 mediana=    606253 ns
W2_Q08       STRUCT_R1    n=15 mediana=    635216 ns
W2_Q32       ALGSTRUCT    n=15 mediana=   2437133 ns
W2_Q32       OFF          n=15 mediana=   2461262 ns
W2_Q32       STRUCT       n=15 mediana=   2458344 ns
W2_Q32       STRUCT_R1    n=15 mediana=   2414179 ns
```
