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

## Artefakty surowe

Kampania wytworzyła 820 surowych plików: para `stdout`/`stderr` dla każdej
z 400 kompilacji (5 profili × 80 plików RQL) oraz logi budowania profili.
Zgodnie z `REQUIREMENTS.md` R14 zostały w katalogu jako archiwum z indeksem:

| Archiwum | Plików | Bajtów | SHA-256 |
|---|---:|---:|---|
| `results/raw.tar.gz` | 820 | 65666 | `407cb32400c57fdc7c9f969821de134062120bce57399ac051c6162618d79968` |

### Dowody odrzuceń

`results/evidence/corpus/<profil>/<suita>/<plik>.stderr` — 25 plików, czyli
komunikat odrzucenia pięciu plików RQL o statusie `expected_failure` w każdym
z pięciu profili. Zachowane jako pliki, bo tylko ta grupa niesie treść
negatywną, a komunikat różni się między profilami: identyczny jest wyłącznie
dla `ut_example.rql`, więc porównanie profili wymaga wszystkich pięciu wersji.
Zrzuty 395 kompilacji udanych są w archiwum; ich `SHA-256` zapisuje
`results/counts.json` w polach `stdout_sha256` i `stderr_sha256`.

```bash
tar -xzOf results/raw.tar.gz raw/corpus/ALGSTRUCT/integration_serial/query-all-df9f47942de2.stdout
```

### Odtworzenie artefaktów

| Repozytorium | Commit | Branch |
|---|---|---|
| `retractordb` (kod) | `50e19b75d71ef42c842c7db6214e5c31d5dd86ab` | `results_20260728_K4_IMPL` |
| `rdb-experiment` (skrypty i wyniki) | `95d35e71739a168f14e18721205b7b76074f09d9` | `results_20260728_K4` |

```bash
git -C /home/michal/github/retractordb checkout 50e19b75   # drzewo musi być czyste
git -C /home/michal/github/rdb-experiment checkout 95d35e71
cd /home/michal/github/rdb-experiment/results_20260728_K4
./run.sh                       # build_profiles.sh + collect.py + verdict.py
```

Zgodność odtworzonego drzewa z zapisanym sprawdza indeks:

```bash
python3 ../lib/artifacts.py index results/raw /tmp/raw.index.tsv
diff results/raw.index.tsv /tmp/raw.index.tsv
```

Zrzuty zawierają ścieżkę katalogu roboczego kompilacji, więc bajtowo
odtwarzalne są wyłącznie liczniki i statusy w `results/counts.json`.

## Odstępstwo od R14

Kampania powstała przed wprowadzeniem R14; archiwum i `results/evidence/`
utworzył `compact_results.sh` 2026-07-30. Treść artefaktów nie zmieniła się —
dowodzi tego indeks `SHA-256`.
