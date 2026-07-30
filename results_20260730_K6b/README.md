# K6b — kampania ablacyjna z powtórzeniami: koszt i korzyść czasowa

**Predeklaracja v2.** Ten plik powstaje i jest commitowany **przed**
wygenerowaniem jakichkolwiek danych tej kampanii. Wszystkie parametry, próg
istotności, reguła wyboru rate'u pomiarowego i reguła decyzyjna są zamrożone.
Po pierwszym przebiegu nie wolno ich zmienić ani doprecyzować. Jedyną
dopuszczalną reakcją na niespodziankę jest **zatrzymanie kampanii i nowy
katalog** (`REQUIREMENTS.md` R3).

Katalog `results_20260730_K6` jest **zamknięty**. Jest zapisem nieudanej
kalibracji v1 i nie wolno w nim niczego edytować ani wznawiać.

## Dlaczego v1 upadła — błąd modelu, nie błąd silnika

Predeklaracja v1 zamroziła drabinę `s ∈ {36, 24, 12, 6}` i regułę „największe
`s`, przy którym **każda** komórka kalibracyjna spełnia
`p99(compute_ns) ≤ 0,5 · slot(φ)`". Kalibracja K6.0 wykonała 96 przebiegów
i **odrzuciła całą drabinę**.

Powodem był **milcząco przyjęty model kosztu**: drabina zakładała, że koszt
pracy na slot maleje, gdy slot się wydłuża — czyli że praca na slot skaluje się
z rate'em. Dla rodziny **W4** to założenie jest fałszywe. Okno `@(1,30)`
(`generate.py`, funkcja `w4`) liczy **30 próbek w każdym slocie**, niezależnie od
tego, jak długi jest slot. `W4_Q32` ma więc `p99(compute_ns) ≈ 35 ms` przy
`s = 36` i przy `s = 6` tak samo:

| `s` | `f_φ` | budżet `0,5 · slot` | `W4_Q32` `p99` (OFF) | `W4_Q32` `p99` (STRUCT) |
|---:|---:|---:|---:|---:|
| 36 | 540 Hz | 0,93 ms | 32,66 ms | 35,62 ms |
| 24 | 360 Hz | 1,39 ms | 34,92 ms | 35,50 ms |
| 12 | 180 Hz | 2,78 ms | 34,77 ms | 35,59 ms |
| 6 | 90 Hz | 5,56 ms | 35,30 ms | 35,48 ms |

Diagnostyka (`results_20260730_K6/results/evidence/diag_w4*`) wykluczyła defekt
silnika: koszt jest liniowy w `Q` (`W4_Q01` 0,98 ms, `W4_Q08` 7,89 ms,
`W4_Q32` 32,29 ms mediany) i stały co-slot (`p99/mediana` 1,06–1,20). Ogona
outlierów nie ma. Instrument działa; błędne było założenie w predeklaracji.

Pozostałe komórki kalibracyjne mieściły się w budżecie przy `s = 6`
(`W2_Q32` 2,6–3,3 ms, `W3_d3` 1,08 ms, `W9_Q32` 3,6–4,0 ms). Jedna komórka —
`W4_Q32` — zablokowała całą kampanię, bo reguła v1 wybierała **jeden rate
globalny** dla wszystkich rodzin.

## Co zmienia v2

Cztery zmiany, zatwierdzone przez człowieka 2026-07-30 (zapis w `JOURNAL.md`,
wpisy `16:20` i `16:35`), **przed** wygenerowaniem jakichkolwiek danych:

1. **Drabina rozszerzona o dwa szczeble w dół:** `s ∈ {36, 24, 12, 6, 3, 1}`,
   `f_φ = 15 · s` Hz. Dwa najniższe szczeble istnieją po to, żeby rodziny
   z kosztem stałym co-slot (W4) mogły w ogóle wejść do pomiaru.
2. **Rate wybierany per rodzina, nie globalnie.** Jedna komórka nie blokuje już
   rodzin, z którymi nie ma nic wspólnego.
3. **Komórka niemieszcząca się nawet przy `s = 1` wypada z Tier B** i jest
   raportowana jako **wykluczona**, wraz z liczbami i przyczyną. Wykluczenie
   jest wynikiem, nie zamiataniem: „ta komórka wymaga `f_φ ≤ X` Hz" jest
   zdaniem publikowalnym.
