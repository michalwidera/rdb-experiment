# K24f — predeklaracja kampanii dla reguły okna rekordowego

**Data zamrożenia:** 2026-09-12, **przed** uruchomieniem kampanii
**Silnik:** `retractordb` gałąź `master`, commit **`098e531`**; zawartość `src/`
identyczna z `40d9bbb` (ostatni commit ruszający silnik)
**Poprzednik:** [`results_20260818_K24e`](../results_20260818_K24e/) (dziewięć klas
dokładnych dla ogona i origin, silnik `e2a61ff`)
**Plan pracy:** `paper-arXiv/usecases/engine_on_k24f.md`
**Aparatura:** `retractordb` `test/research_gate/h10/`, commit `3511897`

Dokument zamyka twierdzenie, kryteria i ziarna przed przebiegiem. Zmiana
którejkolwiek pozycji po tej dacie unieważnia przebieg i wymaga nowej
predeklaracji.

---

## 1. Dlaczego ten przebieg powstał

Po K24e `compiler::computeLogicalOrigin()` dostał regułę, której **żadna kampania
ani bramka nie zmierzyła i zmierzyć nie mogła** — okno rekordowe w liście `SELECT`
(`src/retractor/lib/compiler.cpp`, gałąź `q.lProgram.size() == 1`):

```cpp
if (const auto width = windowWidthOf(q, windowError); width.has_value()) result = o1 + *width - 1;
```

Generator korpusu K24e wypisywał wyłącznie `SELECT * STREAM <n> FROM <wyrażenie>`,
a `windowWidthOf()` szuka tokenów `WINDOW_*` w programach pól listy `SELECT` —
których `SELECT *` nie ma ani jednego. Bramka świeciła na zielono, bo nie miała
jak zaświecić inaczej. Nie było wiadomo, czy reguła jest błędna — było wiadomo,
że **nic jej nie sprawdziło**.

Stan był pilniejszy, niż wyglądał: reguła stoi już w snapshocie przypiętym jako
domyślny silnik odtworzeniowy pakietu artefaktu (`8aa4ee2f…`), czyli pakiet wydaje
**dziś** regułę początku logicznego, której nikt nie zmierzył.

**K24f nie jest powtórką K24e.** Rachunek ogona startowego jest tym samym kodem,
który zmierzyła K24e; jego powtórka nie odpowiedziałaby na żadne otwarte pytanie.
K24f nie jest też kampanią członu (b) — ten porównuje regułę lokalną z oracle'em,
nie z silnikiem, i K24e ma go potwierdzonego (2310/2310).

## 2. Co jest twierdzone

**H10a-win (reguła okna rekordowego).** Dla każdego poprawnego planu RQL, w którym
lista `SELECT` zawiera agregat okna rekordowego, **początek logiczny** wyznaczany
przez silnik jest **równy** granicy z modelu zdarzeniowego, w konwencji
dostępności **C1** (nieostrej).

Rachunek badany w tym przebiegu:

```
  O = O_src + W - 1,   W = najszersze okno listy SELECT
```

Model zdarzeniowy wyprowadza tę wielkość **niezależnie**, z definicji operatora:
okno jest przesuwne i stemplowane końcem przedziału, więc rekord `n` obejmuje
rekordy źródła `n-(W-1) … n`, a istnieje wtedy, gdy najstarsza z tych zależności
istnieje. W `oracle/model.py` nie ma ani `O_src + W - 1`, ani żadnej innej postaci
zamkniętej — origin wychodzi ze skanu po liście zależności.

**Twierdzenie jest wąskie celowo.** K24f nie twierdzi niczego o całym początku
logicznym: pozostałe dziewięć klas ma werdykt z K24e i tu są **kontrolą braku
regresji**, nie przedmiotem twierdzenia. Konwencja C2 pozostaje kolumną
wrażliwości i nie jest przedmiotem twierdzenia.

## 3. Predeklarowane przewidywania

Zapisane **przed** uruchomieniem. Każde falsyfikowalne.

| # | Przewidywanie | Falsyfikuje je |
|---|---|---|
| **P1** | Początek logiczny klasy `WINDOW`: **reżim dokładny**, atrybucja izolowana, **oba** ziarna | jedna niezgodność w klasie `WINDOW` |
| **P2** | **Ogon** klasy `WINDOW`: reżim dokładny, a wartość **równa ogonowi producenta** — okno nie dokłada do ogona ani go nie zeruje | jeden węzeł `WINDOW`, którego ogon różni się od ogona producenta przeliczonego przez takt |
| **P3** | Pozostałe **dziewięć** klas: reżim dokładny dla ogona i dla origin, bez zmian wobec K24e | jedna niezgodność w klasie innej niż `WINDOW` |
| **P4** | Zero klas w reżimie **zaniżającym**, dla ogona i dla origin | jeden węzeł zaniżony |
| **P5** | Bramka odwzorowania: zero rozbieżności treści na podpróbie, w obu skalach | jedna rozbieżność treści albo rozjazd między skalami |
| **P6** | Populacja `WINDOW` co najmniej **500 węzłów** na każdym ziarnie | mniejsza populacja — przebieg traci moc i jest raportowany jako `NIEOCENIALNY` w tej klasie, nie jako wsparcie |

