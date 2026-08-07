# K24 / H10 — raport

**Data:** 2026-08-03
**Krok:** 3 ścieżki §16.1 `research_plan.md` (bramka daty werdyktu: 2026-10-15)
**Silnik:** `retractordb` `5e3eb42`, gałąź `issue_223-fixes` — patrz [PIN.md](PIN.md)
**Predeklaracja:** [PREDECLARATION.md](PREDECLARATION.md) · **Werdykt:** [VERDICT.md](VERDICT.md)

---

## 1. Streszczenie

Test prospektywny H10 wykonano na korpusie **10 010 planów** (35 827 obserwacji
węzłowych, zero błędów aparatury). Wynik jest **mieszany i częściowo negatywny**:

* **H10a jest sfalsyfikowana w sześciu z dziewięciu klas operatorów.** Wsparta
  pozostaje w trzech: `PASS`, `>N`, redukcje — tam postać zamknięta jest
  dokładna na całym korpusie.
* Rozbieżności nie są przypadkowe. Rozkładają się na **dwa jakościowo różne
  reżimy**: cztery klasy (`#`, `-`, `Θ`, `~Θ`) **zawyżają ogon o dokładnie jeden
  slot** na części faz — postać zamknięta jest tam bezpieczna, ale nie równa;
  dwie klasy (`@`, `+`) **zaniżają**, czyli dopuszczają emisję rekordu, zanim
  wszystkie jego zależności są określone.
* **Człon (b) jest nieocenialny na tej aparaturze.** Obie predeklarowane
  kontrole negatywne pękły, a przyczyną jest sprzeczność w samej specyfikacji
  „naturalnej reguły lokalnej” w §10/K24 — nie wynik pomiaru (§5).
* Przy okazji ujawniono **pięć defektów silnika** niezależnych od hipotezy,
  w tym dwa poważne: `-` o całkowitym ilorazie `>= 3` produkuje strumień złożony
  wyłącznie z rekordów `NULL`, a trzy plany ze 112 w podpróbie kończą wykonanie
  twardą awarią na odczycie historii poza pojemnością bufora (§6).

Wniosek dla ścieżki §16.1: zachodzi przesłanka z `harmonogram.md` §4.2 —
rozbieżność nie jest wyłącznie falsyfikacją H10, lecz dotyka relacji `Obs`.
Decyzja o dalszej kolejności należy do człowieka (§8).

## 2. Aparatura

| Element | Rola | Bramka |
|---|---|---|
| `oracle/model.py` | model zdarzeniowy: ogon wyprowadzony z chwil dostępności | `tests/test_independence.py` — brak postaci zamkniętej w kodzie: **przeszła** |
| `oracle/closedform.py` | replika `computeStartupLatency()` | `tests/test_closedform.py` — 40/40 węzłów zgodnych ze zrzutem silnika: **wierność potwierdzona** |
| `tests/hand_cases.py` | 37 przypadków o ręcznie wyprowadzonej odpowiedzi | `tests/test_oracle.py` — 80 porównań, **przeszła** |
| `oracle/mutants.py` | 5 zamrożonych mutantów | `tests/test_mutants.py` — **100% wykrytych** |
| `generator.py` | korpus, ziarno 20260803, 14 strat po 715 planów | zero planów odrzuconych przez kompilator |
| `oracle/execute.py` | bramka odwzorowania end-to-end, dwie skale | §3 |

Reguła wyprowadzenia ogona w oracle'u (PREDECLARATION.md §4.1) jest jedna dla
wszystkich operatorów: rekord `n` emitowany jest w chwili `(n+1+W)·Δ`, a `W`
jest najmniejszą liczbą, przy której każdy rekord wypada nie wcześniej niż
dostępność jego zależności. Odwzorowanie rekordów pochodzi z definicji
operatorów w artykule; nic w oracle'u nie pochodzi z rachunku ogona silnika.

### 2.1. Wyprowadzenia ręczne — dwa przykłady

**Przeplot `1/3 # 1/2`.** `Δ_c = 1/5`, `z = Δ_b/(Δ_a+Δ_b) = 3/5`.
Slot 0: `⌊0⌋ = ⌊3/5⌋`, więc `c_0 = b_0`, dostępny w `1/2`; deficyt
`(1/2)/(1/5) − 1 = 3/2`, czyli 2 sloty. Slot 2: `⌊6/5⌋ = ⌊9/5⌋`, więc
`c_2 = b_1`, dostępny w `1`; deficyt `5 − 3 = 2`. Sloty 1, 3, 4 dają deficyt
ujemny. Maksimum = **2** — zgodne z postacią zamkniętą i z silnikiem.

