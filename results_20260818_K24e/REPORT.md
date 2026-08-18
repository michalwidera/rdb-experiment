# K24e — raport

Kampania na silniku **`e2a61ff`** (gałąź `issue_232-k24h10`), po wyprowadzeniu
i wdrożeniu postaci dokładnych dla `-`, `Θ` i `~Θ`. Punkt odniesienia:
[PIN.md](PIN.md). Predeklaracje: [PREDECLARATION.md](PREDECLARATION.md)
(iteracja 1) i [PREDECLARATION-2.md](PREDECLARATION-2.md) (obowiązująca).
Zatrzymanie iteracji 1: [STOP.md](STOP.md). Werdykty:
[VERDICT.md](VERDICT.md) (ziarno `20260818`), [VERDICT_oos.md](VERDICT_oos.md)
(ziarno `20260820`).

## 1. Wynik w jednym zdaniu

**Dziewięć klas operatorów na dziewięć ma ogon dokładny, zero klas zawyżających,
zero zaniżających, początek logiczny dokładny w 9/9 — na obu ziarnach, zarówno
w atrybucji izolowanej, jak i propagowanej.**

## 2. Ogon — per klasa

| Klasa | Węzłów `20260818` | Izolowana C1 | Propagowana C1 | Węzłów `20260820` | Izolowana C1 | Propagowana C1 | Reżim |
|---|---:|---:|---:|---:|---:|---:|---|
| `HASH` | 5953 | 100.0% | 100.0% | 5958 | 100.0% | 100.0% | dokładna |
| `SHIFT` | 5440 | 100.0% | 100.0% | 5395 | 100.0% | 100.0% | dokładna |
| `PASS` | 4735 | 100.0% | 100.0% | 4688 | 100.0% | 100.0% | dokładna |
| `SUB` | 4433 | 100.0% | 100.0% | 4376 | 100.0% | 100.0% | dokładna |
| `AGSE` | 4361 | 100.0% | 100.0% | 4417 | 100.0% | 100.0% | dokładna |
| `REDUCE` | 3297 | 100.0% | 100.0% | 3309 | 100.0% | 100.0% | dokładna |
| `THETA` | 2567 | 100.0% | 100.0% | 2574 | 100.0% | 100.0% | dokładna |
| `NTHETA` | 2559 | 100.0% | 100.0% | 2521 | 100.0% | 100.0% | dokładna |
| `ADD` | 2490 | 100.0% | 100.0% | 2465 | 100.0% | 100.0% | dokładna |

Korpus: 10 010 planów na ziarno, 35 835 i 35 703 obserwacji węzłowych, zero
błędów aparatury na obu.

Rozkład różnicy (postać zamknięta − oracle C1) to `+0` w 100% węzłów każdej
klasy. Początek logiczny: 100% w kolumnie izolowanej, propagowanej i w sumie
`origin + ogon`.

## 3. Co się zmieniło wobec K24d

| Klasa | K24d izolowana | K24d propagowana | **K24e izolowana** | **K24e propagowana** |
|---|---:|---:|---:|---:|
| `SUB` (`-`) | 19,1% | 6,6% | **100%** | **100%** |
| `THETA` (`Θ`) | 59,7% | 52,9% | **100%** | **100%** |
| `NTHETA` (`~Θ`) | 99,2% | 98,1% | **100%** | **100%** |
| `HASH` | 100% | 92,7% | 100% | **100%** |
| `SHIFT` | 100% | 99,5% | 100% | **100%** |
| `PASS` | 100% | 97,1% | 100% | **100%** |
| `AGSE` | 100% | 97,6% | 100% | **100%** |
| `REDUCE` | 100% | 98,7% | 100% | **100%** |
| `ADD` | 100% | 97,6% | 100% | **100%** |

Kolumna propagowana sześciu klas **nietkniętych przez naprawę** też doszła do
100% — bo wcześniej dziedziczyła błąd po naprawionych dzieciach. To jest
najmocniejszy pojedynczy wynik tej kampanii i był **predeklarowany jako P2**.

## 4. Przewidywania — rozliczenie

| # | Treść | Wynik |
|---|---|---|
| P1 | 9/9 klas dokładnych, izolowana, oba ziarna | **potwierdzone** |
| P2 | kolumna propagowana 100% w 9/9 | **potwierdzone** |
| P3 | zero klas zaniżających (ogon i origin) | **potwierdzone** |
| P4 | origin dokładny 9/9, bez zmian wobec K24d | **potwierdzone** |
| P5 | człon (b) wsparty, `ceil((p+q-1)/p)` w 100% populacji | **potwierdzone** — 2310/2310, gęstość 52,9%, kontrole negatywne 0/8568 i 0/1113 |
| P6' | zero niedomiaru pojemności w klasach naprawionych; `AGSE` bez zmian | **potwierdzone** — `-`, `Θ`, `~Θ`, `>N`, `#`, `+`: zero; `AGSE` 69,0% i 70,5% wobec 69,0% i 68,6% w K24d |
| P7 | powtarzalność ziarna w próbie | **potwierdzone** |
| P8 | bezczynność naprawy aparatury | **potwierdzone** — plik surowy `20260818` bajtowo identyczny z iteracją 1 (SHA-256 `7ebffdd6...`) |
| — | kryterium end-to-end: bramka odwzorowania, zero awarii | **spełnione** — 109 i 101 planów zgodnych, zero awarii, plany poza budżetem raportowane osobno (3 i 11) |