4. **Nowy warunek unieważniający:** rate nieidentyczny dla wszystkich profili
   w obrębie jednej komórki unieważnia kampanię.

Zmienia się także **budżet przebiegu**: `slots = clamp(round(8 s / slot(φ)),
400, 6000)`. Podłoga spada z 1500 na 400, bo przy 15 Hz 1500 slotów to 100 s na
przebieg; 400 slotów × 15 powtórzeń daje 6000 próbek na komórkę.

**Nic więcej się nie zmienia.** Pięć profili, dziewięć rodzin, `Q ∈ {1, 2, 4, 8,
16, 32}`, 15 powtórzeń, losowa kolejność, metryka główna = mediana
`compute_ns`, próg istotności 10%, klasy A/B/C, pozostałe warunki
unieważniające, `W8` na stałych 360 Hz — wszystko jak w v1.

## Dlaczego per rodzina, a nie per komórka

Rate wybierany osobno dla każdej **komórki** dałby najwięcej mieszczących się
komórek, ale **skaziłby porównanie skalowania w `Q` wewnątrz rodziny**:
`W2_Q08` przy 180 Hz i `W2_Q32` przy 90 Hz nie są porównywalne, bo różni je
także rate. Rodzina jest najmniejszą jednostką, wewnątrz której `Q` jest
jedyną zmienną — i dlatego to rodzina, a nie komórka, dostaje wspólny rate.

To samo w drugą stronę: rate globalny jest zbyt gruby, bo wiąże ze sobą
rodziny, między którymi żadne porównanie nie zachodzi. Werdykt kampanii
porównuje profile **w obrębie komórki**, nigdy komórkę z komórką innej rodziny.

## Silnik jest zamrożony i nie jest modyfikowany

Kampania biegnie na `retractordb` @ `master`
**`bb3a5216b952432818b23a26365001fe4f7627f5`** i **nie wprowadza żadnej zmiany
w kodzie silnika**. Cała potrzebna instrumentacja istnieje po K5i:

| Metryka §9.2 | Instrument | Aktywacja |
|---|---|---|
| rozmiar planu, tokeny FROM/pól, dedup | `PLAN bench` | `RDB_BENCH_PLAN` |
| atrybucja reguł | `REWRITE_APPLIED r1= r2=` | `RDB_BENCH_PLAN` |
| czas kompilacji | `COMPILE_NS <ns> sonda=<ns>` | `RDB_BENCH_PLAN` |
| rozmiar buforów | `PLAN capacity: strumieni= suma= maks=` | `RDB_BENCH_PLAN` |
| materializacje trwałe i pamięciowe | `MATERIALIZED trwale: … pamieciowe: …` | `RDB_BENCH_MATERIALIZE` |
| `compute_ns`, `wake_lag_ns`, `e2e_ns` | sonda E1, CSV | `RDB_BENCH_CSV` |
| peak RSS, CPU time, checksum | poza silnikiem: `/proc/PID/status VmHWM`, `/proc/PID/stat`, `sha256sum` | harness |

Pięć profili K6 jest już zbudowanych i zweryfikowanych na workerze
(`--build-info` bajtowo, `cap_ipc_lock,cap_sys_nice=ep` na każdej binarce).
K6b ich **nie przebudowuje** — to te same binarki z tego samego commita.

**Dlaczego zamrożenie jest częścią metody.** Każda zmiana `master` unieważnia
przypięcie wyników i wymusza kolejne badanie higieniczne — precedens
`Fix (#214)` (K5h) i `bb3a521` (K5i). Branch w repozytorium kodu powstaje
w tej kampanii **wyłącznie reaktywnie**: jeżeli K6b wykryje defekt silnika,
kampania zostaje zatrzymana przed werdyktem, defekt naprawiony na `issue_NNN`,
wykonane badanie higieniczne i kampania powtórzona w nowym katalogu.

## Czego ta kampania świadomie nie mierzy

1. **Ablacji infrastruktury z §9.2** (persistence/metadata/IPC włączone
   i wyłączone, integer vs rational scheduling). Przełączniki nie istnieją,
   a ich dodanie jest zmianą architektoniczną w rdzeniu.
