# Badanie 5 -- rodzina W7

- data: 2026-07-31T12:26:39+02:00
- commit kodu: `e1e5181141f96965da4a092f7e7191f8cb0b2748`
- przebiegow: 60 (plan: 60)
- powtorzen na komorke: 15, scale: 6, f_phi generatora: 90 Hz
- budzet slotow per komorka (slot z silnika): W7_Q32=720 slotow@90 Hz
- komorki wykluczone przez kalibracje: brak

Metryka konczy sie na emisji do kolejki klienta. Nie jest pelnym application E2E.

## Mediany compute_ns na komorke

```
W7_Q32       ALGSTRUCT    n=15 mediana=   3066577 ns
W7_Q32       OFF          n=15 mediana=   3035352 ns
W7_Q32       STRUCT       n=15 mediana=   3047440 ns
W7_Q32       STRUCT_R1    n=15 mediana=   3041529 ns
```
