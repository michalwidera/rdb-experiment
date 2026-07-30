# Badanie 7 -- rodzina W9

- data: 2026-07-31T21:02:34+02:00
- commit kodu: `1bb2d2ce8bec35cd0ab46d168249b706ccbaf303`
- przebiegow: 120 (plan: 120)
- powtorzen na komorke: 15, scale: 12, f_phi generatora: 180 Hz
- budzet slotow per komorka (slot z silnika): W9_Q08=960 slotow@120 Hz; W9_Q32=960 slotow@120 Hz
- komorki wykluczone przez kalibracje: brak
- komorki wykluczone decyzja: brak

Metryka konczy sie na emisji do kolejki klienta. Nie jest pelnym application E2E.

## Mediany compute_ns na komorke

```
W9_Q08       ALGSTRUCT    n=15 mediana=    817418 ns
W9_Q08       OFF          n=15 mediana=    827121 ns
W9_Q08       STRUCT       n=15 mediana=    894927 ns
W9_Q08       STRUCT_R2    n=15 mediana=    815529 ns
W9_Q32       ALGSTRUCT    n=15 mediana=   2969633 ns
W9_Q32       OFF          n=15 mediana=   3264763 ns
W9_Q32       STRUCT       n=15 mediana=   3077531 ns
W9_Q32       STRUCT_R2    n=15 mediana=   2969791 ns
```