**Różnica o ilorazie całkowitym `r`.** Rekord `n` czyta indeks `r·n`, dostępny
w `(rn+1)·Δ_src`, a slot `n` kończy się w `(n+1)·r·Δ_src`. Deficyt wynosi
`1/r − 1 < 0` dla każdego `r >= 1`, więc ogon jest **zerowy**. Postać zamknięta
daje tu 1 (człon `sourceDeclared` w `SubtractStartupLatency`) — to jest źródło
80,8% zawyżeń w klasie `-`.

## 3. Bramka odwzorowania (end-to-end)

Bramka odpowiada na pytanie, bez którego rozbieżność ogona jest
nieinterpretowalna: czy silnik emituje te rekordy, o których mówi definicja
operatora? Plan jest wykonywany, a treść rekordów porównywana z modelem treści.
Każdy plan biegnie w **dwóch skalach**; różnica między skalami dyskwalifikuje
przebieg jako aparaturę (§7.2 — bez tej ochrony pierwsza wersja bramki dała
fałszywe „defekty”, które okazały się artefaktem zbyt szybkiego zegara).

Podpróba: **112 planów** (8 na stratę), wyniki w
[`raw/mapping_gate.csv`](raw/mapping_gate.csv).

| Wynik | Planów |
|---|---:|
| zgodne — treść silnika == treść oracle'a | **75** |
| rozbieżność treści | 21 |
| poza budżetem czasu (rozpiętość interwałów) | 13 |
| twarda awaria silnika | **3** |

Rozbieżności treści rozkładają się na cztery przyczyny:

| Klasa | Charakter rozbieżności | Skutek dla wyniku ogona |
|---|---|---|
| `+` (7) | silnik paruje `b_{⌊(n+1)Δ_a/Δ_b⌋}`, definicja z artykułu mówi `b_{⌊nΔ_a/Δ_b⌋}` | rozbieżność ogona w klasie `+` zachodzi **przy obu odwzorowaniach** (§4.3), więc nie jest artefaktem definicji |
| `-` (9) | rekordy wyłącznie `NULL` przy ilorazie `>= 3` | defekt silnika, §6.1, reproducer [`evidence/sub_ratio3_all_null.rql`](evidence/sub_ratio3_all_null.rql) |
| redukcje (4) | `avg` zwraca wartość obciętą w polu typu `RATIONAL` | bez wpływu na ogon (redukcje są dokładne w 100%) |
| `@` (1) | pole okna wypada `NULL` w rekordzie, który wg postaci zamkniętej jest już określony | **potwierdzenie reżimu zaniżającego** — §4.3, reproducer [`evidence/agse_null_field_63.rql`](evidence/agse_null_field_63.rql) |

Ostatni wiersz jest istotny: plan 63 emituje rekord `@`, w którym jedno pole
okna jest `NULL`, choć ogon wyliczony przez silnik deklaruje ten rekord jako
w pełni określony. Oracle wymaga tam ogona o 1 slot dłuższego. Jest to
**bezpośrednie, obserwowalne potwierdzenie zaniżenia**, niezależne od
zastrzeżenia §7.5 o replayu z pliku: brakującego rekordu nie ma w historii,
więc żaden prefetch go nie zastąpi. Wynik jest stabilny w obu skalach.

## 4. Wynik główny — H10a

### 4.1. Atrybucja

Werdykt liczony jest w **atrybucji izolowanej**: ogon węzła wyliczany postacią
zamkniętą z ogonów składowych wziętych z oracle'a. Bez tego niezgodność dziecka
liczyłaby się jako niezgodność rodzica i „per klasa operatora” nie znaczyłoby
nic. Różnica jest duża — dla `+` zgodność propagowana wynosi 8,8%, a izolowana
42,3%; reszta była dziedziczona.

### 4.2. Trzy reżimy

| Reżim | Klasy | Zgodność izolowana C1 |
|---|---|---|
| **dokładna** | `PASS`, `>N`, redukcje | 100,0% / 100,0% / 100,0% |
| **zawyżająca o 1 slot** | `#`, `-`, `Θ`, `~Θ` | 90,9% / 19,2% / 59,9% / 98,7% |
| **ZANIŻAJĄCA** | `@`, `+` | 31,8% / 42,3% |

