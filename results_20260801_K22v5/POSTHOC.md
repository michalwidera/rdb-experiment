# K22v5 — analiza po werdykcie

**Dopisane 2026-08-01, po zamknięciu kampanii wynikiem `a9af132`.**

Ten plik jest **poza zamrożonym pakietem dowodowym**. `REPORT.md`,
`PREDECLARATION.md`, `results/` i `evidence/` pozostają nietknięte, a ich
SHA-256 w `results/artifact_sha256.tsv` są nadal ważne — sprawdzone przed
napisaniem tej analizy. Nic tutaj nie zmienia werdyktu ani żadnej liczby;
analiza dotyczy **mocy dowodowej** protokołu, nie jego wykonania.

## 1. Werdykt przeliczony niezależnie

Przeliczenie z surowych `evidence/diffs/*/*/*.json`, z pominięciem
`results/wins.csv` i `results/verdict.md`, daje ten sam wynik co do komórki:
F1 0/4, F2 1/4, F3 2/4 przy progu 3/4. `results/modifications.csv` zgadza się
z JSON-ami w 36/36 wierszach. `git diff 3366f13..a9af132` potwierdza, że
katalog `tasks/` nie zmienił się po zamrożeniu ani o bajt; jedyne zmiany poza
`results/` i `evidence/` to status w `PREDECLARATION.md`, SHA zamrożenia
w `manifest.md` oraz `README.md` i `REPORT.md`.

Sprawdzone dodatkowo dwie odporności, obie pomyślnie:

- **na metrykę:** ten sam rachunek na `D1` zamiast `D2` daje 0/4, 1/4, 2/4 —
  werdykt nie wisi na wyborze miary rozstrzygającej;
- **na sporne decyzje:** M1/F2 i M1/F3 były z góry zapisane jako brak wygranej,
  ale obie i tak wyszły remisem 2:2. Werdykt nie wisi na `forced_nonwin`.

Wykonanie protokołu nie budzi zastrzeżeń.

## 2. Próg był arytmetycznie nieosiągalny przed pomiarem

`D2 >= 1` z definicji: `metrics/diffsites.py` zgłasza `MeasureError`, gdy
wariant nie różni się od bazy, więc każda policzona komórka ma co najmniej
jedno miejsce edycji. Wygrana wymaga `D2_rql <` **obu** modeli. Zatem w każdym
zadaniu, w którym Python i Flink mają `D2 = 1`, RQL nie może wygrać —
niezależnie od tego, co zostanie napisane w RQL.

| Rodzina | M1 | M2 | M3 | M4 | maksimum osiągalne | próg |
|---|---|---|---|---|---:|---:|
| F1 | wygrywalna | niemożliwa (py=1) | niemożliwa (py=1, fl=1) | niemożliwa (py=1) | **1/4** | 3/4 |
| F2 | z góry przegrana | niemożliwa (1, 1) | niemożliwa (1, 1) | wygrywalna | **1/4** | 3/4 |
| F3 | z góry przegrana | niemożliwa (1, 1) | wygrywalna | wygrywalna | **2/4** | 3/4 |

**Żadna z trzech rodzin nie mogła przejść progu.** Wynik `0/3` był przesądzony
w chwili zamrożenia.

Dało się to stwierdzić bez uruchomienia licznika: wystarczyło przeczytać
zamrożone rdzenie Pythona i Flinka (`WIN = 26` jako nazwana stała, zmieniana
w jednym miejscu) i zestawić je z regułą „remis liczy się przeciw RQL”.
`PREDECLARATION.md` §2 sam odnotowuje, że rdzenie bazowe były znane podczas
naprawy aparatury, więc informacja ta była dostępna.

Kierunek błędu jest przeciwny do naginania — protokół okazał się surowszy dla
własnej hipotezy, niż zakładał — ale konsekwencja pozostaje: **werdykt „H8 bez
wsparcia” niesie bardzo mało informacji o samej H8.** Nie odróżnia świata,
w którym H8 jest fałszywa, od świata, w którym jest prawdziwa, bo w obu
protokół zwraca `0/3`.

## 3. Co ta kampania faktycznie zmierzyła

Twierdzenie, które te dane rzeczywiście uzasadniają, jest węższe od H8 i warto
przenieść do artykułu właśnie je:

> RQL nie ma nazwanej stałej ani parametru planu, więc w zmianie pojedynczej
> wartości przegrywa z dowolnym dobrze sfaktoryzowanym programem imperatywnym.
> Przewaga pojawia się wyłącznie tam, gdzie zmiana pociąga za sobą arytmetykę
> wyrównania: M3/F3 (2 wobec 5 i 5) oraz M4/F2 i M4/F3 (1 wobec 2 i 2).

Ilustracja w `evidence/diffs/M2/F1/`: RQL zmienia `26` w trzech miejscach —
deklaracji tablicy współczynników, operatorze okna `@(1,26)` i dzielniku
normalizującym `/26` — podczas gdy Python i Flink w jednym, bo mają `WIN`.
To jest realny i cytowalny wynik o języku. Nie jest to wynik o deklaratywności.

## 4. Dwie dalsze granice konstrukcyjne

1. **M4 nie realizuje zadania z planu.** `research_plan.md` §K22 definiuje M4
   jako „dodać `Q=8` **niezależnie nazwanych** monitorów korzystających z tego
   samego podplanu, bez ręcznego współdzielenia”. Zamrożona predeklaracja
   zwęziła to do jednego nazwanego wyniku z ośmioma polami `qj = v+j`, czyli do
   operacji trywialnie wektoryzowalnej. M4 miało być zadaniem, w którym RQL ma
   przewagę strukturalną z tytułu sharingu; w tej postaci mierzy co innego.
   Zwężenie zapadło podczas naprawy aparatury w łańcuchu K22v2--K22v5 i nie
   zostało wtedy odnotowane jako zmiana zakresu.
2. **Jeden koder.** Wszystkie 36 wierszy `manual_coding.csv` mają
   `Codex-manual`. „Zgodność 36/36” to zgodność automatu z jednym agentem, nie
   inter-rater reliability. Do artykułu trzeba albo dwóch niezależnych koderów
   i miary zgodności, albo jawnego zdania, że metryka jest w pełni
   algorytmiczna, a kodowanie ręczne było kontrolą implementacji licznika.
   Drugie jest przy `SequenceMatcher` obronne, ale musi być tak nazwane.

## 5. Wniosek metodologiczny

Reguła do zapamiętania, ogólniejsza niż ta kampania:

> **Przed zamrożeniem policzyć maksimum osiągalne przy zamrożonym korpusie
> i progu.** Jeżeli maksimum jest niższe od progu, protokół nie jest testem
> hipotezy, tylko jej kosztownym odrzuceniem.

Kontrola jest tania — wymaga wyłącznie przeczytania korpusu porównawczego
i policzenia, w ilu komórkach przeciwnik ma wartość minimalną metryki.
Jest bliską krewną reguły zapisanej po badaniu higienicznym `e1e5181`:
kryterium zapisane słowami i kryterium zapisane w kodzie muszą dać się
zestawić. Tutaj zestawić trzeba było kryterium z **przestrzenią możliwych
wyników**.
