# Faza 1 — wyprowadzenie postaci zamkniętych dla `-`, `Θ`, `~Θ`

Data: 2026-08-18. Plan: `paper-arXiv/debs/plan-realizacji-k24h10.md`, faza 1.
Wejście: [`PHASE0.md`](PHASE0.md) (H-scal potwierdzona, brak postaci `O(1)`).
**Bez silnika, bez workera.** Kontrole: [`phase1_checks.py`](phase1_checks.py).

## 1. Lemat okresowości

Rozważamy węzeł jednoargumentowy o interwale `d_out` nad składową o interwale
`d_src` i ogonie `W_src`, którego rekord `n` czyta rekord `idx(n)` składowej.
Warunek dostępności (konwencja C1) dla slotu `n` brzmi

```
W >= f(n),    f(n) = ceil( (idx(n) + 1 + W_src) * d_src/d_out ) - 1 - n,
```

a ogon węzła to `W = max(0, sup_n f(n))`.

**Lemat.** Jeżeli istnieje `T ∈ N+` takie, że dla każdego `n`

```
idx(n + T) = idx(n) + T * d_out/d_src        oraz     T * d_out/d_src ∈ N,
```

to `f(n + T) = f(n)`.

*Dowód.* Niech `k = T*d_out/d_src ∈ N`. Wtedy

```
f(n+T) = ceil( (idx(n) + k + 1 + W_src) * d_src/d_out ) - 1 - n - T
       = ceil( (idx(n) + 1 + W_src) * d_src/d_out + k*d_src/d_out ) - 1 - n - T
       = ceil( (idx(n) + 1 + W_src) * d_src/d_out ) + T - 1 - n - T = f(n),
```

bo `k*d_src/d_out = T ∈ N` wolno wynieść przed sufit. ∎

**Wniosek.** `sup_n f(n)` jest maksimum po **dowolnym** oknie długości `T`,
w szczególności po `[0, T)` — bez wiedzy o początku logicznym węzła.

Warunek lematu mówi dokładnie tyle: przez `T` slotów wyjścia odwzorowanie
indeksu przesuwa się o tyle rekordów składowej, ile ich w tym czasie powstaje.
Wtedy faza odczytu wraca do punktu wyjścia.

## 2. Instancjacja — `T = q` dla wszystkich trzech klas

Niech `d_out/d_src = p/q` po skróceniu. Dla każdej z trzech klas `T = q`.

### `-` (C-Delta, `Subtract`)

`idx(n) = ceil(n * d_out/d_src) = ceil(n*p/q)` (dla `d_out = d_src` tożsamość,
co jest przypadkiem `p = q = 1`).

```
idx(n+q) = ceil((n+q)p/q) = ceil(np/q) + p = idx(n) + p,     q * d_out/d_src = p ∈ N.
```

### `Θ` (`Div`)

`idx(n) = n + ceil((n+1) * d_out/param)`, gdzie `param` jest interwałem drugiej
składowej przeplotu. Z definicji rozplotu `1/d_src = 1/d_out + 1/param`, więc
przy `d_out/param = a/b` po skróceniu mamy `d_out/d_src = (a+b)/b`, a ponieważ
`gcd(a,b)=1` daje `gcd(a+b,b)=1`, ułamek ten jest już skrócony: `p = a+b`, `q = b`.

```
idx(n+b) = (n+b) + ceil((n+b+1)a/b) = idx(n) + a + b,        b * d_out/d_src = a+b ∈ N.
```

### `~Θ` (`Mod`)

`idx(n) = n + floor(n * d_out/param)`, `param` = interwał pierwszej składowej.
Ten sam rachunek: `d_out/param = a/b`, `d_out/d_src = (a+b)/b = p/q`, `q = b`,

```
idx(n+b) = (n+b) + floor((n+b)a/b) = idx(n) + a + b.
```

**Postać zamknięta (jedna, trzy wejścia):**

