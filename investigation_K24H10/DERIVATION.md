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

## 5. Postać zamknięta `O(1)` — przegląd był narzędziem dowodu

Sekcja dopisana po fazie 2c. Wyprowadzenie wariantu zapasowego pokazało, że
przegląd okresu **nie jest potrzebny w silniku**: te same wartości daje postać
`O(1)`.

**Twierdzenie.** Niech `r = d_out/d_src` i niech odwzorowanie indeksu rozkłada
się jako `idx(n) = n·r + e(n)`, gdzie `sup_n e(n) = c` jest **osiągane**. Wtedy

```
W = max(0, ceil( (c + 1 + W_src) / r ) - 1).
```

*Dowód.* Podstawiając rozkład do warunku dostępności:

```
f(n) = ceil( (n·r + e(n) + 1 + W_src)/r ) - 1 - n = ceil( (e(n)+1+W_src)/r ) - 1,
```

bo `n·r/r = n` jest całkowite i wychodzi przed sufit, kasując `-n`. Prawa strona
zależy od `n` wyłącznie przez `e(n)` i rośnie z nim niemalejąco, więc maksimum
po `n` osiąga się tam, gdzie `e(n)` osiąga kres. ∎

**Stałe `c` i osiągalność kresu** (`d_out/d_src = p/q`, `gcd(p,q)=1`):

| Klasa | `e(n)` | `c` | Kres osiągany, bo |
|---|---|---|---|
| `-` | `ceil(np/q) - np/q = (q - s)/q`, `s = np mod q` | `(q-1)/q` | `gcd(p,q)=1`, więc `s=1` dla pewnego `n` |
| `Θ` | `(a - t)/b` przy `t=0`, inaczej `(a + b - t)/b`, `t = (n+1)a mod b` | `(a+b-1)/b` | `gcd(a,b)=1`, więc `t=1` dla pewnego `n` (dla `b=1` kres to `a`, ta sama wartość) |
| `~Θ` | `-(na mod b)/b <= 0` | `0` | `n = 0` |

Osiągalność jest istotą rzeczy: bez niej postać byłaby tylko oszacowaniem
z góry. To zarazem wyjaśnia, dlaczego dzisiejsza reguła `-` zawyża — jej człon
fazowy `(q-1)/q` jest poprawny, ale wchodzi do rachunku w złym miejscu
(jako dodatek do `W_src` zamiast do indeksu), a reguła `Θ` dokłada stały slot
tam, gdzie kres wynosi `a/b` i po podzieleniu przez `r` daje zero.

**Weryfikacja** ([`phase2_closed.py`](phase2_closed.py), [`phase2_bound.py`](phase2_bound.py)):

| Kontrola | `-` | `Θ` | `~Θ` |
|---|---|---|---|
| postać `O(1)` `==` oracle, korpus, ziarno `20260804` | 4329/4329 | 2578/2578 | 2503/2503 |
| to samo, ziarno `20260807` | 4320/4320 | 2612/2612 | 2619/2619 |
| postać `O(1)` `==` przegląd okresu (oba ziarna) | 100% | 100% | 100% |
| przemiatanie poza korpusem (`q` do 60, `W_src` do 8): zaniżeń | 0 / 19818 | 0 / 13218 | 0 / 13218 |
| to samo: przypadków, gdzie `O(1)` `==` przegląd | 100% | 100% | 100% |

**Korekta wobec `PHASE0.md` §3.** Tam zapisano „postaci `O(1)` nie ma".
Zdanie jest prawdziwe w tym, co mierzyło — **człon własny** operatora nie jest
funkcją samego `(p, q)` — ale mylące jako wniosek ogólny: pełny ogon **jest**
funkcją `O(1)` argumentów `(c, r, W_src)`. Pomyłka brała się stąd, że człon
własny rozbija rachunek na „generyczne przeliczenie plus dodatek", a poprawny
rozkład idzie po `idx(n) = n·r + e(n)`, nie po tej granicy.

**Skutek dla planu: znika próg przeglądu.** Nie ma `kPhaseScanLimit`, nie ma
wariantu zapasowego i nie ma zadania 2c w pierwotnym brzmieniu — kontrola progu
zamieniła się w kontrolę dokładności postaci, i tę postać zamyka dowód, a nie
przemiatanie. Klasa `#` zostaje jedyną, która przegląda okres (`O(p+q)`).

## 6. Zadanie 1c — materiał do `SOperations.hpp` (do wklejenia w fazie 3)

Odwzorowania indeksu (`Subtract`, `Div`, `Mod`) zostają tam, gdzie są — używa
ich `computeLogicalOrigin()`. Rachunek ogona ich **nie wywołuje**: wchodzi do
niego wyłącznie stała `c` wyprowadzona z tego samego odwzorowania.

```cpp
// Ogon C-Delta. Rekord n czyta rekord ceil(n*d_out/d_src) źródła, czyli
// idx(n) = n*r + e(n) przy r = d_out/d_src = p/q, gdzie e(n) = (q - n*p mod q)/q.
// Warunek dostępności upraszcza się wtedy do W >= ceil((e(n)+1+W_src)/r) - 1,
// a kres e(n) = (q-1)/q jest osiągany, bo gcd(p,q) = 1 (dowód: DERIVATION.md §5).
constexpr int SubtractStartupLatency(const rational<int> &deltaSource, const rational<int> &deltaTarget,
                                     const int sourceLatency) {
  const auto ratio = deltaTarget / deltaSource;
  const rational<int> phase(ratio.denominator() - 1, ratio.denominator());
  return std::max(0, ceilR((phase + 1 + sourceLatency) / ratio) - 1);
}
```

| Klasa | `c` | Co znika z dzisiejszego rachunku |
|---|---|---|
| `-` | `(q-1)/q` | gałąź `sourceDeclared` (§4) oraz błędne miejsce członu fazowego |
| `Θ` | `(a+b-1)/b`, `a/b = d_out/param` | bezwarunkowe `++result` |
| `~Θ` | `0` | milczące poleganie na zaokrągleniu bazy `ceil(W_src*d_src/d_out)` |

Uwaga do komentarzy, które trzeba **poprawić, a nie tylko uzupełnić**:
dzisiejszy tekst przy `STREAM_DEHASH_DIV` w `compiler.cpp` („Θ zawsze wyprzedza
swój slot o mniej niż jeden okres wyjścia. Jeden slot jest dokładnym własnym
ogonem operatora") jest nieprawdziwy — przy ilorazie całkowitym człon własny
`Θ` wynosi zero w 100% węzłów korpusu.

## 7. Co faza 1 i 2 zostawiają fazie 3

- Trzy postacie `O(1)`, każda w jednej linii, bez przeglądu i bez progu.
- Rachunek ogona przestaje zależeć od `isDeclaration()` — jedna zmienna mniej
  w sygnaturze.
- Przypadki ręczne do testu są policzone i sprawdzone wobec oracle'a
  ([`PHASE2.md`](PHASE2.md) §4).