2. **Pełnego application E2E.** Sonda kończy się na emisji do kolejki klienta
   (`REQUIREMENTS.md` R10). Metryka nazywa się `queue-emission latency`.
3. **Progu 480/510 Hz z powtórzeniami ani soak testu** — to K11.
4. **Skalowania liczby klientów z `Q`.** Jeden klient `xqry` na przebieg.
5. **Kryterium every-slot jako sufitu publikacyjnego** — sufit z §7.4 pozostaje
   wynikiem kampanii wydajnościowej, nie tej.

## Profile

Pięć profili z K4, bez zmian (`profiles.tsv`), wszystkie Release
z `RDB_BENCH_PROBE=ON`. Katalogi budowy mają przedrostek `K6-`.

| Profil | dedup | share | commutative (R2) | factor (R1) |
|---|---|---|---|---|
| `OFF` | OFF | OFF | OFF | OFF |
| `STRUCT` | ON | ON | OFF | OFF |
| `STRUCT+R1` | ON | ON | OFF | ON |
| `STRUCT+R2` | ON | ON | ON | OFF |
| `ALGSTRUCT` | ON | ON | ON | ON |

Porównaniem podstawowym jest `ALGSTRUCT` względem `STRUCT`: obie mają pełną
redukcję strukturalną, więc różnica jest wkładem algebry, a nie CSE. `OFF` jest
dolnym punktem odniesienia, `STRUCT+R1` i `STRUCT+R2` służą atrybucji (G14).

## Rodziny workloadów

Bez zmian względem v1 — osiem rodzin K5 w niezmienionej konstrukcji oraz W9.

| | Rodzina | Konstrukcja | Rola w K6b |
|---|---|---|---|
| W1 | pojedyncza instancja reguły | `(A>2)#(B>1)` | tylko Tier A |
| W2 | `Q` zapytań ze wspólnym `phi(A,B)` | `Q` × `(A>2)#(B>1)` | rdzeń: `r1 = Q`, `net = −1` |
| W3 | głębokość wspólnego podplanu | zagnieżdżone `((phi>2)#(S>1))`, `d = 1,2,3` | jedyna rodzina, w której `net` rośnie (−1, −2, −3) |
| W4 | kosztowny operator za wspólnym podplanem | `phi → projekcja → @(1,30) → .avg` | koszt **stały co-slot**; patrz niżej |
| W5 | **kontrola negatywna** | `Q` × `A_j#B_j`, bez przesunięć | `net = 0`; **musi wyjść neutralnie** |
| W6 | near-miss | `(A>1)#(B>1)`, `i·Δ_A ≠ k·Δ_B` | tylko Tier A |
| W7 | materializacja blokuje rewrite | przesunięcia jako strumienie publiczne | `net = 0`; **musi wyjść neutralnie** |
| W8 | **umotywowana zewnętrznie** | potok Pan-Tompkins `rec205` + `Q` monitorów | zamyka G7; rate 360 Hz ze źródła |
| W9 | **R2-shaped** | `Q` publicznych `SELECT` z tym samym kosztownym programem pól, naprzemiennie `FROM a+b` i `FROM b+a` | jedyna rodzina, w której odpala R2 |

`Q ∈ {1, 2, 4, 8, 16, 32}` (W3: `d ∈ {1,2,3}` przy `Q = 8`).

### Co już wiadomo o W4 i co z tym robimy

Kalibracja v1 ustaliła, że w `W4_Q32` profil `STRUCT` **nie jest szybszy** od
`OFF` (35,59 vs 34,77 ms `p99`). Współdzielenie podplanu `(A>2)#(B>1)` nie daje
korzyści czasowej, bo koszt jest zdominowany przez **32 niewspółdzielone okna**
`@(1,30)`. Rodzina W4 w obecnej postaci mierzy własne okna, nie dedup.

To jest zapisane **przed** pomiarami K6b i ma być zaraportowane niezależnie od
werdyktu. W4 zostaje w macierzy bez zmiany konstrukcji: zmiana rodziny po
zobaczeniu danych byłaby dokładnie tym, czego zakazuje R3.

## Rate pomiarowy — reguła zamrożona, wartości wyznaczane

### Drabina

