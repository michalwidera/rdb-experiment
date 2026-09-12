# K24f — zatrzymanie poziomu bramki odwzorowania i jego zniesienie

**Zakres:** wyłącznie **kryterium end-to-end** z [`PREDECLARATION.md`](PREDECLARATION.md)
§6 i przewidywanie **P5**.
**Klasyfikacja przyczyny:** `apparatus` — błąd aparatury, nie wynik o silniku.
**Status końcowy:** zatrzymanie **zniesione** po naprawie aparatury, na wyraźną
zgodę człowieka. P5 spełnione w przebiegu powtórzonym.

Werdykty H10a i H10b na obu ziarnach nie były tym zatrzymane ani chwilę
i obowiązują bez zmian: nie zależą od bramki odwzorowania, a `decision_rule.py`
**nie była uruchamiana ponownie**.

**Kolejność zdarzeń jest częścią wyniku i nie wolno jej czytać inaczej:** P5
zostało najpierw ocenione i wyszło **niespełnione**, przyczynę zdiagnozowano jako
aparaturę, aparaturę naprawiono za zgodą, a poziom powtórzono. To **nie** jest
przebieg, w którym P5 przeszło od razu.

---

## 1. Przebieg pierwszy — poziom zatrzymany

`run_mapping_gate.py --with-window --per-stratum 8`, dwie skale, oba ziarna:

| Ziarno | zgodne | poza budżetem | **rozbieżność treści** |
|---|---|---|---|
| `20260912` | 114 | 4 | **2** |
| `20260913` | 112 | 7 | **1** |

Predeklaracja wymaga zera rozbieżności treści, a P5 falsyfikuje **jedna**. Litera
predeklaracji była więc niespełniona.

Wszystkie trzy rozbieżności miały ten sam objaw — **`zero rekordów`** — i dotyczyły
węzłów `SHIFT` i `HASH`. **Ani jedna nie dotyczyła klasy `WINDOW`**, czyli klasy,
o której K24f twierdzi.

| Ziarno | Plan | Strata | Węzły |
|---|---|---|---|
| `20260912` | 39 | `HC_NONINT` | `n1` (`SHIFT`), `n2` (`HASH`), `n3` (`HASH`) |
| `20260912` | 55 | `HC_SHIFT_UNDER_HASH` | `n4` (`SHIFT`) |
| `20260913` | 10 | `HC_SHIFT_UNDER_HASH` | `n1` (`SHIFT`) |

## 2. Diagnoza — dwie wady wymiarowania przebiegu, nie semantyka

Bramka wymiarowała przebieg wzorem

```python
loops = int((RECORDS + 8) * spread) + 24      # spread = slowest/fastest
```

**Wada pierwsza: origin nie wchodził do wzoru.** W planie, w którym `>N` składają
się w łańcuch, początek logiczny narasta (plan 39: `n0` = 8, `n1` = 13, `n3` = 26,
`n2` = 34). Budżet kończył się, zanim najgłębszy węzeł doszedł do własnego origin,
i artefakt zostawał pusty — **poprawnie**, bo przed origin nie ma rekordów.

Zmierzone na planie 39, skala 1/200:

| `-m` | `n0` | `n1` | `n2` | `n3` |
|---|---|---|---|---|
| **76** (wybór bramki) | 5 | **0** | **0** | **0** |
| 200 | 27 | 22 | 56 | 44 |
| 500 | 81 | 76 | 195 | 151 |
| 1200 | 206 | 201 | 520 | 401 |

Mechanizm widać dokładnie: przy `-m 76` węzeł `n0` emituje 5 rekordów, a jego
origin to 8, więc są to rekordy logiczne 8-12. `n1 = n0>5` ma origin 13 i wymaga
`n0` do indeksu logicznego 13, czyli szóstego rekordu fizycznego. Brakowało
jednego, więc `n1` był pusty, a za nim puste były oba przeploty.

To samo na dwóch pozostałych planach, przy czterokrotnym budżecie:

| Ziarno / plan | węzeł | origin | `-m` bramki | rekordów | `-m` × 4 | rekordów |
|---|---|---|---|---|---|---|
| `20260912` / 55 | `n4` | 7 | 277 | **0** | 1108 | 24 |
| `20260913` / 10 | `n1` | 8 | 264 | **0** | 1056 | 27 |

**Wada druga, znaleziona przy czytaniu kodu do naprawy pierwszej: pomylone
jednostki.** Wzór traktował `-m N` jako N taktów najszybszego strumienia, a `-m`
jest budżetem **slotów**, czyli chwil, w których tyka co najmniej jeden strumień.
Plan wielotaktowy ma ich więcej niż taktów najszybszego strumienia, więc budżet
był zaniżony **także tam, gdzie origin jest zerowy**. Ta sama pomyłka siedziała
w kryterium odrzucenia (`loops * fastest > BUDGET`), które było proxy na czas
ścienny.

**Dowód, że to nie była niezgodność semantyczna.** Wszystkie pięć dotkniętych
węzłów ma w kampanii `agree_origin = 1` **i** `agree_c1 = 1`, czyli początek
logiczny i ogon wyznaczone przez silnik są **równe** granicom modelu
zdarzeniowego. Nie było tu rozbieżności między silnikiem a modelem — był przebieg,
który skończył się, zanim węzeł zaczął istnieć.

Nie był to też **rozjazd między skalami**, który predeklaracja wymienia jako
zatrzymanie: bramka klasyfikuje go osobno i nie zgłosiła ani jednego.

