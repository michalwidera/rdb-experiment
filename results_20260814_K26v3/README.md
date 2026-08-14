# K26v3 / H9 — powtórzenie po K26v2 bez werdyktu

Ten katalog jest nową, prospektywną iteracją testu H9. Nie poprawia zamrożonych
`results_20260808_K23v2/`, `results_20260809_K26/` ani `results_20260810_K26v2/`
i nie dziedziczy ich wyników. K26v2 przeszła cały pomiar — bramki 21/21,
kalibracja 60/60, macierz 1440/1440 — ale zatrzymała się na procedurze
decyzyjnej, która pierwszy raz w całym łuku zetknęła się z prawdziwymi danymi.
Jej werdykt brzmi **BRAK WERDYKTU** i taki pozostaje.

Stan: **F0 — naprawy N1–N8 wykonane, N9 i N10 przed nami; P6 nie rozpoczęte**.
Nie wykonano pomiaru kosztowego K26v3. ANEKS-2/3 wymagają odświeżenia dla nowych
binariów. Bezpośrednio przed pierwszym P6 `bind_campaign.py` zapisuje
aktualne SHA do ignorowanego `results/ANEKS-0_start.tsv`. Dopiero ten zapis
rozpoczyna kampanię i wiąże rewizje; wcześniej HEAD silnika może się zmieniać,
pod warunkiem przebudowy profili, ponowienia dowodu korpusu oraz końcowego
commitu, pushu i zielonego `freeze_check.sh predeklaracja`.

Korpus, dane, bloki, profile, progi i reguły STOP są identyczne z K26v2. Zmiany
metodyczne dotyczą wyłącznie procedury decyzyjnej i jej bramek:

- `instances` ma jedną definicję dla wszystkich rodzin, a strażnik izolacji
  mechanizmu jest sprawdzany na zrzutach planu w P4, nie dopiero w P9 (§7.2);
- kontrola negatywna `Q=1` porównuje z zerem **z tolerancją** (§7.3);
- redukcja jest określona także dla zdegenerowanej metryki odniesienia (§7.4);
- każdy nieprzechwycony wyjątek `verdict.py` daje kod 2, nigdy 1 (§7.5);
- procedura decyzyjna musi przejść **na danych pilota przed** związaniem
  kampanii (§7.5);
- ANEKS-1 jest rozsyłany na workera, a bramka `macierz` sprawdza obie kopie (§12.1);
- żaden wynik K26 ani K26v2 nie wchodzi do P6, P7, P8 ani redukcji K26v3.

Pozostałe różnice wobec K23, odziedziczone z K26:

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
- dane są generowane z ziaren `20260809_2601` i `20260809_2602`.

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
- 23/23 testy jednostkowe aparatury, w tym kontrakty `screen` i odmowa
  nadpisania statusu;
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
OUT=/bezwzgledna/sciezka/do/k26v3_calib ./calib/run_calib_rdb.sh
./calib/analyze_calib.py --runs /sciezka/do/k26v3_calib \
  --slots calib/slots.tsv --out results/ANEKS-1_rate.tsv
./freeze_check.sh macierz
```

Macierz rozpoczyna wyłącznie `start_matrix_screen.sh`; surowe dane, log nadzorcy
i indeks SHA pozostają poza git. Do sesji można wejść przez
`screen -r K26v2-P8-supervisor` i odłączyć się przez `Ctrl-a d`. Po 1440/1440
workerowe sesje zamykają się automatycznie po zapisaniu `runner.rc`, a sesja
hosta po `SUPERVISOR_COMPLETE`. Aktywnej sesji nie wolno kończyć przez
`screen -X quit`. Wejścia werdyktu powstają deterministycznie:

```bash
./reduce_results.py mechanism --rdb /sciezka/do/P6-rdb \
  --flink /sciezka/do/P6-flink --out /sciezka/do/matrix/mechanism.tsv
./reduce_results.py timing --raw /sciezka/do/P8 \
  --out /sciezka/do/matrix/timing.tsv
```
