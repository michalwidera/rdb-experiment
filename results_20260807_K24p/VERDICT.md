# K24p / H10 — werdykt

Korpus: **10010 planów**, **35544 obserwacji węzłowych**, zero błędów aparatury. Ziarno 20260804, silnik `db4a360` (PIN.md).

Werdykt jest raportowany per klasa operatora. Zgodność 100% jest jedynym
wsparciem H10a w klasie; jedna niezgodność falsyfikuje H10a w tej klasie.

## 1. H10a — dokładność, per klasa operatora

Kolumna **izolowana** jest werdyktem: postać zamknięta policzona z ogonów
składowych wziętych z oracle'a, więc niezgodność pochodzi z reguły tego
węzła. Kolumna **propagowana** to zgodność zrzutu planu silnika z oracle'em
na całym planie — zawiera skutki niezgodności odziedziczonych po dzieciach.

| Klasa | Węzłów | Izolowana C1 | Izolowana C2 | Propagowana C1 | Reżim | Werdykt H10a |
|---|---:|---:|---:|---:|---|---|
| `HASH` | 5960 | 92.1% | 44.4% | 81.6% | zawyżająca | **FALSYFIKACJA** |
| `SHIFT` | 5314 | 93.4% | 91.6% | 90.4% | zawyżająca | **FALSYFIKACJA** |
| `PASS` | 4825 | 100.0% | 0.0% | 96.4% | dokładna | **wsparta** |
| `SUB` | 4329 | 19.1% | 37.6% | 6.4% | zawyżająca | **FALSYFIKACJA** |
| `AGSE` | 4256 | 100.0% | 43.7% | 97.0% | dokładna | **wsparta** |
| `REDUCE` | 3292 | 100.0% | 0.0% | 98.6% | dokładna | **wsparta** |
| `THETA` | 2578 | 59.7% | 87.9% | 52.9% | zawyżająca | **FALSYFIKACJA** |
| `NTHETA` | 2503 | 99.2% | 99.4% | 98.0% | zawyżająca | **FALSYFIKACJA** |
| `ADD` | 2487 | 100.0% | 42.9% | 97.5% | dokładna | **wsparta** |

### Trzy reżimy

* **dokładna** (postać zamknięta == oracle wszędzie): `PASS`, `AGSE`, `REDUCE`, `ADD`;
* **zawyżająca** (nigdy nie zaniża, bezpieczna, ale nie równa): `HASH`, `SHIFT`, `SUB`, `THETA`, `NTHETA`;
* **zaniżająca** (ogon mniejszy od wymaganego przez model zdarzeniowy): brak.

Reżim zaniżający jest jakościowo inny od zawyżającego: zawyżenie
opóźnia emisję o slot, zaniżenie oznacza rekord wyemitowany, zanim
wszystkie jego zależności są określone.

### Rozkład różnicy (postać zamknięta − oracle C1)

| Klasa | Rozkład |
|---|---|
| `HASH` | `+0`: 5489 (92.1%), `+1`: 471 (7.9%) |
| `SHIFT` | `+0`: 4961 (93.4%), `+1`: 199 (3.7%), `+2`: 95 (1.8%), `+3`: 32 (0.6%), `+4`: 9 (0.2%), `+5`: 7 (0.1%), `+6`: 1 (0.0%), `+7`: 2 (0.0%), `+8`: 8 (0.2%) |
| `PASS` | `+0`: 4825 (100.0%) |
| `SUB` | `+0`: 828 (19.1%), `+1`: 3501 (80.9%) |
| `AGSE` | `+0`: 4256 (100.0%) |
| `REDUCE` | `+0`: 3292 (100.0%) |
| `THETA` | `+0`: 1540 (59.7%), `+1`: 1038 (40.3%) |
| `NTHETA` | `+0`: 2483 (99.2%), `+1`: 20 (0.8%) |
| `ADD` | `+0`: 2487 (100.0%) |

### Świadkowie

