# K22v3 — protokół wykonawczy po zatrzymanych K22 i K22v2

**Status: ZATRZYMANA — TIMEOUT BAZY F3 PRZED D1/D2.**

Pełna kampania przeszła `base/F1` i `base/F2`, po czym zatrzymała się na
`base/F3`: wspólne 4200 cykli F3, potrzebne dla M3/F3, wytworzyło już 2966
rekordów, ale nie zakończyło procesu w 200 s. Zmiana liczby cykli po
zamrożeniu byłaby zmianą aparatury. K22v3 nie wydaje werdyktu; następca K22v4
używa 4200 wyłącznie dla M3/F3 i 2850 dla pozostałych F3. D1/D2 nie zostały
otwarte ani obliczone.

K22v3 dziedziczy definicje i korpus wariantów wytworzony po
zamrożeniu K22v2. K22v2 nie wydało żadnego wyniku: pierwszy przebieg zakończył
się kodem 37 przed utworzeniem artefaktów, ponieważ absolutne `argv[0]`
skierowało blokadę do katalogu binarki tylko do odczytu. Jedyna zmiana K22v3
dotyczy wywołania tej samej, zahashowanej binarki przez jej nazwę z przypiętym
`PATH`. Kontrole semantyczne przed D1/D2 naprawiły M1/F3 (wielopolowe okno
ujawniło błąd deskryptora silnika; komórka została z góry niepunktowana) oraz
stałą ogona M3/F3 z 19 na wartość 21 odczytaną z planu. Metryki i progi poza
tym konserwatywnym niepunktowaniem nie zmieniają się.

To nadal nie jest nietknięta pierwotna predeklaracja K22. Prospektywna linia
D1/D2 pochodzi z zamrożenia K22v2: warianty powstały po nim, a przed ich
wytworzeniem ustalono metryki i progi; przed K22v3 nie otwarto diffów ani nie
obliczono D1/D2. M1/F2 pozostaje znanym wynikiem pilota i nie może pomagać RQL.

## 1. Przypięcia

| Repozytorium | Commit | Rola |
|---|---|---|
| `retractordb` | `dd733e3792fbcd5727db244b802610a6d710b8dc` | semantyka silnika |
| `paper-arXiv` | `5f7fdbc` | plan resetu K22; wpis K22v3 zostanie przypięty przed kampanią |
| `rdb-experiment` | `fcaa0ed9e3d1ea7f2129f9f06ef70498d8fa2b88` | zatrzymane K22v2 i zamrożony korpus wariantów |

Korpus bazowy to dokładnie dziewięć plików `core.*` z pilota. W korpusie
wariantów 31 z 36 rdzeni pochodzi bez zmian z K22v2@`fcaa0ed`; pięć napraw
M1/F3 i M3/F3 jest jawnie opisanych wyżej. Całość jest weryfikowana hashami w
`manifest.md` i po zamrożeniu nie wolno jej poprawiać.

## 2. Zakres wniosku

K22v3 mierzy jawne obowiązki programu i lokalizację zmian w trzech konkretnych
rodzinach oraz trzech sposobach programowania. Nie jest badaniem ludzi ani
próbą losową z populacji programów. Wynik nie upoważnia do twierdzeń o
zrozumiałości, produktywności, liczbie błędów ani wyższości Javy/Pythona.

Wynik konstrukcji bazowych `C1--C7` jest **opisowy**, ponieważ rdzenie były
znane podczas naprawy aparatury. Prospektywny element rozstrzygający dotyczy
nieoglądanych wariantów modyfikacyjnych.

## 3. Rodziny i zadania

Rodziny pozostają niezmienione:

- F1: FIR 26 odczepów, okno i redukcja;
- F2: niekliniczny potok cech ECG;
- F3: wieloczęstotliwościowy przeplot, przesunięcie i okno.

Każdy wariant powstaje bezpośrednio z bazy, nigdy kumulatywnie.

