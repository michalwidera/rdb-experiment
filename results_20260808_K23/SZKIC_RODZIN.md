# Szkic trzech rodzin K23 — F9-R2, F9-R1, F9-X

**Status: szkic do przeglądu człowieka. To NIE jest predeklaracja.** Nic w tym
pliku nie jest zamrożone, żadnej liczby nie zmierzono. Predeklaracja to STOP-5
i wchodzi dopiero po pilocie compile-only (STOP-4), którego również **nie
wykonano** — w sesji, w której powstał ten dokument, nie uruchomiono ani jednego
planu.

Źródło normatywne: `paper-arXiv/debs/research_plan.md` §10/K23. Przy rozbieżności
z tym plikiem wygrywa §10.

---

## 1. Skąd biorą się liczby w tym dokumencie

Wszystkie przewidywania wyprowadzono **z lektury kodu** na SHA `1cfccf9`
(`retractordb`), nie z przebiegu:

| Co przeczytano | Gdzie |
|---|---|
| reguła R1 (dopasowane przesunięcia przed `#`) | `src/retractor/lib/compiler.cpp:1296` `factorMatchedHashTimeMoves()` |
| deduplikacja substratów | `src/retractor/lib/compiler.cpp:1472` `deduplicateSubstrats()` |
| współdzielenie SELECT-ów + kanonizacja R2 | `src/retractor/lib/compiler.cpp:1510` `shareEquivalentSelectComputations()` |
| kolejność i bramkowanie przejść | `src/retractor/lib/compiler.cpp:1690–1730` (`#if RDB_OPT_*`) |
| liczniki mechanizmu i metryki | `src/include/rdb/probe.hpp:110` (`logicalWriteCounters`), `src/rdb/lib/probe.cc:207` (`REWRITE_APPLIED`) |
| działające postacie RQL obu reguł | `test/IntegrationTest_serial/{optimizer_ablation,select_cse_commutative_add,issue202_hash_shift_e2e,r1_identity_nulls}/query.rql` |

Każda liczba w §4–§7 jest **przewidywaniem do potwierdzenia przez pilota P4**.
Rozbieżność pilota wobec tej tabeli jest wynikiem informacyjnym przed
predeklaracją, a nie porażką — po predeklaracji byłaby już STOP-6.

---

## 2. Cztery ustalenia z kodu, które zmieniają czytanie progu

### U-1. Sufit redukcji wobec ablacji to `1 − 1/F`, nie `1 − 1/Q`

`RDB_OPT_DEDUP_SUBSTRATES` zostaje **ON we wszystkich czterech profilach K23** —
§10 żąda ablacji minimalnych, a dedup nie jest badanym mechanizmem żadnej
rodziny. `deduplicateSubstrats()` scala substraty o identycznym programie,
schemacie i interwale, **niezależnie od tego, ilu monitorów dotyczą**. Zatem już
w ablacji wszystkie monitory zapisane **tą samą postacią składniową** dzielą
jedną instancję.

Liczba fizycznych instancji w ablacji to więc liczba **postaci** `F`, a nie
liczba monitorów `Q`. Przy `F = 2` sufit redukcji wynosi **50%**, nie 87,5%.

Zdanie z §10 („korekta akcentu”), że przy `Q=8` mechanizm daje 87,5% albo 0%,
a wartości pośrednich praktycznie nie ma, **opisuje porównanie z
`FLINK_NATURAL`** (który nie ma normalizacji algebraicznej ani deduplikacji, więc
zostaje przy `Q` instancjach). Dla ablacji wewnętrznej przewidywana wartość to
dokładnie 50% (F9-R2, F9-R1) i 58,3% (F9-X) — czyli **pas, o którym §10 mówi, że
praktycznie nie istnieje**. To nie jest powód do zmiany progu 40%; jest powodem,
żeby zapisać w predeklaracji, że wiążącym porównaniem jest ablacja z zapasem
10 pp, a nie Flink z zapasem 47 pp.

### U-2. Każda postać musi być użyta przez **co najmniej dwa** monitory

`shareEquivalentSelectComputations()` tworzy substrat `STREAM_SELECT_*` tylko dla
grupy o `queryIds.size() >= 2`. Grupa jednoelementowa nie dostaje nic — kosztowny
program pól zostaje w publicznym zapytaniu i **nie jest materializowany wcale**.

