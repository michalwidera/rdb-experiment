# K22 — podręcznik kodowania metryk

**Status: PROJEKT DO PRZEGLĄDU. Zamrażany razem z `PREDECLARATION.md`.**

Ten dokument definiuje, **co jest jednym wystąpieniem** każdej metryki
i przypisuje każdemu wystąpieniu identyfikator reguły `rule_id`. Skrypt
`metrics/measure.py` implementuje te reguły dosłownie i zapisuje `rule_id`
przy każdym trafieniu w `results/hits.csv`. Rozbieżność między podręcznikiem
a skryptem jest błędem skryptu.

Zasada nadrzędna: **recenzent musi móc zakwestionować pojedyncze trafienie
bez czytania kodu skryptu.** Dlatego każde trafienie ma plik, numer linii,
treść i `rule_id` odsyłający do konkretnego akapitu niżej.

---

## 0. Zakres liczenia

1. Liczy się **wyłącznie** tekst między `CORE_BEGIN` i `CORE_END`
   (`PREDECLARATION.md` §2). Wszystko poza znacznikami jest niewidoczne dla
   skryptu.
2. Puste linie i linie wyłącznie komentarzowe są pomijane we wszystkich
   metrykach, łącznie z `loc`.
3. Importy, deklaracja pakietu i adnotacje `@Override` są pomijane.
4. Jedno wystąpienie = **jeden węzeł składniowy** (Python), **jedna linia
   dopasowana do wzorca** (RQL, Java). Ta różnica jest świadoma i wynika
   z dostępności parsera; §5 opisuje jej konsekwencje.

### 0.1. Rozłączność metryk

`C1`–`C7` są **rozłączne**: jedno wystąpienie trafia do dokładnie jednej
metryki. Kolejność rozstrzygania przy kolizji jest zamrożona:

```text
C4  →  C5  →  C1  →  C3  →  C2  →  C6  →  C7
```

Czytane tak: jeżeli konstrukcja pasuje do `C4` (pacing), trafia do `C4`
i nie jest już rozważana dla pozostałych. `C7` jest workiem na resztę:
instrukcja rdzenia, która nie pasuje do niczego wcześniejszego, jest
instrukcją domenową.

Uzasadnienie kolejności: pacing i wyprowadzanie ogona są najbardziej
specyficzne (najwęższe wzorce), więc rozstrzygają pierwsze; `C2` jest szersze
niż `C3`, więc `C3` idzie przed nim; `C6` wymaga analizy przepływu, więc
trafia tam tylko to, czego wcześniejsze reguły nie wchłonęły.

`C3d` i `C4d` są **poza** tą kolejnością — liczą deklaracje, nie utrzymanie,
i mogą pokrywać się z `C7`. To jest zamierzone (`PREDECLARATION.md` §7.1.1).

---

## 1. Metryki — definicja operacyjna

### C1 — jawne pętle sterujące przetwarzaniem próbek

Jedno wystąpienie = jedna konstrukcja pętli w rdzeniu.

Liczone są **wszystkie** pętle rdzenia, ale `rule_id` rozróżnia ich rolę,
żeby recenzent widział podział:

| `rule_id` | Znaczenie |
|---|---|
| `*-C1-01` | pętla najbardziej zewnętrzna w rdzeniu — pętla slotowa/próbkowa |
| `*-C1-02` | pętla zagnieżdżona w innej liczonej pętli — np. iloczyn skalarny po odczepach |

Powód liczenia obu: pętla po odczepach też jest jawnym sterowaniem, którego
autor RQL nie pisze. Powód rozróżnienia: implementacja wektorowa (`np.dot`)
usuwa `C1-02`, ale nie `C1-01`, i tabela ma to pokazywać.

**Nie jest pętlą** rekurencja ani wywołanie funkcji bibliotecznej, która
iteruje wewnętrznie (`np.dot`, `stream().sum()`). To jest właśnie różnica,
którą metryka ma mierzyć.

### C2 — jawne mutowalne obiekty stanu

Jedno wystąpienie = jedna **nazwa**, nie jedno przypisanie do niej.

Warunki łączne:

1. nazwa jest przypisywana w rdzeniu **poza** pętlą slotową (inicjalizacja),
   albo jest polem instancji operatora;
2. nazwa jest celem przypisania, przypisania złożonego (`+=`) albo mutacji
   przez indeks **wewnątrz** pętli slotowej / metody wywoływanej per rekord;
3. nazwa **nie** jest kontenerem okiennym (wtedy `C3`).

