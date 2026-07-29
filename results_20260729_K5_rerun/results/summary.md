# Wynik K5 — punkt go/no-go

**Werdykt: GO**

- commit kodu: `2a5aa86148cc4e76ccc0adb8f3e2fa9f450b9123`
- przypadków: 40, profili: 5
- wykluczonych z reguły: 0

## Warunki reguły decyzyjnej

| Warunek | Treść | Wynik |
|---|---|---|
| (a) | istnieje `(w,Q)` z `net < 0` | spełniony (22 przypadków) |
| (b) | każdy taki przypadek bajtowo identyczny | spełniony |
| (c) | `net = 0` w W5, W6, W7 | spełniony |
| kwalifikator | redukcja w rodzinie umotywowanej zewnętrznie (W8) | tak |

## Porównanie STRUCT → ALGSTRUCT

`net` to zmiana liczby węzłów planu wyjściowego. Kolumny tokenów pochodzą
z `PLAN bench` w punkcie wyjścia kompilatora.

| Rodzina | Przypadek | Parametr | Węzły STRUCT | Węzły ALGSTRUCT | net | tokeny-from | tokeny-pól | r1 | r2 |
|---|---|---|---:|---:|---:|---|---|---:|---:|
| W1 | `W1` | - | 5 | 4 | -1 | 7 → 5 | 3 → 2 | 1 | 0 |
| W2 | `W2_Q01` | Q=1 | 5 | 4 | -1 | 7 → 5 | 3 → 2 | 1 | 0 |
| W2 | `W2_Q02` | Q=2 | 6 | 5 | -1 | 10 → 7 | 4 → 3 | 2 | 0 |
| W2 | `W2_Q04` | Q=4 | 8 | 7 | -1 | 16 → 11 | 6 → 5 | 4 | 0 |
| W2 | `W2_Q08` | Q=8 | 12 | 11 | -1 | 28 → 19 | 10 → 9 | 8 | 0 |
| W2 | `W2_Q16` | Q=16 | 20 | 19 | -1 | 52 → 35 | 18 → 17 | 16 | 0 |
| W2 | `W2_Q32` | Q=32 | 36 | 35 | -1 | 100 → 67 | 34 → 33 | 32 | 0 |
| W3 | `W3_d1` | d=1 | 12 | 11 | -1 | 28 → 19 | 10 → 9 | 8 | 0 |
| W3 | `W3_d2` | d=2 | 16 | 14 | -2 | 35 → 24 | 13 → 11 | 9 | 0 |
| W3 | `W3_d3` | d=3 | 20 | 17 | -3 | 42 → 29 | 16 → 13 | 10 | 0 |
| W4 | `W4_Q01` | Q=1 | 8 | 7 | -1 | 12 → 10 | 35 → 34 | 1 | 0 |
| W4 | `W4_Q02` | Q=2 | 12 | 11 | -1 | 20 → 17 | 68 → 67 | 2 | 0 |
| W4 | `W4_Q04` | Q=4 | 20 | 19 | -1 | 36 → 31 | 134 → 133 | 4 | 0 |
| W4 | `W4_Q08` | Q=8 | 36 | 35 | -1 | 68 → 59 | 266 → 265 | 8 | 0 |
| W4 | `W4_Q16` | Q=16 | 68 | 67 | -1 | 132 → 115 | 530 → 529 | 16 | 0 |
| W4 | `W4_Q32` | Q=32 | 132 | 131 | -1 | 260 → 227 | 1058 → 1057 | 32 | 0 |
| W5 | `W5_Q01` | Q=1 | 3 | 3 | 0 | 3 → 3 | 1 → 1 | 0 | 0 |
| W5 | `W5_Q02` | Q=2 | 6 | 6 | 0 | 6 → 6 | 2 → 2 | 0 | 0 |
| W5 | `W5_Q04` | Q=4 | 12 | 12 | 0 | 12 → 12 | 4 → 4 | 0 | 0 |
| W5 | `W5_Q08` | Q=8 | 24 | 24 | 0 | 24 → 24 | 8 → 8 | 0 | 0 |
| W5 | `W5_Q16` | Q=16 | 48 | 48 | 0 | 48 → 48 | 16 → 16 | 0 | 0 |
| W5 | `W5_Q32` | Q=32 | 96 | 96 | 0 | 96 → 96 | 32 → 32 | 0 | 0 |
| W6 | `W6_Q01` | Q=1 | 5 | 5 | 0 | 7 → 7 | 3 → 3 | 0 | 0 |
| W6 | `W6_Q02` | Q=2 | 6 | 6 | 0 | 10 → 10 | 4 → 4 | 0 | 0 |
| W6 | `W6_Q04` | Q=4 | 8 | 8 | 0 | 16 → 16 | 6 → 6 | 0 | 0 |
| W6 | `W6_Q08` | Q=8 | 12 | 12 | 0 | 28 → 28 | 10 → 10 | 0 | 0 |
| W6 | `W6_Q16` | Q=16 | 20 | 20 | 0 | 52 → 52 | 18 → 18 | 0 | 0 |
| W6 | `W6_Q32` | Q=32 | 36 | 36 | 0 | 100 → 100 | 34 → 34 | 0 | 0 |
| W7 | `W7_Q01` | Q=1 | 5 | 5 | 0 | 7 → 7 | 3 → 3 | 0 | 0 |
| W7 | `W7_Q02` | Q=2 | 6 | 6 | 0 | 10 → 10 | 4 → 4 | 0 | 0 |
| W7 | `W7_Q04` | Q=4 | 8 | 8 | 0 | 16 → 16 | 6 → 6 | 0 | 0 |
| W7 | `W7_Q08` | Q=8 | 12 | 12 | 0 | 28 → 28 | 10 → 10 | 0 | 0 |
| W7 | `W7_Q16` | Q=16 | 20 | 20 | 0 | 52 → 52 | 18 → 18 | 0 | 0 |
| W7 | `W7_Q32` | Q=32 | 36 | 36 | 0 | 100 → 100 | 34 → 34 | 0 | 0 |
| W8 | `W8_Q01` | Q=1 | 16 | 15 | -1 | 27 → 25 | 164 → 163 | 1 | 1 |
| W8 | `W8_Q02` | Q=2 | 17 | 16 | -1 | 30 → 27 | 165 → 164 | 2 | 1 |
| W8 | `W8_Q04` | Q=4 | 19 | 18 | -1 | 36 → 31 | 167 → 166 | 4 | 1 |
| W8 | `W8_Q08` | Q=8 | 23 | 22 | -1 | 48 → 39 | 171 → 170 | 8 | 1 |
| W8 | `W8_Q16` | Q=16 | 31 | 30 | -1 | 72 → 55 | 179 → 178 | 16 | 1 |
| W8 | `W8_Q32` | Q=32 | 47 | 46 | -1 | 120 → 87 | 195 → 194 | 32 | 1 |