Konsekwencja jest przeciwintuicyjna i groźna dla metryki: gdyby w ablacji każda
postać miała po jednym monitorze, ablacja materializowałaby **zero** bajtów
badanego etapu, a `DEFAULT` — jedną instancję. Metryka pierwotna by się
**odwróciła** (redukcja ujemna) przy w pełni działającym mechanizmie.

Stąd reguła alokacji z §3.3: liczba postaci nigdy nie przekracza `Q/2`.

### U-3. R2 działa wyłącznie na publicznych SELECT-ach z jawnym programem pól

`queryFingerprint()` zwraca `nullopt` (czyli zapytanie wypada ze współdzielenia),
gdy zapytanie jest substratem, deklaracją albo dyrektywą; gdy jego odcisk nie
zawiera `ADD{` (czyli `FROM` nie jest pojedynczym węzłem `STREAM_ADD`); gdy
program pola używa `PUSH_ID1…PUSH_ID5`, `PUSH_IDX` lub `PUSH_TSCAN` (tak wypada
`SELECT *` — potwierdza to negatywna para `d1`/`d2` w
`select_cse_commutative_add`); oraz gdy program pola odwołuje się **do własnego
strumienia** (`sourceId == qry.id`).

To zawęża dopuszczalne postacie rodzin R2 i X: monitor musi mieć jawną listę pól
odwołującą się do **nazwanych** strumieni, identyczną we wszystkich monitorach co
do tokenów i kształtów pól. Nazwy pól wyniku nie są porównywane (tylko typ,
długość, liczność), więc mogą się różnić.

### U-4. Węzeł przeplotu dziedziczy szerokość substratu przesunięcia

W `factorMatchedHashTimeMoves()` nowy węzeł powstaje jako `query hashQuery =
coreInstance.at(leftShiftIndex);` — **kopia** lewego przesunięcia z podmienionym
programem, a warunek ponownego użycia sprawdza `schemasMatch(hash, leftShift)`.
Kanoniczna szerokość rekordu przeplotu jest więc równa szerokości źródła, a nie
jego sumie. Dzięki temu rachunek bajtów w F9-R1 upraszcza się do liczby zapisów i
wypada dokładnie 50% niezależnie od rate’ów — pod warunkiem, że **oba źródła mają
identyczny deskryptor** (patrz §5.1).

---

## 3. Ustalenia wspólne dla trzech rodzin

### 3.1. Granica badanego podplanu

Badany podplan = **wszystkie strumienie planu z `isSubstrat == true`**. Operacyjnie
jest to dokładnie ta granica, którą już rozróżnia instrument: `storage::markAsSubstrate()`
ustawiane z `qry.isSubstrat`, a `probe::onLogicalWrite(substrate, append, bytes)`
rozdziela `substrateBytes` od `publicBytes`.

Wyłączone z licznika (zgodnie z §10): ingress źródeł, bufory transportowe,
publiczne wyniki monitorów i ich metadane. Publiczne wyniki wchodzą wyłącznie do
**mianownika** (`publicAppends`).

Ta sama granica obowiązuje job Flinka: operatory między źródłem a per-monitorowym
sinkiem. Strona Flinka czeka na **D-2** i nie jest przedmiotem tego szkicu.

### 3.2. Metryka pierwotna i to, czego normalizacja nie zmienia

Metryka = `substrateBytes / publicAppends`. Mianownik rośnie z `Q` (każdy monitor
pisze swój wynik), więc **wartość bezwzględna metryki maleje z `Q` w każdym
profilu**. Iloraz między profilami jest od tego niezależny: mianownik jest
identyczny w `DEFAULT` i w ablacji, bo publiczne wyniki mają być identyczne
(bramka poprawności §10). Wszystkie redukcje w §4–§7 są ilorazami, więc dotyczą
zarówno metryki surowej, jak i znormalizowanej.

### 3.3. Alokacja monitorów na postacie przy zmiennym `Q`

Siatka `Q = {1, 2, 4, 8, 16, 32}` (§10). Reguła (do zamrożenia):

> `F(Q) = min(F_max, floor(Q/2))`, monitory rozdzielone równo między pierwsze
> `F(Q)` postaci w zamrożonej kolejności; przy `F(Q) <= 1` wszystkie monitory
> mają postać pierwszą.

`F_max` = 2 (F9-R2, F9-R1), 4 (F9-X). Reguła realizuje U-2 przy każdym `Q`.

Przewidywane redukcje wobec ablacji minimalnej:

| `Q` | 1 | 2 | 4 | 8 | 16 | 32 |
|---|---|---|---|---|---|---|
| F9-R2, F9-R1 (`F_max=2`) | 0% | 0% | 50% | **50%** | 50% | 50% |
| F9-X (`F_max=4`) | 0% | 0% | 33,3%¹ | **58,3%** | 58,3% | 58,3% |
| dla porównania: wobec `FLINK_NATURAL` | 0% | 50% | 75% | **87,5%** | 93,75% | 96,875% |

¹ przy `Q=4` rodzina X ma tylko dwie postacie (W1 i W4), więc 2×2 degeneruje się
do jednej przekątnej; wartość podana dla kompletności, komórką rozstrzygającą
pozostaje `Q=8`.

**To jest predykcja o konsekwencjach dla narracji:** wewnątrz RetractorDB
redukcja **nie rośnie** z `Q` powyżej `Q=4` — nasyca się na `1 − 1/F`. Rośnie
wyłącznie porównanie z Flinkiem. „Kontrola trendu” z §10 (`Q=1,2,4`) i „pomiar
skalowania” (`Q=16,32`) mają więc różne znaczenie po obu stronach porównania i
skrypt werdyktu nie może oczekiwać wzrostu po stronie ablacji.

### 3.4. Wspólny szkielet danych

Wszystkie źródła: jedno pole `INTEGER` (kanonicznie 8 B + 1 B mapy `NULL`/luk =
**9 B**), plik tekstowy generatora, stała liczba rekordów **zamrożona w
predeklaracji** (obserwacja z §5 Kroku 2 planu: przy zmiennej długości źródła
liczba zapisów substratu wahała się 19 wobec 15 — kampania nie może na to
pozwolić). Wyniki monitorów: jedno pole `INTEGER`, więc `w_out = w = 9 B`.
Jednostki w tabelach: `w` = szerokość kanoniczna rekordu, `n_X` = liczba zapisów
strumienia `X` w przebiegu.

---

## 4. F9-R2 — przemienny multi-sensor feature

### 4.1. Funkcja monitorująca

Dwuosiowy czujnik drgań maszyny: `A` = oś X, `B` = oś Y, oba 100 Hz. Monitor
liczy chwilową amplitudę wektora drgań `sqrt(x² + y²)`. Program pól jest
kosztowny (dwa mnożenia, dodawanie, pierwiastek) i **materializowany raz na slot**
w substracie `STREAM_SELECT_*`, gdy monitory się scalą.

### 4.2. Dwie postacie

```rql
STORAGE 'temp'
SUBSTRAT 'memory'

DECLARE v INTEGER STREAM A, 1/100 FILE 'axis_x.txt'
DECLARE v INTEGER STREAM B, 1/100 FILE 'axis_y.txt'

# --- postać P1: FROM A+B  (monitory m1..m4 przy Q=8)
SELECT Sqrt(A[0]*A[0]+B[0]*B[0]) STREAM m1 FROM A+B
SELECT Sqrt(A[0]*A[0]+B[0]*B[0]) STREAM m2 FROM A+B
SELECT Sqrt(A[0]*A[0]+B[0]*B[0]) STREAM m3 FROM A+B
SELECT Sqrt(A[0]*A[0]+B[0]*B[0]) STREAM m4 FROM A+B

# --- postać P2: FROM B+A  (monitory m5..m8)
SELECT Sqrt(A[0]*A[0]+B[0]*B[0]) STREAM m5 FROM B+A
SELECT Sqrt(A[0]*A[0]+B[0]*B[0]) STREAM m6 FROM B+A
SELECT Sqrt(A[0]*A[0]+B[0]*B[0]) STREAM m7 FROM B+A
SELECT Sqrt(A[0]*A[0]+B[0]*B[0]) STREAM m8 FROM B+A
```

Wzorzec potwierdzony działającym testem: `select_cse_commutative_add` pary
`c1`/`c2` i `e1`/`e2`.

### 4.3. Granica podplanu i schemat kanoniczny

Badany podplan to jeden węzeł: `STREAM_SELECT_m1` o programie `{PUSH A, PUSH B,
STREAM_ADD}` i schemacie jednego `INTEGER` (wynik `Sqrt`). Interwał = interwał
sumy strumieni `A+B`. Schemat kanoniczny substratu: `[INTEGER]` → 9 B.

