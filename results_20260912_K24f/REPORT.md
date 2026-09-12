# K24f — raport

Kampania H10 dla **reguły okna rekordowego** w liście `SELECT`, na silniku
`098e531` (gałąź `master`). Predeklaracja zamrożona przed przebiegiem
([`PREDECLARATION.md`](PREDECLARATION.md), commit `cfed5e5`), przypięcie
w [`PIN.md`](PIN.md), werdykty w [`VERDICT.md`](VERDICT.md)
i [`VERDICT_oos.md`](VERDICT_oos.md), zatrzymanie poziomu bramki odwzorowania
i jego zniesienie w [`STOP.md`](STOP.md).

---

## 1. Po co ta kampania istniała

Po K24e `compiler::computeLogicalOrigin()` dostał regułę, której **żadna kampania
ani bramka nie zmierzyła i zmierzyć nie mogła**:

```cpp
if (const auto width = windowWidthOf(q, windowError); width.has_value()) result = o1 + *width - 1;
```

Generator korpusu K24e wypisywał wyłącznie `SELECT * STREAM <n> FROM <wyrażenie>`,
a `windowWidthOf()` szuka tokenów `WINDOW_*` w programach pól listy `SELECT` —
których `SELECT *` nie ma ani jednego. Bramka świeciła na zielono, bo nie miała
jak zaświecić inaczej. Reguła stała przy tym już w snapshocie przypiętym jako
domyślny silnik odtworzeniowy pakietu artefaktu.

K24f zamyka tę lukę: korpus został rozszerzony o stratę okna rekordowego,
a model zdarzeniowy o niezależne wyprowadzenie tej samej wielkości.

## 2. Wynik w jednym zdaniu

**H10a-win wsparta na obu ziarnach: początek logiczny i ogon klasy `WINDOW`
zgadzają się z modelem zdarzeniowym w 100% węzłów, a dziewięć klas K24e nie
wykazuje regresji — 10/10 klas dokładnych w obu wielkościach jednocześnie.**

## 3. Werdykty

| | ziarno główne `20260912` | ziarno potwierdzające `20260913` |
|---|---|---|
| planów | 10 010 | 10 010 |
| obserwacji węzłowych | 36 162 | 36 089 |
| błędów aparatury | 0 | 0 |
| **H10a** | **WSPARTA** — 10/10 klas dokładnych | **WSPARTA** — 10/10 klas dokładnych |
| **H10b** | WSPARTA — rozjazd 53,0%, 2276/2276 dodatnich, 2276/2276 co do postaci | WSPARTA — rozjazd 52,9%, 2200/2200 dodatnich, 2200/2200 co do postaci |

Procedura decyzyjna `decision_rule.py` uruchomiona **raz na ziarno**, przed
naprawą aparatury opisaną w `STOP.md`, i nie powtarzana.

Populacja klasy `WINDOW`: **784** i **769** węzłów.

## 4. Rozliczenie predeklarowanych przewidywań

| # | Przewidywanie | Wynik | Liczby |
|---|---|---|---|
| **P1** | origin klasy `WINDOW` dokładny, oba ziarna | **potwierdzone** | 784/784 i 769/769 |
| **P2** | ogon `WINDOW` dokładny i **równy ogonowi producenta** | **potwierdzone** | 784/784 i 769/769 |
| **P3** | dziewięć pozostałych klas dokładnych, bez regresji wobec K24e | **potwierdzone** | 100,00% na obu wielkościach, oba ziarna |
| **P4** | zero klas w reżimie zaniżającym | **potwierdzone** | zero węzłów zaniżonych, ogon i origin |
| **P5** | bramka odwzorowania: zero rozbieżności treści | **potwierdzone w przebiegu powtórzonym** | 119/120 zgodnych na ziarno, 0 rozbieżności; pierwszy przebieg dał 3 rozbieżności o przyczynie aparaturowej — patrz `STOP.md` |
| **P6** | populacja `WINDOW` >= 500 na ziarno | **potwierdzone** | 784 i 769 |

**P2 wymaga podkreślenia, bo jest przewidywaniem nowym wobec wszystkich kampanii
K24.** Zostało sprawdzone nie przez odczyt reżimu klasy, a przez **rekonstrukcję
planu i dotarcie do producenta każdego węzła okna**: dla wszystkich 1553 węzłów
`WINDOW` obu ziaren ogon wyznaczony przez silnik równa się ogonowi producenta.
Okno rusza więc wyłącznie początek logiczny — i to jest teraz zmierzone, a nie
wywnioskowane z tego, że `computeStartupLatency()` o oknie nie wie.

**P5 ma zastrzeżenie i nie wolno go czytać jako „przeszło od razu".** Pierwszy
przebieg bramki odwzorowania wypadł negatywnie (3 rozbieżności treści na
226 przebiegów), przyczynę zdiagnozowano jako granicę aparatury — wymiarowanie
przebiegu pomijało narosły początek logiczny i myliło sloty z taktami najszybszego
strumienia — aparaturę naprawiono na wyraźną zgodę człowieka, a poziom powtórzono.
Pełna sekwencja z liczbami przed i po: [`STOP.md`](STOP.md).

## 5. Wynik poza predeklaracją, wart zapisania

Postać zamknięta reguły, **policzona wprost wobec zrzutu planu silnika**, bez
pośrednictwa repliki:

```
O = O_src + W - 1,   W = najszersze okno listy SELECT
```

trafia **784/784** i **769/769** węzłów. Ma to znaczenie epistemiczne: gdyby
replika i silnik dzieliły ten sam błąd, porównanie repliki z silnikiem tego nie
pokazałoby. Tu porównana została postać wypisana z lektury kodu z wartością
odczytaną ze zrzutu, dla każdego węzła osobno.

