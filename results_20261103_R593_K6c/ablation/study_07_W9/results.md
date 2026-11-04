# Badanie 7 -- rodzina W9

- data: 2026-11-03T19:04:18+01:00
- commit kodu: `dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb`
- przebiegow: 120 (plan: 120)
- powtorzen na komorke: 15, scale: 12, f_phi generatora: 180 Hz
- budzet slotow per komorka (slot z silnika): W9_Q08=960 slotow@120 Hz; W9_Q32=960 slotow@120 Hz
- komorki wykluczone przez kalibracje: brak
- komorki wykluczone decyzja: brak

Metryka konczy sie na emisji do kolejki klienta. Nie jest pelnym application E2E.

## Mediany compute_ns na komorke

```
W9_Q08       ALGSTRUCT    n=15 mediana=    558852 ns
W9_Q08       OFF          n=15 mediana=    531551 ns
W9_Q08       STRUCT       n=15 mediana=    616921 ns
W9_Q08       STRUCT_R2    n=15 mediana=    560319 ns
W9_Q32       ALGSTRUCT    n=15 mediana=   2038748 ns
W9_Q32       OFF          n=15 mediana=   2090474 ns
W9_Q32       STRUCT       n=15 mediana=   2073551 ns
W9_Q32       STRUCT_R2    n=15 mediana=   2023755 ns
```
