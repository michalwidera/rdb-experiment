# K19/G16 — ogony i pełna obserwowalność operatorów

Eksperyment sprawdza niezależnie od kodu C++ granice indeksów `SUBTRACT`
i `AGSE`, minimalny ogon fazowy, pojemność historii, zachowanie prawdziwego
`NULL` oraz rozróżnienie ogona od rekordu all-null.

Oracle enumeruje wymierne fazy zamiast powtarzać pętlę wykonawczą silnika.
Kwalifikowane mutacje zmieniają osobno: ogon na częściowe okno, `NULL` na
zero, pusty ślad luk i politykę materializacji. Każda musi zostać wykryta
przez relację obserwowalności.

Obecna polityka luk pozostaje bez zmian: detektor działa na deklaracjach,
natomiast strumienie obliczane mają `G_S = empty`. Włączenie propagacji luk
jest zmianą obserwowalnego artefaktu i wymaga osobnego wersjonowania.

Uruchomienie:

```bash
./run.sh
RDB_BUILD=/sciezka/do/build/Debug ./run.sh
```

Most do silnika uruchamia testy jednostkowe wzorów, test graniczny z `NULL`,
trzy macierze AGSE oraz dokładny round-trip przeplotu i obu rozplotów.