Model zdarzeniowy **nie zawiera** tej postaci: `oracle/model.py` ma wyłącznie
listę zależności `n-(W-1) … n`, a origin wychodzi ze skanu. Bramka
`tests/test_independence.py` przeszła na przypiętym silniku, czyli oracle nadal
nie importuje repliki.

## 6. Zestawienie wobec K24e

| Pozycja | K24e (`e2a61ff`) | K24f (`098e531`) |
|---|---|---|
| przedmiot twierdzenia | ogon i origin, dziewięć klas | **wyłącznie** origin okna rekordowego; dziewięć klas jako kontrola regresji |
| klas w werdykcie | 9 | **10** |
| klas dokładnych (ogon) | 9/9 | 10/10 |
| klas dokładnych (origin) | 9/9 | 10/10 |
| ziarna | `20260818`, `20260819` | `20260912`, `20260913` |
| korpus | `STRATA`, 14 strat | `STRATA_WITH_WINDOW`, **15** strat |
| planów na stratę | 715 | 667 (pięć pierwszych po 668) |
| człon (b) | wsparty, 2310/2310 | wsparty, 2276/2276 i 2200/2200 |

**K24e nie jest wyparta.** Zakres twierdzenia K24f jest wąski i nie obejmuje
rachunku ogona pozostałych klas, który jest tym samym kodem, co zmierzyła K24e.
Łańcuch K24 → K24r → K24b → K24p → K24d → K24e → K24f rośnie o ogniwo; żadne
poprzednie nie przestaje obowiązywać dla swojego stanu silnika.

**Korpus K24e nie drgnął** i jest to sprawdzone, nie założone: korpus 10 010
planów wyprodukowany kodem K24e i kodem przypiętym daje tę samą sumę SHA-256 na
oba zamrożone ziarna (`PIN.md` §5.1). Potwierdza to niezależnie `ninja test_gate`,
który na przypiętym silniku daje dalej 9/9 i 9/9.

## 7. Status epistemiczny

**To nie jest test prospektywny reguły.** Aparatura powstała po tym, jak reguła
weszła do silnika; przy jej budowie reguła była znana i zmierzona na siedmiu
planach ręcznych. Predeklarowane były **ziarna, kryteria i przewidywania**, nie
hipoteza.

Status do raportowania dosłownie: **potwierdzenie poza próbą na ziarnach
nieużytych przy budowie aparatury**. Aparatura była budowana i uruchamiana
wyłącznie na ziarnie spalonym `20260803`; oba ziarna kampanii były przed
zamrożeniem predeklaracji nietknięte i nie występowały w żadnym pliku żadnego
z czterech repozytoriów.

Zielona K24f znaczy **„reguła okna rekordowego zgadza się z modelem zdarzeniowym
na przypiętym SHA"** — nie „silnik jest poprawny".

## 8. Czego K24f nie rozstrzygnęła

* **Progu czasowego H9** — inna kampania, inny sprzęt, ~48 h na przypiętym pi400
  pod `PREEMPT_RT`.
* **Niczego o wydajności** — badanie jest compile-only, bez workera i bez pomiaru
  czasu. Jedynym elementem uruchamiającym silnik jest bramka odwzorowania.
* **Członu (b) H10** — porównuje regułę lokalną z oracle'em, nie z silnikiem;
  potwierdzony w K24e i tutaj tylko odnotowany.
* **Kontraktu typu `tan`/`log`/`log2` i `Sqrt` nad `INTEGER`** — wada otwarta,
  poza zakresem korpusu (`PIN.md` §3). Ustalenie tej sesji: `Sqrt` należy do tej
  samej klasy co tamte trzy, a korpus H9 stoi na `Sqrt(INTEGER)` w 14 z 21 planów,
  więc spójna naprawa zmienia format artefaktu.
* **Kształtu „okno nad oknem"** — wyłączony z generatora, bo węzeł okna ma pola
  `RATIONAL` i model treści liczyłby słowa źródła źle. Reguła origin składa się
  tam poprawnie (zmierzone) i kształt pilnuje przypadek ręczny, ale w korpusie
  losowym go nie ma.

## 9. Znaleziska aparaturowe tej kampanii

Dwa, oba naprawione, oba udokumentowane:

1. **Wymiarowanie przebiegu bramki odwzorowania** — pomijało narosły początek
   logiczny i myliło budżet slotów z taktami najszybszego strumienia. Objawem
   były rozbieżności treści `zero rekordów` na planach z łańcuchem `>N`. Naprawa
   po decyzji człowieka, przebieg powtórzony; pokrycie **wzrosło** (119 wobec 114
   i 112 zgodnych). Szczegóły: [`STOP.md`](STOP.md).
2. **Zaszyta dziewiątka klas w `decision_rule.py`** — `EXPECTED_CLASSES` był stałą,
   więc korpus z dziesiątą klasą oblewałby się na aparaturze. Zestaw oczekiwany
   wyprowadzany jest teraz ze **straty zapisanej w wierszach CSV**, co nie ma jak
   rozejść się z korpusem, który faktycznie przebiegł. Strażnik zachowany w obie
   strony i pokryty trzema nowymi przypadkami samotestu. Naprawione w Fazie 2,
   przed zamrożeniem predeklaracji.

## 10. Wada predeklaracji do poprawienia w następnej

§6 żąda „zero rozbieżności treści", a §8 mówi, że błąd aparatury zatrzymuje
iterację i nie jest wynikiem o silniku. Dla rozbieżności **spowodowanej
aparaturą** oba zdania dają sprzeczne odczyty. Predeklaracja nie była poprawiana
po fakcie; następna musi z góry mówić, że rozbieżność z przyczyną aparaturową
jest zatrzymaniem poziomu, a nie falsyfikacją przewidywania.
