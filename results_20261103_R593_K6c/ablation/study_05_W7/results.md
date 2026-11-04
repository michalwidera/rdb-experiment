# Badanie 5 -- rodzina W7

- data: 2026-11-03T18:01:55+01:00
- commit kodu: `dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb`
- przebiegow: 60 (plan: 60)
- powtorzen na komorke: 15, scale: 6, f_phi generatora: 90 Hz
- budzet slotow per komorka (slot z silnika): W7_Q32=720 slotow@90 Hz
- komorki wykluczone przez kalibracje: brak
- komorki wykluczone decyzja: brak

Metryka konczy sie na emisji do kolejki klienta. Nie jest pelnym application E2E.

## Mediany compute_ns na komorke

```
W7_Q32       ALGSTRUCT    n=15 mediana=   1957197 ns
W7_Q32       OFF          n=15 mediana=   1963951 ns
W7_Q32       STRUCT       n=15 mediana=   1960855 ns
W7_Q32       STRUCT_R1    n=15 mediana=   1971697 ns
```
