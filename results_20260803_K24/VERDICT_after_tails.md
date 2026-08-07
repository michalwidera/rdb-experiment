# K24 / H10 — werdykt

Korpus: **10010 planów**, **35827 obserwacji węzłowych**, zero błędów aparatury. Ziarno 20260803, silnik `5e3eb42` (PIN.md).

Werdykt jest raportowany per klasa operatora. Zgodność 100% jest jedynym
wsparciem H10a w klasie; jedna niezgodność falsyfikuje H10a w tej klasie.

## 1. H10a — dokładność, per klasa operatora

Kolumna **izolowana** jest werdyktem: postać zamknięta policzona z ogonów
składowych wziętych z oracle'a, więc niezgodność pochodzi z reguły tego
węzła. Kolumna **propagowana** to zgodność zrzutu planu silnika z oracle'em
na całym planie — zawiera skutki niezgodności odziedziczonych po dzieciach.

| Klasa | Węzłów | Izolowana C1 | Izolowana C2 | Propagowana C1 | Reżim | Werdykt H10a |
|---|---:|---:|---:|---:|---|---|
| `HASH` | 5995 | 90.9% | 46.4% | 82.2% | zawyżająca | **FALSYFIKACJA** |
| `SHIFT` | 5484 | 100.0% | 0.0% | 97.1% | dokładna | **wsparta** |
| `PASS` | 4704 | 100.0% | 0.0% | 96.8% | dokładna | **wsparta** |
| `AGSE` | 4309 | 100.0% | 29.4% | 97.3% | dokładna | **wsparta** |
| `SUB` | 4295 | 19.2% | 38.2% | 6.6% | zawyżająca | **FALSYFIKACJA** |
| `REDUCE` | 3265 | 100.0% | 0.0% | 98.8% | dokładna | **wsparta** |
| `NTHETA` | 2674 | 98.7% | 99.1% | 97.2% | zawyżająca | **FALSYFIKACJA** |
| `THETA` | 2574 | 59.9% | 87.5% | 53.5% | zawyżająca | **FALSYFIKACJA** |
| `ADD` | 2527 | 100.0% | 42.2% | 97.2% | dokładna | **wsparta** |

### Trzy reżimy

* **dokładna** (postać zamknięta == oracle wszędzie): `SHIFT`, `PASS`, `AGSE`, `REDUCE`, `ADD`;
* **zawyżająca** (nigdy nie zaniża, bezpieczna, ale nie równa): `HASH`, `SUB`, `NTHETA`, `THETA`;
* **zaniżająca** (ogon mniejszy od wymaganego przez model zdarzeniowy): brak.

Reżim zaniżający jest jakościowo inny od zawyżającego: zawyżenie
opóźnia emisję o slot, zaniżenie oznacza rekord wyemitowany, zanim
wszystkie jego zależności są określone.

### Rozkład różnicy (postać zamknięta − oracle C1)

| Klasa | Rozkład |
|---|---|
| `HASH` | `+0`: 5450 (90.9%), `+1`: 545 (9.1%) |
| `SHIFT` | `+0`: 5484 (100.0%) |
| `PASS` | `+0`: 4704 (100.0%) |
| `AGSE` | `+0`: 4309 (100.0%) |
| `SUB` | `+0`: 825 (19.2%), `+1`: 3470 (80.8%) |
| `REDUCE` | `+0`: 3265 (100.0%) |
| `NTHETA` | `+0`: 2639 (98.7%), `+1`: 35 (1.3%) |
| `THETA` | `+0`: 1543 (59.9%), `+1`: 1031 (40.1%) |
| `ADD` | `+0`: 2527 (100.0%) |

### Świadkowie

| Klasa | Kierunek | Plan | Węzeł | Interwał | Silnik | Postać zamknięta (izol.) | Oracle C1 |
|---|---|---:|---|---|---:|---:|---:|
| `HASH` | zawyżenie | 2 | n3 | `3/31` | 15 | 15 | 14 |
| `HASH` | zawyżenie | 23 | n1 | `147/1294` | 5 | 5 | 4 |
| `SUB` | zawyżenie | 4 | n0 | `3/10` | 1 | 1 | 0 |
| `SUB` | zawyżenie | 10 | n0 | `4/3` | 1 | 1 | 0 |
| `NTHETA` | zawyżenie | 895 | n5 | `5/3` | 1 | 1 | 0 |
| `NTHETA` | zawyżenie | 1049 | n3 | `1/10` | 2 | 2 | 1 |
| `THETA` | zawyżenie | 5 | n1 | `9/10` | 2 | 2 | 1 |
| `THETA` | zawyżenie | 5 | n2 | `2/3` | 1 | 1 | 0 |

## 2. H10b — nielokalność

* rozjazd reguły lokalnej A z dokładną: **5287 z 10010 planów = 52.8%** (próg predeklarowany: >= 5%)
* populacja predeklarowana (dokładnie jeden `#`, poza tym `PASS`/`>N`): **479 planów**, rozjazdów dodatnich **293**
* rozjazdów o predeklarowanej postaci `ceil((p+q-1)/p)`: **284 z 293** (96.9%; próg: 100%)

## 3. Kontrole negatywne

| Kontrola | Węzłów | Rozjazdów | Stan |
|---|---:|---:|---|
| HC_SINGLE (dosłownie) | 4165 | 43 | **ZŁAMANA** |
| HC_SINGLE (operatory bez własnego ogona) | 3897 | 0 | **przeszła** |
| HC_INT (dosłownie) | 6848 | 2893 | **ZŁAMANA** |
| HC_INT (węzły `#`, reguła lokalna B) | 2904 | 319 | **ZŁAMANA** |

Obie kontrole predeklarowane **w postaci dosłownej są złamane**.
Zgodnie z PREDECLARATION.md §6 oznacza to źle zdefiniowaną regułę
lokalną, a nie wynik — dlatego **człon (b) jest nieocenialny na tej
aparaturze** i powyższe liczby H10b nie stanowią werdyktu. Diagnoza
sprzeczności w specyfikacji członu (b): REPORT.md §5.

