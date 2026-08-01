# K22v2 — podręcznik kodowania

## Konstrukcje bazowe

- `C1`: jawna pętla `for`/`while` wewnątrz rdzenia.
- `C2`: mutowalny stan przechodzący między rekordami, identyfikowany kluczem
  `zakres.nazwa`; nie obejmuje wejść `final`, stałych, parametrów ani kolektora
  wyniku.
- `C3`: stan `C2` utrzymujący okno/historię; rozpoznawany przez operację
  przesunięcia/deque albo nazwę `win`, `window`, `history`, `buffer`, `buf`.
- `C4`: zegar, termin, sleep/wait albo jawna synchronizacja.
- `C5`: ręczny warunek rozgrzewki, faza modulo lub stała tail/delay/warmup.
- `C6`: ręcznie nazwana wartość wspólna używana przez co najmniej dwa nazwane
  wyniki; metryka ręcznie potwierdzana i nierozstrzygająca.
- `C7`: pozostała niepusta instrukcja rdzenia.
- `C3d`: deklaracja okna przez `@`, `window`, `countWindow`, `timeWindow`.
- `C4d`: deklaracja interwału/rate.

Każde trafienie zawiera `scope`, plik, linię, tekst oraz `rule_id`. Liczniki
`C2/C3` deduplikują po `(scope,name)`, nigdy po samej nazwie.

## Zmiana

`D1` i `D2` są zdefiniowane w `PREDECLARATION.md` §5. Jedno miejsce edycji to
jeden niezgodny opcode po normalizacji. Przeniesienie tekstu liczy się jako
usunięcie i dodanie, ponieważ zmienia lokalizację odpowiedzialności.

Ręczne drugie kodowanie obejmuje wszystkie 9 baz i wszystkie warianty. Każda
rozbieżność automatu z drugim kodowaniem zatrzymuje kampanię; nie obowiązuje
próg tolerancji.

Drugie kodowanie jest wykonywane z zamrożonego, jawnego pliku
`manual_coding.csv`. Autor drugiego kodowania widzi wyłącznie parę
znormalizowanych rdzeni i wpisuje D1/D2 przed wygenerowaniem tabeli wygranych.
Skrypt porównuje każdy wiersz 1:1 z wynikiem automatu i odmawia werdyktu przy
braku lub rozbieżności. C1--C7 są również sprawdzane w całości na poziomie
listy trafień, ale pozostają opisowe i nie wpływają na H8.