## Usunięte węzły

Imienna lista wymagana przez warunek (a).

- `W1` (net -1) — usunięte: `STREAM_TIMEMOVE_A`, `STREAM_TIMEMOVE_B`; dodane: `STREAM_HASH_A_B`
- `W2_Q01` (net -1) — usunięte: `STREAM_TIMEMOVE_A`, `STREAM_TIMEMOVE_B`; dodane: `STREAM_HASH_A_B`
- `W2_Q02` (net -1) — usunięte: `STREAM_TIMEMOVE_A`, `STREAM_TIMEMOVE_B`; dodane: `STREAM_HASH_A_B`
- `W2_Q04` (net -1) — usunięte: `STREAM_TIMEMOVE_A`, `STREAM_TIMEMOVE_B`; dodane: `STREAM_HASH_A_B`
- `W2_Q08` (net -1) — usunięte: `STREAM_TIMEMOVE_A`, `STREAM_TIMEMOVE_B`; dodane: `STREAM_HASH_A_B`
- `W2_Q16` (net -1) — usunięte: `STREAM_TIMEMOVE_A`, `STREAM_TIMEMOVE_B`; dodane: `STREAM_HASH_A_B`
- `W2_Q32` (net -1) — usunięte: `STREAM_TIMEMOVE_A`, `STREAM_TIMEMOVE_B`; dodane: `STREAM_HASH_A_B`
- `W3_d1` (net -1) — usunięte: `STREAM_TIMEMOVE_A`, `STREAM_TIMEMOVE_B`; dodane: `STREAM_HASH_A_B`
- `W3_d2` (net -2) — usunięte: `STREAM_TIMEMOVE_A`, `STREAM_TIMEMOVE_B`, `STREAM_TIMEMOVE_S1`, `STREAM_TIMEMOVE_STREAM_HASH_STREAM_TIMEMOVE_A_STREAM_TIMEMOVE_B`; dodane: `STREAM_HASH_A_B`, `STREAM_HASH_STREAM_HASH_STREAM_TIMEMOVE_A_STREAM_TIMEMOVE_B_S1`
- `W3_d3` (net -3) — usunięte: `STREAM_TIMEMOVE_A`, `STREAM_TIMEMOVE_B`, `STREAM_TIMEMOVE_S1`, `STREAM_TIMEMOVE_S2`, `STREAM_TIMEMOVE_STREAM_HASH_STREAM_TIMEMOVE_A_STREAM_TIMEMOVE_B`, `STREAM_TIMEMOVE_STREAM_HASH_STREAM_TIMEMOVE_STREAM_HASH_STREAM_TIMEMOVE_A_STREAM_TIMEMOVE_B_STREAM_TIMEMOVE_S1`; dodane: `STREAM_HASH_A_B`, `STREAM_HASH_STREAM_HASH_STREAM_TIMEMOVE_A_STREAM_TIMEMOVE_B_S1`, `STREAM_HASH_STREAM_HASH_STREAM_TIMEMOVE_STREAM_HASH_STREAM_TIMEMOVE_A_STREAM_TIMEMOVE_B_STREAM_TIMEMOVE_S1_S2`
- `W4_Q01` (net -1) — usunięte: `STREAM_TIMEMOVE_A`, `STREAM_TIMEMOVE_B`; dodane: `STREAM_HASH_A_B`
- `W4_Q02` (net -1) — usunięte: `STREAM_TIMEMOVE_A`, `STREAM_TIMEMOVE_B`; dodane: `STREAM_HASH_A_B`
- `W4_Q04` (net -1) — usunięte: `STREAM_TIMEMOVE_A`, `STREAM_TIMEMOVE_B`; dodane: `STREAM_HASH_A_B`
- `W4_Q08` (net -1) — usunięte: `STREAM_TIMEMOVE_A`, `STREAM_TIMEMOVE_B`; dodane: `STREAM_HASH_A_B`
- `W4_Q16` (net -1) — usunięte: `STREAM_TIMEMOVE_A`, `STREAM_TIMEMOVE_B`; dodane: `STREAM_HASH_A_B`
- `W4_Q32` (net -1) — usunięte: `STREAM_TIMEMOVE_A`, `STREAM_TIMEMOVE_B`; dodane: `STREAM_HASH_A_B`
- `W8_Q01` (net -1) — usunięte: `STREAM_TIMEMOVE_mlii`, `STREAM_TIMEMOVE_mwi`; dodane: `STREAM_HASH_mlii_mwi`
- `W8_Q02` (net -1) — usunięte: `STREAM_TIMEMOVE_mlii`, `STREAM_TIMEMOVE_mwi`; dodane: `STREAM_HASH_mlii_mwi`
- `W8_Q04` (net -1) — usunięte: `STREAM_TIMEMOVE_mlii`, `STREAM_TIMEMOVE_mwi`; dodane: `STREAM_HASH_mlii_mwi`
- `W8_Q08` (net -1) — usunięte: `STREAM_TIMEMOVE_mlii`, `STREAM_TIMEMOVE_mwi`; dodane: `STREAM_HASH_mlii_mwi`
- `W8_Q16` (net -1) — usunięte: `STREAM_TIMEMOVE_mlii`, `STREAM_TIMEMOVE_mwi`; dodane: `STREAM_HASH_mlii_mwi`
- `W8_Q32` (net -1) — usunięte: `STREAM_TIMEMOVE_mlii`, `STREAM_TIMEMOVE_mwi`; dodane: `STREAM_HASH_mlii_mwi`

