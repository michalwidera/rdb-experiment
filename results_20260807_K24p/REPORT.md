# K24p — raport

Przebieg wymuszony zmianą silnika z 2026-08-06 (`5f31051`, „Issue 227
precesja”), która **zmieniła wielkość mierzoną przez K24 i K24r**. Punkt
odniesienia: [PIN.md](PIN.md). Predeklaracja: [PREDECLARATION.md](PREDECLARATION.md).
Werdykty: [VERDICT.md](VERDICT.md) (ziarno porównawcze `20260804`),
[VERDICT_oos.md](VERDICT_oos.md) (ziarno potwierdzające `20260807`).

---

## 1. Co zmieniło się w mierzonej wielkości i dlaczego aparatura musiała pójść za tym

Do 2026-08-06 silnik niósł **jedną** wielkość: `query::startupLatency`. Po
`5f31051` niesie **dwie**:

| Wielkość | Znaczenie | Kto ją liczy |
|---|---|---|
| `query::logicalOrigin` | indeks pierwszego rekordu, który **w ogóle istnieje** | `compiler::computeLogicalOrigin()` |
| `query::startupLatency` | ile początkowych slotów istniejącego rekordu **jeszcze nie ma** | `compiler::computeStartupLatency()` |

Rozdzielenie nie jest kosmetyczne. Zmieniły się cztery rzeczy naraz:

1. **Okno `@(k,L)` jest stemplowane końcem przedziału.** Rekord `n` obejmuje
   pozycje `n*k-(|L|-1) ... n*k` zamiast `n*k ... n*k+|L|-1`. Indeks logiczny
   okna oznacza teraz tę samą chwilę co indeks logiczny źródła, więc złączenie
   okna z jego własnym źródłem (potok FIR) nie wyprzedza sygnału.
2. **Postać zamknięta ogona `@` straciła człon fazowy**
   `P = floor((|L|-1)/gcd(F,k))*gcd(F,k)`. Rozpiętość okna przeszła do origin:
   `O = ceil((O_src*F + |L| - 1)/k)`.
3. **`>N` przeniosło opóźnienie z ogona do origin:** `O = O_src + N`,
   `W = W_src` zamiast `W = W_src + N`.
4. **Model pojemności historii dla `@` przestał być postacią zamkniętą** —
   silnik przegląda jeden pełny okres fazowy od origin.

Aparatura K24r mierzyła wielkość, której już nie ma. Oracle (`oracle/model.py`)
został więc przepisany w trzech miejscach — pełna lista w [PIN.md](PIN.md):
okno stemplowane końcem, `>N` jako przesunięcie indeksu (nie opóźnienie czasu),
i **origin jako wielkość pierwszej klasy**, z ogonem liczonym od origin, a nie
od zera. `generator.py` jest bajtowo bez zmian, więc korpusy czterech kampanii
są porównywalne.

### 1.1. Zasada ciągłości — reguła, której przed 2026-08-06 nie było gdzie zapisać

Origin nie jest „pierwszym indeksem o kompletnych zależnościach”. Przeplot
pokazuje różnicę i pokazał ją w tym badaniu jako awarię pierwszej wersji
oracle'a: przy składowych o różnych początkach rekord 0 może mieć komplet (bo
w slocie 0 wypada element składowej o origin zerowym), a rekord 1 już nie (bo
wypada element składowej przesuniętej). Brakujące rekordy **nie tworzą
prefiksu**.

Strumień jest ciągiem rekordów, nie zbiorem z dziurami: zasada brzegu zabrania
wypełnić lukę NULL-em, a przesunięcie kolejnych rekordów zmieniłoby
odwzorowanie indeksu. Początkiem logicznym jest więc **pierwszy indeks, od
którego nie ma już ani jednej luki**. Silnik liczy dokładnie to (maksimum
progów po obu składowych w `computeLogicalOrigin()`); oracle wyprowadza to
niezależnie, ze skanu warunku istnienia. Reguła jest zapisana w
[PREDECLARATION.md](PREDECLARATION.md) §9.

## 2. Wynik — ogon, zestawienie „przed/po” na tym samym korpusie

