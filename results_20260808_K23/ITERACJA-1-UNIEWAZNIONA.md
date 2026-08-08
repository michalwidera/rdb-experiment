# Ta iteracja K23 jest UNIEWAŻNIONA — 2026-08-08, w fazie P6, przed jakimkolwiek pomiarem

**Nie łączyć żadnych danych z tego katalogu z danymi iteracji następnej** (§10,
`PREDEKLARACJA.md` §8.3). Katalog zostaje **nietknięty** jako zapis tego, co było
zamrożone; ten plik jest jedynym, który po zamrożeniu tu dopisano.

## Powód

Zamrożony korpus **nie wykonuje się** na przypiętym silniku
`1cfccf97e954025d5fb055f1cfd4f1fa9aff05e8`:

```
$ xretractor F9_R2_Q8.rql -m 100 -r
Unsupported function call: Sqrt
exit = 4
```

Gramatyka zna nazwy funkcji wyłącznie w postaci z wielkiej litery
(`RQL.g4`: `'Sqrt'`, `'Ceil'`, `'Floor'`, …), parser wkłada do tokena tekst
dosłowny (`RQLParser.cpp`, `exitFunction_call`), a ewaluator dopasowywał wyłącznie
nazwy pisane małymi literami (`expressionEvaluator.cpp`: `tkStr == "sqrt"`).
Plan **kompiluje się** i wywraca dopiero w **wykonaniu**.

Zasięg: 14 z 21 zamrożonych planów zawiera `Sqrt` — całe F9-R2 i F9-X wraz
z kontrolami. F9-R1 (program pola `m1[0]*m1[0]`, bez wywołania funkcji) wykonuje
się poprawnie. Przy jednej ważnej rodzinie reguła 2/3 nie może dać werdyktu
(`verdict.py` kod 2), więc iteracji nie da się dokończyć.

## Dlaczego pilot tego nie wykrył

P4 był **compile-only** (`xretractor -c`, 24 kompilacje), a tryb compile-only nie
woła ewaluatora. To ta sama klasa usterki, którą ten projekt notuje po raz szósty:
**bramka nie umiała odróżnić wersji obalonej** — tym razem różnicą było
„kompiluje się" wobec „wykonuje się".

Defekt jest starszy niż kampania: dopasowanie po małych literach pochodzi
z `7388b84` (2023-08-07), nazwy z wielkiej litery w gramatyce z `77d2088`
(2024-06-07). W `test/` i `examples/` nie ma **ani jednego** przebiegu funkcji
pisanej wielką literą; jedyny test, który ich dotyka
(`IntegrationTest_parallel/Pattern4/query-crc.rql`), uruchamia `xretractor -c`
i sam deklaruje w komentarzu, że sprawdza **kompilację**. `ctest` przechodził
183/183 z defektem.

## Klasyfikacja (STOP-6, decyzja człowieka 2026-08-08)

**Defekt aparatury/silnika, nie brak wsparcia H9.** Wszystkie cztery profile
przewracają się identycznie, więc nie jest to rozbieżność między `DEFAULT`
a ablacją. Skutek wg §8.3: zatrzymanie iteracji, nowa wersja, bez łączenia danych.

Wybrane wyjście: **naprawa silnika**. Korpus, dane, siatka `Q`, profile, progi,
ziarna, kolejność bloków, `verdict.py` i strona Flinka są **poprawne** i przechodzą
do iteracji następnej bez zmian merytorycznych; zmienia się wyłącznie przypięcie
SHA, a wraz z nim — zgodnie z §8.3 — predeklaracja i katalog.

## Co z tego katalogu przechodzi dalej

| Pozycja | Stan |
|---|---|
| `gen_corpus.py`, `data/`, `rql/` | bez zmian merytorycznych (naprawa nie dotyka kompilatora ani danych) |
| `gen_blocks.py`, `blocks.tsv`, `verdict.py`, `mechanism_table.py`, `profiles.tsv` | bez zmian |
| `flink/` (sześć jobów, serializer, oracle, plany) | bez zmian — strona Flinka nie zależy od SHA silnika |
| `RAPORT_PILOTA.md`, `pilot/` | w mocy: naprawa jest w ewaluatorze, nie w żadnym przejściu kompilatora, więc liczby compile-only się nie zmieniają (do potwierdzenia bramką w nowej iteracji) |
| `PREDEKLARACJA.md` | **nie przechodzi** — nowa predeklaracja, nowy katalog, nowe SHA |
| binaria hosta i workera | **nie przechodzą** — do przebudowy na naprawionym SHA |

## Co NIE powstało w tej iteracji

Żadnego pomiaru kosztowego, żadnego aneksu (ANEKS-1/2/3 nie istnieją), żadnego
`gates.tsv`, żadnego uruchomienia jobów Flinka. `freeze_check.sh predeklaracja`
przechodził kodem 0 do końca — bramka zamrożenia nie zawiodła; zawiódł pilot.
