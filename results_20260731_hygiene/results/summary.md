# Wynik badania higienicznego — `bb3a521` → `e1e5181`

**Werdykt: BRAK WPŁYWU**

- korpus: 81 plików RQL
- HISTORICAL `bb3a521`: 76 skompilowanych, 5 odrzuconych, R1=8, R2=18
- FIXED `e1e5181`: 76 skompilowanych, 5 odrzuconych, R1=8, R2=18

## Kryterium

| Warunek | Wynik |
|---|---|
| zero różnic w zrzutach planu | spełniony |
| zero regresji statusu kompilacji | spełniony |
| zero różnic w licznikach R1/R2 | spełniony |
| artefakty potoków identyczne | spełniony (3 ocenionych, 1 wyłączonych) |
| wyjście klienta identyczne | spełniony (78 poleceń porównanych, 6 wyłączonych) |

## Artefakty potoków

| Potok | Cykli | Artefaktów | Identyczne |
|---|---:|---:|---|
| `examples/ecg/rec205/rec205-qrs.rql` | 4000 | 33 | tak |
| `test/IntegrationTest_serial/optimizer_ablation/query.rql` | 200 | 116 | tak |
| `test/IntegrationTest_serial/agse_volatile/query.rql` | 200 | 11 | tak |

### Potoki wyłączone z kryterium

Dwa przebiegi tym samym silnikiem dają różne bajty, więc potok nie odróżnia
zmiany kodu od zmiany wejścia i nie może służyć za wyrocznię.

- `test/IntegrationTest_parallel/dsp/query.rql` — potok niedeterministyczny — dwa przebiegi tym samym silnikiem dają różne bajty; wyłączony z kryterium, bo nie odróżnia zmiany kodu od zmiany wejścia

## Warstwa 3 — klient `xqry`

Silnik trzymany stały (binarka FIXED), żeby różnica była przypisywalna klientowi.
Porównanych poleceń: **78**.

| Potok | Polecenie | `rc` HISTORICAL | `rc` FIXED | Identyczne |
|---|---|---:|---:|---|
| `optimizer_ablation` | `-l` | 0 | 0 | tak |
| `optimizer_ablation` | `-d` | 0 | 0 | tak |
| `optimizer_ablation` | `-t FA` | 0 | 0 | tak |
| `optimizer_ablation` | `-t FB` | 0 | 0 | tak |
| `optimizer_ablation` | `-t STREAM_HASH_FA_FB` | 0 | 0 | tak |
| `optimizer_ablation` | `-t factored` | 0 | 0 | tak |
| `optimizer_ablation` | `-t MA` | 0 | 0 | tak |
| `optimizer_ablation` | `-t MB` | 0 | 0 | tak |
| `optimizer_ablation` | `-t STREAM_HASH_MA_MB` | 0 | 0 | tak |
| `optimizer_ablation` | `-t mixed_hash` | 0 | 0 | tak |
| `optimizer_ablation` | `-t FA2` | 0 | 0 | tak |
| `optimizer_ablation` | `-t FB2` | 0 | 0 | tak |
| `optimizer_ablation` | `-t STREAM_HASH_FA2_FB2` | 0 | 0 | tak |
| `optimizer_ablation` | `-t QA2` | 0 | 0 | tak |
| `optimizer_ablation` | `-t QB2` | 0 | 0 | tak |
| `optimizer_ablation` | `-t STREAM_HASH_QA2_QB2` | 0 | 0 | tak |
| `optimizer_ablation` | `-t multi_reference` | 0 | 0 | tak |
| `optimizer_ablation` | `-t CA2` | 0 | 0 | tak |
| `optimizer_ablation` | `-t CB2` | 0 | 0 | tak |
| `optimizer_ablation` | `-t STREAM_HASH_CA2_CB2` | 0 | 0 | tak |
| `optimizer_ablation` | `-t CA` | 0 | 0 | tak |
| `optimizer_ablation` | `-t CB` | 0 | 0 | tak |
| `optimizer_ablation` | `-t STREAM_HASH_CA_CB` | 0 | 0 | tak |
| `optimizer_ablation` | `-t QA` | 0 | 0 | tak |
| `optimizer_ablation` | `-t QB` | 0 | 0 | tak |
| `optimizer_ablation` | `-t STREAM_HASH_QA_QB` | 0 | 0 | tak |
| `optimizer_ablation` | `-t multi2` | 0 | 0 | tak |
| `optimizer_ablation` | `-t STREAM_TIMEMOVE_CA` | 0 | 0 | tak |
| `optimizer_ablation` | `-t STREAM_TIMEMOVE_CB` | 0 | 0 | tak |
| `optimizer_ablation` | `-t collide_user` | 0 | 0 | tak |
| `optimizer_ablation` | `-t factor_reference` | 0 | 0 | tak |
| `optimizer_ablation` | `-t collide_reference` | 0 | 0 | tak |
| `optimizer_ablation` | `-t multi1` | 0 | 0 | tak |
| `optimizer_ablation` | `-t STREAM_TIMEMOVE_MA` | 0 | 0 | tak |
| `optimizer_ablation` | `-t DB2` | 0 | 0 | tak |
| `optimizer_ablation` | `-t DA2` | 0 | 0 | tak |
| `optimizer_ablation` | `-t A` | 0 | 0 | tak |
| `optimizer_ablation` | `-t B` | 0 | 0 | tak |
| `optimizer_ablation` | `-t STREAM_SELECT_commuted` | 0 | 0 | tak |
| `optimizer_ablation` | `-t same1` | 0 | 0 | tak |
| `optimizer_ablation` | `-t DA` | 0 | 0 | tak |
| `optimizer_ablation` | `-t MA2` | 0 | 0 | tak |
| `optimizer_ablation` | `-t DB` | 0 | 0 | tak |
| `optimizer_ablation` | `-t STREAM_TIMEMOVE_MA2` | 0 | 0 | tak |
| `optimizer_ablation` | `-t dedup_owner` | 0 | 0 | tak |
| `optimizer_ablation` | `-t dedup_shifted` | 0 | 0 | tak |
| `optimizer_ablation` | `-t mixed_shift` | 0 | 0 | tak |
| `optimizer_ablation` | `-t same2` | 0 | 0 | tak |
| `optimizer_ablation` | `-t commuted` | 0 | 0 | tak |
| `optimizer_ablation` | `-t dedup_reference_owner` | 0 | 0 | tak |
| `optimizer_ablation` | `-t MB2` | 0 | 0 | tak |
| `optimizer_ablation` | `-t mixed_shift_reference` | 0 | 0 | tak |
| `optimizer_ablation` | `-t dedup_reference` | 0 | 0 | tak |
| `optimizer_ablation` | `-s A -m 20` | 0 | 0 | tak |
| `optimizer_ablation` | `-s B -m 20` | 0 | 0 | tak |
| `optimizer_ablation` | `-s CA -m 20` | 0 | 0 | tak |
| `optimizer_ablation` | `-t nie_ma_takiego_strumienia` | 2 | 2 | tak |
| `optimizer_ablation` | `-s nie_ma_takiego_strumienia -m 1` | 2 | 2 | tak |
| `rec205` | `-l` | 0 | 0 | tak |
| `rec205` | `-t ecg` | 0 | 0 | tak |
| `rec205` | `-t mlii` | 0 | 0 | tak |
| `rec205` | `-t mlii_win` | 0 | 0 | tak |
| `rec205` | `-t bpf` | 0 | 0 | tak |
| `rec205` | `-t bp_acc` | 0 | 0 | tak |
| `rec205` | `-t bp_out` | 0 | 0 | tak |
| `rec205` | `-t bp_win` | 0 | 0 | tak |
| `rec205` | `-t df` | 0 | 0 | tak |
| `rec205` | `-t d_acc` | 0 | 0 | tak |
| `rec205` | `-t d_out` | 0 | 0 | tak |
| `rec205` | `-t sq_out` | 0 | 0 | tak |
| `rec205` | `-t mwi_win` | 0 | 0 | tak |
| `rec205` | `-t mwi` | 0 | 0 | tak |
| `rec205` | `-t STREAM_ADD_mlii_mwi` | 0 | 0 | tak |
| `rec205` | `-t mwi_long` | 0 | 0 | tak |
| `rec205` | `-t mwi_thr` | 0 | 0 | tak |
| `rec205` | `-t qrs_out` | 0 | 0 | tak |
| `rec205` | `-t nie_ma_takiego_strumienia` | 2 | 2 | tak |
| `rec205` | `-s nie_ma_takiego_strumienia -m 1` | 2 | 2 | tak |

