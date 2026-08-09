# PREDEKLARACJA K26 / H9 — nowa iteracja po K23

**Status: przygotowana do zamrożenia 2026-08-09; STOP-5 pozostaje otwarty do
zatwierdzenia, commitu i pushu. Żaden pomiar kosztowy K26 nie został wykonany.**

Zmiana któregokolwiek z poniższych ustaleń po zamrożeniu wymaga nowej
predeklaracji i nowego katalogu. Danych K23 i K26 nie wolno łączyć.

## 0. Powód nowej iteracji

K23 zakończyła się bez werdyktu. F9-R1 odpadła przez bramkę wymagającą
identycznej liczby artefaktów mimo formalnego warunku `Lat(Q)<=Lat(P)`, a F9-X
nie była legalnym programem RQL: nazywała składniki po przeplocie `#`.

K26 zamyka te dwa defekty aparatury, nie zmieniając hipotezy, progów ani rodzin
F9-R2/F9-R1. Katalog `results_20260808_K23v2/` jest tylko historycznym dowodem;
nie jest źródłem danych, wyników ani klasyfikacji K26.

## 1. Przypięcia i proweniencja

| Pozycja | Wartość |
|---|---|
| Gałąź eksperymentu | `experiment/20260809_K26` |
| SHA silnika | `189b3f8187d80492644438be706e45c7e783b201` |
| Profile | `DEFAULT`, `NO_R2_CANON`, `NO_R1_FACTOR`, `NO_R1_NO_R2` |
| Flink | 2.3.0, JDK 17 przypięty ścieżką |
| Generator danych i RQL | `gen_corpus.py` |
| Korpus | 21 planów: 18 rodzin + 3 kontrole |

Binaria profili są budowane w osobnych `build/K26-*` i przed użyciem
sprawdzane przez `--build-info`. `freeze_check.sh predeklaracja` wymaga czystego
drzewa silnika, właściwego SHA, właściwej gałęzi eksperymentu, czystego drzewa
eksperymentu i zgodności manifestu.

## 2. Pytanie, metryka i próg H9

Pytanie pozostaje takie jak w K23: czy automatyczne rozpoznanie wspólnego
materializowanego podplanu daje co najmniej 40% redukcji logicznych bajtów
substratu na publiczny rekord, względem minimalnej ablacji oraz naturalnego
planu Flinka, bez ceny czasowej większej niż 5% według górnej granicy
sparowanego bootstrapu 95% CI.

Komórką rozstrzygającą jest `Q=8`; `Q={1,2,4}` kontroluje trend, a
`Q={16,32}` skalowanie. Wsparcie H9 wymaga przejścia pełnego progu przez co
najmniej 2 z 3 rodzin. Próg, reguła 2/3, 20 bloków, 10 000 replikacji i ziarno
bootstrapu `20260809_2603` są stałymi `verdict.py`, nie parametrami CLI.

## 3. Rodziny

### 3.1. F9-R2

Źródła `A,B` mają takt `1/100`. Monitor liczy
`Sqrt(A[0]*A[0]+B[0]*B[0])` nad `A+B` albo `B+A`. Mechanizm to kanonizacja
przemiennego `+` oraz wspólna materializacja równoważnego SELECT.

### 3.2. F9-R1

Źródła `A` (`1/100`) i `B` (`1/50`) mają ten sam schemat. Dwie postacie to
`(A>2)#(B>1)` oraz `(A#B)>3`. Program monitora czyta własny wynik. R1 zachowuje
ciąg wartości i origin, ale może skrócić ogon.

### 3.3. F9-X — legalne złożenie R1 → R2

Pary `(A,B)` i `(C,D)` mają odpowiednio wspólne pola `front` i `rear`:

```rql
DECLARE front INTEGER STREAM A, 1/100 FILE 'front_vib.txt'
DECLARE front INTEGER STREAM B, 1/50  FILE 'front_cur.txt'
DECLARE rear  INTEGER STREAM C, 1/100 FILE 'rear_vib.txt'
DECLARE rear  INTEGER STREAM D, 1/50  FILE 'rear_cur.txt'
SELECT Sqrt(front*front+rear*rear) STREAM m
FROM ((A>2)#(B>1))+((C>2)#(D>1))
```

W szybkim slocie wynik jest normą `(A,C)`, w wolnym `(B,D)`. Program odwołuje
się do schematów wyników `#`, nie do tożsamości jego składników. Cztery postacie
W1, W4, W2, W3 zachowują układ R1 × kolejność R2. Przy `Q=8` liczba
`STREAM_SELECT_*` wynosi `1/2/2/4`, a jednostki planu RDB wynoszą odpowiednio
`5/6/10/12` dla czterech profili.

