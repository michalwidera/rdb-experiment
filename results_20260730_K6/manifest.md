# Manifest K6

| Pole | Wartość |
|---|---|
| Identyfikator eksperymentu | `20260730_K6` |
| Krok planu badawczego | K6 — kampania ablacyjna z powtórzeniami; luka G8 i kosztowa część G14 |
| Data utworzenia | 2026-07-30 |
| Commit kodu | `bb3a5216b952432818b23a26365001fe4f7627f5` |
| Branch kodu | `master` |
| Zmiany w kodzie silnika | **brak** — instrumentacja kompletna po K5i |
| Bazowy commit wyników | `ea36fa5bda67e6432decca3552c3e05f1d0ea674` |
| Branch wyników | `experiment/20260730_K6` |
| Nadzorca | `B850MDESK`, Linux `6.18.33.2-microsoft-standard-WSL2` |
| Worker pomiarowy | żądany `192.168.88.21`, hostname `pi400`, PREEMPT_RT `#50-Ubuntu`, `isolcpus=3 nohz_full=3 rcu_nocbs=3` |
| SHA-256 `README.md` | `050f5f4a2decf8f8dd185000887d453611a20d0a2d787f1965212ded171dfe92` (z addendum K6.1b) |

Pola wyznaczane w trakcie kampanii — rzeczywisty adres workera, wybrany mnożnik
rate'u `s`, liczby przebiegów i sumy kontrolne archiwów — są dopisywane do tego
manifestu po zakończeniu odpowiednich kroków.

## Dlaczego bez brancha w repozytorium kodu

K6 mierzy kod, którego nie zmienia. Wszystkie metryki §9.2 mają instrument
w `bb3a521`:

| Metryka | Instrument | Plik |
|---|---|---|
| rozmiar planu, tokeny, dedup | `PLAN bench` | `src/retractor/lib/compiler.cpp` |
| atrybucja reguł | `REWRITE_APPLIED` | `src/retractor/lib/compiler.cpp` |
| czas kompilacji | `COMPILE_NS` | `src/retractor/lib/compiler.cpp` |
| rozmiar buforów | `PLAN capacity` | `src/retractor/lib/compiler.cpp` |
| materializacje | `MATERIALIZED` | `src/retractor/lib/executorsm.cpp` |
| compute, jitter, queue-emission | sonda E1 | `src/retractor/lib/executorsm.cpp` |
| peak RSS, CPU, checksum | poza silnikiem | harness |

Ablacja infrastruktury z §9.2 (persistence/metadata/IPC, integer vs rational
scheduling) świadomie nie istnieje — decyzja K5i; kryterium ukończenia K6 jej
nie wymaga.

## Zgodność z REQUIREMENTS.md

Pełna tabela w `README.md`. Odstępstwo: R4 — człowiek zezwolił 2026-07-30 na
commity i push w trakcie realizacji, na nadzorcy i na workerze.

## Odtworzenie kampanii

Kolejność jest istotna: kalibracja ustala `s`, którym karmione są oba tiery.

```bash
# 0. Nadzorca: kontrola wejściowa i macierz funkcjonalna pięciu profili.
cd results_20260730_K6
./build_profiles.sh                                     # 5 profili, --build-info bajtowo
K6_RUN_CTEST=1 K6_RAW_DIR=/dev/shm/k6-ctest ./build_profiles.sh
python3 generate.py --output /dev/shm/k6-w --scale 36
python3 check_counters.py --code-repo ../../retractordb \
        --workloads /dev/shm/k6-w --output results

# 1. Worker: profile pomiarowe (ccache, wszystkie rdzenie, capabilities RT).
K6_BUILD_JOBS=4 K6_CPUS=0-3 K6_CCACHE=1 K6_SETCAP=1 ./build_profiles.sh

# 2. Worker: kalibracja (K6.0), Tier A (K6.3), saturacja (K6.5).
worker/run_k6_step.sh --step calibrate  --code-commit <SHA> --experiment-branch <B> --results-root results_20260730_K6
worker/run_k6_step.sh --step tier-a     --scale <S> ...
worker/run_k6_step.sh --step saturation --scale <S> ...

# 3. Nadzorca: Tier B — siedem badań, reboot między badaniami.
./start_supervisor.sh ablation --experiment-id 20260730_K6 --scale <S> --skip-build

# 4. Nadzorca: analiza i werdykt.
python3 results_20260730_K6/analyze.py \
        --runs results_20260730_K6/ablation/study_*/runs.csv \
        --compile-runs results_20260730_K6/results/compile_runs.csv \
        --output results_20260730_K6/results
```

## Defekt naprawiony w preflight

Repozytorium kodu zawierało 34 artefakty silnika w katalogu wejściowym
`examples/ecg/rec205/`, niewidoczne dla `git status --short`, bo wypisane
w `.gitignore`. Naprawa objęła usunięcie artefaktów, utwardzenie kontroli R2
w `lib/common.sh`, regresję `tests/test_code_guard.sh` i przepisanie R2/R11.
Pełny zapis: `JOURNAL.md`, wpis z 2026-07-30.
