# K26 / H9 — nowa iteracja po K23

Ten katalog jest nową, prospektywną iteracją testu H9. Nie jest korektą
`results_20260808_K23v2/` i nie dziedziczy jego danych ani wyników. K23 pozostaje
zamrożone; łączenie obserwacji między iteracjami jest zabronione.

Stan: **P3–P4 wykonane, predeklaracja przygotowana do przeglądu; STOP-5 otwarty**.
Nie wykonano pomiaru kosztowego. Pełne bramki P6 oraz kalibracja i macierz mogą
ruszyć dopiero po zatwierdzeniu, commicie i pushu zamrożenia.

Najważniejsze różnice wobec K23:

- F9-X jest legalnym programem RQL. Przeploty mają schematy `front` i `rear`, a
  monitor liczy `Sqrt(front*front+rear*rear)` bez odwołań do składników `#`;
- cały zestaw 21 planów jest kompilowany przed zamrożeniem w czterech profilach;
- błąd planu/korpusu ma osobną klasyfikację `corpus`;
- `public_identity` sprawdza `Val(Q)=Val(P)` i `Lat(Q)<=Lat(P)`, więc nie odrzuca
  poprawnego skrócenia ogona przez R1;
- port Flinka liczy normę bieżących wartości dwóch przeplotów i nie ma
  historycznych zatrzasków A–D;
- dane K26 są generowane od nowa z ziaren `20260809_2601` i `20260809_2602`.

## Odtworzenie stanu przed zamrożeniem

```bash
./gen_corpus.py --check
./validate_corpus.py --selftest
./validate_corpus.py --check
python3 -m unittest -v test_apparatus.py
./verdict.py --selftest
./mechanism_table.py --gate
./pilot/run_pilot.py
./pilot/verify_flink_f9x.py  # wymaga lokalnych portów MiniCluster Flinka
./freeze_check.sh preflight
```

Wynik referencyjny przygotowania:

- 37 plików korpusu, w tym dokładnie 21 planów RQL;
- 84/84 poprawne kompilacje i 4/4 odrzucone historyczne mutanty F9-X;
- 24/24 komórki pilota compile-only i runtime;
- 16/16 strumieni F9-X Flinka, po 150 wartości, niezależny oracle 100%;
- 20/20 przypadków własnych skryptu werdyktu;
- 6/6 testów jednostkowych nowych bramek;
- serializer Flinka 18/18 wobec oracle'a linkowanego z `librdb`;
- F9-X przy `Q=8`: RDB `5/6/10/12` jednostek planu, Flink
  `natural=32`, `manual=5`.

Wszystkie powyższe liczby są bramkami konstrukcji aparatury, nie wynikiem
kosztowym H9.
