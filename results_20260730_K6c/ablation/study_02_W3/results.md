# Badanie 2 -- rodzina W3

- data: 2026-07-31T11:11:49+02:00
- commit kodu: `e1e5181141f96965da4a092f7e7191f8cb0b2748`
- przebiegow: 120 (plan: 120)
- powtorzen na komorke: 15, scale: 12, f_phi generatora: 180 Hz
- budzet slotow per komorka (slot z silnika): W3_d1=1440 slotow@180 Hz; W3_d3=3240 slotow@405 Hz
- komorki wykluczone przez kalibracje: brak

Metryka konczy sie na emisji do kolejki klienta. Nie jest pelnym application E2E.

## Mediany compute_ns na komorke

```
W3_d1        ALGSTRUCT    n=15 mediana=    636342 ns
W3_d1        OFF          n=15 mediana=    602093 ns
W3_d1        STRUCT       n=15 mediana=    602334 ns
W3_d1        STRUCT_R1    n=15 mediana=    630157 ns
W3_d3        ALGSTRUCT    n=15 mediana=    650584 ns
W3_d3        OFF          n=15 mediana=    588482 ns
W3_d3        STRUCT       n=15 mediana=    589583 ns
W3_d3        STRUCT_R1    n=15 mediana=    642463 ns
```
