# Badanie 6 -- rodzina W8

- data: 2026-07-31T20:15:24+02:00
- commit kodu: `1bb2d2ce8bec35cd0ab46d168249b706ccbaf303`
- przebiegow: 120 (plan: 120)
- powtorzen na komorke: 15, scale: 6, f_phi generatora: 90 Hz
- budzet slotow per komorka (slot z silnika): W8_Q01=5760 slotow@720 Hz; W8_Q08=5760 slotow@720 Hz; W8_Q32=5760 slotow@720 Hz
- komorki wykluczone przez kalibracje: brak
- komorki wykluczone decyzja: W8_Q32

Metryka konczy sie na emisji do kolejki klienta. Nie jest pelnym application E2E.

## Mediany compute_ns na komorke

```
W8_Q01       ALGSTRUCT    n=15 mediana=    517301 ns
W8_Q01       OFF          n=15 mediana=    513920 ns
W8_Q01       STRUCT       n=15 mediana=    519557 ns
W8_Q01       STRUCT_R1    n=15 mediana=    523356 ns
W8_Q08       ALGSTRUCT    n=15 mediana=   1049659 ns
W8_Q08       OFF          n=15 mediana=   1049508 ns
W8_Q08       STRUCT       n=15 mediana=   1060768 ns
W8_Q08       STRUCT_R1    n=15 mediana=   1056398 ns
```
