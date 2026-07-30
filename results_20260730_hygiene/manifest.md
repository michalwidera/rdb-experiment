# Manifest badania higienicznego `2a5aa86` → `bb3a521`

| Pole | Wartość |
|---|---|
| Identyfikator | `20260730_hygiene` |
| Cel | weryfikacja, czy scalenie sond K6 unieważniło którykolwiek zapisany wynik |
| Data | 2026-07-30 |
| Commit `HISTORICAL` | `2a5aa86148cc4e76ccc0adb8f3e2fa9f450b9123` |
| Commit `FIXED` | `bb3a5216b952432818b23a26365001fe4f7627f5` |
| Branch kodu | `master` |
| Bazowy commit wyników | `a13515a6333311096b229fb5ff9dd2735d7c0cb1` |
| Branch wyników | `experiment/20260730_hygiene` |
| Maszyna | `B850MDESK` (nadzorca) |
| Worker pomiarowy | **nie użyty** — badanie nie mierzy czasu |
| SHA-256 `README.md` | `405cbdac38ea86c70ce244b3b516cbbfc6f7eb0633d38a6057c549ec12f78b8f` |
| Werdykt | **BRAK WPŁYWU** |

## Co badane

`bb3a521` dodał trzy instrumenty dla K6 — `COMPILE_NS`, `PLAN capacity`
i `MATERIALIZED` — dotykając `compiler.cpp` (`compile()`) i `storage.cc`
(`storage::write`), czyli kodu wspólnego dla wszystkich profili i wszystkich
zapytań. `storage::write` jest ścieżką gorącą wykonywaną raz na rekord.

## Warunek ważności

Sprawdzany maszynowo przez `build_trees.sh`: różnica między commitami nie może
obejmować żadnego wejścia silnika (`*.rql`, `examples/`). Warunek spełniony.
Zmiana w `test/IntegrationTest_serial/optimizer_ablation/verify.sh` została
zgłoszona jako **nieblokująca** — to harness testowy, którego to badanie nie
uruchamia, a nie wejście silnika.

Oba drzewa zbudowane tym samym toolchainem, z identycznymi przełącznikami
optymalizatora i **z `RDB_BENCH_PROBE=ON`** — bo dla kampanii pomiarowych (R6)
nowy kod nie jest wyłączony, lecz jest właśnie tym, co działa. Zgodność
potwierdza pusty `results/raw/build/build-info-diff.txt`. Kontrola pozytywna
przerywa badanie, gdyby drzewo historyczne stało na commicie docelowym.

## Zakres i wynik

| Warstwa | Zakres | Wynik |
|---|---|---|
| plany | 81 plików RQL × 2 silniki, compile-only | 0 różnic zrzutu, 0 zmian statusu, 0 różnic liczników |
| artefakty | 4 potoki × 3 przebiegi, porównanie bajtowe | 142 artefakty identyczne, 1 potok wyłączony |

Wyłączony `dsp` czyta `/dev/urandom`; kontrola determinizmu (trzeci przebieg
tym samym silnikiem) wykryła to samodzielnie i wyłączyła potok z kryterium.

## Artefakty surowe (R14)

| Archiwum | Plików | Bajtów | SHA-256 |
|---|---:|---:|---|
| `results/raw.tar.gz` | 813 | 533667 | `b582f33356f73bf0a4e2f200733d5cc0c8a5bd2cac2c5367f61c61db290695b5` |

Indeks `results/raw.index.tsv` wymienia każdy plik z rozmiarem i `SHA-256`,
więc pojedynczy artefakt można wyjąć bez rozpakowywania całości:

```bash
tar -xzOf results/raw.tar.gz raw/pipelines/rec205/FIXED/qrs_out
```

### Dowody porażki

**Brak** — badanie nie wykazało różnic, więc `results/evidence_list.txt` jest
pusty. Pusty plik jest zapisany celowo: dowodzi, że nie było czego zachować,
w odróżnieniu od braku pliku, który nie dowodzi niczego.

### Odtworzenie artefaktów

```bash
git -C /home/michal/github/retractordb checkout bb3a5216   # drzewo musi być czyste
git -C /home/michal/github/rdb-experiment checkout a13515a6333311096b229fb5ff9dd2735d7c0cb1
cd /home/michal/github/rdb-experiment/results_20260730_hygiene
./run.sh                       # build_trees.sh + corpus_diff.py + artifact_diff.py + verdict.py
```

`run.sh` sam sprawdza commit kodu i czystość repozytorium, więc pomyłka w kroku
`checkout` zatrzymuje przebieg. Zgodność odtworzonego drzewa sprawdza indeks:

```bash
python3 ../lib/artifacts.py index results/raw /tmp/raw.index.tsv
diff results/raw.index.tsv /tmp/raw.index.tsv
```

Zrzuty `stdout` kompilacji są normalizowane (ścieżka katalogu roboczego → `<WORK>`)
**przed** policzeniem hasha, więc — w odróżnieniu od kampanii K4 — są odtwarzalne.

## Zgodność z REQUIREMENTS.md

| Wymaganie | Zastosowanie |
|---|---|
| R2 zakaz zapisu do repo kodu | drzewo `HISTORICAL` z klonu; przebiegi w `/dev/shm`; `git status` sprawdzany przed i po |
| R3 katalog docelowy | `results_20260730_hygiene/`, bez rotacji; poprzednie badanie nietknięte |
| R6 build pomiarowy | oba drzewa Release z `RDB_BENCH_PROBE=ON`, `--build-info` weryfikowane bajtowo |
| R7 środowisko RT | **nie dotyczy** — brak metryk czasowych |
| R12 odtwarzalność | ten manifest, `README.md` z SHA-256, wpis w `JOURNAL.md` |
| R14 higiena artefaktów | `results/raw` spakowany przez pułapkę `EXIT`; 9 luźnych plików w `results/` |

## Odstępstwa

1. **Raport pierwszego przebiegu nosił commity z poprzedniej kampanii.**
   `verdict.py` miał je zaszyte w kodzie. Poprawione: `build_trees.sh` zapisuje
   `results/commits.tsv` na podstawie **faktycznie zbudowanych** drzew, a raport
   je odczytuje. Dane badania nie zmieniły się — poprawka dotyczyła wyłącznie
   nagłówka raportu, przeliczonego z tych samych `corpus.json` i `pipelines.json`.