| Zadanie | F1 | F2 | F3 |
|---|---|---|---|
| M1 | drugi kanał w wyniku | V1 w wyniku — **znany pilot, stały brak wygranej RQL** | drugie pole ze źródła B |
| M2 | okno 26 → 45 | MWI 30 → 45 | okno 30 → 45 |
| M3 | źródło 1000 → 750 Hz | źródło 360 → 250 Hz | A: 10 → 12 Hz i zależne wyrównanie |
| M4 | Q=8 monitorów nad FIR | Q=8 monitorów nad MWI | Q=8 nad wspólnym przeplotem |

Semantyka zadań jest zamknięta następująco (nazwy pól są częścią oracle'a):

- M1/F1 dołącza do `f1_out` pole `channel_2` z drugiego regularnego źródła
  1000 Hz, wyrównane do indeksu logicznego wyniku; źródło ma deterministyczną
  wartość `2000-i` w indeksie `i`.
- M1/F2 jest dokładnie zachowanym wariantem pilota: `qrs_out_3=V1-900`.
- M1/F3 rozszerza źródło B o pole `aux=30000+i`, prowadzi przez przeplot i
  okno wyłącznie bazowe pole `value`, po czym dołącza `B_aux` do `f3_base`.
  Wyniki to `f3_out_0` i `f3_out_1`; wolniejszy `B_aux` jest wyrównywany przez
  `+` do indeksu wyniku (wartość `30000+floor((L-2)/3)` w indeksie logicznym L,
  zgodna z fazą `STREAM_HASH` odczytaną z 30-slotowej kontroli RQL).
  Pierwsza próba przepuszczenia dwóch pól przez `@(1,30)` ujawniła błąd
  deskryptora silnika przed pomiarem D1/D2, dlatego komórka M1/F3 jest
  konserwatywnie z góry liczona jako brak wygranej RQL.
- M2 zmienia tylko wskazane okno; wszystkie dalsze ogony wynikają z planu.
  W F1 wektor współczynników ma wtedy 45 pól: 26 bazowych współczynników i
  19 jawnych zer, a dzielnik normalizujący zmienia się z 26 na 45.
- M3/F1 i M3/F2 zmienia interwał źródła odpowiednio na `1/750` i `1/250`;
  proceduralny pacing to odpowiednio `1_333_333 ns` i `4_000_000 ns`.
  M3/F3 zmienia A na `1/12`, wspólną siatkę na `1/60 s`, jednostki A/B na
  5/12, wyrównanie na `(A>12)#(B>5)`, ogon `f3_mix=21` odczytany z planu i
  pacing przeplotu na `58_823_529 ns` (1/17 s).
  Proceduralny wybór gałęzi realizuje formalne `Hash` silnika:
  `z=12/17`, B wtedy, gdy `floor(z*r)==floor(z*(r+1))`, w przeciwnym razie A;
  zwykłe scalanie znaczników czasu nie daje tej samej fazy Beatty'ego.
- M4 tworzy jeden nazwany wynik z ośmioma polami `q0..q7`, gdzie
  `qj=v+j`. Dla F1 `v=f1_out[0]`, dla F2 `v=mwi[0]`, a dla F3
  `v=f3_mix[0]`. Oracle porównuje właśnie ten ośmiopolowy wynik; bazowy
  program nie ma go i dlatego musi oblać test zadania.

Każde zadanie ma automatyczny test obserwowalnego wyniku: baza musi go oblać,
a wszystkie trzy warianty modelowe muszą przejść wspólny oracle z tolerancją
zero na 2000 zdefiniowanych slotów po ogonie. M1/F2 jest ponownie uruchamiane
wyłącznie jako kontrola semantyczna; jego znany wynik D2 pozostaje stałym
brakiem wygranej RQL.

W M3 oracle sprawdza także deklarowany interwał/rate (RQL z planu
kompilatora, Python/Java z przypiętej stałej); same wartości po indeksach nie
ujawniłyby zmiany częstotliwości F1/F2. Baza ma więc oblać M3 na metadanej
harmonogramu, nawet gdy sekwencja wartości jest identyczna.

## 4. Metryki konstrukcji — opisowe

`C1--C7`, `C3d`, `C4d`, LOC i cyclomatic definiuje `coding_manual.md`.
Najważniejsza korekta względem pilota:

- stan i okna są identyfikowane w zakresie funkcji/klasy, nie globalną nazwą;
- niemutowalne wejścia, konfiguracja i kolektory wyniku nie są stanem okiennym;
- kilka pól `win` w kilku klasach daje kilka obiektów `C3`;
- każde trafienie trafia do `results/hits.csv` i podlega pełnemu drugiemu
  kodowaniu, nie tylko próbce 20%.

## 5. Metryki zmiany — prospektywne

Po pilocie porzucono nakładające się, językowo różne „jednostki programu”.
Wszystkie modele otrzymują tę samą operację na tekście rdzenia:

1. zachować wyłącznie tekst pomiędzy `CORE_BEGIN` i `CORE_END`;
2. usunąć komentarze i puste linie;
3. zwinąć każdą linię do pojedynczych odstępów;
4. porównać sekwencje znormalizowanych linii algorytmem `SequenceMatcher`.

Raportowane są:

- `D1`: suma `max(linie_bazy, linie_wariantu)` dla każdego niezgodnego bloku;
- `D2`: liczba rozłącznych niezgodnych bloków, czyli miejsc edycji;
- pełny unified diff i dokładne zakresy każdego miejsca.

`D2` jest metryką rozstrzygającą lokalizację. Formatowanie jest zamrożone;
zmiany wyłącznie kosmetyczne są zakazane. Sto procent diffów podlega ręcznemu
drugiemu kodowaniu przed otwarciem tabeli zbiorczej.

## 6. Kryterium H8

Wygrana komórki oznacza jednocześnie:

```text
D2_RQL < D2_Python  oraz  D2_RQL < D2_Flink
```

Remis jest brakiem wygranej RQL.

- F1 przechodzi, gdy RQL wygrywa co najmniej 3 z 4 zadań.
- M1/F3 jest z góry zapisane jako brak wygranej; F3 przechodzi tylko przy
  wygranej RQL we wszystkich M2, M3 i M4.
- M1/F2 jest z góry zapisane jako brak wygranej. F2 przechodzi tylko wtedy,
  gdy RQL wygrywa wszystkie nieoglądane M2, M3 i M4.
- H8 otrzymuje ograniczone wsparcie, gdy przechodzą co najmniej 2 z 3 rodzin.

Nie wolno zmieniać progów, metryk, formatowania, rdzeni bazowych ani zadań po
utworzeniu pierwszego nowego wariantu.

## 7. Reprodukowalność i bramki

1. `tests/run.sh` przechodzi przed wygenerowaniem wariantów.
2. `manifest.md` przypina pełne SHA repozytoriów, narzędzi i dziewięciu baz.
3. Każde wywołanie `xretractor` sprawdza `--build-info` oraz SHA-256 binarki.
4. Każdy proces zewnętrzny ma timeout; timeout jest błędem aparatury.
5. Surowe CSV, logi i diffy są pakowane, indeksowane SHA-256 i nie są
   zastępowane samym werdyktem.
6. `results/verdict.md` powstaje także dla NO-GO i pokazuje każdą rodzinę.

Ponieważ K22 nie bada czasu, harness wykonawczy może wyłączyć samo czekanie na
termin (nie obliczanie terminu, indeksów ani kolejności). Kopia wykonawcza
Pythona/Javy różni się od mierzonego rdzenia wyłącznie zamianą warunku
`now < deadline` na fałsz; skrypt zapisuje i sprawdza ten diff. Pełny przebieg
z realnym pacingiem pozostaje kontrolą baz, a nie obserwacją wydajnościową.

## 8. Zamrożenie

| Pole | Wartość |
|---|---|
| Decyzja o resecie | operacyjna kontynuacja po K22v2 bez wyników |
| Plan | `paper-ArXiv@5f7fdbc` |
| Commit zamrażający aparaturę | `3ba765e9556033a73f25b45501fc34048e9dc383` |
| Korpus wariantów | `rdb-experiment@fcaa0ed9e3d1ea7f2129f9f06ef70498d8fa2b88` |
| Pierwszy pomiar D1/D2 | nie istnieje w chwili zamrożenia |
