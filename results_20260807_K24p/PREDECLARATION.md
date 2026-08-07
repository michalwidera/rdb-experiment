# K24p — predeklaracja przebiegu po przestemplowaniu

**Data zamrożenia:** 2026-08-07, przed uruchomieniem kampanii
**Poprzednicy:** [`results_20260803_K24`](../results_20260803_K24/) (falsyfikacja
H10a-impl), [`results_20260804_K24r`](../results_20260804_K24r/) (potwierdzenie
poza próbą dla `+` i `@`), [`results_20260804_K24b`](../results_20260804_K24b/)
(człon (b))
**Kontekst:** `paper-arXiv/debs/research_plan.md` §K24 oraz §16.1 krok 3a

Dokument zamyka aparaturę przed kampanią. Zmiana którejkolwiek pozycji po tej
dacie unieważnia przebieg i wymaga nowej predeklaracji.

---

## 1. Dlaczego ten przebieg w ogóle powstał

K24r zmierzyła silnik przypięty do `master:c4b63a7`. Trzy dni później, w scaleniu
`5f31051` („Issue 227 precesja”), **zmieniła się mierzona wielkość**:

* okno `@(k,L)` jest teraz stemplowane **końcem** przedziału (rekord `n` obejmuje
  pozycje `n*k-(|L|-1) ... n*k`), a nie początkiem;
* rozpiętość okna i opóźnienie `>N` przestały być ogonem — przeszły do nowej
  wielkości `query::logicalOrigin`, wyliczanej przebiegiem
  `compiler::computeLogicalOrigin()`;
* postać zamknięta ogona `@` straciła człon fazowy
  `P = floor((|L|-1)/gcd(F,k))*gcd(F,k)`;
* model pojemności historii dla `@` przestał być postacią zamkniętą — silnik
  przegląda jeden pełny okres fazowy.

Liczby K24r (`@`: 4256/4256, `>`: 5484/5484) dotyczą semantyki, której już nie
ma. **Nie da się ich przenieść do artykułu** — i to jest jedyny powód tego
przebiegu. K24p nie unieważnia werdyktów K24 ani K24r: tamte opisują stan silnika
sprzed 2026-08-06 i pozostają w mocy dla tamtego stanu.

## 2. Co jest twierdzone

**H10a-ex (per klasa operatora).** Dla każdego poprawnego planu RQL obie
wielkości wyznaczane przez silnik są **równe** granicom z modelu zdarzeniowego:

```
  origin O_S — najmniejszy indeks, OD KTÓREGO strumień jest ciągły
               (wszystkie rekordy od niego wzwyż mają komplet istniejących
                zależności);
  ogon   W_S — najmniejsze W >= 0, przy którym emisja każdego ISTNIEJĄCEGO
               rekordu (n >= O_S) w chwili (n+1+W)*Delta_S wypada nie wcześniej
               niż dostępność wszystkich jego zależności.
```

Rachunek silnika badany w tym przebiegu:

```
  `@`  : O = ceil( (O_src*F + |L| - 1) / k )        F = szerokość rekordu źródła
         W = ceil( (1 + W_src) * F / k ) - 1
  `>N` : O = O_src + N
         W = W_src
  `+`  : W = max_skł ceil( (1 + W_skł) * D_skł / D_out ) - 1     (bez zmian)
  origin dla `+`, `#`, `-`, `Θ`, `~Θ`: najmniejszy indeks osiągający próg
         składowej, wyznaczany POSZUKIWANIEM po niemalejącym odwzorowaniu
         (`firstIndexReaching`), nie wzorem
```

Twierdzona jest **równość**, nie oszacowanie z góry, w konwencji dostępności C1
(nieostrej). Konwencja C2 jest kolumną wrażliwości i **nie jest** przedmiotem
twierdzenia. Origin konwencji nie ma: istnienie rekordu nie zależy od tego, czy
odczyt w tym samym takcie jest dozwolony.

## 3. Predeklarowana predykcja negatywna dla `>N`

Wyprowadzenie ręczne wykonane przy budowie aparatury (przed kampanią, zapis
w `tests/hand_cases.py`) daje dla przesunięcia deficyt **stały** i równy
`W_src - N`, czyli dokładną postać

```
  `>N` : W = max(0, W_src - N)
```

Silnik ustawia `W = W_src`, bo `dataModel::fetchBack` adresuje **offsetem
względnym** i nie potrafi wyrazić „rekord o indeksie logicznym n-N” niezależnie
od ogona. **Predeklarowana predykcja: klasa `>N` wypadnie zawyżająca (nie
dokładna) wszędzie tam, gdzie producent ma niezerowy ogon, a różnica wyniesie
dokładnie `min(W_src, N)`.** Predykcja jest zapisana **przed** uruchomieniem
kampanii; jej potwierdzenie nie jest wsparciem H10a-impl dla `>N`, tylko
zlokalizowaniem defektu o znanej postaci i znanym koszcie naprawy.

Rozjazd o innej wartości niż `min(W_src, N)` falsyfikuje tę predykcję.

## 4. Czego ten przebieg nie twierdzi

* Nic o klasach `#`, `-`, `Θ`, `~Θ` ponad to, co zmierzy — pozostają
  sfalsyfikowane przez K24 i raportowane jako tło.
