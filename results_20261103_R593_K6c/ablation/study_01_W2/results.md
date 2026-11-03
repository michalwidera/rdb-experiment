# Badanie 1 -- rodzina W2

- data: 2026-11-03T16:45:24+01:00
- commit kodu: `dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb`
- przebiegow: 180 (plan: 180)
- powtorzen na komorke: 15, scale: 12, f_phi generatora: 180 Hz
- budzet slotow per komorka (slot z silnika): W2_Q01=1440 slotow@180 Hz; W2_Q08=1440 slotow@180 Hz; W2_Q32=1440 slotow@180 Hz
- komorki wykluczone przez kalibracje: brak
- komorki wykluczone decyzja: brak

Metryka konczy sie na emisji do kolejki klienta. Nie jest pelnym application E2E.

## Mediany compute_ns na komorke

```
W2_Q01       ALGSTRUCT    n=15 mediana=     95675 ns
W2_Q01       OFF          n=15 mediana=     92620 ns
W2_Q01       STRUCT       n=15 mediana=     92667 ns
W2_Q01       STRUCT_R1    n=15 mediana=     95537 ns
W2_Q08       ALGSTRUCT    n=15 mediana=    433516 ns
W2_Q08       OFF          n=15 mediana=    405526 ns
W2_Q08       STRUCT       n=15 mediana=    405767 ns
W2_Q08       STRUCT_R1    n=15 mediana=    433748 ns
W2_Q32       ALGSTRUCT    n=15 mediana=   1616549 ns
W2_Q32       OFF          n=15 mediana=   1621900 ns
W2_Q32       STRUCT       n=15 mediana=   1628845 ns
W2_Q32       STRUCT_R1    n=15 mediana=   1620613 ns
```
