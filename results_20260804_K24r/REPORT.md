# K24r — raport

**Data:** 2026-08-04
**Punkt odniesienia:** [`PIN.md`](PIN.md) — silnik `master:c4b63a7`
**Predeklaracja:** [`PREDECLARATION.md`](PREDECLARATION.md), zamrożona przed kampanią
**Poprzednik:** [`../results_20260803_K24/`](../results_20260803_K24/) — nietknięty

---

## 1. Wynik

Obie predeklarowane hipotezy potwierdzenia przeszły.

| Kryterium z predeklaracji | Wymagane | Osiągnięte |
|---|---|---|
| zgodność `+` z granicą zdarzeniową (C1, ziarno `20260804`) | 100% | **100,0%** (2487 węzłów) |
| zgodność `@` z granicą zdarzeniową (C1, ziarno `20260804`) | 100% | **100,0%** (4256 węzłów) |
| bramka odwzorowania, nowe ziarno | 0 rozbieżności, 0 awarii | **0 / 0** (102 zgodne, 10 poza budżetem) |
| `capacity.py`, oba ziarna | zerowy niedomiar | **0 we wszystkich klasach** |

Nowe postacie zamknięte dla `+` i `@` zostały wyprowadzone na korpusie ziarna
`20260803`. Ziarno `20260804` generuje inny korpus — inne plany, inne takty,
inne głębokości — i na nim zgodność jest również pełna. To jest różnica między
dopasowaniem a postacią zamkniętą.

## 2. Zestawienie „przed/po” per klasa operatora

Zgodność postaci zamkniętej z granicą zdarzeniową w konwencji C1, atrybucja
izolowana (ogony składowych brane z oracle'a, więc niezgodność pochodzi z reguły
tego węzła, a nie jest dziedziczona).

| Klasa | K24 — silnik `5e3eb42` | K24r ziarno `20260803` | K24r ziarno `20260804` | Werdykt |
|---|---:|---:|---:|---|
| `@` AGSE | 31,8% | **100,0%** | **100,0%** | **wsparta** |
| `+` ADD | 42,3% | **100,0%** | **100,0%** | **wsparta** |
| `>N` SHIFT | 100,0% | 100,0% | 100,0% | wsparta |
| projekcja PASS | 100,0% | 100,0% | 100,0% | wsparta |
| redukcje REDUCE | 100,0% | 100,0% | 100,0% | wsparta |
| `~Θ` NTHETA | 98,7% | 98,7% | 98,6% | falsyfikacja |
| `#` HASH | 90,9% | 90,9% | 90,8% | falsyfikacja |
| `Θ` THETA | 59,9% | 59,9% | 59,4% | falsyfikacja |
| `-` SUB | 19,2% | 19,2% | 19,2% | falsyfikacja |

Kolumna środkowa i lewa dzielą korpus (to samo ziarno), więc różnica między nimi
jest **wyłącznie** skutkiem zmiany silnika. Kolumna prawa ma inny korpus, więc
drobne wahania w klasach niezmienionych (`90,9% → 90,8%`, `59,9% → 59,4%`) są
losowaniem planów, nie efektem naprawy.

### Zmiana reżimu — najważniejsza pozycja tego raportu

| Reżim | K24 (`5e3eb42`) | K24r (`c4b63a7`) |
|---|---|---|
| dokładna | `>N`, projekcja, redukcje | `>N`, projekcja, redukcje, **`@`**, **`+`** |
| zawyżająca (bezpieczna) | `#`, `-`, `Θ`, `~Θ` | `#`, `-`, `Θ`, `~Θ` |
| **zaniżająca** (rekord przed określeniem zależności) | **`@`, `+`** | **brak** |

Reżim zaniżający zniknął z korpusu. Żaden węzeł żadnego z 10 010 planów, na
żadnym z dwóch ziaren, nie emituje rekordu wcześniej, niż wszystkie jego
zależności są określone. Reżim zawyżający pozostaje w czterech klasach i jest
jakościowo inny: opóźnia emisję najwyżej o jeden slot, nie psuje danych.

## 3. Bramka odwzorowania (end-to-end)

Podpróba wykonywana w silniku, treść rekordów porównywana z modelem treści
oracle'a, w dwóch skalach czasowych (kontrola stabilności).

| Miara | K24 (`5e3eb42`) | po naprawach, ziarno `20260803` | K24r, ziarno `20260804` |
|---|---:|---:|---:|
| zgodne | 75 | 99 | **102** |
| rozbieżność treści | 21 | 0 | **0** |
| twarda awaria silnika | 3 | 0 | **0** |
| poza budżetem aparatury | 13 | 13 | 10 |

Przebieg środkowy pochodzi z `../results_20260803_K24/raw/mapping_gate_after_tails.csv`
(ten sam silnik, korpus K24). Plany „poza budżetem” to plany o rozpiętości
taktów wymagającej dłuższego przebiegu, niż pozwala budżet aparatury (8 s);
są wyłączone z oceny w obie strony i nie liczą się ani na korzyść, ani na
niekorzyść.

## 4. Model pojemności historii

`capacity.py` porównuje pojemność zapewnianą przez `compiler::computeRequiredCapacities()`
z odległością wsteczną wynikającą z modelu zdarzeniowego.