Ziarno `20260804` jest jednocześnie ziarnem potwierdzającym K24r, więc korpus
jest **ten sam co do planu i co do węzła** (liczności węzłów zgadzają się
klasa po klasie). Kolumna „przed” pochodzi z
[`../results_20260804_K24r/VERDICT_oos.md`](../results_20260804_K24r/VERDICT_oos.md).

| Klasa | Węzłów | Przed (`c4b63a7`) | Po (`db4a360`) | Zmiana |
|---|---:|---:|---:|---|
| `PASS` | 4825 | 100,0% **dokładna** | 100,0% **dokładna** | bez zmian |
| `AGSE` | 4256 | 100,0% **dokładna** | 100,0% **dokładna** | **inna postać, ta sama dokładność** |
| `ADD` | 2487 | 100,0% **dokładna** | 100,0% **dokładna** | bez zmian |
| `REDUCE` | 3292 | 100,0% **dokładna** | 100,0% **dokładna** | bez zmian |
| `SHIFT` | 5314 | 100,0% **dokładna** | 93,4% zawyżająca | **regresja** |
| `HASH` | 5960 | 90,8% zawyżająca | 92,1% zawyżająca | +1,3 p.p. |
| `NTHETA` | 2503 | 98,6% zawyżająca | 99,2% zawyżająca | +0,6 p.p. |
| `THETA` | 2578 | 59,4% zawyżająca | 59,7% zawyżająca | +0,3 p.p. |
| `SUB` | 4329 | 19,2% zawyżająca | 19,1% zawyżająca | −0,1 p.p. |

**Żadna klasa nie zaniża ogona** — ani przed, ani po. To jest wynik, który
podtrzymuje przesłankę zdjętą przez K24r z `harmonogram.md` §4.2: reżim
zaniżający, dotykający relacji `Obs`, nadal nie występuje w korpusie.

Poprawa `#`, `Θ` i `~Θ` o ułamki punktu procentowego ma jedną przyczynę: ogon
liczy się teraz **od origin**, a nie od zera, więc sloty, które nie są
rekordami, przestały stawiać wymagania. To nie jest zmiana wzoru, tylko
zawężenie dziedziny, po której bierze się maksimum.

### 2.1. `@` — postać zamknięta wymieniona, dokładność zachowana

To jest najmocniejszy wynik tego przebiegu. Postać z K24r

```
  W = ceil( (P + (1+W_src)*F) / k ) - 1,   P = floor((|L|-1)/gcd(F,k))*gcd(F,k)
```

została zastąpiona parą

```
  O = ceil( (O_src*F + |L| - 1) / k )
  W = ceil( (1 + W_src) * F / k ) - 1
```

i **obie części zgadzają się z granicą zdarzeniową w 100% węzłów** — 4256/4256
na ziarnie porównawczym i 4242/4242 na ziarnie potwierdzającym. Dokładność `@`
nie była więc własnością konkretnego wzoru, tylko własnością operatora:
H10a-ex dla `@` przechodzi przez zmianę konwencji stemplowania bez uszczerbku.

### 2.2. `>N` — regresja o predeklarowanej postaci

Predeklaracja §3 zapisała **przed kampanią**, że klasa `>N` wypadnie
zawyżająca, a różnica wyniesie dokładnie `min(W_src, N)`. Wyprowadzenie ręczne:
deficyt slotu `n` przesunięcia wynosi

```
  (n - N + 1 + W_src) - (n + 1) = W_src - N     — jest STAŁY,
```

więc dokładną postacią zamkniętą jest `W = max(0, W_src - N)`. Silnik ustawia
`W = W_src`, bo `dataModel::fetchBack` adresuje **offsetem względnym**: w slocie
`n+W` dostaje rekord `(n + W - W_src) - N`, a równość z żądanym `n-N` wymaga
`W = W_src`.

Weryfikacja predykcji na korpusie: **3002 węzły `>N` sprawdzone, 207
z niezerową różnicą, 0 niezgodnych z `min(W_src, N)`**. Rozkład różnicy w całej
klasie (ziarno `20260804`): `+0` 93,4%, `+1` 3,7%, `+2` 1,8%, dalej ogon do `+8`
zgodny z rozkładem `N` w generatorze.

