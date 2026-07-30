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

## Artefakty surowe

Badanie wytworzyło 813 surowych plików: zrzuty planów 81 plików RQL po obu
stronach porównania oraz artefakty potoków z trzech przebiegów. Zgodnie
z `REQUIREMENTS.md` R14 zostały w katalogu jako archiwum z indeksem:

| Archiwum | Plików | Bajtów | SHA-256 |
|---|---:|---:|---|
| `results/raw.tar.gz` | 813 | 139161 | `340872b0f338bd92bb2ae204456eefd308b85b3047002353fc48f96ba9aeec9b` |

Katalogu `results/evidence/` nie ma — werdykt jest pozytywny i żaden artefakt
nie stanowi dowodu porażki. Jedyny wynik negatywny badania, niedeterminizm
potoku `dsp`, jest widoczny **wprost w indeksie**, bez rozpakowywania. Kontrola
determinizmu porównuje dwa przebiegi tego samego silnika (`HISTORICAL`
i `HISTORICAL_2`) pomijając pierwsze 8 bajtów sidecara `.meta`, czyli znacznik
czasu utworzenia. Zestawienie `SHA-256` z `results/raw.index.tsv`:

| Potok | Różne `.meta` | Różne pozostałe pliki |
|---|---:|---:|
| `dsp` | 4 | **4** (`temp__accRow`, `temp__output`, `temp__outputAll`, `temp__signalRow`) |
| `rec205` | 13 | 0 |
| `optimizer_ablation` | 29 | 0 |
| `agse_volatile` | 4 | 0 |

Tylko `dsp` różni się danymi, pozostałe potoki wyłącznie znacznikiem czasu.
Pojedynczą parę sprawdza się bezpośrednio w indeksie, a plik wyjmuje bez
rozpakowywania całości:

```bash
awk -F'\t' '$1 ~ /pipelines\/dsp\/HISTORICAL(_2)?\/temp__output$/' results/raw.index.tsv
tar -xzOf results/raw.tar.gz raw/pipelines/dsp/FIXED/temp__output.desc
```

### Odtworzenie artefaktów

| Repozytorium | Commit | Branch |
|---|---|---|
| `retractordb` — `FIXED` | `2a5aa86148cc4e76ccc0adb8f3e2fa9f450b9123` | `master` |
| `retractordb` — `HISTORICAL` | `0e0f70161fd46ffd918dbdb457e6dbdcd4439b03` | klon w `.trees/`, tworzy `build_trees.sh` |
| `rdb-experiment` (skrypty i wyniki) | `23451d8c886fedf4f0ad6a7d8e3e422bdbb7e950` | `experiment/20260729_hygiene` |

```bash
git -C /home/michal/github/retractordb checkout 2a5aa861   # drzewo musi być czyste
git -C /home/michal/github/rdb-experiment checkout 23451d8c
cd /home/michal/github/rdb-experiment/results_20260729_hygiene
./run.sh                       # build_trees.sh + corpus_diff.py + artifact_diff.py + verdict.py
```

`build_trees.sh` klonuje drzewo `HISTORICAL` do `.trees/` i buduje oba profile;
`run.sh` przerywa, jeżeli commit `FIXED` lub czystość repozytorium kodu nie
zgadza się z manifestem. Zgodność odtworzonego drzewa z zapisanym:

```bash
python3 ../lib/artifacts.py index results/raw /tmp/raw.index.tsv
diff results/raw.index.tsv /tmp/raw.index.tsv
```

Różnice wystąpią w gałęzi `pipelines/dsp/*` — ten potok jest niedeterministyczny
i właśnie dlatego został wyłączony z kryterium.

## Odstępstwa

1. Dwie wady instrumentu poprawione po pierwszym przebiegu, opisane
   w `instrument_defects.md`; surowe wyniki pierwszego przebiegu zachowane.
2. Katalog `.trees/` z drzewem historycznym nie jest commitowany (klon
   repozytorium kodu, odtwarzalny z `build_trees.sh`).
3. **R14, kompaktowanie po fakcie.** Badanie powstało przed wprowadzeniem R14;
   archiwum utworzył `compact_results.sh` 2026-07-30. Treść artefaktów nie
   zmieniła się — dowodzi tego indeks `SHA-256`.
