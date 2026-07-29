# Wynik badania higienicznego — `Fix (#214)`

**Werdykt: BRAK WPŁYWU**

- korpus: 81 plików RQL
- HISTORICAL `0e0f701`: 76 skompilowanych, 5 odrzuconych, R1=8, R2=18
- FIXED `2a5aa86`: 76 skompilowanych, 5 odrzuconych, R1=8, R2=18

## Kryterium

| Warunek | Wynik |
|---|---|
| zero różnic w zrzutach planu | spełniony |
| zero regresji statusu kompilacji | spełniony |
| zero różnic w licznikach R1/R2 | spełniony |
| artefakty potoków identyczne | spełniony (3 ocenionych, 1 wyłączonych) |

## Artefakty potoków

| Potok | Cykli | Artefaktów | Identyczne |
|---|---:|---:|---|
| `examples/ecg/rec205/rec205-qrs.rql` | 4000 | 15 | tak |
| `test/IntegrationTest_serial/optimizer_ablation/query.rql` | 200 | 116 | tak |
| `test/IntegrationTest_serial/agse_volatile/query.rql` | 200 | 11 | tak |

### Potoki wyłączone z kryterium

Dwa przebiegi tym samym silnikiem dają różne bajty, więc potok nie odróżnia
zmiany kodu od zmiany wejścia i nie może służyć za wyrocznię.

- `test/IntegrationTest_parallel/dsp/query.rql` — potok niedeterministyczny — dwa przebiegi tym samym silnikiem dają różne bajty; wyłączony z kryterium, bo nie odróżnia zmiany kodu od zmiany wejścia

## Uwaga do liczników R1/R2

Liczniki są identyczne po obu stronach porównania i to jest treścią warunku.
Nie należy ich natomiast zestawiać z liczbami zapisanymi w K4 (`R1=5`, `R2=18`):
tamte pochodzą z commitu `50e19b7` i korpusu 80 plików — sprzed zniesienia warunku
jednego konsumenta w R1 oraz przed dodaniem testów `agse_volatile`
i `r1_identity_nulls`. Wzrost R1 z 5 do 8 wynika z tych zmian, nie z tej poprawki;
widać to stąd, że **oba** drzewa raportują tę samą wartość.

## Wniosek

Poprawka nie zmieniła zachowania dla żadnego planu, który kompilował się przed nią.
Wyniki zapisane na wcześniejszych rewizjach (K4, K18, K19) pozostają w mocy.
