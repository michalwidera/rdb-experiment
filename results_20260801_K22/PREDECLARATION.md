# K22 — predeklaracja: deklaratywny koszt specyfikacji i modyfikacji monitora

**Status: PROJEKT DO PRZEGLĄDU CZŁOWIEKA. Nie utrwalona.**

Ten dokument powstaje **przed** utworzeniem brakujących programów korpusu,
przed uruchomieniem oracle'a i przed obliczeniem jakiejkolwiek metryki
(`REQUIREMENTS.md` R3, etap K22a z `next_session_K22.md`). Po zatwierdzeniu
przez człowieka i commicie staje się niemutowalny: każda późniejsza zmiana
definicji metryki, granicy rdzenia, przypisania zadań albo progu decyzyjnego
unieważnia kampanię i wymaga nowego katalogu `results_YYYYMMDD_K22b`.

Bramka: **bez zaakceptowanej predeklaracji nie wolno przejść do K22b.**

---

## 0. Pytanie i teza

RQ7 (`research_plan.md` §5.1): dla równoważnych statycznych zadań monitorowania
jaką część proceduralnej odpowiedzialności RQL usuwa z programu użytkownika?

H8 (`research_plan.md` §5.2): dla semantycznie równoważnych statycznych potoków
regularnych RQL zawiera mniej jawnych konstrukcji sterowania i stanu oraz
wymaga zmian w mniejszej liczbie jednostek programu dla zamrożonych
modyfikacji.

**Czego K22 nie bada.** Nie mierzy szybkości, throughputu ani real-time (to
było P0/K6, zamknięte werdyktem A=0/B=12/C=1). Nie odpowiada na pytanie, czy
człowiek szybciej rozumie RQL, jest bardziej produktywny albo popełnia mniej
błędów — to wymagałoby badania ludzi i osobnego protokołu etycznego. Nie
porównuje języków: porównuje **modele programowania**. Wniosek „Java/Python
jest gorszy" jest zakazany niezależnie od wyniku.

---

## 1. Rewizje wejściowe i provenance

Zamrożone punkty odniesienia (zweryfikowane 2026-08-01, drzewa czyste):

| Repozytorium | Commit | Rola |
|---|---|---|
| `retractordb` | `dd733e3` | silnik; źródło semantyki i programów RQL |
| `rdb-experiment` | `91352d3` | to repozytorium; baseline'y i rodziny W |
| `paper-arXiv` | `6375de5` | plan badawczy i artykuł |

SHA-256 programów wejściowych w chwili zamrożenia. Kopie trafiają do
`corpus/*/provenance/` **bez modyfikacji**; oczyszczanie odbywa się w osobnym
pliku rdzenia, żeby diff „oryginał → rdzeń" był przeglądalny.

| Plik | SHA-256 | Rola w K22 |
|---|---|---|
| `retractordb:examples/ecg/rec205/rec205-qrs.rql` | `8f55a162b7986fc77367f17b481c4ca45898578be5b15d6beb550e98356e13b3` | baza F2 (RQL) |
| `retractordb:examples/ecg/rec205/rec205-detect.rql` | `f0fbe8fce36851a49987e5535e08a35c7c1eb8caf5de36417153d18ff8574232` | wzorzec zachowania po M1 (F2) |
| `retractordb:examples/ecg/rec205/bp_coef.txt` | `99e4619a07797822c5afd34bf9cb88d9bff8f9cd808b0faa0667d07645f978c2` | współczynniki band-pass (25) |
| `retractordb:examples/ecg/rec205/d_coef.txt` | `39c0f3bc6135e87acf72ebc0aa159dce329436665251fc2a9dc50d0625aa1c6c` | współczynniki różniczki (5) |
| `config/dsp-simple-fir.rql` | `81f7b58b81d0cee15590470b109a163e3102ae8755c253d1c26bdf99dddaa4cc` | punkt wyjścia F1 (RQL) |
| `config/pan_tompkins_numpy.py` | `88e1697a65428904ee1e8738b6be2eaf4f4fc3e3bc4e80f31cb7c233f8426a18` | provenance F2 (Python) |
| `config/PanTompkinsFlinkJob.java` | `4cbb0f6105f7e65a6c1e73a391bcd8c25b6ee86fbe66f18129cbcbf6a0108b06` | provenance F2 (Flink) |
| `results_20260730_K6c/generate.py` | `b7627f132146f0fc94f32319df921eeaf02e6b1b02937b3f2a9d6b31b3794b04` | provenance F3 (rodziny W2/W8) |

### 1.1. Czego z provenance NIE wolno użyć wprost

`pan_tompkins_numpy.py` (211 linii) i `PanTompkinsFlinkJob.java` (344 linie)
powstały jako **baseline'y czasowe**. Zawierają: parser argumentów, `SCHED_FIFO`,
fazę settle, sondę CSV, `gc.disable()`, tryb `batch`, `Tuple8` niosący znaczniki
czasu przez cały potok, `setBufferTimeout(0)`, `ProbeSink`. Porównanie 211/344
z ~20 liniami RQL byłoby porównaniem harnessów, nie modeli programowania.
**Surowy LOC tych plików nie wchodzi do żadnej tabeli K22.**

