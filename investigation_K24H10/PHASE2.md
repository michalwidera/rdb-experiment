# Faza 2 — weryfikacja postaci docelowej offline, przed dotknięciem silnika

Data: 2026-08-18. Plan: `paper-arXiv/debs/plan-realizacji-k24h10.md`, faza 2.
Wejście: [`DERIVATION.md`](DERIVATION.md). **Bez silnika, bez workera.**
Skrypty: [`phase2_form.py`](phase2_form.py) (2a), [`phase2_scope.py`](phase2_scope.py) (2b),
[`phase2_threshold.py`](phase2_threshold.py) (2c).

Dyscyplina kroków 3c i 3d: postać jest sprawdzona na korpusie **zanim** zmieni
się `compiler.cpp`. Dzięki temu kampania K24e będzie przypięciem, nie loterią.

## 2a — postać docelowa wobec oracle'a

Liczona jest już postać w tej formie, w jakiej pójdzie do C++: przegląd okna
`[0, q)` po odwzorowaniach `Subtract` / `Div` / `Mod`, z progiem przejścia na
wariant zapasowy.

| Klasa | Izolowana `20260804` | Izolowana `20260807` | Zaniżeń |
|---|---|---|---|
| `-` | 4329/4329 (100%) | 4320/4320 (100%) | 0 |
| `Θ` | 2578/2578 (100%) | 2612/2612 (100%) | 0 |
| `~Θ` | 2503/2503 (100%) | 2619/2619 (100%) | 0 |
| pozostałe sześć klas | 100% | 100% | 0 |

**Wynik uboczny, ważniejszy niż sama bramka: kolumna PROPAGOWANA również
osiąga 100% we wszystkich dziewięciu klasach, na obu ziarnach** (35 545
i 35 583 węzłów). To nie jest przypadek, tylko konsekwencja składania: jeśli
każda reguła jest dokładna przy dokładnych ogonach składowych, dokładne jest
też złożenie. K24d miała tu 92,7% (`#`) do 99,5% (`>N`) właśnie dlatego, że trzy
reguły zawyżały i zawyżenie dziedziczyło się w górę planu.

**To jest przewidywanie dla fazy 4** i tak trzeba je predeklarować: kampania
K24e ma pokazać 100% w obu kolumnach, dla wszystkich dziewięciu klas. Odchyłka
oznaczałaby, że silnik nie implementuje postaci, którą tu sprawdzono.

## 2b — zasięg zmiany

Kontrola bez tautologii: węzeł klasy innej niż trzy naprawiane, w którego
**poddrzewie nie ma** ani jednego węzła tych klas, musi mieć ogon propagowany
identyczny z zamrożoną kolumną `replica_tail` kampanii K24d.

| Klasa | Węzłów bez naprawianej klasy w poddrzewie | Identycznych |
|---|---|---|
| `+` | 2331 / 2316 | **100%** |
| `@` | 4062 / 4058 | **100%** |
| `#` | 5356 / 5455 | **100%** |
| `PASS` | 4607 / 4477 | **100%** |
| redukcje | 3186 / 3153 | **100%** |
| `>N` | 5087 / 5213 | **100%** |

(liczby dla ziaren `20260804` / `20260807`)

Węzły, które **mają** naprawianą klasę w poddrzewie, wolno zmienić — i zmiana
idzie wyłącznie w stronę oracle'a: `ku oracle` 60/104/435/142/42/28 węzłów,
**`od oracle` 0** w każdej klasie i na obu ziarnach.

Zmiana rusza więc dokładnie to, co ma ruszać: trzy reguły plus dziedziczenie po
naprawionym dziecku.

## 2c — próg przeglądu, czyli zadanie, które zniknęło

Zadanie brzmiało: sprawdzić, czy powyżej progu przeglądu wariant zapasowy nie
zaniża. W trakcie okazało się, że **progu nie będzie**, bo postać docelowa jest
`O(1)` — dowód i weryfikacja w [`DERIVATION.md`](DERIVATION.md) §5.

Droga do tego wyniku szła przez wariant zapasowy. Zamiast przyjąć „dzisiejszą
regułę" na wiarę, wyprowadziłem oszacowanie `O(1)` z rozkładu `idx(n) = n·r + e(n)`:

```
W <= ceil( (c + 1 + W_src)/r ) - 1,     c = sup_n e(n)
```

