# STOP-6 — materiał do klasyfikacji przez człowieka

**Data: 2026-08-09. Faza P6 (bramki przed odczytem kosztów), iteracja 2.**
**Kosztów nie otwarto.** Ten dokument nie zawiera żadnej klasyfikacji — §7.1
predeklaracji i §5A.2 przypisują ją człowiekowi, a asystentowi wyłącznie
przygotowanie materiału.

Do rozstrzygnięcia są **dwa niezależne znaleziska**. Każde może dostać osobną
klasyfikację, bo dotyczą różnych bramek i różnych rodzin.

| Rodzina | oracle_values | oracle_mutants | counter_known_answer | public_identity | near_miss_controls | no_materialization |
|---|---|---|---|---|---|---|
| **F9-R2** | PASS | PASS | PASS | PASS | PASS | PASS |
| **F9-R1** | PASS | PASS | PASS | **FAIL** | PASS | PASS |
| **F9-X** | **FAIL** | PASS | PASS | **FAIL** | PASS | PASS |

**Skąd te liczby.** Strona RetractorDB: 84 komórki (4 profile × 21 planów) na
danych głównych, wykonane **na workerze** (`pi400`, aarch64, binaria ANEKS-2),
każda z niezerowym mianownikiem i licznikami `LOGICAL`/`WORK`. Strona Flinka:
36 przebiegów z `env.execute()` na hoście, `--slots 3000`. Ten sam komplet
przebiegnięto **niezależnie na hoście** (x86-64, binaria §1.4) i **832 publiczne
artefakty są bajtowo identyczne między architekturami — zero różnic**, więc
żadne ze znalezisk nie jest efektem maszyny.

`verdict.py` na tym `gates.tsv` kończy się **kodem 2 — BRAK WERDYKTU**, dokładnie
dlatego, że kolumna `classification` przy `FAIL` jest pusta. Tak ma być: kodu 2
nie wolno obejść, a wypełnić go może wyłącznie człowiek.

Klasyfikacja rozstrzyga o dwóch różnych rzeczach (§7.1, §8.3):

* **silnik albo profil** → *brak wsparcia H9 w rodzinie*; wynik **zostaje
  w kampanii**, iteracja biegnie dalej, rodziny się nie podmienia;
* **defekt portu, oracle'a albo harnessu** → **zatrzymanie iteracji**, nowa
  wersja, **bez łączenia danych** z tą.

---

## Znalezisko A — `public_identity`: profile różnią się DŁUGOŚCIĄ, nie wartościami

**Bramka:** §7.1, „dla RetractorDB także identyczność publicznych artefaktów
między profilami". **Rodziny:** F9-R1 (68 rozbieżności) i F9-X (66). F9-R2
czysta.

**Kształt rozbieżności jest jeden, powtórzony w każdej komórce:**

```
F9_R1_Q8/m1 DEFAULT~NO_R1_FACTOR: [record_count_tail]
   4496 wobec 4494 rekordow, roznica -2, zadeklarowany ogon 0
```

| Profil | R1 factor | rekordów publicznych `m1` |
|---|---|---|
| `DEFAULT` | ON | **4496** |
| `NO_R2_CANON` | ON | **4496** |
| `NO_R1_FACTOR` | **OFF** | **4494** |
| `NO_R1_NO_R2` | **OFF** | **4494** |

**Wartości są identyczne na całym wspólnym oknie 4494 rekordów** — rozbieżność
dotyczy wyłącznie tego, że profile z wyłączonym R1 kończą strumień publiczny
**dwa rekordy wcześniej**. Podział przebiega dokładnie po `RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES`,
niezależnie od `Q` i niezależnie od rodziny (F9-R1 i F9-X, czyli obie rodziny
z przeplotem; F9-R2, która przeplotu nie ma, jest czysta).

**Co to znaczy operacyjnie:** przy zamrożonym progu §7.3 punkt 4 brzmi
„publiczne wyniki i ich materializacja pozostają identyczne". Dwa rekordy ogona
różnicy to 18 B kanonicznych na 40 464 B publicznych, czyli 0,04% — ale bramka
jest binarna i predeklaracja nie przewiduje tu marginesu.

