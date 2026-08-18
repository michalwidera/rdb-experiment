# K24e — zatrzymanie na błędzie aparatury i przefreezowanie

**Data:** 2026-08-18. Dotyczy: [`PREDECLARATION.md`](PREDECLARATION.md)
(iteracja 1), przebieg na ziarnie potwierdzającym `20260819`.

## 1. Co się stało

Kampania na ziarnie głównym `20260818` przeszła czysto: 10 010 planów, 35 835
obserwacji węzłowych, **zero błędów aparatury**.

Kampania na ziarnie potwierdzającym `20260819` **zatrzymała się**:

```
planów: 10010, wierszy: 35919, błędów aparatury: 1
APARATURA plan 8878: oracle — oracle: nie znaleziono początku logicznego
dla n2 poniżej 100000
KAMPANIA ZATRZYMANA
```

Zgodnie z §8 predeklaracji błąd aparatury zatrzymuje iterację. Ten dokument
zamyka iterację 1 i uzasadnia iterację 2.

## 2. Diagnoza — sufit aparatury, nie zjawisko

Plan 8878 zawiera węzeł `n2 = n1#s0` o składowych `2/203` i `147/1000`, czyli
ilorazie `2000/29841` i okresie fazowym `p+q = 31841`. Oracle sonduje początek
logiczny oknem `4*(p+q) = 127 364`, a `ORIGIN_LIMIT` w `oracle/model.py` wynosił
`100 000` — **wartość bezwzględna, nie powiązana z oknem**. Strażnik strzelił
więc w przebiegu całkowicie legalnym.

Skala zapasu w kampaniach dotychczasowych:

| Ziarno | max `p+q` | okno `4(p+q)` | limit | zapas |
|---|---:|---:|---:|---:|
| `20260804` (K24d) | 16 027 | 64 108 | 100 000 | 36% |
| `20260807` (K24d, poza próbą) | 24 557 | **98 228** | 100 000 | **1,8%** |
| `20260818` (K24e, główne) | 19 087 | 76 348 | 100 000 | 24% |
| **`20260819`** (K24e, potwierdzające) | **31 841** | **127 364** | 100 000 | **przekroczony** |

**Kampania K24d przeszła z zapasem 1772 kroków na 100 000.** Nie było to
świadome — stała nie miała żadnego związku z szerokością okna. Każde nowe ziarno
mogło ten sufit przebić i to jest właściwe znalezisko tego zatrzymania.

Rzeczy, którymi to zatrzymanie **nie jest**:

* nie jest skutkiem naprawy z fazy 3 — dotyczy klasy `#`, której rachunek jest
  nietknięty, i mechanizmu **origin**, nie ogona;
* nie jest planem odrzuconym przez kompilator — silnik ten plan kompiluje;
* nie jest rozbieżnością silnik-oracle — do porównania w ogóle nie doszło.

## 3. Naprawa aparatury

`oracle/model.py`: limit jest teraz **marginesem nad oknem**, nie zamiast niego.

```python
limit = ORIGIN_LIMIT + window
```

Strażnik zachowuje swoją rolę (odwzorowanie, które wbrew założeniu nie rośnie,
nadal zatrzymuje przebieg i nie kończy się cicho), ale nie może już strzelić
w planie, którego okno jest po prostu szerokie.

Bramki aparatury po zmianie: `test_oracle.py` PRZESZŁA (45 przypadków, 228
porównań), `test_mutants.py` PRZESZŁA (100%), `test_independence.py` PRZESZŁA.

## 4. Konsekwencja dla predeklaracji

§8 predeklaracji wymienia zmianę `oracle/model.py` jako unieważniającą przebieg.
Zmiana jest konieczna, więc **iteracja 1 jest zamknięta bez werdyktu**,
a kampania idzie ponownie pod [`PREDECLARATION-2.md`](PREDECLARATION-2.md).

Dwie rzeczy, które trzeba przy tym powiedzieć wprost:

1. **Ziarno `20260819` jest spalone jako potwierdzające.** Uruchomiłem na jego
   obciętym pliku `verdict.py` i zobaczyłem część wyniku (brak klas
   zawyżających i zaniżających). Nie wolno go teraz raportować jako
   potwierdzenia poza próbą — iteracja 2 bierze ziarno **nowe i nieoglądane**.
2. **Ziarno `20260818` staje się ziarnem w próbie.** Jego wynik widziałem
   w całości. W iteracji 2 jest powtarzane, ale nie jako potwierdzenie, tylko
   jako **kontrola bezczynności naprawy**: żaden jego plan nie zbliżał się do
   sufitu (okno 76 348), więc plik surowy musi wyjść **bajtowo identyczny**.
   Jeśli się zmieni, naprawa aparatury nie jest bezczynna i to jest wynik.