W klasach zawyżających **każda** rozbieżność wynosi dokładnie `+1`. To nie jest
rozrzut, tylko systematyczne przesunięcie o jeden slot, występujące dokładnie
tam, gdzie faza wypada na granicy taktu. Innymi słowy: silnik stosuje ostrą
konwencję odczytu w tym samym takcie dla `-`, `Θ` i części faz `#`, a nieostrą
dla `>N`, `PASS`, redukcji i pozostałych faz `#`. **Obie konwencje nie mogą być
jednocześnie poprawne przy jednej dyscyplinie szeregowania.**

### 4.3. Reżim zaniżający

`@` zaniża w 12,3% węzłów (o 1, 2, wyjątkowo 6 slotów), `+` w 57,7% (o 1 do 99
slotów). Dla `+` sprawdzono odporność wyniku na wybór odwzorowania:

| Odwzorowanie `+` | Zgodnych | Zaniżonych | Największe zaniżenie |
|---|---:|---:|---:|
| z artykułu (`spec`, kampania) | 42,3% | 57,7% | −99 |
| zaobserwowane w silniku (`engine`, diagnostyka) | 24,3% | 75,7% | −100 |

Zaniżenie nie znika przy żadnym z odwzorowań, więc nie jest artefaktem sporu
o definicję `Σ`. Przyczyna jest prosta: postać zamknięta dla `+` to
`max(conv(W_A), conv(W_B))` bez żadnego członu fazowego, podczas gdy oba
odwzorowania wymagają, by rekord wolniejszej składowej był domknięty.

## 5. Człon (b) — dlaczego jest nieocenialny

Predeklaracja wymaga dwóch rzeczy naraz (za §10/K24 planu badawczego):

1. reguła lokalna to „suma ogonów operatorów przeliczona przez takt, **bez
   składnika fazowego**”, a rozjazd ma mieć postać `ceil((p+q−1)/p)`;
2. kontrole negatywne `HC_SINGLE` i `HC_INT` mają dać **zero rozjazdów**.

Te dwa wymagania są **wzajemnie sprzeczne**:

* przy regule „bez składnika fazowego” (wariant A) rozjazd faktycznie równa się
  `ceil((p+q−1)/p)` — ale wtedy dla ilorazu całkowitego `q | p` też jest
  niezerowy, więc kontrola `HC_INT` nie może wypaść zerowa (zmierzone: 2893
  rozjazdy na 6848 węzłach);
* przy regule z członem pierwszej fazy `ceil(q/p)` (wariant B, postać sprzed K2)
  kontrola `HC_INT` zbliża się do zera, ale rozjazd wynosi wtedy
  `ceil((p+q−1)/p) − ceil(q/p)`, a nie predeklarowaną wartość.

Zgodnie z PREDECLARATION.md §6 rozjazd w kontroli negatywnej oznacza **źle
zdefiniowaną regułę lokalną, a nie wynik**. Dlatego liczby członu (b)
(52,8% planów z rozjazdem, 284/293 rozjazdów o predeklarowanej postaci)
są raportowane, ale **nie stanowią werdyktu**. Kontrola `HC_SINGLE` przechodzi
(0 na 3897), gdy ograniczyć ją do operatorów rzeczywiście pozbawionych własnego
ogona — dosłownie zapisana pęka dlatego, że dopuszcza `@` i `-`, które własny
ogon mają.

Naprawa wymaga decyzji autorskiej o tym, czym jest „naturalna reguła lokalna”,
i powtórzenia wyłącznie ramienia (b). Ramię (a) jest tą decyzją nietknięte.

## 6. Znaleziska poboczne w silniku

Pięć obserwacji niezależnych od H10, każda odtwarzalna.

### 6.1. `-` o całkowitym ilorazie `>= 3` daje strumień samych `NULL`

```rql
DECLARE s0_f0 INTEGER STREAM s0, 1/100 FILE 's0.txt'
SELECT * STREAM n0 FROM s0-3/100
```

Liczba rekordów jest poprawna, wartości wszystkie `NULL`. Iloraz 1 i 2 działają
poprawnie; 3, 4, 5 nie. Wynik identyczny dla `SUBSTRAT 'default'` i `'memory'`
oraz dla zegara 10 ms i 50 ms, więc nie jest to artefakt tempa ani substratu.
Hipoteza przyczyny: `computeRequiredCapacities` dla `STREAM_SUBTRACT` liczy
pojemność jako `floor(W·ratio) + 2`, podczas gdy odczyt `fetchForward(src, r·n)`
zostaje w tyle za czołem źródła o `r·(1+W)` rekordów. Odczyt poza zakresem
historii materializuje się jako rekord all-`NULL`.

