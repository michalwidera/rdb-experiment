# Manifest K5

| Pole | Wartość |
|---|---|
| Identyfikator eksperymentu | `20260729_K5` |
| Krok planu badawczego | K5 — workload wielozapytaniowy `Q = 1,2,4,8,16,32`, punkt go/no-go |
| Data utworzenia | 2026-07-29 |
| Commit kodu | `0e0f70161fd46ffd918dbdb457e6dbdcd4439b03` |
| Branch kodu | `master` |
| Bazowy commit wyników | `0aae66f773cfc1c44875a999d84408bfc887f776` |
| Branch wyników | `experiment/20260729_K5` |
| Maszyna | `B850MDESK` (nadzorca) |
| Jądro | `6.18.33.2-microsoft-standard-WSL2` |
| Worker pomiarowy | **nie użyty** |
| SHA-256 `README.md` | `922afa8538a9608bec8fe78c656c977ca84e9eb6f2b43def3054ab44e37976d6` |

## Dlaczego bez workera

Kryterium go/no-go K5 jest rozstrzygane compile-only i kampania nie rejestruje
żadnej metryki czasowej. Warunki `REQUIREMENTS.md` R7 (PREEMPT_RT, governor
`performance`, izolowany rdzeń, `SCHED_FIFO`) nie mają wpływu na wynik
`xretractor w.rql -c`, a akapit „Zakres" tego samego dokumentu wprost wyłącza
kampanie niemierzące czasu spod procedury nadzorcy. Precedensem jest K4 — ta
sama klasa pomiaru, wykonana lokalnie.

Worker wchodzi dopiero w K6.

## Zgodność z REQUIREMENTS.md

| Wymaganie | Zastosowanie |
|---|---|
| R1 dwa repozytoria | kod `retractordb` @ `master`, wyniki `rdb-experiment` @ `experiment/20260729_K5` |
| R2 zakaz zapisu do repo kodu | kompilacje w kopii roboczej poza repozytorium; `git status` sprawdzany przed i po |
| R3 katalog docelowy | `results_20260729_K5/`, bez rotacji |
| R4 branch i commity | commity w trakcie realizacji dozwolone przez człowieka (odstępstwo od reguły jednego commita, uzgodnione 2026-07-29) |
| R5 warunki wejściowe | oba repozytoria czyste, commit kodu przypięty w `run.sh` |
| R6 build pomiarowy | pięć profili Release z `RDB_BENCH_PROBE=ON`, `--build-info` weryfikowane bajtowo |
| R7 środowisko RT | **nie dotyczy** — kampania bez metryk czasowych |
| R9 rejestrowane dane | `state_before.md`, `state_after.md`, dane surowe, `summary.md` |
| R12 odtwarzalność | ten manifest, `README.md` z SHA-256, wpis w `JOURNAL.md` |
| R13 wykrywanie workera | **nie dotyczy** |

## Odstępstwa

1. **R4, jeden commit.** Człowiek zezwolił 2026-07-29 na commity w trakcie
   realizacji na branchu `experiment/20260729_K5`. Branch zawiera zatem
   historię kroków kampanii, a nie pojedynczy commit.
2. **R9, `e1_probe.csv` i `metrics.csv`.** Nie powstają — dotyczą sondy
   czasowej, której ta kampania nie uruchamia.