| `s` | `f_A` | `f_B` | `f_φ` | slot `φ` | budżet `0,5 · slot` | `slots` |
|---:|---:|---:|---:|---:|---:|---:|
| 36 | 360 Hz | 180 Hz | 540 Hz | 1,85 ms | 0,93 ms | 4320 |
| 24 | 240 Hz | 120 Hz | 360 Hz | 2,78 ms | 1,39 ms | 2880 |
| 12 | 120 Hz | 60 Hz | 180 Hz | 5,56 ms | 2,78 ms | 1440 |
| 6 | 60 Hz | 30 Hz | 90 Hz | 11,1 ms | 5,56 ms | 720 |
| 3 | 30 Hz | 15 Hz | 45 Hz | 22,2 ms | 11,1 ms | 400 |
| 1 | 10 Hz | 5 Hz | 15 Hz | 66,7 ms | 33,3 ms | 400 |

`slots = clamp(round(8 s / slot(φ)), 400, 6000)`, ta sama liczba dla wszystkich
przypadków i profili w danej rodzinie. Pierwsze **5 %** slotów jest odrzucane
w analizie jako transjent startowy (komentarz `executorsm.cpp`: 20–47 ms
w `wake_lag`). Odrzucenie jest zapisane w kodzie analizy, nie wybierane po
zobaczeniu danych.

### Reguła wyboru (zamrożona)

Dla każdej rodziny obecnej w Tier B:

> `rate(rodzina)` = **największe** `s` z drabiny, przy którym **każda
> niewykluczona komórka** tej rodziny spełnia `p99(compute_ns) ≤ 0,5 · slot(φ)`
> **w najgorszym zmierzonym profilu**.

> Komórka, która nie spełnia tego warunku nawet przy `s = 1`, jest
> **wykluczona z Tier B** i nie ogranicza rate'u swojej rodziny. Wykluczenie
> jest raportowane w `results/rate.json` i `results/calibration.md` wraz
> z `p99`, budżetem i wymaganym `f_φ`.

> Jeżeli wykluczone zostaną **wszystkie** komórki rodziny, rodzina wypada
> z Tier B w całości i jest tak raportowana.

Powód warunku 50 %: porównanie profili musi zachodzić w reżimie
**nienasyconym**; w saturacji `compute_ns` przestaje mierzyć koszt planu,
a zaczyna mierzyć backlog. Saturacja jest osobnym, jawnym punktem kampanii
(K6b.5), nie tłem pozostałych pomiarów.

### Komórki i profile kalibracyjne (zamrożone)

Kalibracja obejmuje **wszystkie komórki Tier B** rodzin podlegających drabinie
(W2, W3, W4, W5, W7, W9 — 11 komórek), po `{OFF, STRUCT}` i **3 powtórzenia**,
przy budżecie `slots` z tabeli wyżej. Bierzemy **maksimum** `p99` z powtórzeń
i profili.

Rozszerzenie względem v1 (tam: 4 komórki) jest wymuszone przez samą regułę:
rate per rodzina nie da się wyznaczyć z komórek jednej rodziny. Szacowany czas:
**40–50 min**, bo rodziny wypadają z drabiny w miarę, jak się rozstrzygają.

Przebieg kalibracyjny ma włączone **te same trzy instrumenty** co przebieg
Tier B (`RDB_BENCH_CSV`, `RDB_BENCH_PLAN`, `RDB_BENCH_MATERIALIZE`) — v1
kalibrowała bez dwóch z nich, mierząc tym samym inny przebieg niż ten, który
potem mierzyła kampania. Liczniki planu i materializacji z tych przebiegów
trafiają do `rate.json` i są wejściem modelu kosztu slotu; bez nich komórka
wykluczona z Tier B nie miałaby żadnego wektora cech.

`{OFF, STRUCT}` to profile **bez przepisywania algebraicznego**, czyli
z największą pracą na slot; profile z R1/R2 mogą pracę wyłącznie usunąć.
Kalibracja mierzy więc górne oszacowanie. **Kontrola tego założenia** jest
raportowana po kampanii: `analyze.py` podaje liczbę komórek Tier B, w których
jakikolwiek profil przekroczył `0,5 · slot` w danych właściwych. Jest to
kontrola **raportowana**, nie unieważniająca — reguła wyboru rate'u jest
zamrożona i nie podlega korekcie po zobaczeniu danych.