**Czego to NIE jest:** nie jest różnicą wartości, kolejności, deskryptora ani
mapy `NULL`/luk. Wszystkie te warunki przeszły — rozbieżność zatrzymała się
dokładnie na warunku liczby rekordów, po zdanym warunku deskryptora.

**Materiał:** `results_gates/rdb/<profil>/<plan>/temp/`, pełna lista
w `results_gates/gates_run.log`.

---

## Znalezisko B — `oracle_values`: F9-X rozjeżdża się z Flinkiem od rekordu 0

**Bramka:** §7.1, wspólny oracle wartości. **Rodzina:** wyłącznie **F9-X**
(126 rozbieżności — wszystkie `Q`, oba warianty Flinka). F9-R2 i F9-R1 zgodne
**co do rekordu**.

```
Monitor: SELECT Sqrt(A[0]*C[0]+B[0]*D[0]) STREAM m1
         FROM ((A>2)#(B>1)) + ((C>2)#(D>1))

slot | RetractorDB DEFAULT | Flink natural
   0 |                 494 |           349
   1 |                1030 |           808
   2 |                1277 |           968
   3 |                 440 |           955
   4 |                  42 |           312
```

Na wspólnym oknie 4496 rekordów zgodnych jest **5 (0,11%)** — tyle, ile daje
przypadek. Źródła do sprawdzenia ręcznego:

```
A = front_vib 1/100: 686, 889, 307, 574, 284, 396, 193, 85
B = front_cur 1/50 : 333, 364, 216, 824, 432, 998, 729, 996
C = rear_vib  1/100: 774, 918,   3, 336, 993, 402, 308, 825
D = rear_cur  1/50 : 367, 266, 666, 838, 516, 695, 292, 98
```

### Zestawienie, które zawęża miejsce rozjazdu

| Rodzina | program pola | przeplot `#` | zgodność z Flinkiem |
|---|---|---|---|
| F9-R2 | `Sqrt(A[0]*A[0]+B[0]*B[0])` — **obce** strumienie | **nie** | 2999/2999 = **100%** |
| F9-R1 | `m[0]*m[0]` — **własny** strumień | tak | 4496/4496 = **100%** |
| F9-X | `Sqrt(A[0]*C[0]+B[0]*D[0])` — **obce** strumienie | tak | 5/4496 = **0,11%** |

Rozjazd występuje **dokładnie i tylko** tam, gdzie program pola sięga po
**obce strumienie poprzez strumień przepleciony**. F9-R2 sprawdza rozwiązywanie
pól obcych bez przeplotu (działa). F9-R1 sprawdza przeplot bez pól obcych —
jej program odwołuje się wyłącznie do własnego strumienia (`m1[0]*m1[0]`), więc
tej ścieżki **nie dotyka wcale**. Złożenia obu nie sprawdzała do tej pory żadna
komórka kampanii.

Po stronie portu jedyną implementacją tego rozwiązywania jest `latch[]`
w `K23Ops.AddFeature` — tablica ostatnio widzianej wartości per znacznik
strumienia. Po stronie silnika odpowiada za to rozwiązywanie pól nad węzłem
`STREAM_HASH_*`.

### Co przemawia za tym, że port jest wewnętrznie spójny

* `FLINK_NATURAL` i `FLINK_MANUAL` dają **identyczne ciągi wartości** we
  wszystkich trzech rodzinach (0 różnic), mimo że mają różne grafy operatorów.
* Bramka serializera kanonicznego przechodzi 18/18 wobec oracle'a C++
  linkującego `librdb.a`.

### Co przemawia za tym, że silnik jest wewnętrznie spójny

* Wszystkie **cztery profile** RetractorDB dają w F9-X **identyczne wartości**
  na wspólnym oknie (0 różnic) — żaden profil nie jest wyróżniony.
* F9-R2 i F9-R1 zgadzają się z Flinkiem co do rekordu na danych głównych.

**Żadna z tych obserwacji nie jest klasyfikacją.** Obie strony są wewnętrznie
spójne i rozjeżdżają się ze sobą; rozstrzygnięcie, która realizuje zamierzoną
semantykę `Sqrt(A[0]*C[0]+B[0]*D[0])` nad `((A>2)#(B>1)) + ((C>2)#(D>1))`,
jest decyzją człowieka.

