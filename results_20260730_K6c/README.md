# K6c — kampania ablacyjna z powtórzeniami: koszt i korzyść czasowa

**Predeklaracja v3.** Ten plik powstaje i jest commitowany **przed**
wygenerowaniem jakichkolwiek danych tej kampanii. Wszystkie parametry, próg
istotności, reguła wyboru rate'u pomiarowego i reguła decyzyjna są zamrożone.
Po pierwszym przebiegu nie wolno ich zmienić ani doprecyzować. Jedyną
dopuszczalną reakcją na niespodziankę jest **zatrzymanie kampanii i nowy
katalog** (`REQUIREMENTS.md` R3).

Katalogi `results_20260730_K6` (v1) i `results_20260730_K6b` (v2) są
**zamknięte**. Nie wolno w nich niczego edytować ani wznawiać.

## Dlaczego v2 upadła — dwie rzeczy, obie nazwane

K6b została zatrzymana przed werdyktem na warunku unieważniającym nr 5 (defekt
silnika). Zatrzymanie ujawniło jednak **dwie** wady, nie jedną, i tylko jedna
z nich była defektem kodu.

### 1. Defekt klienta — naprawiony częściowo, patrz korekta niżej

`xqry` kończył się przed silnikiem w rodzinie W8 (zmierzone: `W8_Q08` kod 4
przy silniku żyjącym 6419 ms, `W8_Q32` kod 4 przy 10 647 ms). Ponieważ `e2e_ns`
jest z definicji opóźnieniem emisji do kolejki **tego** klienta, zniknięcie go
po ¼ przebiegu oznacza, że reszta przebiegu mierzy co innego niż zadeklarowano.
Naprawa jest w `master` jako `e1e5181` („Poprawka klienta po eksperymencie
(#216)") wraz z dziesięcioma regresjami, o których wykazano, że czerwienią się
po cofnięciu naprawy.

> **Korekta z 2026-07-31.** Ta sekcja twierdziła „naprawiony, zamknięty".
> To było przedwczesne. `e1e5181` naprawił tryb, w którym klient kończył się
> kodem 4; K6c zatrzymała się na **innym** trybie, kończącym się kodem 110
> (`timed_out`), którego tamta naprawa nie dotykała. Pełna diagnoza w sekcji
> „Zatrzymanie na W8" niżej.

### 2. Zła definicja `slot` — powód istnienia K6c

Predeklaracje v1 i v2 wyliczały `slot(φ) = 1/(15·s)` arytmetycznie, jako
interwał przeplotu **dwóch** strumieni `A#B`. Dla rodzin, których strumień
wyjściowy jest głębszym zagnieżdżeniem, to jest po prostu nieprawda: przeplot
**sumuje częstotliwości**, więc każdy kolejny poziom zagęszcza slot. Zapytany
o to silnik (`xqry -t`) odpowiada, przy `s = 24`:

| Komórka | strumień mierzony | wyliczone wg v2 | **wg silnika** | rozjazd |
|---|---|---:|---:|---:|
| `W2_Q32` | `w2_out_000` | 1/360 | 1/360 | — |
| `W3_d1` | `w3_out_000` | 1/360 | 1/360 | — |
| `W3_d3` | `w3_out_000` | 1/360 | **1/810** | 2,25× |
| `W8` | `mon_000` | 1/360 | **1/720** | 2× |

Skutek jest dokładnie tym, czemu reguła 50 % miała zapobiec: `W3_d3` przeszła
kalibrację K6b (`p99` 1122 µs wobec budżetu 1389 µs), choć wobec **prawdziwego**
slotu 1235 µs pracowała na **91 %** — czyli w nasyceniu. Drugi skutek: przebiegi
tej komórki trwały ~3,5 s zamiast zadeklarowanych 8 s.

Wniosek metodologiczny jest ten sam co po v1, tylko dotyczy innej wielkości:
**to, co system wie, należy z systemu odczytać, a nie odtwarzać rachunkiem obok
niego.** Interwał każdego strumienia jest znany w czasie kompilacji i silnik go
publikuje. Rachunek w predeklaracji był kopią tej wiedzy, która rozjechała się
z oryginałem.

Trzecim miejscem tego samego błędu był krok saturacji: liczył przekroczenia
wobec `1/rate` **źródła** `rec205`, podczas gdy mierzony `mon_000` biegnie dwa
razy gęściej. Udział przekroczeń był przez to zaniżony.

## Co zmienia v3

Pięć zmian, wszystkie wynikające z jednego ustalenia:

1. **`slot` pochodzi z silnika, nie z rachunku.** Kalibracja pyta `xqry -t`
   o interwał strumienia wskazanego w kolumnie `client_stream` macierzy i tę
   wartość podstawia do reguły 50 % oraz do budżetu slotów.
2. **`slot` jest własnością KOMÓRKI, nie rodziny.** `W3_d1` i `W3_d3` mają go
   różny przy tym samym `s`. Budżet przebiegu — zamrożone
   `slots = clamp(round(8 s / slot), 400, 6000)` — liczony jest więc per
   komórka. **Wzór się nie zmienia; zmienia się to, że wstawiamy do niego
   prawdziwą wartość.** Rate rodziny (szczebel `s`) pozostaje wspólny, bo to on
   decyduje o porównywalności `Q` wewnątrz rodziny.
3. **Macierz rozdziela dwie wielkości, które v2 myliła.** Kolumna `rate` mówi,
   skąd bierze się rate (`calibration` / `source`), a `source_hz` opisuje
   **źródło danych** (`rec205`, 360 Hz). Slot strumienia **mierzonego** nie jest
   ani jednym, ani drugim — jest odczytywany z silnika.
4. **Warunek unieważniający nr 6 obejmuje `stream_hz`.** Sam `scale` nie
   wyznacza slotu, więc kontrola oparta wyłącznie na `scale`/`f_φ` przepuściłaby
   porównanie profili przy różnym slocie. `runs.csv` dostaje kolumnę `stream_hz`.
5. **Krok saturacji liczy przekroczenia wobec slotu z silnika**, nie wobec
   `1/rate` źródła.

**Nic więcej się nie zmienia.** Pięć profili, dziewięć rodzin,
`Q ∈ {1, 2, 4, 8, 16, 32}`, drabina `s ∈ {36, 24, 12, 6, 3, 1}`, 15 powtórzeń,
losowa kolejność, metryka główna = mediana `compute_ns`, próg istotności 10 %,
klasy A/B/C, pozostałe warunki unieważniające, Tier A przy `s = 6`, W8 z rate'em
ze źródła — wszystko jak w v2.

## Dlaczego per rodzina, a nie per komórka

Bez zmian względem v2, bo zmiana v3 tego nie dotyka. Rate wybierany osobno dla
każdej **komórki** skaziłby porównanie skalowania w `Q` wewnątrz rodziny:
`W2_Q08` przy 180 Hz i `W2_Q32` przy 90 Hz nie są porównywalne, bo różni je
także rate. Rodzina jest najmniejszą jednostką, wewnątrz której `Q` jest jedyną
zmienną.

Odróżnienie, na którym stoi v3: **rate jest wyborem, slot jest konsekwencją.**
Rate (szczebel `s`) wybieramy per rodzina. Slot wynika z rate'u i z kształtu
planu komórki, więc różni się między komórkami tej samej rodziny i nie jest
niczyim wyborem. Wspólny rate zachowuje porównywalność `Q`; wspólny slot był
fikcją.

## Silnik jest zamrożony i nie jest modyfikowany

Kampania biegnie na `retractordb` @ `master`
**`e1e5181`** i **nie wprowadza żadnej zmiany w kodzie silnika**. Przypięcie
przesuwa się z `bb3a521` (v2) wyłącznie dlatego, że v2 wykryła defekt klienta,
który został naprawiony — czyli dokładnie tą ścieżką, którą v2 przewidziała
(„branch w repozytorium kodu powstaje wyłącznie reaktywnie").

**Zakres `e1e5181` wobec ścieżki pomiarowej silnika.** Poza `src/qry/` i testami
commit rusza wyłącznie `src/common/uxSysTermTools.cpp` (`_kbhit`). Silnik woła
`_kbhit(ignoreanykey)` raz na obrót pętli, ale kampania uruchamia go z `-k`,
czyli `noanykey` (`launcher.cpp:292`), więc funkcja zwraca `false` w **pierwszej
linii** i nie dochodzi do zmienionego fragmentu.

Powyższe jest argumentem, nie werdyktem, więc **badanie higieniczne zostało
wykonane**: `results_20260731_hygiene/` (branch `experiment/20260731_hygiene`,
commit `c836a60`). Werdykt: **brak wpływu**. Korpus 81 plików RQL bez różnicy
w zrzutach planu, statusie kompilacji i licznikach R1/R2; trzy deterministyczne
potoki bajtowo identyczne; klient — 78 poleceń porównanych, zero niezgodnych.
Badanie dostało trzecią warstwę, porównującą `xqry`, bo to w kliencie siedzi
164 z 171 zmienionych linii. Polecenie `-t`, od którego zależy kalibracja K6c,
porównano 70 razy — za każdym razem identycznie.

**Klient jest częścią aparatury pomiarowej.** Kampania czyta przez `xqry`
interwał strumienia, więc harness sprawdza nie tylko obecność klienta na PATH,
ale i **commit, z którego pochodzi** (`--help` wypisuje `Branch: <branch>:<sha>`).
Bez tej kontroli stary klient przeszedłby walidację i po cichu wróciłby
z defektem, dla którego naprawy zatrzymano K6b. Regresja:
`tests/test_slot_guard.sh`.

Pięć profili K6 jest zbudowanych na workerze (`--build-info` bajtowo,
`cap_ipc_lock,cap_sys_nice=ep` na każdej binarce). Przejście na `e1e5181`
wymaga ich **przebudowy** — binarki z `bb3a521` nie są binarkami tej kampanii.

**Drugie przesunięcie przypięcia: `e1c13bb` (dla W8, W9, K6c.5).** Ta sama
reguła i ten sam kształt argumentu. Commit rusza `src/qry/` (klient), testy,
`src/retractor/README.md` (dokumentacja) oraz — poza klientem — dwie rzeczy
w kodzie linkowanym do silnika:

- `src/common/uxSysTermTools.cpp`: console sink w `setupLoggerMain` przełączony
  ze STDOUT na STDERR **wyłącznie w gałęzi `dual`**. Silnik woła
  `setupLoggerMain(argv[0], false /* dual */, serviceLog)` (`launcher.cpp:221`),
  więc do zmienionej gałęzi nie wchodzi. Jedynym binarium z `dual=true` jest
  `xqry`.
- `src/retractor/lib/appConfig.hpp`: domyślna wartość
  `ipc.client_response_max_fails` 10 → 300. Silnik waliduje to pole razem z
  resztą konfiguracji (`appConfig.cpp:48`), ale nigdzie go nie **używa** —
  jedynym konsumentem jest `qryLauncher.cpp:93` przy konstrukcji `qry`.
  Wartość 300 nie przekracza progu ostrzeżenia (1000), więc nie zmienia nawet
  treści logu silnika.

Ścieżka pomiarowa silnika (`processRows()`, `boradcast()`, kompilacja) nie jest
tknięta, więc `compute_ns` mierzy dokładnie to samo, co w W2–W7.

## Zatrzymanie na W8 — diagnoza i decyzja o zakresie powtórzeń

Wpis z 2026-07-31, po zatrzymaniu Tier B na `W8_Q32_ALGSTRUCT_r03`. Zapisany
**przed** jakimkolwiek ponownym pomiarem, zgodnie z reguła „rozstrzygnięcie
przed pomiarem".

### Co się naprawdę stało

Klient **nie uległ awarii i nie zniknął w ¼ przebiegu**. Zakończył się czysto,
z komunikatem, w ciągu ~100 ms od startu. Dowód wprost z przebiegu, który padł
(`/tmp/xqry.log` na workerze, mtime 12:31, ta sama minuta co wpis `BLAD`):

```
260731 12:31:57.879 ipc_transport.cpp:136 [E] server not found
260731 12:31:57.879 qry.cpp:67 [E] serwer nie odpowiedzial na komende 'get' ... (strumien: mon_000)
```

Trzy obserwacje, które trzeba było odwrócić:

1. **„Zniknął bez komunikatu" to artefakt harnessa, nie objaw.** `xqry` woła
   `setupLoggerMain(argv[0], dual=true)`; console sink to **stdout**, a wszystkie
   ścieżki błędu w `qryLauncher.cpp` używają `std::println` — też stdout. Na
   stderr nie idzie **nic**. Harness uruchamia klienta jako
   `xqry … >/dev/null 2>xqry.err`, więc `xqry.err` ma 0 bajtów **w każdym
   przebiegu**, także w zakończonych sukcesem — sprawdzone na dowodzie
   `ablation_study_06_W8`: pięć przebiegów, wszystkie 0 bajtów, cztery z
   `exit_code 0`. Puste `xqry.err` nigdy nie niosło informacji.
2. **Awaria nie wypada w ¼ przebiegu, tylko przy dołączaniu klienta.** Kontrola
   żywotności stoi `sleep 1` po starcie klienta (`run_ablation_study.sh`). Sonda
   ma 1170 slotów nie dlatego, że klient dotrwał do 20 %, tylko dlatego, że
   `die` ubiło silnik ~2,9 s po starcie przetwarzania.
3. **Mechanizm.** Wątek przetwarzania dostaje SCHED_FIFO 50 (`rtActivate` →
   `sched_setscheduler(0,…)`, więc tylko wątek wołający). Wątek komunikacyjny
   `commandProcessorLoop` powstaje **wcześniej** i zostaje SCHED_OTHER.
   `taskset -c $XR_CPU` przypina oba do jednego rdzenia. Klient ma na odpowiedź
   na `get` budżet 10 prób × 10 ms = **100 ms**. Przy wysyceniu rdzenia przez
   wątek RT wątek komunikacyjny dostaje CPU tylko w oknie throttlingu RT i w
   100 ms się nie mieści.

### Potwierdzenie ilościowe — i zgodność z kalibracją

Z sondy `e1_probe.csv` przebiegu, który padł, wobec slotu 1389 µs (720 Hz):

| komórka | mean `compute_ns` | duty | slotów ponad budżet |
|---|---:|---:|---:|
| `W8_Q32` ALGSTRUCT | 2462 µs | **177 %** (po rozgrzaniu 200–220 %) | 991 / 1170 |
| `W8_Q08` STRUCT | 1002 µs | 72 % | 1299 / 5759 |
| `W8_Q01` ALGSTRUCT | 543 µs | 39 % | 85 / 5759 |

Rampa: do iter ~200 duty rośnie (11 % → 63 % → 200 %), bo napełniają się okna
`mlii@(1,25)`, `bp_out@(1,5)`, `sq_out@(1,30)`; od iter ~200 stoi na ~200 %.

**To nie jest niespodzianka — to potwierdzenie przewidywania kalibracji.**
`calibration.md` zadeklarowała `W8_Q32` = **243 %**, `W8_Q08` = **133 %**,
`W8_Q01` = **61 %**, wprost jako „rodziny ze źródła poza budżetem 50 %", i
zostawiła człowiekowi decyzję, czy mierzyć rodzinę w tym reżimie. Pomiar Tier B
niezależnie odtworzył ten sam rząd wielkości. Reguła „reakcją na niespodziankę
jest nowy katalog wyników" **nie ma tu zastosowania**: warunek był zadeklarowany
przed kampanią, a nie odkryty w jej trakcie.

Czego kalibracja nie przewidziała: że przy takim duty **klient nie zdąży się
dołączyć**. To jest realny defekt kodu i wychodzi poza kampanię — naprawa na
branchu `issue_217-client-unexpected-close`.

### Decyzja o zakresie powtórzeń

Naprawa obejmuje dwie rzeczy, obie **poza mierzoną ścieżką**: (a) błędy klienta
kierowane na stderr zamiast wyłącznie na stdout, (b) wydłużony i oparty na
zegarze budżet oczekiwania klienta na odpowiedź serwera na `get`.

| materiał | czy naprawa go dotyka | decyzja |
|---|---|---|
| Tier A, 3450 kompilacji | nie — mierzy kompilację, klient nie bierze udziału | **zostaje** |
| kalibracja, 258 przebiegów, `rate.json` v3 | slot czytany przez `xqry -t`, ale slot jest własnością kompilacji; naprawa nie rusza parsowania ani odpowiedzi `detail` | **zostaje** |
| Tier B, 540 przebiegów (W2, W3, W4, W5, W7) | nie — `e2e_ns` mierzy pętlę `producer()` klienta i `boradcast()` silnika; naprawa nie dotyka ani jednej, ani drugiej. Zmienia się wyłącznie faza **przed** dołączeniem oraz miejsce, gdzie ląduje komunikat błędu | **zostaje** |

Argument jest jawny i falsyfikowalny: **naprawa zmienia zachowanie klienta
tylko na ścieżkach, które w zaliczonym przebiegu nigdy się nie wykonują.**
Przebieg zaliczony to taki, w którym klient dostał odpowiedź na `get` (więc
wydłużony budżet jest nieużyty) i nie zgłosił błędu (więc sink stderr jest
nieużyty). Gdyby naprawa musiała ruszyć `producer()`, `boradcast()` albo
format rekordu — argument upada i 540 przebiegów wymaga powtórzenia.

**Konsekwencja operacyjna, mimo powyższego:** przypięcie kampanii przesuwa się
na commit z naprawą, więc profile i `xqry` wymagają przebudowy. Kampania ma
zatem **trzy przypięcia**:

| materiał | commit | uzasadnienie |
|---|---|---|
| kalibracja, Tier A, Tier B W2–W7 (540 przebiegów) | `e1e5181` | zmierzone przed naprawą; argument o ważności wyżej |
| Tier B W8 i W9, K6c.5 | **`1bb2d2c`** | „engine rt - issue separation of client thered": szeregowanie wątku IPC poza rdzenie RT (patrz „Trzecie przypięcie" niżej) |

Commit `e1c13bb` (#218, „diagnostyka na stderr i realny budzet czekania") był
**przypięciem pośrednim, na którym nie wykonano żadnego pomiaru**: naprawił
widoczność błędu klienta i jego budżet oczekiwania, ale nie usunął przyczyny
zatrzymania na W8 — patrz „Trzecie przypięcie".

Harness sprawdza pochodzenie klienta (`tests/test_slot_guard.sh` #9, `XQRY_COMMIT`
z `xqry --help` wobec `--code-commit`), więc bez przebudowy `xqry` odmówi startu.
Dla W8, W9 i K6c.5 `--code-commit` to `1bb2d2ce8bec35cd0ab46d168249b706ccbaf303`.

**Zakres pozostały do zmierzenia:** W8 (bez `W8_Q32`, patrz niżej) i W9
(nieuruchomione), potem K6c.5, K6c.6 i K6c.7.

### Trzecie przypięcie: `1bb2d2c` — szeregowanie wątku IPC poza rdzenie RT

Wpis z 2026-07-31, przed pomiarem W8/W9 na tym przypięciu.

Naprawa klienta z `e1c13bb` (stderr + budżet oczekiwania) była **konieczna, ale
niewystarczająca**. Nie tłumaczyła zatrzymania na W8, bo przyczyna nie leży
w kliencie. Wątek komunikacyjny silnika `commandProcessorLoop` powstaje **przed**
`rtActivate`, więc zostaje SCHED_OTHER, a `taskset -c 3` przypina cały proces do
izolowanego rdzenia. Przy duty ≥ 100 % wątek RT nigdy nie oddaje rdzenia i wątek
komunikacyjny **nie jest szeregowany wcale** — żaden budżet klienta tego nie
naprawi.

`1bb2d2c` („engine rt - issue separation of client thered") dodaje
`rtKeepThreadOffRtCpus()`, które daje wątkowi pomocniczemu dopełnienie maski
rdzeni wątku RT. Zweryfikowane A/B na `W8_Q32_ALGSTRUCT_r03`:
**0 → 5020 odebranych wierszy, kod wyjścia klienta 110 → 0**.

**To przypięcie rusza silnik, nie tylko klienta**, więc argument „naprawa jest
poza mierzoną ścieżką" z sekcji wyżej **nie przenosi się automatycznie** na
`1bb2d2c`. Dlatego wykonano osobne badanie higieniczne:
`results_20260731_hygiene217/` (branch `experiment/20260731_hygiene217`, commit
`108b69c`). Werdykt: **brak wpływu**. 240 przebiegów; margines równoważności
±0,02; `W2_Q32` Δ = −0,0077 CI95 (−0,0107; −0,0049), `W3_d3` Δ = −0,0126 CI95
(−0,0150; −0,0097). Skutek zapisany **przed** pomiarem: 540 przebiegów Tier B
(W2, W3, W4, W5, W7) na `e1e5181` **pozostaje ważne**.

**Znany bias aparatury.** Efekt higieniczny, choć w granicach równoważności, nie
zawiera zera i oba profile poszły w przeciwne strony: na `1bb2d2c` iloraz
`ALGSTRUCT/STRUCT` wychodzi **0,8–1,3 % niżej** niż na `e1c13bb`. Przy zestawianiu
komórek W8/W9 (mierzonych na `1bb2d2c`) obok W2–W7 (mierzonych na `e1e5181`) tyle
różnicy może pochodzić z aparatury, nie z optymalizacji. Progu istotności
praktycznej 10 % to nie przekracza, ale werdykt kampanii musi ten bias odnotować
przy każdej komórce W8/W9 klasy (A) blisko granicy.

### Czy klient może zniknąć po cichu W TRAKCIE przebiegu — sprawdzone, nie może

Pytanie postawione przy naprawie, bo gdyby odpowiedź brzmiała „tak", W8 przy
duty 200 % byłaby na nie najbardziej narażona, a skutek byłby niewidoczny.
Łańcuch, który trzeba było wykluczyć: klient nie nadąża → kolejka odpowiedzi się
przepełnia → `boradcast()` po nieudanym `try_send` usuwa kolejkę i wykreśla
klienta z `id2StreamName_Relation` → od tego miejsca `printRowValue` nie jest
wołane (formatowanie jest leniwe), więc `e2e_ns` mierzy pustą pętlę.

Ten łańcuch byłby cichy na każdym ogniwie: ostrzeżenie `queue erased on timeout`
to `SPDLOG_WARN`, a kampania buduje Release, gdzie
`SPDLOG_ACTIVE_LEVEL=SPDLOG_LEVEL_ERROR` **wycina WARN na etapie kompilacji**;
`qry::select` po timeoucie braku danych zwraca `ok`, bo `rendered > 0`, więc
klient wychodzi zerem; `finalize_required_process` przyjmuje proces, który sam
zakończył się zerem; a `validate_probe_csv` nic nie zauważa, bo **sonda pisze
wiersz w każdym slocie niezależnie od tego, czy jakikolwiek klient istnieje**
(`fprintf` stoi po `boradcast()`, bez związku z liczbą subskrybentów).

Łańcuch jest jednak **nieosiągalny przy tej parametryzacji**. Kolejka odpowiedzi
powstaje z pojemnością `(1/interwał) × ipc.queue_buffer_seconds`, czyli dla
`mon_000` **720 × 10 = 7200 elementów**, podczas gdy cały przebieg W8 to **5760
slotów**. Bufor 10 s wobec przebiegu 8 s jest własnością konstrukcji, nie
przypadkiem, i ta sama nierówność zachodzi w pozostałych rodzinach (W2: 1800
wobec 1440; W3_d3: 4050 wobec 3240). Klient może więc dowolnie zostawać w tyle
i nie zostanie odrzucony ani razu.

Wniosek dla metryki: opóźnienie klienta w czytaniu nie zanieczyszcza `e2e_ns`,
bo mierzoną wielkością jest emisja **do kolejki**, zgodnie z R10 — a emisja
zachodzi zawsze, dopóki klient jest zarejestrowany. Rejestracja to dokładnie ten
krok, który psuł się przed naprawą issue_217.

### `W8_Q32` wykluczona z Tier B — decyzja, nie korekta

Rozstrzygnięcie zapadło (człowiek, 2026-07-31), zapisane **przed** pomiarem W8.
Nawet z dołączonym klientem `W8_Q32` przy 720 Hz mierzy **przeciążenie**, a nie
opóźnienie emisji: duty slotu 212 % po rozgrzaniu, 243 % w p99 przy kalibracji
(`rate.json`: p99 3376 µs / slot 1389 µs), silnik nie nadąża z slotem. Komórka
nie mierzy wtedy metryki głównej, tylko wysycenie rdzenia.

**`W8_Q32` zostaje wykluczona z Tier B.** To jest **wynik**, nie korekta
parametru: warunek był zadeklarowany w `calibration.md` przed kampanią, decyzja
świadomie odłożona i teraz podjęta. Wykluczenie zapisane jest w `rate.json` pod
osobnym kluczem `decision_excluded_cases` (odrębnym od `excluded_cases`, które
należy do wykluczeń kalibracyjnych drabinki): `run_ablation_study.sh` sumuje oba
klucze do skipu w planie, ale raportuje je osobnymi etykietami, a `analyze.py`
nie miesza wykluczenia decyzyjnego z tabelą kalibracyjną. Nie jest to ręczna
edycja `matrix.tsv` w trakcie kampanii. `W8_Q08` (133 % w p99, 72 % średnio)
**zostaje** — jest wysoka, ale klient dołącza i emisja jest mierzalna.

Wykluczenie dotyczy **wyłącznie Tier B (latencja)**. K6c.5 (punkt saturacji)
mierzy właśnie udział slotów ponad budżetem i `W8_Q32` jest tam komórką celową,
nie wykluczoną.

## Czego ta kampania świadomie nie mierzy

Bez zmian względem v2:

1. **Ablacji infrastruktury z §9.2** (persistence/metadata/IPC włączone
   i wyłączone, integer vs rational scheduling).
2. **Pełnego application E2E.** Sonda kończy się na emisji do kolejki klienta
   (`REQUIREMENTS.md` R10). Metryka nazywa się `queue-emission latency`.
3. **Progu 480/510 Hz z powtórzeniami ani soak testu** — to K11.
4. **Skalowania liczby klientów z `Q`.** Jeden klient `xqry` na przebieg.
5. **Kryterium every-slot jako sufitu publikacyjnego.**

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

Bez zmian względem v1 i v2.

| | Rodzina | Konstrukcja | Rola w K6c |
|---|---|---|---|
| W1 | pojedyncza instancja reguły | `(A>2)#(B>1)` | tylko Tier A |
| W2 | `Q` zapytań ze wspólnym `phi(A,B)` | `Q` × `(A>2)#(B>1)` | rdzeń: `r1 = Q`, `net = −1` |
| W3 | głębokość wspólnego podplanu | zagnieżdżone `((phi>2)#(S>1))`, `d = 1,2,3` | jedyna rodzina, w której `net` rośnie (−1, −2, −3) |
| W4 | kosztowny operator za wspólnym podplanem | `phi → projekcja → @(1,30) → .avg` | koszt **stały co-slot** |
| W5 | **kontrola negatywna** | `Q` × `A_j#B_j`, bez przesunięć | `net = 0`; **musi wyjść neutralnie** |
| W6 | near-miss | `(A>1)#(B>1)`, `i·Δ_A ≠ k·Δ_B` | tylko Tier A |
| W7 | materializacja blokuje rewrite | przesunięcia jako strumienie publiczne | `net = 0`; **musi wyjść neutralnie** |
| W8 | **umotywowana zewnętrznie** | potok Pan-Tompkins `rec205` + `Q` monitorów | zamyka G7; rate 360 Hz ze źródła |
| W9 | **R2-shaped** | `Q` publicznych `SELECT` z tym samym kosztownym programem pól, naprzemiennie `FROM a+b` i `FROM b+a` | jedyna rodzina, w której odpala R2 |

`Q ∈ {1, 2, 4, 8, 16, 32}` (W3: `d ∈ {1,2,3}` przy `Q = 8`).

### Co już wiadomo o W4 i co z tym robimy

Bez zmian względem v2. Kalibracja v1 ustaliła, że w `W4_Q32` profil `STRUCT`
**nie jest szybszy** od `OFF` (35,59 vs 34,77 ms `p99`): koszt jest zdominowany
przez **32 niewspółdzielone okna** `@(1,30)`, a nie przez dedup. Kalibracja v2
potwierdziła to niezależnie i wykluczyła `W4_Q32` z Tier B (35 291 µs wobec
budżetu 33 333 µs, wymaga `f_φ ≤ 14,17 Hz`). W4 zostaje w macierzy bez zmiany
konstrukcji: zmiana rodziny po zobaczeniu danych byłaby dokładnie tym, czego
zakazuje R3. To, czy `W4_Q32` wypadnie także w v3, rozstrzyga pomiar v3 — liczby
z v2 nie są tu przenoszone, bo slot się zmienił.

## Rate pomiarowy — reguła zamrożona, wartości wyznaczane

### Drabina generatora

`s` jest mnożnikiem częstotliwości **źródeł** generowanych przez `generate.py`.
`f_φ` w tej tabeli to rate przeplotu **dwóch źródeł** — jest własnością
generatora, nie strumienia mierzonego, i **nie jest** slotem żadnej komórki.

| `s` | `f_A` | `f_B` | `f_φ` generatora |
|---:|---:|---:|---:|
| 36 | 360 Hz | 180 Hz | 540 Hz |
| 24 | 240 Hz | 120 Hz | 360 Hz |
| 12 | 120 Hz | 60 Hz | 180 Hz |
| 6 | 60 Hz | 30 Hz | 90 Hz |
| 3 | 30 Hz | 15 Hz | 45 Hz |
| 1 | 10 Hz | 5 Hz | 15 Hz |

### Slot i budżet przebiegu

> `slot(komórka, s)` = interwał strumienia z kolumny `client_stream`,
> **odczytany z silnika** (`xqry -t`, pole `delta`) dla workloadu
> wygenerowanego przy tym `s`.

> `slots(komórka) = clamp(round(8 s / slot(komórka, s_wybrane)), 400, 6000)`

Budżet jest więc różny dla komórek tej samej rodziny — i taki był zamiar
zamrożonego wzoru „8 sekund pracy" od v2. Metryka główna jest **na slot**,
a porównanie zachodzi zawsze **w obrębie komórki**, gdzie liczba slotów jest
identyczna dla wszystkich profili i powtórzeń; różna liczba slotów między
komórkami nie wchodzi więc do żadnego porównania.

Pierwsze **5 %** slotów jest odrzucane w analizie jako transjent startowy.
Odrzucenie jest zapisane w kodzie analizy, nie wybierane po zobaczeniu danych.

### Reguła wyboru rate'u (zamrożona)

Dla każdej rodziny podlegającej drabinie:

> `rate(rodzina)` = **największe** `s` z drabiny, przy którym **każda
> niewykluczona komórka** tej rodziny spełnia
> `p99(compute_ns) ≤ 0,5 · slot(komórka, s)` **w najgorszym zmierzonym
> profilu**.

> Komórka, która nie spełnia tego warunku nawet przy `s = 1`, jest
> **wykluczona z Tier B** i nie ogranicza rate'u swojej rodziny. Wykluczenie
> jest raportowane w `results/rate.json` i `results/calibration.md` wraz
> z `p99`, slotem, budżetem i **wymaganą częstotliwością strumienia**.

> Jeżeli wykluczone zostaną **wszystkie** komórki rodziny, rodzina wypada
> z Tier B w całości i jest tak raportowana.

Powód warunku 50 %: porównanie profili musi zachodzić w reżimie
**nienasyconym**; w saturacji `compute_ns` przestaje mierzyć koszt planu,
a zaczyna mierzyć backlog. Saturacja jest osobnym, jawnym punktem kampanii
(K6c.5), nie tłem pozostałych pomiarów.

### Komórki i profile kalibracyjne (zamrożone)

Kalibracja obejmuje **wszystkie komórki Tier B**: 11 komórek rodzin
podlegających drabinie (W2, W3, W4, W5, W7, W9) plus 3 komórki W8, po
`{OFF, STRUCT}` i **3 powtórzenia**. Bierzemy **maksimum** `p99` z powtórzeń
i profili.

Rozszerzenie o W8 względem v2 jest wymuszone przez zmianę v3: slot W8 też
pochodzi teraz z silnika, a nie z deklaracji źródła, więc trzeba go zmierzyć.
Przy okazji mierzony jest jej `p99` — patrz niżej.

Przebieg kalibracyjny ma włączone **te same trzy instrumenty** co przebieg
Tier B (`RDB_BENCH_CSV`, `RDB_BENCH_PLAN`, `RDB_BENCH_MATERIALIZE`). Liczniki
planu i materializacji z tych przebiegów trafiają do `rate.json` i są wejściem
modelu kosztu slotu; bez nich komórka wykluczona z Tier B nie miałaby żadnego
wektora cech.

`{OFF, STRUCT}` to profile **bez przepisywania algebraicznego**, czyli
z największą pracą na slot; profile z R1/R2 mogą pracę wyłącznie usunąć.
Kalibracja mierzy więc górne oszacowanie. **Kontrola tego założenia** jest
raportowana po kampanii: `analyze.py` podaje liczbę komórek Tier B, w których
jakikolwiek profil przekroczył `0,5 · slot` **swojej komórki** w danych
właściwych. Jest to kontrola **raportowana**, nie unieważniająca.

### W8 nie podlega drabinie

Rate `W8` wynika z deklaracji źródła `rec205` (`1/360`) i jest kotwicą
porównywalności z §7 artykułu; drabina go nie dotyczy. Workloady W8 generowane
są przy `s = 6`, którego generator dla tej rodziny nie używa — mnożnik jest
zapisany w `rate.json`, żeby kalibracja i Tier B wytwarzały te same pliki.

Slot W8 mierzymy z silnika tak samo jak każdy inny; wynosi on 1/720, nie 1/360,
bo `mon_000` powstaje z przeplotu. Jeżeli komórka W8 narusza regułę 50 %, jej
cele **nie są zwalniane** i rate **nie jest zmieniany** — należy do źródła, nie
do nas. Fakt jest raportowany w `calibration.md` **przed** kampanią; decyzja, czy
mierzyć rodzinę w tym reżimie, należy do człowieka.

**Wyniki kalibracji nie są wynikami kampanii.** Służą wyłącznie ustaleniu
rate'ów i budżetów, są zapisywane w `results/calibration.md` oraz
`results/rate.json` i tam zostają.

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
Zmiana v3 go nie dotyka: slot nie wchodzi do metryk kompilacji.

### Tier B — metryki runtime

14 przypadków × 4 profile × **15 powtórzeń** = 840 przebiegów, **minus komórki
wykluczone przez kalibrację** oraz `W8_Q32` wykluczona decyzją (patrz „`W8_Q32`
wykluczona z Tier B"). Liczba faktycznie wykonanych przebiegów jest raportowana
i porównywana z planem.

| Przypadki | Profile | Rate | Slot |
|---|---|---|---|
| `W2_Q01`, `W2_Q08`, `W2_Q32` | `OFF`, `STRUCT`, `STRUCT+R1`, `ALGSTRUCT` | `rate(W2)` | z silnika, per komórka |
| `W3_d1`, `W3_d3` | `OFF`, `STRUCT`, `STRUCT+R1`, `ALGSTRUCT` | `rate(W3)` | z silnika, per komórka |
| `W4_Q08`, `W4_Q32` | `OFF`, `STRUCT`, `STRUCT+R1`, `ALGSTRUCT` | `rate(W4)` | z silnika, per komórka |
| `W5_Q32` | `OFF`, `STRUCT`, `STRUCT+R1`, `ALGSTRUCT` | `rate(W5)` | z silnika, per komórka |
| `W7_Q32` | `OFF`, `STRUCT`, `STRUCT+R1`, `ALGSTRUCT` | `rate(W7)` | z silnika, per komórka |
| `W8_Q01`, `W8_Q08` (`W8_Q32` **wykluczona z Tier B**) | `OFF`, `STRUCT`, `STRUCT+R1`, `ALGSTRUCT` | 360 Hz (źródło) | z silnika, per komórka |
| `W9_Q08`, `W9_Q32` | `OFF`, `STRUCT`, `STRUCT+R2`, `ALGSTRUCT` | `rate(W9)` | z silnika, per komórka |

Jedno **badanie** (`study_NN` w rozumieniu R8) = jedna rodzina; wewnątrz
badania kolejność wszystkich trójek (przypadek, profil, powtórzenie) jest
losowana, żeby dryf termiczny i częstotliwościowy nie sprzęgł się z profilem.
Reboot workera następuje **między** badaniami. Siedem badań: W2, W3, W4, W5,
W7, W8, W9.

### K6c.5 — punkt saturacji

`W8_Q32` × `{STRUCT, ALGSTRUCT}` × `{360, 480, 540}` Hz źródła × 5 powtórzeń.
Metryka: udział slotów z `compute_ns > slot`, gdzie `slot` jest interwałem
strumienia `mon_000` **wg silnika** przy danym rate źródła. Pytanie: czy
`ALGSTRUCT` utrzymuje rate, którego `STRUCT` nie utrzymuje.

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

## Reguła decyzyjna — zamrożona, bez zmian względem v1 i v2

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
   wypisywane imiennie.
3. **Środowisko nie trzymało reżimu.** Naruszenie któregokolwiek warunku R7,
   brak wątku `SCHED_FIFO` 50, governor inny niż `performance`, throttling
   termiczny w trakcie badania.
4. **Liczniki nie zgadzają się z K5.** Spełnienie tego warunku jest przeniesione
   przez referencję z v1 — patrz niżej.
5. **Defekt silnika.** Zatrzymanie przed werdyktem, `issue_NNN`, badanie
   higieniczne, nowy katalog.
6. **Rate albo slot nieidentyczny w obrębie komórki.** Jeżeli w obrębie jednej
   komórki (przypadek, profil, 15 powtórzeń) albo między profilami tego samego
   przypadku wystąpi więcej niż jedna wartość `scale`, `f_phi_hz` **lub
   `stream_hz`**, kampania jest nieważna. Rozszerzenie o `stream_hz` jest zmianą
   v3: `scale` sam nie wyznacza slotu, więc kontrola v2 przepuściłaby porównanie
   profili przy różnym slocie. Kontrola jest wykonywana przez `analyze.py` na
   `runs.csv` i ma regresję w `tests/test_rate_guard.sh`.

### Reguła zliczania

Wniosek metodologiczny z K5h i K5i: **milczenie instrumentu wygląda jak
sukces**. Dlatego każde porównanie w tej kampanii raportuje **liczbę**
porównanych rzeczy, a zero porównanych rzeczy jest **błędem**, nie zgodnością.
Dotyczy to porównań artefaktów, liczników, komórek macierzy, replikacji
bootstrapu, liczby przebiegów kalibracyjnych oraz liczby komórek, na których
wyznaczono rate każdej rodziny.

Kontrola czystości repozytorium kodu (R2) obejmuje pliki ignorowane
(`code_tree_fingerprint`, `require_input_dirs_pristine` w `lib/common.sh`).
Dane wejściowe EKG są **kopiowane** do `/dev/shm`, nie symlinkowane.

## Wyniki przeniesione przez referencję z `results_20260730_K6`

Obie poniższe pozycje są **niezależne od rate'u i od slotu**, powstały przed
jakimkolwiek pomiarem czasu i **nie są powtarzane**:

| Pozycja | Plik | Zawartość |
|---|---|---|
| kontrola wejściowa liczników | `results_20260730_K6/results/counters.md`, `counters.json` | 230 kompilacji, 46 porównań, **0 niezgodności** |
| macierz funkcjonalna | `results_20260730_K6/results/functional_matrix.md` | **45/45** |

Warunek unieważniający nr 4 jest zatem spełniony na mocy tych plików.

**Addendum W9 z v1 również obowiązuje** (`results_20260730_K6/README.md`,
sekcja „Predykcja dla W9 zawiodła, mechanizm się potwierdził"): kryterium
wejściowe W9 jest mechanizmowe (`exec_STRUCT = 2`, `exec_ALGSTRUCT = 1`,
`r2 ≥ 1`), nie węzłowe.

### Czego NIE przenosimy z K6b

Nic z pomiarów czasowych. `rate.json` i `calibration.md` z v2 są **nieważne**,
bo wyznaczono je wobec złego slotu; `ablation/study_01_W2` (180 przebiegów)
jest niekompletnym Tier B (1 z 7) i nie wchodzi do żadnej tabeli. K6b zostaje
zapisem zatrzymanej kampanii i dowodem defektu klienta.

## Produkt uboczny: model kosztu slotu (K20 etap 1)

**Nie zmienia reguły wyboru rate'u.** Model jest dopasowywany **po** kampanii,
na danych, które i tak powstają, bez ani jednego dodatkowego przebiegu
pomiarowego i bez zmian w silniku.

- **Wejście:** pary (komórka, rate, `p99`) z kalibracji oraz liczniki Tier A
  (`PLAN bench` — tokeny, `PLAN capacity`, `MATERIALIZED` — materializacje
  i bajty).
- **Postać:** `koszt_slotu ≈ a · tokeny + b · bajty_trwałe + c · bajty_pamięciowe`.
- **Procedura:** dopasowanie na `{W2, W3, W5, W7}`, predykcja na `{W4, W9}`.
  Podział jest zamrożony **tutaj**. W4 jest w zbiorze testowym celowo — to ona
  łamie model liczący same tokeny.
- **Produkt:** `results/cost_model.md` z tabelą przewidziane vs zmierzone
  i jawnie podanym błędem względnym per rodzina.

**Model musi ważyć materializacje osobno od tokenów.** `W4_Q32` to ~33 µs na
element okna — koszt siedzi w zapisach przez `storage`, nie w arytmetyce.
Współczynnik ujemny jest objawem współliniowości i jest raportowany jako
ostrzeżenie, nie chowany.

Etap drugi K20 — kontrola dopuszczenia planu wewnątrz `xretractor` — jest
zmianą w silniku i **nie należy do K6c**.

## Kolejność wykonania

| Krok | Zawartość | Gdzie |
|---|---|---|
| K6c.1 | predeklaracja v3 (ten plik) + kod, commit **przed** danymi | nadzorca |
| K6c.2 | przebudowa pięciu profili na `e1e5181` | worker |
| K6c.0 | kalibracja: slot z silnika, rate per rodzina, budżet per komórka | worker |
| K6c.3 | Tier A przy `s = 6` | worker |
| K6c.4 | Tier B, siedem badań, reboot między badaniami | worker |
| K6c.5 | punkt saturacji | worker |
| K6c.6 | `analyze.py` — werdykt | nadzorca |
| K6c.7 | `cost_model.py` — model kosztu slotu (K20 etap 1) | nadzorca |

## Zgodność z REQUIREMENTS.md

| Wymaganie | Zastosowanie |
|---|---|
| R1 dwa repozytoria | kod `retractordb` @ `master`: `e1e5181` dla kalibracji, Tier A i Tier B W2–W7; `1bb2d2c` dla Tier B W8, W9 i K6c.5 (patrz „Zatrzymanie na W8" oraz „Trzecie przypięcie"). Wyniki `rdb-experiment` @ `experiment/20260730_K6` |
| R2 zakaz zapisu do repo kodu | dane robocze i artefakty w `/dev/shm`; dane EKG kopiowane; `code_tree_fingerprint` + `require_input_dirs_pristine` przed i po |
| R3 katalog docelowy | `results_20260730_K6c/`, bez rotacji; `results_20260730_K6/` i `_K6b/` zamknięte i nietknięte |
| R4 branch i commity | commity i push w trakcie realizacji dozwolone przez człowieka; jeden commit, `--amend` + `push --force-with-lease` |
| R5 warunki wejściowe | oba repozytoria czyste, commit kodu przypięty, `/dev/shm` = tmpfs, walidacja builda i RT |
| R6 build pomiarowy | pięć profili Release z `RDB_BENCH_PROBE=ON` w `build/K6-<slug>`, przebudowane na `e1e5181`, a dla W8/W9 i K6c.5 **ponownie na `1bb2d2c`** |
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
   z `results_20260730_K6`, zamiast powtórzenia.
3. **Przypięcie silnika przesunięte na `e1e5181`** wobec `bb3a521` z v2 — powód
   i zakres zmiany opisane w sekcji „Silnik jest zamrożony". Badanie higieniczne
   wykonane, werdykt „brak wpływu": `results_20260731_hygiene/`, `c836a60`.
4. **R14, `raw.tar.gz` każdego badania poza git.** Surowy tar rodzin o wysokim
   rate/slotach przekracza limit GitHub 100 MB (`W8` = 155 MB), co zablokowało
   push W8. Polityka (decyzja człowieka 2026-07-31): **żaden `raw.tar.gz` nie
   wchodzi do git**, niezależnie od rozmiaru i kampanii. W git zostaje
   **indeks SHA-256 per plik** jako audyt integralności; sam tar jest
   przenoszony na hosta **obok indeksu, pod unikalną nazwą**
   `<kampania>_<badanie>_raw.tar.gz` (np. `results_20260730_K6c_study_06_W8_raw.tar.gz`),
   z weryfikacją SHA-256 worker↔host. Indeks nosi ten sam rdzeń nazwy co archiwum
   (`<kampania>_<badanie>_raw.index.tsv`), zgodnie z tym, jak wywodzi ją
   `lib/artifacts.py`; kontrola `tests/test_artifacts.sh` tego pilnuje. `.gitignore` kampanio-niezależny:
   `*raw.tar.gz` — łapie bezimienny tar workera i nazwaną kopię hosta w każdej
   przyszłej kampanii (harness `git add` respektuje gitignore, bez zmian w kodzie).
   Małe tary `W2`–`W7` (2–9 MB) zostały w git wcześniej i tam zostają (historia).
   Integralność surowych danych nadal zweryfikowana indeksem SHA-256, zgodnie
   z intencją R14.
