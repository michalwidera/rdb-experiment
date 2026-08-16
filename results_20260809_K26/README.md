# K26 / H9 — nowa iteracja po K23

Ten katalog jest nową, prospektywną iteracją testu H9. Nie jest korektą
`results_20260808_K23v2/` i nie dziedziczy jego danych ani wyników. K23 pozostaje
zamrożone; łączenie obserwacji między iteracjami jest zabronione.

Stan: **P3–P5 wykonane; STOP-5 zamknięty, P6 nie rozpoczęte**. Nie wykonano
pomiaru kosztowego. Bezpośrednio przed pierwszym P6 `bind_campaign.py` zapisuje
aktualne SHA do ignorowanego `results/ANEKS-0_start.tsv`. Dopiero ten zapis
rozpoczyna kampanię i wiąże rewizje; wcześniej HEAD silnika może się zmieniać,
pod warunkiem przebudowy profili, ponowienia dowodu korpusu oraz końcowego
commitu, pushu i zielonego `freeze_check.sh predeklaracja`.

Najważniejsze różnice wobec K23:

- F9-X jest legalnym programem RQL. Przeploty mają schematy `front` i `rear`, a
  monitor liczy `Sqrt(front*front+rear*rear)` bez odwołań do składników `#`;
- cały zestaw 21 planów jest kompilowany przed zamrożeniem w czterech profilach;
- `RDB_OPT_SIMPLIFY_EXPRESSIONS=ON` jest wspólne dla profili, a główne plany
  mają bramkę braku przepisań R3, aby nowa optymalizacja nie stała się osią H9;
- `corpus_validity` jest osobną, siódmą bramką P6 i ponownie weryfikuje
  zamrożony dowód 84/84 + 4/4 przed bramkami runtime;
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
python3 -m unittest -v test_apparatus.py test_pipeline.py
./verdict.py --selftest
./mechanism_table.py --gate
./calib/gen_calib.py --check
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
- 19/19 testów jednostkowych aparatury (w tym 6 bramek wcześniejszych);
- serializer Flinka 18/18 wobec oracle'a linkowanego z `librdb`;
- F9-X przy `Q=8`: RDB `5/6/10/12` jednostek planu, Flink
  `natural=32`, `manual=5`.

Wszystkie powyższe liczby są bramkami konstrukcji aparatury, nie wynikiem
kosztowym H9.

## Dalszy przebieg

Po przygotowaniu workera `capture_worker.py` zapisuje ANEKS-2/3. W chwili
faktycznego rozpoczęcia `bind_campaign.py` tworzy ANEKS-0 i włącza kontrolę
niezmienności `freeze_check.sh bound`. Po P6 kalibrację zamyka:

```bash
# na workerze; runner sam generuje 15 planów do nowego katalogu OUT i używa data/calib/
OUT=/bezwzgledna/sciezka/do/k26_calib ./calib/run_calib_rdb.sh
./calib/analyze_calib.py --runs /sciezka/do/k26_calib \
  --slots calib/slots.tsv --out results/ANEKS-1_rate.tsv
./freeze_check.sh macierz
```

Macierz wykonuje `run_matrix_supervisor.sh`; surowe dane i indeks SHA pozostają
poza git. Po 1440/1440 wejścia werdyktu powstają deterministycznie:

```bash
./reduce_results.py mechanism --rdb /sciezka/do/P6-rdb \
  --flink /sciezka/do/P6-flink --out /sciezka/do/matrix/mechanism.tsv
./reduce_results.py timing --raw /sciezka/do/P8 \
  --out /sciezka/do/matrix/timing.tsv
```