## Skalowanie z Q (luka G6)

Raportowane, ale **nieuwzględniane** w regule decyzyjnej.

- **W2** — net: Q=1: -1, Q=2: -1, Q=4: -1, Q=8: -1, Q=16: -1, Q=32: -1
  - oszczędność tokenów FROM: Q=1: 2, Q=2: 3, Q=4: 5, Q=8: 9, Q=16: 17, Q=32: 33
- **W4** — net: Q=1: -1, Q=2: -1, Q=4: -1, Q=8: -1, Q=16: -1, Q=32: -1
  - oszczędność tokenów FROM: Q=1: 2, Q=2: 3, Q=4: 5, Q=8: 9, Q=16: 17, Q=32: 33
- **W5** — net: Q=1: 0, Q=2: 0, Q=4: 0, Q=8: 0, Q=16: 0, Q=32: 0
  - oszczędność tokenów FROM: Q=1: 0, Q=2: 0, Q=4: 0, Q=8: 0, Q=16: 0, Q=32: 0
- **W6** — net: Q=1: 0, Q=2: 0, Q=4: 0, Q=8: 0, Q=16: 0, Q=32: 0
  - oszczędność tokenów FROM: Q=1: 0, Q=2: 0, Q=4: 0, Q=8: 0, Q=16: 0, Q=32: 0