### W8 nie podlega drabinie

Rate `W8` jest zamrożony na **360 Hz**, bo wynika z deklaracji źródła `rec205`
(`1/360`) i jest kotwicą porównywalności z §7 artykułu. `slots(W8) = 2880`
(8 s przy 360 Hz). Jeżeli najcięższa komórka W8 narusza regułę 50 %, jej cele
**nie są zwalniane** — komórka zostaje w macierzy i jest raportowana jako
nasycona, wraz z konsekwencją dla interpretacji.

**Wyniki kalibracji nie są wynikami kampanii.** Służą wyłącznie ustaleniu
rate'ów, są zapisywane w `results/calibration.md` oraz `results/rate.json`
i tam zostają.

**Kwantyzacja deadline'ów do pełnych milisekund** (G11) dotyczy wszystkich
profili identycznie, więc nie jest zakłóceniem porównania. Wpływa na
`wake_lag_ns` i `e2e_ns`, nie na `compute_ns`, mierzony bezpośrednio wokół
`processRows()`. To jest powód, dla którego metryką **główną** jest
`compute_ns`.

## Macierz

### Tier A — metryki kompilacji

46 przypadków (osiem rodzin K5 = 40, W9 = 6) × 5 profili × **15 powtórzeń**,
kolejność losowana w obrębie powtórzenia (ziarno `20260730-tierA`, zapisane
w kodzie). Zbierane: `COMPILE_NS`, `PLAN bench`, `PLAN capacity`,
`REWRITE_APPLIED`.

Tier A jest **niezależny od rate'u** — mierzy kompilację, nie pętlę slotową —
więc jest generowany przy **jednym, zamrożonym `s = 6`** dla wszystkich rodzin.
Wybór `s = 6` jest arbitralny i nieistotny: `check_counters` z v1 wykazał
230 kompilacjami, że przeskalowanie nie zmienia struktury planu. Uruchamiany
na workerze z governorem `performance` i przypięciem do izolowanego rdzenia 3 —
czas kompilacji jest metryką czasową.

### Tier B — metryki runtime

14 przypadków × 4 profile × **15 powtórzeń** = 840 przebiegów, **minus komórki
wykluczone przez kalibrację**. Liczba faktycznie wykonanych przebiegów jest
raportowana i porównywana z planem.

| Przypadki | Profile | Rate |
|---|---|---|
| `W2_Q01`, `W2_Q08`, `W2_Q32` | `OFF`, `STRUCT`, `STRUCT+R1`, `ALGSTRUCT` | `rate(W2)` |
| `W3_d1`, `W3_d3` | `OFF`, `STRUCT`, `STRUCT+R1`, `ALGSTRUCT` | `rate(W3)` |
| `W4_Q08`, `W4_Q32` | `OFF`, `STRUCT`, `STRUCT+R1`, `ALGSTRUCT` | `rate(W4)` |
| `W5_Q32` | `OFF`, `STRUCT`, `STRUCT+R1`, `ALGSTRUCT` | `rate(W5)` |
| `W7_Q32` | `OFF`, `STRUCT`, `STRUCT+R1`, `ALGSTRUCT` | `rate(W7)` |
| `W8_Q01`, `W8_Q08`, `W8_Q32` | `OFF`, `STRUCT`, `STRUCT+R1`, `ALGSTRUCT` | 360 Hz (źródło) |
| `W9_Q08`, `W9_Q32` | `OFF`, `STRUCT`, `STRUCT+R2`, `ALGSTRUCT` | `rate(W9)` |

Jedno **badanie** (`study_NN` w rozumieniu R8) = jedna rodzina; wewnątrz
badania kolejność wszystkich trójek (przypadek, profil, powtórzenie) jest
losowana, żeby dryf termiczny i częstotliwościowy nie sprzęgł się z profilem.
Reboot workera następuje **między** badaniami. Siedem badań: W2, W3, W4, W5,
W7, W8, W9.

### K6b.5 — punkt saturacji

