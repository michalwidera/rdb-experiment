# R593 K18 - exactness/replay

Ta część pomiaru używa RetractorDB z gałęzi `dev/muro`, commit `dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb`. Zakres i reguły porównania są takie jak w `results_20260728_K18/exactness/README.md`.

Harness `../run.sh` używa planów po migracji S1/S2 z `../config/` (sumy i dowód w `../config/migration.tsv`) i zapisuje do tego katalogu surowe logi, identyfikator binarki, `configuration.sha256`, porównania i migawki stanu.