Wniosek do raportowania: **postać zamknięta dla `>N` istnieje i jest dokładna
(`W = max(0, W_src - N)`), ale silnik jej nie implementuje** — implementuje
bezpieczne oszacowanie wymuszone adresowaniem względnym w `fetchBack()`.
Falsyfikacji podlega H10a-**impl**, nie H10a-**ex**. Koszt naprawy: adresowanie
`fetchBack` indeksem logicznym zamiast offsetem względnym, czyli ta sama zmiana
natury co `logicalIndexBase` wprowadzony w `fetchForward` przez `5f31051`.

## 3. Wynik — początek logiczny

| Klasa | Węzłów (`20260804`) | Izolowana | Węzłów (`20260807`) | Izolowana |
|---|---:|---:|---:|---:|
| `HASH` | 5960 | **100,0%** | 5998 | **100,0%** |
| `SHIFT` | 5314 | **100,0%** | 5438 | **100,0%** |
| `PASS` | 4825 | **100,0%** | 4668 | **100,0%** |
| `SUB` | 4329 | **100,0%** | 4320 | **100,0%** |
| `AGSE` | 4256 | **100,0%** | 4242 | **100,0%** |
| `REDUCE` | 3292 | **100,0%** | 3237 | **100,0%** |
| `THETA` | 2578 | **100,0%** | 2612 | **100,0%** |
| `NTHETA` | 2503 | **100,0%** | 2619 | **100,0%** |
| `ADD` | 2487 | **100,0%** | 2448 | **100,0%** |

**Dziewięć klas na dziewięć, obie próby, zero rozbieżności, zero zaniżeń.**
Rozkład różnicy `rachunek silnika − oracle` to w każdej klasie `+0`: 100%.

Zastrzeżenie, które **musi** iść razem z tą tabelą: dla `+`, `#`, `-`, `Θ` i `~Θ`
silnik nie wyznacza origin wzorem, tylko **poszukiwaniem** najmniejszego indeksu
osiągającego próg składowej (`firstIndexReaching`, połowienie po niemalejącym
odwzorowaniu). Wynik jest dokładny, ale nie jest „postacią zamkniętą” w tym
sensie, w jakim artykuł używa tego określenia dla ogona. Postać zamknięta origin
istnieje jawnie dla `@` (`ceil((O_src*F+|L|-1)/k)`), `>N` (`O_src + N`), `PASS`
i redukcji (`O_src`).

## 4. Suma slotów milczenia — jedyna wielkość porównywalna z kampaniami sprzed zmiany

Kolumna „suma” w werdyktach porównuje `origin + ogon`, bo tylko ta wielkość
istniała po obu stronach zmiany. Zgodność sumy jest **niższa** niż zgodność
origin, dokładnie w tych klasach, w których ogon zawyża — co potwierdza, że
przestemplowanie przeniosło milczenie między członami, a nie zmieniło jego
sumy tam, gdzie rachunek był i jest dokładny.

## 5. Człon (b) — kontrola po przestemplowaniu

Aparatura K24b (`run_member_b.py`), populacja twierdzenia i progi **bez zmian**,
ziarno `20260805` (to samo, na którym K24b dała werdykt), oracle nowy:

| Kryterium | Wynik | Próg |
|---|---|---|
| gęstość rozjazdu reguły lokalnej A | 5293/10010 planów = **52,9%** | >= 5% |
| postać rozjazdu `ceil((p+q-1)/p)` | **2310/2310** | 100% |
| dodatniość deficytu | **2310/2310** | 100% |
| kontrola: plany bez `#` | 0/8568 | zero |
| kontrola: `HC_SINGLE` bez własnego ogona | 0/1113 | zero |

**H10b: WSPARTA.** Człon nielokalności przechodzi przez przestemplowanie bez
zmiany, co było do przewidzenia i zostało potwierdzone: populacja twierdzenia
to węzły `#` o **obu składowych deklarowanych**, a deklaracje mają origin
i ogon zerowe, więc przeniesienie milczenia między członami ich nie dotyka.

Jedna zmiana w regule lokalnej A była konieczna i jest odnotowana w kodzie:
zniknął wyjątek `ogon składowej + N` dla `>N`. Po przestemplowaniu `N` nie jest
ogonem, więc reguła z tym członem przypisywałaby przesunięciu ogon nieobecny
zarówno w silniku, jak i w modelu zdarzeniowym — i **zawyżałaby próg gęstości
na korzyść H10b**. Populacja twierdzenia jest na tę zmianę niewrażliwa.

