# K4 — profile reguł i `rewrite_applied`

Eksperyment domyka krok K4 planu badawczego: rozdziela regułę R1
(faktoryzacja dopasowanych przesunięć przeplotu) od R2 (przemienna
kanonizacja dzieci `STREAM_ADD`) i liczy ich zastosowania na istniejącym
korpusie RQL.

## Profile

| Profil | Deduplikacja | Współdzielenie SELECT | R2 | R1 |
|---|:---:|:---:|:---:|:---:|
| `OFF` | OFF | OFF | OFF | OFF |
| `STRUCT` | ON | ON | OFF | OFF |
| `STRUCT+R1` | ON | ON | OFF | ON |
| `STRUCT+R2` | ON | ON | ON | OFF |
| `ALGSTRUCT` | ON | ON | ON | ON |

Każdy profil jest osobnym buildem Release z sondą pomiarową. Skrypt uruchamia
pełny zestaw `it_optimizer_ablation-*`, a następnie kompiluje każdy plik RQL
z `test/IntegrationTest_serial`, `test/IntegrationTest_parallel` i
`examples/`.

## Znaczenie liczników

- `r1` rośnie po każdym skutecznym przepisaniu
  `(A>i)#(B>k) -> (A#B)>(i+k)`.
- `r2` liczy unikalne węzły `STREAM_ADD`, dla których kanoniczny odcisk
  rzeczywiście zamienił kolejność dzieci. Nie liczy ponownych odwiedzin tego
  samego węzła podczas rekurencyjnego tworzenia fingerprintu.

Licznik R2 oznacza zastosowanie prawa podczas kanonizacji, nie liczbę
ostatecznie usuniętych węzłów. Efekt strukturalny pozostaje osobną metryką
planu.

## Uruchomienie

```bash
./run.sh
```

Opcjonalnie:

```bash
RDB_CODE_REPO=/inna/sciezka/retractordb K4_BUILD_JOBS=2 ./run.sh
```

Eksperyment nie mierzy czasu i nie korzysta z workera PREEMPT_RT.
Nieoczekiwany błąd kompilacji, brak licznika albo licznik aktywny przy
wyłączonej regule unieważnia przebieg.

## Wynik

Wszystkie pięć profili przeszło po 6/6 testów `optimizer_ablation`.
Korpus obejmuje 80 plików RQL: 75 kompiluje się poprawnie, a 5 historycznych
lub celowo wadliwych fixture'ów jest jawnie sklasyfikowanych jako oczekiwane
odrzucenia.

- R1 zastosowano 5 razy w 5 plikach — wyłącznie w dedykowanych testach
  regresyjnych; żaden istniejący przykład nie aktywował R1.
- R2 zastosowano 18 razy w 13 plikach, w tym w 4 istniejących przykładach.
- Profile z wyłączoną regułą zachowały dla niej licznik równy zero.

Pełne agregaty i listę trafień zawiera
[`results/summary.md`](results/summary.md), dane jednostkowe są w
[`results/counts.csv`](results/counts.csv) i
[`results/counts.json`](results/counts.json), a zamrożony spis korpusu w
[`results/corpus.tsv`](results/corpus.tsv).

Brak trafień R1 poza dedykowanymi testami ogranicza możliwość wnioskowania
o wkładzie tej reguły w K5/K6 i musi pozostać jawnym zagrożeniem trafności.