## 5. Dwie rzeczy, które poszły nie tak, i co z nimi zrobiono

### 5.1. Zatrzymanie iteracji 1 — sufit aparatury

Ziarno potwierdzające iteracji 1 (`20260819`) zatrzymało kampanię na błędzie
aparatury: `ORIGIN_LIMIT` w oracle'u był stałą bezwzględną, niepowiązaną
z oknem sondowania `4*(p+q)`. Pełna diagnoza w [STOP.md](STOP.md); w skrócie —
**K24d przeszła z zapasem 1,8%**, czego nikt nie wiedział, bo stała nie miała
z oknem żadnego związku.

Naprawa (limit jako margines **nad** oknem) unieważniła iterację 1 zgodnie z §8
predeklaracji. Ziarna `20260818` i `20260819` zostały spalone jako
potwierdzające, bo ich wyniki obejrzano; iteracja 2 wzięła nowe `20260820`,
a `20260818` przeszło do roli kontroli bezczynności (P8).

**Odróżnienie, na którym to stoi:** awaria aparatury to przebieg, w którym
pomiar w ogóle nie doszedł do skutku, i taki wolno powtórzyć. Wynik negatywny —
pomiar wykonany, tylko niewygodny — jest nieodwracalny. Gdyby `20260819`
pokazało klasę zawyżającą, byłby to werdykt.

### 5.2. Defekt mojej predeklaracji — P6

Brzmienie P6 w iteracji 1 („zerowy niedomiar we **wszystkich** klasach”)
przepisałem z predeklaracji K24p bez zawężenia. Jest za mocne: `capacity.py`
od czasów K24p pokazuje dla `AGSE` niedomiar rzędu 69%, przypisany członowi
`DECLARATION_PREFETCH` liczonemu po innej stronie w modelu niż w silniku
i sprawdzony w K24p kontrolą celowaną (zero objawów).

**W iteracji 1 P6 jest literalnie sfalsyfikowane i tak zostaje zapisane.**
Iteracja 2 obowiązuje w brzmieniu P6' zawężonym do klas, których dotyczy
naprawa. Jest to defekt predeklaracji, nie wynik pomiaru — i nie wolno go
raportować jako „doprecyzowania”.

## 6. Zdarzenie środowiskowe, warte odnotowania osobno

Pierwszy przebieg bramki odwzorowania oblał 110 planów na 112 z komunikatem
`Another instance is running`. Przyczyną był **proces `xretractor` zostawiony
przez test `it_issue113_null_skip`** z zakończonego przebiegu `ctest` w Release
— żył 28 minut i trzymał blokadę instancji. Po jego ubiciu bramka przeszła
czysto na obu ziarnach.

Zdarzenie **nie dotyczy silnika w sensie semantyki** i nie wpływa na żadną
liczbę tego raportu (wszystkie bramki powtórzono w czystym środowisku), ale
ujawnia realny defekt higieny testów: test kończy się zielono, zostawiając żywy
proces, a ofiarą pada dowolny późniejszy odbiorca blokady. Ma własny plan:
`paper-arXiv/debs/plan-ad-hoc-flak.md`.

## 7. Status epistemiczny — do raportowania dosłownie

K24e **nie jest testem prospektywnym**. Postacie zamknięte wyprowadzono
i sprawdzono offline na korpusach ziaren `20260804` i `20260807` **przed**
dotknięciem silnika (`../investigation_K24H10/PHASE2.md`), a kampania potwierdza
je na poziomie silnika, na **ziarnach nieużytych w wyprowadzeniu**.
Predeklarowane były ziarna, kryteria i osiem przewidywań — nie hipoteza.

Wartością tej kampanii jest **przypięcie**: gdyby wypadła inaczej niż
przewidywanie, znaczyłoby to, że silnik nie implementuje postaci, którą
sprawdzono offline — i to byłby wynik.

Model zdarzeniowy, generator i procedura werdyktu są wobec K24d **bajtowo bez
zmian** poza jedną poprawką warunku przerwania (§5.1), której bezczynność
zmierzono (P8).

## 8. Co z tego idzie do artykułu

**Tabela per klasa ma iść z tego katalogu, nie z K24d.** Twierdzenie w tekście
zmienia się z „sześć klas dokładnych, trzy zawyżające o slot” na **„dziewięć klas
dokładnych, zero zawyżających, zero zaniżających”**, a zapis o reżimie
bezpiecznym jako kompromisie znika — nie ma już czego usprawiedliwiać.

Pakiet artefaktów ma wieźć silnik **`e2a61ff`** albo jego potomka, w którym
rachunek ogona i origin jest nietknięty. Reguła z `research_plan.md` §16
obowiązuje dalej: zmiana `computeStartupLatency()`, `computeLogicalOrigin()`,
`SOperations.hpp` albo odwzorowań w `dataModel.cpp` unieważnia te liczby.
