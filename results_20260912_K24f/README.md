# K24f — H10 dla reguły okna rekordowego

**Wynik:** H10a-win **wsparta** na obu ziarnach — początek logiczny i ogon klasy
`WINDOW` zgadzają się z modelem zdarzeniowym w 100% węzłów, a dziewięć klas K24e
nie wykazuje regresji: **10/10 klas dokładnych** w obu wielkościach jednocześnie.

Silnik: `retractordb` `master`, commit `098e531`. Data: 2026-09-12.

## Czym ta kampania jest

Pomiarem **jednej reguły**, która weszła do silnika po K24e i której dotąd nie
zmierzyła żadna kampania ani bramka:

```
  O = O_src + W - 1,   W = najszersze okno listy SELECT
```

Okno rekordowe w liście `SELECT` (`MIN(pole : W)`) jest przesuwne i stemplowane
końcem przedziału, więc rekord `n` obejmuje rekordy źródła `n-(W-1) … n`, a pierwszy
w pełni określony wypada na `O_src + W - 1`. Korpus K24e nie mógł tego dotknąć:
wypisywał wyłącznie `SELECT *`, a `windowWidthOf()` szuka tokenów okna w programach
pól listy `SELECT`.

## Czym NIE jest

* **Nie jest powtórką K24e.** Rachunek ogona pozostałych dziewięciu klas jest tym
  samym kodem, który K24e zmierzyła; tutaj jest **kontrolą braku regresji**, nie
  przedmiotem twierdzenia. K24e nie jest wyparta.
* **Nie jest kampanią członu (b).** Człon (b) porównuje regułę lokalną z oracle'em,
  nie z silnikiem — zmiana silnika nie może go poruszyć.
* **Nie jest testem prospektywnym.** Reguła była znana przy budowie aparatury.
  Predeklarowane są ziarna, kryteria i przewidywania, nie hipoteza. Status
  dosłownie: potwierdzenie poza próbą na ziarnach nieużytych przy budowie
  aparatury.
* **Nie mówi nic o wydajności** — badanie jest compile-only.
* **Nie obejmuje progu czasowego H9** — inna kampania, ~48 h na przypiętym pi400.

## Zawartość katalogu

| Plik | Co zawiera |
|---|---|
| [`PREDECLARATION.md`](PREDECLARATION.md) | twierdzenie, sześć przewidywań, kryteria, korpus, oba ziarna — **zamrożone przed przebiegiem** |
| [`PIN.md`](PIN.md) | SHA silnika i rodzica, stan drzewa, przełączniki binarki, dziewięć poziomów fazy 0 z liczbami, cztery wady z planu, sumy kontrolne, dowód że korpus K24e nie drgnął |
| [`VERDICT.md`](VERDICT.md) | werdykt na ziarnie głównym `20260912` |
| [`VERDICT_oos.md`](VERDICT_oos.md) | werdykt na ziarnie potwierdzającym `20260913` |
| [`REPORT.md`](REPORT.md) | rozliczenie przewidywań, zestawienie wobec K24e, status epistemiczny, znaleziska aparaturowe |
| [`STOP.md`](STOP.md) | zatrzymanie poziomu bramki odwzorowania, diagnoza, decyzja człowieka, naprawa i przebieg powtórzony |
| `raw/` | surowe CSV kampanii (2 × 10 010 planów) i bramki odwzorowania |
| `apparatus/` | kopia aparatury użytej w przebiegu |
| `SHA256SUMS` | sumy artefaktów |

## Jak czytać wynik

Zielona K24f znaczy **„reguła okna rekordowego zgadza się z modelem zdarzeniowym
na przypiętym SHA"** — nie „silnik jest poprawny".

Jedna rzecz wymaga uwagi przy czytaniu: przewidywanie **P5** (bramka odwzorowania)
było ocenione **dwukrotnie**. Pierwszy przebieg wypadł negatywnie, przyczynę
zdiagnozowano jako granicę aparatury, aparaturę naprawiono za zgodą człowieka
i poziom powtórzono. `STOP.md` niesie całą sekwencję z liczbami przed i po.
Pozostałe pięć przewidywań oceniono raz.