## 3. Wada predeklaracji, którą to obnażyło

Predeklaracja ma w tym miejscu **defekt redakcyjny**. §6 żąda „zero rozbieżności
treści", a §8 mówi, że błąd aparatury zatrzymuje iterację i nie jest wynikiem
o silniku. Dla rozbieżności **spowodowanej aparaturą** oba zdania dają sprzeczne
odczyty, a predeklaracja nie rozstrzyga, które wygrywa.

Tego zdania **nie poprawiono po fakcie** — predeklaracja jest zamrożona i jej
retroaktywna edycja jest dokładnie tym, czemu zamrożenie ma zapobiegać.
Sprzeczność jest zapisana tutaj, a wniosek dla następnej predeklaracji brzmi:
kryterium end-to-end musi z góry mówić, że rozbieżność z przyczyną aparaturową
jest zatrzymaniem poziomu, a nie falsyfikacją przewidywania.

Precedens rozstrzygnięcia jest w K24e: sufit `ORIGIN_LIMIT` w `oracle/model.py`
strzelił na ziarnie spoza bramki, przebieg został zatrzymany i opisany w
`STOP.md`, a nie zaraportowany jako znalezisko o silniku. Ten przypadek ma ten
sam kształt: granica aparatury, nie własność mechanizmu.

## 4. Decyzja człowieka i naprawa

Człowiekowi przedstawiono dwie drogi: przyjąć P5 jako `NIEOCENIALNY`, albo
naprawić wymiarowanie i powtórzyć **wyłącznie** poziom bramki odwzorowania.
**Wybrano drogę drugą**, wyraźnie i przed jakąkolwiek zmianą kodu.

Naprawa w `run_mapping_gate.py` ma dwie części, po jednej na każdą wadę z §2:

* **`horizon_of(plan, origins, tails)`** — horyzont czasowy wyprowadzony
  z definicji: rekord `n` jest emitowany w chwili `(n+1+W)*Delta`, a pierwszym
  istniejącym jest rekord o indeksie `origin`, więc ostatni potrzebny ma indeks
  `origin + RECORDS - 1`. Origin i ogon pochodzą z **modelu zdarzeniowego**
  (`model.evaluate`), nie z repliki: bramka odwzorowania nie ma prawa wpuścić
  rachunku silnika do wykonania. Są wielkościami indeksowymi, więc liczone są raz,
  na planie nieprzeskalowanym, i użyte w obu skalach.
* **`wakeup_budget(plan, horizon)`** — górne ograniczenie liczby slotów
  w horyzoncie: suma tyknięć wszystkich strumieni. Chwile wspólne tę liczbę tylko
  zmniejszają, więc suma jest bezpieczna.

Kryterium odrzucenia porównuje teraz **horyzont w sekundach** z budżetem 8 s,
a nie `loops * najszybszy takt`.

Budżety na trzech planach, które zatrzymały poziom:

| Ziarno / plan | `loops` przed | horyzont | `loops` po |
|---|---|---|---|
| `20260912` / 39 | 76 | 0,33 s / 0,65 s | 260 |
| `20260912` / 55 | 277 | 1,20 s / 2,41 s | 973 |
| `20260913` / 10 | 264 | 1,20 s / 2,40 s | 971 |

Każdy z trzech wychodzi po naprawie **`zgodne`**, czyli jest teraz sprawdzony co
do treści, a nie pominięty.

## 5. Przebieg powtórzony — poziom zaliczony

`run_mapping_gate.py` po naprawie, te same ziarna, ta sama podpróba
(`--per-stratum 8`), te same dwie skale:

| Ziarno | zgodne | poza budżetem | rozbieżność treści | awarie | niestabilne w skali |
|---|---|---|---|---|---|
| `20260912` | **119** | 1 | **0** | 0 | 0 |
| `20260913` | **119** | 1 | **0** | 0 | 0 |

Pokrycie **wzrosło** wobec przebiegu pierwszego (119 wobec 114 i 112): plany,
które przedtem fałszywie oblewały albo były pomijane, teraz faktycznie się liczą.

Jedyny plan poza budżetem na ziarno ma podaną przyczynę liczbową — horyzont
8,81 s (`20260912`, plan 69) i 8,44 s (`20260913`, plan 115) wobec progu 8 s.
To jest kryterium działające zgodnie z zamysłem, a nie pominięcie.

**Wszystkie osiem planów straty `WINDOW` na każdym ziarnie wyszło `zgodne`**,
czyli model treści okna rekordowego z `oracle/model.py` jest sprawdzony wobec
bajtów artefaktu na 16 planach, w dwóch skalach — nie tylko napisany.

## 6. Status P5 i zakres zmiany

**P5: spełnione w przebiegu powtórzonym**, z zastrzeżeniem z nagłówka: ocena
odbyła się dwukrotnie, a między ocenami zmieniono aparaturę. Czytelnik ma prawo
wiedzieć, że pierwsza ocena wypadła negatywnie i dlaczego.

Co zmiana aparatury **ruszyła**: skład podpróby (inne plany wchodzą teraz do
kategorii „poza budżetem") i budżet slotów każdego przebiegu.

Co **nie** ruszyła: korpus (generator nietknięty), model zdarzeniowy, replikę,
zestaw mutantów, przypadki ręczne, procedurę decyzyjną i oba werdykty H10a/H10b.
`decision_rule.py` uruchomiona raz na ziarno, przed naprawą, i nie powtarzana.
