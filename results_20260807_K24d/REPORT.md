# K24d — raport

Kampania na silniku `34db1a2`, po dwóch naprawach z 2026-08-07: kroku 3d
(`>N`, `fcc5a44`) i kroku 3c (`#`, `34db1a2`). Punkt odniesienia i zmiany
aparatury: [PIN.md](PIN.md). Werdykty: [VERDICT.md](VERDICT.md) (ziarno
`20260804`), [VERDICT_oos.md](VERDICT_oos.md) (ziarno `20260807`).

## 1. Po co powtórzenie

K24p opisuje `db4a360`. Tego samego dnia dwie klasy operatorów zmieniły reżim,
więc gdyby artykuł raportował liczby K24p, a pakiet artefaktów wysyłał silnik
po naprawach, recenzent odtwarzający kampanię dostałby inną tabelę niż ta
w tekście. Dokładnie to zdarzyło się między K24r a K24p i jest opisane w planie
jako reguła: **kampania semantyczna jest ważna wyłącznie dla przypiętego SHA.**

K24d nie stawia nowej hipotezy. Dostarcza jednej rzeczy, której nie da się
wyprowadzić z papieru: **kolumny „silnik wobec oracle'a” dla stanu, który
faktycznie pójdzie do pakietu artefaktów.**

## 2. Wynik — ogon, per klasa

