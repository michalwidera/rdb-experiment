# Badanie 4 -- rodzina W5

- data: 2026-07-31T12:14:59+02:00
- commit kodu: `e1e5181141f96965da4a092f7e7191f8cb0b2748`
- przebiegow: 60 (plan: 60)
- powtorzen na komorke: 15, scale: 12, f_phi generatora: 180 Hz
- budzet slotow per komorka (slot z silnika): W5_Q32=1440 slotow@180 Hz
- komorki wykluczone przez kalibracje: brak

Metryka konczy sie na emisji do kolejki klienta. Nie jest pelnym application E2E.

## Mediany compute_ns na komorke

```
W5_Q32       ALGSTRUCT    n=15 mediana=   2523148 ns
W5_Q32       OFF          n=15 mediana=   2479991 ns
W5_Q32       STRUCT       n=15 mediana=   2476389 ns
W5_Q32       STRUCT_R1    n=15 mediana=   2482788 ns
```