Przemiatanie pokazało, że oszacowanie jest nie tylko bezpieczne, ale **ciasne
w 100% przypadków** — a to znaczy, że jest samą postacią dokładną, bo kres
`e(n) = c` jest osiągany (`gcd = 1` po skróceniu).

| Kontrola | `-` | `Θ` | `~Θ` |
|---|---|---|---|
| przemiatanie `q` do 60, `W_src` do 8: zaniżeń postaci `O(1)` | 0 / 19818 | 0 / 13218 | 0 / 13218 |
| tamże: przypadków `O(1)` `==` przegląd okresu | 100% | 100% | 100% |
| korpus, oba ziarna: `O(1)` `==` oracle | 100% | 100% | 100% |
| przemiatanie: niestabilności okresu (`q` wobec `20q`) | 0 | 0 | 0 |
| przemiatanie: zaniżeń **dzisiejszej** reguły jako wariantu zapasowego | 0 / 23121 | 0 / 15421 | 0 / 15421 |

Ostatni wiersz jest odpowiedzią na pierwotne zadanie 2c — dzisiejsza reguła
byłaby bezpiecznym wariantem zapasowym — ale jest już bezużyteczny, bo nie ma
czego zabezpieczać.

**Błąd aparatury, złapany po drodze.** Pierwsze przemiatanie zgłosiło 9270
zaniżeń dla `-`. Wszystkie były artefaktem: gałąź deklaracyjna była testowana
z `W_src > 0`, a deklaracja ma ogon zerowy z definicji, więc ta kombinacja
w żadnym planie nie występuje. Po rozdzieleniu gałęzi (`declared` jako osobny
argument, nie wyprowadzany z `child.kind`) zaniżeń jest zero. Wersja poprawiona
jest w [`phase2_threshold.py`](phase2_threshold.py); przypadek `p/q = 3/2`,
`W_src = 2` daje zapasowy 2 = dokładny 2.

## 3. Bramka fazy 2

| Zadanie | Kryterium | Wynik |
|---|---|---|
| 2a | 100% per klasa, oba ziarna, zero zaniżeń | **przeszło** (9/9 klas, także propagowana) |
| 2b | sześć klas niezmienionych co do węzła | **przeszło** (25 tys. węzłów identycznych, 811 zmian tylko ku oracle'owi) |
| 2c | wariant zapasowy nie zaniża | **bezprzedmiotowe** — postać jest `O(1)`, progu nie ma |

## 4. Przypadki ręczne do fazy 3 (3c)

Policzone i sprawdzone wobec oracle'a zdarzeniowego. Trzy pierwsze **zmieniają**
wynik wobec dzisiejszego silnika, czwarty jest bramką regresyjną (nie zmienia).

| # | RQL | Węzeł | Dziś | Po naprawie | Oracle |
|---|---|---|---|---|---|
| 1 | `DECLARE ... STREAM s1, 5/8` + `s1-5/2` | `-`, `d_out = 5/2` | 1 | **0** | 0 |
| 2 | `DECLARE ... STREAM s2, 1/2` + `s2&1` | `Θ`, `d_out = 1`, iloraz całkowity | 1 | **0** | 0 |
| 3 | `DECLARE ... STREAM s0, 1/16` + `s0&1/6` + `n0%1/5` | `~Θ`, `W_src = 1` | 1 | **0** | 0 |
| 4 | `DECLARE ... STREAM s0, 1/2` + `s0&3/2` | `Θ`, `d_out = 3/4` | 1 | 1 | 1 |
| 5 | `DECLARE ... STREAM s0, 1/2` + `s0&3/2` + `a0-2` | `-` nad składową obliczaną, `W_src = 1` | 1 | **0** | 0 |

Przypadek 3 pokazuje przy okazji, że `~Θ` myli się tylko przy niezerowym ogonie
składowej — dlatego w korpusie zawyża jedynie w 0,8% węzłów.

## 5. Co faza 2 zmienia w planie fazy 3

- `SOperations.hpp`: **trzy postacie `O(1)`**, nie wspólny przegląd; bez progu
  i bez wariantu zapasowego.
- `SubtractStartupLatency()` traci argument `sourceDeclared` — rachunek ogona
  przestaje zależeć od `isDeclaration()`.
- Zadanie 3c zyskuje piąty przypadek (`-` nad składową obliczaną) i traci
  przypadek „powyżej progu przeglądu", którego nie ma.
