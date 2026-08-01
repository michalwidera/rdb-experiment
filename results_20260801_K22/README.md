# K22 — deklaratywny koszt specyfikacji i modyfikacji monitora

**Stan: etap K22a (audyt i predeklaracja). Wynik NIE istnieje.**

Kampania bada, czy dla semantycznie równoważnych statycznych potoków
regularnych RQL zawiera mniej jawnych konstrukcji sterowania i stanu oraz
wymaga zmian w mniejszej liczbie jednostek programu niż proceduralna pętla
slotowa (Python) i stanowe API ogólnego dataflow (Flink DataStream).

K22 **nie** mierzy szybkości. To był P0/K6, zamknięty werdyktem A=0/B=12/C=1.
K22 **nie** jest badaniem ludzi: nie odpowiada na pytanie o zrozumiałość ani
produktywność. Potok ECG jest niekliniczny — bez twierdzeń diagnostycznych.

## Co jest w tym katalogu na etapie K22a

| Ścieżka | Zawartość | Stan |
|---|---|---|
| `PREDECLARATION.md` | zamrożone rodziny, zadania, metryki, oracle, GO/NO-GO | **projekt do przeglądu** |
| `coding_manual.md` | mechaniczne reguły zliczania i `rule_id` każdego trafienia | **projekt do przeglądu** |
| `manifest.md` | rewizje, provenance, odtwarzalność (`REQUIREMENTS.md` R12) | wypełniony częściowo |
| `oracle/refsem.py` | semantyka referencyjna — arytmetyka silnika `abe075e` | gotowe, przetestowane |
| `oracle/compare.py` | komparator strumieni kanonicznych | gotowe, przetestowane |
| `oracle/run.sh` | bramka etapowa; zatrzymuje się, bo korpus nie istnieje | gotowe |
| `metrics/measure.py` | statyczne metryki konstrukcji + surowa tabela trafień | gotowe, przetestowane |
| `tests/test_k22a.sh` | testy o znanej odpowiedzi całej aparatury | **61 kontroli, przechodzą** |
| `corpus/`, `tasks/` | układ katalogów, bez programów | puste (K22b/K22c) |
| `results/` | tabele i werdykt | puste (K22d) |

## Uruchomienie aparatury

```bash
./tests/test_k22a.sh      # 3 zestawy: semantyka referencyjna, komparator, metryki
./oracle/run.sh           # bramka: zatrzyma sie, dopoki korpus nie istnieje
```

Aparatura, która nie przechodzi własnych testów, nie może rozstrzygać hipotezy.
Dlatego `oracle/run.sh` uruchamia je jako pierwszy krok.

## Bramka

**Bez zaakceptowanej i utrwalonej `PREDECLARATION.md` nie wolno przejść do
K22b.** Predeklaracja zamraża definicje przed zobaczeniem jakiejkolwiek liczby;
utrwalenie jej po obejrzeniu wyniku nie byłoby predeklaracją.

Dodatkowy warunek utrwalenia: doprecyzowanie kryterium go/no-go
(`PREDECLARATION.md` §8.1) musi najpierw trafić do `paper-arXiv/debs/research_plan.md`.

## Dlaczego rdzenie Python i Flink powstają od nowa

Istniejące `config/pan_tompkins_numpy.py` (211 linii) i
`config/PanTompkinsFlinkJob.java` (344 linie) są baseline'ami **czasowymi**:
zawierają parser argumentów, `SCHED_FIFO`, sondę CSV, tryb batch, `Tuple8`
niosący znaczniki czasu. Ich surowy LOC nie wchodzi do żadnej tabeli K22.

Poważniejszy powód: oba liczą w `float64`, a silnik liczy w liczbach
całkowitych z pośrednim `boost::rational<int>` — w szczególności `.avg` dzieli
przez liczbę pól **nie-`NULL`**, a nie przez szerokość okna. Zero-fill obu
baseline'ów rozjeżdża się z silnikiem na całym ogonie startowym. Szczegóły
i odniesienia do kodu: `PREDECLARATION.md` §4.

## Kolejne etapy

`K22b` równoważny korpus → `K22c` 36 wariantów M1–M4 → `K22d` metryki i werdykt
→ `K22e` publikacja. Worker RT jest niepotrzebny w całym K22.
