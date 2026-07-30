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

## Artefakty surowe

Kampania wytworzyła 2816 surowych plików artefaktów silnika. Zgodnie z
`REQUIREMENTS.md` R14 w katalogu zostały dowody porażki jako pliki, a całość
w archiwach:

| Archiwum | Plików | Bajtów | SHA-256 |
|---|---:|---:|---|
| `results/raw.tar.gz` | 2701 | 85273 | `975af64bc94cef2949fdfbc442866c8486deadc9acfee7bde840e35ecea99460` |
| `results/workloads.tar.gz` | 115 | 7460 | `c145b94a23c13116e541b5c58fcbad474a691a9530565ad5b987186d528aef15` |

Indeksy `results/raw.index.tsv` i `results/workloads.index.tsv` wymieniają każdy
plik z rozmiarem i `SHA-256`, więc pojedynczy artefakt można odnaleźć i wyjąć
bez rozpakowywania całości:

```bash
tar -xzOf results/raw.tar.gz raw/semantic/W8_Q01/STRUCT/mwi.desc
```

### Dowody porażki

`results/evidence/semantic/W8_Q{01..32}/{STRUCT,ALGSTRUCT}/{mlii,mwi}.desc` —
24 pliki, po dwa deskryptory na profil dla każdego z sześciu przypadków `W8`.
To są artefakty imiennie wskazane w `results/semantic.json` jako różnica
bajtowa, czyli materialna treść werdyktu NO-GO tej kampanii. Pozostałe pliki
tych przypadków (dane strumieni, `.meta`, `.shadow`, substraty) niosły tylko
potwierdzenie zgodności i są w archiwum.

### Odtworzenie artefaktów

Artefakty odtwarza para commitów: kod i skrypty kampanii.

| Repozytorium | Commit | Branch |
|---|---|---|
| `retractordb` (kod) | `0e0f70161fd46ffd918dbdb457e6dbdcd4439b03` | `master` |
| `rdb-experiment` (skrypty i wyniki) | `b32c9d2f202e56cf17a3a07b83622ccedd9b67a7` | `experiment/20260729_K5` |

```bash
git -C /home/michal/github/retractordb checkout 0e0f7016   # drzewo musi być czyste
git -C /home/michal/github/rdb-experiment checkout b32c9d2f
cd /home/michal/github/rdb-experiment/results_20260729_K5
./run.sh                       # build_profiles.sh + generate.py + collect.py + semantic.py + verdict.py
```

`run.sh` sam sprawdza commit kodu i czystość obu repozytoriów, więc pomyłka
w kroku `checkout` zatrzymuje przebieg, zamiast wytworzyć artefakty z innego
kodu. Zgodność odtworzonego drzewa z zapisanym sprawdza indeks:

```bash
python3 ../lib/artifacts.py index results/raw /tmp/raw.index.tsv
diff results/raw.index.tsv /tmp/raw.index.tsv
```

Nazwy plików tymczasowych zawierają katalog roboczy `/dev/shm`, więc zrzuty
`stdout` kompilacji nie są odtwarzalne bajtowo — porównywalne są wyłącznie
artefakty silnika i sparsowane liczniki w `results/counts.json`.

## Odstępstwa

1. **R4, jeden commit.** Człowiek zezwolił 2026-07-29 na commity w trakcie
   realizacji na branchu `experiment/20260729_K5`. Branch zawiera zatem
   historię kroków kampanii, a nie pojedynczy commit.
2. **R9, `e1_probe.csv` i `metrics.csv`.** Nie powstają — dotyczą sondy
   czasowej, której ta kampania nie uruchamia.
3. **R14, kompaktowanie po fakcie.** Kampania powstała przed wprowadzeniem R14;
   archiwa i `results/evidence/` utworzył `compact_results.sh` 2026-07-30.
   Treść artefaktów nie zmieniła się — dowodzą tego indeksy `SHA-256`.