```
W = max(0, max_{n in [0, q)} [ ceil( (idx(n) + 1 + W_src) * d_src/d_out ) - 1 - n ])
```

Koszt: `O(q)` operacji wymiernych. W korpusie K24 `q <= 3` dla `-` oraz `q <= 5`
dla `Θ` i `~Θ` — przegląd jest tańszy niż dzisiejszy rachunek fazowy klasy `#`
(`O(p+q)`, tam do 24 557).

## 3. Kontrole wyprowadzenia na korpusie

| Kontrola | `-` | `Θ` | `~Θ` |
|---|---|---|---|
| **K1** okres ciasny `T=q` daje to samo co `P=p+q` z fazy 0 | 4329/4329 | 2578/2578 | 2503/2503 |
| **K2** przegląd od `n=0` daje to samo co od `n=O` | 4329/4329 | 2578/2578 | 2503/2503 |

Ziarno `20260804`; na `20260807` odpowiednio 4320, 2612, 2619 — również 100%.

K2 jest kontrolą **implementacyjną**: potwierdza wniosek z lematu, że
`computeStartupLatency()` nie musi znać początku logicznego i nie wchodzi
w zależność od kolejności wobec `computeLogicalOrigin()`. Klasa `#` ma dziś
dokładnie ten sam argument, sprawdzony w K24p.

## 4. Zadanie 1b — gałąź `sourceDeclared` w `SubtractStartupLatency()`

**Werdykt: gałąź znika.** Nie jest to uproszczenie, tylko usunięcie protezy
najgorszej fazy, i ma dowód liczbowy.

Podpopulacja: węzły `-` o składowej będącej deklaracją (2669 i 2670 węzłów).

| Wielkość | Ziarno 20260804 | Ziarno 20260807 |
|---|---|---|
| kandydat `==` oracle C1 | 2669/2669 | 2670/2670 |
| **silnik − kandydat** | `+1` w **2669/2669** | `+1` w **2670/2670** |
| silnik `==` oracle C1 | 0/2669 | 0/2670 |
| silnik `==` oracle C2 | 722/2669 | 698/2670 |

Gałąź deklaracyjna dokłada slot **zawsze**, nie „przy fazie całkowitej".
Jej uzasadnienie w komentarzu (`źródło jest publikowane po konsumentach w tym
samym takcie`) jest twierdzeniem o konwencji dostępności, więc sprawdziłem, jak
z deklaracjami obchodzi się **reszta rachunku silnika**. Węzły, których
wszystkie składowe są deklaracjami, reguła izolowana wobec obu konwencji:

| Klasa | `== C1` | `== C2` |
|---|---|---|
| `PASS`, `REDUCE` | **100%** | 0% |
| `+`, `@`, `#` | **100%** | 69,0% / 48,7% / 48,0% |
| `>N`, `~Θ` | **100%** | 100% (obie konwencje pokrywają się na tej podpopulacji) |
| `Θ` | 71,1% | **100%** |
| `-` | **0%** | 27,1% |

Siedem klas czyta deklaracje w konwencji **C1** i jest w niej dokładnych.
Dwie klasy — dokładnie te dwie, które dokładają stały człon własny (`-` przez
fazę `(q-1)/q`, `Θ` przez bezwarunkowe `++result`) — systematycznie lądują na
`C2`. Wniosek: to nie deklaracje wymagają dodatkowego slotu, tylko te dwie
reguły zostały napisane przy niejawnym założeniu „odczyt w tym samym takcie
jest niedozwolony", sprzecznym z resztą własnego rachunku silnika.

**Do wiadomości człowieka (nie blokuje fazy 2).** Formalnie jest to ten sam typ
pytania, co F9: albo cały silnik jest C1 i te dwie reguły mylą się o slot, albo
deklaracje wymagają C2 i myli się siedem pozostałych klas. Kampania K24
**predeklarowała C1** jako konwencję werdyktu, a siedem klas niezależnie ją
implementuje, więc wyprowadzenie idzie dalej w C1. Gdyby człowiek rozstrzygnął
odwrotnie, zmiana dotyczy siedmiu klas i całego artykułu, nie tej pozycji.

