# K24 / H10 — predeklaracja

**Data zamrożenia:** 2026-08-03
**Krok:** 3 ścieżki §16.1 `research_plan.md`, bramka daty werdyktu 2026-10-15
**Hipoteza:** H10 (§5 `research_plan.md`, sformułowana 2026-08-01, przed tym testem)

Dokument zamyka aparaturę przed kampanią. Po jego dacie generator, oracle,
progi i stratyfikacja nie są zmieniane. Zmiana którejkolwiek pozycji unieważnia
kampanię i wymaga nowej predeklaracji z nową datą.

---

## 1. Co jest twierdzone

**H10a — dokładność.** Dla każdego poprawnego planu RQL nad źródłami
o wymiernych interwałach, złożonego z `{PASS, >N, #, +, -, Θ, ~Θ, @(k,w),
redukcje}`, indeks pierwszego w pełni określonego rekordu wyjściowego jest
wyliczalny w postaci zamkniętej z samego planu i **równy** granicy wynikającej
z modelu zdarzeniowego. Twierdzona jest równość, nie oszacowanie z góry.

**H10b — nielokalność.** Istnieje klasa planów zawierających `#` o ilorazie
taktów `p/q` z `q` niedzielącym `p`, dla której naturalna reguła lokalna zaniża
prawdziwy ogon o wartość daną postacią zamkniętą `ceil((p+q-1)/p) >= 1`, a klasa
ta ma dodatnią gęstość w losowo generowanym korpusie.

## 2. Czego test nie twierdzi

K24 nie mówi nic o produktywności, zrozumiałości, liczbie błędów w praktyce ani
o wydajności. Nie jest badaniem użytkowników. Nie porównuje RQL z żadnym innym
systemem: człon (b) porównuje **regułę wyprowadzania z regułą wyprowadzania**.
Anegdota M3/F3 z K22v5 (ręcznie wyprowadzone ogony 19/49 wobec prawdziwych
21/51) jest motywacją do wstępu artykułu i **nie jest pomiarem błędów ludzkich**.

## 3. Różnica wobec prior work (obowiązkowa, ustalona przez K8)

Predeklaracja **nie opiera** różnicy na tym, że nasza granica jest dokładna,
a cudza bezpieczna z góry: rachunek n-synchroniczny (Cohen i in., POPL 2006,
Prop. 8) liczy minimalne opóźnienie dokładnie, z dowodem minimalności.
Różnica ma trzy punkty:

1. **inna wielkość** — indeks pierwszego w pełni określonego rekordu, zależny od
   okien historii, `NULL`-i, luk i polityki pustych przedziałów, a nie opóźnienie
   synchronizacji pary zegarów (POPL 2006) ani opóźnienie bodziec→skutek
   maksymalizowane po odpaleniach (Ghamarian i in., DSD 2007);
2. **inny zakres** — postać zamknięta dla całego planu jako punkt stały nad
   `qTree`, a nie inferencja parami na krawędzi komunikacyjnej;
3. **człon (b)** — nielokalność `ceil((p+q-1)/p)` bez odnalezionego odpowiednika.

Ślad wyszukiwania: §4.6 [`related_work_k8.md`](../../paper-arXiv/debs/related_work_k8.md).

## 4. Aparatura

| Element | Wartość |
|---|---|
| Silnik | `retractordb` gałąź `issue_223-fixes`, SHA `5e3eb42`, Debug i Release, `ctest` 174/174 w obu (PIN.md) |
| Oracle | `oracle/model.py` — model zdarzeniowy, **bez postaci zamkniętej** |
| Replika postaci zamkniętej | `oracle/closedform.py` — wyłącznie do bramki mutantów |
| Generator | `generator.py`, ziarno **20260803**, `N = 10 010` |
| Kampania | `run_campaign.py`, tryb compile-only (`xretractor -c`) |
| Bramka odwzorowania | `oracle/execute.py` — porównanie treści rekordów |

### 4.1. Reguła wyprowadzenia ogona w oracle'u

Rekord `n` strumienia `S` jest emitowany w chwili `(n + 1 + W_S) * Delta_S`.
Zależy od rekordów składowych o własnych chwilach dostępności. `W_S` jest
najmniejszą liczbą całkowitą `>= 0`, dla której emisja każdego rekordu wypada
nie wcześniej niż dostępność wszystkich jego zależności:

    W_S = max(0, max_n ceil( avail(n) / Delta_S - (n + 1) ))