Druga, poważniejsza przeszkoda: oba liczą w `float64`, a RQL liczy w liczbach
całkowitych z konwersją przez `boost::rational<int>` (§4). Nie są więc
semantycznie równoważne z RQL nawet po usunięciu harnessu. Rdzenie K22 dla
Pythona i Flinka powstają **od nowa w arytmetyce całkowitej** zgodnej z §4;
pliki provenance służą wyłącznie jako wzorzec struktury etapów i jako dowód, że
K22 nie wymyślił nierealistycznej implementacji porównawczej.

---

## 2. Granica rdzenia: `CORE_BEGIN` / `CORE_END`

Metryki liczone są **wyłącznie** między znacznikami. Każdy plik korpusu ma
dokładnie jedną parę znaczników na jednostkę pliku; dopuszczalne jest wiele
rozłącznych par w jednym pliku (np. klasa operatora + blok składania topologii).

```text
RQL:    # CORE_BEGIN / # CORE_END
Python: # CORE_BEGIN / # CORE_END
Java:   // CORE_BEGIN / // CORE_END
```

**Wewnątrz rdzenia (liczone):** deklaracja źródeł i ich interwałów, definicja
okien, wyrażenia algorytmu, definicja i nazwanie wyjść, cały stan i sterowanie
potrzebne do tego, żeby monitor policzył swój wynik przyrostowo.

**Poza rdzeniem (nieliczone):** parsowanie argumentów, wczytanie plików
wejściowych z dysku do pamięci, konfiguracja frameworka niezwiązana z
semantyką potoku, polityka szeregowania procesu, instrumentacja i sondy,
formatowanie i zapis wyniku kanonicznego, `main()` wołający rdzeń, importy,
komentarze, deklaracja pakietu.

### 2.1. Reguła sporna, rozstrzygnięta z góry

Pacing (utrzymanie tempa slotu) **należy do rdzenia**, nie do harnessu.
Uzasadnienie: to jest dokładnie przedmiot sporu H8 — czy autor monitora musi
napisać pętlę taktującą. Wyrzucenie pacingu do harnessu przesądziłoby wynik
przez definicję. W RQL odpowiednikiem jest interwał w `DECLARE` (jedna
konstrukcja domenowa, liczona w C7, nie w C4); w Pythonie `deadline`/`sleep`;
we Flinku `PacedSource` albo generator zdarzeń.

Konsekwencja przeciwna, dla uczciwości: **emisja do sinka i pomiar czasu do
rdzenia nie należą.** RQL też ich nie deklaruje.

### 2.2. Zasada oczyszczania

Oczyszczenie provenance → rdzeń musi być **semantyczne i jawne**, nigdy
redakcyjne na korzyść RQL. Każde usunięcie linii z pliku provenance ma trafić
do `corpus/<rodzina>/<model>/CLEANUP.md` z jednym z trzech uzasadnień:
`harness` (poza granicą §2), `arytmetyka` (zmiana float→int wg §4),
`format wyjścia` (kanoniczny CSV §5). Usunięcie bez uzasadnienia jest błędem
aparatury i musi zostać cofnięte.

---

## 3. Trzy rodziny

Wejścia są **zamrożone i deterministyczne**. Żadna rodzina nie używa
`/dev/urandom` — `dsp-simple-fir.rql` czyta losowe bajty, co uniemożliwia
oracle; F1 zastępuje to zamrożonym plikiem.

### F1 — FIR z oknem i redukcją

Izoluje podstawowy obowiązek utrzymania okna i stanu. Bez ECG.

| Element | Wartość zamrożona |
|---|---|
| źródło | `f1_source.txt`, 4096 wierszy, `INTEGER`, wartość wiersza `i` (0-indeksowany) = `((i * 37) % 1000) - 500` |
| interwał źródła | `1/1000` s |
| współczynniki | `f1_coef.txt`, 25 wartości `INTEGER`, kopia `test/IntegrationTest_parallel/dsp/filterremez.txt` (SHA-256 do wpisania przy kopiowaniu) |
| okno | `@(1,25)` |
| redukcja | `.sumc`, następnie `/25/1000` |
| wyjście | strumień `f1_out`, jedno pole `y` |

Zakres wartości: `|x| ≤ 500`, `|coef| ≤ 32767` (do potwierdzenia po skopiowaniu
pliku), okno 25 → `|Σ| ≤ 25 · 500 · 32767 ≈ 4,1·10^8 < 2^31−1`. Przepełnienie
`int32` **wykluczone przez zakres danych**; test `oracle/test_range.py` to
sprawdza i jest warunkiem wejścia rodziny do tabeli.

### F2 — niekliniczny potok cech ECG

Baza: `rec205-qrs.rql` (SHA w §1). Pięć etapów: band-pass 25-tap →
różniczka 5-tap → kwadrat/1000 → MWI `@(1,30)`.avg → próg `@(1,180)`.avg.
Wejście: `rec205` (int32 LE, pary MLII,V1), 360 Hz, interwał `1/360`.

**To nie jest detektor kliniczny.** Zakaz twierdzeń diagnostycznych, brak
Se/PPV/F1, brak anotacji uderzeń (`205.atr` nie jest używany). To potok cech.

Wyjście bazowe `qrs_out`: `mlii-900`, `mwi*5`, `(mwi - mwi_thr*2)*5`.

### F3 — monitor wieloczęstotliwościowy

Musi **rzeczywiście** używać wymiernych interwałów, przesunięcia `>N`,
przeplotu `#` i nazwanych monitorów. Osiem kopii niezależnego filtra nie
spełnia tego warunku.

