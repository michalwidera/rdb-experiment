# K24 / H10 — werdykt

Korpus: **10010 planów**, **35544 obserwacji węzłowych**, zero błędów aparatury. Ziarno 20260804, silnik `c4b63a7` (PIN.md).

Werdykt jest raportowany per klasa operatora. Zgodność 100% jest jedynym
wsparciem H10a w klasie; jedna niezgodność falsyfikuje H10a w tej klasie.

## 1. H10a — dokładność, per klasa operatora

Kolumna **izolowana** jest werdyktem: postać zamknięta policzona z ogonów
składowych wziętych z oracle'a, więc niezgodność pochodzi z reguły tego
węzła. Kolumna **propagowana** to zgodność zrzutu planu silnika z oracle'em
na całym planie — zawiera skutki niezgodności odziedziczonych po dzieciach.

| Klasa | Węzłów | Izolowana C1 | Izolowana C2 | Propagowana C1 | Reżim | Werdykt H10a |
|---|---:|---:|---:|---:|---|---|
| `HASH` | 5960 | 90.8% | 45.3% | 81.5% | zawyżająca | **FALSYFIKACJA** |
| `SHIFT` | 5314 | 100.0% | 0.0% | 96.5% | dokładna | **wsparta** |
| `PASS` | 4825 | 100.0% | 0.0% | 96.6% | dokładna | **wsparta** |
| `SUB` | 4329 | 19.2% | 38.6% | 6.5% | zawyżająca | **FALSYFIKACJA** |
| `AGSE` | 4256 | 100.0% | 29.1% | 97.0% | dokładna | **wsparta** |
| `REDUCE` | 3292 | 100.0% | 0.0% | 98.7% | dokładna | **wsparta** |
| `THETA` | 2578 | 59.4% | 87.7% | 52.6% | zawyżająca | **FALSYFIKACJA** |
| `NTHETA` | 2503 | 98.6% | 99.4% | 97.5% | zawyżająca | **FALSYFIKACJA** |
| `ADD` | 2487 | 100.0% | 42.6% | 97.5% | dokładna | **wsparta** |

### Trzy reżimy

* **dokładna** (postać zamknięta == oracle wszędzie): `SHIFT`, `PASS`, `AGSE`, `REDUCE`, `ADD`;
* **zawyżająca** (nigdy nie zaniża, bezpieczna, ale nie równa): `HASH`, `SUB`, `THETA`, `NTHETA`;
* **zaniżająca** (ogon mniejszy od wymaganego przez model zdarzeniowy): brak.

Reżim zaniżający jest jakościowo inny od zawyżającego: zawyżenie
opóźnia emisję o slot, zaniżenie oznacza rekord wyemitowany, zanim
wszystkie jego zależności są określone.

### Rozkład różnicy (postać zamknięta − oracle C1)

| Klasa | Rozkład |
|---|---|
| `HASH` | `+0`: 5409 (90.8%), `+1`: 551 (9.2%) |
| `SHIFT` | `+0`: 5314 (100.0%) |
| `PASS` | `+0`: 4825 (100.0%) |
| `SUB` | `+0`: 831 (19.2%), `+1`: 3498 (80.8%) |
| `AGSE` | `+0`: 4256 (100.0%) |
| `REDUCE` | `+0`: 3292 (100.0%) |
| `THETA` | `+0`: 1531 (59.4%), `+1`: 1047 (40.6%) |
| `NTHETA` | `+0`: 2468 (98.6%), `+1`: 35 (1.4%) |
| `ADD` | `+0`: 2487 (100.0%) |

### Świadkowie

| Klasa | Kierunek | Plan | Węzeł | Interwał | Silnik | Postać zamknięta (izol.) | Oracle C1 |
|---|---|---:|---|---|---:|---:|---:|
| `HASH` | zawyżenie | 23 | n4 | `5/126` | 5 | 5 | 4 |
| `HASH` | zawyżenie | 58 | n1 | `3/22` | 5 | 5 | 4 |
| `SUB` | zawyżenie | 4 | n0 | `5/2` | 1 | 1 | 0 |
| `SUB` | zawyżenie | 4 | n1 | `5/4` | 1 | 1 | 0 |
| `THETA` | zawyżenie | 5 | n0 | `1` | 1 | 1 | 0 |
| `THETA` | zawyżenie | 5 | n1 | `3/4` | 1 | 1 | 0 |
| `NTHETA` | zawyżenie | 167 | n2 | `1/5` | 1 | 1 | 0 |
| `NTHETA` | zawyżenie | 209 | n4 | `3/32` | 2 | 2 | 1 |

## 2. H10b — nielokalność

* rozjazd reguły lokalnej A z dokładną: **5287 z 10010 planów = 52.8%** (próg predeklarowany: >= 5%)
* populacja predeklarowana (dokładnie jeden `#`, poza tym `PASS`/`>N`): **515 planów**, rozjazdów dodatnich **314**
* rozjazdów o predeklarowanej postaci `ceil((p+q-1)/p)`: **304 z 314** (96.8%; próg: 100%)

## 3. Kontrole negatywne

| Kontrola | Węzłów | Rozjazdów | Stan |
|---|---:|---:|---|
| HC_SINGLE (dosłownie) | 3929 | 52 | **ZŁAMANA** |
| HC_SINGLE (operatory bez własnego ogona) | 3645 | 0 | **przeszła** |
| HC_INT (dosłownie) | 6821 | 2861 | **ZŁAMANA** |
| HC_INT (węzły `#`, reguła lokalna B) | 2859 | 311 | **ZŁAMANA** |

Obie kontrole predeklarowane **w postaci dosłownej są złamane**.
Zgodnie z PREDECLARATION.md §6 oznacza to źle zdefiniowaną regułę
lokalną, a nie wynik — dlatego **człon (b) jest nieocenialny na tej
aparaturze** i powyższe liczby H10b nie stanowią werdyktu. Diagnoza
sprzeczności w specyfikacji członu (b): REPORT.md §5.

