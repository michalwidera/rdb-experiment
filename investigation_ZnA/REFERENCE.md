# Znalezisko A — oracle granicy zdarzeniowej i korpus kształtów

**Zebrane 2026-08-09.** Silnik `9f1bb33` (po dwóch naprawach kompilatora z tego
samego dnia). Plan pracy: `paper-arXiv/debs/plan-znalezisko-A.md`.
Wszystko compile-only i deterministyczne — **to nie jest kampania pomiarowa**.

---

## 1. Co tu jest

| Plik | Co robi |
|---|---|
| `oracle_boundary.py` | niezależny oracle granicy zdarzeniowej, zbudowany **wyłącznie** z definicji formalnych artykułu (`eq:interleave`, `eq:sum`, `eq:shift`); bramka mutantów |
| `corpus_check.py` | 196 kształtów × oracle wobec silnika; sprawdza też kandydacką regułę naprawy |
| `oracle_result.txt`, `corpus_result.txt` | zapisane wyjścia obu |

Oracle **nie importuje** kodu RetractorDB i nie odtwarza jego postaci zamkniętych.

---

## 2. Wynik główny — kierunek błędu

Korpus 196 kształtów (7 par taktów × przesunięcia 0–3 po obu stronach × `#` i `+`,
plus postacie z przesunięciem po operatorze), silnik w budowie **R1 OFF**, żeby
oglądać kształt **napisany**, a nie przepisany:

| | liczba |
|---|---|
| silnik zgodny z oracle | **89** |
| silnik **zawyża** ogon | **107** |
| silnik **zaniża** ogon | **0** |

**Zero zaniżeń na całym korpusie.** Reżim niebezpieczny — wydanie rekordu, który
nie jest jeszcze określony — **nie występuje**. Konfiguracja `DEFAULT` jest
zachowawcza, nie wadliwa w tę stronę. To wyklucza najcięższą z trzech gałęzi
rozważanych w §1 planu.

Bramka mutantów przechodzi: dla każdego kształtu `W` wystarcza, a `W−1` nie —
oracle umie odróżnić wartość przesuniętą o jeden. Na kształtach bezspornych
(`A#B`, `A+B`, obie postacie czynnikowe) oracle **odtwarza silnik co do liczby**,
co jest kontrolą aparatury: model zmyślony rozjechałby się i tam.

---

## 3. Wynik uboczny — kandydacka reguła naprawy **OBALONA**

Naiwna poprawka „odejmij od ogona ciszę już zapisaną w originie",
`W' = max(0, W − O)`, odtwarza oracle tylko **159/196**. Chybia **37 razy**,
w tym w sposób **niebezpieczny**:

```
(A>1)+B   oracle (1,1)   silnik (1,1)   regula dalaby (1,0)  <- ZANIZENIE
(A>2)+B   oracle (2,1)   silnik (2,1)   regula dalaby (2,0)  <- ZANIZENIE
(A#B)>1   oracle (1,1)   silnik (1,1)   regula dalaby (1,0)  <- ZANIZENIE
A#(B>1)   oracle (1,0)   silnik (1,2)   regula dalaby (1,1)  <- za malo koryguje
```

Reguła zepsułaby **przypadki, w których silnik jest dziś poprawny**, i to
w kierunku zaniżającym. Gdyby naprawę oprzeć na ośmiu kształtach z kroku 3,
weszłaby do silnika. **Korpus jest tu bramką, nie ozdobą.**

---

## 4. Pytanie, które to otworzyło — do rozstrzygnięcia przez człowieka

Oracle mierzy granicę zdarzeniową **strumienia matematycznego**: kiedy dane
fizycznie istnieją. Silnik pracuje w modelu **emisji slotowej**: strumień wydaje
rekord `n` w slocie `n+W`, więc konsument nie zobaczy go wcześniej niż na końcu
tego slotu — **nawet jeśli dane istniały wcześniej**.

Dla `(A>2)#(B>1)` te dwa modele dają różne odpowiedzi:

* granica zdarzeniowa (oracle): **0** — `b₀` istnieje w 0,02 s, a slot 3 kończy
  się w 0,0267 s;
* model emisji slotowej: **2** — substrat `τ₂(A)` wydaje rekord `j` dopiero
  w slocie `j`, więc przeplot nie ma czego wziąć wcześniej.

**Oba są wewnętrznie spójne.** To nie jest więc pytanie „który wzór jest zły",
tylko **który model brzegu obowiązuje w RetractorDB** — i dopiero z niego wynika,
która strona ustępuje.

Niezależnie od odpowiedzi **defekt zostaje**, bo dotyczy czegoś innego:
`(A>2)#(B>1)` i `(A#B)>3` to **ten sam strumień**, a silnik wydaje dla nich
różną liczbę rekordów. Reguła R1 nie jest więc obserwacyjnie neutralna w modelu
emisji slotowej — a artykuł opisuje ją jako przepisanie zachowujące semantykę.

Trzy możliwe rozstrzygnięcia, każde o innym zasięgu:

| Wariant | Treść | Skutek |
|---|---|---|
| **M1** | obowiązuje granica zdarzeniowa | ogon liczyć jak oracle; zmiana dotyka 107/196 kształtów, w tym `+` w konfiguracji domyślnej |
| **M2** | obowiązuje emisja slotowa | ogony są poprawne, a defektem jest **R1**: przepisanie skraca ciszę o 2 sloty, więc nie jest neutralne |
| **M3** | emisja slotowa, ale substraty przezroczyste | rozjazd znika, jeżeli substrat nie narzuca własnego slotu emisji — do sprawdzenia w `dataModel` |

**M3 jest warta sprawdzenia przed wyborem M1/M2**, bo mogłaby usunąć rozjazd
bez zmiany żadnej postaci zamkniętej.

---

## 5. Jak odtworzyć

```bash
# budowa profilu bez czynnikowania R1 (kształt napisany, nie przepisany)
cmake -S <retractordb> -B build-r1off -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=<conan_toolchain.cmake> -DCMAKE_BUILD_TYPE=Release \
  -DRDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=OFF
cmake --build build-r1off --target xretractor

./oracle_boundary.py
./corpus_check.py build-r1off/src/retractor/xretractor <katalog-roboczy>
```

---

## 6. Proweniencja

| Pozycja | Wartość |
|---|---|
| Silnik | `9f1bb33` (zawiera naprawy `[AGSE-shift-uaf]` i usunięcie UB `--it2`) |
| Objaw źródłowy | `results_20260808_K23v2/STOP-6_MATERIAL.md`, znalezisko A |
| Definicje formalne | `paper-arXiv/debs/main-debs.tex`: `eq:interleave`, `eq:sum`, `eq:shift` |
| Odtworzenie | host x86-64, 2026-08-09, compile-only |
