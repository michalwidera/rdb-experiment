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
| `HASH` | 5995 | 90.9% | 46.4% | 80.4% | zawyżająca | **FALSYFIKACJA** |
| `SHIFT` | 5484 | 100.0% | 0.0% | 95.1% | dokładna | **wsparta** |
| `PASS` | 4704 | 100.0% | 0.0% | 94.7% | dokładna | **wsparta** |
| `AGSE` | 4309 | 31.8% | 52.0% | 25.4% | ZANIŻAJĄCA | **FALSYFIKACJA** |
| `SUB` | 4295 | 19.2% | 38.2% | 5.8% | zawyżająca | **FALSYFIKACJA** |
| `REDUCE` | 3265 | 100.0% | 0.0% | 97.2% | dokładna | **wsparta** |
| `NTHETA` | 2674 | 98.7% | 99.1% | 96.6% | zawyżająca | **FALSYFIKACJA** |
| `THETA` | 2574 | 59.9% | 87.5% | 53.2% | zawyżająca | **FALSYFIKACJA** |
| `ADD` | 2527 | 42.3% | 1.0% | 8.8% | ZANIŻAJĄCA | **FALSYFIKACJA** |

### Trzy reżimy

* **dokładna** (postać zamknięta == oracle wszędzie): `SHIFT`, `PASS`, `REDUCE`;
* **zawyżająca** (nigdy nie zaniża, bezpieczna, ale nie równa): `HASH`, `SUB`, `NTHETA`, `THETA`;
* **zaniżająca** (ogon mniejszy od wymaganego przez model zdarzeniowy): `AGSE`, `ADD`.

Reżim zaniżający jest jakościowo inny od zawyżającego: zawyżenie
opóźnia emisję o slot, zaniżenie oznacza rekord wyemitowany, zanim
wszystkie jego zależności są określone.

### Rozkład różnicy (postać zamknięta − oracle C1)

| Klasa | Rozkład |
|---|---|
| `HASH` | `+0`: 5450 (90.9%), `+1`: 545 (9.1%) |
| `SHIFT` | `+0`: 5484 (100.0%) |
| `PASS` | `+0`: 4704 (100.0%) |
| `AGSE` | `-6`: 1 (0.0%), `-2`: 273 (6.3%), `-1`: 256 (5.9%), `+0`: 1371 (31.8%), `+1`: 2408 (55.9%) |
| `SUB` | `+0`: 825 (19.2%), `+1`: 3470 (80.8%) |
| `REDUCE` | `+0`: 3265 (100.0%) |
| `NTHETA` | `+0`: 2639 (98.7%), `+1`: 35 (1.3%) |
| `THETA` | `+0`: 1543 (59.9%), `+1`: 1031 (40.1%) |
| `ADD` | `-99`: 1 (0.0%), `-66`: 5 (0.2%), `-62`: 9 (0.4%), `-49`: 6 (0.2%), `-44`: 2 (0.1%), `-39`: 16 (0.6%), `-37`: 9 (0.4%), `-33`: 16 (0.6%), `-29`: 8 (0.3%), `-26`: 1 (0.0%), `-24`: 12 (0.5%), `-23`: 1 (0.0%), `-19`: 14 (0.6%), `-15`: 37 (1.5%), `-14`: 9 (0.4%), `-12`: 17 (0.7%), `-10`: 13 (0.5%), `-9`: 45 (1.8%), `-8`: 2 (0.1%), `-7`: 20 (0.8%), `-6`: 59 (2.3%), `-5`: 31 (1.2%), `-4`: 73 (2.9%), `-3`: 161 (6.4%), `-2`: 301 (11.9%), `-1`: 589 (23.3%), `+0`: 1070 (42.3%) |

### Świadkowie

| Klasa | Kierunek | Plan | Węzeł | Interwał | Silnik | Postać zamknięta (izol.) | Oracle C1 |
|---|---|---:|---|---|---:|---:|---:|
| `HASH` | zawyżenie | 2 | n3 | `3/31` | 15 | 15 | 14 |
| `HASH` | zawyżenie | 23 | n1 | `147/1294` | 5 | 5 | 4 |
| `AGSE` | zawyżenie | 7 | n3 | `1/24` | 3 | 3 | 2 |
| `AGSE` | zawyżenie | 21 | n1 | `1/2` | 1 | 1 | 0 |
| `AGSE` | **zaniżenie** | 7 | n0 | `1/48` | 4 | 4 | 5 |
| `AGSE` | **zaniżenie** | 7 | n2 | `1/48` | 3 | 3 | 4 |
| `SUB` | zawyżenie | 4 | n0 | `3/10` | 1 | 1 | 0 |
| `SUB` | zawyżenie | 10 | n0 | `4/3` | 1 | 1 | 0 |
| `NTHETA` | zawyżenie | 895 | n5 | `5/3` | 1 | 1 | 0 |
| `NTHETA` | zawyżenie | 1049 | n3 | `1/10` | 2 | 2 | 1 |
| `THETA` | zawyżenie | 5 | n1 | `9/10` | 2 | 2 | 1 |
| `THETA` | zawyżenie | 5 | n2 | `2/3` | 1 | 1 | 0 |
| `ADD` | **zaniżenie** | 3 | n0 | `1/8` | 0 | 0 | 1 |
| `ADD` | **zaniżenie** | 17 | n0 | `1/3` | 0 | 0 | 2 |

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

