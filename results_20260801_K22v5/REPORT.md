# K22v5 — raport końcowy

## Wynik

K22v5 nie wspiera H8 według zamrożonego progu: nie przeszła żadna z trzech
rodzin.

| Rodzina | Wygrane RQL w D2 | Próg | Wynik |
|---|---:|---:|---|
| F1 | 0/4 | 3/4 | FAIL |
| F2 | 1/4 | 3/4 | FAIL |
| F3 | 2/4 | 3/4 | FAIL |

RQL ma ściśle mniej miejsc edycji niż oba modele porównawcze tylko w M4/F2,
M3/F3 i M4/F3. W prostych zmianach M2/M3 najczęściej remisuje z Pythonem i
Flinkiem, a remis zgodnie z predeklaracją nie jest wygraną. M1/F2 i M1/F3 są
dodatkowo z góry niepunktowane; ich pomiar nie może poprawić wyniku RQL.

## Poprawność i bramki

- aparatura: `rdb-experiment@3366f1379803f1d46db25c515b9964621372d52f`;
- plan przed kampanią: `paper-arXiv@6a4c5f794060fbe672d04db6aa072c0b9d2708f1`;
- silnik: `retractordb@dd733e3792fbcd5727db244b802610a6d710b8dc`;
- 70/70 kontroli aparatury PASS;
- pełny smoke przed zamrożeniem: 15/15 komórek PASS;
- właściwy oracle: 15/15 komórek PASS, po 2000 pozycji;
- testy negatywne baz: oczekiwany FAIL w 12/12 zadań;
- ręczne D1/D2 wpisane przed automatem: zgodność 36/36;
- ręczny przegląd trafień konstrukcji: 1764/1764;
- pełne diffy, logi, CSV i wyniki mają końcowy indeks SHA-256 w
  `results/artifact_sha256.tsv`.

Opisowy warunek redukcji jawnych obowiązków jest spełniony we wszystkich
trzech bazach: RQL ma C1=C3=C4=0, podczas gdy Python i Flink mają jawne pętle,
stan okna i pacing. Nie wystarcza to jednak do wsparcia H8, ponieważ żaden
wynik rodzinny D2 nie osiąga 3/4.

## Interpretacja

Wynik rozdziela dwie tezy. W badanym korpusie RQL rzeczywiście przenosi pętlę
próbkową, okno i harmonogram z kodu użytkownika do języka/runtime'u. Nie daje
jednak ogólnej, zamrożonej przewagi w lokalizacji zmian: przewaga pojawia się
przy wielomonitorowym sharingu F2/F3 oraz zmianie fazy wieloczęstotliwościowej,
ale nie przy większości lokalnych zmian stałej, interwału lub pola wyniku.

To porównanie trzech konkretnych modeli programowania i trzech rodzin, nie
badanie użytkowników ani losowa próba programów. Nie uzasadnia twierdzeń o
zrozumiałości, produktywności, liczbie błędów ani ogólnej wyższości języka.

## Historia zatrzymań

K22c zachowano jako nieważny pilot po zmianach granicy rdzenia i błędach
metryk. K22v2 zatrzymano przed artefaktami z powodu absolutnego `argv[0]` i
blokady w katalogu binarki. K22v3 zatrzymano na timeoutcie bazowego F3. K22v4
przeszło bazy, lecz ujawniło niemożliwą wspólną etykietę `channel_2` w M1/F1.
Każdą zamrożoną iterację pozostawiono bez cichej naprawy; K22v5 zmieniło tylko
writer poza mierzonym rdzeniem i przed zamrożeniem przeszło pełne 15/15 smoke.
