# Badanie 2 -- rodzina W3

- data: 2026-11-03T17:00:05+01:00
- commit kodu: `dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb`
- przebiegow: 120 (plan: 120)
- powtorzen na komorke: 15, scale: 12, f_phi generatora: 180 Hz
- budzet slotow per komorka (slot z silnika): W3_d1=1440 slotow@180 Hz; W3_d3=3240 slotow@405 Hz
- komorki wykluczone przez kalibracje: brak
- komorki wykluczone decyzja: brak

Metryka konczy sie na emisji do kolejki klienta. Nie jest pelnym application E2E.

## Mediany compute_ns na komorke

```
W3_d1        ALGSTRUCT    n=15 mediana=    433135 ns
W3_d1        OFF          n=15 mediana=    406247 ns
W3_d1        STRUCT       n=15 mediana=    406227 ns
W3_d1        STRUCT_R1    n=15 mediana=    433626 ns
W3_d3        ALGSTRUCT    n=15 mediana=    441537 ns
W3_d3        OFF          n=15 mediana=    394960 ns
W3_d3        STRUCT       n=15 mediana=    396882 ns
W3_d3        STRUCT_R1    n=15 mediana=    442540 ns
```