`W8_Q32` × `{STRUCT, ALGSTRUCT}` × `{360, 480, 540}` Hz × 5 powtórzeń.
Metryka: udział slotów z `compute_ns > slot(φ)`. Pytanie: czy `ALGSTRUCT`
utrzymuje rate, którego `STRUCT` nie utrzymuje. Bez zmian względem v1 — W8 nie
podlega drabinie, więc zmiana reguły rate'u tego kroku nie dotyka.

## Metryki

**Metryka główna:** mediana `compute_ns` na slot w przebiegu. Komórka =
(przypadek, profil) = 15 median po jednej z każdego przebiegu.

**Metryki drugorzędne**, raportowane z tym samym traktowaniem statystycznym:

| Metryka | Źródło | Uwaga |
|---|---|---|
| `COMPILE_NS` | Tier A | koszt normalizacji; wynik ujemny dla `ALGSTRUCT` byłby ceną, nie korzyścią |
| `PLAN capacity` suma i maksimum | Tier A | rozmiar buforów |
| peak RSS | `/proc/PID/status VmHWM`, próbkowane w trakcie | |
| CPU time procesu | `/proc/PID/stat` `utime+stime` | całość procesu, wraz z kompilacją |
| `Σ compute_ns` | sonda E1 | koszt CPU samego rdzenia obliczeń |
| materializacje trwałe i pamięciowe | `MATERIALIZED` | liczba i bajty, rozdzielnie |
| queue-emission p50 / p99 / p99,9 / max | `e2e_ns` | **nie** application E2E (R10) |
| `wake_lag_ns` p99,9 | sonda E1 | kontrola jakości środowiska RT, nie wynik |
| checksum artefaktów | `sha256sum` | kontrola poprawności |

## Reguła decyzyjna — zamrożona, bez zmian względem v1

Dla komórki `c` niech `r(c) = mediana₁₅(ALGSTRUCT) / mediana₁₅(STRUCT)`
metryki głównej, a `CI(c)` — przedział bootstrapowy 95 % ilorazu
(10 000 replikacji, ziarno `20260730`, percentyle 2,5 i 97,5).

**Próg istotności praktycznej: 10 %.**

| Klasa | Warunek |
|---|---|
| **(A) poprawa** | `r(c) ≤ 0,90` **i** górna granica `CI(c) < 1,00` |
| **(B) neutralna** | `CI(c)` zawiera `1,00` **albo** `\|1 − r(c)\| < 0,10` |
| **(C) regresja** | `r(c) ≥ 1,10` **i** dolna granica `CI(c) > 1,00` |

**Werdykt kampanii** podaje liczbę komórek w każdej klasie — **wszystkich**,
nie tylko najlepszych — liczbę komórek **wykluczonych** przez kalibrację, oraz
jawnie stwierdza:

1. czy istnieje choć jedna komórka klasy (A);
2. czy istnieje komórka klasy (A) w rodzinie umotywowanej zewnętrznie (W8);
3. czy istnieje komórka klasy (C), i jeżeli tak — czy jej wielkość przekreśla
   korzyść z komórek (A) (H4).

Brak komórek (A) **nie jest porażką kampanii** — jest wynikiem: korzyść jest
wtedy strukturalna (plan, tokeny, bufory, materializacje), a nie czasowa.
Zdanie „plan jest mniejszy, ale nie szybszy" jest publikowalne; zdanie „jest
szybszy" bez tej kampanii nie jest.

### Warunki unieważniające kampanię

1. **Kontrola negatywna daje efekt.** `W5_Q32` albo `W7_Q32` w klasie (A) lub
   (C) oznacza, że instrument mierzy coś innego niż optymalizację.
2. **Wynik się zmienił.** Artefakty strumieni **nazwanych przez użytkownika**
   muszą być identyczne co do bajtu między profilami w obrębie komórki —
   z wyjątkami z K5: ośmiobajtowy nagłówek `.meta` ze znacznikiem czasu oraz
   wartość `RETMEMORY` w `.desc`, przy czym każde takie wystąpienie jest
   wypisywane imiennie. Przyspieszenie z innym wynikiem nie jest
   przyspieszeniem.
3. **Środowisko nie trzymało reżimu.** Naruszenie któregokolwiek warunku R7,
   brak wątku `SCHED_FIFO` 50, governor inny niż `performance`, throttling
   termiczny w trakcie badania.