Historyczna postać `Sqrt(A[0]*C[0]+B[0]*D[0])` jest mutantem negatywnym i musi
zostać odrzucona przez każdy profil.

### 3.4. Dlaczego F9-X pozostaje ważną rodziną metodologiczną

F9-X jest rodziną **mechanizmową**, a nie próbą reprezentatywnego benchmarku
całych zastosowań. Jej rolą jest sprawdzenie przypadku, którego nie obejmują
F9-R1 ani F9-R2 osobno: czy wspólna materializacja zostaje rozpoznana dopiero po
złożeniu dwóch niezależnych równoważności, R1 na każdym przeplocie i R2 na ich
sumie. Układ czterech profili jest dzięki temu kontrolą 2×2: `NO_R2_CANON`
usuwa tylko R2, `NO_R1_FACTOR` tylko R1, a `NO_R1_NO_R2` oba przejścia. Rodzina
pozostaje w badaniu tylko wtedy, gdy obserwowana struktura planu ma postać
`1/2/2/4`; inny układ nie jest słabszym efektem H9, lecz nieudaną izolacją
mechanizmu.

Scenariusz ma legalne znaczenie domenowe. `front` i `rear` są dwiema pozycjami
pomiaru, a szybkie tory A/C i wolne B/D są parami tej samej modalności i fazy.
Przeplot wybiera modalność, nie zachowuje tożsamości źródła; w każdym slocie
monitor liczy więc normę dwóch jednoczesnych wartości tej samej modalności.
Nazwa pola wynikowego jest dokładnie informacją dostępną po `#`. Historyczne
zatrzaski A–D oraz wariant z rozplotem `&`/`%` są wykluczone, bo pierwszy nie
jest programem RQL, a drugi zmienia takt, graf operatorów i badany mechanizm.

Postać inline jest częścią badanej populacji, a nie sztucznym sposobem
wymuszenia wyniku. Każdy przesunięty przeplot jest używany raz w pojedynczym
monitorze, więc wydzielenie go przez autora jako nazwany wynik nie usuwa
powtórzenia między `Q` monitorami; przenosi natomiast materializację przez
granicę publiczne/substrat i zmienia mianownik metryki. Badane pytanie brzmi
właśnie, czy kompilator rozpozna wspólną postać powtarzaną przez monitory bez
ręcznego przepisania programu do wariantu `manual`.

Decyzja o zachowaniu rodziny, jej znaczenie i układ ablacji zostały zapisane
przed otwarciem kosztów K26. Liczby `5/6/10/12`, pilot runtime i oracle są
bramkami poprawności konstrukcji, nie obserwacją wspierającą H9. Nawet wynik
pozytywny wolno uogólnić wyłącznie na tę klasę legalnych, jednorazowych
podwyrażeń inline o zgodnych schematach i fazach; nie dowodzi on częstości tej
postaci w programach użytkowników ani ogólnej przewagi wydajnościowej.

## 4. Korpus i dane

| Pozycja | Wartość |
|---|---|
| Ziarno danych głównych | `20260809_2601` |
| Ziarno danych kalibracyjnych | `20260809_2602` |
| Zakres | całkowite `[0,1000]` |
| Źródło szybkie | 3000 rekordów |
| Źródło wolne | 1500 rekordów |
| Kalibracja | 600/300 rekordów, osobny strumień PRNG |
| Siatka Q | `1,2,4,8,16,32` |

`gen_corpus.py --check` wymaga dokładnej zgodności treści oraz odrzuca każdy
dodatkowy plik w `data/` lub `rql/`.

### 4.1. Bramka ważności całego korpusu

Przed zamrożeniem `validate_corpus.py`:

1. wyprowadza dokładną listę 21 planów z generatora;
2. odrzuca brak lub dodatkowy plan na dysku;
3. sprawdza SHA silnika i czystość jego drzewa;
4. sprawdza flagi i tożsamość czterech binariów;
5. kompiluje każdy plan w każdym profilu — 84 kompilacje;
6. wymaga odrzucenia historycznego F9-X w każdym profilu;
7. zapisuje plany, diagnostykę, proweniencję i własny manifest.

Wynik przed zamrożeniem: **84/84 PASS, 4/4 REJECTED, 182 sumy kontrolne**.
`--check` odtwarza kompletność dowodu bez ponownego wyboru populacji.

## 5. Profile i oczekiwania planu

| Profil | R1 | R2 | Rola |
|---|---:|---:|---|
| `DEFAULT` | ON | ON | oba mechanizmy |
| `NO_R2_CANON` | ON | OFF | minimalna ablacja F9-R2 |
| `NO_R1_FACTOR` | OFF | ON | minimalna ablacja F9-R1 |
| `NO_R1_NO_R2` | OFF | OFF | minimalna ablacja F9-X |