| Element | Wartość zamrożona |
|---|---|
| źródło A | `f3_a.txt`, 8000 wierszy, wartość wiersza `i` = `i + 1`, interwał `1/10` s |
| źródło B | `f3_b.txt`, 8000 wierszy, wartość wiersza `i` = `1001 + i`, interwał `1/5` s |
| konstrukcja bazowa | `SELECT * STREAM f3_out FROM (A>2)#(B>1)` |
| liczba monitorów w bazie | `Q = 1` |

Baza pochodzi z rodziny W2 z `generate.py` (§1), gdzie warunek reguły
`i·Δ_A = k·Δ_B` zachodzi dla `(i,k) = (2,1)`. Interwał przeplotu:
`Δ_φ = 1/(1/Δ_A + 1/Δ_B) = 1/15` s.

**Zakaz ręcznego sharingu w wersji źródłowej.** Wersje Python i Flink nie mogą
zawierać ręcznie wpisanego współdzielenia wspólnego podplanu **ani** ręcznie
zduplikowanego obliczenia dobranego tak, by pomóc RQL. Reguła rozstrzygająca:
autor pisze wersję porównawczą tak, jak napisałby ją kompetentny programista
tego modelu **nieznający wyniku K22** — czyli najprostszą poprawną. Jeżeli w
danym modelu najprostsza poprawna wersja zawiera sharing (bo framework go
oferuje deklaratywnie), to sharing zostaje i jest liczony jako 0 w C6.

---

## 4. Semantyka arytmetyczna — odczytana z silnika, nie założona

Wszystkie reguły niżej pochodzą z kodu `retractordb@dd733e3`. Odniesienia są
częścią predeklaracji: recenzent ma móc je sprawdzić bez uruchamiania.

| Reguła | Zachowanie | Źródło |
|---|---|---|
| dzielenie `INTEGER/INTEGER` | C++ `int/int`, **obcięcie do zera** (nie `//` Pythona) | `expressionEvaluator.cpp:206` |
| dzielenie przez zero | wynik `NULL`, strumień pracuje dalej — **nie wyjątek** | `expressionEvaluator.cpp:189-199` |
| `NULL` w `+ - * /` | pochłaniający: dowolny operand `NULL` → `NULL` | `expressionEvaluator.cpp:84,114,146,178` |
| typy mieszane | promocja do wyższego indeksu wariantu: `BYTE < INTEGER < UINT < RATIONAL < FLOAT < DOUBLE` | `expressionEvaluator.cpp:72-80`, `fldType.hpp:15` |
| `.sumc` / `.avg` na `INTEGER` | pola rzutowane na `boost::rational<int>`, sumowane **dokładnie** | `streamInstance.cpp:256-275` |
| dzielnik `.avg` | **liczba pól NIE-`NULL`** (`validItemCount`), nie szerokość okna | `streamInstance.cpp:288-290, 318-319` |
| finalizacja `INTEGER` | `rational_cast<int>` = obcięcie do zera, z nasyceniem do `INT_MAX`/`INT_MIN` | `streamInstance.cpp:352-362` |
| wszystkie pola `NULL` | wynik agregatu `NULL` | `streamInstance.cpp:312-316` |
| przepełnienie w `.sumc` | przechwycone → `numeric_limits<T>::max()` (nasycenie) | `streamInstance.cpp:172-178` |
| przepełnienie w `a*b` na `int` | **nie** przechwycone (zwykłe `int`) | `expressionEvaluator.cpp:155` |

### 4.1. Konsekwencje wiążące dla portów

1. **Python nie może użyć `//`.** `-7 // 2 == -4`, a silnik daje `-3`.
   Rdzeń Pythona używa funkcji `idiv(a, b)` z `oracle/refsem.py`, która obcina
   do zera i zwraca `None` dla `b == 0`.
2. **Java `/` na `int` jest zgodna** (obcięcie do zera), ale dzielenie przez
   zero rzuca `ArithmeticException` zamiast dać `NULL` — rdzeń Flinka musi
   jawnie obsłużyć zero jako `NULL`.
3. **Zero-fill okien jest zakazany.** Oba baseline'y inicjują okna zerami
   (`np.zeros`, `new double[WIN]`) i dzielą przez pełne `N`. Silnik dzieli przez
   `validItemCount`. Rdzenie K22 muszą odwzorować regułę silnika albo — jeśli
   ogon jest wyciszony (§5.2) — nie emitować w ogóle w slotach ogona.
4. **Przepełnienie jest wykluczane zakresem danych, nie nadzieją.**
   `oracle/test_range.py` liczy najgorszy przypadek dla każdej rodziny wprost z
   zamrożonych danych i współczynników. Rodzina, która tego nie przejdzie, nie
   wchodzi do tabeli równoważności wartości.

---

## 5. Oracle: kanoniczny strumień i zakres porównania

### 5.1. Format kanoniczny

```text
family,variant,logical_index,field_name,value,is_null,is_gap
```

Reguły zapisu (zamrożone):

- `logical_index` — numer slotu strumienia wyjściowego, liczony **od 0 dla
  pierwszego slotu istnienia strumienia**, łącznie ze slotami ogona.
- `field_name` — nazwa pola z deklaracji wyjścia. Kolejność wierszy w obrębie
  jednego `logical_index` jest kolejnością pól w deklaracji i jest **istotna**.