4. **Liczniki nie zgadzają się z K5.** Przeskalowane rodziny muszą odtwarzać
   `net` i `r1` z tabeli werdyktu K5. Spełnienie tego warunku jest przeniesione
   przez referencję z v1 — patrz niżej.
5. **Defekt silnika.** Zatrzymanie przed werdyktem, `issue_NNN`, badanie
   higieniczne, nowy katalog.
6. **NOWY w v2 — rate nieidentyczny w obrębie komórki.** Jeżeli w obrębie
   jednej komórki (przypadek, profil, 15 powtórzeń) albo między profilami tego
   samego przypadku wystąpi więcej niż jedna wartość `scale`/`f_φ`, kampania
   jest nieważna. Powodem jest sama reguła per rodzina: porównanie profili ma
   sens wyłącznie przy identycznym rate'cie, a rate jest teraz zmienną, nie
   stałą kampanii. Kontrola jest wykonywana przez `analyze.py` na kolumnach
   `scale` i `f_phi_hz` w `runs.csv` i ma regresję w `tests/test_rate_guard.sh`.

### Reguła zliczania

Wniosek metodologiczny z K5h i K5i: **milczenie instrumentu wygląda jak
sukces**. Dlatego każde porównanie w tej kampanii raportuje **liczbę**
porównanych rzeczy, a zero porównanych rzeczy jest **błędem**, nie zgodnością.
Dotyczy to porównań artefaktów, liczników, komórek macierzy, replikacji
bootstrapu oraz — nowe w v2 — liczby przebiegów kalibracyjnych i liczby
komórek, na których wyznaczono rate każdej rodziny.

Kontrola czystości repozytorium kodu (R2) obejmuje pliki ignorowane
(`code_tree_fingerprint`, `require_input_dirs_pristine` w `lib/common.sh`).
Dane wejściowe EKG są **kopiowane** do `/dev/shm`, nie symlinkowane.

## Wyniki przeniesione przez referencję z `results_20260730_K6`

Obie poniższe pozycje są **niezależne od rate'u**, powstały przed jakimkolwiek
pomiarem czasu i **nie są powtarzane** w K6b:

| Pozycja | Plik | Zawartość |
|---|---|---|
| kontrola wejściowa liczników | `results_20260730_K6/results/counters.md`, `counters.json` | 230 kompilacji, 46 porównań, **0 niezgodności**; `net` i `r1` odtwarzają tabelę werdyktu K5 |
| macierz funkcjonalna | `results_20260730_K6/results/functional_matrix.md` | **45/45** |

Warunek unieważniający nr 4 jest zatem spełniony na mocy tych plików.
Powtarzanie ich w K6b nie dodałoby informacji, a dodałoby dwie godziny pracy
workera.