| Klasa | Kierunek | Plan | Węzeł | Interwał | Silnik | Postać zamknięta (izol.) | Oracle C1 |
|---|---|---:|---|---|---:|---:|---:|
| `HASH` | zawyżenie | 23 | n4 | `5/126` | 4 | 4 | 3 |
| `HASH` | zawyżenie | 58 | n1 | `3/22` | 5 | 5 | 4 |
| `SHIFT` | zawyżenie | 10 | n4 | `1/5` | 2 | 2 | 0 |
| `SHIFT` | zawyżenie | 55 | n3 | `1/3` | 5 | 2 | 1 |
| `SUB` | zawyżenie | 4 | n0 | `5/2` | 1 | 1 | 0 |
| `SUB` | zawyżenie | 4 | n1 | `5/4` | 1 | 1 | 0 |
| `THETA` | zawyżenie | 5 | n0 | `1` | 1 | 1 | 0 |
| `THETA` | zawyżenie | 5 | n1 | `3/4` | 1 | 1 | 0 |
| `NTHETA` | zawyżenie | 167 | n2 | `1/5` | 1 | 1 | 0 |
| `NTHETA` | zawyżenie | 209 | n4 | `3/32` | 1 | 1 | 0 |

## 1b. H10a — początek logiczny, per klasa operatora

Wielkość wprowadzona przestemplowaniem z 2026-08-06 i nieobecna
w kampaniach K24/K24r. Kolumna **suma** porównuje origin+ogon —
to jedyna wielkość wspólna z kampaniami sprzed zmiany.

| Klasa | Węzłów | Izolowana | Propagowana | Suma (origin+ogon) | Reżim | Werdykt |
|---|---:|---:|---:|---:|---|---|
| `HASH` | 5960 | 100.0% | 100.0% | 81.6% | dokładna | **wsparta** |
| `SHIFT` | 5314 | 100.0% | 100.0% | 90.4% | dokładna | **wsparta** |
| `PASS` | 4825 | 100.0% | 100.0% | 96.4% | dokładna | **wsparta** |
| `SUB` | 4329 | 100.0% | 100.0% | 6.4% | dokładna | **wsparta** |
| `AGSE` | 4256 | 100.0% | 100.0% | 97.0% | dokładna | **wsparta** |
| `REDUCE` | 3292 | 100.0% | 100.0% | 98.6% | dokładna | **wsparta** |
| `THETA` | 2578 | 100.0% | 100.0% | 52.9% | dokładna | **wsparta** |
| `NTHETA` | 2503 | 100.0% | 100.0% | 98.0% | dokładna | **wsparta** |
| `ADD` | 2487 | 100.0% | 100.0% | 97.5% | dokładna | **wsparta** |

### Rozkład różnicy origin (rachunek silnika − oracle)

| Klasa | Rozkład |
|---|---|
| `HASH` | `+0`: 5960 (100.0%) |
| `SHIFT` | `+0`: 5314 (100.0%) |
| `PASS` | `+0`: 4825 (100.0%) |
| `SUB` | `+0`: 4329 (100.0%) |
| `AGSE` | `+0`: 4256 (100.0%) |
| `REDUCE` | `+0`: 3292 (100.0%) |
| `THETA` | `+0`: 2578 (100.0%) |
| `NTHETA` | `+0`: 2503 (100.0%) |
| `ADD` | `+0`: 2487 (100.0%) |

Origin zaniżony (odczyt przed początkiem źródła): **brak**.

## 2. H10b — nielokalność

* rozjazd reguły lokalnej A z dokładną: **5250 z 10010 planów = 52.4%** (próg predeklarowany: >= 5%)
* populacja predeklarowana (dokładnie jeden `#`, poza tym `PASS`/`>N`): **515 planów**, rozjazdów dodatnich **353**
* rozjazdów o predeklarowanej postaci `ceil((p+q-1)/p)`: **353 z 353** (100.0%; próg: 100%)

## 3. Kontrole negatywne

| Kontrola | Węzłów | Rozjazdów | Stan |
|---|---:|---:|---|
| HC_SINGLE (dosłownie) | 3929 | 0 | **przeszła** |
| HC_SINGLE (operatory bez własnego ogona) | 3645 | 0 | **przeszła** |
| HC_INT (dosłownie) | 6821 | 3168 | **ZŁAMANA** |
| HC_INT (węzły `#`, reguła lokalna B) | 2859 | 346 | **ZŁAMANA** |

Obie kontrole predeklarowane **w postaci dosłownej są złamane**.
Zgodnie z PREDECLARATION.md §6 oznacza to źle zdefiniowaną regułę
lokalną, a nie wynik — dlatego **człon (b) jest nieocenialny na tej
aparaturze** i powyższe liczby H10b nie stanowią werdyktu. Diagnoza
sprzeczności w specyfikacji członu (b): REPORT.md §5.