Predeklarowane krzywe redukcji wewnętrznej są zamrożone w `verdict.py`:
F9-R2 i F9-R1: `0,0,1/2,1/2,1/2,1/2`; F9-X:
`0,0,1/2,7/12,7/12,7/12` dla rosnącego Q. Odejście od krzywej jest
raportowane, ale samo nie unieważnia wyniku; o H9 rozstrzyga próg.

## 6. Port Flinka

Wariant `natural` tworzy osobny podplan na monitor, a `manual` ręcznie wydziela
wspólną postać osiąganą przez `DEFAULT`. F9-X łączy bieżący rekord przeplotu
`front` z bieżącym rekordem `rear` i liczy `sqrt(left²+right²)`. Nie przechowuje
zatrzasków A–D.

Plan-only przy `Q=8` daje:

| Rodzina | Flink natural | Flink manual |
|---|---:|---:|
| F9-R2 | 5.3333 | 0.6667 |
| F9-R1 | 8 | 1 |
| F9-X | 32 | 5 |

Serializer kanoniczny przechodzi 18/18 wektorów wobec oracle'a C++ linkowanego
z `librdb`. Pilot wykonawczy F9-X uruchamia oba warianty na 100 szybkich i 50
wolnych rekordach: **16/16** publicznych strumieni ma po 150 ciągłych rekordów
i zgadza się w 100% z niezależnym oracle'em `isqrt(front²+rear²)`. Są to bramki
aparatury, nie pomiar H9.

## 7. Bramki poprawności i klasyfikacja

Wymagane bramki per rodzina: `oracle_values`, `oracle_mutants`,
`counter_known_answer`, `public_identity`, `near_miss_controls` oraz
`no_materialization`.

Nieczysty wpis musi otrzymać dokładnie jedną klasyfikację:

| Klasyfikacja | Znaczenie | Skutek |
|---|---|---|
| `engine_or_profile` | rozbieżność przypisana silnikowi/profilowi | ważny wynik przeciw H9 w rodzinie |
| `apparatus` | port, oracle albo harness | brak werdyktu, nowa iteracja |
| `corpus` | plan nie jest poprawnym członkiem zadeklarowanej populacji | unieważnienie komórki i iteracji, nowy katalog |

Brak lub nieznana klasyfikacja daje kod 2 i zakazuje werdyktu. `clean` jest
używane wyłącznie dla PASS.

### 7.1. `public_identity` zgodne z Obs

Dla profili o tym samym stanie R1 wymagane są identyczne artefakty. Dla pary
R1-ON wobec R1-OFF wymagane są:

- identyczny deskryptor;
- identyczny wspólny prefiks wartości i kolejności;
- brak NULL i luk w obu przebiegach;
- co najmniej 2000 wspólnych rekordów;
- liczba rekordów R1-ON nie mniejsza niż R1-OFF, czyli
  `Lat(R1-ON) <= Lat(R1-OFF)`.

Testy negatywne odrzucają dłuższy ogon po optymalizacji, zmianę wartości oraz
NULL/lukę. Sama różna liczba rekordów nie jest już błędem, jeśli różnica ma
dozwolony kierunek.

## 8. Pilot przed zamrożeniem

`pilot/run_pilot.py` najpierw odrzuca plan, który kompiluje się, ale nie wykonuje,
a następnie uruchamia 4 profile × 6 reprezentatywnych planów. Wynik:
**24/24 kompilacje i 24/24 przebiegi runtime**, każdy z wierszami `LOGICAL` i
`WORK` oraz niezerowym mianownikiem.

Pilot nie jest pomiarem kosztowym. Liczniki dowodzą jedynie, że instrument działa
i że główne rodziny materializują niezerowy substrat.

## 9. Kolejność dalszego wykonania

1. przegląd tej predeklaracji i całego diffu;
2. commit i push zamrożenia — STOP-5;
3. pełne bramki P6 na danych głównych, bez odczytu kosztu;
4. klasyfikacja każdego FAIL przed dalszym krokiem;
5. kalibracja na osobnych danych, bez porównania efektu;
6. 20 sparowanych bloków pełnej macierzy;
7. automatyczny werdykt `verdict.py`;
8. raport bez łączenia danych z K23.

Przekroczenie 80% slotu lub zgubiony rekord zatrzymuje całą rodzinę bez
werdyktu. Zmiana rate po takim zatrzymaniu wymaga kolejnej predeklaracji i
nowego katalogu.

## 10. Granica twierdzenia

Nawet wsparcie H9 upoważnia jedynie do stwierdzenia, że w badanych trzech
rodzinach i przy `Q=8` automatyczne współdzielenie osiągnęło zadeklarowany próg
bez zadeklarowanej ceny czasowej. Nie dowodzi ogólnej przewagi RetractorDB nad
Flinkiem ani uniwersalnej redukcji pamięci.
