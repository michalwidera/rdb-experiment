# Manifest K4

| Pole | Wartość |
|---|---|
| Identyfikator | `20260728_K4` |
| Rodzaj | lokalny eksperyment semantyczny, compile-only |
| Repozytorium kodu | `/home/michal/github/retractordb` |
| Branch kodu | `results_20260728_K4_IMPL` |
| Commit kodu | `50e19b75d71ef42c842c7db6214e5c31d5dd86ab` |
| Bazowy commit wyników | `b2edf5cb4f65d788295048b151b02ec30837ddee` |
| Branch wyników | `results_20260728_K4` |
| Worker | nie dotyczy |

Każdy wariant używa `RDB_BENCH_PROBE=ON`. Dokładne wartości czterech
przełączników optymalizatora są zapisane w `profiles.tsv` i ponownie
sprawdzane przez `xretractor --build-info`.

Jednostką korpusu jest jeden istniejący plik RQL. Każdy przypadek jest
kompilowany w świeżej kopii swojego katalogu, aby kompilator nie zapisywał
deskryptorów ani artefaktów w repozytorium kodu.
