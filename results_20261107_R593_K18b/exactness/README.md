# R593 K18b - exactness/replay

Ta część pomiaru używa RetractorDB z gałęzi `dev/muro`, commit `e389edd3596e4b83b6f3f4a9e238905a91c667b4`. Zakres i reguły porównania są takie jak w `results_20260728_K18/exactness/README.md`.

Harness `../run.sh` używa planów po migracji S1/S2 z `../config/` (sumy i dowód w `../config/migration.tsv`) i zapisuje do tego katalogu surowe logi, identyfikator binarki, `configuration.sha256`, porównania i migawki stanu.
