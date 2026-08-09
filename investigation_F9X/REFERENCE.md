# Materiał porównawczy F9-X — punkt odniesienia dla naprawy

**Zebrany 2026-08-09 z zamkniętej kampanii K23 (iteracja 2).** Wszystkie liczby
tutaj są **odtworzone na hoście** i porównane z zapisem kampanii; nic nie jest
przepisane z pamięci.

Dowody kampanii są w `main`, nie w gałęzi: commit scalający
**`e7d238d`**, katalog `rdb-experiment/results_20260808_K23v2/`. Gałąź
`experiment/20260808_K23` może zniknąć — te odsyłacze przeżyją.

---

## 1. Co odtworzono i czy wiernie

| Wielkość | Wartość | Zgodność z zapisem K23 |
|---|---|---|
| seria RetractorDB `m1`, F9-X Q=1, profil DEFAULT | 4496 rekordów | **12/12 pierwszych co do cyfry** wobec `results_gates/f9x_reproducer.txt` |
| seria Flinka `m1`, wariant `natural`, Q=1 | 4500 rekordów | **5/5 pierwszych co do cyfry** wobec tego samego pliku |
| zgodność obu stron na wspólnym oknie | **5 / 4496 = 0,11%** | **dokładnie** tyle, ile zapisała kampania |

Odtworzenie biegło na hoście (x86-64), kampania mierzyła na workerze (aarch64).
P6 wykazała, że **832 publiczne artefakty są bajtowo identyczne między
architekturami**, więc host jest legalnym punktem odniesienia.

Pliki: `reference/rdb_m1.txt`, `reference/flink_m1_natural.txt`.

---

## 2. Przyczyna rozjazdu — ustalona, nie postawiona jako hipoteza

Monitor, o który chodzi (plan zamrożony `rql/F9_X_Q1.rql`):

```
DECLARE v INTEGER STREAM A, 1/100 FILE 'front_vib.txt'
DECLARE v INTEGER STREAM B, 1/50  FILE 'front_cur.txt'
DECLARE v INTEGER STREAM C, 1/100 FILE 'rear_vib.txt'
DECLARE v INTEGER STREAM D, 1/50  FILE 'rear_cur.txt'

SELECT Sqrt(A[0]*C[0]+B[0]*D[0]) STREAM m1 FROM ((A>2)#(B>1)) + ((C>2)#(D>1))
```

Dwa modele odczytu tego, czym jest `A[0]` **wewnątrz monitora, którego `FROM`
jest strumieniem przeplecionym**:

* **Model L — zatrzask per strumień składowy.** Każdy składnik ma własną,
  ostatnio widzianą wartość; slot przeplotu wnosi wartość dokładnie jednego
  z nich, reszta zachowuje poprzednią; przed pierwszym wystąpieniem 0.
  `A[0]` i `B[0]` są **rozróżnialne**.
* **Model S — wartość strumienia przeplecionego.** Tożsamość składników po `#`
  zanika; `A[0]` i `B[0]` odwzorowują się na tę samą wielkość. Program pola
  degeneruje się do `Sqrt(2 · HAB[0] · HCD[0])`.

**Wynik porównania na PEŁNEJ serii** (`reference/model_semantyk.py`):

| Porównanie | Okno | Zgodnych | Udział |
|---|---|---|---|
| RetractorDB ~ **model S** | 4496 | 4496 | **100,00%** |
| RetractorDB ~ model L | 4496 | 5 | 0,11% |
| Flink `natural` ~ **model L** | 4500 | 4500 | **100,00%** |
| Flink `natural` ~ model S | 4500 | 5 | 0,11% |
| RetractorDB ~ Flink `natural` | 4496 | 5 | 0,11% |

Pierwsze osiem slotów:

```
RetractorDB : [494, 1030, 1277, 440,  42, 621, 536, 751]
model S     : [494, 1030, 1277, 440,  42, 621, 536, 751]
Flink       : [349,  808,  968, 955, 312, 538, 580, 652]
model L     : [349,  808,  968, 955, 312, 538, 580, 652]
```

Te same 5 rekordów, na których obie strony się zgadzają, to przypadki, w których
oba modele dają tę samą liczbę — nie ślad częściowej zgodności semantyk.

