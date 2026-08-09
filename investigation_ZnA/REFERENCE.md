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

## 4. Rozstrzygnięcie — **to nie jest defekt silnika, tylko bramki K23**

### 4.1. M3 i M1 obalone w kodzie wykonawczym

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
rekord all-NULL i wpis błędu. Gate emisji (`dataModel.cpp:215`) jest
bezwarunkowy: w slotach ciszy strumień nie liczy i nie zapisuje.

* **M3 (substrat przezroczysty) — obalone.** Przezroczysty nie jest.
* **M1 (obowiązuje granica zdarzeniowa) — obalone tym samym.** Ogon 0 dla
  kształtu nieczynnikowego dałby odczyt rekordu jeszcze niezapisanego, czyli
  realny reżim zaniżający. Wartość 0 z oracle'a opisuje **dane surowe**, których
  runtime nie wykorzystuje.

Mechanizm właściwy: **R1 przenosi materializację pośrednika na siatkę
drobniejszą** — `τ₁(B)` na 1/50 udostępnia `b₀` w 0,0400 s, a `A#B` na 1/150
w 0,0200 s, przy slocie 3 przeplotu kończącym się w 0,0267 s.

### 4.2. Werdykt: artykuł już to twierdzi i **dowodzi**

Decyzja człowieka **D1** (2026-08-09) brzmiała: uznać różnicę opóźnienia za
dopuszczalną i doprecyzować twierdzenie o R1 w artykule. Sprawdzenie artykułu
**przed** wprowadzeniem poprawki wykazało, że **poprawki nie ma czego
wprowadzać**.

`def:observable` dzieli obserwację na część wartościową i opóźnieniową i żąda
`Val(P) = Val(Q)` **dokładnie**, ale tylko `Lat(Q) <= Lat(P)` — przepisaniu
**wolno skrócić** oczekiwanie, nigdy wydłużyć. Uzasadnienie stoi w artykule
wprost:

> *„The asymmetry is deliberate and was forced on us by measurement, not chosen
> for convenience… Demanding equality of $W_U$ would declare that rewrite
> unsound, although no observer can distinguish its output except by receiving
> it sooner."*

`thm:shift-match` orzeka dla tożsamości R1:

> *„the two plans agree on the entire value part — interval, logical origin, and
> record sequence — while the right-hand side has a tail **no larger** than the
> left, and **strictly smaller for some rates**. The identity is thus an equality
> of results and an inequality of latencies."*

Zmierzone: lewa `(A>2)#(B>1)` ma ogon **2**, prawa `(A#B)>3` ma **0**. To jest
dokładnie przypadek przewidziany przez twierdzenie, **po właściwej stronie
nierówności**. Profil `DEFAULT` ma R1 włączone, więc jest tą krótszą stroną.

> **Znalezisko A nie jest defektem silnika. Jest defektem bramki
> `public_identity` kampanii K23**, która żądała identyczności publicznych
> artefaktów **między profilami**, podczas gdy profile różnią się dokładnie tym,
> czy R1 jest stosowane — a R1 **wolno** skrócić ogon. Bramka była zatem
> **ostrzejsza niż `def:observable`**, czyli niż relacja równoważności, którą
> sama kampania deklarowała jako obowiązującą.

Silnik przez cały czas zachowywał się zgodnie z własną, dowiedzioną teorią.

### 4.3. Co z tego wynika

* **Dla artykułu: nic.** Zapis jest poprawny i pokrywa ten przypadek z dowodem;
  `main-debs.tex` i `main-debs-pl.tex` pozostają nietknięte.
* **Dla przyszłej predeklaracji:** bramka porównująca artefakty **między
  profilami** musi respektować asymetrię `Lat`, inaczej odrzuca przepisania,
  które sama teoria dopuszcza. Dołącza to do pozycji `[F9-kat]`
  w `research_plan.md` §15.
* **Otwarte, do decyzji człowieka:** czy przeklasyfikować rozbieżność F9-R1
  z `engine_or_profile` na `apparatus`. Jeżeli tak, **obie** nieczyste rodziny
  iteracji 2 K23 są `apparatus`, co wzmacnia zapisany już wniosek „iteracja 2
  bez werdyktu", nie zmieniając go.

Zapis trwały: `paper-arXiv/debs/research_plan.md` §14.20.

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
