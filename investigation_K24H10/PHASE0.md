# Faza 0 — falsyfikacja hipotezy scalajacej H-scal

Data: 2026-08-18. Plan: `paper-arXiv/debs/plan-realizacji-k24h10.md`, faza 0.
Gałąź silnika: `issue_232-k24h10` (silnika ta faza **nie dotyka**).

**Bez workera, bez pomiaru czasu, bez uruchamiania silnika.** Materiał wejściowy
to zamrożone CSV kampanii K24d (`results_20260807_K24d/raw/`) i korpus odtworzony
z ziarna przez `generator.generate()` (ten sam plik, bajtowo bez zmian).
Czas przebiegu: ~6 s na obu ziarnach łącznie.

## Co było testowane

Kandydat H-scal — przegląd **jednego** okresu fazowego warunku dostępności:

```
W = max(0, max_{n in [O, O+P)} [ ceil((idx(n)+1+W_src)*d_src/d_out) - 1 - n ])
```

`idx(n)` z `model.dependencies()`, `O` = `oracle_origin`, `W_src` = `oracle_c1`
składowej (atrybucja izolowana), `P = p+q` z `plan.period_hint()`.

## Wynik — bramka fazy 0

Skrypt: [`phase0_scan.py`](phase0_scan.py).

| Ziarno | Klasa | Węzłów | Zgodnych z `oracle_c1` | Zaniżeń | Zawyżeń | Okres stabilny (P vs 4P) |
|---|---|---|---|---|---|---|
| 20260804 | `-` | 4329 | **4329 (100%)** | 0 | 0 | 4329/4329 |
| 20260804 | `Θ` | 2578 | **2578 (100%)** | 0 | 0 | 2578/2578 |
| 20260804 | `~Θ` | 2503 | **2503 (100%)** | 0 | 0 | 2503/2503 |
| 20260807 | `-` | 4320 | **4320 (100%)** | 0 | 0 | 4320/4320 |
| 20260807 | `Θ` | 2612 | **2612 (100%)** | 0 | 0 | 2612/2612 |
| 20260807 | `~Θ` | 2619 | **2619 (100%)** | 0 | 0 | 2619/2619 |

Plik rozjazdów `raw/phase0_misses.csv` **nie powstał** — zero wierszy.

Kontrola niesprzeczności (zadanie 0d): na węzłach, gdzie silnik już dziś zgadza
się z oracle'em, kandydat daje **tę samą** wartość — 286/286, 1365/1365,
2455/2455 (ziarno `20260804`) i 292/292, 1404/1404, 2573/2573 (`20260807`).
Postać nie psuje żadnego węzła dziś poprawnego.

**H-scal trzyma. Jedna postać, trzy wejścia — plan nie rozgałęzia się.**

## Diagnostyka do fazy 1

Skrypt: [`phase0_stats.py`](phase0_stats.py).

### 1. Odtworzenie kolumny izolowanej K24d

| Klasa | Izolowana zgodność (`20260804`) | REPORT.md K24d §2 | Rozjazd |
|---|---|---|---|
| `-` | 828/4329 = 19,1% | 19,1% | `+1` w 3501, `0` w 828 |
| `Θ` | 1540/2578 = 59,7% | 59,7% | `+1` w 1038, `0` w 1540 |
| `~Θ` | 2483/2503 = 99,2% | 99,2% | `+1` w 20, `0` w 2483 |

Liczby zgadzają się co do węzła — rekonstrukcja odniesienia jest poprawna.
Rozjazd jest **wyłącznie `+1`**, nigdy `-1`, na obu ziarnach. Na ziarnie
`20260807` odpowiednio 19,3%, 60,7%, 99,4%.

### 2. Okres fazowy jest mały

`P = p+q`: `-` — mediana 5, max **11**; `Θ` i `~Θ` — mediana 7, max **13**.
Koszt przeglądu jest w korpusie pomijalny; próg w rodzaju
`kHashPhaseScanLimit` będzie zabezpieczeniem przed patologicznym `p+q`,
nie mechanizmem używanym realnie.

### 3. Człon własny NIE jest stałą — postaci `O(1)` nie ma

Człon własny = `oracle_c1 − ceil(W_src·d_src/d_out)`, czyli to, co dokładny
rachunek dokłada do generycznego przeliczenia. Rozkład (ziarno `20260804`):

| Klasa | Człon własny | Wniosek |
|---|---|---|
| `-` | `0` w 4212, **`−1` w 117** | generyczne przeliczenie samo w sobie potrafi zawyżyć o slot |
| `Θ` | `+1` w 1540, **`0` w 1038** | dzisiejsze bezwarunkowe `++result` jest błędne dla 40% węzłów |
| `~Θ` | `0` w 2483, **`−1` w 20** | dzisiejsze `+0` zawyża tam, gdzie zaokrąglenie bazy było za hojne |

Rozbicie po `(p, q)` pokazuje, że człon własny **nie jest funkcją samego
`(p, q)`**: dla `Θ` przy ilorazie całkowitym (`(2,1)`, `(3,1)`) wychodzi zawsze
`0`, ale przy `(3,2)` rozkłada się na `0` w 99 i `1` w 287 węzłów — o wartości
decyduje również `W_src`. To rozstrzyga pytanie z zadania 1a **przecząco**:
dla tych trzech klas nie ma postaci `O(1)` analogicznej do `+` czy `@`;
dokładna postać jest przeglądowa, `O(p+q)`, dokładnie jak w klasie `#`.

Uboczny wniosek diagnostyczny: **`Θ` przy ilorazie całkowitym ma człon własny
zerowy w 100% węzłów**. Dzisiejszy komentarz w `compiler.cpp`
(„Θ zawsze wyprzedza swój slot o mniej niż jeden okres wyjścia. Jeden slot jest
dokładnym własnym ogonem operatora”) jest w tym zakresie po prostu nieprawdziwy.

## Status epistemiczny — do raportowania dosłownie

Kandydat używa `model.dependencies()`, czyli **tego samego odwzorowania
indeksu**, co oracle. Faza 0 nie jest więc niezależnym potwierdzeniem
odwzorowania — testuje wyłącznie tezę „jeden okres fazowy wystarcza” przy
odwzorowaniu przyjętym za dane. Niezależność wraca w fazie 4: tam po jednej
stronie stoi zrzut planu silnika (rachunek w C++, pisany osobno), a po drugiej
oracle zdarzeniowy.

To ten sam status, jaki miały kontrole offline kroków 3c i 3d — i z tego samego
powodu kampania końcowa jest **przypięciem**, a nie loterią.

## Decyzja

Wchodzimy w fazę 1 bez rozgałęzienia: jedna postać przeglądowa `O(p+q)`
z trzema odwzorowaniami indeksu, próg bezpieczeństwa jak w `#`.
Zadanie 1a ma już odpowiedź negatywną co do `O(1)`; zostaje formalny argument
o okresowości `idx(n) − n·(d_out/d_src)` i rozstrzygnięcie gałęzi
`sourceDeclared` w `SubtractStartupLatency()` (zadanie 1b).