Nazwa spełniająca (1) i (2) liczy się **raz**, niezależnie od liczby mutacji.
Zmienna czysto lokalna dla jednego slotu (przypisana i odczytana wyłącznie
w tej samej iteracji, bez przeniesienia wartości do następnej) **nie jest
stanem** — jest wynikiem pośrednim i trafia do `C7`.

`rule_id`: `*-C2-01`.

### C3 — jawne bufory lub kontenery okienne

Jedno wystąpienie = jedna nazwa spełniająca warunki `C2`, której wartość
początkowa powstaje przez konstrukcję kontenera z zamrożonej listy:

```text
Python: np.zeros(  np.empty(  np.array(  [ ]*  list(  deque(  collections.deque(
Java:   new double[  new int[  new long[  new ArrayDeque  new ArrayList  new LinkedList
```

albo która jest mutowana przez operację przesunięcia okna:

```text
Python: <nazwa>[:-1] = <nazwa>[1:]      <nazwa>.append(   <nazwa>.popleft(
Java:   System.arraycopy(<nazwa>, 1, <nazwa>, 0,          <nazwa>.addLast(   <nazwa>.pollFirst(
```

`rule_id`: `*-C3-01` (konstrukcja kontenera), `*-C3-02` (operacja przesunięcia).
Nazwa trafiająca w obie reguły liczy się **raz**; `hits.csv` zawiera oba
trafienia, `constructs.csv` liczy nazwy unikalne.

### C4 — pacer, zegar, harmonogram, synchronizacja

Jedno wystąpienie = jedno wywołanie albo konstrukcja z zamrożonej listy:

| `rule_id` | Wzorzec |
|---|---|
| `*-C4-01` | odczyt zegara: `time.monotonic_ns`, `time.monotonic`, `time.time`, `time.perf_counter_ns`, `time.perf_counter`, `System.nanoTime`, `System.currentTimeMillis`, `Instant.now` |
| `*-C4-02` | uśpienie/oczekiwanie: `time.sleep`, `Thread.sleep`, `LockSupport.park`, `await`, `wait(` |
| `*-C4-03` | arytmetyka terminu slotu: przypisanie, którego prawa strona zawiera jednocześnie nazwę zawierającą `deadline`/`period`/`termin` i operator `+` lub `*` |
| `*-C4-04` | synchronizacja: `threading.`, `Lock(`, `Queue(`, `synchronized`, `AtomicLong`, `ConcurrentLinkedQueue`, `CountDownLatch` |
| `*-C4-05` | harmonogram frameworka wymagający jawnej konfiguracji czasu: `setBufferTimeout`, `TimeCharacteristic`, `assignTimestampsAndWatermarks`, `WatermarkStrategy`, `TumblingProcessingTimeWindows`, `SlidingProcessingTimeWindows` |

**Deklaratywny interwał źródła nie jest `C4`.** `1/360` w `DECLARE` deklaruje
tempo, nie realizuje go — trafia do `C4d` i do `C7`. To jest rozstrzygnięcie
sporne i dlatego jawne: `C4d` pokazuje, że RQL nie „nie ma tempa", tylko
je deklaruje.

### C5 — ręczne wyprowadzanie historii, fazy lub ogona

| `rule_id` | Wzorzec |
|---|---|
| `*-C5-01` | jawny warunek rozgrzewki: instrukcja warunkowa, której warunek porównuje licznik slotów ze stałą lub z długością okna (`if n < WARMUP`, `if (n < win.length)`) |
| `*-C5-02` | jawne wypełnienie okna wartością początkową na potrzeby ogona: konstrukcja kontenera z argumentem wypełnienia (`np.zeros`, `Arrays.fill`) **użyta w celu ogona** — rozpoznawana po tym, że nazwa kontenera jest odczytywana przed pierwszym pełnym zapełnieniem |
| `*-C5-03` | jawne wyliczenie fazy: wyrażenie z operatorem modulo, którego wynik steruje wyborem gałęzi, źródła albo indeksu (`n % 2 == 0`, `idx = n % nRec`) |
| `*-C5-04` | jawne opóźnienie grupowe wpisane liczbą: literał całkowity przypisany do nazwy zawierającej `delay`, `tail`, `latency`, `warmup`, `ogon` |