Odwzorowanie rekordów (który rekord składowej wchodzi do rekordu `n`) pochodzi
z definicji operatorów w §Formal Foundations artykułu. Oracle nie zawiera
wyrażenia `ceil((p+q-1)/p)`, `AgseStartupLatency` ani `SubtractStartupLatency`;
warunek jest sprawdzany mechanicznie (`tests/test_independence.py`).

### 4.2. Konwencja dostępności

* **C1 (główna)** — nieostra: rekord jest dostępny w chwili swojej emisji;
  konsument, którego slot kończy się w tej samej chwili, może go użyć.
  Uzasadnienie: `dataModel::processRows()` publikuje deklaracje jako pierwsze,
  a dalej przetwarza w porządku topologicznym.
* **C2 (wrażliwość)** — ostra: odczyt w tym samym takcie niedozwolony.

Werdykt główny liczony jest w C1. C2 raportowany jest jako kolumna wrażliwości,
żeby wynik nie był zakładnikiem wyboru konwencji.

### 4.3. Co pochodzi z definicji, a co z obserwacji

Rozdział jest sztywny i wchodzi do raportu:

* **z definicji (nigdy z silnika)** — odwzorowanie rekordów w czasie, interwały
  wyjściowe operatorów, reguła wyprowadzania ogona;
* **z obserwacji na zbiorze kalibracyjnym (wyłącznie prezentacja)** — orientacja
  okna AGSE (dodatnia długość: pole najnowsze jako pierwsze) oraz kodowanie
  wyniku reduktorów jako pola `RATIONAL` (para licznik/mianownik).

Dopasowanie oracle'a do silnika w warstwie **czasowej** byłoby tautologią
i jest zakazane. Zaobserwowane rozbieżności czasowe zostają rozbieżnościami.

## 5. Korpus

* `N = 10 010` planów, ziarno `20260803`, głębokość 1–6;
* interwały losowane z zamrożonego zbioru 16 liczb wymiernych
  (`generator.INTERVALS`), w tym para audio `4/25`, `147/1000`;
* 14 strat po 715 planów (próg predeklarowany: `>= 500`):
  dziewięć klas operatorów `PASS, >N, #, +, -, Θ, ~Θ, @, redukcje`
  oraz pięć klas trudnych `HC_NONINT`, `HC_SHIFT_UNDER_HASH`, `HC_INT`,
  `HC_SINGLE`, `HC_DEEP`;
* generator produkuje wyłącznie plany poprawne. **Plan odrzucony przez
  kompilator jest błędem aparatury i zatrzymuje iterację**, nie jest cicho
  pomijany;
* każdy węzeł planu jest osobną obserwacją (plany są zdekomponowane, każdy
  operator ma jawnie nazwany strumień).

## 6. Kryteria

**H10a** — wsparta w klasie operatora, gdy zgodność postaci zamkniętej
z oracle'em wynosi **100%**, obustronnie. Raportowane **per klasa operatora,
nigdy agregatem**. Jedna niezgodność falsyfikuje H10a w tej klasie; wynik
9 999/10 000 nie jest wsparciem, tylko zlokalizowanym defektem do opisania.

**H10b** — wsparta, gdy naturalna reguła lokalna rozjeżdża się z dokładną
w co najmniej **5%** korpusu **oraz** rozbieżność ma postać `ceil((p+q-1)/p)`
w **100%** rozjazdów. Rozjazd o innej wartości falsyfikuje człon (b) nawet przy
spełnionym progu 5%.

*Naturalna reguła lokalna* (definicja predeklarowana): ta sama rekursja po
planie, w której własny ogon każdego operatora wynosi zero, a ogon składowej
jest przeliczany przez takt wzorem `ceil(w * Delta_src / Delta_dst)`;
przesunięcie `>N` dodaje `N`. Populacją członu (b) są plany, w których
występuje dokładnie jeden `#`, a pozostałe operatory należą do `{PASS, >N}` —
tylko wtedy rozjazd można przypisać jednemu ilorazowi `p/q`.

**Kontrole negatywne** — zero rozjazdów reguły lokalnej w klasach:
`HC_SINGLE` (plany jednotaktowe bez `#`) oraz `HC_INT` (`#` o ilorazie
całkowitym, gdzie `own` degeneruje się do wartości reguły lokalnej).
Rozjazd w tych klasach oznacza źle zdefiniowaną regułę lokalną, nie wynik.

## 7. Bramki wykonane przed zamrożeniem