Kolumna izolowana jest werdyktem (reguła węzła policzona z ogonów składowych
wziętych z oracle'a), propagowana pokazuje zgodność zrzutu planu silnika
na całym planie.

| Klasa | Izolowana K24p → K24d | Propagowana K24p → K24d | Reżim K24d |
|---|---|---|---|
| `HASH` (`#`) | 92,1% → **100%** | 81,6% → 92,7% | **dokładna** |
| `SHIFT` (`>N`) | 93,4% → **100%** | 90,4% → 99,5% | **dokładna** |
| `PASS` | 100% → 100% | 96,4% → 97,1% | dokładna |
| `AGSE` (`@`) | 100% → 100% | 97,0% → 97,6% | dokładna |
| `REDUCE` | 100% → 100% | 98,6% → 98,7% | dokładna |
| `ADD` (`+`) | 100% → 100% | 97,5% → 97,6% | dokładna |
| `NTHETA` (`~Θ`) | 99,2% → 99,2% | 98,0% → 98,1% | zawyżająca |
| `THETA` (`Θ`) | 59,7% → 59,7% | 52,9% → 52,9% | zawyżająca |
| `SUB` (`-`) | 19,1% → 19,1% | 6,4% → 6,6% | zawyżająca |

Ziarno `20260804`; na ziarnie `20260807` te same wnioski i te same reżimy
(`HASH` 92,0% → 100%, `SHIFT` 93,4% → 100%, pozostałe bez zmian).

**Sześć klas dokładnych, trzy zawyżające, zero zaniżających.** Rozkład różnicy
dla klas zawyżających jest niezmieniony wobec K24p i wynosi dokładnie jeden
slot: `SUB` `+1` w 80,9% węzłów, `THETA` `+1` w 40,3%, `NTHETA` `+1` w 0,8%.

## 3. Kontrola zasięgu napraw

Porównanie wiersz po wierszu z surowymi danymi K24p (ten sam korpus co do
węzła, `generator.py` bajtowo bez zmian):

| Wielkość | Gdzie się zmieniła wobec K24p |
|---|---|
| reguła **izolowana** | wyłącznie `SHIFT` (353 i 357 węzłów) i `HASH` (471 i 482) |
| ogon **silnika** (propagowany) | dodatkowo `PASS`, `AGSE`, `ADD`, `SUB`, `THETA`, `NTHETA`, `REDUCE` |
| **origin** | nigdzie, na żadnym ziarnie |

Pierwszy wiersz jest kontrolą zasięgu: naprawy miały dotknąć dwóch reguł
i dotknęły **dokładnie** dwóch. Liczby zgadzają się co do węzła z rozmiarem
niezgodności zmierzonych w K24p (`SHIFT` 6,6% z 5314, `HASH` 7,9% z 5960) —
naprawione zostały te węzły, które kampania wskazała, i żadne inne.

Drugi wiersz nie jest usterką, tylko dziedziczeniem: ogon węzła `PASS` nad
naprawionym `>N` zmienia się, choć reguła `PASS` jest nietknięta. Rozdzielenie
tych dwóch kolumn jest jedynym powodem, dla którego da się to w ogóle
powiedzieć — bez atrybucji izolowanej naprawa `#` wyglądałaby na zmianę
w siedmiu klasach.

Trzeci wiersz jest kontrolą negatywną wobec obu napraw: żadna nie miała ruszyć
początku logicznego i żadna go nie ruszyła.

## 4. Status epistemiczny — do raportowania dosłownie

K24d **nie jest testem prospektywnym** i nie należy go tak przedstawiać.
Obie naprawy zostały sprawdzone offline na korpusie K24p **zanim** dotknięto
silnika: dla `>N` — 5314/5314 i 5438/5438 węzłów, dla `#` — 5960/5960
i 5998/5998, obie kontrole wobec kolumny `oracle_c1` z surowej kampanii K24p.
Kampania K24d potwierdza więc na poziomie **silnika** to, co było już wiadome
na poziomie **postaci zamkniętej**.

Predeklaracja jest odziedziczona z K24p (te same ziarna, generator, kryteria,
progi); K24d nie zamraża nowych. Kryterium wyniku — „sześć klas dokładnych,
trzy zawyżające, zero zaniżeń, origin 9/9” — zapisano w
`paper-arXiv/debs/research_plan.md` §16.1 (wiersz 3e) **przed** uruchomieniem
kampanii, ale nie jest to predeklaracja w sensie K24: przewidywanie
wyprowadzono z kontroli offline, a nie z hipotezy postawionej w ciemno.

Wartością K24d nie jest zaskoczenie, tylko **przypięcie**. Gdyby kampania
pokazała cokolwiek innego niż przewidywanie, znaczyłoby to, że silnik nie
implementuje postaci, którą sprawdzono — i to byłby wynik.

## 5. Człon (b)

Ramię (b) uruchomiono osobno na ziarnie `20260805`, aparaturą K24b bez zmian.
Wynik **identyczny z K24p**: gęstość rozjazdu 52,9% (próg ≥ 5%), postać
`ceil((p+q−1)/p)` w **2310/2310** węzłów populacji twierdzenia (węzły `#`
o obu składowych deklarowanych), dodatniość 2310/2310, obie kontrole negatywne
zerowe (0/8568 i 0/1113). **H10b wsparta.**

Niezmienność nie jest przypadkiem i była przewidziana w K24b: człon (b)
porównuje regułę lokalną z **oracle'em**, nie z silnikiem, więc naprawa
rachunku silnika nie może go poruszyć. Gdyby liczby drgnęły, oznaczałoby to
błąd w izolacji ramienia.

## 6. Pojemność historii

Model pojemności bez zmian wobec K24p: dla `@` przewiduje niedomiar jednego
rekordu w 69,0% par ze składową deklarowaną (ziarno `20260804`) i 68,6%
(`20260807`); dla `SHIFT`, `HASH`, `ADD`, `SUB`, `THETA` i `NTHETA` —
**zero niedomiaru**.

Dwie rzeczy warte odnotowania. Po pierwsze, przewidywanie dla `@` jest znane
z K24p i tam sprawdzone kontrolą celowaną na 55 planach **wyłącznie
z przewidywanym niedomiarem** — zero objawów, źródłem rozbieżności jest człon
`DECLARATION_PREFETCH` liczony po innej stronie w modelu niż w silniku.
K24d niczego tu nie zmienia i nie powtarza tamtej kontroli. Po drugie,
**`HASH` ma zerowy niedomiar również po zmianie ogona** — to nie było
oczywiste, bo pojemność źródeł przeplotu liczy się z `q.startupLatency`,
który właśnie zmalał w 7,9% węzłów.

## 7. Bramka odwzorowania — silnik uruchomiony naprawdę

Kampania jest compile-only, więc sprawdza rachunek, a nie to, czy silnik
naprawdę wydaje te rekordy. Bramka odwzorowania uruchamia plany w czasie
rzeczywistym i porównuje treść z modelem. To najważniejsza kontrola przy tej
zmianie: obniżenie ogona `#` w 7,9% węzłów przesuwa moment emisji, a więc
mogłoby przesunąć albo zgubić rekordy.

| Ziarno | Zgodne | Poza budżetem | Rozbieżność treści | Awarie |
|---|---:|---:|---:|---:|
| `20260804` | 101 | 10 | 1 (rozstrzygnięta niżej) | 0 |
| `20260807` | 103 | 9 | **0** | 0 |

„Poza budżetem” oznacza plan, którego rozpiętość interwałów nie mieści się
w czasie przebiegu bramki — to własność planu, nie wynik.

**Jedyne zgłoszenie: plan 38, węzeł `n3` (`-`), „zero rekordów”.** Jest to
**ten sam przypadek, który zgłosiła K24p**, i ma to samo rozstrzygnięcie:
artefakt długości przebiegu, nie rozbieżność semantyczna. Reprodukcja
(`repro_plan38.py`) na trzech długościach przebiegu:

| Pętli | `n3` rekordów | Stan |
|---:|---:|---|
| 129 (budżet bramki) | 0 | „zero rekordów” |
| 258 | 16 | zgodne |
| 516 | 48 | zgodne |

Przyczyna: budżet bramki liczy rozpiętość interwałów, ale nie uwzględnia
`origin+ogon`, który dla tego węzła wynosi 15 slotów. Przy 129 pętlach węzeł
nie zdąża wyjść z milczenia. Po podwojeniu przebiegu emituje rekordy zgodne
z modelem.

Warto odnotować, że zgłoszenie dotyczy klasy `-`, której K24d **nie** dotyka,
i że pojawiło się identycznie przed naprawami. To jest argument, że bramka
mierzy tu własną długość przebiegu, a nie skutek zmiany ogona `#`.

**Zestawienie „przed/po" plan po planie** (`compare_gates.py`, wobec bramek
K24p):

