# Strona Flinka K23 — dwa warianty jobów dla trzech rodzin, plany i instancje operatorów

**Data: 2026-08-08 (czwarta sesja tego dnia). Status: produkt kroku „strona Flinka",
wykonanego po zamknięciu D-2. To NIE jest predeklaracja i NIE jest pomiarem kosztowym.**

Czego w tym dokumencie nie ma i być nie może:

* **żadnego pomiaru czasu.** Joby nie zostały uruchomione — `--plan-only` buduje graf
  transformacji i kończy się przed `env.execute()`. Aparatura nie ma zegara ściennego:
  źródła nie śpią, a czasem logicznym jest wyłącznie indeks slotu. §10 zakazuje
  porównywania czasu RetractorDB z czasem JVM, a przy rozdzielonych maszynach (D-2) jest
  to najłatwiejsza pomyłka kampanii, więc aparatura nie daje nawet możliwości jej popełnienia;
* **żadnej predeklaracji.** `freeze_check.sh` nadal kończy się kodem 2 („pole `@@CODE_SHA@@`
  niewypełnione"), co potwierdzono na wejściu tej sesji. STOP-5 obowiązuje.

Jednostki bajtowe poniżej są **arytmetyką predeklaracyjną** (liczba węzłów × rate ×
szerokość kanoniczna), dokładnie jak w `RAPORT_PILOTA.md` §1 — nie odczytem licznika.
Licznik `LOGICAL` po obu stronach czyta się w P6, na zamrożonej liczbie rekordów.

---

## 1. Środowisko hosta (krok A) — odczytane, nie przepisane

Pełny zapis maszynowy: `results/flink_environment.tsv` (42 pola, wraz z SHA-256 wszystkich
14 jarów z `lib/`). Pozycje istotne dla predeklaracji:

| Pozycja | Wartość |
|---|---|
| host | `B850MDESK`, Ubuntu 26.04 LTS, kernel `6.18.33.2-microsoft-standard-WSL2`, AMD Ryzen 9 9900X, 24 CPU |
| JDK **przypięty** | `/usr/lib/jvm/java-17-openjdk-amd64`, `openjdk 17.0.19 2026-04-21`, `javac 17.0.19` |
| SHA-256 `java` / `javac` | `a89ad12dc799a14a…` / `9a4eedebe503abd0…` |
| Flink | `/home/michal/opt/flink-2.3.0`, `Implementation-Version: 2.3.0` z manifestu jara |
| SHA-256 `flink-dist-2.3.0.jar` | `7c51cba8e3f2b35d62cc0f7212eb03b73e07c9541e0ce566579846af5ea9d493` (208 986 386 B) |
| oracle C++ | `oracle/canonical_oracle`, SHA-256 `60f82d9e5c6273ad…` |
| wektory serializera | `canonical_vectors.tsv`, SHA-256 `e4600d0a7149b20d…` |

**Ustalenie wymagające zapisu w predeklaracji, którego nie było w planie.** Domyślne `java`
z `PATH` na tym hoście to **25.0.3**, nie 17.0.19 (`/usr/lib/jvm/java-25-openjdk-amd64`).
Wersja z §9.1f planu (JDK 17.0.19) jest prawdziwa **tylko dla jawnie przypiętej ścieżki**.
Cała aparatura tej strony (`build_flink.sh`, `dump_plans.sh`, `sweep_q.sh`, `env_inventory.sh`)
przypina JDK ścieżką, nigdy przez `PATH` — tak samo, jak `results_20260801_K22v5/freeze_check.sh`.
`freeze_check.sh` K23 musi sprawdzać **ścieżkę i wersję**, nie samo `java -version`.

Wersja i SHA-256 jara zgodne z tym, co §9.1f planu zapisało z K22 — to jest zgodność
odczytu z zapisem, a nie przepisanie: wartość pochodzi z `sha256sum` w tej sesji.

---

## 2. Kanoniczny serializer (krok B) — bramka przeszła

Serializer po stronie Flinka: `java/Canon.java`, metoda `Canon.recordBytes(Descriptor)`.
Port `rdb::probe::canonicalRecordBytes` (`retractordb/src/rdb/lib/probe.cc:86`) — jedynego
miejsca definicji metryki — **przeczytanego z kodu**, wraz z regułą spłaszczonego widoku pól
z `Descriptor::rebuildFieldMappings` (`descriptor.cc:42`).

Bramka jest **podwójna** i to jest w niej istotne:

1. 18 wektorów o znanej odpowiedzi w `canonical_vectors.tsv` — 12 z nich to przypadki
   1:1 z `test/UnitTest/test_probe.cpp` (bramka tej metryki po stronie C++);
2. porównanie z `oracle/canonical_oracle` — programem, który **nie ma własnej
   implementacji**: linkuje `librdb.a` z drzewa budowy `build/K23-DEFAULT` i woła funkcję
   silnika. Ani jedna linia `retractordb` nie została w tym celu zmieniona.

Punkt 2 jest ważniejszy od punktu 1: wyklucza sytuację, w której oba przepisania
specyfikacji zgadzają się ze sobą i **oba** rozjeżdżają się z kodem. Wynik:

```
wektory=18 porownane_z_oracle=18 bledy=0
WYNIK: OK — serializer Flinka zgodny z rdb::probe::canonicalRecordBytes
```

Wychwycone przy porcie subtelności odwzorowania, obie utrwalone w wektorach:

* `NULLTYPE` **nie wnosi szerokości, ale wnosi wartość do mapy `NULL`/luk** — nie jest polem
  konfiguracyjnym, więc wchodzi do spłaszczonego widoku. Przepisanie „NULLTYPE = 0"
  bez tego rozróżnienia dałoby zaniżoną mapę dla deskryptorów z jawnym `NULL`;
* `STRING` liczy się jako **jedna** wartość mapy niezależnie od `rarray`, a jego szerokość
  jest zadeklarowana, nie kanonizowana — jedyny typ, dla którego `rlen` jest szerokością
  kanoniczną.

Deskryptor używany przez wszystkie trzy rodziny: jedno pole `INTEGER` → **9 B**
(8 B wartości + 1 B mapy). Ta liczba jest identyczna po obu stronach porównania.

---

## 3. Sześć jobów (krok C)

`java/F9R2Job.java`, `java/F9R1Job.java`, `java/F9XJob.java`, każdy z `--variant natural`
i `--variant manual`. Wspólne operatory w `java/K23Ops.java`.

Wspólne dla wszystkich sześciu: **równoległość 1**, te same źródła (jedno źródło na
zadeklarowany strumień, rozgałęzione do konsumentów), ten sam czas logiczny (indeks slotu),
te same schematy (jedno pole `INTEGER`, 9 B kanonicznie), ta sama funkcja. Postacie monitorów
odwzorowują postacie RQL z `SZKIC_RODZIN.md`, w tym **zamrożoną postać inline dla F9-X**
(D-3) i regułę alokacji `F(Q) = min(F_max, ⌊Q/2⌋)` (`K23Ops.formOf`).

`FLINK_NATURAL` nie zawiera **ani jednego** ręcznego wydzielenia: każdy monitor buduje
własny podplan od źródła. `FLINK_MANUAL` to ten sam job po ręcznym wydzieleniu wspólnego
podplanu — kontrola best case, **niewchodząca do progu** (§10).

### 3.1. Granica podplanu — decyzja tego kroku, do zamrożenia w predeklaracji

Job Flinka odwzorowuje plan RQL **węzeł w węzeł**:

* każdy węzeł substratu planu RetractorDB → jeden operator Flinka, którego rekordy
  wyjściowe idą do **licznika** metryki (`Canon.onSubstrateWrite`);
* własny szczytowy węzeł `FROM` monitora **razem z jego programem pól** → jeden końcowy
  operator, którego wynik jest rekordem **publicznym** (mianownik) i idzie na per-monitorowy
  sink.

Dzięki temu po obu stronach zgadzają się schematy, szerokości kanoniczne i liczba rekordów
każdego węzła — różni się wyłącznie **liczba instancji**, czyli dokładnie to, o co pyta H9.
Granica jest sprawdzalna maszynowo: konwencja nazw `SUB:` / `PUB:` / `SINK:` / `SRC:`,
a `PlanDump` odrzuca każdy operator poza konwencją i każdy węzeł `SUB:` bez wpisu w rejestrze
wag. Ingress źródeł, transport, checkpointy i sink są poza metryką (§10).

**Ta granulacja jest konserwatywna, czyli działa przeciw H9 — i to jest świadomy wybór.**
Idiomatyczny DataStream rozbiłby operator monitora na osobne kroki. Dla F9-R2 oznaczałoby to
`align` (rekord dwupolowy, kanonicznie **17 B**) i osobno `feature`; wtedy `FLINK_NATURAL`
materializowałby 8 × 17 B na slot wobec 9 B w `DEFAULT`, czyli redukcja **93,4%** zamiast
87,5%. Wybraliśmy wariant dający liczbę **niższą** o 5,9 pp. W F9-R1 i F9-X ten sam kierunek:
rozbicie szczytowego węzła monitora tylko dodałoby `FLINK_NATURAL` materializacji.

### 3.2. Czego w jobach świadomie nie ma

**Przeplot nie jest realizowany w źródle** — inaczej niż w aparaturze K22
(`results_20260801_K22/corpus/F3_multirate`, gdzie scalanie siedzi w `MergedSource`).
Tam było to uzasadnione, bo K22 porównywało wartości co do bajtu. Tutaj przeniesienie
przeplotu do źródła włożyłoby badany węzeł do **ingressu**, czyli wyjęło go z metryki —
to jest dokładnie ta pomyłka, przed którą ostrzega §10 i którą zmierzono w
`RAPORT_PILOTA.md` §6a. Przeplot jest operatorem między źródłem a sinkiem.

Reguły przeplotu (krok siatki, rozstrzyganie remisu na rzecz strumienia o wolniejszym
takcie) przeniesiono z K22, gdzie ustalono je **pomiarem** na artefakcie silnika.

Równoważność **wartości** obu stron nie jest przedmiotem tego kroku — sprawdza ją wspólny
oracle w P6 (§10, bramka poprawności: ≥2000 publicznych rekordów każdego nazwanego wyniku).
Tutaj wiążą schematy, granica podplanu i liczba rekordów. Zatrzaski w `AddFeature`
(rozwiązywanie `A[0]`…`D[0]` przez złożone `FROM`) są odczytem do potwierdzenia przez ten
oracle, nie ustaleniem.

---

## 4. Plany i instancje operatorów (krok D)

Wszystkie sześć planów: `plans/<rodzina>_<wariant>_Q8_{logical.json,logical.tsv,physical.tsv,subplan_nodes.tsv}`.
Zestawienie maszynowe: `results/flink_instances.tsv`.

| Rodzina | Wariant | Węzły podplanu | Jednostki `n_h·w` | Etapy publiczne | Sinki | Węzły grafu | Wierzchołki JobGraphu |
|---|---|---|---|---|---|---|---|
| F9-R2 | `FLINK_NATURAL` | **8** | **5,333** | 8 | 8 | 26 | 10 |
| F9-R2 | `FLINK_MANUAL` | **1** | **0,667** | 8 | 8 | 19 | 3 |
| F9-R1 | `FLINK_NATURAL` | **12** | **8,000** | 8 | 8 | 30 | 10 |
| F9-R1 | `FLINK_MANUAL` | **1** | **1,000** | 8 | 8 | 19 | 3 |
| F9-X | `FLINK_NATURAL` | **40** | **32,000** | 8 | 8 | 60 | 28 |
| F9-X | `FLINK_MANUAL` | **5** | **5,000** | 8 | 8 | 25 | 7 |

Rozbicie na węzły (`plans/*_subplan_nodes.tsv`) i skąd biorą się jednostki:

* **F9-R2 `NATURAL`** — 8 węzłów `SUB:m{i}:select_P{1,2}`, każdy 100 Hz (waga 2/3): 8 × 2/3.
* **F9-R1 `NATURAL`** — 4 monitory postaci P1 mają po dwa substraty przesunięć
  (`shift_A` 100 Hz = 2/3, `shift_B` 50 Hz = 1/3), 4 monitory postaci P2 mają po jednym
  substracie przeplotu (150 Hz = 1): 4 × (2/3 + 1/3) + 4 × 1 = 8. **Węzłów 12, jednostek 8** —
  to nie ta sama wielkość, dokładnie jak ostrzega `RAPORT_PILOTA.md` §5 pkt 2.
* **F9-X `NATURAL`** — po 2 monitory na każdą z czterech postaci; postacie W1/W2
  („skompensuj, potem przeplataj") mają 6 węzłów i 4 jednostki, postacie W3/W4
  („przeplataj, potem skompensuj") mają 4 węzły i 4 jednostki: 40 węzłów, 8 × 4 = 32 jednostki.
* **`MANUAL`** we wszystkich trzech rodzinach odtwarza **dokładnie** zestaw węzłów planu
  `DEFAULT`: 1 / 1 / 5 węzłów i 0,667 / 1,000 / 5,000 jednostek.

### 4.1. Czy Flink sam scalił badany podplan — NIE, i to jest odczyt z planu fizycznego

Optymalizacja Flinka **nie była blokowana**: łańcuchowanie operatorów zostało włączone,
`disableOperatorChaining()` nie występuje w kodzie. Plan fizyczny pokazuje, co Flink zrobił:

```
Source: SRC:A -> (SUB:m1:shift_A, SUB:m2:shift_A, SUB:m3:shift_A, SUB:m4:shift_A)   1   5
Source: SRC:B -> (SUB:m1:shift_B, SUB:m2:shift_B, SUB:m3:shift_B, SUB:m4:shift_B)   1   5
```

(`plans/F9-R1_natural_Q8_physical.tsv`)

Cztery operatory `shift_A` są **identyczne**: ta sama funkcja, ta sama stała, to samo wejście.
Flink **wciągnął je do jednego wierzchołka** (60 węzłów grafu → 28 wierzchołków w F9-X,
26 → 10 w F9-R2), ale **nie scalił ich w jeden operator** — zostały cztery osobne instancje
i cztery osobne strumienie rekordów. To jest łańcuchowanie **fizyczne**, redukujące koszt
transportu, a nie eliminacja wspólnego podplanu.

Wniosek dla kampanii: DataStream nie ma **żadnej** eliminacji wspólnych podwyrażeń —
nie tylko brakuje mu normalizacji algebraicznej (o czym mówi §10), ale nie scala nawet
podplanów **identycznych składniowo**. Ryzyko osi kampanii („naturalny Flink sam współdzieli
i obala H9 w tej rodzinie") w tej postaci **nie zmaterializowało się**.

Uczciwe zastrzeżenie: łańcuchowanie oznacza, że rekord przechodzi między operatorami
wywołaniem funkcji, bez serializacji. Metryka pierwotna liczy **logiczne** bajty
kanonicznego rekordu pośredniego, nie natywną serializację — natywny rozmiar stanu Flinka
jest w §10 metryką drugorzędną właśnie dlatego, że reprezentacje obu systemów są
nieporównywalne. Łańcuchowanie nie zmienia więc ani jednej liczby w tabeli wyżej, ale
**zmienia to, co można powiedzieć o koszcie** — i dlatego o koszcie nic tu nie mówimy.

### 4.2. Krzywa po siatce `Q` — dwie różne krzywe, jak żąda §10

`results/flink_q_curve.tsv`, `Q ∈ {1,2,4,8,16,32}` przy zamrożonej regule `F(Q)`:

| `Q` | 1 | 2 | 4 | 8 | 16 | 32 |
|---|---|---|---|---|---|---|
| F9-R2 `NATURAL` (jednostki) | 0,667 | 1,333 | 2,667 | **5,333** | 10,667 | 21,333 |
| F9-R1 `NATURAL` (jednostki) | 1,000 | 2,000 | 4,000 | **8,000** | 16,000 | 32,000 |
| F9-X `NATURAL` (jednostki) | 4,000 | 8,000 | 16,000 | **32,000** | 64,000 | 128,000 |
| `MANUAL` (wszystkie rodziny) | 0,667 / 1,000 / 5,000 | bez zmian | bez zmian | bez zmian | bez zmian | bez zmian |

Krzywa flinkowa jest **liniowa w `Q`**, więc redukcja wobec niej rośnie jak `1 − 1/Q`.
Krzywa wewnętrzna RetractorDB nasyca się na `1 − 1/F` powyżej `Q = 4` (`SZKIC_RODZIN.md` §3.3).
Skrypt werdyktu musi przewidywać obie — potwierdzone teraz po obu stronach porównania.

**Kontrola negatywna `Q = 1` po stronie Flinka** (brak klasy równoważności, więc nic nie ma
prawa się scalić):

* F9-R2: `NATURAL` = `MANUAL` = 0,667 → redukcja **0%** ✅;
* F9-R1: `NATURAL` = `MANUAL` = 1,000 → redukcja **0%** ✅, przy różnej liczbie węzłów
  (2 wobec 1). To jest **dokładnie** ta sama obserwacja, którą pilot zrobił po stronie
  RetractorDB (`RAPORT_PILOTA.md` §3): liczba instancji zmienia się, liczba bajtów nie.
  Powtórzenie jej w drugim systemie jest niezależnym potwierdzeniem wyboru bajtów jako
  metryki pierwotnej;
* F9-X: `NATURAL` 4,000 wobec `MANUAL` 5,000 — **`MANUAL` jest tu gorszy o 25%**. Powód
  jest ten sam, co w U-2: przy jednym monitorze ręczne wydzielenie materializuje wspólny
  węzeł cechy, który pojedynczy monitor policzyłby w swoim etapie publicznym, nic nie
  materializując. **Konsekwencja do predeklaracji:** `FLINK_MANUAL` nie jest „best case"
  przy `Q ≤ 2` i skrypt werdyktu nie może go tam tak czytać. Progu to nie dotyczy —
  `MANUAL` do progu nie wchodzi, a komórką rozstrzygającą jest `Q = 8`.

### 4.3. Praca — wielkość odporna na cięcie obliczenia na operatory

**Po co ta tabela istnieje.** Metryka bajtowa mierzy **materializację, nie pracę**, i ma jedną
konkretną słabość: autor Flinka, który scali cały monitor w **jeden** operator, nie
materializuje ani jednego rekordu pośredniego — licznik bajtów pokazałby wtedy zero, mimo
`Q`-krotnie zduplikowanego obliczenia. Granulacja z §3.1 broni się przed tym zamrożeniem,
ale zamrożenie jest **decyzją**, a recenzent może zaproponować własną. Liczba **wykonań
programu na slot** takiej słabości nie ma: jest niezmienna wobec dowolnego cięcia obliczenia
na operatory. §10 wymienia ją wśród metryk mechanizmu („wykonań kosztownego programu na
slot").

Liczniki są portem `probe::workCounters` (`evalCalls`, `evalTokens`, `hashPicks`, `addMerges`),
z semantyką przeniesioną z `expressionEvaluator::eval` — **jedno wywołanie na wykonanie
programu**, nie na węzeł planu. Długości programów są **odczytane ze zrzutów planu pilota**
(`pilot/out/DEFAULT_F9_*.plan`), nie oszacowane:

| Program | Tokeny | Gdzie w planie |
|---|---|---|
| `PUSH_ID, PUSH_ID, MULTIPLY, PUSH_ID, PUSH_ID, MULTIPLY, ADD, CALL(Sqrt)` | **8** | program `STREAM_SELECT_*` (F9-R2, F9-X) — **kosztowny** |
| `PUSH_ID, PUSH_ID, MULTIPLY` | **3** | program pola monitora F9-R1 (`m[0]*m[0]`) |
| `PUSH_ID(x[0])` | **1** | substraty `>`/`#` oraz monitor czytający gotowy substrat |

Wynik przy `Q = 8` (`results/flink_work.tsv`, jednostki `n_h` — na jednostkę slotów przeplotu):

| Rodzina | Wielkość | `FLINK_NATURAL` | `FLINK_MANUAL` | Redukcja |
|---|---|---|---|---|
| F9-R2 | wykonania kosztownego programu | 5,333 | 0,667 | **87,5%** |
| F9-R2 | scalenia `+` (`addMerges`) | 5,333 | 0,667 | **87,5%** |
| F9-R1 | wykonania programu pola (3 tokeny) | 8,000 | 8,000 | **0,0%** |
| F9-R1 | wybory przeplotu (`hashPicks`) | 8,000 | 1,000 | **87,5%** |
| F9-X | wykonania kosztownego programu | 8,000 | 1,000 | **87,5%** |
| F9-X | wybory przeplotu | 16,000 | 2,000 | **87,5%** |
| F9-X | scalenia `+` | 8,000 | 1,000 | **87,5%** |

Trzy rzeczy z tej tabeli wchodzą do predeklaracji.

**1. W F9-R1 program pola NIE jest wielkością rozdzielającą — daje 0,0%.** Każdy z ośmiu
monitorów liczy swój kwadrat w każdym profilu i w każdym wariancie; współdzielenie dotyczy
tam przeplotu, nie arytmetyki. Gdyby zdanie §10 „wykonań kosztownego programu na slot”
czytać literalnie jako program **pola**, F9-R1 wyglądałaby na rodzinę bez efektu. Dlatego
predeklaracja musi **nazwać per rodzinę**, która wielkość pracy jest rozdzielająca:
`hashPicks` dla F9-R1, wykonania programu 8-tokenowego dla F9-R2 i F9-X. Bez tego zapisu
skrypt werdyktu miałby jedną regułę na trzy różne mechanizmy.

**2. Parytet z planem RetractorDB, sprawdzony na zrzutach pilota.** `FLINK_MANUAL` musi mieć
tyle wykonań kosztownego programu, co `DEFAULT`, bo to ta sama liczba instancji:

| Rodzina | `DEFAULT` (ze zrzutu planu) | `FLINK_MANUAL` (z tego kroku) |
|---|---|---|
| F9-R2 | 1 × program 8-tokenowy przy 1/100 = **0,667** | **0,667** ✅ |
| F9-X | 1 × program 8-tokenowy przy 1/150 = **1,000** | **1,000** ✅ |

W F9-X komórka kontrolna `NO_R1_NO_R2` ma cztery węzły `STREAM_SELECT_m{1,3,5,7}`, czyli
**4,000** — zgodnie z liczbą postaci. Wielkości po stronie RetractorDB czyta się w P6
licznikiem `RDB_BENCH_WORK`, który **już istnieje**; tutaj są wyprowadzone ze zrzutu planu
i służą jako kontrola parytetu, nie jako wynik.

**3. Kontrola `Q = 1` na pracy jest czysta we wszystkich trzech rodzinach** —
`NATURAL` = `MANUAL` co do cyfry, także w F9-X (1,000 wobec 1,000). Metryka pracy **nie ma**
inwersji, którą metryka bajtowa ma w F9-X przy `Q = 1` (§4.2). To jest argument za tym, żeby
w raporcie i w artykule wielkość pracy stała **przy** liczbie bajtowej, a nie zamiast niej:
obie mierzą ten sam mechanizm, ale mają różne słabości i różne miejsca, w których się psują.

Krzywa pracy po całej siatce `Q`: `results/flink_work_q_curve.tsv` — liniowa w `Q` dla
`NATURAL`, płaska dla `MANUAL` (poza F9-R1, gdzie program pola rośnie w obu, a płaskie są
`hashPicks`).

**Zastrzeżenie.** Liczby wyżej są **arytmetyką planu** — `PlanDump` sumuje wagi rate’u
operatorów odczytanych ze zbudowanego grafu. Licznik runtime (`Canon.workReport()`) jest
wpięty w te same operatory i czyta te same wielkości, ale jego odczyt należy do P6, po
zamrożeniu liczby rekordów.

---

## 5. Zestawienie z tabelą `RAPORT_PILOTA.md` §2 (krok E)

Jednostki są te same po obu stronach: `n_h·w`, gdzie `n_h` = liczba slotów strumienia
przeplecionego (150 Hz), `w` = 9 B. Kolumny RetractorDB pochodzą z pilota (compile-only,
2026-08-08), kolumny Flinka z tego kroku.

| Rodzina | `DEFAULT` (RDB) | ablacja min. (RDB) | `FLINK_NATURAL` | `FLINK_MANUAL` |
|---|---|---|---|---|
| F9-R2 | **0,667** | 1,333 (`NO_R2_CANON`) | **5,333** | 0,667 |
| F9-R1 | **1,000** | 2,000 (`NO_R1_FACTOR`) | **8,000** | 1,000 |
| F9-X | **5,000** | 12,000 (`NO_R1_NO_R2`) | **32,000** | 5,000 |

Instancje wspólnego podplanu:

| Rodzina | `DEFAULT` | ablacja min. | `FLINK_NATURAL` | `FLINK_MANUAL` |
|---|---|---|---|---|
| F9-R2 | 1 | 2 | **8** | 1 |
| F9-R1 | 1 | 3 | **12** | 1 |
| F9-X | 5 | 14 | **40** | 5 |

Oba członki progu §10 pkt 2 (redukcja ≥ **40%** wobec ablacji minimalnej **oraz** wobec
`FLINK_NATURAL`) — stan przewidywany przed pomiarem:

| Rodzina | wobec ablacji (pilot) | zapas | wobec `FLINK_NATURAL` (ten krok) | zapas |
|---|---|---|---|---|
| F9-R2 | 50,0% | 10,0 pp | **87,5%** | 47,5 pp |
| F9-R1 | 50,0% | 10,0 pp | **87,5%** | 47,5 pp |
| F9-X | 58,3% | 18,3 pp | **84,4%** | 44,4 pp |

`DEFAULT` wobec `FLINK_MANUAL`: **0,0% w każdej z trzech rodzin — liczby są identyczne.**
To jest kształt, którego §10 oczekuje od wyniku wspierającego H9: „`DEFAULT` ≈ `FLINK_MANUAL`,
ale wygrywa z `FLINK_NATURAL`: przewagą jest automatyczne wykrycie, nie zdolność niedostępna
dla Flinka". Zastrzeżenie: identyczność jest **konstrukcyjna**, bo `FLINK_MANUAL` został
zbudowany jako odtworzenie zestawu węzłów planu `DEFAULT` — nie jest to niezależny pomiar,
tylko formalne stwierdzenie, że ręczne wydzielenie osiąga to samo, co kompilator robi sam.
W raporcie i w artykule wolno tak to i tylko tak nazwać.

### 5.1. Poprawka do wiersza zbiorczego szkicu i raportu pilota

`SZKIC_RODZIN.md` §7 i `RAPORT_PILOTA.md` §2 mają wiersz „każda rodzina, wobec
`FLINK_NATURAL`: 1 → 8 instancji, 87,5%". Po zbudowaniu jobów: wiersz jest poprawny dla
**F9-R2 i F9-R1**, ale **nie dla F9-X**, gdzie `DEFAULT` ma 5 jednostek wobec 32 —
czyli **84,4%**, nie 87,5%, a instancje to 5 → 40, nie 1 → 8. Powód jest ten sam, dla którego
`DEFAULT` w F9-X ma 5 jednostek, a nie 1: rodzina ma **złożenie**, więc wspólny podplan to
pięć węzłów, nie jeden. Wiersz zbiorczy był uproszczeniem policzonym dla rodzin jednowęzłowych.

Poprawka jest o **2,3 pp w dół** i nie zmienia niczego w werdykcie (zapas nad progiem 40%
wynosi 44,4 pp), ale wchodzi do predeklaracji w tej postaci, a nie jako 87,5% dla trzech
rodzin. Szkic i raport pilota zostają **nietknięte** — są zamkniętym zapisem tego, co było
wiadomo przed tym krokiem; poprawka mieszka tutaj i w predeklaracji.

---

## 6. Co ten krok domyka, a czego nie

Domknięte:

1. **D-2 wykonane** — strona Flinka istnieje na hoście, sześć jobów, kompilacja przypiętym
   JDK 17 wobec przypiętego Flinka 2.3.0.
2. **Serializer kanoniczny po stronie Flinka** wraz z bramką wobec kodu silnika (18/18).
3. **Plany logiczny i fizyczny** obu wariantów trzech rodzin oraz liczba instancji operatorów
   badanego podplanu, przy tej samej granicy co po stronie RetractorDB.
4. **Drugi członek progu** (redukcja wobec `FLINK_NATURAL`) ma przewidywane wartości dla
   wszystkich trzech rodzin — pilot miał tylko pierwszy.
5. **Metryka pracy po stronie Flinka** (§4.3) — port `probe::workCounters` z długościami
   programów odczytanymi ze zrzutów planu pilota. Domyka słabość metryki bajtowej: liczba
   wykonań programu na slot jest niezmienna wobec cięcia obliczenia na operatory, więc
   twierdzenie o zduplikowanej pracy **nie zależy** od granulacji z §3.1. Redukcja 87,5%
   w każdej z trzech rodzin — pod warunkiem sięgnięcia po właściwą wielkość w F9-R1.
6. **Ryzyko osi kampanii sprawdzone i niezmaterializowane**: naturalny Flink nie scala nawet
   podplanów identycznych składniowo.

Otwarte, wchodzi do P5/P6:

1. **Zamrożona liczba rekordów** wspólna dla obu maszyn — parametr `--slots` istnieje,
   wartość zamraża predeklaracja (§10: „Flink wykonuje tę samą liczbę rekordów"). Do tego
   czasu jednostki bajtowe są arytmetyką, nie odczytem licznika.
2. **Odczyt liczników `LOGICAL` i `WORK` po stronie Flinka** — `Canon.onSubstrateWrite`,
   `onPublicAppend`, `onEval`, `onHashPick`, `onAddMerge` są wpięte i raportują na końcu
   przebiegu, ale uruchomienie jobów należy do P6, po zamrożeniu. Po stronie RetractorDB
   odpowiednik (`RDB_BENCH_WORK`) już istnieje i nie wymaga dobudowy.
3. **Wspólny oracle wartości** (≥2000 rekordów każdego nazwanego wyniku po ogonie) i mutanty.
4. **`mechanism_table.py` nadal klasyfikuje publiczny strumień nazwany konwencją kompilatora
   jako substrat** (`RAPORT_PILOTA.md` §6 pkt 4). Dotyczy wyłącznie planów kontrolnych
   i żadnej liczby w §2 pilota ani w §4–§5 tego dokumentu — po stronie Flinka granica jest
   liczona przez konwencję nazw `SUB:`/`PUB:`, nie przez ten skrypt. **Do naprawy przed
   wejściem skryptu do aparatury werdyktu**; świadomie nietknięte w tej sesji, żeby nie
   zmieniać artefaktu, na którym stoi zamknięty raport pilota.

Do zamrożenia w predeklaracji z tego kroku, punkt po punkcie:

| Co | Gdzie |
|---|---|
| granulacja podplanu po stronie Flinka (odwzorowanie węzeł w węzeł) + argument konserwatywności | §3.1 |
| konwencja nazw `SUB:`/`PUB:`/`SINK:`/`SRC:` jako maszynowo sprawdzalna granica | §3.1, `java/PlanDump.java` |
| serializer kanoniczny Flinka + wektory + oracle C++ | §2, `canonical_vectors.tsv` |
| przypięcie JDK **ścieżką** (domyślne `java` to 25.0.3) | §1 |
| dwa środowiska, oba komplety w `freeze_check.sh` | §1 |
| poprawka wiersza „87,5% dla każdej rodziny" → 84,4% dla F9-X | §5.1 |
| `FLINK_MANUAL` nie jest best case przy `Q ≤ 2` | §4.2 |
| **która wielkość pracy jest rozdzielająca w danej rodzinie** — `hashPicks` dla F9-R1, program 8-tokenowy dla F9-R2 i F9-X | §4.3 |
| długości programów (8 / 3 / 1 tokenów) odczytane ze zrzutów planu pilota | §4.3 |

---

## 7. Odtworzenie

```bash
cd results_20260808_K23/flink
bash oracle/build_oracle.sh          # oracle C++ z librdb.a profilu K23-DEFAULT
bash env_inventory.sh                # krok A -> results/flink_environment.tsv
bash build_flink.sh                  # kompilacja szesciu jobow przypietym JDK 17
./oracle/canonical_oracle canonical_vectors.tsv > results/canonical_oracle_cpp.tsv
/usr/lib/jvm/java-17-openjdk-amd64/bin/java -cp build CanonTest \
    canonical_vectors.tsv results/canonical_oracle_cpp.tsv   # krok B, bramka 18/18
bash dump_plans.sh                   # krok D, Q=8 -> plans/ + results/flink_instances.tsv
bash sweep_q.sh                      # krzywe po siatce Q -> results/flink_{q_curve,work_q_curve}.tsv
```

Żadne z tych poleceń nie uruchamia joba i nie mierzy kosztu.