* Nic o wydajności, produktywności ani porównaniu międzysystemowym.
* Nie jest testem prospektywnym. Postacie zamknięte silnika były znane przed
  zamrożeniem; predeklarowane są **ziarno, kryteria i predykcja z §3**, nie
  hipoteza. Status do raportowania dosłownie: **potwierdzenie po zmianie
  semantyki, na modelu zdarzeniowym wyprowadzonym niezależnie od silnika**.
* Nie rozstrzyga, czy przestemplowanie było dobrą decyzją projektową. Mierzy
  wyłącznie zgodność rachunku z modelem zdarzeniowym.

## 5. Korpus i ziarna

| Pozycja | Wartość |
|---|---|
| generator | `generator.py`, **bajtowo bez zmian** wobec K24/K24r |
| liczność | 10 010 planów |
| ziarno porównawcze | `20260804` — ten sam korpus co potwierdzenie K24r, dla tabeli „przed/po” |
| **ziarno potwierdzające (out-of-sample)** | **`20260807`** |
| stratyfikacja, głębokość, zbiór taktów | bez zmian |

Ziarno `20260807` jest zapisane **przed uruchomieniem** i jest jedynym ziarnem
potwierdzającym. Jeżeli wynik na nim wypadnie negatywnie, jest to wynik
negatywny — nie wolno próbować kolejnych ziaren i raportować najlepszego.

## 6. Kryteria

**Kryterium główne (per klasa, nigdy agregatem).** Na obu ziarnach, w atrybucji
izolowanej i w C1:

* **ogon** — zgodność 100% w klasie oznacza reżim „dokładna” i wsparcie H10a-ex
  w tej klasie; jedna niezgodność falsyfikuje;
* **origin** — jak wyżej, osobną tabelą;
* **suma origin+ogon** — raportowana jako jedyna wielkość porównywalna
  z kampaniami sprzed przestemplowania.

**Kryterium bezpieczeństwa.** Zero klas w reżimie **zaniżającym**, osobno dla
ogona i dla origin. Origin zaniżony jest jakościowo gorszy od zawyżonego:
oznacza rekord wyemitowany, mimo że jego definicja sięga przed początek źródła.

**Kryterium end-to-end.** Bramka odwzorowania na podpróbie obu ziaren daje
**zero rozbieżności treści** i **zero awarii**. Pozycja w artefakcie jest
przeliczana na indeks logiczny przez origin; plany odrzucone przez budżet czasu
aparatury są raportowane osobno i nie liczą się w żadną stronę.

**Kryterium spójności pojemności.** `capacity.py` na obu ziarnach daje zerowy
niedomiar we wszystkich klasach dla składowych deklarowanych.

**Kryterium członu (b).** Kontrola na aparaturze K24b, ziarno `20260805`,
populacja i reguła lokalna **bez zmian**: werdykt H10b ma pozostać wsparty.
Zmiana werdyktu członu (b) po przestemplowaniu jest wynikiem, nie awarią.

## 7. Bramki aparatury, które muszą przejść przed kampanią

| Bramka | Warunek |
|---|---|
| `tests/test_independence.py` | oracle nie importuje repliki i nie zawiera nazw rachunku silnika (w tym `AgseLogicalOrigin`, `computeLogicalOrigin`, `firstIndexReaching`) |
| `tests/test_oracle.py` | 100% zgodności z przypadkami o ręcznie wyprowadzonej odpowiedzi, dla ogona (C1 i C2) **oraz** origin |
| `tests/test_mutants.py` | 100% wykrycia zamrożonych mutantów, osobno dla rodziny ogona i rodziny origin |
| `tests/test_closedform.py` | replika zgodna ze zrzutem planu silnika co do ogona **i** origin |

## 8. Co unieważnia ten przebieg

* zmiana `generator.py`, `oracle/model.py`, progów, konwencji lub predykcji z §3
  po dacie zamrożenia;
* uruchomienie kampanii potwierdzającej na ziarnie innym niż `20260807`;
* jakakolwiek zmiana rachunku ogona lub origin w silniku po tej dacie — wtedy
  potrzebna jest nowa predeklaracja i nowe ziarno;
* plan odrzucony przez kompilator (błąd aparatury, zatrzymuje iterację).

## 9. Semantyka ustalona przed pomiarem

Chwila emisji rekordu deklaracji pozostaje ta sama co w K24/K24r: rekord `k`
strumienia o takcie `D` jest określony w chwili `(k+1)*D`, jednakowo dla
deklaracji i strumieni obliczanych (`research_plan.md` §K24, rozstrzygnięcie
z 2026-08-03).

Nowa jest **zasada ciągłości**: strumień jest ciągiem rekordów, nie zbiorem
z dziurami. Jeżeli odwzorowanie indeksu sprawia, że rekord `n` ma komplet
zależności, a rekord `n+1` nie (co przy przeplocie składowych o różnych
początkach zdarza się realnie), początkiem logicznym jest pierwszy indeks, od
którego **nie ma już ani jednej luki**. Zasada wynika wprost z zasady brzegu
(NULL nigdy nie jest rezerwacją miejsca) i jest zapisana tutaj, bo oracle jej
używa, a przed 2026-08-06 nie było jej gdzie zapisać.
