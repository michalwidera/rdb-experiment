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

## 4. Rozstrzygnięcie — M3 i M1 **obalone**, zostaje **M2**

Oracle mierzy granicę zdarzeniową **strumienia matematycznego**: kiedy dane
fizycznie istnieją. Silnik pracuje w modelu **emisji slotowej**. Pytanie brzmiało,
czy substrat jest przezroczysty (wariant M3) — sprawdzone 2026-08-09 w kodzie
wykonawczym.

### M3 obalone: substrat NIE jest przezroczysty

`dataModel::fetchForward()` (`dataModel.cpp:120`) czyta **zmaterializowane
rekordy źródła**, nie surowe dane:

```cpp
const auto count = static_cast<int>(out.getRecordsCount());   // ile zrodlo NAPRAWDE zapisalo
const int physical = forwardIndex - *logicalBase;
const int rev      = count - 1 - physical;
if (physical < 0 || rev < 0 || ...) {
    SPDLOG_ERROR("fetchForward {}: record {} not available ...");
    nullRecord.setNullBitset(... true);      // rekord ALL-NULL
    return nullRecord;
}
```

Gdy żądany rekord nie został jeszcze wydany, konsument **nie czeka** — dostaje
rekord all-NULL i wpis błędu. Gate emisji (`dataModel.cpp:215`,
`if (runtime.elapsedSlots++ < silentSlots) continue;`) jest bezwarunkowy:
w slotach ciszy strumień nie liczy i nie zapisuje niczego.

### M1 obalone tym samym

Ustawienie ogona nieczynnikowego przeplotu na 0 „bo dane fizycznie istnieją"
sprawiłoby, że `τ₁(B)` nie ma jeszcze zapisanego rekordu 1, a przeplot dostaje
**all-NULL**. To jest reżim zaniżający — realne zepsucie, nie poprawka.
Wartość 0 z oracle'a opisuje dane surowe, których runtime **nie wykorzystuje**.

### Mechanizm: R1 przenosi materializację na siatkę drobniejszą

| kształt | gdzie materializuje się pośrednik | `b₀` widoczne dla konsumenta |
|---|---|---|
| `(A>2)#(B>1)` | `τ₁(B)` na siatce **1/50** | koniec slotu 1 = **0,0400 s** |
| `(A#B)>3` | `A#B` na siatce **1/150** | koniec slotu 2 = **0,0200 s** |

Slot 3 przeplotu kończy się w 0,0267 s: postać czynnikowa zdąża, nieczynnikowa
nie — stąd jej dodatkowe dwa sloty ogona. **Oba wyniki są poprawne w modelu
silnika.** Różnica nie bierze się z błędnego wzoru, tylko z tego, że R1 zmienia
**rozdzielczość czasową pośrednika**.

### Werdykt M2, w postaci ostrzejszej niż w planie

> **Tożsamość shift-matching zachowuje wartości i indeksy logiczne, ale NIE
> zachowuje opóźnienia przy materializacji wyrównanej do slotów.**

Obie postacie emitują te same rekordy o tych samych indeksach; nieczynnikowa
zaczyna dwa sloty później, więc na przebiegu o ustalonej długości oddaje dwa
rekordy mniej. Dokładnie to zmierzyła K23.

### Co zostaje do decyzji człowieka

Nie „który wzór poprawić", tylko **czy R1 wolno tak działać**:

| Droga | Treść | Koszt |
|---|---|---|
| **D1** | uznać różnicę opóźnienia za dopuszczalną i doprecyzować twierdzenie o R1 w artykule („zachowuje wartości i indeksy, może skrócić brzeg") | tanie, bez zmian w silniku |
| **D2** | wymagać neutralności — R1 musi zachowywać łączną ciszę | koliduje z regułą `>N` z 2026-08-07, zmierzoną przez K24p jako usunięcie realnego zawyżenia |

To jest decyzja o treści artykułu, nie o kodzie.

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
