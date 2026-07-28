# S1 — moc detekcyjna mostu K19 wobec mutanta pojemnosci

- data: 2026-07-28T20:49:00+02:00
- FIXED: commit `3db781711a84c08ce794c3924aab533dba6fcbd1`
- MUTANT: ten sam commit, odwrocona silnikowa czesc poprawki
- HISTORICAL: commit `7942b78b74763c88283f7a7bc6262a80d6a90b76` bez zmian
- mutacja: `compiler::computeRequiredCapacities`, galaz `STREAM_AGSE`
- typ builda: Debug (trzy drzewa w `/home/michal/.tmp/rdb-extend`, klony repozytorium kodu)

## Wynik

| Drzewo | Silnik | Zestaw testow | Selekcja | Wynik | Oblane testy |
|---|---|---|---|---|---|
| HISTORICAL | wadliwy | z epoki K19 | `K19_ORIGINAL` | PRZEZYL |  |
| MUTANT | wadliwy | rozszerzony | `K19_ORIGINAL` | zabity | ut_compiler |
| MUTANT | wadliwy | rozszerzony | `K19_EXTENDED` | zabity | it_agse_volatile ut_compiler |
| FIXED | poprawiony | rozszerzony | `K19_ORIGINAL` | zielony |  |
| FIXED | poprawiony | rozszerzony | `K19_EXTENDED` | zielony |  |

HISTORICAL i MUTANT roznia sie wylacznie zestawem testow — kod silnika jest
w obu bajtowo identyczny (kontrola w `lib/build_trees.sh`).

Surowe wyjscia ctest: `raw/<drzewo>__<selekcja>.txt`.