- `value` — dziesiętna reprezentacja liczby całkowitej bez separatorów, `-`
  dla wartości ujemnych. Dla `is_null=1` pole `value` jest puste.
- `is_null` / `is_gap` — `0` albo `1`. `is_gap=1` oznacza brak rekordu
  w slocie (ogon, luka), `is_null=1` — rekord istnieje, ale pole nie ma wartości.
- Bez nagłówka w danych; nagłówek wyłącznie w `expected/`.

### 5.2. Pierwszy emitowany indeks — czytany z silnika

Silnik **wycisza emisję** przez pierwsze `startupLatency` slotów:
`dataModel.cpp:167` (`if (elapsedSlots++ < max(startupLatency,0)) continue;`).
Wartość jest wyliczana w `compiler::computeStartupLatency()` i publikowana jako
`tail=` przez `xretractor <plan>.rql -c` (`presenter.cpp:345`).

> **Uwaga do zapisania w raporcie.** Komentarz w `compiler.cpp:958-960`
> twierdził, że przebieg „wyłącznie WYLICZA ogon", a doprowadzenie emisji do
> zgodności jest „osobnym krokiem" — było to nieaktualne wobec
> `dataModel.cpp:167`. Rozbieżność wykryto podczas audytu K22a i **poprawiono
> sam komentarz** w `retractordb` (zmiana wyłącznie dokumentacyjna, zero wpływu
> na zachowanie silnika, `ut_compiler` i `ut_presenter` przechodzą). Nie jest to
> naruszenie zakazu zmiany silnika dla ułatwienia GO: poprawka nie dotyka
> semantyki i nie może przesunąć żadnej metryki. Fakt o ogonie i tak ustala
> pomiar, nie komentarz.

**Reguła zamrożona:** `tail` **nie jest wyliczany w predeklaracji**. Jest
odczytywany z `xretractor <plan>.rql -c` dla każdego strumienia wyjściowego każdego
wariantu i zapisywany w `results/tails.csv` przed porównaniem. To jest wprost
wniosek metodologiczny z K6c: *to, co system wie, należy z systemu odczytać, a
nie odtwarzać rachunkiem obok niego.* Rachunek równoległy w predeklaracji był
tam źródłem błędu i nie zostanie powtórzony.

### 5.3. Zakres porównania

Niech `T` = maksimum `tail` po wszystkich trzech modelach danej rodziny/wariantu.

- Zakres porównywany: `logical_index ∈ [T, T + 2000)`.
- W zakresie porównania oczekiwane jest `is_gap = 0` dla każdego indeksu.
  Luka wewnątrz zakresu jest **porażką oracle'a**, nie do zignorowania.
- Sloty `logical_index < T` są raportowane w `semantic.csv`, ale **nie wchodzą
  do rozstrzygnięcia równoważności** — modele mają prawo do różnych ogonów.
  Sama wartość `tail` per model jest natomiast raportowana jako wynik.
- `2000` slotów zamrożone dla wszystkich rodzin. Uzasadnienie: przy F2
  (`tail` rzędu 234 slotów) daje ponad 8-krotność ogona, a przy F1/F3 pokrywa
  wielokrotność okresu przeplotu.

### 5.4. Werdykt równoważności

Rodzina/wariant przechodzi oracle, gdy dla **każdego** `logical_index`
w zakresie i **każdego** pola: zgadzają się `field_name`, `value`, `is_null`
i `is_gap` we wszystkich trzech modelach, bajt w bajt po normalizacji zapisu
z §5.1. Tolerancja numeryczna: **zero**. Arytmetyka jest całkowita, więc
tolerancja byłaby przyznaniem, że porty nie realizują tej samej semantyki.

Model, którego nie da się doprowadzić do tej samej arytmetyki, wchodzi do
analizy struktury specyfikacji, ale **nie** do tabeli równoważności wartości —
i ten fakt jest raportowany jawnie, nie pomijany.

---

## 6. Mapa zadań M1–M4 na rodziny — pełna macierz 3×4

Zamrożone przed jakąkolwiek implementacją. **Każda rodzina otrzymuje wszystkie
cztery zadania**: 12 wariantów na model, 36 wariantów łącznie.

Powód wyboru pełnej macierzy: kryterium go/no-go z `research_plan.md` mówi
„na co najmniej dwóch z trzech rodzin ... M1–M4 wymagają zmian w mniejszej
liczbie jednostek programu". Przy przypisaniu 1:1 zadanie→rodzina to zdanie
przestaje mieć sens dosłowny, a rodzina ma jeden punkt pomiarowy zamiast
czterech. Pełna macierz **usuwa też zagrożenie ważności nr 1** (autor
przypisuje zadanie do rodziny wygodnej dla RQL) — nie ma czego przypisywać.

|  | F1_fir | F2_ecg | F3_multirate |
|---|---|---|---|
| **M1** dodać drugi kanał do nazwanego wyniku | drugie źródło `f1_source2.txt` dołączone do `f1_out` | `ecg.V1` dołączone do wyniku (wzorzec: `rec205-detect.rql`) | drugie pole ze źródła `B` w `f3_out` |
| **M2** zmienić szerokość wskazanego okna | `@(1,25)` → `@(1,45)` | MWI `@(1,30)` → `@(1,45)` | okno agregujące `@(1,30)` → `@(1,45)` nad `f3_out` |
| **M3** zmienić interwał źródła i zależne wyrównanie | `1/1000` → `1/750` | `1/360` → `1/250` | `Δ_A: 1/10 → 1/12`, przesunięcia zależne |
| **M4** dodać `Q=8` nazwanych monitorów wspólnego podplanu | 8 monitorów nad wyjściem FIR | 8 monitorów nad `mwi` (wzorzec: rodzina W8) | 8 monitorów nad `(A>2)#(B>1)` (wzorzec: W2) |

