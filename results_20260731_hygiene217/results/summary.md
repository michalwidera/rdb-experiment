# Werdykt badania higienicznego `1bb2d2c`

Liczony przez `verdict.py` wg kryterium zamrożonego w predeklaracji **przed**
pomiarem. Kryterium ani zestaw komórek nie były zmieniane po starcie.

## Werdykt: **BRAK WPŁYWU**

Metryka główna `compute_ns`, 240 przebiegów, 2 komórki × 2 profile × 2 strony
× 30 powtórzeń. Zero przebiegów z niezerowym kodem klienta, zero niepełnych sond.

| komórka | `r_PRZED` | `r_PO` | `Δ` | `CI95(Δ)` | margines | werdykt |
|---|---:|---:|---:|---|---:|---|
| `W2_Q32` | 0,9970 | 0,9893 | **−0,0077** | (−0,0107; −0,0049) | ±0,02 | BRAK WPŁYWU |
| `W3_d3` | 1,1005 | 1,0879 | **−0,0126** | (−0,0150; −0,0097) | ±0,02 | BRAK WPŁYWU |

Metryka uboczna `e2e_p50_ns`, bez mocy decyzyjnej, potwierdza kierunek i rząd
wielkości: `W2_Q32` Δ = −0,0081 (−0,0108; −0,0047), `W3_d3` Δ = −0,0127
(−0,0156; −0,0093).

## Czego ten werdykt NIE mówi — efekt jest realny, tylko mały

Obie różnice są **ujemne**, a ich przedziały ufności **nie zawierają zera**.
Test równoważności orzeka „brak wpływu" w sensie praktycznym, a nie „brak
różnicy". Różnica istnieje i jest powtarzalna.

Nie jest to też przesunięcie wspólne, które by się skróciło w ilorazie —
profile poszły w **przeciwne strony**:

| komórka | profil | PRZED | PO | zmiana |
|---|---|---:|---:|---:|
| `W2_Q32` | STRUCT | 2386,3 µs | 2396,4 µs | **+0,42 %** |
| `W2_Q32` | ALGSTRUCT | 2379,2 µs | 2370,8 µs | **−0,35 %** |
| `W3_d3` | STRUCT | 588,7 µs | 591,0 µs | **+0,39 %** |
| `W3_d3` | ALGSTRUCT | 647,9 µs | 643,0 µs | **−0,76 %** |

Zaszedł więc dokładnie ten scenariusz, którego predeklaracja się obawiała:
przeniesienie wątku komunikacyjnego dotknęło profili **nierówno**, bo mają one
różne zbiory robocze. Skala jest jednak o rząd wielkości mniejsza od progu
istotności praktycznej kampanii (10 %) i mieści się w marginesie równoważności.

## Znany, skwantyfikowany bias przy zestawianiu rodzin

Skoro `Δ < 0`, to na `1bb2d2c` iloraz `ALGSTRUCT/STRUCT` wychodzi o **0,8–1,3 %
niżej** niż na `e1c13bb`, czyli minimalnie korzystniej dla `ALGSTRUCT`.

W8 i W9 będą mierzone na `1bb2d2c`, a W2–W7 są zmierzone na `e1c13bb`. Przy
zestawianiu rodzin obok siebie należy pamiętać, że różnica do 1,3 punktu
procentowego w ilorazie może pochodzić z aparatury, nie z optymalizatora.
Reguła decyzyjna kampanii operuje progiem 10 %, więc **żadna komórka nie może
przez to zmienić klasy** — i to był powód, dla którego margines ustawiono na
jedną piątą progu.

## Skutek, zapisany w predeklaracji przed pomiarem

**BRAK WPŁYWU → 540 przebiegów Tier B (W2, W3, W4, W5, W7) zostaje ważne.**
Domierzamy W8 (bez `Q32`, wykluczonej jako komórka za punktem saturacji)
oraz W9 na `1bb2d2c`.

## Ograniczenia

Wypisane w predeklaracji, powtórzone tu, żeby werdykt nie był czytany szerzej,
niż na to zasługuje:

- Mierzone komórki mają **najmniejszą ekspozycję** wątku komunikacyjnego
  spośród komórek z duty < 100 % (1,4 i 3,0 pobudki na slot; `W4_Q32` ma 33,6).
  Werdykt `BRAK WPŁYWU` z tego zestawu jest przez to słabszy, niż byłby
  z `W4_Q32`.
- Badanie **nie orzeka o komórkach z duty ≥ 100 %** (`W8_Q32`, `W8_Q08` w p99).
- Badanie **nie zastępuje werdyktu kampanii** i nie wchodzi do tabel artykułu.

## Warunki pomiaru

Governor `performance` (jak w kampanii), silnik `taskset -c 3` na izolowanym
rdzeniu, klient `taskset -c 0-2`, `rt_priority = 50`, klient **stały**
(`e1c13bb`) po obu stronach. Przeplot stron co powtórzenie zamiast reboota.
W trakcie pomiaru dołożono chłodzenie workera — sprawdzone, bez śladu w danych
(`get_throttled = 0x0`, bity trwałe zerowe, rdzeń 1,8 GHz przez cały czas).

Dowody: `evidence.tar.gz` (9 plików, `--build-info` czterech binarek, sumy
SHA-256 binarek, logi budowy i pomiaru, stan maszyny po pomiarze), indeks obok.
