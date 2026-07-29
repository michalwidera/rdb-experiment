# Manifest badania higienicznego

| Pole | Wartość |
|---|---|
| Identyfikator | `20260729_hygiene` |
| Cel | weryfikacja, czy `Fix (#214)` unieważnił którykolwiek zapisany wynik |
| Data | 2026-07-29 |
| Commit `HISTORICAL` | `0e0f70161fd46ffd918dbdb457e6dbdcd4439b03` (sprzed poprawki) |
| Commit `FIXED` | `2a5aa86148cc4e76ccc0adb8f3e2fa9f450b9123` (`master`, z poprawką) |
| Branch wyników | `experiment/20260729_hygiene` |
| Maszyna | `B850MDESK` (nadzorca) |
| Worker pomiarowy | **nie użyty** — badanie nie mierzy czasu |
| Werdykt | **BRAK WPŁYWU** |

## Warunek ważności

`git diff 0e0f701 2a5aa86` obejmuje wyłącznie `src/retractor/lib/compiler.cpp`
(34 wiersze) i `test/UnitTest/test_compiler.cpp` (56 wierszy). Żaden plik `.rql`
ani plik danych nie zmienił się, więc jedyną różnicą między drzewami jest kod
silnika.

Oba drzewa zbudowano tym samym toolchainem, z identycznymi przełącznikami
optymalizatora, potwierdzonymi porównaniem `--build-info` (`build-info-diff.txt`
jest pusty). Kontrola pozytywna: skrypt przerywa, gdyby drzewo historyczne
stało na commicie z poprawką.

## Zakres

| Warstwa | Zakres | Wynik |
|---|---|---|
| plany | 81 plików RQL × 2 silniki, compile-only | 0 różnic, 0 zmian statusu, 0 różnic liczników |
| artefakty | 4 potoki × 3 przebiegi, porównanie bajtowe | 142 artefakty identyczne, 1 potok wyłączony |

## Zgodność z REQUIREMENTS.md

| Wymaganie | Zastosowanie |
|---|---|
| R2 zakaz zapisu do repo kodu | drzewo `HISTORICAL` z klonu; przebiegi w `/dev/shm`; `git status` sprawdzany przed i po |
| R3 katalog docelowy | `results_20260729_hygiene/`, bez rotacji |
| R7 środowisko RT | **nie dotyczy** — brak metryk czasowych |
| R12 odtwarzalność | ten manifest, `README.md`, wpis w `JOURNAL.md` |

## Odstępstwa

1. Dwie wady instrumentu poprawione po pierwszym przebiegu, opisane
   w `instrument_defects.md`; surowe wyniki pierwszego przebiegu zachowane.
2. Katalog `.trees/` z drzewem historycznym nie jest commitowany (klon
   repozytorium kodu, odtwarzalny z `build_trees.sh`).