Skutek uboczny tej samej poprawki: kontrola negatywna `HC_SINGLE`, która
w K24 była złamana **w postaci dosłownej** (i wymusiła zawężenie populacji
w K24b), przechodzi teraz dosłownie — 0/3929 rozjazdów na ziarnie porównawczym.
Kontrola `HC_INT` pozostaje złamana dosłownie, z tego samego powodu co w K24
(diagnoza: `../results_20260803_K24/REPORT.md` §5).

## 6. Model pojemności historii — przewidywanie bez potwierdzenia

`capacity.py` przewiduje dla klasy `@` niedomiar **dokładnie jednego rekordu**
w 1809/2620 par (69,0%) na ziarnie porównawczym i 1816/2648 (68,6%) na
potwierdzającym. Wszystkie pozostałe klasy: zero niedomiaru.

Źródło rozbieżności jest jedno i daje się wskazać palcem. Model żądania
w `capacity.py` zakłada, że czoło deklaracji wyprzedza rachunek czasowy
o `DECLARATION_PREFETCH = 2` rekordy w chwili odczytu, i dokłada ten człon do
**żądania**. Silnik dokłada `kDeclarationPrefetch = 2` do **pojemności**, licząc
dystans od rekordu najnowszego — co w sumie daje o jeden mniej. Człon `+2`
w modelu żądania jest heurystyką wykrytą empirycznie w K24/P1 i już wtedy
odnotowaną jako **niejednolity** (potwierdzony tylko dla `-`, `@` i `+`).

Rozstrzygnięcie może przyjść wyłącznie z wykonania — niedomiar pojemności
historii objawia się rekordem all-NULL albo przerwaniem w `storage::revRead`,
nigdy cicho.

**Kontrola celowana** (`check_agse_capacity.py`, ziarno `20260804`): wybrano
**wyłącznie** plany, dla których model przewiduje niedomiar dla `@` nad składową
deklarowaną, i puszczono je end-to-end.

| Wynik | Planów |
|---|---:|
| zgodne (rekordy takie, jakie przewiduje model treści) | **55** |
| poza budżetem czasu aparatury | 5 |
| rekord all-NULL, awaria `revRead`, inna treść | **0** |

**Objawów niedomiaru: brak.** Wniosek: przewidywanie pochodzi z członu `+2`
w modelu żądania `capacity.py`, a nie z silnika. Raportowane jako
**przewidywanie bez potwierdzenia**, tą samą kategorią, którą K24r zastosowała
do `#`, `Θ` i `~Θ`. Rozstrzygnięcie, czy czoło deklaracji wyprzedza rachunek
czasowy o jeden rekord czy o dwa, pozostaje otwarte i jest tanie (§9) — ale
**nie jest** blokadą dla kroku 3a, bo żaden wariant nie zmienia werdyktu H10a.

## 7. Bramka odwzorowania — end-to-end

Podpróba stratyfikowana, po 8 planów na stratę (14 strat = 112 planów), każdy
uruchomiony w **dwóch skalach** czasu; różnica między skalami dyskwalifikuje
przebieg jako aparaturę, nie liczy się jako znalezisko. Treść porównywana
z modelem treści oracle'a, z pozycją w artefakcie przeliczaną na indeks
logiczny przez origin.

| Ziarno | Planów | Zgodne | Poza budżetem | Rozbieżność treści | Awarie |
|---|---:|---:|---:|---:|---:|
| `20260807` (potwierdzające) | 112 | **103** | 9 | **0** | **0** |
| `20260804` (porównawcze) | 112 | 101 | 10 | 1 | **0** |

### 7.1. Jedyne zgłoszenie i jego rozstrzygnięcie

Ziarno `20260804`, plan 38 (`HC_SHIFT_UNDER_HASH`), węzeł `n3` klasy `-`:
**„zero rekordów”**. Reproducer `repro_plan38.py` uruchamia ten jeden plan
w trzech długościach przebiegu:

