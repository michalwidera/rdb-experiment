# K20 etap 1b — model kosztu slotu z cechami sondy E4

- obserwacji: 43 (uczace 22, testowe 18)
- podzial ZAMROZONY: dopasowanie ['W2', 'W3', 'W5', 'W7'], predykcja ['W4', 'W9']
- odniesienie (etap 1, same liczniki planu): MAE_test = 258.3%
- prog sukcesu zamrozony w predeklaracji: MAE_test <= 50.0%, MAE_train <= 2.0x MAE_test

## Warianty cech — wszystkie policzone, zaden nie wybrany po fakcie

| wariant | cechy | MAE_train | MAE_test | wspolczynniki ujemne |
|---|---|---:|---:|---|
| `v1` | tokeny, bajty_trwale, bajty_pamieciowe | 14.9% | 258.3% | `bajty_trwale`, `bajty_pamieciowe` |
| `v2` | tokeny, bajty_trwale, bajty_pamieciowe, agse_elements | — | — | UKLAD OSOBLIWY |
| `v3` | agse_elements, agse_reads, eval_tokens | — | — | UKLAD OSOBLIWY |
| `v4` | agse_elements, agse_reads, eval_tokens, bajty_trwale | — | — | UKLAD OSOBLIWY |

## Werdykt

**UKLAD OSOBLIWY dla wariantu ocenianego -- brak werdyktu**


## Zagrozenie trafnosci — jawne

Cechy pochodza z buildu instrumentowanego (`issue_219-instrument`), a cele `p99` z kampanii K6c na `1bb2d2c`. Zestawienie jest uprawnione tylko przy przechodzacym badaniu higienicznym i pozostaje slabsze niz pomiar z jednego drzewa kodu. Decyzja o tym odstepstwie: czlowiek, 2026-07-31 (README, sekcja Odstepstwo).
