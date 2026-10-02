# Poprawiony most G3 - wyniki

Cisza `origin+tail` w kolejnosci optimized/blocked/explicit_rhs; oczekiwana z K24-C1,
sprawdzonego wobec `causal_shift_matching_declared`. Generuje `make_summary.py`.

## Silnik `1695ed8d1f3727c5393d9920c5059c3eaba0645f`

- plik: `results/engine-1695ed8d.json`, werdykt **OK** (13/13)
- binarka: `xretractor`, sha256 `4e96e77eb86a`
- przelaczniki: RDB_OPT_DEDUP_SUBSTRATES=ON RDB_OPT_SHARE_EQUIVALENT_SELECTS=ON RDB_OPT_COMMUTATIVE_ADD=ON RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=ON RDB_BENCH_PROBE=OFF RDB_OPT_SIMPLIFY_EXPRESSIONS=ON
- rdb-experiment: `d319e886` (drzewo niezacommitowane)

| przypadek | W_hash | cisza | K24-C1 | rekordy | rozbieznosci wartosci | zamrozony G3 | wynik |
|---|--:|---|---|---|---|---|---|
| p2_equal | 1 | 2+0/2+1/2+0 | 2+0/2+1/2+0 | 87/86/87 | 0/0/0 | MISMATCH | OK |
| p3_regression | 2 | 3+0/3+2/3+0 | 3+0/3+2/3+0 | 49/47/49 | 0/0/0 | MISMATCH | OK |
| p3_reverse | 1 | 3+0/3+1/3+0 | 3+0/3+1/3+0 | 56/55/56 | 0/0/0 | MISMATCH | OK |
| p4_skew | 3 | 4+0/4+3/4+0 | 4+0/4+3/4+0 | 55/52/55 | 0/0/0 | MISMATCH | OK |
| p5_remainder1 | 2 | 5+0/5+2/5+0 | 5+0/5+2/5+0 | 57/55/57 | 0/0/0 | MISMATCH | OK |
| p7_remainder1 | 2 | 7+0/7+2/7+0 | 7+0/7+2/7+0 | 57/55/57 | 0/0/0 | MISMATCH | OK |
| p8_remainder2 | 3 | 8+0/8+3/8+0 | 8+0/8+3/8+0 | 60/57/60 | 0/0/0 | MISMATCH | OK |
| p5_fast | 2 | 10+0/10+2/10+0 | 10+0/10+2/10+0 | 71/69/71 | 0/0/0 | MISMATCH | OK |
| p5_slow | 2 | 10+0/10+2/10+0 | 10+0/10+2/10+0 | 33/31/33 | 0/0/0 | MISMATCH | OK |
| p18_fast | 3 | 18+0/18+3/18+0 | 18+0/18+3/18+0 | 77/74/77 | 0/0/0 | MISMATCH | OK |
| p18_slow | 3 | 18+0/18+3/18+0 | 18+0/18+3/18+0 | 29/26/29 | 0/0/0 | MISMATCH | OK |
| p3_unreduced | 2 | 5+0/5+2/5+0 | 5+0/5+2/5+0 | 51/49/51 | 0/0/0 | MISMATCH | OK |
| p307_audio | 2 | 307+0/307+2/307+0 | 307+0/307+2/307+0 | 219/217/219 | 0/0/0 | MISMATCH | OK |

## Silnik `40c28dbefec8324df45365d863050fc577623768`

- plik: `results/engine-40c28dbe.json`, werdykt **OK** (13/13)
- binarka: `xretractor`, sha256 `5afa04357cd2`
- przelaczniki: RDB_OPT_DEDUP_SUBSTRATES=ON RDB_OPT_SHARE_EQUIVALENT_SELECTS=ON RDB_OPT_COMMUTATIVE_ADD=ON RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=ON RDB_BENCH_PROBE=OFF RDB_OPT_SIMPLIFY_EXPRESSIONS=ON
- rdb-experiment: `d319e886` (drzewo niezacommitowane)

