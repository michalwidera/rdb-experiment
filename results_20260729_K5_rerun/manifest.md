# Manifest K5 (powtórka)

| Pole | Wartość |
|---|---|
| Identyfikator eksperymentu | `20260729_K5_rerun` |
| Krok planu badawczego | K5 — workload wielozapytaniowy `Q = 1,2,4,8,16,32`, punkt go/no-go |
| Data utworzenia | 2026-07-29 |
| Commit kodu | `2a5aa86148cc4e76ccc0adb8f3e2fa9f450b9123` |
| Branch kodu | `master` |
| Poprzednia kampania | `results_20260729_K5/` (zatrzymana przed werdyktem, kod `0e0f701`) |
| Bazowy commit wyników | `0aae66f773cfc1c44875a999d84408bfc887f776` |
| Branch wyników | `experiment/20260729_K5` |
| Maszyna | `B850MDESK` (nadzorca) |
| Jądro | `6.18.33.2-microsoft-standard-WSL2` |
| Worker pomiarowy | **nie użyty** |
| SHA-256 `README.md` | `e021ae83eed94e20ad3a09ad8f24fdb128c6fbdd56957d0b90c3d61234459a0c` |

## Dlaczego powtórka

Pierwsza kampania ujawniła wadę `resolveStreamIntervals` niezależną od badanych
reguł: plany bezcykliczne bywały odrzucane zależnie od kolejności w planie.
Człowiek zatrzymał eksperyment przed rozstrzygnięciem go/no-go, wada została
naprawiona na branchu `issue_213-defect-interval` i scalona do `master`
(`Fix (#214)`), a kampania powtórzona na naprawionym kodzie.

Zgodnie z `REQUIREMENTS.md` R3 zmiana kodu wymusza nowy katalog wyników;
katalog pierwszej kampanii pozostaje niezmieniony.

## Dlaczego bez workera

Kryterium go/no-go K5 rozstrzyga się compile-only i kampania nie rejestruje
żadnej metryki czasowej. Warunki R7 nie wpływają na wynik `xretractor w.rql -c`,
a akapit „Zakres" `REQUIREMENTS.md` wyłącza kampanie niemierzące czasu spod
procedury nadzorcy. Worker wchodzi dopiero w K6.

## Zgodność z REQUIREMENTS.md

| Wymaganie | Zastosowanie |
|---|---|
| R1 dwa repozytoria | kod `retractordb` @ `master`, wyniki `rdb-experiment` @ `experiment/20260729_K5` |
| R2 zakaz zapisu do repo kodu | kompilacje w kopii roboczej poza repozytorium; `git status` sprawdzany przed i po |
| R3 katalog docelowy | `results_20260729_K5_rerun/`, bez rotacji; poprzedni katalog nietknięty |
| R4 branch i commity | commity w trakcie realizacji dozwolone przez człowieka (odstępstwo uzgodnione 2026-07-29) |
| R5 warunki wejściowe | oba repozytoria czyste, commit kodu przypięty w `run.sh` |
| R6 build pomiarowy | pięć profili Release z `RDB_BENCH_PROBE=ON`, `--build-info` weryfikowane bajtowo |
| R7 środowisko RT | **nie dotyczy** — kampania bez metryk czasowych |
| R9 rejestrowane dane | `state_before.md`, `state_after.md`, dane surowe, `summary.md` |
| R12 odtwarzalność | ten manifest, `README.md` z SHA-256, wpis w `JOURNAL.md` |
| R13 wykrywanie workera | **nie dotyczy** |

## Artefakty surowe

Kampania wytworzyła 4328 surowych plików artefaktów silnika. Zgodnie z
`REQUIREMENTS.md` R14 zostały w katalogu jako archiwa z indeksem:

| Archiwum | Plików | Bajtów | SHA-256 |
|---|---:|---:|---|
| `results/raw.tar.gz` | 4213 | 194945 | `cd20f8d38984ac4164a9b45a4aee601441271215ff223785b0790d2df59503dd` |
| `results/workloads.tar.gz` | 115 | 8319 | `a10c708ab839ba7aae5e9c713ee7094f7d81b34a9dd86ae91749cb78b1901f0c` |

Katalogu `results/evidence/` nie ma i to jest treść werdyktu: wszystkie 25
przypadków kontroli semantycznej dały artefakty identyczne co do bajtu, więc
żaden plik surowy nie jest dowodem czegokolwiek poza własną zgodnością.
Zgodność jest zapisana w `results/semantic.json`, a tożsamość bajtów archiwum
potwierdza `results/raw.index.tsv`.

Pojedynczy artefakt wyjmuje się bez rozpakowywania całości:

```bash
grep w4_avg_000.desc results/raw.index.tsv
tar -xzOf results/raw.tar.gz raw/semantic/W4_Q32/ALGSTRUCT/w4_avg_000.desc
```

### Odtworzenie artefaktów

| Repozytorium | Commit | Branch |
|---|---|---|
| `retractordb` (kod) | `2a5aa86148cc4e76ccc0adb8f3e2fa9f450b9123` | `master` |
| `rdb-experiment` (skrypty i wyniki) | `c081a0bb889e148d3d8ffa201d9781c4b216e484` | `experiment/20260729_K5` |

```bash
git -C /home/michal/github/retractordb checkout 2a5aa861   # drzewo musi być czyste
git -C /home/michal/github/rdb-experiment checkout c081a0bb
cd /home/michal/github/rdb-experiment/results_20260729_K5_rerun
./run.sh                       # build_profiles.sh + generate.py + collect.py + semantic.py + verdict.py
```

`run.sh` weryfikuje commit kodu i czystość obu repozytoriów przed pierwszą
kompilacją, więc pomyłka w `checkout` zatrzymuje przebieg. Zgodność odtworzonych
artefaktów z zapisanymi sprawdza indeks:

```bash
python3 ../lib/artifacts.py index results/raw /tmp/raw.index.tsv
diff results/raw.index.tsv /tmp/raw.index.tsv
```

Zrzuty `stdout` kompilacji zawierają ścieżkę katalogu roboczego w `/dev/shm`
i nie są odtwarzalne bajtowo; porównywalne są artefakty silnika oraz liczniki
w `results/counts.json`.

## Odstępstwa

1. **R4, jeden commit.** Człowiek zezwolił 2026-07-29 na commity w trakcie
   realizacji na branchu `experiment/20260729_K5`.
2. **R9, `e1_probe.csv` i `metrics.csv`.** Nie powstają — dotyczą sondy
   czasowej, której ta kampania nie uruchamia.
3. **R14, kompaktowanie po fakcie.** Kampania powstała przed wprowadzeniem R14;
   archiwa utworzył `compact_results.sh` 2026-07-30. Treść artefaktów nie
   zmieniła się — dowodzą tego indeksy `SHA-256`.