| Ziarno | Planów o zmienionym statusie | Regresje |
|---|---:|---|
| `20260804` | **0** | brak |
| `20260807` | **0** | brak |

To jest mocniejsze stwierdzenie niż same sumy. Obniżenie ogona `#` w 7,9%
węzłów i ogona `>N` w 6,6% przesunęło moment emisji w setkach węzłów korpusu,
a mimo to **żaden plan nie zmienił statusu wykonania**: to, co było zgodne,
pozostało zgodne, a to, co nie mieściło się w budżecie, nadal się nie mieści.
Zmiana dotknęła opóźnienia, nie treści — czyli dokładnie tej części relacji
`Obs`, która ma prawo się zmieniać.

## 8. Wnioski dla artykułu (krok 3a)

1. **Tabela klas ma iść z K24d, nie z K24p.** Sześć klas wspartych, trzy
   otwarte, zero zaniżeń, origin 9/9 na obu ziarnach.
2. **Przy `#` trzeba podać koszt rachunku.** Ogon `#` nie jest wyrażeniem
   `O(1)`, tylko przeglądem okresu fazowego `O(p+q)`; rozstrzygnięcie
   definicyjne i jego uzasadnienie są w `research_plan.md` §5, poz. H10a.
   Bez tego zdania twierdzenie jest podatne na kontrprzykład.
3. **Człon (b) wyłącznie w zawężeniu** do węzłów `#` o obu składowych
   deklarowanych — bez tego warunku jest fałszywy.
4. **Status epistemiczny dosłownie** wg §4: potwierdzenie przy przypiętym SHA,
   nie test prospektywny.
5. **Pakiet artefaktów (krok 4) przypina `34db1a2`** i ten katalog. Cztery
   wcześniejsze katalogi K24 zostają jako zapis historyczny, ale żaden z nich
   nie opisuje wydawanego silnika.