### 6.1. Reguły wykonania zadań

1. **Każdy wariant powstaje z czystej bazy, nie kumulatywnie.** Inaczej
   kolejność zadań zmieniałaby wielkość diffu. `tasks/M2/F1_fir/python/` jest
   diffem wobec `corpus/F1_fir/python/`, nie wobec `tasks/M1/...`.
2. **Zadanie opisuje zmianę zachowania, nie sposób implementacji.** Tabela
   wyżej podaje, co ma być inne w wyniku; nie podaje, jak to osiągnąć w żadnym
   z modeli.
3. **M2 w F1 i F2 zmienia ogon.** Nowy `tail` jest odczytywany z silnika (§5.2),
   nie wyliczany. Zakres porównania przesuwa się razem z `T`.
4. **M3 zmienia interwał, więc zmienia liczbę slotów w sekundzie.** Zakres
   porównania pozostaje 2000 **slotów**, nie 2000 sekund.
5. **M4 nie wolno realizować przez ręczny sharing w wersji porównawczej**
   ani przez ręczną duplikację w wersji RQL. Obowiązuje reguła z §3 (F3).

### 6.2. Test fail-before / pass-after

Każde z 36 zadań ma test, który:

1. **zawodzi** na niezmodyfikowanej bazie danego modelu,
2. **przechodzi** na wariancie zadania,
3. porównuje **obserwowalny wynik** (kanoniczny CSV), nie obecność tekstu
   w pliku źródłowym.

Test sprawdzający `grep` po treści programu jest z definicji nieważny i jego
obecność unieważnia komórkę.

---

## 7. Metryki

Definicje operacyjne, reguły przypadków granicznych i identyfikatory reguł
zliczania: `coding_manual.md`. Ten rozdział zamraża **co** jest liczone;
podręcznik zamraża **jak**.

### 7.1. Metryki pierwotne (kolumny `results/constructs.csv`)

| ID | Metryka | Kierunek korzystny dla H8 |
|---|---|---|
| `C1` | jawne pętle sterujące przetwarzaniem próbek | mniej |
| `C2` | jawne mutowalne obiekty stanu | mniej |
| `C3` | jawne bufory lub kontenery okienne | mniej |
| `C4` | konstrukcje pacera, zegara, harmonogramu, synchronizacji | mniej |
| `C5` | miejsca ręcznego wyprowadzania historii, fazy lub ogona | mniej |
| `C6` | miejsca ręcznego współdzielenia obliczeń | mniej |
| `C7` | instrukcje domenowe opisujące właściwy algorytm | **neutralne** |
| `C3d` | **zadeklarowane** okna (specyfikatory szerokości) | **neutralne, towarzyszące** |
| `C4d` | **zadeklarowane** interwały/tempa źródeł | **neutralne, towarzyszące** |

### 7.1.1. Po co kolumny towarzyszące `C3d` i `C4d`

`C3` i `C4` liczą obowiązek **utrzymania** (bufor, który autor przesuwa; zegar,
który autor odczytuje). Przy takiej definicji RQL ma `C3 = C4 = 0`, bo `@(1,25)`
i `1/360` nic nie utrzymują — deklarują. Samo zero jest jednak podatne na
zarzut, że definicja została dobrana pod wynik.

`C3d` i `C4d` liczą **deklaracje** tych samych pojęć. Tabela mówi wtedy wprost:
RQL deklaruje cztery okna i utrzymuje zero; Python deklaruje zero i utrzymuje
cztery. To jest twierdzenie mocniejsze i sprawdzalne, a nie definicyjna sztuczka.

Kolumny towarzyszące **nie wchodzą do kryterium go/no-go** (§8), bo kryterium
zostało zamrożone w `research_plan.md` na trzech klasach obowiązku. Są
raportowane obowiązkowo. Rodzina, w której RQL ma `C3 = 0` przy `C3d = 0`
(czyli nie deklaruje żadnego okna), jest **niepoprawnie zbudowana** — nie
realizuje zadania okienkowego — i musi zostać naprawiona w K22b, przed metrykami.

`C7` jest **jawnie neutralne**: nie jest ani zaletą, ani wadą. Służy do
wykazania, że różnica w `C1`–`C6` nie bierze się z tego, że jeden program
robi mniej. Rodzina, w której `C7` różni się o więcej niż czynnik 2 między
modelami, jest sygnałem, że rdzenie nie są porównywalne — do odnotowania jako
zagrożenie, nie do cichej korekty.

### 7.2. Metryki modyfikacji (kolumny `results/modifications.csv`)

| ID | Metryka |
|---|---|
| `D1` | liczba zmienionych instrukcji (dodane + usunięte + zmodyfikowane) |
| `D2` | liczba zmienionych **jednostek programu** |

`D2` jest wielkością rozstrzygającą w kryterium go/no-go. Jednostki programu
zamrożone per model:

