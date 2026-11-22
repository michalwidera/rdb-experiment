# R631 K18d - exactness/replay

Ta część pomiaru używa RetractorDB z gałęzi `dev/muro`, commit `758be53b3b8339d176dc678f9a75a259b8926925`. Zakres i reguły porównania są takie jak w `results_20260728_K18/exactness/README.md`.

Harness `../run.sh` używa planów po migracji S1/S2 z `../config/` (sumy i dowód w `../config/migration.tsv`) i zapisuje do tego katalogu surowe logi, identyfikator binarki, `configuration.sha256`, porównania i migawki stanu.