| Pętli | `n0` (`#`) | `n1` (`>N`) | `n2` (`#`) | `n3` (`-`) |
|---:|---:|---:|---:|---|
| 129 (budżet bramki) | 22 | 1 | 3 | **0 — zgłoszenie** |
| 258 | 46 | 10 | 51 | 16, **zgodne** |
| 516 | 95 | 28 | 147 | 48, **zgodne** |

To jest **artefakt długości przebiegu, nie defekt silnika**. Budżet bramki
(`loops`) liczy się z rozpiętości interwałów i **nie uwzględnia origin**,
który po przestemplowaniu bywa duży — tu `n2` ma origin 43, a `n3` czyta `n2`
pod indeksem `3n`, więc pierwszy rekord `n3` wymaga rekordu 45 strumienia `n2`.
Po podwojeniu przebiegu węzeł emituje rekordy i **wszystkie zgadzają się
z modelem treści**.

Poprawka aparatury (dodanie `origin` do budżetu `loops`) jest oczywista, ale
**nie została wprowadzona po zobaczeniu wyniku** — zmiana aparatury po
zamrożeniu unieważniłaby przebieg (PREDECLARATION.md §8). Jest zapisana jako
praca otwarta (§9).

**Kryterium end-to-end z predeklaracji §6 uznaję za spełnione:** zero
rozbieżności treści i zero awarii na obu ziarnach, po rozstrzygnięciu jedynego
zgłoszenia jako artefaktu aparatury o udokumentowanym reproducerze.

## 8. Co z tego wchodzi do artykułu (krok 3a)

Brzmienie członu (a) do przeniesienia, w wersji obowiązującej po tym przebiegu:

> Dla operatorów `PASS`, `@`, `+` i redukcji granica określoności planu ma
> postać zamkniętą **równą** granicy zdarzeniowej. Dla `>N` postać zamknięta
> istnieje i jest dokładna (`W = max(0, W_src − N)`), ale realizacja używa
> oszacowania z góry wymuszonego adresowaniem względnym. Dla `#`, `-`, `Θ`
> i `~Θ` znane postacie są bezpiecznymi oszacowaniami z góry z błędem
> dokładnie jednego slotu. Początek logiczny jest wyznaczany dokładnie we
> wszystkich dziewięciu klasach, przy czym dla pięciu z nich — poszukiwaniem
> po niemalejącym odwzorowaniu, nie wzorem.

Trzy zdania, które **nie wolno** żeby padły w artykule:

1. „postać zamknięta jest dokładna dla wszystkich operatorów” — nie jest,
   i to jest zmierzone;
2. „granica planu ma postać zamkniętą jako punkt stały nad `qTree`” bez
   zastrzeżenia — origin dla pięciu klas liczy się poszukiwaniem, a pojemność
   `@` enumeracją okresu fazowego; różnica (ii) wobec prior work
   (`related_work_k8.md` §4.6) wymaga zawężenia do ogona;
3. „K24p jest testem prospektywnym” — nie jest; jest potwierdzeniem po zmianie
   semantyki, na modelu zdarzeniowym wyprowadzonym niezależnie od silnika,
   z jedną predeklarowaną predykcją negatywną (§2.2).

Człon (b) wchodzi bez zmian — jest wsparty i po przestemplowaniu (§5).

## 9. Praca otwarta o znanym koszcie

| Pozycja | Koszt | Status |
|---|---|---|
| `>N` — adresowanie `fetchBack` indeksem logicznym, żeby `W = max(0, W_src−N)` dało się wdrożyć | jak `logicalIndexBase` w `fetchForward` | otwarte, przenosi `>N` z powrotem do klasy dokładnej |
| `#`, `-`, `Θ`, `~Θ` — własne wyprowadzenia postaci dokładnych | jak naprawa `+` i `@` | otwarte od K24 |
| rozstrzygnięcie członu `DECLARATION_PREFETCH` w modelu żądania pojemności | dzień | §6, przewidywanie bez potwierdzenia; nie blokuje kroku 3a |
| origin dla `+`, `#`, `-`, `Θ`, `~Θ` — postać zamknięta zamiast poszukiwania | nieznany | otwarte, wpływa na brzmienie różnicy (ii) |
| budżet `loops` bramki odwzorowania nie uwzględnia origin | godzina | §7.1; poprawka dopiero w następnej predeklaracji |