- **RQL:** jedna instrukcja `DECLARE` / `SELECT` / `RULE`; nazwany strumień
  jest tożsamy z instrukcją, która go definiuje.
- **Python:** funkcja, metoda, klasa **oraz** blok pętli rdzenia (pętla
  slotowa liczy się jako osobna jednostka, nawet gdy leży wewnątrz funkcji).
- **Flink:** klasa operatora, metoda funkcjonalna (`map`, `open`, `invoke`,
  `run`) **oraz** blok składania topologii.

Jednostka jest „zmieniona", jeżeli po zastosowaniu zadania różni się od bazy
w obrębie znaczników `CORE_BEGIN`/`CORE_END` w czymkolwiek poza białymi
znakami i komentarzami. Jednostka **dodana** i **usunięta** też liczy się jako
zmieniona (po jednej).

### 7.3. Metryki drugorzędne

`LOC` (bez komentarzy, importów, pustych linii, tylko wewnątrz rdzenia) oraz
złożoność cyklomatyczna. **Nigdy jako jedyna miara**, nigdy w kryterium
decyzyjnym. Raportowane, bo ich pominięcie wyglądałoby na ukrywanie.

### 7.4. Zakaz indeksu złożonego

**Nie powstaje żaden ważony indeks „prostoty".** Kolumny są raportowane
osobno. Dobór wag po obejrzeniu danych jest dokładnie tym błędem, który
przekreślił model kosztu slotu w K6c (`MAE_test` 258 %).

### 7.5. Wymagania wobec skryptu metryk

1. Skrypt ma fixture'y o **znanej odpowiedzi** (`metrics/fixtures/`),
   sprawdzane przez `metrics/test_metrics.sh`.
2. **Zero zliczonych programów jest błędem, nie wynikiem.** Skrypt kończy się
   kodem ≠ 0, gdy macierz jest pusta albo niekompletna.
3. Skrypt emituje **surową tabelę kwalifikacji każdego trafienia**
   (`results/hits.csv`: rodzina, model, wariant, metryka, `rule_id`, plik,
   linia, treść). Recenzent musi móc zakwestionować pojedyncze trafienie bez
   czytania skryptu.
4. Drugie, niezależne zakodowanie próbki: **≥ 20 % losowo wybranych plików
   rdzenia**, kodowane ręcznie wg `coding_manual.md`, przed obejrzeniem wyniku
   skryptu. Rozbieżność > 10 % w dowolnej metryce zatrzymuje kampanię i wymaga
   poprawienia podręcznika **przed** liczeniem całości. Wynik ręcznego kodowania
   trafia do `results/double_coding.csv` niezależnie od zgodności.

---

## 8. Kryterium GO/NO-GO — zamrożone

Obowiązuje zapis K22 z `research_plan.md` wraz z doprecyzowaniem z §8.1.

**H8 otrzymuje wsparcie wtedy i tylko wtedy, gdy co najmniej 2 z 3 rodzin
spełniają oba warunki:**

**Warunek 1 — eliminacja obowiązku proceduralnego.** W wersji RQL rodziny
zachodzi `C1 = 0` **i** `C3 = 0` **i** `C4 = 0` (pętla próbkowa, jawny stan
okienny, pacing/harmonogram), przy czym w **obu** modelach porównawczych każda
z tych trzech metryk jest `> 0`.

**Warunek 2 — lokalizacja zmiany.** RQL ma **ściśle mniejsze** `D2` niż
**oba** modele porównawcze w co najmniej **3 z 4** zadań M1–M4 tej rodziny.

### 8.1. Doprecyzowanie niejednoznaczności (wymagane przed utrwaleniem)

`next_session_K22.md` wskazuje otwartą niejednoznaczność: czy warunek M1–M4
jest liczony łącznie per rodzina, czy każde zadanie osobno. Przyjęte
rozstrzygnięcie — **każde zadanie raportowane osobno, warunek rodziny spełniony
przy przewadze RQL w ≥ 3 z 4 zadań wobec obu alternatyw** — jest wpisane do
`research_plan.md` §K22 **przed** utrwaleniem tej predeklaracji. Predeklaracja
nie może zostać scommitowana wcześniej niż ta zmiana planu.

Remis (`D2` równe) liczy się **przeciwko** RQL: warunek wymaga ściśle mniejszej
wartości. Uzasadnienie: teza H8 mówi „mniejszej liczbie jednostek", nie
„nie większej".

### 8.2. Co jest zakazane po zobaczeniu danych

1. zmiana definicji metryki, `rule_id` albo granicy `CORE_BEGIN`/`CORE_END`;
2. usunięcie niekorzystnej rodziny albo zadania z tabeli;
3. dodanie czwartego języka, na tle którego RQL wypada lepiej;
4. przeniesienie zadania do innej rodziny (przy pełnej macierzy niemożliwe
   z definicji — to jedna z jej zalet);
5. zmiana progu `≥ 3 z 4` albo `2 z 3`;
6. zmiana kodu silnika w celu poprawienia wyniku;
7. strojenie wag (żadnych wag nie ma — §7.4).

**Jedyną dopuszczalną reakcją na niespodziankę jest zatrzymanie kampanii i nowy
katalog** (`REQUIREMENTS.md` R3).

### 8.3. NO-GO jest prawidłowym wynikiem

