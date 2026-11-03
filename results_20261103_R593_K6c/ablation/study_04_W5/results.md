# Badanie 4 -- rodzina W5

- data: 2026-11-03T17:52:58+01:00
- commit kodu: `dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb`
- przebiegow: 60 (plan: 60)
- powtorzen na komorke: 15, scale: 12, f_phi generatora: 180 Hz
- budzet slotow per komorka (slot z silnika): W5_Q32=1440 slotow@180 Hz
- komorki wykluczone przez kalibracje: brak
- komorki wykluczone decyzja: brak

Metryka konczy sie na emisji do kolejki klienta. Nie jest pelnym application E2E.

## Mediany compute_ns na komorke

```
W5_Q32       ALGSTRUCT    n=15 mediana=   1684030 ns
W5_Q32       OFF          n=15 mediana=   1679871 ns
W5_Q32       STRUCT       n=15 mediana=   1685140 ns
W5_Q32       STRUCT_R1    n=15 mediana=   1686417 ns
```
