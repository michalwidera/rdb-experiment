# K20 etap 1c — model kosztu slotu z rodzina okienna w zbiorze uczacym

- obserwacji: 43 (uczace 25, testowe 18)
- podzial ZAMROZONY: dopasowanie ['W2', 'W3', 'W5', 'W7', 'W8'], predykcja ['W4', 'W9']
- odniesienie oceny: wariant `v1` NA TYM SAMYM podziale (nie liczba z etapu 1)
- kontekst historyczny (etap 1, inny zbior uczacy): MAE_test = 258.3%
- prog sukcesu zamrozony w predeklaracji: MAE_test <= 50.0%, MAE_train <= 2.0x MAE_test

## Warianty cech — wszystkie policzone, zaden nie wybrany po fakcie

| wariant | cechy | MAE_train | MAE_test | wspolczynniki ujemne |
|---|---|---:|---:|---|
| `v1` | tokeny, bajty_trwale, bajty_pamieciowe | 13.1% | 296.2% | `bajty_trwale`, `bajty_pamieciowe` |
| `v2` | tokeny, bajty_trwale, bajty_pamieciowe, agse_elements | 14.5% | 439.2% | `bajty_trwale`, `bajty_pamieciowe` |
| `v3` | agse_elements, agse_reads, eval_tokens | — | — | UKLAD OSOBLIWY |
| `v4` | agse_elements, agse_reads, eval_tokens, bajty_trwale | — | — | UKLAD OSOBLIWY |

## Werdykt

**CECHA NIC NIE WNOSI -- v2 nie jest lepszy od v1 na tym samym podziale**

Wariant oceniany `v2` (odniesienie + `agse_elements`): MAE_train 14.5%, MAE_test 439.2%.

Odniesienie `v1` na TYM SAMYM podziale: MAE_train 13.1%, MAE_test 296.2%.

Wklad samej cechy `agse_elements`: 296.2% -> 439.2% (brak poprawy).

Kontekst historyczny (etap 1, bez W8 w uczeniu): MAE_test = 258.3%. Ta liczba NIE jest punktem odniesienia oceny -- pochodzi z innego podzialu.

**Ostrzezenie: wspolczynnik ujemny przy `bajty_trwale`, `bajty_pamieciowe`.** Koszt nie bywa ujemny, wiec to objaw wspolliniowosci cech, a nie wielkosc fizyczna. Liczby nalezy czytac z tym zastrzezeniem.

## Zagrozenie trafnosci — jawne

Cechy pochodza z buildu instrumentowanego (`issue_219-instrument`), a cele `p99` z kampanii K6c na `1bb2d2c`. Zestawienie jest uprawnione tylko przy przechodzacym badaniu higienicznym i pozostaje slabsze niz pomiar z jednego drzewa kodu. Decyzja o tym odstepstwie: czlowiek, 2026-07-31 (README, sekcja Odstepstwo).