### 4.4. Przewidywane liczby mechanizmu (`Q = 8`)

| Profil | `REWRITE_APPLIED r1` | `r2` | `STREAM_SELECT_*` | substraty | konsumenci substratu | bajty substratów |
|---|---|---|---|---|---|---|
| `DEFAULT` | 0 | **4** | **1** | 1 | 8 | `n·w` |
| `NO_R2_CANON` | 0 | 0 | **2** | 2 | 4 + 4 | `2·n·w` |
| `NO_R1_FACTOR` | 0 | 4 | 1 | 1 | 8 | `n·w` (jak `DEFAULT`) |
| `NO_R1_NO_R2` | 0 | 0 | 2 | 2 | 4 + 4 | `2·n·w` |

`n` = liczba slotów strumienia `A+B`. **Redukcja `DEFAULT` wobec ablacji
minimalnej (`NO_R2_CANON`) = 50%.**

`r2 = 4`, bo `onRewriteR2(qry.id)` liczy **zbiór węzłów**, w których nastąpiła
zamiana; zamiana zachodzi tam, gdzie odcisk prawego dziecka sortuje się przed
lewym, czyli w czterech monitorach `FROM B+A` (`SOURCE{A} < SOURCE{B}`).

Kolumna `NO_R1_FACTOR` jest w tej rodzinie **kontrolą pustą**: R1 nie ma czego
dopasować (brak `#` i `>`), więc profil musi dać liczby identyczne z `DEFAULT`.
Różnica byłaby dowodem, że plan nie izoluje mechanizmu — to jest przypadek
STOP-6, nie „słabszy wynik”.

### 4.5. Kontrole near-miss (nie wolno scalić)

| Kontrola | Postać | Dlaczego nie wolno |
|---|---|---|
| kolejność pól wyniku | `SELECT B[0],A[0] …` wobec `SELECT A[0],B[0] …` | kolejność projekcji ujawnia kolejność wejścia (`n1`/`n2` w teście) |
| `SELECT *` | `SELECT * STREAM d1 FROM A+B` wobec `… FROM B+A` | `SELECT *` ujawnia kolejność wejścia (`d1`/`d2`) |
| inne grupowanie trzech źródeł | `(A+B)+C` wobec `(C+B)+A` | brak reasocjacji; inny substrat pośredni = inny rytm uruchomienia (`x1`/`x3`) |
| `Q = 1` | jeden monitor | brak klasy równoważności → brak `STREAM_SELECT_*` |

---

## 5. F9-R1 — rational-rate delayed fusion

### 5.1. Funkcja monitorująca

Dwa czujniki tej samej maszyny o różnym takcie: `A` = drgania 100 Hz, `B` = prąd
50 Hz. Każdy tor ma własne opóźnienie akwizycji, oba równe **20 ms**; monitor
kompensuje je i przeplata oba sygnały w jeden strumień cech.

Stałe: `Δ_A = 1/100`, `Δ_B = 1/50`, `i = 2`, `k = 1`.
Warunek reguły: `i·Δ_A = 2/100 = 1/50` oraz `k·Δ_B = 1/50` — **spełniony**.
Przesunięcie łączne `i + k = 3` slotu strumienia przeplecionego
(`Δ_h = 1/150`, bo `3/150 = 1/50`). Ta arytmetyka jest tą samą, którą sprawdza
działający test `issue202_hash_shift_e2e` (tam `0,1`/`0,2`, `i=2`, `k=1`, `>3`).

**Wymóg:** `A` i `B` mają **identyczny deskryptor** (jedno `INTEGER`). Bez tego
`schemasMatch` w regule R1 może nie przejść, a rachunek z U-4 przestaje być
domknięty.

### 5.2. Dwie postacie

```rql
DECLARE v INTEGER STREAM A, 1/100 FILE 'vib.txt'
DECLARE v INTEGER STREAM B, 1/50  FILE 'cur.txt'

# --- postać P1: „skompensuj każdy tor, potem przeplataj”  (m1..m4)
SELECT m1[0]*m1[0] STREAM m1 FROM (A>2)#(B>1)
…
# --- postać P2: „przeplataj, potem skompensuj wspólne 20 ms”  (m5..m8)
SELECT m5[0]*m5[0] STREAM m5 FROM (A#B)>3
…
```