`C5-02` jest jedyną regułą wymagającą oceny („w celu ogona"). Dlatego
`measure.py` **nie rozstrzyga jej automatycznie**: emituje trafienie
kandydujące z `rule_id = *-C5-02?` i wymaga rozstrzygnięcia ręcznego,
zapisanego w `metrics/manual_C5_02.csv`. Nierozstrzygnięty kandydat zatrzymuje
skrypt kodem ≠ 0. Ta metryka nie może być liczona po cichu.

### C6 — ręczne współdzielenie obliczeń

Jedno wystąpienie = jedna nazwa, która wewnątrz pętli slotowej (albo metody
wywoływanej per rekord) jest **przypisana dokładnie raz** i **odczytana co
najmniej dwa razy**, i która nie została już policzona jako `C2` ani `C3`.

`rule_id`: `*-C6-01`.

To jest **nadprzybliżenie** zamierzonego pojęcia „wartość policzona raz
i użyta przez dwa różne nazwane wyjścia". Mechanicznie da się sprawdzić
krotność odczytu, ale nie to, czy odczyt trafia do nazwanego wyjścia.
Konsekwencja: zmienna pomocnicza użyta dwa razy w jednym wyrażeniu wyjściowym
zostanie policzona jako `C6`, choć współdzieleniem nie jest.

**Kierunek tego błędu sprzyja H8 i musi być tak nazwany.** RQL ma `C6 = 0`
z braku zmiennych pośrednich, więc zawyżenie `C6` w Pythonie i Flinku powiększa
różnicę na korzyść tezy. Dlatego:

1. `C6` **nie wchodzi do kryterium go/no-go** (`PREDECLARATION.md` §8 — warunek 1
   używa `C1`, `C3`, `C4`, warunek 2 używa `D2`). Nadprzybliżenie nie może więc
   przechylić werdyktu;
2. wszystkie trafienia `C6` podlegają **obowiązkowemu przeglądowi ręcznemu**
   przy drugim kodowaniu (§4), a nie tylko wyrywkowemu;
3. każde trafienie jest w `hits.csv` z numerem linii i podlega zakwestionowaniu.

Jeżeli model realizuje współdzielenie deklaratywnie (autor nie pisze ani
zmiennej pośredniej, ani duplikatu), `C6 = 0` i jest to wynik, nie brak
danych. Jeżeli autor **duplikuje** obliczenie zamiast je współdzielić, to nie
jest `C6` — to jest podniesione `C7`, i tak ma zostać zaraportowane.

### C7 — instrukcje domenowe

Jedno wystąpienie = jedna instrukcja rdzenia, która nie trafiła do `C1`–`C6`.

| `rule_id` | Model | Jednostka |
|---|---|---|
| `RQL-C7-01` | RQL | jedna instrukcja `DECLARE` / `SELECT` / `RULE` |
| `PY-C7-01` | Python | jedna instrukcja `ast.stmt` na dowolnym poziomie rdzenia |
| `JAVA-C7-01` | Java | jedna linia zakończona `;` albo otwierająca blok metody/klasy operatora |

`C7` jest **neutralne** (`PREDECLARATION.md` §7.1). Nie jest ani zaletą, ani
wadą. Jego zadanie to wykazać, że różnica w `C1`–`C6` nie bierze się stąd, że
jeden program po prostu robi mniej.

### C3d — zadeklarowane okna

| `rule_id` | Wzorzec |
|---|---|
| `RQL-C3d-01` | wystąpienie `@(` w instrukcji `SELECT` |
| `PY-C3d-01` | argument nazwany `window=` albo wywołanie funkcji okna z frozen list (pusta dla obecnego korpusu) |
| `JAVA-C3d-01` | `.window(`, `.countWindow(`, `.timeWindow(` |

### C4d — zadeklarowane interwały

| `rule_id` | Wzorzec |
|---|---|
| `RQL-C4d-01` | literał wymierny `N/M` albo całkowity w pozycji interwału instrukcji `DECLARE` |
| `PY-C4d-01` | parametr nazwany `rate_hz=`, `interval=`, `period=` w wywołaniu konstruktora źródła |
| `JAVA-C4d-01` | argument `rateHz`/`intervalNs` przekazany do konstruktora źródła |

---

## 2. Jednostki programu (`D2`)

`D2` jest wielkością rozstrzygającą w kryterium go/no-go, więc jej definicja
jest najostrzejsza.

| Model | Jednostka programu | `rule_id` |
|---|---|---|
| RQL | jedna instrukcja `DECLARE` / `SELECT` / `RULE`; nazwany strumień jest tożsamy z instrukcją, która go definiuje | `RQL-U-01` |
| Python | funkcja, metoda, klasa | `PY-U-01` |
| Python | blok pętli rdzenia (pętla slotowa jest osobną jednostką, także wewnątrz funkcji) | `PY-U-02` |
| Flink | klasa operatora | `JAVA-U-01` |
| Flink | metoda funkcjonalna: `map`, `flatMap`, `open`, `close`, `invoke`, `run`, `processElement` | `JAVA-U-02` |
| Flink | blok składania topologii (ciąg wywołań `.map(...).addSink(...)` na `DataStream`) | `JAVA-U-03` |

### 2.1. Kiedy jednostka jest „zmieniona"

Jednostka jest zmieniona, jeżeli jej tekst w obrębie `CORE_BEGIN`/`CORE_END`
różni się od bazy w czymkolwiek **poza białymi znakami i komentarzami**.

- jednostka **dodana** → liczy się jako 1 zmieniona;
- jednostka **usunięta** → liczy się jako 1 zmieniona;
- jednostka **przeniesiona bez zmiany treści** → **nie** liczy się jako
  zmieniona (inaczej zwykłe przestawienie kolejności zawyżałoby `D2`);
- zmiana samej **nazwy** jednostki → liczy się jako zmieniona.

### 2.2. `D1` — zmienione instrukcje

`D1` = liczba instrukcji dodanych + usuniętych + zmodyfikowanych, liczona na
znormalizowanym diffie (białe znaki i komentarze usunięte przed diffem).
Instrukcja zmodyfikowana liczy się **raz**, nie jako para dodanie+usunięcie.

---

## 3. Metryki drugorzędne

- `loc` — linie rdzenia po usunięciu pustych, komentarzowych, importów
  i deklaracji pakietu.
- `cyclomatic` — 1 + liczba punktów rozgałęzienia w rdzeniu. Punkty
  rozgałęzienia: `if`, `elif`, `else if`, `for`, `while`, `case`, `catch`,
  `and`, `or`, `&&`, `||`, operator warunkowy `?:` / wyrażenie warunkowe.
  Dla RQL: `cyclomatic = 1` z definicji (brak rozgałęzień w gramatyce), co
  samo w sobie nie jest argumentem i tak ma być opisane.

Obie **nigdy** nie wchodzą do kryterium decyzyjnego.

---

## 4. Drugie kodowanie

Losowo wybrane **≥ 20 %** plików rdzenia jest kodowane **ręcznie** wg tego
podręcznika, **przed** obejrzeniem wyniku skryptu. Wybór losowy: `sort` po
SHA-256 ścieżki, pierwsze `ceil(0,2·N)` plików — deterministyczny i niepodatny
na dobór.

Wynik trafia do `results/double_coding.csv` **niezależnie od zgodności**.
Rozbieżność > 10 % w dowolnej metryce zatrzymuje kampanię: poprawia się
**podręcznik**, nie liczby, i liczy całość od nowa.

---

## 5. Znane ograniczenia tego podręcznika

Zapisane z góry, żeby nie zostały odkryte przez recenzenta jako ukryte.

1. **Python jest parsowany składniowo (`ast`), Java i RQL wzorcami tekstowymi.**
   Java nie ma parsera w bibliotece standardowej, a dołożenie zależności
   zewnętrznej do skryptu metryk zwiększyłoby powierzchnię błędu bardziej niż
   zmniejszyłoby niepewność. Konsekwencja: liczby dla Javy są wrażliwe na
   formatowanie. Ograniczenie: pliki Javy w korpusie są formatowane jednym
   stylem, a `metrics/fixtures/flink/` przypina zachowanie na przykładach
   o znanej odpowiedzi.
2. **`C6` wykrywa współdzielenie przez nazwę pośrednią.** Współdzielenie
   zrealizowane inaczej (np. przez pole obiektu przekazywanego między
   operatorami) nie zostanie policzone automatycznie. Takie przypadki mają
   być zgłoszone ręcznie w `metrics/manual_C6.csv`.
3. **`C5-02` wymaga oceny** i celowo nie jest automatyzowane (§1, `C5`).
4. **Wzorce Javy są listami zamkniętymi.** Konstrukcja spoza listy nie zostanie
   policzona. Lista jest zamrożona razem z predeklaracją; jej rozszerzenie po
   obejrzeniu danych jest zakazane (`PREDECLARATION.md` §8.2 pkt 1).
5. **Metryki liczą tekst, nie zachowanie.** Program o mniejszej liczbie
   konstrukcji może przenosić złożoność do kompilatora, a nie usuwać ją
   z systemu (`PREDECLARATION.md` §10 pkt 4).