| Ziarno | Par (konsument, składowa) | Niedomiar |
|---|---:|---:|
| `20260803` | 23 504 wiążących z 36 354 | **0** |
| `20260804` | 23 187 wiążących z 35 851 | **0** |

Wiążące są pary, w których składową jest strumień **deklarowany**: tylko tam
limit pojemności działa (strażniki sprawdzają historię pod warunkiem
`isDeclared()`; strumienie obliczane czytają z magazynu zachowującego komplet
rekordów).

Klasa `ADD` weszła do tej analizy dopiero po zmianie odwzorowania `Σ` (suma
strumieni czyta teraz składowe po indeksie, nie bieżący payload) i również
nie wykazuje niedomiaru.

## 5. Co pozostaje otwarte

Cztery klasy nadal nie mają dokładnej postaci zamkniętej: `-` (19,2%),
`Θ` (59,4%), `#` (90,8%) i `~Θ` (98,6%). Wszystkie są w reżimie **zawyżającym**,
czyli bezpiecznym — postać zamknięta nigdy nie zaniża ogona, więc poprawność
obserwacyjna planów nie jest zagrożona; cena to najwyżej jeden slot opóźnienia.

Rozkład różnicy pokazuje, że w każdej z tych klas rozjazd wynosi dokładnie
`+1` slot i nigdy więcej. Najgorsza jest `-`: 80,8% węzłów zawyża o slot.
Doświadczenie z `+` i `@` sugeruje, że i tu przyczyną jest wzór, a nie brak
postaci zamkniętej — ale to jest **hipoteza, nie wynik**, i wymaga osobnego
wyprowadzenia oraz osobnego potwierdzenia poza próbą.

## 6. Zagrożenia dla trafności

1. **Wyprowadzenie po fakcie.** Postacie dla `+` i `@` powstały ze znajomością
   oracle'a, na korpusie `20260803`. Zagrożenie zaadresowane przebiegiem
   potwierdzającym na `20260804`, predeklarowanym przed uruchomieniem, z jednym
   ziarnem i bez możliwości powtórki. Nie jest to jednak preregistracja
   *hipotezy* — postacie były znane przed zamrożeniem predeklaracji, więc K24r
   jest **potwierdzeniem out-of-sample, nie testem prospektywnym**. Ten status
   trzeba raportować w artykule dosłownie.
2. **Oracle wspólny dla obu kampanii.** `oracle/model.py` jest bajtowo
   identyczny z K24 — to warunek porównywalności, ale oznacza, że błąd
   w oracle'u przeszedłby przez obie kampanie. Zabezpieczenie: bramka
   niezależności (oracle nie importuje repliki), 37 przypadków ręcznych
   i zestaw mutantów wykrywanych w 100%.
3. **Konwencja C2 nie jest wspierana.** W C2 zgodność `+` wynosi 42,6%,
   a `@` 29,1%. Twierdzenie dotyczy wyłącznie C1, zgodnie z semantyką ustaloną
   2026-08-03 (rekord `k` określony w chwili `(k+1)·Δ`). Gdyby semantyka
   deklaracji została kiedyś zmieniona na `k·Δ`, wynik K24r wymaga powtórzenia.
4. **Budżet bramki odwzorowania.** 10 planów nowego ziarna nie zostało
   wykonanych end-to-end. Nie są to plany wybrane ze względu na wynik —
   kryterium jest rozpiętość taktów, znana przed uruchomieniem.
5. **Jedna maszyna, jedno binarium.** Kampania jest compile-only i deterministyczna,
   więc nie zależy od maszyny; bramka odwzorowania zależy i dlatego biegła na tej
   samej maszynie co w K24.

## 7. Co z tego wynika dla artykułu

Fakty do decyzji człowieka — **nie podejmuję jej w tym raporcie**:

1. **Falsyfikacja H10a w klasach `@` i `+` była defektem implementacji, nie
   własnością problemu.** Po naprawie obie klasy są dokładne na dwóch
   niezależnych korpusach. Twierdzenie, które daje się dziś obronić, brzmi:
   *postać zamknięta jest dokładna dla `PASS`, `>N`, redukcji, `@` i `+`,
   a dla `#`, `-`, `Θ` i `~Θ` jest bezpiecznym oszacowaniem z góry z błędem
   najwyżej jednego slotu*. To jest wynik pozytywny i mocniejszy niż ten
   z K24, ale nadal węższy od H10a w brzmieniu predeklarowanym.
2. **Zniknięcie reżimu zaniżającego zdejmuje przesłankę z `harmonogram.md` §4.2.**
   Zaniżenie ogona dotykało relacji `Obs`, na której opiera się H1, a przez H1
   interpretacja K5, K6c i K19. Ta przesłanka nie zachodzi już na żadnym
   z dwóch korpusów.
3. **Pozostałe cztery klasy są otwartą pracą o znanym koszcie.** Wyprowadzenie
   dla `-` i `Θ` jest najbardziej obiecujące (największy rozjazd, ten sam typ
   przyczyny). Każde wymaga własnego potwierdzenia poza próbą — czyli własnego
   ziarna i własnej predeklaracji.

Zgodnie z regułą §16.1 **nie naniesiono niczego na `main-debs.tex` ani
`main-debs-pl.tex`** — transfer wymaga decyzji z punktu 1.
