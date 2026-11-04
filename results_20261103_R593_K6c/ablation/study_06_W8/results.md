# Badanie 6 -- rodzina W8

- data: 2026-11-03T18:43:24+01:00
- commit kodu: `dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb`
- przebiegow: 120 (plan: 120)
- powtorzen na komorke: 15, scale: 6, f_phi generatora: 90 Hz
- budzet slotow per komorka (slot z silnika): W8_Q01=5760 slotow@720 Hz; W8_Q08=5760 slotow@720 Hz; W8_Q32=5760 slotow@720 Hz
- komorki wykluczone przez kalibracje: brak
- komorki wykluczone decyzja: W8_Q32

Metryka konczy sie na emisji do kolejki klienta. Nie jest pelnym application E2E.

## Mediany compute_ns na komorke

```
W8_Q01       ALGSTRUCT    n=15 mediana=    142998 ns
W8_Q01       OFF          n=15 mediana=    141285 ns
W8_Q01       STRUCT       n=15 mediana=    142341 ns
W8_Q01       STRUCT_R1    n=15 mediana=    142536 ns
W8_Q08       ALGSTRUCT    n=15 mediana=    494513 ns
W8_Q08       OFF          n=15 mediana=    455939 ns
W8_Q08       STRUCT       n=15 mediana=    458921 ns
W8_Q08       STRUCT_R1    n=15 mediana=    492994 ns
```
