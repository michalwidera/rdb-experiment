# Legalny projekt F9-X dla iteracji po K23

**Status: kandydat sprawdzony 2026-08-09.** Ten katalog nie jest trzecią
iteracją K23, predeklaracją ani wynikiem pomiarowym. Jest wykonaniem drugiego
warunku wejścia zapisanego w `paper-arXiv/debs/research_plan.md`: projektuje
legalną rodzinę F9-X i sprawdza, że nadal bada złożenie R1 → R2.

Zamrożony katalog `results_20260808_K23v2/` pozostaje nietknięty.

## Decyzja

Historyczny monitor K23:

```rql
SELECT Sqrt(A[0]*C[0]+B[0]*D[0]) STREAM m
FROM ((A>2)#(B>1)) + ((C>2)#(D>1))
```

nie jest programem RQL. Po `#` składniki mają jeden wspólny schemat, więc
`A[0]` i `B[0]` nie oznaczają dwóch zachowanych zatrzasków. Od silnika
`530c80e` taki zapis jest błędem kompilacji.

Nowa rodzina nadaje wspólnemu polu pary przedniej nazwę `front`, a pary tylnej
`rear`. Program czyta dwa pola **wyniku sumy przeplotów**:

```rql
DECLARE front INTEGER STREAM A, 1/100 FILE 'front_vib.txt'
DECLARE front INTEGER STREAM B, 1/50  FILE 'front_cur.txt'
DECLARE rear  INTEGER STREAM C, 1/100 FILE 'rear_vib.txt'
DECLARE rear  INTEGER STREAM D, 1/50  FILE 'rear_cur.txt'

SELECT Sqrt(front*front+rear*rear) STREAM m
FROM ((A>2)#(B>1)) + ((C>2)#(D>1))
```

W slocie wybranym z szybkich torów wynik jest normą pary `(A,C)`, a w slocie
wybranym z wolnych — normą `(B,D)`. Obie pary mają te same takty i fazę
przeplotu, więc `front` i `rear` zawsze opisują tę samą modalność. To jest
legalna, deterministyczna cecha dwóch łożysk, nie próba odzyskania tożsamości
składnika przez `#`.

## Dlaczego nie `&` / `%`

Rozplot jest właściwym zapisem, jeśli dalsze obliczenie naprawdę potrzebuje
osobnych A, B, C i D. Sonda wykazała jednak, że literalne dodanie czterech
rozplotów:

1. zmienia takt publicznego wyniku z `1/150` na `1/100`;
2. dokłada osobną warstwę operatorów;
3. w bieżącym pipeline nie uruchamia przejścia R2 między czterema postaciami.

Byłaby to zatem inna rodzina badająca rozplot, a nie naprawiona rodzina
złożenia R1 → R2. Wariant z odwołaniem do własnego wyniku `m[0]`, `m[1]` jest
legalny, ale również nie nadaje się do tego celu: reguła R2 świadomie wyklucza
takie programy i liczba `STREAM_SELECT_*` spada do zera. `verify.py` zachowuje
oba przypadki jako kontrolę zdolności odróżnienia wariantu obalonego.

## Cztery postacie

Plik [`F9_X_Q8.rql`](F9_X_Q8.rql) utrzymuje kolejność K23: W1, W4, W2, W3.
Każda postać ma dwa monitory, aby dzielenie mogło się zmaterializować.

| Postać | R1 | Kolejność R2 |
|---|---|---|
| W1 | `(A>2)#(B>1)` i `(C>2)#(D>1)` | przód + tył |
| W4 | `(A#B)>3` i `(C#D)>3` | tył + przód |
| W2 | `(A>2)#(B>1)` i `(C>2)#(D>1)` | tył + przód |
| W3 | `(A#B)>3` i `(C#D)>3` | przód + tył |

Na bieżącym silniku cztery profile dają oczekiwaną macierz:

| Profil | R1 | R2 | `STREAM_SELECT_*` | `STREAM_TIMEMOVE_*` |
|---|---:|---:|---:|---:|
| `DEFAULT` | ON | ON | **1** | 0 |
| `NO_R2_CANON` | ON | OFF | **2** | 0 |
| `NO_R1_FACTOR` | OFF | ON | **2** | 6 |
| `NO_R1_NO_R2` | OFF | OFF | **4** | 6 |

To zachowuje istotę F9-X: jedna wspólna instancja `STREAM_SELECT_*` powstaje
wyłącznie wtedy, gdy oba przejścia są włączone.

## Weryfikacja

```bash
cd investigation_F9X_redesign
./verify.py
```

Skrypt:

1. sprawdza flagi i plany czterech lokalnych profili `build/K23-*`;
2. pokazuje, że historyczne odwołanie A–D jest odrzucane przez F9/S3;
3. pokazuje, że legalny mutant `mN[*]` traci R2;
4. generuje niezależne dane w katalogu tymczasowym;
5. wykonuje `Q=8` na co najmniej 2000 rekordach;
6. porównuje osiem artefaktów bitowo i z niezależnym oracle'em
   `isqrt(front²+rear²)`;
7. sprawdza mapę NULL/luk przez `xtrdb`.

Wynik referencyjny 2026-08-09 na SHA silnika
`189b3f8187d80492644438be706e45c7e783b201`: profile `1/2/2/4`, osiem
identycznych wyników, 2246 rekordów, zgodność oracle'a 100%, brak NULL i luk.

## Granica wykonania kroku 2

Projekt rodziny jest domknięty. Przyszła predeklaracja musi jeszcze skopiować
go do **nowego katalogu** (roboczo K26), przygotować zgodny port Flinka i
przeliczyć metryki — starych przewidywań liczbowych K23 nie wolno przenieść
automatycznie. Port ma łączyć bieżące wartości dwóch przeplotów i liczyć
`sqrt(left²+right²)`; nie może utrzymywać zatrzasków A–D, bo odtworzyłby
historyczny model spoza algebry RQL.
