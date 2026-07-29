# Wada znaleziona przy przygotowaniu K5: `resolveStreamIntervals` zależy od kolejności planu

**Status:** znaleziona 2026-07-29 przy budowie rodziny W4, **nienaprawiona**.
Poza zakresem K5 — dotyczy kodu, którego ta kampania nie bada, a
`REQUIREMENTS.md` R2 zakazuje zmian w repozytorium kodu w trakcie eksperymentu.

**Rewizja:** `0e0f70161fd46ffd918dbdb457e6dbdcd4439b03` (`master`).

## Objaw

Plan bezcykliczny bywa odrzucany komunikatem `Circular dependency in stream
definitions` (rc 71) albo kompilowany z zerowym interwałem, co ujawnia się jako
`bad rational: zero denominator` (rc 4). To, który wariant wystąpi i czy
wystąpi, zależy od liczby zapytań w planie w sposób **niemonotoniczny**.

Pierwotna konstrukcja W4, `Q` niezależnych łańcuchów
`(A>2)#(B>1) -> projekcja -> okno@(1,30) -> .avg`:

| `Q` | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 12 | 16 | 20 | 32 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| wynik | OK | OK | OK | **71** | **71** | **71** | OK | **71** | OK | OK | **71** | OK | OK | OK |

Wariant bez okna i bez agregatu — sam łańcuch arytmetyczny nad przeplotem —
zawodzi inaczej i przy innych `Q` (rc 4 dla `Q` = 8 i 32), co pokazuje, że
przyczyna nie leży w AGSE.

## Przyczyna źródłowa

`compiler::resolveStreamIntervals` (`src/retractor/lib/compiler.cpp:39-192`)
rozwiązuje interwały iteracyjnie. Każdy przebieg sortuje plan
(`coreInstance.sort()`, po `rInterval`), po czym próbuje policzyć interwał
każdego zapytania z interwałów jego źródeł; nierozwiązane źródło daje
`getDelta() == 0`.

Gałęzie dwuargumentowe robią to poprawnie — sprawdzają zero, ustawiają
`bOnceAgain` i zwiększają `unresolvedCount`, czyli proszą o kolejny przebieg.
**Dwie ścieżki tego nie robią:**

1. **Program jednoelementowy** (`compiler.cpp:49-52`) — `SELECT expr STREAM x
   FROM y`, najczęstsza konstrukcja w RQL:

   ```cpp
   if (q.lProgram.size() == 1) {
     token tInstance(*(q.lProgram.begin()));
     q.rInterval = coreInstance.getDelta(tInstance.getStr_());
     continue;  // Just one stream
   }
   ```

   Brak kontroli zera. Jeżeli w tym przebiegu `y` jest jeszcze nierozwiązane,
   `x` dostaje interwał 0 **i nikt nie prosi o kolejny przebieg**.

2. **`STREAM_AGSE`** (`compiler.cpp:160-176`) — `delta = (coreDelta * step) /
   coreWindow` bez sprawdzenia `coreDelta == 0`, z tym samym skutkiem.

Stąd dwa tryby awarii:

- jeżeli żadne inne zapytanie nie zażądało kolejnego przebiegu, pętla kończy
  się z `rInterval == 0` → późniejszy `bad rational: zero denominator`;
- jeżeli inne zapytania żądają przebiegów, ale liczba nierozwiązanych przestaje
  **ściśle** maleć, zadziała warunek `unresolvedCount >= prevUnresolved`
  (`compiler.cpp:187-190`) i zgłosi cykl, którego w planie nie ma. Warunek jest
  heurystyką postępu, nie detektorem cykli.

Zależność od `Q` bierze się z `coreInstance.sort()`: kolejność, w jakiej
zapytania trafiają pod ocenę, zmienia się z liczbą i interwałami zapytań, więc
o trafieniu w wadę decyduje układ planu, a nie jego poprawność.

## Repro

```bash
cat > q.rql <<'EOF'
STORAGE 'temp'
SUBSTRAT 'memory'
DECLARE value INTEGER STREAM A, 1/10 FILE 'a.txt'
DECLARE value INTEGER STREAM B, 1/5 FILE 'b.txt'
EOF
for j in 0 1 2 3; do
  printf 'SELECT * STREAM o_%s FROM (A>2)#(B>1)\n' $j >> q.rql
  printf 'SELECT o_%s[0] STREAM p_%s FROM o_%s\n' $j $j $j >> q.rql
  printf 'SELECT * STREAM w_%s FROM p_%s@(1,30)\n' $j $j >> q.rql
  printf 'SELECT w_%s[0] STREAM v_%s FROM w_%s.avg\n' $j $j $j >> q.rql
done
seq 1 512 > a.txt; seq 1001 1512 > b.txt; mkdir -p temp
xretractor q.rql -c    # Circular dependency in stream definitions
```

Usunięcie jednego z czterech łańcuchów (`Q = 3`) sprawia, że ten sam plan
kompiluje się poprawnie.

## Kierunek naprawy (nie wykonany)

1. W obu ścieżkach sprawdzić zerowy interwał źródła i zażądać kolejnego
   przebiegu, tak jak robią to gałęzie dwuargumentowe.
2. Warunek zakończenia oprzeć na braku postępu w rozwiązywaniu (żadne zapytanie
   nie zostało rozwiązane w całym przebiegu), a nie na tym, czy licznik
   nierozwiązanych ściśle zmalał.
3. Pokryć testem plan bezcykliczny, którego kolejność przed sortowaniem stawia
   konsumenta przed producentem — z liczbą zapytań z zakresu, w którym wada się
   ujawnia.

Naprawa dotyka `resolveStreamIntervals`, czyli kodu wspólnego dla wszystkich
profili ablacyjnych. Wykonana w trakcie K5 unieważniłaby przypięcie commita
kodu, dlatego jest odłożona.

## Wpływ na K5

1. **Rodzina W4 została przekonstruowana.** Kosztowne wyrażenie siedzi teraz
   w tym samym zapytaniu co wspólny podplan, przez co plan nie zawiera
   strumieni pochodnych o programie jednoelementowym nad przeplotem. Wariant
   ten kompiluje się dla `Q ∈ {1,2,3,4,5,6,7,8,12,16,20,32}`. Odstępstwo od
   pierwotnego brzmienia §9.2 („kosztowny operator **za** wspólnym podplanem")
   polega na tym, że koszt jest wyrażony arytmetyką w projekcji, a nie oknem
   i agregatem w osobnym strumieniu.
2. **`collect.py` pilnuje statusu kompilacji per profil.** Przypadek, który nie
   kompiluje się czysto pod **każdym** z pięciu profili, jest wykluczany
   z reguły decyzyjnej i raportowany imiennie. Bez tego wada mogłaby
   przypadkiem trafić jeden profil, a nie trafić drugiego — bo profile różnią
   się liczbą węzłów, a więc i kolejnością sortowania — i zostałaby odczytana
   jako różnica strukturalna między `STRUCT` a `ALGSTRUCT`.

Punkt 2 jest istotniejszy: to zagrożenie trafności kampanii, nie tylko
niedogodność.