**P2 jest przewidywaniem nowym wobec wszystkich kampanii K24.** Uzasadnienie:
`computeStartupLatency()` o oknie nie wie — `windowWidthOf()` jest wołane wyłącznie
z `resolveStreamIntervals()`, `computeLogicalOrigin()` i
`computeRequiredCapacities()`. Jeżeli to jest prawdą rachunku, a nie przypadkiem,
to ogon węzła okna musi być ogonem producenta, bo interwały są równe. Rozdzielenie
„okno rusza wyłącznie origin" jest treścią reguły i P2 jest jedynym miejscem,
w którym to twierdzenie jest sprawdzalne wprost.

**P6 jest przewidywaniem o mocy, nie o silniku.** Strata `WINDOW` wchodzi
rotacyjnie jak każda inna, a węzeł okna jest liściem, więc plan zawiera go zwykle
raz. Bez progu populacji zielony wynik w tej klasie mógłby pochodzić z kilkunastu
węzłów i nie znaczyłby nic.

## 4. Czego ten przebieg nie twierdzi

* **Nie jest testem prospektywnym reguły.** Aparatura powstała przed zamrożeniem
  tej predeklaracji i była uruchamiana na ziarnie **spalonym** `20260803`; reguła
  silnika była przy jej budowie znana i zmierzona na siedmiu planach ręcznych.
  Predeklarowane są **ziarna, kryteria i przewidywania**, nie hipoteza. Status do
  raportowania dosłownie: **potwierdzenie poza próbą na ziarnach nieużytych przy
  budowie aparatury**.
* Nic o wydajności — badanie jest compile-only, bez workera i bez pomiaru czasu.
* Nic o progu czasowym H9 — inna kampania, inny sprzęt, ~48 h na pi400.
* Nic o członie (b) H10 — potwierdzony w K24e, nie ma czego przeliczać.
* Nic o kontrakcie typu `tan`/`log`/`log2` nad `INTEGER` ani o `Sqrt` nad
  `INTEGER` — wada otwarta, poza zakresem korpusu (patrz `PIN.md`).

## 5. Korpus i ziarna

| Pozycja | Wartość |
|---|---|
| generator | `generator.py` po `3511897`, strata `WINDOW` **dołożona** |
| zestaw strat | `STRATA_WITH_WINDOW` — **15** strat, wywołanie jawne `--with-window` |
| liczność | 10 010 planów |
| planów na stratę | 667 (pięć pierwszych strat po 668) |
| **ziarno główne** | **`20260912`** |
| **ziarno potwierdzające (out-of-sample)** | **`20260913`** |
| stratyfikacja, głębokość, zbiór taktów | bez zmian wobec K24e |

**To jest INNY korpus, nie poszerzenie zamrożonego.** Strata przydzielana jest
rotacyjnie po indeksie planu, a każdy plan ciągnie z tego samego `random.Random`,
więc piętnasta strata przesuwa wszystkie losowania. Korpus K24e został **bajtowo
nietknięty** i to jest sprawdzone, nie założone: suma SHA-256 całego korpusu
10 010 planów zgadza się przed i po zmianie na ziarnach `20260804` i `20260807`,
a `ninja test_gate` daje dalej 9/9 klas dokładnych na obu.

Liczność na stratę spadła z 715 (14 strat) na 667 (15 strat) — nadal powyżej
predeklarowanego progu 500 z K24.

**Oba ziarna kampanii są nowe i nieużyte.** Sprawdzone: ani `20260912`, ani
`20260913` nie występuje w żadnym pliku `rdb-experiment`, `retractordb/test/research_gate`,
`paper-arXiv` ani `rdb-artifact`. Ziarna zapisane tutaj są jedynymi dopuszczonymi;
wynik negatywny na którymkolwiek **jest wynikiem negatywnym**. Nie wolno próbować
kolejnych ziaren i raportować najlepszego.

**Ziarna spalone**, których nie wolno użyć: `20260803` (budowa aparatury K24f),
`20260804`, `20260805`, `20260806`, `20260807`, `20260818`, `20260819`
(unieważnione), `20260820`.

## 6. Kryteria

**Kryterium główne (per klasa, nigdy agregatem).** Na obu ziarnach, w atrybucji
izolowanej i w C1: zgodność 100% w klasie oznacza reżim „dokładna"; **jedna
niezgodność falsyfikuje** w tej klasie. Osobne tabele dla ogona i dla początku
logicznego.