Jest to jednocześnie **kontrprzykład dla Definicji obserwowalności** w artykule
(„An out-of-range history read is an internal all-null guard, but a valid plan
never materializes it”). Obecny zestaw testów tego nie łapie: `k19_boundaries`
sprawdza wyłącznie ilorazy 1 i 2.

### 6.2. Przepełnienie `boost::rational<int>` na głębokich łańcuchach `&`

Plan z pięcioma zagnieżdżonymi `&` o interwałach rzędu `10^4/10^4` przepełnia
`int` w `(D_a·D_b)/|D_a−D_b|` i kończy się komunikatem „You cannot make faster
div from slower source”, który nie ma związku z rzeczywistą przyczyną.
Reproducer: [`evidence/overflow_rational_int.rql`](evidence/overflow_rational_int.rql) (plan 5031 korpusu sprzed zawężenia).
Korpus finalny ogranicza licznik i mianownik do 40 000, żeby mierzyć rachunek
ogona, a nie zakres typu.

### 6.3. `avg` obcina wynik w polu `RATIONAL`

Reduktor `avg` deklaruje pole typu `RATIONAL`, ale zwraca parę
`(⌊średnia⌋, 1)` zamiast dokładnego ułamka: dla pól `1000000, 1000001, 1000002`
wynik to `3000003/1` dla `sumc` (poprawnie) i `1000001/1` dla `avg`, choć
średnia wynosi `1000001`. Dla dwóch pól o sumie nieparzystej różnica jest widoczna:
oczekiwane `2000003/2`, otrzymane `1000001/1`.

### 6.4. Twarda awaria: `>N` pod `#` i kompozycje głębokie

Trzy plany podpróby (2 ze straty `HC_SHIFT_UNDER_HASH`, 1 z `HC_DEEP`) kończą
wykonanie sygnałem, nie wynikiem:

```
FATAL: storage::revRead: recordIndexFromBack 7 >= circularBuffer_.capacity() 6 in 's0.txt'
```

Kompilator przyjmuje plan, po czym runtime przerywa działanie na odczycie
historii poza pojemnością bufora. To ten sam mechanizm co §6.1
(`computeRequiredCapacities` liczy za małą pojemność), ale objawia się
zatrzymaniem procesu zamiast cichym `NULL`-em. Plany 80, 97, 108 korpusu (ziarno 20260803); reproducery:
[`evidence/crash_revread_80.rql`](evidence/crash_revread_80.rql),
`crash_revread_97.rql`, `crash_revread_108.rql`.

### 6.5. Niezgodność implementacji `Σ` z jej definicją

Silnik paruje `c_n = (a_n, b_{⌊(n+1)Δ_a/Δ_b⌋})`, artykuł definiuje
`c_n = (a_n, b_{⌊nΔ_a/Δ_b⌋})` (Definicja sumy strumieni). Różnica jest widoczna
w treści rekordów przy niecałkowitym ilorazie taktów i została potwierdzona
end-to-end na sześciu planach podpróby.

## 7. Zagrożenia dla trafności

**7.1. Oracle jest modelem, nie wyrocznią.** Wynik mówi, że postać zamknięta
różni się od modelu zdarzeniowego zbudowanego z definicji operatorów. Jeżeli
definicje w artykule nie oddają zamierzonej semantyki, część rozbieżności
przenosi się na definicje. Bramka odwzorowania ogranicza to ryzyko do warstwy
czasowej: treść rekordów zgadza się wszędzie poza trzema klasami z §3.

**7.2. Zegar bramki odwzorowania.** Pierwsza wersja bramki, uruchamiana przy
interwale ~5 ms, produkowała rekordy `NULL` nieodróżnialne od defektu; przy
80 ms te same plany były czyste. Stąd wymóg dwóch skal (PREDECLARATION.md §9).
Cztery plany podpróby odpadły jako „poza budżetem” — ich rozpiętość interwałów
wymaga przebiegu dłuższego niż budżet 8 s.

**7.3. Konwencja dostępności.** Werdykt liczony jest w konwencji nieostrej C1.
W konwencji ostrej C2 obraz się odwraca dla części klas (np. `Θ`: 59,9% → 87,5%),
co jest dodatkowym argumentem, że silnik nie stosuje jednej konwencji.
Żadna pojedyncza konwencja nie daje 100% w komplecie klas.