**Addendum W9 z v1 również obowiązuje** (`results_20260730_K6/README.md`,
sekcja „Predykcja dla W9 zawiodła, mechanizm się potwierdził"): kryterium
wejściowe W9 jest mechanizmowe (`exec_STRUCT = 2`, `exec_ALGSTRUCT = 1`,
`r2 ≥ 1`), nie węzłowe, a `W9_Q02` jest samodzielnym wynikiem — plan większy
(`net = +1`), praca na slot mniejsza (2 → 1 wykonania kosztownego programu
pól).

## Produkt uboczny: model kosztu slotu (K20 etap 1)

**Nie zmienia reguły wyboru rate'u.** Reguła zostaje empiryczna: o tym, który
szczebel drabiny wchodzi, rozstrzyga pełne przemiecenie drabiny, nie predykcja.
Model jest dopasowywany **po** kampanii, na danych, które i tak powstają, bez
ani jednego dodatkowego przebiegu pomiarowego i bez zmian w silniku.

- **Wejście:** pary (komórka, rate, `p99`) z kalibracji oraz liczniki Tier A
  (`PLAN bench` — tokeny, `PLAN capacity`, `MATERIALIZED` — materializacje
  i bajty).
- **Postać:** `koszt_slotu ≈ a · tokeny + b · materializacje + c · bajty`.
- **Procedura:** dopasowanie na części rodzin, predykcja na pozostałych,
  walidacja na medianach Tier B. Podział rodzin na uczące i testowe jest
  zamrożony **tutaj**: dopasowanie na `{W2, W3, W5, W7}`, predykcja na
  `{W4, W9}`. W4 jest w zbiorze testowym celowo — to ona łamie model liczący
  same tokeny.
- **Produkt:** `results/cost_model.md` z tabelą przewidziane vs zmierzone
  i jawnie podanym błędem względnym per rodzina.

**Model musi ważyć materializacje osobno od tokenów.** `W4_Q32` to ~33 µs na
element okna — koszt siedzi w zapisach przez `storage`, nie w arytmetyce. Model
liczący same tokeny pomyli się o rzędy wielkości. Sprawdzalna przepowiednia
zapisana przed dopasowaniem: ta sama komórka na `SUBSTRAT memory` powinna być
radykalnie tańsza.

Etap drugi K20 — kontrola dopuszczenia planu wewnątrz `xretractor` — jest
zmianą w silniku i **nie należy do K6b**: osobny `issue_NNN` z badaniem
higienicznym po zamknięciu kampanii.

## Kolejność wykonania

| Krok | Zawartość | Gdzie |
|---|---|---|
| K6b.1 | predeklaracja v2 (ten plik) + kod, commit **przed** danymi | nadzorca |
| K6b.0 | kalibracja rate per rodzina po drabinie sześcioszczeblowej | worker |
| K6b.3 | Tier A przy `s = 6` | worker |
| K6b.4 | Tier B, siedem badań, reboot między badaniami | worker |
| K6b.5 | punkt saturacji | worker |
| K6b.6 | `analyze.py` — werdykt | nadzorca |
| K6b.7 | `cost_model.py` — model kosztu slotu (K20 etap 1) | nadzorca |

## Zgodność z REQUIREMENTS.md

| Wymaganie | Zastosowanie |
|---|---|
| R1 dwa repozytoria | kod `retractordb` @ `master` `bb3a521`, wyniki `rdb-experiment` @ `experiment/20260730_K6` |
| R2 zakaz zapisu do repo kodu | dane robocze i artefakty w `/dev/shm`; dane EKG kopiowane; `code_tree_fingerprint` + `require_input_dirs_pristine` przed i po |
| R3 katalog docelowy | `results_20260730_K6b/`, bez rotacji; `results_20260730_K6/` zamknięty i nietknięty |
| R4 branch i commity | commity i push w trakcie realizacji dozwolone przez człowieka; jeden commit, `--amend` + `push --force-with-lease` |
| R5 warunki wejściowe | oba repozytoria czyste, commit kodu przypięty, `/dev/shm` = tmpfs, walidacja builda i RT |
| R6 build pomiarowy | pięć profili Release z `RDB_BENCH_PROBE=ON` w `build/K6-<slug>`, już zbudowanych i zweryfikowanych; K6b nie przebudowuje |
| R7 środowisko RT | PREEMPT_RT, governor `performance`, rdzeń 3 izolowany, tło na 0–2, `SCHED_FIFO` 50, capabilities na każdej z pięciu binarek |
| R8 przebieg badania | siedem badań Tier B, reboot i `sync` między badaniami |
| R9 rejestrowane dane | `state_before.md`, `state_after.md`, `e1_probe.csv`, `metrics.csv`, `xretractor.log`, `results.md` per przebieg |
| R10 znaczenie metryk | `queue-emission latency`, nigdy „E2E" |
| R11 walidacja i fałszywy sukces | warunki unieważniające wyżej + reguła zliczania |
| R12 odtwarzalność | `manifest.md`, ten plik, wpisy w `JOURNAL.md` |
| R13 wykrywanie workera | nadzorca, fingerprint SSH z `known_hosts`; worker na kablu, `192.168.88.13` |
| R14 higiena artefaktów | surowe w `/dev/shm`, do repo `tar.gz` + indeks SHA-256, dowody porażek imiennie w `results/evidence/` |

## Odstępstwa

1. **R4, jeden commit.** Człowiek zezwolił 2026-07-30 na commity i push
   w trakcie realizacji, na nadzorcy i na workerze.
2. **Kontrola wejściowa i macierz funkcjonalna przeniesione przez referencję**
   z `results_20260730_K6`, zamiast powtórzenia. Uzasadnienie w sekcji wyżej;
   jest to decyzja udokumentowana, nie skrót.
