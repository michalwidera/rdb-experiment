# K24r — predeklaracja potwierdzenia poza próbą

**Data zamrożenia:** 2026-08-04, przed uruchomieniem kampanii na nowym ziarnie
**Poprzednik:** [`results_20260803_K24`](../results_20260803_K24/) — kampania,
która sfalsyfikowała H10a-impl w sześciu klasach operatorów
**Kontekst:** `paper-arXiv/debs/research_plan.md` §K24, blok „KOREKTA H10a”

Dokument zamyka aparaturę przed kampanią. Aparatura (generator, oracle, progi,
stratyfikacja, konwencje dostępności) jest **skopiowana bez zmian** z K24;
jedyną różnicą jest ziarno korpusu i stan silnika. Zmiana którejkolwiek pozycji
po tej dacie unieważnia kampanię i wymaga nowej predeklaracji.

---

## 1. Po co ten przebieg

K24 zmierzyła postać zamkniętą ogona **zaimplementowaną w silniku** i odrzuciła
ją w sześciu klasach. Dla dwóch z nich (`+`, `@`) wyprowadzono następnie nowe
postacie zamknięte i wdrożono je w silniku. Wyprowadzenie powstało **znając
oracle'a i na tym samym korpusie**, z którego pochodzi falsyfikacja — jest więc
dopasowaniem po fakcie do momentu, w którym nie zostanie sprawdzone na korpusie
niewidzianym podczas wyprowadzania.

K24r ma dokładnie jeden cel: **rozstrzygnąć, czy nowe postacie działają poza
próbą**. Nie jest powtórzeniem K24 i nie unieważnia jej werdyktu.

## 2. Co jest twierdzone

**H10a-ex (`+`, `@`)** — dla każdego poprawnego planu RQL indeks pierwszego
w pełni określonego rekordu węzła `+` oraz węzła `@` jest równy granicy
z modelu zdarzeniowego i dany postaciami:

```
  `+` :  W = max_skł  ceil( (1 + W_skł) * D_skł / D_out ) - 1
  `@` :  W = ceil( (P + (1 + W_src) * F) / step ) - 1
         P = floor((|len| - 1) / gcd(F, step)) * gcd(F, step)
         F = szerokość rekordu źródła (liczba pól)
```

Twierdzona jest **równość**, nie oszacowanie z góry, w konwencji dostępności C1
(nieostrej — patrz `../results_20260803_K24/PREDECLARATION.md` §konwencje).
Konwencja C2 jest raportowana jako kolumna wrażliwości i **nie jest** przedmiotem
twierdzenia.

## 3. Czego ten przebieg nie twierdzi

* Nic o klasach `#`, `-`, `Θ`, `~Θ` — pozostają sfalsyfikowane przez K24
  i ich wyniki są tu raportowane wyłącznie jako tło, bez twierdzenia.
* Nic o wydajności, produktywności ani porównaniu międzysystemowym.
* Nie unieważnia werdyktu K24: tam mierzono inną postać zamkniętą.

## 4. Korpus i ziarno

| Pozycja | Wartość |
|---|---|
| generator | `generator.py`, skopiowany bez zmian z K24 |
| liczność | 10 010 planów |
| **ziarno potwierdzające (out-of-sample)** | **`20260804`** |
| ziarno porównawcze | `20260803` — ten sam korpus co K24, dla tabeli „przed/po” |
| stratyfikacja, głębokość, zbiór taktów | bez zmian wobec K24 |

Ziarno `20260804` jest zapisane **przed uruchomieniem** i jest jedynym ziarnem
potwierdzającym. Jeżeli wynik na nim wypadnie negatywnie, jest to wynik
negatywny — nie wolno próbować kolejnych ziaren i raportować najlepszego.

## 5. Kryteria

**Kryterium potwierdzenia (per klasa, nigdy agregatem):** na ziarnie `20260804`
zgodność postaci zamkniętej z oracle'em w C1 wynosi **100%** dla `+` oraz
**100%** dla `@`, zarówno w atrybucji izolowanej (ogony składowych brane
z oracle'a), jak i w replice pełnej (ogony liczone rekurencyjnie). Jedna
niezgodność w klasie falsyfikuje nową postać w tej klasie.

**Kryterium end-to-end:** bramka odwzorowania na podpróbie nowego ziarna daje
**zero rozbieżności treści** i **zero awarii**. Plany odrzucone przez budżet
czasu aparatury są raportowane osobno i nie liczą się ani na korzyść, ani na
niekorzyść.

**Kryterium spójności pojemności:** `capacity.py` na obu ziarnach daje zerowy
niedomiar we wszystkich klasach.

## 6. Co unieważnia ten przebieg

* zmiana `generator.py`, `oracle/`, progów lub konwencji po dacie zamrożenia;
* uruchomienie kampanii potwierdzającej na ziarnie innym niż `20260804`;
* jakakolwiek zmiana postaci zamkniętych w silniku po tej dacie — wtedy
  potrzebna jest nowa predeklaracja i nowe ziarno;
* plan odrzucony przez kompilator (błąd aparatury, zatrzymuje iterację).

## 7. Semantyka ustalona przed pomiarem

Chwila emisji rekordu deklaracji została rozstrzygnięta 2026-08-03:
rekord `k` strumienia o takcie `D` jest określony w chwili `(k+1)*D`,
jednakowo dla deklaracji i strumieni obliczanych (`research_plan.md` §K24).
K24r mierzy tę semantykę i żadnej innej.