- **W7** — net: Q=1: 0, Q=2: 0, Q=4: 0, Q=8: 0, Q=16: 0, Q=32: 0
  - oszczędność tokenów FROM: Q=1: 0, Q=2: 0, Q=4: 0, Q=8: 0, Q=16: 0, Q=32: 0
- **W8** — net: Q=1: -1, Q=2: -1, Q=4: -1, Q=8: -1, Q=16: -1, Q=32: -1
  - oszczędność tokenów FROM: Q=1: 2, Q=2: 3, Q=4: 5, Q=8: 9, Q=16: 17, Q=32: 33
- **W3** (Q stałe, zmienna głębokość) — net: d=1: -1, d=2: -2, d=3: -3
  - oszczędność tokenów FROM: d=1: 9, d=2: 11, d=3: 13

## Kontrola semantyczna

Porównywane są artefakty strumieni nazwanych przez użytkownika. Substraty
są pominięte — ich nazwy zmienia sama badana reguła.

| Przypadek | Cykli | Artefaktów publicznych | Wynik zachowany |
|---|---:|---:|---|
| `W1` | 200 | 6 | tak |
| `W2_Q01` | 200 | 6 | tak |
| `W2_Q02` | 200 | 10 | tak |
| `W2_Q04` | 200 | 18 | tak |
| `W2_Q08` | 200 | 34 | tak |
| `W2_Q16` | 200 | 66 | tak |
| `W2_Q32` | 200 | 130 | tak |
| `W3_d1` | 200 | 34 | tak |
| `W3_d2` | 200 | 35 | tak |
| `W3_d3` | 200 | 36 | tak |
| `W4_Q01` | 200 | 18 | tak |
| `W4_Q02` | 200 | 34 | tak |
| `W4_Q04` | 200 | 66 | tak |
| `W4_Q08` | 200 | 130 | tak |
| `W4_Q16` | 200 | 258 | tak |
| `W4_Q32` | 200 | 514 | tak |
| `W8_Q01` | 600 | 27 | tak |
| `W8_Q02` | 600 | 31 | tak |
| `W8_Q04` | 600 | 39 | tak |
| `W8_Q08` | 600 | 55 | tak |
| `W8_Q16` | 600 | 87 | tak |
| `W8_Q32` | 600 | 151 | tak |
| `W5_Q01` | 200 | 6 | tak |
| `W6_Q01` | 200 | 6 | tak |
| `W7_Q01` | 200 | 14 | tak |

### Dozwolone zmiany pojemności (RETMEMORY)

Punkt 4 definicji warunku (b) wymaga wypisania ich imiennie.

