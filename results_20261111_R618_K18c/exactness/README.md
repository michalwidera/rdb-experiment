# R618 K18c - exactness/replay

Ta część pomiaru używa RetractorDB z gałęzi `dev/muro`, commit `16c516f9eb76c473d5ff8510a2a812b8c23a893d`. Zakres i reguły porównania są takie jak w `results_20260728_K18/exactness/README.md`.

Harness `../run.sh` używa planów po migracji S1/S2 z `../config/` (sumy i dowód w `../config/migration.tsv`) i zapisuje do tego katalogu surowe logi, identyfikator binarki, `configuration.sha256`, porównania i migawki stanu.
