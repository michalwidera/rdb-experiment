# Strona Flinka kampanii K23

Produkt kroku „strona Flinka na hoście" (2026-08-08), wykonanego po zamknięciu **D-2**.
Raport: [`PLANY_FLINKA.md`](PLANY_FLINKA.md).

**Nic tutaj nie mierzy kosztu.** Predeklaracja jest niezamrożona (STOP-5), więc pomiar
kosztowy jest zabroniony; joby budują się i zapisują plany, ale nie są uruchamiane
(`--plan-only` kończy się przed `env.execute()`). Aparatura nie ma zegara ściennego.

| Plik | Co to jest |
|---|---|
| `PLANY_FLINKA.md` | raport kroku: środowisko, bramka serializera, sześć jobów, plany, instancje, zestawienie z pilotem |
| `env_inventory.sh` | krok A — inwentarz środowiska hosta → `results/flink_environment.tsv` |
| `canonical_vectors.tsv` | 18 wektorów o znanej odpowiedzi; wspólne wejście obu stron serializera |
| `oracle/canonical_oracle.cc`, `oracle/build_oracle.sh` | oracle C++ — linkuje `rdb::probe::canonicalRecordBytes` z `librdb.a`, bez własnej implementacji i bez zmian w `retractordb` |
| `java/Canon.java` | kanoniczny serializer po stronie Flinka + liczniki logicznych zapisów |
| `java/CanonTest.java` | bramka kroku B: Java wobec kolumny oczekiwanej **i** wobec oracle'a |
| `java/K23Ops.java` | operatory wspólne trzech rodzin; tu mieszka zamrożona granulacja podplanu |
| `java/PlanDump.java` | krok D — plan logiczny, plan fizyczny, zliczenie instancji, kontrola konwencji nazw |
| `java/F9R2Job.java`, `java/F9R1Job.java`, `java/F9XJob.java` | trzy rodziny, każda z wariantem `natural` i `manual` |
| `build_flink.sh` | kompilacja przypiętym JDK 17 wobec przypiętego Flinka 2.3.0 (bez Mavena) |
| `dump_plans.sh` | krok D dla komórki rozstrzygającej `Q = 8` → `plans/`, `results/flink_instances.tsv` |
| `sweep_q.sh` | krzywa flinkowa po siatce `Q = {1,2,4,8,16,32}` → `results/flink_q_curve.tsv` |
| `plans/` | plany logiczny (JSON i TSV) oraz fizyczny szesciu jobów przy `Q = 8`, plus rozbicie węzłów podplanu |
| `results/` | `flink_environment.tsv`, `canonical_oracle_cpp.tsv`, `flink_instances.tsv`, `flink_q_curve.tsv` |

Czego tu nie ma: `build/` (produkt `javac`, poza gitem), plików per-`Q` z przemiatania
(zachowany jest wyłącznie materiał planistyczny komórki `Q = 8`).

## Pułapki potwierdzone w tym kroku

* **Domyślne `java` na hoście to 25.0.3, nie 17.0.19.** Wszystkie skrypty przypinają JDK
  ścieżką. `freeze_check.sh` musi sprawdzać ścieżkę i wersję, nie samo `java -version`.
* **Przeplot nie może siedzieć w źródle** (jak w aparaturze K22) — włożyłby badany węzeł
  do ingressu, czyli wyjął go z metryki.
* **Liczba węzłów ≠ liczba jednostek bajtowych.** F9-R1 `FLINK_NATURAL` ma 12 węzłów i
  8 jednostek. Ta sama pułapka, którą pilot odnotował po stronie RetractorDB.
* **`FLINK_MANUAL` nie jest best case przy `Q ≤ 2`** — w F9-X przy `Q = 1` jest gorszy od
  `FLINK_NATURAL` (5,000 wobec 4,000 jednostek), bo ręczne wydzielenie materializuje węzeł,
  który pojedynczy monitor policzyłby w swoim etapie publicznym.
* **Łańcuchowanie operatorów Flinka nie jest współdzieleniem podplanu.** Cztery identyczne
  operatory trafiają do jednego wierzchołka JobGraphu, ale zostają czterema instancjami.
