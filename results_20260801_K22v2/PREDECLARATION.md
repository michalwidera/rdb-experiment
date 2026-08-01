# K22v2 — zamrożony protokół po zatrzymanym pilocie K22

**Status: ZATRZYMANA — BŁĄD HARNESSU PRZED PIERWSZYM WYNIKIEM.**

Po wygenerowaniu wariantów pierwszy przebieg `base/F1` zakończył się przed
utworzeniem artefaktów: harness wywołał `xretractor` pełną ścieżką, więc
`argv[0]` spowodował próbę utworzenia blokady w katalogu binarki tylko do
odczytu. Naprawa wywołania zmieniałaby zamrożoną aparaturę po pierwszym
wariancie, dlatego K22v2 nie wydaje werdyktu. Następca: `../results_20260801_K22v3/`.

K22v2 jest prospektywną kontynuacją po jawnym pilocie
`results_20260801_K22/`. Nie jest przedstawiana jako nietknięta pierwotna
predeklaracja. Pilot służył do ustalenia semantyki i naprawy aparatury; jego
jedyna komórka modyfikacyjna M1/F2 jest znanym wynikiem i nie może pomagać RQL
w kryterium poniżej.

## 1. Przypięcia

| Repozytorium | Commit | Rola |
|---|---|---|
| `retractordb` | `dd733e3792fbcd5727db244b802610a6d710b8dc` | semantyka silnika |
| `paper-arXiv` | `ef166c5` | plan i reguła przejścia pilota do K22v2 |
| `rdb-experiment` | `8ca125806a6f302eb3cc51636110d784f4a24390` | zamknięty pilot i rdzenie bazowe |

Korpus bazowy K22v2 to dokładnie dziewięć plików `core.*` z commita pilota,
zweryfikowanych hashami w `manifest.md`. Nie wolno ich poprawiać po zamrożeniu;
warianty powstają wyłącznie w tym katalogu.

## 2. Zakres wniosku

K22v2 mierzy jawne obowiązki programu i lokalizację zmian w trzech konkretnych
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
- M1/F3 rozszerza **oba** źródła przeplotu o pole `aux`: dla A jest to
  `20000+i`, dla B `30000+i`. Przeplot, przesunięcie i `avg` działają na obu
  polach; wyniki to `f3_out_0` i `f3_out_1`. To usuwa wcześniejszą
  niejednoznaczność sformułowania „pole ze źródła B”.
- M2 zmienia tylko wskazane okno; wszystkie dalsze ogony wynikają z planu.
  W F1 wektor współczynników ma wtedy 45 pól: 26 bazowych współczynników i
  19 jawnych zer, a dzielnik normalizujący zmienia się z 26 na 45.
- M3/F1 i M3/F2 zmienia interwał źródła odpowiednio na `1/750` i `1/250`;
  proceduralny pacing to odpowiednio `1_333_333 ns` i `4_000_000 ns`.
  M3/F3 zmienia A na `1/12`, wspólną siatkę na `1/60 s`, jednostki A/B na
  5/12, wyrównanie na `(A>12)#(B>5)`, wynikowy ogon przesunięcia na 19 i
  pacing przeplotu na `58_823_529 ns` (1/17 s).
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
- F3 przechodzi, gdy RQL wygrywa co najmniej 3 z 4 zadań.
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
| Decyzja o resecie | potwierdzona 2026-08-01 przed zmianami K22v2 |
| Plan | `paper-ArXiv@ef166c5` |
| Commit zamrażający aparaturę | `f8ecdb8a5115ff6d04682317b1f8c2f6aae666c2` |
| Pierwszy wariant K22v2 | nie istnieje w chwili zamrożenia |