---

## Co zostało sprawdzone i jest czyste

* **`oracle_mutants` — 20 mutantów, wszystkie odrzucone przez warunek
  ZAMIERZONY** i po zdaniu wszystkich warunków wcześniejszych. Pokazane
  **przed** wariantem poprawnym, zgodnie z regułą łuku. Cztery mechanizmy
  (F9-R2, F9-R1, F9-X, artefakt wielopolowy) × pięć klas mutanta
  (faza/shift, kolejność pola, mapa `NULL`, luka, brak rekordu ogona).
* **`counter_known_answer` — 36 przypadków** o znanej odpowiedzi:
  8 (`probeCanonicalRecord`) + 6 (`probeLogicalWrite`) na liczniku oraz 22
  (`probeLogicalGate`) prowadzone przez `storage::write()`. Wymagane ≥ 30.
* **`near_miss_controls`** — żadna para near-miss nie została scalona wspólnym
  węzłem `STREAM_SELECT_*` w żadnym z czterech profili; przy `Q=1` `DEFAULT`
  nie jest tańszy od ablacji minimalnej.
* **`no_materialization`** — w żadnym profilu ani planie kontrolnym nie powstał
  substrat nad źródłem `ZA`; warunek jest niepusty, bo `ZA` **jest** w planie
  i **są** nad nim strumienie (`z1`, `z2`), tyle że publiczne.

## Dwie decyzje aparatury, które podjęto w tej fazie i które wymagają potwierdzenia

**1. Wartość `-m` jest różna per rodzina.** Predeklaracja §4 zamraża **liczbę
rekordów źródła** (3000 szybkiego, 1500 wolnego), a po stronie Flinka realizuje
ją `--slots 3000`. Po stronie RetractorDB `-m` jest limitem **iteracji pętli**,
nie licznikiem rekordów, więc przelicznik zależy od taktu planu. Zmierzone:
`-m 3000` dla F9-R2 (oba źródła `1/100`) i `-m 6000` dla F9-R1 oraz F9-X, gdzie
przeplot `1/150` ma wtedy 4500 rekordów, czyli dokładnie `3000 + 1500` — obydwa
źródła skonsumowane w całości. Iteracja 1 i pilot używały `-m 100` na danych
miniaturowych, więc ta pozycja nie była wcześniej ustalona. **To jest realizacja
zamrożonej liczby, nie jej zmiana** — ale warto to potwierdzić.

**2. `oracle_values` porównuje z Flinkiem profil `DEFAULT`.** Pozostałe trzy
profile wchodzą do porównania przez `public_identity`. Przy znalezisku A ta
przechodniość jest **przerwana** dla profili z wyłączonym R1: ich zgodność
z Flinkiem nie jest tym samym stwierdzeniem, co zgodność `DEFAULT`. Wartości na
wspólnym oknie są identyczne we wszystkich czterech profilach, więc różnica
dotyczy wyłącznie długości ogona — ale zapisuję to jawnie, żeby nie wyglądało
na sprawdzone mocniej, niż jest.

## Uwaga do kryterium `near_miss_controls`

Predeklaracja mówi „kontrole near-miss nie mogą zostać scalone", ale nie podaje
kryterium operacyjnego. Przyjęto: **scaleniem jest wspólny węzeł
`STREAM_SELECT_*`**, bo tworzy go `shareEquivalentSelectComputations()`, czyli
mechanizm, którego kontrola dotyczy, i to jego liczbę zlicza §3.2 oraz §0.3.

Powód, dla którego to trzeba było rozstrzygnąć: kontrola F9-X jest zbudowana
jako „jedna para dopasowana, druga nie" (komentarz w zamrożonym
`F9_X_controls.rql`), więc `h1` i `h2` **dzielą** w `DEFAULT` substrat
dopasowanej pary `STREAM_TIMEMOVE_STREAM_HASH_HA_HB` — i to jest zamierzone.
Kryterium ostrzejsze (pełna rozłączność substratów) uznałoby tę kontrolę za
scaloną. **Kryterium zostało wybrane po zobaczeniu tych liczb i wymaga
potwierdzenia człowieka.**
