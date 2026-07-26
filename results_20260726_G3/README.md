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

## Wynik 2026-07-26 — po poprawce

Oracle przeszedł pełną macierz:

- 65 536 par exhaustive `1 <= a,b <= 256`, zawsze co najmniej `10P`;
- 10 000 deterministycznie losowanych par do `a,b <= 10^6`;
- 12 przypadków obowiązkowych;
- łącznie 75 548 przypadków i 143 065 922 porównane pozycje;
- zero rozbieżności.

Pierwsze wykonanie mostu dało 6/13 przypadków zgodnych i ujawniło, że dawne
`ceil(delta_B/delta_A)` zabezpiecza tylko pierwszą próbkę B, a nie najgorszą
fazę okresu. Silnik używa teraz maksimum fazowego; dla zredukowanego
`delta_A/delta_B=p/q` jego zamknięta postać wynosi
`ceil((p+q-1)/p)`. Oracle nadal liczy maksimum bezpośrednio po całym okresie,
nie korzysta więc z implementacyjnej postaci zamkniętej.

Po poprawce most przeszedł **13/13** przypadków. Plan zoptymalizowany,
nieprzepisana LHS i jawna RHS mają w każdym przypadku ten sam interwał, ogon,
schemat, payload, mapę `NULL` i pusty ślad luk; liczba błędów względem oracle'a
wynosi zero. Wynik powtarza się przy interwałach 2 ms i 20 ms.

Szczegóły, provenance brudnych worktree i liczności:
[`results/summary.md`](results/summary.md).

Werdykt: **K2/G3 spełnia kryterium eksperymentalne**.
