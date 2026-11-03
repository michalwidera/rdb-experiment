# Badanie 3 -- rodzina W4

- data: 2026-11-03T17:43:52+01:00
- commit kodu: `dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb`
- przebiegow: 120 (plan: 120)
- powtorzen na komorke: 15, scale: 1, f_phi generatora: 15 Hz
- budzet slotow per komorka (slot z silnika): W4_Q08=400 slotow@15 Hz; W4_Q32=400 slotow@15 Hz
- komorki wykluczone przez kalibracje: brak
- komorki wykluczone decyzja: brak

Metryka konczy sie na emisji do kolejki klienta. Nie jest pelnym application E2E.

## Mediany compute_ns na komorke

```
W4_Q08       ALGSTRUCT    n=15 mediana=   4616186 ns
W4_Q08       OFF          n=15 mediana=   4606016 ns
W4_Q08       STRUCT       n=15 mediana=   4571860 ns
W4_Q08       STRUCT_R1    n=15 mediana=   4613128 ns
W4_Q32       ALGSTRUCT    n=15 mediana=  18179148 ns
W4_Q32       OFF          n=15 mediana=  18369991 ns
W4_Q32       STRUCT       n=15 mediana=  18160655 ns
W4_Q32       STRUCT_R1    n=15 mediana=  18183743 ns
```