### Polecenia wyłączone z kryterium

Dwa przebiegi tym samym klientem dają różne wyjście, więc polecenie nie
odróżnia zmiany kodu od chwili podłączenia i nie może służyć za wyrocznię.

- `-y` w `optimizer_ablation`
- `-d` w `rec205`
- `-y` w `rec205`
- `-s bp_acc -m 20` w `rec205`
- `-s bp_out -m 20` w `rec205`
- `-s bp_win -m 20` w `rec205`

### Zmiany na ścieżkach porażki — treść poprawki, nie odstępstwo

Poprawka `#216` uczyniła tryby porażki rozróżnialnymi: po kodzie wyjścia
i po komunikacie. Poniższe polecenia **już przed poprawką kończyły się**
**niezerowo** — zmiana ich kodu albo komunikatu jest skutkiem zamierzonym.
Odstępstwem byłoby przejście z zera na niezero; takich nie ma.

- `-s nie_ma_takiego_strumienia -m 1` w `optimizer_ablation`: rc 2 → 2; komunikat diagnostyczny
- `-s nie_ma_takiego_strumienia -m 1` w `rec205`: rc 2 → 2; komunikat diagnostyczny

## Uwaga do liczników R1/R2

Liczniki są identyczne po obu stronach porównania i to jest treścią warunku.
Nie należy ich natomiast zestawiać z liczbami zapisanymi w K4 (`R1=5`, `R2=18`):
tamte pochodzą z commitu `50e19b7` i korpusu 80 plików — sprzed zniesienia warunku
jednego konsumenta w R1 oraz przed dodaniem testów `agse_volatile`
i `r1_identity_nulls`. Wzrost R1 z 5 do 8 wynika z tych zmian, nie ze scalenia
badanego tutaj; widać to stąd, że **oba** drzewa raportują tę samą wartość.

## Wniosek

Scalenie `e1e5181` nie zmieniło zachowania dla żadnego planu, który
kompilował się i wykonywał na `bb3a521`, ani wyjścia klienta
na żadnej ze ścieżek, które przed poprawką kończyły się sukcesem.
Wyniki zapisane na wcześniejszych rewizjach pozostają w mocy.
