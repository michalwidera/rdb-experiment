# K6 — kampania ablacyjna z powtórzeniami: koszt i korzyść czasowa

**Predeklaracja.** Ten plik powstaje i jest commitowany **przed** wygenerowaniem
jakichkolwiek danych tej kampanii. Wszystkie parametry, próg istotności, reguła
wyboru rate'u pomiarowego i reguła decyzyjna są zamrożone. Po pierwszym
przebiegu nie wolno ich zmienić ani doprecyzować. Jedyną dopuszczalną reakcją na
niespodziankę jest **zatrzymanie kampanii i nowy katalog** (`REQUIREMENTS.md`
R3), tak jak w K5 → K5 rerun.

## Cel

Zamknąć lukę **G8** i kosztową część **G14** z `research_plan.md`:

> „Twierdzicie, że plan jest mniejszy. Czy jest szybszy?"

K5 rozstrzygnął strukturę: `ALGSTRUCT` usuwa węzły, których `STRUCT` nie usuwa
(werdykt GO, `results_20260729_K5_rerun/`). K5 świadomie nie zmierzył **żadnej
wielkości czasowej**. Bez K6 contribution nr 2 pozostaje zaimplementowaną
funkcją bez wykazanego efektu, a hipoteza **H4** — niesprawdzona. Zakaz z §3.4
planu („nie wpisywać wyników kosztowych R1/R2 przed kampanią K6") zdejmuje
dopiero ta kampania.

## Silnik jest zamrożony i nie jest modyfikowany

Kampania biegnie na `retractordb` @ `master` **`bb3a521`** i **nie wprowadza
żadnej zmiany w kodzie silnika**. Cała potrzebna instrumentacja istnieje po
K5i:

| Metryka §9.2 | Instrument | Aktywacja |
|---|---|---|
| rozmiar planu, tokeny FROM/pól, dedup | `PLAN bench` | `RDB_BENCH_PLAN` |
| atrybucja reguł | `REWRITE_APPLIED r1= r2=` | `RDB_BENCH_PLAN` |
| czas kompilacji | `COMPILE_NS <ns> sonda=<ns>` | `RDB_BENCH_PLAN` |
| rozmiar buforów | `PLAN capacity: strumieni= suma= maks=` | `RDB_BENCH_PLAN` |
| materializacje trwałe i pamięciowe | `MATERIALIZED trwale: … pamieciowe: …` | `RDB_BENCH_MATERIALIZE` |
| `compute_ns`, `wake_lag_ns`, `e2e_ns` | sonda E1, CSV | `RDB_BENCH_CSV` |
| peak RSS, CPU time, checksum | poza silnikiem: `/proc/PID/status VmHWM`, `/proc/PID/stat`, `sha256sum` | harness |

Wszystkie trzy zmienne środowiskowe działają w jednym przebiegu, więc jedna
komórka macierzy = jedno uruchomienie `xretractor` dające komplet metryk.

**Dlaczego zamrożenie jest częścią metody, a nie wygodą.** Każda zmiana
`master` unieważnia przypięcie wyników i wymusza kolejne badanie higieniczne —
precedens `Fix (#214)` (K5h) i `bb3a521` (K5i). Branch w repozytorium kodu
powstaje w tej kampanii **wyłącznie reaktywnie**: jeżeli K6 wykryje defekt
silnika, kampania zostaje zatrzymana przed werdyktem, defekt naprawiony na
`issue_NNN`, wykonane badanie higieniczne i kampania **powtórzona w nowym
katalogu** — dokładnie ścieżką K5 → `issue_213-defect-interval` → K5 rerun.

## Czego ta kampania świadomie nie mierzy

1. **Ablacji infrastruktury z §9.2** (persistence/metadata/IPC włączone i
   wyłączone, integer vs rational scheduling). Przełączniki nie istnieją, a ich
   dodanie jest zmianą architektoniczną w rdzeniu, nie instrumentacyjną —
   decyzja K5i. §9.2 opisuje je jako „dodatkowo"; kryterium ukończenia K6 ich
   nie wymaga.
2. **Pełnego application E2E.** Sonda kończy się na emisji do kolejki klienta
   (`REQUIREMENTS.md` R10). Metryka nazywa się `queue-emission latency` i nie
   wolno jej nazywać E2E.
3. **Progu 480/510 Hz z powtórzeniami ani soak testu** — to K11.
4. **Skalowania liczby klientów z `Q`.** Każdy przebieg ma dokładnie jednego
   klienta `xqry`, stałego w profilach; skalowanie klientów należy do K11.
5. **Kryterium every-slot jako sufitu publikacyjnego.** K6 raportuje rozkład
   `compute_ns` (mediana, IQR, p99, p99,9, maksimum), ale sufit every-slot
   z §7.4 pozostaje wynikiem kampanii wydajnościowej, nie tej.

## Profile

Pięć profili z K4, bez zmian (`profiles.tsv`), wszystkie Release
z `RDB_BENCH_PROBE=ON`, `--build-info` weryfikowane bajtowo. Katalogi budowy
mają przedrostek `K6-`.

| Profil | dedup | share | commutative (R2) | factor (R1) |
|---|---|---|---|---|
| `OFF` | OFF | OFF | OFF | OFF |
| `STRUCT` | ON | ON | OFF | OFF |
| `STRUCT+R1` | ON | ON | OFF | ON |
| `STRUCT+R2` | ON | ON | ON | OFF |
| `ALGSTRUCT` | ON | ON | ON | ON |

Porównaniem podstawowym jest `ALGSTRUCT` względem `STRUCT`: obie mają pełną
redukcję strukturalną, więc różnica jest wkładem algebry, a nie CSE. `OFF`
jest dolnym punktem odniesienia, `STRUCT+R1` i `STRUCT+R2` służą atrybucji
(G14).

## Rodziny workloadów

Osiem rodzin z K5 w niezmienionej **konstrukcji** oraz nowa rodzina W9.

| | Rodzina | Konstrukcja | Rola w K6 |
|---|---|---|---|
| W1 | pojedyncza instancja reguły | `(A>2)#(B>1)` | tylko Tier A |
| W2 | `Q` zapytań ze wspólnym `phi(A,B)` | `Q` × `(A>2)#(B>1)` | rdzeń: `r1 = Q`, `net = −1` |
| W3 | głębokość wspólnego podplanu | zagnieżdżone `((phi>2)#(S>1))`, `d = 1,2,3` | jedyna rodzina, w której `net` rośnie (−1, −2, −3) |
| W4 | kosztowny operator za wspólnym podplanem | `phi → projekcja → @(1,30) → .avg` | kosztowna praca za wspólnym węzłem |
| W5 | **kontrola negatywna** | `Q` × `A_j#B_j`, bez przesunięć | `net = 0`; **musi wyjść neutralnie** |
| W6 | near-miss | `(A>1)#(B>1)`, `i·Δ_A ≠ k·Δ_B` | tylko Tier A |
| W7 | materializacja blokuje rewrite | przesunięcia jako strumienie publiczne | `net = 0`; **musi wyjść neutralnie** |
| W8 | **umotywowana zewnętrznie** | potok Pan-Tompkins `rec205` + `Q` monitorów nad `(mlii>29)#(mwi>29)` | zamyka G7; jedyna rodzina z realnym sygnałem |
| W9 | **R2-shaped, nowa w K6** | `Q` publicznych `SELECT` z tym samym kosztownym programem pól, naprzemiennie `FROM a+b` i `FROM b+a` | jedyna rodzina, w której odpala R2; bez niej atrybucja kosztowa R2 z G14 zostaje otwarta |

`Q ∈ {1, 2, 4, 8, 16, 32}` (W3: `d ∈ {1,2,3}` przy `Q = 8`).

### Dlaczego W9 musi istnieć

Wszystkie rodziny K5 są R1-shaped: tabela werdyktu K5 raportuje `r1` i ani jednej
aplikacji R2. Gdyby K6 mierzył tylko je, o R2 nie dałoby się powiedzieć nic
czasowego, a G14 pyta wprost: *„która reguła odpowiada za wykazany efekt?"*.

W9 jest zbudowana tak, żeby R2 **musiał** być jedynym mechanizmem scalenia:
`Q` publicznych `SELECT`-ów o identycznym programie pól, połowa nad `a+b`,
połowa nad `b+a`. Pod `STRUCT` deduplikacja strukturalna scala każdą połowę
osobno — zostają **dwa** substraty `STREAM_SELECT_*`, każdy wykonujący
kosztowny program raz na slot. Kanonizacja odcisku R2 zrównuje dzieci węzła
`STREAM_ADD`, więc obie połowy trafiają do **jednego** substratu i kosztowny
program wykonuje się raz, nie dwa razy. Konstrukcja jest wzorowana na
istniejącym teście integracyjnym `select_cse_commutative_add`, w którym ta
równoważność jest już dowiedziona bajtowo; W9 dodaje wyłącznie parametr `Q`
i koszt programu pól (16 pól na strumień, projekcja `a[_]*b[_]`).

W9 jest zatem jedyną rodziną, w której korzyść nie polega na usunięciu węzła
przekazującego dane, lecz na **usunięciu wykonania kosztownego programu**. To
czyni ją najmocniejszym kandydatem na efekt widoczny w `compute_ns` i tak ma
być raportowana — również wtedy, gdy jako jedyna da efekt.

## Rate pomiarowy — reguła zamrożona, wartość wyznaczana

Rate'y K5 (`Δ_A = 1/10 s`, `Δ_B = 1/5 s`, `φ` = 15 Hz) były nieistotne, bo
kampania była compile-only; w K6 dawałyby 4,5 minuty na przebieg. Rodziny
syntetyczne są więc **przeskalowane**: warunek reguły R1 `2·Δ_A = 1·Δ_B` jest
niezmienniczy na skalowanie, więc mnożnik `s` nie zmienia struktury planu, tylko
tempo.

**Drabina kandydatów (zamrożona):** `s ∈ {36, 24, 12, 6}`, czyli
`f_A = 10·s` Hz, `f_B = 5·s` Hz, `f_φ = 15·s` Hz:

| `s` | `f_A` | `f_B` | `f_φ` | slot `φ` |
|---:|---:|---:|---:|---:|
| 36 | 360 Hz | 180 Hz | 540 Hz | 1,85 ms |
| 24 | 240 Hz | 120 Hz | 360 Hz | 2,78 ms |
| 12 | 120 Hz | 60 Hz | 180 Hz | 5,56 ms |
| 6 | 60 Hz | 30 Hz | 90 Hz | 11,1 ms |

**Reguła wyboru (zamrożona):** kampania używa **największego** `s`, dla którego
w kroku kalibracyjnym K6.0 **każda** komórka kalibracyjna spełnia
`p99(compute_ns) ≤ 0,5 · slot(φ)`. Powód: porównanie profili musi zachodzić
w reżimie **nienasyconym**; w saturacji `compute_ns` przestaje mierzyć koszt
planu, a zaczyna mierzyć backlog. Saturacja jest osobnym, jawnym punktem
kampanii (K6.5), nie tłem pozostałych pomiarów.

Komórki kalibracyjne (zamrożone): `{W2_Q32, W3_d3, W4_Q32, W9_Q32}` ×
`{OFF, STRUCT}`, 3 powtórzenia, 1000 slotów. Kalibracja startuje od `s = 36`
i schodzi po drabinie. **Wyniki kalibracji nie są wynikami kampanii** — służą
wyłącznie ustaleniu `s`, są zapisywane w `results/calibration.md` i tam
zostają.

**W8 nie podlega drabinie.** Jej rate jest zamrożony na **360 Hz**, bo wynika
z deklaracji źródła `rec205` (`1/360`) i jest kotwicą porównywalności z §7
artykułu. Jeżeli najcięższa komórka W8 narusza regułę 50%, jej cele **nie są
zwalniane** — komórka zostaje w macierzy i jest raportowana jako nasycona, wraz
z konsekwencją dla interpretacji.

**Kwantyzacja deadline'ów do pełnych milisekund** (G11) dotyczy wszystkich
profili identycznie, więc nie jest zakłóceniem porównania. Wpływa na
`wake_lag_ns` i `e2e_ns`, nie na `compute_ns`, który jest mierzony bezpośrednio
wokół `processRows()`. To jest powód, dla którego metryką **główną** jest
`compute_ns`, a nie queue-emission latency.

**Budżet przebiegu (zamrożony):** liczba slotów =
`clamp(round(8 s / slot(φ)), 1500, 6000)`, ta sama dla wszystkich profili
w danej rodzinie. Pierwsze **5%** slotów jest odrzucane w analizie jako
transjent startowy (komentarz `executorsm.cpp`: 20–47 ms w `wake_lag`).
Odrzucenie jest zapisane w kodzie analizy, nie wybierane po zobaczeniu danych.

## Macierz

### Tier A — metryki kompilacji

46 przypadków (osiem rodzin K5 = 40, W9 = 6) × 5 profili × **15 powtórzeń**,
kolejność losowana w obrębie powtórzenia (ziarno `20260730`, zapisane).
Zbierane: `COMPILE_NS`, `PLAN bench`, `PLAN capacity`, `REWRITE_APPLIED`.
Uruchamiane na workerze z governorem `performance` i przypięciem do
izolowanego rdzenia 3 — czas kompilacji jest metryką czasową.

### Tier B — metryki runtime

14 przypadków × 4 profile × **15 powtórzeń** = 840 przebiegów.

| Przypadki | Profile |
|---|---|
| `W2_Q01`, `W2_Q08`, `W2_Q32`, `W3_d1`, `W3_d3`, `W4_Q08`, `W4_Q32`, `W5_Q32`, `W7_Q32`, `W8_Q01`, `W8_Q08`, `W8_Q32` | `OFF`, `STRUCT`, `STRUCT+R1`, `ALGSTRUCT` |
| `W9_Q08`, `W9_Q32` | `OFF`, `STRUCT`, `STRUCT+R2`, `ALGSTRUCT` |

Jedno **badanie** (`study_NN` w rozumieniu R8) = jedna rodzina; wewnątrz
badania kolejność wszystkich trójek (przypadek, profil, powtórzenie) jest
losowana, żeby dryf termiczny i częstotliwościowy nie sprzęgł się z profilem.
Reboot workera następuje **między** badaniami. Siedem badań: W2, W3, W4, W5,
W7, W8, W9.

### K6.5 — punkt saturacji

`W8_Q32` × `{STRUCT, ALGSTRUCT}` × `{360, 480, 540}` Hz × 5 powtórzeń.
Metryka: udział slotów z `compute_ns > slot(φ)`. Pytanie: czy `ALGSTRUCT`
utrzymuje rate, którego `STRUCT` nie utrzymuje. To jest odpowiedź na „czy jest
szybszy?" w idiomie §7 i nie wymaga sweepu na dziewięć punktów.

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
| checksum artefaktów | `sha256sum` | kontrola poprawności, patrz niżej |

## Reguła decyzyjna — zamrożona

Dla komórki `c` niech `r(c) = mediana₁₅(ALGSTRUCT) / mediana₁₅(STRUCT)`
metryki głównej, a `CI(c)` — przedział bootstrapowy 95% ilorazu
(10 000 replikacji, ziarno `20260730`, percentyle 2,5 i 97,5).

**Próg istotności praktycznej: 10%.** Ustalony przed kampanią.

| Klasa | Warunek |
|---|---|
| **(A) poprawa** | `r(c) ≤ 0,90` **i** górna granica `CI(c) < 1,00` |
| **(B) neutralna** | `CI(c)` zawiera `1,00` **albo** `|1 − r(c)| < 0,10` |
| **(C) regresja** | `r(c) ≥ 1,10` **i** dolna granica `CI(c) > 1,00` |

**Werdykt kampanii** podaje liczbę komórek w każdej klasie — **wszystkich**,
nie tylko najlepszych — oraz jawnie stwierdza:

1. czy istnieje choć jedna komórka klasy (A);
2. czy istnieje komórka klasy (A) w rodzinie umotywowanej zewnętrznie (W8);
3. czy istnieje komórka klasy (C), i jeżeli tak — czy jej wielkość przekreśla
   korzyść z komórek (A) (H4: „bez pogorszenia pozostałych metryk, które
   przekreślałoby tę korzyść").

Brak komórek (A) **nie jest porażką kampanii** — jest wynikiem: korzyść jest
wtedy strukturalna (plan, tokeny, bufory, materializacje), a nie czasowa,
i dokładnie to trafia do artykułu przez K7b. Zdanie „plan jest mniejszy, ale
nie szybszy" jest publikowalne; zdanie „jest szybszy" bez tej kampanii nie
jest.

### Warunki unieważniające kampanię

1. **Kontrola negatywna daje efekt.** `W5_Q32` albo `W7_Q32` w klasie (A) lub
   (C) oznacza, że instrument mierzy coś innego niż optymalizację. Kampania
   jest wtedy nieważna i nie wolno raportować pozostałych komórek jako wyniku.
2. **Wynik się zmienił.** Artefakty strumieni **nazwanych przez użytkownika**
   muszą być identyczne co do bajtu między profilami w obrębie komórki —
   z wyjątkami z K5: ośmiobajtowy nagłówek `.meta` ze znacznikiem czasu oraz
   wartość `RETMEMORY` w `.desc`, przy czym każde takie wystąpienie jest
   wypisywane imiennie. Przyspieszenie z innym wynikiem nie jest
   przyspieszeniem.
3. **Środowisko nie trzymało reżimu.** Naruszenie któregokolwiek warunku R7,
   brak wątku `SCHED_FIFO` 50, governor inny niż `performance`, throttling
   termiczny w trakcie badania.
4. **Liczniki nie zgadzają się z K5.** Kontrola wejściowa wymaga, żeby
   przeskalowane rodziny odtwarzały `net` i `r1` z tabeli werdyktu K5. Inne
   liczniki znaczą inny plan, a wtedy K6 nie mierzy tego, co K5 rozstrzygnął.
5. **Defekt silnika.** Jak w K5: zatrzymanie przed werdyktem, `issue_NNN`,
   badanie higieniczne, nowy katalog.

### Reguła zliczania

Wniosek metodologiczny z K5h i K5i: **milczenie instrumentu wygląda jak
sukces**. Dlatego każde porównanie w tej kampanii raportuje **liczbę**
porównanych rzeczy, a zero porównanych rzeczy jest **błędem**, nie zgodnością.
Dotyczy to porównań artefaktów, liczników, komórek macierzy i replikacji
bootstrapu.

Konsekwencja trzeciego defektu tej klasy, wykrytego przy przygotowaniu K6:
kontrola czystości repozytorium kodu (R2) używa
`git status --short --ignored=matching`, bo `git status --short` jest ślepy na
pliki wypisane w `.gitignore`, a artefakty silnika w `examples/ecg/rec205/` są
tam wypisane imiennie. Dane wejściowe EKG są **kopiowane** do `/dev/shm`, nie
symlinkowane do repozytorium kodu.

## Kolejność wykonania

| Krok | Zawartość | Gdzie |
|---|---|---|
| K6.1 | `generate.py` — rodziny w rate pomiarowym + W9 | nadzorca |
| K6.1b | kontrola wejściowa: liczniki `net`/`r1`/`r2` odtwarzają K5 | nadzorca, compile-only |
| K6.2 | `build_profiles.sh` — 5 profili, `--build-info`, `setcap`, `ctest` ablacji | worker |
| K6.0 | kalibracja rate po zamrożonej drabinie | worker |
| K6.3 | Tier A | worker |
| K6.4 | Tier B, siedem badań, reboot między badaniami | worker |
| K6.5 | punkt saturacji | worker |
| K6.6 | `analyze.py` + `verdict.py` | nadzorca |

## Zgodność z REQUIREMENTS.md

| Wymaganie | Zastosowanie |
|---|---|
| R1 dwa repozytoria | kod `retractordb` @ `master` `bb3a521`, wyniki `rdb-experiment` @ `experiment/20260730_K6` |
| R2 zakaz zapisu do repo kodu | dane robocze i artefakty w `/dev/shm`; dane EKG kopiowane, nie symlinkowane; kontrola `git status --short --ignored=matching` przed i po |
| R3 katalog docelowy | `results_20260730_K6/`, bez rotacji |
| R4 branch i commity | commity i push w trakcie realizacji dozwolone przez człowieka (odstępstwo uzgodnione 2026-07-30) |
| R5 warunki wejściowe | oba repozytoria czyste, commit kodu przypięty, `/dev/shm` = tmpfs, walidacja builda i RT |
| R6 build pomiarowy | pięć profili Release z `RDB_BENCH_PROBE=ON` w `build/K6-<slug>`; `--build-info` weryfikowane bajtowo per profil |
| R7 środowisko RT | PREEMPT_RT, governor `performance`, rdzeń 3 izolowany (`isolcpus=3 nohz_full=3 rcu_nocbs=3`), tło na 0–2, `SCHED_FIFO` 50, `cap_sys_nice`+`cap_ipc_lock` na każdej z pięciu binarek |
| R8 przebieg badania | siedem badań Tier B, reboot i `sync` między badaniami |
| R9 rejestrowane dane | `state_before.md`, `state_after.md`, `e1_probe.csv`, `metrics.csv`, `xretractor.log`, `results.md` per przebieg |
| R10 znaczenie metryk | `queue-emission latency`, nigdy „E2E" |
| R11 walidacja i fałszywy sukces | warunki unieważniające wyżej + reguła zliczania |
| R12 odtwarzalność | `manifest.md`, ten plik z SHA-256, wpisy w `JOURNAL.md` |
| R13 wykrywanie workera | nadzorca, fingerprint SSH z `known_hosts` |
| R14 higiena artefaktów | surowe w `/dev/shm`, do repo `tar.gz` + indeks SHA-256, dowody porażek imiennie w `results/evidence/` |

## Odstępstwa

1. **R4, jeden commit.** Człowiek zezwolił 2026-07-30 na commity i push
   w trakcie realizacji, na nadzorcy i na workerze.

---

## Addendum 2026-07-30, przed jakimkolwiek pomiarem czasu

Zapisane osobno, żeby predeklaracja wyżej pozostała nietknięta. Powstało
w kroku K6.1b (kontrola wejściowa, compile-only), **przed** zbudowaniem
czegokolwiek na workerze i przed pierwszym pomiarem czasu.

### Kontrola wejściowa przeszła dla rodzin z K5

230 kompilacji (46 przypadków × 5 profili), 46 porównań `STRUCT` vs
`ALGSTRUCT`, **zero niezgodności**. Przeskalowanie rate'u mnożnikiem `s = 36`
nie zmieniło struktury planu: `net` i `r1` odtwarzają tabelę werdyktu K5 dla
wszystkich ośmiu rodzin, w tym `net = −1, −2, −3` dla W3 o głębokości 1, 2, 3
oraz zera dla kontroli W5, W6 i W7. Warunek unieważniający nr 4 jest spełniony.

### Predykcja dla W9 zawiodła, mechanizm się potwierdził

Przewidywano `net = −2`. Zmierzono `net = +1` dla `Q = 2` i `net = −1` dla
`Q ≥ 4`. Mechanizm opisany wyżej okazał się natomiast dokładnie taki, jak
zapisano — liczba wykonań kosztownego programu pól na slot spada z **2 do 1**:

| `Q` | `STRUCT` | `ALGSTRUCT` | wykonania programu na slot | `net` | `r2` |
|---:|---|---|---:|---:|---:|
| 1 | brak substratu | brak substratu | 1 → 1 | 0 | 0 |
| 2 | brak substratu, dwa publiczne liczą same | jeden substrat + dwie lekkie projekcje | **2 → 1** | **+1** | 1 |
| 4 | dwa substraty `STREAM_SELECT_*` | jeden substrat | **2 → 1** | −1 | 2 |
| 8 | j.w. | j.w. | **2 → 1** | −1 | 4 |
| 16 | j.w. | j.w. | **2 → 1** | −1 | 8 |
| 32 | j.w. | j.w. | **2 → 1** | −1 | 16 |

**Konsekwencja dla kryterium.** Kryterium wejściowe W9 przestaje być `net`
i staje się mechanizmowe: `exec_STRUCT = 2` i `exec_ALGSTRUCT = 1`, gdzie
`exec` to liczba substratów `STREAM_SELECT_*`, a przy ich braku — `Q`. Metryka
główna kampanii **nie zmienia się**: nadal jest to mediana `compute_ns`.

**Konsekwencja dla artykułu.** `W9_Q02` jest samodzielnym wynikiem: plan jest
**większy** (`net = +1`), a praca na slot **mniejsza** (2 → 1 wykonania).
To jest dowód z własnego systemu na to, dlaczego H4 zabrania zastępowania
korzyści rozmiarem planu — rozmiar planu jest metryką pośrednią i może iść
w przeciwną stronę niż koszt wykonania. K5 pokazał, że korzyść nie skaluje się
z `Q` tak, jak sugerowałaby intuicja; W9 pokazuje, że nie zawsze widać ją
w liczbie węzłów.

Nic w regule decyzyjnej, progu 10%, drabinie rate'u ani macierzy nie zostało
zmienione.