**Kryterium bezpieczeństwa.** Zero klas w reżimie **zaniżającym**, osobno dla
ogona i dla origin. Reżim zaniżający jest **defektem poprawności zawsze**, także
gdyby odniesienie już go miało: rekord wychodzi, zanim jego zależności są
określone.

**Kryterium zestawu klas.** Werdykt musi wymienić **dokładnie dziesięć** klas.
Klasa brakująca znaczy, że próba jej nie pokryła; klasa nadmiarowa — że generator
albo silnik nazywa coś inaczej. Oba przypadki to **BRAK WERDYKTU**, nigdy ciche
orzeczenie o dziewięciu z dziesięciu.

**Kryterium end-to-end.** Bramka odwzorowania na podpróbie obu ziaren, w dwóch
skalach: zero rozbieżności treści, zero awarii. Plan poza budżetem czasu jest
osobną kategorią i nie jest znaleziskiem.

**Kryterium mocy.** Populacja `WINDOW` >= 500 węzłów na ziarnie (P6).

## 7. Bramki aparatury, które muszą przejść przed kampanią

| Bramka | Warunek |
|---|---|
| `tests/test_independence.py` | oracle nie importuje repliki i nie zawiera nazw rachunku silnika |
| `tests/test_oracle.py` | 100% zgodności z przypadkami ręcznymi (ogon C1 i C2 oraz origin) |
| `tests/test_mutants.py` | 100% wykrycia zamrożonych mutantów, osobno dla rodziny ogona i origin |
| `tests/test_closedform.py` | replika zgodna ze zrzutem planu silnika co do ogona i origin |
| `tests/test_phase_forms.py` | postacie fazowe `-`, `Θ`, `~Θ` dla q do 12 |
| `decision_rule.py --selftest` | procedura decyzyjna odrzuca korpus uszkodzony w każdy przewidziany sposób |

Zestaw mutantów rozszerzono o **trzy** pozycje celujące w nową regułę:
`window_drop_span` (origin zapomina o rozpiętości — stan sprzed reguły),
`window_origin_plus_one` i `window_origin_minus_one` (błąd o jeden w obie strony).
Bez nich poziom `test_mutants` nie orzekałby o regule okna: przeszedłby na samych
mutantach starszych klas. Korpus ręczny dostał **siedem** nowych przypadków,
w tym okno nad przeplotem o niezerowym ogonie i okno nad oknem — bez nich mutanty
okna byłyby niewykrywalne, bo `test_mutants` biegnie na przypadkach ręcznych,
nie na korpusie losowym.

## 8. Reguła zatrzymania

Błąd aparatury **zatrzymuje iterację** i nie jest wynikiem o silniku. Precedens:
K24e `STOP.md` — sufit `ORIGIN_LIMIT` w `oracle/model.py` strzelił na ziarnie
spoza bramki i przebieg został zatrzymany, a nie zaraportowany jako znalezisko.

Zatrzymaniem jest w szczególności: plan odrzucony przez kompilator (generator ma
prawo produkować wyłącznie plany poprawne), awaria oracle'a, rozjazd między
skalami w bramce odwzorowania, zestaw klas różny od dziesięciu.

**Procedurę decyzyjną uruchamia się RAZ.** Powtórzenie jej na tych samych danych
unieważnia werdykt.

## 9. Co unieważnia ten przebieg

* zmiana `generator.py`, `oracle/model.py`, `oracle/closedform.py`,
  `oracle/mutants.py`, progów, konwencji lub przewidywań z §3 po dacie zamrożenia;
* uruchomienie kampanii na ziarnie innym niż `20260912` i `20260913`;
* jakakolwiek zmiana rachunku ogona lub origin w silniku po tej dacie;
* uruchomienie kampanii bez `--with-window`, czyli na korpusie K24e;
* plan odrzucony przez kompilator.

## 10. Semantyka ustalona przed pomiarem

Bez zmian wobec K24e §9: rekord `k` strumienia o takcie `D` jest określony
w chwili `(k+1)*D`, jednakowo dla deklaracji i strumieni obliczanych; strumień
jest ciągiem rekordów, nie zbiorem z dziurami (zasada ciągłości), a NULL nigdy
nie jest rezerwacją miejsca (zasada brzegu).

Dla okna rekordowego dochodzi jedna pozycja, ustalona **przed** pomiarem
i wzięta z definicji operatora, nie z silnika: okno jest **przesuwne
i stemplowane końcem przedziału**, więc rekord `n` obejmuje rekordy źródła
`n-(W-1) … n`, a interwał wyjścia jest **równy** interwałowi źródła — lista
`SELECT` nie rusza osi czasu, każda zmiana taktu należy do klauzuli `FROM`.
Przy kilku agregatach w liście o istnieniu rekordu decyduje okno **najszersze**,
bo zależności węższych są jego podzbiorem: wszystkie kończą się na tym samym
rekordzie `n`.