**Bramka, żeby model nie odtwarzał własnego założenia.** `model_semantyk.py`
przed jakimkolwiek porównaniem sprawdza kształt przeplotu wobec **artefaktu
silnika** `STREAM_HASH_A_B` (4497 rekordów, zgodność pełna). Bez tej bramki
model potwierdzałby sam siebie — to jest ta klasa usterki, która w projekcie
wystąpiła sześć razy.

---

## 3. Minimalny reproducer — trzy linijki, bez Flinka i bez kampanii

`reproducer/minimal_identity.rql`:

```
SELECT A[0]-B[0] STREAM roznica FROM A#B
SELECT A[0]      STREAM tylko_a FROM A#B
SELECT B[0]      STREAM tylko_b FROM A#B
```

Wynik na silniku `ebd8aab`, profil DEFAULT, 4497 rekordów:

| Strumień | Pierwsze 10 | Niezerowych |
|---|---|---|
| `roznica` = `A[0]-B[0]` | `0, 0, 0, 0, 0, 0, 0, 0, 0, 0` | **0 / 4497** |
| `tylko_a` = `A[0]` | `333, 686, 889, 364, 307, 574, 216, 284, 396, 824` | 4490 |
| `tylko_b` = `B[0]` | `333, 686, 889, 364, 307, 574, 216, 284, 396, 824` | 4490 |

`A[0]` i `B[0]` dają **serie identyczne**, równe strumieniowi przeplecionemu,
a ich różnica jest **tożsamościowo zerem** — mimo że `A` i `B` to różne
strumienie o różnych wartościach i różnych taktach. To jest przyczyna rozjazdu
w postaci najkrótszej z możliwych i nadaje się wprost na test regresyjny.

---

## 4. Kontekst z kampanii — dlaczego nie złapało tego nic wcześniejszego

| Rodzina | Program pola | Przeplot `#` | Zgodność z Flinkiem |
|---|---|---|---|
| F9-R2 | `Sqrt(A[0]*A[0]+B[0]*B[0])` — **obce** strumienie | **nie** | 2999/2999 = **100%** |
| F9-R1 | `m[0]*m[0]` — **własny** strumień | tak | 4496/4496 = **100%** |
| F9-X | `Sqrt(A[0]*C[0]+B[0]*D[0])` — **obce** strumienie | tak | 5/4496 = **0,11%** |

Defekt wymaga **złożenia**: odwołania do obcych strumieni **przez** strumień
przepleciony. F9-R2 sprawdza obce strumienie bez przeplotu — działa. F9-R1 ma
przeplot, ale jej program pola odwołuje się wyłącznie do własnego strumienia,
więc tej ścieżki nie dotyka wcale. Żadna wcześniejsza komórka kampanii ani
żaden test w `retractordb` nie łączył obu warunków naraz.

---

## 5. Drugie znalezisko K23, jeszcze nie wyjaśnione

Rozjazd F9-X to **znalezisko B** z materiału STOP-6. Otwarte pozostaje
**znalezisko A**: profile z wyłączonym `RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES`
kończą strumień publiczny **o dwa rekordy wcześniej** (4494 wobec 4496),
przy wartościach identycznych na całym wspólnym oknie. Podział przebiega
dokładnie po przełączniku R1, niezależnie od `Q`, w obu rodzinach z przeplotem;
F9-R2 (bez przeplotu) jest czysta.

Oba znaleziska dotyczą przeplotu i oba zostały sklasyfikowane jako
`engine_or_profile`, ale **nie wiadomo, czy mają wspólną przyczynę** — to jest
osobne pytanie planu naprawy, nie założenie.

Uwaga o liczbach rekordów, którą trzeba mieć w głowie przy każdym porównaniu:
RetractorDB oddaje **4496** rekordów, Flink **4500**. Różnica ogona jest
przedmiotem `tab:tail-exactness` i łuku K24, nie tego śledztwa.

---

## 6. Proweniencja

| Pozycja | Wartość |
|---|---|
| Silnik | `ebd8aab826dc471c94c8dc2720af29a31718dbbc`, profil `K23-DEFAULT` (Release-Probe) |
| Kampania | `rdb-experiment/results_20260808_K23v2/` w `main`, commit scalający `e7d238d` |
| Dane | `data/main/` kampanii, ziarno `20260808_0001`, 3000/1500 rekordów |
| Flink | 2.3.0, JDK 17 przypięty ścieżką `/usr/lib/jvm/java-17-openjdk-amd64` |
| Odtworzenie | host x86-64, 2026-08-09 |
