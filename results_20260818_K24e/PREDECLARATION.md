# K24e — predeklaracja kampanii po wyprowadzeniu postaci dokładnych

**Data zamrożenia:** 2026-08-18, **przed** uruchomieniem kampanii
**Silnik:** `retractordb` gałąź `issue_232-k24h10`, commit **`e2a61ff`**
**Poprzednicy:** [`results_20260807_K24d`](../results_20260807_K24d/) (sześć klas
dokładnych, trzy zawyżające, silnik `34db1a2`),
[`results_20260807_K24p`](../results_20260807_K24p/) (przebieg po przestemplowaniu)
**Materiał wyprowadzenia:** [`../investigation_K24H10/`](../investigation_K24H10/)
**Kontekst:** `paper-arXiv/debs/plan-realizacji-k24h10.md`, faza 4

Dokument zamyka aparaturę przed kampanią. Zmiana którejkolwiek pozycji po tej
dacie unieważnia przebieg i wymaga nowej predeklaracji.

---

## 1. Dlaczego ten przebieg powstał

K24d zmierzyła silnik `34db1a2` i zapisała trzy klasy w reżimie **zawyżającym**:
`-` (zgodność izolowana 19,1%), `Θ` (59,7%) i `~Θ` (99,2%). Faza 1 i 2 planu
`plan-realizacji-k24h10.md` wyprowadziły dla nich postacie zamknięte, faza 3
wdrożyła je w silniku (`e2a61ff`).

Zmiana rachunku ogona **unieważnia liczby K24d** — reguła zapisana w
`research_plan.md` §16 mówi to wprost. K24e jest przebiegiem, który je zastępuje,
i jedynym, którego liczby wolno przenieść do artykułu.

## 2. Co jest twierdzone

**H10a-ex (per klasa operatora).** Dla każdego poprawnego planu RQL ogon
startowy i początek logiczny wyznaczane przez silnik są **równe** granicom
z modelu zdarzeniowego, w konwencji dostępności **C1** (nieostrej). Konwencja C2
pozostaje kolumną wrażliwości i nie jest przedmiotem twierdzenia.

Rachunek badany w tym przebiegu — trzy postacie wprowadzone w fazie 3:

```
  wspólna:  W = max(0, ceil( (c + 1 + W_src) / r ) - 1),   r = D_out/D_src
  `-`  :    c = (q-1)/q,          q = mianownik skróconego r
  `Θ`  :    c = (a+b-1)/b,        a/b = skrócone D_out/param
  `~Θ` :    c = 0
```

Postacie wynikają z rozkładu `idx(n) = n*r + e(n)`: warunek dostępności redukuje
się do `ceil((e(n)+1+W_src)/r) - 1`, a kres `sup e(n) = c` jest **osiągany**,
bo po skróceniu `gcd = 1`. Wyprowadzenie: `../investigation_K24H10/DERIVATION.md` §5.

## 3. Predeklarowane przewidywania

Przewidywania zapisane **przed** uruchomieniem. Każde jest falsyfikowalne.

| # | Przewidywanie | Falsyfikuje je |
|---|---|---|
| **P1** | Ogon: **9/9 klas w reżimie dokładnym**, atrybucja izolowana, oba ziarna | jedna niezgodność w dowolnej klasie |
| **P2** | Kolumna **propagowana** również **100% w 9/9 klasach** | jakakolwiek wartość poniżej 100% |
| **P3** | Zero klas w reżimie **zaniżającym**, dla ogona i dla origin | jeden węzeł zaniżony |
| **P4** | Początek logiczny **dokładny w 9/9**, bez zmian wobec K24d | jedna niezgodność |
| **P5** | Człon (b) **wsparty**, postać `ceil((p+q-1)/p)` w 100% populacji | inna gęstość albo inna postać |
| **P6** | `capacity.py`: **zerowy niedomiar** we wszystkich klasach dla składowych deklarowanych, mimo że pojemność źródła `-` **zmalała** wraz z ogonem | jakikolwiek niedomiar |

**P2 jest przewidywaniem nowym wobec wszystkich poprzednich kampanii K24.**
K24d miała w tej kolumnie 92,7%-99,5%, bo trzy zawyżające reguły dziedziczyły
błąd w górę planu. Jeśli każda reguła jest dokładna przy dokładnych ogonach
składowych, dokładne musi być też złożenie — i to jest sprawdzalne.

**P6 jest przewidywaniem o skutku ubocznym naprawy.** Pojemność historii źródła
różnicy to `floor((1+W_out)*ratio) + prefetch`, czyli **funkcja ogona**. Ogon
spadł, więc pojemność też (w teście jednostkowym 4 -> 3). Kierunek jest
bezpieczny tylko wtedy, gdy model pojemności nie wykazuje niedomiaru — i to
mierzy ten przebieg, a nie rozumowanie.

## 4. Czego ten przebieg nie twierdzi