- `W8_Q01` — mlii.desc: RETMEMORY 30 → 63
- `W8_Q01` — mwi.desc: RETMEMORY 30 → 4
- `W8_Q02` — mlii.desc: RETMEMORY 30 → 63
- `W8_Q02` — mwi.desc: RETMEMORY 30 → 4
- `W8_Q04` — mlii.desc: RETMEMORY 30 → 63
- `W8_Q04` — mwi.desc: RETMEMORY 30 → 4
- `W8_Q08` — mlii.desc: RETMEMORY 30 → 63
- `W8_Q08` — mwi.desc: RETMEMORY 30 → 4
- `W8_Q16` — mlii.desc: RETMEMORY 30 → 63
- `W8_Q16` — mwi.desc: RETMEMORY 30 → 4
- `W8_Q32` — mlii.desc: RETMEMORY 30 → 63
- `W8_Q32` — mwi.desc: RETMEMORY 30 → 4

## Atrybucja profili

Liczba węzłów planu wyjściowego w każdym profilu.

| Przypadek | OFF | STRUCT | STRUCT+R1 | STRUCT+R2 | ALGSTRUCT |
|---|---:|---:|---:|---:|---:|
| `W1` | 5 | 5 | 4 | 5 | 4 |
| `W2_Q01` | 5 | 5 | 4 | 5 | 4 |
| `W2_Q02` | 6 | 6 | 5 | 6 | 5 |
| `W2_Q04` | 8 | 8 | 7 | 8 | 7 |
| `W2_Q08` | 12 | 12 | 11 | 12 | 11 |
| `W2_Q16` | 20 | 20 | 19 | 20 | 19 |
| `W2_Q32` | 36 | 36 | 35 | 36 | 35 |
| `W3_d1` | 12 | 12 | 11 | 12 | 11 |
| `W3_d2` | 16 | 16 | 14 | 16 | 14 |
| `W3_d3` | 20 | 20 | 17 | 20 | 17 |
| `W4_Q01` | 8 | 8 | 7 | 8 | 7 |
| `W4_Q02` | 12 | 12 | 11 | 12 | 11 |
| `W4_Q04` | 20 | 20 | 19 | 20 | 19 |
| `W4_Q08` | 36 | 36 | 35 | 36 | 35 |
| `W4_Q16` | 68 | 68 | 67 | 68 | 67 |
| `W4_Q32` | 132 | 132 | 131 | 132 | 131 |
| `W5_Q01` | 3 | 3 | 3 | 3 | 3 |
| `W5_Q02` | 6 | 6 | 6 | 6 | 6 |
| `W5_Q04` | 12 | 12 | 12 | 12 | 12 |
| `W5_Q08` | 24 | 24 | 24 | 24 | 24 |
| `W5_Q16` | 48 | 48 | 48 | 48 | 48 |
| `W5_Q32` | 96 | 96 | 96 | 96 | 96 |
| `W6_Q01` | 5 | 5 | 5 | 5 | 5 |
| `W6_Q02` | 6 | 6 | 6 | 6 | 6 |
| `W6_Q04` | 8 | 8 | 8 | 8 | 8 |
| `W6_Q08` | 12 | 12 | 12 | 12 | 12 |
| `W6_Q16` | 20 | 20 | 20 | 20 | 20 |
| `W6_Q32` | 36 | 36 | 36 | 36 | 36 |
| `W7_Q01` | 5 | 5 | 5 | 5 | 5 |
| `W7_Q02` | 6 | 6 | 6 | 6 | 6 |
| `W7_Q04` | 8 | 8 | 8 | 8 | 8 |
| `W7_Q08` | 12 | 12 | 12 | 12 | 12 |
| `W7_Q16` | 20 | 20 | 20 | 20 | 20 |
| `W7_Q32` | 36 | 36 | 36 | 36 | 36 |
| `W8_Q01` | 16 | 16 | 15 | 16 | 15 |
| `W8_Q02` | 17 | 17 | 16 | 17 | 16 |
| `W8_Q04` | 19 | 19 | 18 | 19 | 18 |
| `W8_Q08` | 23 | 23 | 22 | 23 | 22 |
| `W8_Q16` | 31 | 31 | 30 | 31 | 30 |
| `W8_Q32` | 47 | 47 | 46 | 47 | 46 |