**7.4. Kolejność prac.** Kalibracja aparatury poprzedziła predeklarację
i ujawniła kandydatów na rozbieżności w `+`, `-`, `@` i `Θ` (PREDECLARATION.md §8).
Kryteria H10a/H10b pochodzą jednak z `research_plan.md` z 2026-08-01, sprzed
pierwszej linii kodu tego badania.

**7.5. Replay pliku, nie źródło żywe.** Silnik czyta źródła z plików
i prefetchuje rekordy, więc „emisja przed ogonem” nie objawia się w replayu jako
`NULL`, lecz jako wartość, której model zdarzeniowy w tym slocie jeszcze nie ma.
Twierdzenie z §4.3 dotyczy zatem rachunku ogona wobec semantyki, a nie awarii
obserwowalnej w replayu.

## 8. Co z tego wynika dla ścieżki §16.1

Fakty do decyzji człowieka — **nie podejmuję jej w tym raporcie**:

1. **H10a nie nadaje się do artykułu w obecnym brzmieniu.** Twierdzenie
   o równości nie przechodzi w sześciu klasach. Przechodzi natomiast
   twierdzenie słabsze i nadal nietrywialne: *postać zamknięta jest dokładna
   dla `PASS`, `>N` i redukcji, a dla `#`, `-`, `Θ`, `~Θ` jest bezpiecznym
   oszacowaniem z góry z błędem najwyżej jednego slotu*. To jest wynik
   pozytywny, tylko węższy — i wymaga naprawy dwóch klas zaniżających.
2. **Zachodzi przesłanka z `harmonogram.md` §4.2.** Zaniżenie w `@` i `+`
   dotyka relacji `Obs`, na której opiera się H1, a przez H1 interpretacja
   K5, K6c i K19. Priorytetem staje się zasięg tego defektu, nie K23.
3. **Defekty §6.1 i §6.4 są niezależne od artykułu i wymagają zgłoszenia jako
   issue** — pierwszy daje ciche `NULL`-e, drugi zatrzymuje proces.
4. **Człon (b) wymaga decyzji definicyjnej** (§5), po której powtarza się
   wyłącznie ramię (b) — koszt rzędu godzin, nie dni.

Zgodnie z regułą §16.1 („każdy transfer wyniku do artykułu domykać
synchronizacją wersji polskiej w tej samej sesji”) **nie naniesiono niczego na
`main-debs.tex` ani `main-debs-pl.tex`** — transfer wymaga najpierw decyzji
z punktów 1 i 2.

## 9. Dopisek 2026-08-03 — naprawy silnika po tym raporcie

Raport powyżej opisuje stan `5e3eb42` i **nie jest zmieniany**. Ta sekcja
odnotowuje wyłącznie, co się z jego znaleziskami stało; pełny zapis jest
w `paper-arXiv/debs/plan-naprawy-defektow.md` i w `research_plan.md` §K24
(„KOREKTA H10a”).

| Znalezisko z tego raportu | Stan |
|---|---|
| §6.1 ciche `NULL` w `-` (D1) | zamknięte |
| §6.2 twarda awaria `revRead` (D2) | zamknięte |
| §6.3 odwzorowanie `Σ` (D3) | zamknięte — wariant A, kod dostosowany do definicji |
| §6.4 `avg` w polu `RATIONAL` (D4) | zamknięte |
| §6.5 przepełnienie `rational<int>` (D5) | zamknięte |
| §4.3 zaniżony ogon `@` i `+` | zamknięte — nowe postacie zamknięte, 100% zgodności z oracle'em w C1 |

Skutek dla punktu 1 powyżej: **`@` i `+` przestały być klasami zaniżającymi
i przeszły na „dokładna”**. Twierdzenie węższe z punktu 1 obejmuje teraz
`PASS`, `>N`, redukcje, `@` i `+` jako dokładne, a `#`, `-`, `Θ` i `~Θ` jako
oszacowanie z góry. Bramka odwzorowania na naprawionym silniku: **99 zgodnych,
zero rozbieżności**, 13 planów poza budżetem aparatury.

Materiał: `VERDICT_after_tails.md` (obok nietkniętego `VERDICT.md`),
`raw/campaign_after_tails.csv`, `raw/mapping_gate_after_tails.csv`.
Ostrzeżenie metodologiczne: nowe postacie wyprowadzono **znając oracle'a**
i sprawdzono na tym samym korpusie — potwierdzenie poza próbą należy do K24r
(dwa przebiegi, w tym nowe ziarno).