| Bramka | Wymóg | Stan |
|---|---|---|
| Wierność repliki | replika == silnik na całym zbiorze kalibracyjnym | **przeszła**, 40/40 węzłów |
| Bramka oracle'a | zgodność z >= 30 przypadkami o ręcznie wyprowadzonej odpowiedzi | **przeszła**, 37 przypadków, 80 porównań |
| Bramka mutantów | wykrycie 100% zamrożonych mutantów | **przeszła**, 5/5 (faza ±1, zamiana `p/q`, usunięcie `own`, zerowanie ogona `Θ`) |
| Bramka odwzorowania | treść rekordów silnika == treść z oracle'a | wykonana na zbiorze kalibracyjnym; wynik w REPORT.md §3 |

## 8. Ujawnienie kolejności prac

Kalibracja aparatury poprzedziła tę predeklarację i **ujawniła kandydatów na
rozbieżności** w klasach `+`, `-`, `@` i `Θ`. Predeklaracja powstała po
kalibracji, a przed kampanią na korpusie. Chroni to prospektywność w tym
zakresie, w jakim jest to możliwe:

* kryteria H10a i H10b pochodzą z `research_plan.md` §5 i §10/K24 i były
  zapisane **2026-08-01**, przed jakąkolwiek linią kodu tego badania;
* korpus, ziarno i stratyfikacja są zamrożone tutaj, przed kampanią;
* obserwacje kalibracyjne są wyliczone jawnie w REPORT.md §3 i nie zostały
  użyte do przestrojenia oracle'a w warstwie czasowej.

Ukrycie tej kolejności byłoby gorsze niż jej ujawnienie.

## 9. Bramka skali dla bramki odwzorowania

Wykonanie planu odbywa się w czasie rzeczywistym, więc plan jest przeskalowany
tak, by najszybszy strumień miał interwał mieszczący się w budżecie. Ogon
i odwzorowanie rekordów zależą wyłącznie od ilorazów interwałów, więc
przeskalowanie nie zmienia żadnego wyniku. Ponieważ zbyt szybki zegar potrafi
wyprodukować rekordy `NULL` nieodróżnialne od defektu, każdy plan bramki
odwzorowania jest wykonywany **w dwóch skalach**; różnica treści między skalami
oznacza, że silnik nie nadążył, i dyskwalifikuje przebieg jako aparaturę,
zamiast być raportowana jako znalezisko.

## 10. Naprawy aparatury po pierwszym zamrożeniu

Dwie zmiany wprowadzono **po** pierwszym zapisie tego dokumentu, a **przed**
werdyktem. Obie wynikły z reguły „plan odrzucony przez kompilator zatrzymuje
iterację” i obie zawężają zbiór planów uznawanych za poprawne. Żadna nie dotyka
progów, ziarna, stratyfikacji ani oracle'a.

| Zmiana | Powód | Skutek |
|---|---|---|
| `Θ`/`~Θ` nie mogą dać składowej szybszej od źródła | kompilator odrzuca taki plan (`compiler.cpp:103`, `:123`); generator produkował go jako rzekomo poprawny | 1 plan na 10 010 przestał powstawać |
| licznik i mianownik interwału ograniczone do 40 000 | głębokie łańcuchy `&` przepełniają `boost::rational<int>` w iloczynie interwałów; komunikat kompilatora myli przyczynę | korpus mierzy rachunek ogona, a nie zakres typu; obserwacja opisana w REPORT.md §6.2 |

Ponieważ obie zmiany przesuwają strumień losowy generatora, korpus finalny nie
jest identyczny z pierwszym. Werdykt liczony jest wyłącznie na korpusie
finalnym; korpus pierwszy nie wyprodukował żadnego wyniku, bo kampania
zatrzymała się na błędzie aparatury zgodnie z §5.

## 11. Poprawka atrybucji (przed werdyktem, po kampanii)

Pierwsza wersja werdyktu liczyła zgodność per klasa na ogonach propagowanych,
przez co niezgodność dziecka liczyła się jako niezgodność rodzica i klasa
operatora nie znaczyła tego, co deklaruje §6 („raportowane per klasa
operatora”). Werdykt finalny używa **atrybucji izolowanej**: ogon węzła liczony
postacią zamkniętą z ogonów składowych wziętych z oracle'a. Obie kolumny są
raportowane w VERDICT.md; werdyktem jest izolowana. Zmiana dotyczy wyłącznie
sposobu liczenia zgodności, nie progów.

## 12. Produkt

`rdb-experiment/results_20260803_K24/`: ta predeklaracja, `PIN.md`, generator,
oracle, replika i mutanty, korpus odtwarzalny z ziarna, surowe CSV (`raw/`),
werdykt per klasa (`VERDICT.md`), raport (`REPORT.md`) i indeks `SHA256SUMS`.