## 5. Zadanie 1c — materiał do `SOperations.hpp` (do wklejenia w fazie 3)

Odwzorowania indeksu **już istnieją** w `SOperations.hpp` i są używane przez
`computeLogicalOrigin()`: `Subtract(d_src, d_out, n)`, `Div(d_out, param, n)`,
`Mod(param, d_out, n)`. Faza 3 nie pisze nowych odwzorowań — przegląd wywołuje
te same funkcje, co rachunek początku logicznego. To zarazem kontrola spójności:
jedna definicja odwzorowania obsługuje obie wielkości.

Szkic wspólnej funkcji:

```cpp
// Ogon operatora jednoargumentowego o odwzorowaniu indeksu `indexMap`.
// Warunek dostępności dla slotu n: rekord indexMap(n) składowej jest określony
// w chwili (indexMap(n)+1+W_src)*d_src, a slot n kończy się w (n+1+W)*d_out, więc
//   W >= ceil( (indexMap(n)+1+W_src) * d_src/d_out ) - 1 - n.
// Prawa strona jest okresowa o okresie q = mianownik skróconego d_out/d_src:
// przez q slotów wyjścia odwzorowanie przesuwa się o dokładnie p rekordów
// składowej (p/q = d_out/d_src), więc faza odczytu wraca do punktu wyjścia
// (lemat okresowości, investigation_K24H10/DERIVATION.md §1). Maksimum po
// [0, q) jest zatem maksimum po wszystkich slotach — przegląd nie potrzebuje
// początku logicznego i nie wiąże się z kolejnością wobec computeLogicalOrigin().
//
// Koszt O(q). Powyżej kPhaseScanLimit wraca postać zawyżająca sprzed 2026-08-18:
// zaniżenie ogona oznacza rekord wyemitowany przed określeniem zależności,
// zawyżenie — tylko slot opóźnienia.
template <typename IndexMap>
inline int ScanStartupLatency(const rational<int> &deltaSource, const rational<int> &deltaTarget,
                              const int sourceLatency, IndexMap indexMap);
```

Trzy wejścia i to, co znika:

| Klasa | `indexMap(n)` | Co znika z dzisiejszego rachunku |
|---|---|---|
| `-` | `Subtract(d_src, d_out, n)` | człon fazowy `(q-1)/q` **i** gałąź `sourceDeclared` (§4) |
| `Θ` | `Div(d_out, param, n)` | bezwarunkowe `++result` |
| `~Θ` | `Mod(param, d_out, n)` | milczące poleganie na zaokrągleniu bazy `ceil(W_src*d_src/d_out)` |

Uwaga do komentarzy, które trzeba **poprawić, a nie tylko uzupełnić**:
dzisiejszy tekst przy `STREAM_DEHASH_DIV` w `compiler.cpp` („Θ zawsze wyprzedza
swój slot o mniej niż jeden okres wyjścia. Jeden slot jest dokładnym własnym
ogonem operatora") jest nieprawdziwy — przy ilorazie całkowitym człon własny
`Θ` wynosi zero w 100% węzłów korpusu (PHASE0.md §3).

## 6. Co faza 1 zostawia fazie 2

- Postać jest **jedna**, więc kontrola zasięgu w fazie 2b sprowadza się do
  sprawdzenia, że sześć pozostałych klas nie zmienia ani jednego węzła.
- Próg `kPhaseScanLimit` (2c) wymaga wariantu zapasowego, który **nie zaniża**.
  Kandydatem jest dzisiejsza reguła każdej z trzech klas: w całym korpusie jej
  odchyłka wobec dokładnej postaci wynosi `0` albo `+1`, nigdy `-1`. Dla `q`
  poza korpusem jest to na razie **założenie**, nie wynik — faza 2c ma je
  sprawdzić celowaną kontrolą, a nie odziedziczyć.
