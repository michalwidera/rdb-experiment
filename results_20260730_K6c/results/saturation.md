# K6.5 — punkt saturacji

Zamrożone: `W8_Q32` × STRUCT, ALGSTRUCT × [360, 480, 540] Hz × 5 powtórzeń,
3000 slotów na przebieg. Metryka: udział slotów z `compute_ns > slot`.

Przebiegów: 30.

**Punkt saturacji nie został zlokalizowany — leży poniżej całej siatki.** Każdy
rate w siatce przekracza budżet w obu profilach, więc metryka stoi pod sufitem
i nie różnicuje ani rate'u, ani profilu. Iloczyn `slot · rate` jest w siatce stały
(500·10⁶ ns·Hz); zestawiony z największą medianą `compute_ns`
(2766.05 µs) daje punkt przy ok. 181 Hz źródła — to
ekstrapolacja z pomiarów powyżej saturacji, nie pomiar punktu.

Slot dotyczy strumienia `mon_000` i pochodzi z silnika. Kolumna „wg rate'u”
pokazuje wartość, którą wstawiała v2 — czyli slot źródła, dwukrotnie za długi.

| rate źródła | slot (silnik) | slot wg rate'u | profil | `compute_ns` mediana | przekroczenia mediana | min–max |
|---:|---:|---:|---|---:|---:|---|
| 360 Hz | 1388.89 µs | 2777.78 µs | STRUCT | 2504.75 µs | 98.95% | 98.95–98.95% |
| 360 Hz | 1388.89 µs | 2777.78 µs | ALGSTRUCT | 2572.43 µs | 98.95% | 98.95–98.95% |
| 480 Hz | 1041.67 µs | 2083.33 µs | STRUCT | 2671.59 µs | 98.95% | 98.95–98.95% |
| 480 Hz | 1041.67 µs | 2083.33 µs | ALGSTRUCT | 2766.05 µs | 98.95% | 98.95–98.95% |
| 540 Hz | 925.93 µs | 1851.85 µs | STRUCT | 2554.51 µs | 98.95% | 98.95–98.95% |
| 540 Hz | 925.93 µs | 1851.85 µs | ALGSTRUCT | 2520.41 µs | 98.95% | 98.95–98.95% |

## Odczyt

- 360 Hz: oba profile przekraczają budżet — punkt powyżej saturacji obu
- 480 Hz: oba profile przekraczają budżet — punkt powyżej saturacji obu
- 540 Hz: oba profile przekraczają budżet — punkt powyżej saturacji obu