Przy NO-GO artykuł zachowuje wyłącznie twierdzenie o ekspresywności działającego
przykładu, a deklaratywność pozostaje demonstracją, nie wynikiem ilościowym.
Tytuł wraca pod rozwagę (`Algebra-Backed Declarative Monitoring...` → tytuł
skupiony na normalizacji planu). Tabela pełna powstaje **tak samo** jak przy GO.

---

## 9. Tabela, która powstanie niezależnie od wyniku

Cztery pliki w `results/`, wypełnione dla **wszystkich** 3 rodzin × 3 modeli,
także tam, gdzie RQL przegrywa:

```text
results/semantic.csv       family,variant,model,tail,range_from,range_to,rows_compared,verdict,first_mismatch
results/constructs.csv     family,model,C1,C2,C3,C4,C5,C6,C7,C3d,C4d,loc,cyclomatic
results/modifications.csv  family,task,model,D1,D2,units_total,units_changed,test_fail_before,test_pass_after
results/hits.csv           family,model,variant,metric,rule_id,file,line,text
results/tails.csv          family,variant,model,stream,tail_slots,source
results/double_coding.csv  family,model,metric,script_value,manual_value,delta
results/verdict.md         rozstrzygnięcie per rodzina + agregat + threats to validity
```

`verdict.md` pokazuje **każdą rodzinę osobno**. Agregat nie może ukryć rodziny,
w której RQL jest bardziej rozbudowany.

---

## 10. Zagrożenia dla ważności — zapisane z góry

1. **Stronniczość autora.** Autor RQL projektuje też porównania i zadania.
   Częściowe ograniczenie: pełna macierz 3×4 (§6) usuwa swobodę przypisania
   zadań, a mechaniczne `rule_id` (§7.5) czynią każde trafienie sprawdzalnym.
   Nie usuwa to stronniczości w projekcie rdzeni porównawczych.
2. **Dwa modele to nie cała przestrzeń.** Python i Flink reprezentują pętlę
   slotową i stanowy dataflow. Nie reprezentują deklaratywnych DSL
   monitorowania (Lustre, SIGNAL, StreamIt, CQL) — to zakres K8, nie K22.
3. **Zliczanie zależy od podręcznika kodowania.** Stąd surowe kwalifikacje,
   fixture'y o znanej odpowiedzi i drugie kodowanie próbki.
4. **Mniej jawnych konstrukcji ≠ mniejsza całkowita złożoność.** Złożoność może
   być przeniesiona do kompilatora i runtime'u, a nie usunięta z systemu. To
   jest oczekiwany podział odpowiedzialności — i tak musi być nazwany w
   artykule, bo inaczej wynik zostanie przeczytany mocniej, niż na to zasługuje.
5. **External validity.** Wniosek ogranicza się do statycznych, regularnych,
   stałoschematowych monitorów o wymiernych interwałach.
6. **Brak badania ludzi.** Żadnego wniosku o zrozumiałości, produktywności ani
   błędogenności — nawet przy GO.
7. **Baseline'y powstały do pomiaru czasu.** Ich oczyszczenie jest jawne
   (§2.2, `CLEANUP.md`) i podlega przeglądowi; redakcyjne oczyszczenie na
   korzyść RQL jest naruszeniem protokołu.
8. **Arytmetyka wymusiła przepisanie porównań.** Rdzenie Python/Flink są nowe
   (§1.1), więc nie dziedziczą realizmu baseline'ów produkcyjnych. Ryzyko:
   nowy kod może być nieświadomie prostszy lub bardziej rozwlekły, niż
   napisałby go praktyk. Ograniczenie: struktura etapów odwzorowana z plików
   provenance, `CLEANUP.md` dokumentuje każdą różnicę.

---

## 11. Kolejność i bramki

| Etap | Zakres | Bramka wyjścia |
|---|---|---|
| **K22a** | predeklaracja, coding manual, układ, testy o znanej odpowiedzi | akceptacja człowieka; commit predeklaracji |
| **K22b** | rdzenie F1/F2/F3 × 3 modele, arytmetyka §4, format §5 | 3 wersje każdej rodziny przechodzą oracle albo są jawnie wyłączone z równoważności wartości |
| **K22c** | 36 wariantów M1–M4, każdy z czystej bazy | fail-before/pass-after przechodzi dla wszystkich 36 |
| **K22d** | metryki na pełnej, niepustej macierzy; werdykt | tabela kompletna; kryterium §8 zastosowane bez strojenia |
| **K22e** | `research_plan.md` §11.5/§13.4/§13.8/§14/§15; `main-debs.tex` → `main-debs-pl.tex`; oba PDF-y | brak undefined references/citations |

Worker RT (`pi400`) jest **niepotrzebny** dla całego K22. Nie uruchamiać
kampanii czasowej. K22 nie mierzy czasu.

---

## 11.1. Errata — poprawki faktyczne wykryte na starcie K22b

Predeklaracja opisywała aparaturę, zanim aparatura dotknęła żywego silnika.
Trzy zapisy okazały się nieprawdziwe. Poprawki dotyczą **faktów o narzędziu**,
nie definicji metryk, granicy rdzenia, przypisania zadań ani progów — te
pozostają nietknięte (§8.2). Żadna liczba wynikowa nie istniała w chwili
poprawiania. Wpisane jawnie, bo cicha edycja zamrożonego dokumentu byłaby
gorsza od błędu, który poprawia.