* Nie jest testem prospektywnym. Postacie były wyprowadzone i sprawdzone offline
  na korpusach ziaren `20260804` i `20260807` **przed** dotknięciem silnika
  (`../investigation_K24H10/PHASE2.md`). Predeklarowane są **ziarna, kryteria
  i przewidywania**, nie hipoteza. Status do raportowania dosłownie:
  **potwierdzenie poza próbą na ziarnach nieużytych w wyprowadzeniu**.
* Nic o wydajności, produktywności ani porównaniu międzysystemowym.
* Nic o konwencji dostępności dla deklaracji ponad to, co zmierzy. Faza 1
  ustaliła, że siedem klas silnika czyta deklaracje w C1, a `-` i `Θ` czytały
  je w C2; naprawa ujednoliciła silnik na C1, czyli na konwencji, którą kampania
  K24 predeklarowała w 2026-08-03. Gdyby człowiek rozstrzygnął odwrotnie,
  unieważnia to ten przebieg i siedem pozostałych klas, nie tylko trzy naprawione.

## 5. Korpus i ziarna

| Pozycja | Wartość |
|---|---|
| generator | `generator.py`, **bajtowo bez zmian** wobec K24/K24r/K24p/K24d |
| liczność | 10 010 planów |
| **ziarno główne** | **`20260818`** |
| **ziarno potwierdzające (out-of-sample)** | **`20260819`** |
| ziarno członu (b) | `20260805`, aparatura K24b bez zmian |
| stratyfikacja, głębokość, zbiór taktów | bez zmian |

**Oba ziarna kampanii są nowe.** Ziarna `20260804` i `20260807` posłużyły do
wyprowadzenia postaci w fazach 0-2, więc dla K24e są ziarnami **w próbie**
i nie mogą potwierdzać niczego. Ziarna zapisane tutaj są jedynymi dopuszczonymi;
wynik negatywny na którymkolwiek jest wynikiem negatywnym. Nie wolno próbować
kolejnych ziaren i raportować najlepszego.

## 6. Kryteria

**Kryterium główne (per klasa, nigdy agregatem).** Na obu ziarnach, w atrybucji
izolowanej i w C1: zgodność 100% w klasie oznacza reżim „dokładna” i wsparcie
H10a-ex w tej klasie; jedna niezgodność falsyfikuje. Osobne tabele dla ogona
i dla początku logicznego.

**Kryterium bezpieczeństwa.** Zero klas w reżimie zaniżającym, osobno dla ogona
i dla origin.

**Kryterium end-to-end.** Bramka odwzorowania na podpróbie obu ziaren: zero
rozbieżności treści, zero awarii.

**Kryterium spójności pojemności.** `capacity.py` na obu ziarnach: zerowy
niedomiar we wszystkich klasach dla składowych deklarowanych (patrz P6).

**Kryterium członu (b).** Aparatura K24b, ziarno `20260805`, populacja i reguła
lokalna bez zmian: werdykt H10b ma pozostać wsparty. Zmiana jest wynikiem, nie
awarią — człon (b) porównuje regułę lokalną z **oracle'em**, nie z silnikiem,
więc naprawa rachunku silnika nie ma prawa nim poruszyć.

## 7. Bramki aparatury, które muszą przejść przed kampanią

| Bramka | Warunek |
|---|---|
| `tests/test_independence.py` | oracle nie importuje repliki i nie zawiera nazw rachunku silnika |
| `tests/test_oracle.py` | 100% zgodności z przypadkami o ręcznie wyprowadzonej odpowiedzi (ogon C1 i C2 oraz origin) |
| `tests/test_mutants.py` | 100% wykrycia zamrożonych mutantów, osobno dla rodziny ogona i origin |
| `tests/test_closedform.py` | replika zgodna ze zrzutem planu silnika co do ogona i origin |

Zestaw mutantów rozszerzono o **trzy** pozycje odpowiadające regułom zastąpionym
w fazie 3 (`subtract_declaration_slot`, `theta_constant_own`,
`ntheta_rounds_source_tail`) — tą samą zasadą, którą K24d dołożyła
`shift_tail_keeps_source` i `hash_closed_form_o1`: reguła, która odchodzi,
zostaje mutantem, żeby powrót do niej był wykrywany. Korpus ręczny dostał jeden
nowy przypadek (`~Θ` nad składową o niezerowym ogonie), bez którego mutant
`ntheta_rounds_source_tail` był niewykrywalny.

## 8. Co unieważnia ten przebieg

* zmiana `generator.py`, `oracle/model.py`, progów, konwencji lub przewidywań
  z §3 po dacie zamrożenia;
* uruchomienie kampanii na ziarnie innym niż `20260818` i `20260819`;
* jakakolwiek zmiana rachunku ogona lub origin w silniku po tej dacie;
* plan odrzucony przez kompilator (błąd aparatury, zatrzymuje iterację).

## 9. Semantyka ustalona przed pomiarem

Bez zmian wobec K24p §9: rekord `k` strumienia o takcie `D` jest określony
w chwili `(k+1)*D`, jednakowo dla deklaracji i strumieni obliczanych; strumień
jest ciągiem rekordów, nie zbiorem z dziurami (zasada ciągłości), a NULL nigdy
nie jest rezerwacją miejsca (zasada brzegu).
