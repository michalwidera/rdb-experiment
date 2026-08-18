# K24d / H10 — werdykt

Korpus: **10009 planów**, **35919 obserwacji węzłowych**, zero błędów aparatury. Ziarno 20260819, silnik `e2a61ff` (PIN.md).

Werdykt jest raportowany per klasa operatora. Zgodność 100% jest jedynym
wsparciem H10a w klasie; jedna niezgodność falsyfikuje H10a w tej klasie.

## 1. H10a — dokładność, per klasa operatora

Kolumna **izolowana** jest werdyktem: postać zamknięta policzona z ogonów
składowych wziętych z oracle'a, więc niezgodność pochodzi z reguły tego
węzła. Kolumna **propagowana** to zgodność zrzutu planu silnika z oracle'em
na całym planie — zawiera skutki niezgodności odziedziczonych po dzieciach.

| Klasa | Węzłów | Izolowana C1 | Izolowana C2 | Propagowana C1 | Reżim | Werdykt H10a |
|---|---:|---:|---:|---:|---|---|
| `HASH` | 5962 | 100.0% | 49.8% | 100.0% | dokładna | **wsparta** |
| `SHIFT` | 5447 | 100.0% | 95.8% | 100.0% | dokładna | **wsparta** |
| `PASS` | 4824 | 100.0% | 0.0% | 100.0% | dokładna | **wsparta** |
| `SUB` | 4380 | 100.0% | 71.6% | 100.0% | dokładna | **wsparta** |
| `AGSE` | 4272 | 100.0% | 42.8% | 100.0% | dokładna | **wsparta** |
| `REDUCE` | 3322 | 100.0% | 0.0% | 100.0% | dokładna | **wsparta** |
| `THETA` | 2642 | 100.0% | 66.8% | 100.0% | dokładna | **wsparta** |
| `NTHETA` | 2547 | 100.0% | 99.3% | 100.0% | dokładna | **wsparta** |
| `ADD` | 2523 | 100.0% | 43.7% | 100.0% | dokładna | **wsparta** |

### Trzy reżimy

* **dokładna** (postać zamknięta == oracle wszędzie): `HASH`, `SHIFT`, `PASS`, `SUB`, `AGSE`, `REDUCE`, `THETA`, `NTHETA`, `ADD`;
* **zawyżająca** (nigdy nie zaniża, bezpieczna, ale nie równa): brak;
* **zaniżająca** (ogon mniejszy od wymaganego przez model zdarzeniowy): brak.

Reżim zaniżający jest jakościowo inny od zawyżającego: zawyżenie
opóźnia emisję o slot, zaniżenie oznacza rekord wyemitowany, zanim
wszystkie jego zależności są określone.

### Rozkład różnicy (postać zamknięta − oracle C1)

| Klasa | Rozkład |
|---|---|
| `HASH` | `+0`: 5962 (100.0%) |
| `SHIFT` | `+0`: 5447 (100.0%) |
| `PASS` | `+0`: 4824 (100.0%) |
| `SUB` | `+0`: 4380 (100.0%) |
| `AGSE` | `+0`: 4272 (100.0%) |
| `REDUCE` | `+0`: 3322 (100.0%) |
| `THETA` | `+0`: 2642 (100.0%) |
| `NTHETA` | `+0`: 2547 (100.0%) |
| `ADD` | `+0`: 2523 (100.0%) |

### Świadkowie

| Klasa | Kierunek | Plan | Węzeł | Interwał | Silnik | Postać zamknięta (izol.) | Oracle C1 |
|---|---|---:|---|---|---:|---:|---:|

## 1b. H10a — początek logiczny, per klasa operatora

Wielkość wprowadzona przestemplowaniem z 2026-08-06 i nieobecna
w kampaniach K24/K24r. Kolumna **suma** porównuje origin+ogon —
to jedyna wielkość wspólna z kampaniami sprzed zmiany.

| Klasa | Węzłów | Izolowana | Propagowana | Suma (origin+ogon) | Reżim | Werdykt |
|---|---:|---:|---:|---:|---|---|
| `HASH` | 5962 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |
| `SHIFT` | 5447 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |
| `PASS` | 4824 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |
| `SUB` | 4380 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |
| `AGSE` | 4272 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |
| `REDUCE` | 3322 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |
| `THETA` | 2642 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |
| `NTHETA` | 2547 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |
| `ADD` | 2523 | 100.0% | 100.0% | 100.0% | dokładna | **wsparta** |

### Rozkład różnicy origin (rachunek silnika − oracle)

| Klasa | Rozkład |
|---|---|
| `HASH` | `+0`: 5962 (100.0%) |
| `SHIFT` | `+0`: 5447 (100.0%) |
| `PASS` | `+0`: 4824 (100.0%) |
| `SUB` | `+0`: 4380 (100.0%) |
| `AGSE` | `+0`: 4272 (100.0%) |
| `REDUCE` | `+0`: 3322 (100.0%) |
| `THETA` | `+0`: 2642 (100.0%) |
| `NTHETA` | `+0`: 2547 (100.0%) |
| `ADD` | `+0`: 2523 (100.0%) |

Origin zaniżony (odczyt przed początkiem źródła): **brak**.

## 2. H10b — nielokalność

* rozjazd reguły lokalnej A z dokładną: **5302 z 10009 planów = 53.0%** (próg predeklarowany: >= 5%)
* populacja predeklarowana (dokładnie jeden `#`, poza tym `PASS`/`>N`): **528 planów**, rozjazdów dodatnich **360**
* rozjazdów o predeklarowanej postaci `ceil((p+q-1)/p)`: **360 z 360** (100.0%; próg: 100%)

## 3. Kontrole negatywne

| Kontrola | Węzłów | Rozjazdów | Stan |
|---|---:|---:|---|
| HC_SINGLE (dosłownie) | 3986 | 0 | **przeszła** |
| HC_SINGLE (operatory bez własnego ogona) | 3752 | 0 | **przeszła** |
| HC_INT (dosłownie) | 6816 | 3129 | **ZŁAMANA** |
| HC_INT (węzły `#`, reguła lokalna B) | 2842 | 344 | **ZŁAMANA** |

Obie kontrole predeklarowane **w postaci dosłownej są złamane**.
Zgodnie z PREDECLARATION.md §6 oznacza to źle zdefiniowaną regułę
lokalną, a nie wynik — dlatego **człon (b) jest nieocenialny na tej
aparaturze** i powyższe liczby H10b nie stanowią werdyktu. Diagnoza
sprzeczności w specyfikacji członu (b): REPORT.md §5.