**E1. Odczyt ogona — zła komenda.** Było: „`tail` odczytywany z `xretractor -t`".
`-t` to `--realtime` (SCHED_FIFO), nie raport ogona. Ogon wypisuje presenter
w listingu planu: `xretractor <plan>.rql -c`, kolumna `tail=` przy nazwie
strumienia. Zasada się nie zmienia — ogon nadal pochodzi z silnika, nie
z rachunku. Zmieniła się nazwa polecenia, którym się go pobiera.

**E2. Relacja cykli do rekordów — ZALEŻNA OD PLANU.** Pierwotny zapis brzmiał
„`-m N` daje `N - 1 - tail` rekordów" i był prawdziwy tylko dla planów, których
strumień wyjściowy biegnie w globalnej siatce. Zmierzone:

| Rodzina | interwał wyjścia | relacja | pomiar |
|---|---|---|---|
| F1 | 1/1000 | `N − 1 − tail` | `N ∈ {5,10,20,40}`, różnica stała 4 przy `tail=3` |
| F3 | 1/15 | `⌊3N/4⌋ − tail` | `N ∈ {1006,2006,3006}` → 749/1499/2249 |

Uogólnienie „jeden slot zużywa krok zerowy" pozostaje prawdziwe, ale **nie
wystarcza**: gdy strumień wyjściowy jest wolniejszy od globalnej siatki, liczba
rekordów maleje proporcjonalnie. Wniosek dla aparatury: **nie wyliczać liczby
cykli wzorem**, tylko zamawiać z zapasem i pozwolić emiterowi zatrzymać się,
gdy rekordów zabraknie (`emit_rql.py` robi to kodem ≠ 0). To ten sam wniosek,
co w K6c: rachunek obok silnika rozjeżdża się z silnikiem.

**E3. Orientacja okna `@(1,N)` — nieudokumentowana pułapka.** Rekord `r`
obejmuje próbki `r .. r+N-1`, ale jest zapisany **od najnowszej**:
`win[0] = próbka r+N-1`, `win[N-1] = próbka r`. Ustalone odczytem artefaktu
`win` (nie z dokumentacji): dla `src[i] = (i·37 mod 1000) − 500` silnik zapisał
rekord 0 jako `(−426, −463, −500)`, czyli `(src[2], src[1], src[0])`.

Konsekwencja jest poważniejsza, niż wygląda: splot `Σ win[k]·coef[k]` ze
współczynnikami w kolejności pliku jest przy tej orientacji **korelacją
z odwróconymi współczynnikami**. Port budujący okno „od najstarszej" policzy
poprawnie wyglądającą, ale **inną funkcję**. Co gorsza, filtr symetryczny tego
nie ujawnia — a band-pass Hamminga z F2 jest symetryczny, więc błąd
przeszedłby przez F2 i wyszedł dopiero na niesymetrycznej różniczce
`[-1,-2,0,2,1]`. Reguła jest teraz w `refsem.window_at()` z testem
o znanej odpowiedzi na niesymetrycznych współczynnikach `[1,2,3]`.

**E4. F1 — współczynniki nie zgadzały się z deklaracją.** §3 mówi
„`f1_coef.txt`, 25 wartości, kopia `filterremez.txt`", a plik ma **26** wartości
(SHA-256 `0375887c…`); `dsp-simple-fir.rql` deklarował `INTEGER[25]`, więc
milcząco ucinał ostatni odczep. Specyfikacja była wewnętrznie sprzeczna, zanim
powstał jakikolwiek program.

Rozstrzygnięcie: F1 bierze plik **dosłownie — 26 odczepów, okno `@(1,26)`,
redukcja `.sumc` i `/26/1000`**. Usuwa to niejednoznaczność „które 25 z 26"
bez wymyślania danych; prowenienecja pozostaje nietknięta. Przepełnienie
wykluczone zakresem: `500 · Σ|c| = 500 · 42038 = 21 019 000 < 2^31−1`.

Uwaga metodologiczna do raportu: `filterremez.txt` jest **palindromiczny**,
a band-pass Hamminga z F2 też jest symetryczny. Symetryczny filtr **nie ujawnia
błędu orientacji okna** (E3), więc ani F1, ani pierwszy etap F2 nie są kontrolą
orientacji. Kontrolą jest test `refsem` na niesymetrycznych `[1,2,3]` oraz
asymetryczna różniczka `[-1,-2,0,2,1]` w F2. Gdyby nie E3, błąd przeszedłby
przez F1 i połowę F2.

**Walidacja §4 na żywym silniku.** Po uwzględnieniu E3 `refsem` odtworzył
wyjście silnika **co do bajtu na wszystkich 16 rekordach** przebiegu
kontrolnego (`sumc`, arytmetyka całkowita, ujemne wartości). Reguły z §4
przestały być odczytem z kodu, a stały się potwierdzonym pomiarem.

---

## 12. Podpis przeglądu

| Pole | Wartość |
|---|---|
| Autor projektu predeklaracji | asystent (sesja K22a, 2026-08-01) |
| Przegląd i akceptacja | *(do wypełnienia przez człowieka)* |
| Data utrwalenia | *(do wypełnienia przy commicie)* |
| Commit utrwalający | *(do wypełnienia przy commicie)* |

Po utrwaleniu: zmiana czegokolwiek w §2–§8 unieważnia kampanię.