Program pól odwołuje się do własnego strumienia (`m1[0]`) — wzorzec z
`optimizer_ablation` (`dedup_shifted`). W tej rodzinie to jest **bezpieczne i
zamierzone**: współdzielenie realizuje R1 + dedup substratów, a nie przejście R2,
więc dyskwalifikacja z U-3 nic tu nie psuje. Ubocznie daje to czystą izolację
mechanizmu: odcisk R2 wymaga `ADD{`, którego w tej rodzinie nie ma, więc przejście
R2 jest w F9-R1 **bezczynne**.

### 5.3. Granica podplanu i schemat kanoniczny

Badany podplan: węzeł przeplotu `{PUSH A, PUSH B, STREAM_HASH}` (w `DEFAULT`) oraz
— w ablacji — substraty przesunięć `{PUSH A, TIMEMOVE 2}`, `{PUSH B, TIMEMOVE 1}`
i drugi węzeł przeplotu. Schemat kanoniczny każdego z nich: `[INTEGER]` → 9 B
(U-4). Przesunięcie łączne `>3` zostaje **w programie monitora**, nie w substracie,
więc nie wnosi zapisów.

### 5.4. Przewidywane liczby mechanizmu (`Q = 8`)

| Profil | `r1` | `r2` | substraty | jakie | bajty substratów |
|---|---|---|---|---|---|
| `DEFAULT` | **4** | 0 | **1** | `h = A#B` | `n_h·w` |
| `NO_R1_FACTOR` | 0 | 0 | **3** | `A>2`, `B>1`, `A#B` | `(n_A + n_B + n_h)·w = 2·n_h·w` |
| `NO_R2_CANON` | 4 | 0 | 1 | `h` | `n_h·w` (jak `DEFAULT`) |
| `NO_R1_NO_R2` | 0 | 0 | 3 | j.w. | `2·n_h·w` |

Ponieważ `n_h = n_A + n_B` (przeplot wystawia rekord każdego wejścia), redukcja
`DEFAULT` wobec `NO_R1_FACTOR` wynosi **dokładnie 50%**, niezależnie od rate’ów i
liczby rekordów — jest funkcją wyłącznie struktury planu.

`r1 = 4`: reguła odpala raz na monitor postaci P1. Pierwsze odpalenie tworzy węzeł
przeplotu o nazwie `composeStreamName(B, A, STREAM_HASH)`, trzy kolejne trafiają w
gałąź `hashNameExists` i **używają go ponownie** (warunki: substrat, program
`{PUSH A, PUSH B, HASH}`, zgodny interwał, zgodny schemat). Substraty przesunięć
tracą konsumentów i znikają. Monitory postaci P2 wnoszą własny substrat `A#B`
z ekstrakcji, który `deduplicateSubstrats()` scala z węzłem reguły — **to jest ten
moment, w którym dwie postacie stają się jedną instancją**, i to on musi być
widoczny w pilocie.

`NO_R2_CANON` jest tu kontrolą pustą — jak `NO_R1_FACTOR` w F9-R2.

### 5.5. Kontrole near-miss (nie wolno scalić)

| Kontrola | Postać | Dlaczego nie wolno |
|---|---|---|
| niedopasowane przesunięcie | `(A>2)#(B>2)` — `2/100 ≠ 2/50` | strażnik `leftDelta·leftOffset == rightDelta·rightOffset` |
| inne instancje źródeł | `(A2>2)#(B2>1)` przy `A2`, `B2` nad tym samym plikiem | inne strumienie = inny podplan; wzorzec z `issue202_hash_shift_e2e` |
| kolizja nazwy z konwencją kompilatora | publiczny strumień nazwany `STREAM_HASH_A_B` o zgodnym typowo, lecz przestawionym schemacie | przypadek `collide_user` z `optimizer_ablation` — reguła nie może użyć go ponownie |
| brak etapu materializowanego | ten sam program bez `#` i bez `>` | oczekiwane zero bajtów substratów, nie dowód niedziałania aparatury (§10) |
| `Q = 1` | jeden monitor | jedna postać → nic do scalenia |

---

## 6. F9-X — złożenie R1 → R2

### 6.1. Funkcja monitorująca

Dwie pary czujników: `(A, B)` na łożysku przednim, `(C, D)` na tylnym; w każdej
parze ten sam układ taktów i opóźnień co w F9-R1. Monitor sumuje (zestawia w
czasie) obie skompensowane pary i liczy nad nimi wspólną cechę.

### 6.2. Cztery postacie = dwie niezależne, dowolne decyzje autora

