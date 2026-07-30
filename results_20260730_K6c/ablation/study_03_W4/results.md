# Badanie 3 -- rodzina W4

- data: 2026-07-31T12:03:20+02:00
- commit kodu: `e1e5181141f96965da4a092f7e7191f8cb0b2748`
- przebiegow: 120 (plan: 120)
- powtorzen na komorke: 15, scale: 1, f_phi generatora: 15 Hz
- budzet slotow per komorka (slot z silnika): W4_Q08=400 slotow@15 Hz; W4_Q32=400 slotow@15 Hz
- komorki wykluczone przez kalibracje: brak

Metryka konczy sie na emisji do kolejki klienta. Nie jest pelnym application E2E.

## Mediany compute_ns na komorke

```
W4_Q08       ALGSTRUCT    n=15 mediana=   8109229 ns
W4_Q08       OFF          n=15 mediana=   7968535 ns
W4_Q08       STRUCT       n=15 mediana=   8089013 ns
W4_Q08       STRUCT_R1    n=15 mediana=   8119793 ns
W4_Q32       ALGSTRUCT    n=15 mediana=  32452387 ns
W4_Q32       OFF          n=15 mediana=  31983780 ns
W4_Q32       STRUCT       n=15 mediana=  32512895 ns
W4_Q32       STRUCT_R1    n=15 mediana=  32456892 ns
```
