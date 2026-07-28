# Wynik K4

Jednostką zliczania jest pojedyncza kompilacja istniejącego pliku RQL.
Wyniki zerowe są zachowane jawnie.

## Agregaty profili

| Profil | Skompilowane | Oczekiwane odrzucenia | R1 | R2 | Pliki z R1 | Pliki z R2 |
|---|---:|---:|---:|---:|---:|---:|
| `OFF` | 75 | 5 | 0 | 0 | 0 | 0 |
| `STRUCT` | 75 | 5 | 0 | 0 | 0 | 0 |
| `STRUCT+R1` | 75 | 5 | 5 | 0 | 5 | 0 |
| `STRUCT+R2` | 75 | 5 | 0 | 18 | 0 | 13 |
| `ALGSTRUCT` | 75 | 5 | 5 | 18 | 5 | 13 |

## Trafienia reguł w profilu ALGSTRUCT

| Plik | R1 | R2 |
|---|---:|---:|
| `test/IntegrationTest_serial/Data/query-lnx.rql` | 0 | 1 |
| `test/IntegrationTest_serial/issue167_dedup_nonzero_offset/query.rql` | 0 | 1 |
| `test/IntegrationTest_serial/issue167_triarg/query.rql` | 0 | 1 |
| `test/IntegrationTest_serial/issue202_hash_shift_e2e/query.rql` | 1 | 0 |
| `test/IntegrationTest_serial/optimizer_ablation/query.rql` | 1 | 1 |
| `test/IntegrationTest_serial/r1_identity_nulls/query.rql` | 1 | 0 |
| `test/IntegrationTest_serial/select_cse_commutative_add/query.rql` | 0 | 6 |
| `test/IntegrationTest_parallel/Pattern1/query.rql` | 0 | 1 |
| `test/IntegrationTest_parallel/Pattern2/query.rql` | 0 | 1 |
| `test/IntegrationTest_parallel/dsp/query.rql` | 0 | 1 |
| `test/IntegrationTest_parallel/issue202_hash_shift_factorization/matched.rql` | 1 | 0 |
| `test/IntegrationTest_parallel/issue202_hash_shift_factorization/zero.rql` | 1 | 0 |
| `test/IntegrationTest_parallel/issue96_substrat_reference/queryWithSubstrats.rql` | 0 | 1 |
| `examples/ecg/rec205/rec205-detect.rql` | 0 | 1 |
| `examples/ecg/rec205/rec205-qrs.rql` | 0 | 1 |
| `examples/rmpy/query5.rql` | 0 | 1 |
| `examples/session-record-1/query.rql` | 0 | 1 |

## Jawne wyłączenia

- `examples/mwd/query-mwnd.rql` — Historyczny przykład interaktywny ma sklejone instrukcje SELECT i DECLARE; dołączony test-mwnd.sh również odrzuca go w trybie compile-only.
- `examples/mwd/query-mwnd2.rql` — Historyczny przykład interaktywny używa nieaktualnej, niecytowanej ścieżki FILE.
- `test/IntegrationTest_parallel/issue95_loopInCompile/brokenQuery.rql` — Regresja celowo zawiera cykliczną zależność i musi zostać odrzucona przez kompilator.
- `test/IntegrationTest_serial/Data/query.rql` — Nierejestrowany historyczny fixture używa usuniętych typów i16/i8 oraz dawnej składni FILE.
- `test/IntegrationTest_serial/Data/ut_example.rql` — Nierejestrowany historyczny fixture odwołuje się do niezadeklarowanego strumienia core.

## Interpretacja

- R1 oznacza skuteczne przepisanie planu.
- R2 oznacza unikalny węzeł, którego odcisk wymagał przemiennej zamiany dzieci.
- R2 nie jest liczbą usuniętych węzłów ani miarą przyspieszenia.
- Korpus obejmuje istniejące testy integracyjne i przykłady, nie syntetyczny workload K5.