Postać R1 każdej pary (jak w §5) × kolejność dwóch par w sumie (jak w §4):

```rql
DECLARE v INTEGER STREAM A, 1/100 FILE 'front_vib.txt'
DECLARE v INTEGER STREAM B, 1/50  FILE 'front_cur.txt'
DECLARE v INTEGER STREAM C, 1/100 FILE 'rear_vib.txt'
DECLARE v INTEGER STREAM D, 1/50  FILE 'rear_cur.txt'

# W1  SELECT Sqrt(A[0]*C[0]+B[0]*D[0]) STREAM m1 FROM ((A>2)#(B>1)) + ((C>2)#(D>1))
# W2  … STREAM m3 FROM ((C>2)#(D>1)) + ((A>2)#(B>1))
# W3  … STREAM m5 FROM ((A#B)>3) + ((C#D)>3)
# W4  … STREAM m7 FROM ((C#D)>3) + ((A#B)>3)
```

Kolejność postaci przy redukcji `F(Q)`: **W1, W4, W2, W3** — pierwsza para różni
się w obu wymiarach naraz, więc przy `Q=4` rodzina nadal dotyka obu mechanizmów.

### 6.3. Przewidywane liczby mechanizmu — pełny układ 2×2 (`Q = 8`, po 2 monitory na wariant)

Jednostka bajtów: `n_h·w`, gdzie `n_h` = liczba zapisów jednego węzła przeplotu
(`n_h = n_A + n_B = n_C + n_D`), `w = w_out = 9 B`.

| Komórka | R1 | R2 | substraty złożenia | `STREAM_SELECT_*` | substraty ogółem | bajty |
|---|---|---|---|---|---|---|
| `DEFAULT` | ON | ON | 4 (`h_AB`, `sh_AB`, `h_CD`, `sh_CD`) | **1** | 5 | **5** |
| `NO_R2_CANON` | ON | OFF | 4 | 2 | 6 | 6 |
| `NO_R1_FACTOR` | OFF | ON | 8 | 2 | 10 | 10 |
| `NO_R1_NO_R2` (kontrola progu) | OFF | OFF | 8 | 4 | 12 | 12 |

`REWRITE_APPLIED`: `DEFAULT` → `r1 = 8` (dwa węzły przeplotu × cztery monitory
postaci W1/W2), `r2 = 4` (monitory o kolejności „para tylna pierwsza”);
`NO_R2_CANON` → `r1 = 8`, `r2 = 0`; `NO_R1_FACTOR` → `r1 = 0`, `r2 = 4`;
kontrola → `0/0`.

**Redukcja `DEFAULT` wobec komórki kontrolnej = 1 − 5/12 = 58,3%.**

Efekty brzegowe: R1 przy R2 wyłączonym `12 → 6` (×0,500), R2 przy R1 wyłączonym
`12 → 10` (×0,833), łącznie `12 → 5` = `12 × 0,500 × 0,833`. **Przewidywana
interakcja multiplikatywna wynosi więc 1,00 — złożenie jest dokładnie
multiplikatywne, nie nadaddytywne.** Współdziałanie przejść widać w liczbie
instancji, nie w interakcji: jedna instancja wspólnego podplanu powstaje
**wyłącznie** w komórce, w której oba przejścia są włączone (1 / 2 / 2 / 4).
Interakcja istotnie różna od 1,00 wymaga wyjaśnienia przed odczytem kosztów.

### 6.4. Najkruchsze miejsce całej kampanii — **P-1**

Postacie W1–W4 mają `FROM` złożone **inline**, więc dzieci węzła `+` są
substratami o nazwach generowanych przez kompilator. Autor nie może się do nich
odwołać, a U-3 zabrania obu obejść: `SELECT *` i odwołanie do własnego strumienia
dyskwalifikują zapytanie ze współdzielenia. Zostaje jedno wyjście: program pól
odwołuje się **do zadeklarowanych źródeł** (`A[0]`, `B[0]`, `C[0]`, `D[0]`), które
leżą wewnątrz złożonego `FROM`.

Że to jest w ogóle legalne, potwierdza działający wzorzec
`test/IntegrationTest_serial/Data/query.rql:7`:
`SELECT core0[1,1],a+1,core1.c STREAM str1 FROM core0#(core1>1)` — odwołanie do
źródła leżącego pod przesunięciem wewnątrz `FROM`. **Nie jest jednak
potwierdzone**, że rozwiązywanie odwołań przechodzi przez trzy piętra
(`>` → `#` → `+`) i że po przepisaniu R1 (`retargetSchemaReferences`) odwołania
obu postaci zostają identyczne — a bez tego odciski się rozjadą i R2 nie odpali.

