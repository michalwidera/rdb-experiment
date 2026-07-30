# Macierz funkcjonalna pięciu profili (K6.2)

Wykonana na **nadzorcy** dla commita `bb3a5216b952432818b23a26365001fe4f7627f5`.
Worker buduje te same profile, ale tylko binarki pomiarowe: pełny build wszystkich
celów na Raspberry Pi trwa godziny, a macierz sprawdza kształt planu i równość
artefaktów, które są bajtowo identyczne między architekturami (K18).

**Wynik: 45/45 testów `it_optimizer_ablation`, 0 niepowodzeń.**

| Profil | testów | niepowodzeń | `--build-info` | SHA-256 logu |
|---|---:|---:|---|---|
| `OFF` | 9 | 0 | `DEDUP_SUBSTRATES=OFF; SHARE_EQUIVALENT_SELECTS=OFF; COMMUTATIVE_ADD=OFF; FACTOR_MATCHED_HASH_TIMEMOVES=OFF; probe=ON` | `2b3dd29862abea56…` |
| `STRUCT` | 9 | 0 | `DEDUP_SUBSTRATES=ON; SHARE_EQUIVALENT_SELECTS=ON; COMMUTATIVE_ADD=OFF; FACTOR_MATCHED_HASH_TIMEMOVES=OFF; probe=ON` | `c26ccbca11855c81…` |
| `STRUCT_R1` | 9 | 0 | `DEDUP_SUBSTRATES=ON; SHARE_EQUIVALENT_SELECTS=ON; COMMUTATIVE_ADD=OFF; FACTOR_MATCHED_HASH_TIMEMOVES=ON; probe=ON` | `604c19310262871b…` |
| `STRUCT_R2` | 9 | 0 | `DEDUP_SUBSTRATES=ON; SHARE_EQUIVALENT_SELECTS=ON; COMMUTATIVE_ADD=ON; FACTOR_MATCHED_HASH_TIMEMOVES=OFF; probe=ON` | `d32014513c3ea9cd…` |
| `ALGSTRUCT` | 9 | 0 | `DEDUP_SUBSTRATES=ON; SHARE_EQUIVALENT_SELECTS=ON; COMMUTATIVE_ADD=ON; FACTOR_MATCHED_HASH_TIMEMOVES=ON; probe=ON` | `96908d0967c8851f…` |

Zgodnie z R14 logi udanych przebiegów nie stają się plikami — ich tożsamość
dowodzą sumy kontrolne powyżej. Odtworzenie:

```bash
cd results_20260730_K6
K6_RUN_CTEST=1 K6_RAW_DIR=/dev/shm/k6-host-ctest ./build_profiles.sh
```
