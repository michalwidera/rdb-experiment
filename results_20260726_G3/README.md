# K2/G3 — niezależny oracle reguły shift-matching

Cel: zamknąć lukę G3 przez niezależną, wykonywalną kontrolę reguły:

```text
phi(tau_i(A), tau_k(B)) = tau_(i+k)(phi(A,B))
gdy i*delta_A = k*delta_B
```

Eksperyment rozszerza zakres badania `results_20260725`, ale nie modyfikuje
jego historycznych plików ani wyników.

## Niezależność definicji

Oracle nie używa wzoru Beatty'ego ani kodu wykonawczego RetractorDB. Definiuje
przeplot przez scalenie dwóch arytmetycznych siatek zdarzeń:

```text
A[k] = (k+1)*delta_A
B[j] =  j   *delta_B
```

Przesunięcie `>N` opóźnia całą siatkę o `N*delta` i zwiększa ogon startowy;
nie usuwa rekordów ani nie wstawia prefiksu. Porównywany ślad zawiera fazę,
czas logiczny, źródło, indeks źródłowy, dwupolowy rekord i jego mapę `NULL`.

## Zakres

- kwalifikowane mutacje uruchamiane przed wynikiem;
- exhaustive `1 <= a,b <= 256`, co najmniej `10P` pozycji;
- co najmniej 10 000 deterministycznie losowanych par do `a,b <= 10^6`;
- przypadki równe, skośne, względnie pierwsze, nieskrócone `6/4` i audio
  `160/147`;
- rekordy bez `NULL`, częściowo null i all-null;
- trzy wykonania silnika: LHS zoptymalizowana, LHS zablokowana i jawna RHS;
- porównanie `delta`, `tail`, `.desc`, payloadu, mapy `NULL` i luk.

Nieskrócony stosunek jest kontrolą benign: `6/4` i `3/2` muszą dać ten sam
ślad. Traktowanie samego braku skrócenia jako błędu byłoby fałszywą mutacją.

## Luki

W aktualnej implementacji strumienie obliczane nie zapisują markerów `gap`.
Dla wyników R1 obowiązuje więc sprawdzalna polityka `G_S = empty`. Mutacja
wstrzykująca marker potwierdza, że komparator tej warstwy nie ignoruje.
Włączenie propagacji luk zmieniłoby obserwowalny artefakt i należy do K19/G16.

## Odtworzenie

```bash
./run.sh
QUICK=1 ./run.sh
XRETRACTOR=/sciezka/do/xretractor ./run.sh
```

Wynik generowany jest do `results/summary.md`; nie należy edytować go ręcznie.

## Wynik 2026-07-26

Oracle przeszedł pełną macierz:

- 65 536 par exhaustive `1 <= a,b <= 256`, zawsze co najmniej `10P`;
- 10 000 deterministycznie losowanych par do `a,b <= 10^6`;
- 12 przypadków obowiązkowych;
- łącznie 75 548 przypadków i 143 065 922 porównane pozycje;
- zero rozbieżności.

Most do silnika dał wynik negatywny: 6/13 przypadków zgodnych. We wszystkich
porażkach plan zoptymalizowany i jawna RHS zgadzają się z oracle'em, natomiast
nieprzepisana LHS emituje okresowe rekordy all-null zamiast kolejnych elementów
drugiego argumentu przeplotu. Wynik powtarza się przy interwałach 2 ms i 20 ms,
więc nie jest skutkiem zbyt szybkiego taktowania.

Przyczynę zawężono do ogona własnego `#`. Bieżące
`ceil(delta_B/delta_A)` nie uwzględnia najgorszej fazy okresu. Maksimum
wymaganego wyprzedzenia B po wszystkich fazach jest o jeden większe dokładnie
w siedmiu przypadkach, które zawiodły. Szczegóły i liczności:
[`results/summary.md`](results/summary.md).

Werdykt: **K2/G3 pozostaje otwarte**. Przed powtórzeniem kampanii trzeba
skorygować wyliczenie ogona przeplotu i dodać regresję dla proporcji innych niż
dotychczasowe `1/2`.
