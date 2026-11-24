# R648 K18e - exactness/replay

Ta część pomiaru używa RetractorDB z gałęzi `dev/muro`, commit `7e5659f4c070b39f1c1a711217fb98548ca60cf4`. Zakres i reguły porównania są takie jak w `results_20260728_K18/exactness/README.md`.

Harness `../run.sh` używa planów po migracji S1/S2 z `../config/` (sumy i dowód w `../config/migration.tsv`) i zapisuje do tego katalogu surowe logi, identyfikator binarki, `configuration.sha256`, porównania i migawki stanu.