| przypadek | W_hash | cisza | K24-C1 | rekordy | rozbieznosci wartosci | zamrozony G3 | wynik |
|---|--:|---|---|---|---|---|---|
| p2_equal | 1 | 2+0/2+1/2+0 | 2+0/2+1/2+0 | 87/86/87 | 0/0/0 | MISMATCH | OK |
| p3_regression | 2 | 3+0/3+2/3+0 | 3+0/3+2/3+0 | 49/47/49 | 0/0/0 | MISMATCH | OK |
| p3_reverse | 1 | 3+0/3+1/3+0 | 3+0/3+1/3+0 | 56/55/56 | 0/0/0 | MISMATCH | OK |
| p4_skew | 3 | 4+0/4+3/4+0 | 4+0/4+3/4+0 | 55/52/55 | 0/0/0 | MISMATCH | OK |
| p5_remainder1 | 2 | 5+0/5+2/5+0 | 5+0/5+2/5+0 | 57/55/57 | 0/0/0 | MISMATCH | OK |
| p7_remainder1 | 2 | 7+0/7+2/7+0 | 7+0/7+2/7+0 | 57/55/57 | 0/0/0 | MISMATCH | OK |
| p8_remainder2 | 3 | 8+0/8+3/8+0 | 8+0/8+3/8+0 | 60/57/60 | 0/0/0 | MISMATCH | OK |
| p5_fast | 2 | 10+0/10+2/10+0 | 10+0/10+2/10+0 | 71/69/71 | 0/0/0 | MISMATCH | OK |
| p5_slow | 2 | 10+0/10+2/10+0 | 10+0/10+2/10+0 | 33/31/33 | 0/0/0 | MISMATCH | OK |
| p18_fast | 3 | 18+0/18+3/18+0 | 18+0/18+3/18+0 | 77/74/77 | 0/0/0 | MISMATCH | OK |
| p18_slow | 3 | 18+0/18+3/18+0 | 18+0/18+3/18+0 | 29/26/29 | 0/0/0 | MISMATCH | OK |
| p3_unreduced | 2 | 5+0/5+2/5+0 | 5+0/5+2/5+0 | 51/49/51 | 0/0/0 | MISMATCH | OK |
| p307_audio | 2 | 307+0/307+2/307+0 | 307+0/307+2/307+0 | 219/217/219 | 0/0/0 | MISMATCH | OK |

## Silnik `db4a3604bd31ad06e7cc89e95739f7f7e87597d6`

- plik: `results/engine-db4a3604.json`, werdykt **MISMATCH** (0/13)
- binarka: `xretractor`, sha256 `e9dd41d1ef3a`
- przelaczniki: RDB_OPT_DEDUP_SUBSTRATES=ON RDB_OPT_SHARE_EQUIVALENT_SELECTS=ON RDB_OPT_COMMUTATIVE_ADD=ON RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=ON RDB_BENCH_PROBE=OFF
- rdb-experiment: `d319e886` (drzewo niezacommitowane)

| przypadek | W_hash | cisza | K24-C1 | rekordy | rozbieznosci wartosci | zamrozony G3 | wynik |
|---|--:|---|---|---|---|---|---|
| p2_equal | 1 | 2+1/2+1/2+1 | 2+0/2+1/2+0 | 86/86/86 | 0/0/0 | MISMATCH | MISMATCH (cisza) |
| p3_regression | 2 | 3+2/3+2/3+2 | 3+0/3+2/3+0 | 47/47/47 | 0/0/0 | MISMATCH | MISMATCH (cisza) |
| p3_reverse | 1 | 3+1/3+1/3+1 | 3+0/3+1/3+0 | 55/55/55 | 0/0/0 | MISMATCH | MISMATCH (cisza) |
| p4_skew | 3 | 4+3/4+3/4+3 | 4+0/4+3/4+0 | 52/52/52 | 0/0/0 | MISMATCH | MISMATCH (cisza) |
| p5_remainder1 | 2 | 5+2/5+2/5+2 | 5+0/5+2/5+0 | 55/55/55 | 0/0/0 | MISMATCH | MISMATCH (cisza) |
| p7_remainder1 | 2 | 7+2/7+2/7+2 | 7+0/7+2/7+0 | 55/55/55 | 0/0/0 | MISMATCH | MISMATCH (cisza) |
| p8_remainder2 | 3 | 8+3/8+3/8+3 | 8+0/8+3/8+0 | 57/57/57 | 0/0/0 | MISMATCH | MISMATCH (cisza) |
| p5_fast | 2 | 10+2/10+2/10+2 | 10+0/10+2/10+0 | 69/69/69 | 0/0/0 | MISMATCH | MISMATCH (cisza) |
| p5_slow | 2 | 10+2/10+2/10+2 | 10+0/10+2/10+0 | 31/31/31 | 0/0/0 | MISMATCH | MISMATCH (cisza) |
| p18_fast | 3 | 18+3/18+3/18+3 | 18+0/18+3/18+0 | 74/74/74 | 0/0/0 | MISMATCH | MISMATCH (cisza) |
| p18_slow | 3 | 18+3/18+3/18+3 | 18+0/18+3/18+0 | 26/26/26 | 0/0/0 | MISMATCH | MISMATCH (cisza) |
| p3_unreduced | 2 | 5+2/5+2/5+2 | 5+0/5+2/5+0 | 49/49/49 | 0/0/0 | MISMATCH | MISMATCH (cisza) |
| p307_audio | 2 | 307+2/307+2/307+2 | 307+0/307+2/307+0 | 217/217/217 | 0/0/0 | MISMATCH | MISMATCH (cisza) |
