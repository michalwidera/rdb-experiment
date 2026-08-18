# K24d / H10 — werdykt

Korpus: **10010 planów**, **35703 obserwacji węzłowych**, zero błędów aparatury. Ziarno 20260820, silnik `e2a61ff` (PIN.md).

Werdykt jest raportowany per klasa operatora. Zgodność 100% jest jedynym
wsparciem H10a w klasie; jedna niezgodność falsyfikuje H10a w tej klasie.

## 1. H10a — dokładność, per klasa operatora

Kolumna **izolowana** jest werdyktem: postać zamknięta policzona z ogonów
składowych wziętych z oracle'a, więc niezgodność pochodzi z reguły tego
węzła. Kolumna **propagowana** to zgodność zrzutu planu silnika z oracle'em
na całym planie — zawiera skutki niezgodności odziedziczonych po dzieciach.

| Klasa | Węzłów | Izolowana C1 | Izolowana C2 | Propagowana C1 | Reżim | Werdykt H10a |
|---|---:|---:|---:|---:|---|---|
| `HASH` | 5958 | 100.0% | 51.4% | 100.0% | dokładna | **wsparta** |
| `SHIFT` | 5395 | 100.0% | 95.8% | 100.0% | dokładna | **wsparta** |
| `PASS` | 4688 | 100.0% | 0.0% | 100.0% | dokładna | **wsparta** |
| `AGSE` | 4417 | 100.0% | 43.8% | 100.0% | dokładna | **wsparta** |
| `SUB` | 4376 | 100.0% | 71.7% | 100.0% | dokładna | **wsparta** |
| `REDUCE` | 3309 | 100.0% | 0.0% | 100.0% | dokładna | **wsparta** |
| `THETA` | 2574 | 100.0% | 69.9% | 100.0% | dokładna | **wsparta** |
| `NTHETA` | 2521 | 100.0% | 99.4% | 100.0% | dokładna | **wsparta** |
| `ADD` | 2465 | 100.0% | 43.0% | 100.0% | dokładna | **wsparta** |

### Trzy reżimy

* **dokładna** (postać zamknięta == oracle wszędzie): `HASH`, `SHIFT`, `PASS`, `AGSE`, `SUB`, `REDUCE`, `THETA`, `NTHETA`, `ADD`;
* **zawyżająca** (nigdy nie zaniża, bezpieczna, ale nie równa): brak;
* **zaniżająca** (ogon mniejszy od wymaganego przez model zdarzeniowy): brak.

Reżim zaniżający jest jakościowo inny od zawyżającego: zawyżenie
opóźnia emisję o slot, zaniżenie oznacza rekord wyemitowany, zanim
wszystkie jego zależności są określone.

### Rozkład różnicy (postać zamknięta − oracle C1)

| Klasa | Rozkład |
|---|---|
| `HASH` | `+0`: 5958 (100.0%) |
| `SHIFT` | `+0`: 5395 (100.0%) |
| `PASS` | `+0`: 4688 (100.0%) |
| `AGSE` | `+0`: 4417 (100.0%) |
| `SUB` | `+0`: 4376 (100.0%) |
| `REDUCE` | `+0`: 3309 (100.0%) |
| `THETA` | `+0`: 2574 (100.0%) |
| `NTHETA` | `+0`: 2521 (100.0%) |
| `ADD` | `+0`: 2465 (100.0%) |

### Świadkowie

| Klasa | Kierunek | Plan | Węzeł | Interwał | Silnik | Postać zamknięta (izol.) | Oracle C1 |
|---|---|---:|---|---|---:|---:|---:|

## 1b. H10a — początek logiczny, per klasa operatora

Wielkość wprowadzona przestemplowaniem z 2026-08-06 i nieobecna
w kampaniach K24/K24r. Kolumna **suma** porównuje origin+ogon —
to jedyna wielkość wspólna z kampaniami sprzed zmiany.

| Klasa | Węzłów | Izolowana | Propagowana | Suma (origin+ogon) | Reżim | Werdykt |
|---|---:|---:|---:|---:|---|---|
| `HASH` | 5958 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |
| `SHIFT` | 5395 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |
| `PASS` | 4688 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |
| `AGSE` | 4417 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |
| `SUB` | 4376 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |
| `REDUCE` | 3309 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |
| `THETA` | 2574 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |
| `NTHETA` | 2521 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |
| `ADD` | 2465 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |

### Rozkład różnicy origin (rachunek silnika − oracle)

| Klasa | Rozkład |
|---|---|
| `HASH` | `+0`: 5958 (100.0%) |
| `SHIFT` | `+0`: 5395 (100.0%) |
| `PASS` | `+0`: 4688 (100.0%) |
| `AGSE` | `+0`: 4417 (100.0%) |
| `SUB` | `+0`: 4376 (100.0%) |
| `REDUCE` | `+0`: 3309 (100.0%) |
| `THETA` | `+0`: 2574 (100.0%) |
| `NTHETA` | `+0`: 2521 (100.0%) |
| `ADD` | `+0`: 2465 (100.0%) |

Origin zaniżony (odczyt przed początkiem źródła): **brak**.

## 2. H10b — nielokalność

* rozjazd reguły lokalnej A z dokładną: **5275 z 10010 planów = 52.7%** (próg predeklarowany: >= 5%)
* populacja predeklarowana (dokładnie jeden `#`, poza tym `PASS`/`>N`): **492 planów**, rozjazdów dodatnich **351**
* rozjazdów o predeklarowanej postaci `ceil((p+q-1)/p)`: **351 z 351** (100.0%; próg: 100%)

## 3. Kontrole negatywne

| Kontrola | Węzłów | Rozjazdów | Stan |
|---|---:|---:|---|
| HC_SINGLE (dosłownie) | 4098 | 0 | **przeszła** |
| HC_SINGLE (operatory bez własnego ogona) | 3809 | 0 | **przeszła** |
| HC_INT (dosłownie) | 6890 | 3192 | **ZŁAMANA** |
| HC_INT (węzły `#`, reguła lokalna B) | 2878 | 345 | **ZŁAMANA** |

Obie kontrole predeklarowane **w postaci dosłownej są złamane**.
Zgodnie z PREDECLARATION.md §6 oznacza to źle zdefiniowaną regułę
lokalną, a nie wynik — dlatego **człon (b) jest nieocenialny na tej
aparaturze** i powyższe liczby H10b nie stanowią werdyktu. Diagnoza
sprzeczności w specyfikacji członu (b): REPORT.md §5.