**To jest dokładnie pytanie, na które odpowiada pilot P4, i dokładnie ten
przypadek, dla którego §10 mówi: „jeżeli złożenie F9-X nie działa w bieżącym
pipeline, K23 zatrzymuje się przed predeklaracją zamiast zastępować rodzinę”.**
Zastępczej postaci nie proponuję świadomie: nazwanie strumieni pośrednich przez
autora usuwa problem składniowy, ale zabija współdzielenie (odcisk niesubstratu to
`SOURCE{nazwa}`, a nazwy dwóch niezależnych autorów są różne), więc byłaby to
rodzina pozornie działająca.

### 6.5. Kontrole near-miss

Wszystkie z §4.5 i §5.5 plus: jedna para w postaci dopasowanej, druga w
niedopasowanej (`(C>2)#(D>2)`) — złożenie nie może scalić takiego monitora
z żadnym z W1–W4.

---

## 7. Zbiorcza tabela przewidywań do potwierdzenia przez pilota (`Q = 8`)

| Rodzina | ablacja minimalna | instancje `DEFAULT` → ablacja | przewidywana redukcja | zapas nad progiem 40% |
|---|---|---|---|---|
| F9-R2 | `NO_R2_CANON` | 1 → 2 | **50,0%** | 10 pp |
| F9-R1 | `NO_R1_FACTOR` | 1 → 3 | **50,0%** | 10 pp |
| F9-X | `NO_R1_NO_R2` | 5 → 12 | **58,3%** | 18,3 pp |
| każda, wobec `FLINK_NATURAL` | — | 1 → 8 | 87,5% | 47,5 pp |

Metryka bajtowa jest deterministyczna (zależy wyłącznie od deskryptorów i liczby
zapisów), więc te zapasy nie są zagrożone rozrzutem — są zagrożone **błędem w
projekcie rodziny**. Dwie rzeczy, które strącają je poniżej progu:
naruszenie U-2 (postać z jednym monitorem) i różne szerokości kanoniczne źródeł
(łamie rachunek U-4).

Bramką, o którą naprawdę toczy się gra, pozostaje — zgodnie z §10 i K6c — punkt
(ii): górna granica 95% CI ilorazu czasu `DEFAULT/minimal_ablation ≤ 1,05`.
Ten szkic jej nie dotyczy.

---

## 8. Czego ten szkic nie rozstrzyga

1. **Strona Flinka** — trzy joby `FLINK_NATURAL`/`FLINK_MANUAL` z tym samym
   serializerem kanonicznym. Blokada: **D-2**.
2. **Rate i zamrożona liczba rekordów** — P7/STOP-7, na osobnych danych, bez
   oglądania efektu.
3. **Dokładne `n_h`, `n_A`, `n_B`** — wynikają z zamrożonej liczby rekordów.
4. **Oracle, mutanty, skrypt werdyktu** — P5/P6.
5. **Czy `+` nad dwoma strumieniami 150 Hz ma interwał 150 Hz** — przyjęte w §6.3,
   do potwierdzenia pilotem.
6. **P-1 z §6.4** — istnienie rodziny F9-X.

## 9. Pytania do decyzji człowieka przed predeklaracją

1. **U-1**: czy przyjmujemy, że wiążącą wartością jest 50% wobec ablacji (zapas
   10 pp), a 87,5% dotyczy wyłącznie porównania z Flinkiem — i czy §10 „korekta
   akcentu” dostaje w predeklaracji odpowiedni przypis?
2. **§3.3**: czy reguła alokacji `F(Q) = min(F_max, floor(Q/2))` zostaje
   zamrożona wraz z przewidywaniem „0% przy `Q ≤ 2`, płasko od `Q = 4`”?
3. **§6.4 / P-1**: czy pilot F9-X wchodzi jako pierwszy z trzech rodzin, skoro
   jest jedyną bramką NO-GO całej kampanii?
4. **§5.1**: czy stałe `Δ_A = 1/100`, `Δ_B = 1/50`, `i = 2`, `k = 1` są do
   przyjęcia — z zastrzeżeniem z `SZKIC_D3.md` §3.2 o naturalności postaci P2?
