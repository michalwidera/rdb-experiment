# Szkic D-3 — kto pisze `Q` równoważnych postaci tego samego monitora

**Status: szkic do przeglądu człowieka. To NIE jest predeklaracja.**
§10 żąda, żeby ten tekst istniał **przed wynikami**: „Odpowiedź musi być zapisana
w predeklaracji przed wynikami, nie dopisana po nich, inaczej cały układ czyta się
jako skonstruowany pod tezę”. Ten plik jest wersją roboczą tej odpowiedzi.

---

## 1. Dlaczego to pytanie decyduje o wartości K23

Cała konstrukcja K23 broni się przed jednym zarzutem: w idiomatycznym
DataStreamie pisze się **jeden** uchwyt wspólnego etapu i `Q` konsumentów z niego,
co daje jedną instancję fizyczną i obala H9 w rodzinie. `FLINK_NATURAL` nie
tworzy `Q` instancji dlatego, że Flink jest gorszy, tylko dlatego, że monitory są
**równoważne, lecz strukturalnie różne**, a DataStream nie ma normalizacji
algebraicznej.

To przenosi ciężar z internal validity na **motivational validity**. Pierwsze
pytanie recenzenta brzmi: *kto pisze to samo obliczenie w ośmiu różnych,
równoważnych postaciach?* Jeżeli odpowiedź jest naciągana, wynik nie broni H9 —
broni artefaktu.

**Kryterium dyskwalifikujące (z §10, przyjmowane tu wprost):**

> Każda użyta postać musi być tą, którą wybrałby autor piszący **wyłącznie swój**
> monitor, bez wiedzy o pozostałych `Q−1`. **Postać, której nikt nie napisałby
> w izolacji, dyskwalifikuje rodzinę.**

Kryterium jest jednostronne i nie ma progu „prawie naturalna”. W §3 sprawdzam nim
własny szkic i jedna rodzina go **nie przechodzi bez zastrzeżeń**.

---

## 2. Scenariusz — konkretny, do zamrożenia

Stanowisko: linia produkcyjna z kilkoma maszynami, wspólna magistrala telemetrii.
Strumienie źródłowe (`A`, `B`, `C`, `D`) są **infrastrukturą**: deklaruje je zespół
platformy, a każdy zespół aplikacyjny czyta je pod tymi samymi nazwami. Monitory
**nie są** infrastrukturą — pisze je ten, kto ich potrzebuje.

Trzy niezależne drogi, którymi powstaje `Q` równoważnych postaci tego samego
obliczenia. Wszystkie trzy są w tym scenariuszu jednocześnie obecne:

1. **Wielu najemców nad wspólnym źródłem.** Utrzymanie ruchu, jakość i zespół
   procesowy monitorują tę samą maszynę do innych celów (alarm, karta kontrolna,
   raport zmianowy). Każdy pisze własny strumień wyjściowy, bo każdy ma własną
   regułę, retencję i odbiorcę. Żaden nie czyta RQL pozostałych — nie ma po co,
   a często nie ma też dostępu.
2. **Monitory dziedziczone i kopiowane między wdrożeniami.** Nowa maszyna dostaje
   monitor skopiowany z poprzedniej i lokalnie poprawiony (inne nazwy kanałów,
   inny próg). Kopia zachowuje **postać składniową źródła kopiowania**, a nie
   postać kanoniczną — dlatego postacie rozchodzą się między wdrożeniami i wracają
   na jedną instalację razem z maszynami.
3. **Ta sama specyfikacja zapisana przez różne osoby.** Wymaganie brzmi
   „amplituda wektora drgań z dwóch osi” albo „zestaw oba tory po kompensacji
   20 ms”. Specyfikacja mówi **co**, nie **w jakiej kolejności wymienić wejścia** —
   ta decyzja jest po stronie autora i jest arbitralna.

Czego ten scenariusz **nie** zakłada i zakładać nie wolno: że ktokolwiek pisze
osiem wariantów celowo, że istnieje przegląd kodu wymuszający jedną postać, ani
że autorzy wiedzą o istnieniu pozostałych monitorów. Gdyby którekolwiek z tych
założeń było potrzebne, rodzina byłaby sztuczna.

**Konsekwencja dla Flinka, którą trzeba zapisać uczciwie:** w tym samym
scenariuszu autor jobu Flinka **też** nie widzi pozostałych `Q−1` monitorów, więc
`FLINK_NATURAL` z `Q` niezależnymi jobami/gałęziami jest wierną, a nie
osłabioną reprezentacją. `FLINK_MANUAL` odpowiada sytuacji, w której ktoś
**zobaczył wszystkie `Q`** i ręcznie wydzielił wspólny etap — czyli dokładnie tej
wiedzy, której scenariusz odmawia autorom. Dlatego `FLINK_MANUAL` jest kontrolą
best-case poza progiem, a nie baseline’em.

---

## 3. Argument per rodzina

### 3.1. F9-R2 — `FROM A+B` wobec `FROM B+A`

**Werdykt: przechodzi kryterium.**

Autor liczący `sqrt(x² + y²)` z dwóch osi tego samego czujnika musi wymienić oba
strumienie w `FROM`. Kolejność nie ma żadnego uzasadnienia merytorycznego: osie są
symetryczne, żadna nie jest „pierwsza”. O wyborze decydują rzeczy przypadkowe —
kolejność w dokumentacji czujnika, kolejność w schemacie szafy sterowniczej,
alfabet nazw kanałów. Autor piszący **wyłącznie swój** monitor wybierze jedną z
dwóch i nigdy się nad tym nie zastanowi.

To jest najmocniejsza z trzech rodzin pod względem D-3: obie postacie są nie tylko
możliwe, ale **równie prawdopodobne**, a rozkład 50/50 w rodzinie odpowiada
rozkładowi, jakiego oczekiwalibyśmy w rzeczywistej instalacji.

### 3.2. F9-R1 — `(A>2)#(B>1)` wobec `(A#B)>3`

**Werdykt: przechodzi warunkowo — z jednym zastrzeżeniem, które trzeba
rozstrzygnąć przed predeklaracją.**

Obie postacie odpowiadają dwóm modelom myślowym o tym samym opóźnieniu akwizycji:

* **P1 „kompensuj tor, potem zestawiaj”** — autor myśli o czujnikach: *tor drgań
  spóźnia się o 2 próbki, tor prądu o 1 próbkę; skompensuj każdy w jego własnych
  jednostkach, potem przeplataj*. Postać jest bezpośrednim zapisem tego zdania i
  napisałby ją każdy, kto patrzy na kartę katalogową czujnika.
* **P2 „zestaw, potem kompensuj wspólne opóźnienie”** — autor myśli o sygnale:
  *oba tory mają to samo opóźnienie 20 ms; przeplataj je, a potem cofnij całość
  o 20 ms*. Postać jest bezpośrednim zapisem tego zdania.

**Zastrzeżenie.** P2 wymaga, żeby autor wyraził 20 ms **w slotach strumienia
przeplecionego** (`Δ_h = 1/150`, czyli `>3`), a nie w slotach któregokolwiek ze
źródeł. To jest krok rachunkowy, którego P1 nie wymaga — tam obie liczby (`2` i
`1`) czyta się wprost z opóźnień torów. Autor, który tego rachunku nie zrobi,
napisze `>2` albo `>1` i **dostanie inny monitor**, nie inną postać tego samego.

Trzy sposoby domknięcia, do wyboru przez człowieka:

1. **Dobrać stałe tak, żeby przesunięcie łączne było liczbą oczywistą** w
   jednostkach naturalnych dla autora (np. taką, w której `i + k` odpowiada
   pełnemu okresowi wolniejszego toru).
2. **Zapisać w predeklaracji, że P2 jest postacią autora myślącego sygnałowo**,
   dla którego takt strumienia przeplecionego jest wielkością pierwotną — i przyjąć
   ten model jawnie, zamiast go zakładać.
3. **Uznać zastrzeżenie za dyskwalifikujące** i zatrzymać F9-R1 przed
   predeklaracją. Wtedy H9 może wesprzeć co najwyżej 2/3 rodzin, czyli próg
   pozostaje osiągalny, ale bez zapasu.

Rekomendacja: (1) plus (2). Wariant (3) tylko wtedy, gdy (1) nie da się spełnić
bez naciągania stałych pod tezę.

### 3.3. F9-X — złożenie inline

**Werdykt: NIE przechodzi kryterium w obecnej postaci. Wymaga decyzji człowieka
przed pilotem.**

Cztery postacie W1–W4 powstają z dwóch niezależnych, arbitralnych decyzji (postać
R1 każdej pary × kolejność par w sumie), i **ta część** argumentu jest tak mocna
jak w §3.1 i §3.2: żadna z tych decyzji nie ma uzasadnienia merytorycznego.

Problem leży gdzie indziej — w **składni, której rodzina wymaga**. Postać

```
FROM ((A>2)#(B>1)) + ((C>2)#(D>1))
```

wkłada całe złożenie w jedno wyrażenie `FROM`, z trzema piętrami nawiasów. Autor
piszący wyłącznie swój monitor prawdopodobnie **nazwałby strumienie pośrednie**:

```
SELECT * STREAM front FROM (A>2)#(B>1)
SELECT * STREAM rear  FROM (C>2)#(D>1)
SELECT Sqrt(…) STREAM m1 FROM front+rear
```

— bo to jest czytelniejsze, daje się podejrzeć osobno i odpowiada temu, jak
myśli o maszynie (przód/tył). Postać inline jest postacią kogoś, kto **wie**, że
nazwanie pośrednich zablokuje współdzielenie. To jest dokładnie sytuacja, którą
kryterium ma wykluczać.

Co gorsza, obejścia nie ma i trzeba to powiedzieć wprost: nazwane strumienie
pośrednie są **publiczne**, a odcisk równoważności widzi je jako
`SOURCE{nazwa}` — dwaj niezależni autorzy nadadzą im różne nazwy, więc R2 nie
odpali. Rodzina naturalna składniowo byłaby rodziną, w której mechanizm nie
działa; rodzina, w której mechanizm działa, jest składniowo nienaturalna.

Trzy możliwe wyjścia, **wszystkie wymagają decyzji człowieka**:

1. **Uzasadnić postać inline osobno.** Da się bronić w wąskim kontekście:
   monitor generowany z szablonu albo z konfiguracji (typowe przy `Q` najemcach
   obsługiwanych przez jedno narzędzie), gdzie wyrażenie powstaje przez podstawienie,
   a nie przez ręczne pisanie. Wtedy scenariusz z §2 trzeba **rozszerzyć o czwartą
   drogę** — monitory generowane — i zapisać, że F9-X opiera się właśnie na niej.
   Uczciwe, ale zawęża twierdzenie.
2. **Uznać F9-X za rodzinę o słabszej motivational validity** i zapisać to jako
   ograniczenie w raporcie i w artykule — przy zachowaniu pełnej internal validity
   (mechanizm i tak jest badany poprawnie).
3. **Nie robić F9-X.** §10 dopuszcza wsparcie H9 przy 2/3 rodzin, ale F9-X jest
   jedyną rodziną badającą **współdziałanie** przejść, a jej brak zmienia
   twierdzenie z „kompilator składa przejścia” na „każde przejście działa osobno”.

Rekomendacja: (1) — z jawnym rozszerzeniem scenariusza i z zapisem, że twierdzenie
F9-X dotyczy monitorów generowanych. Ale to jest decyzja o zakresie contribution,
nie decyzja techniczna, więc należy do człowieka.

### 3.4. Zastrzeżenie wspólne dla wszystkich trzech rodzin (D-3-C)

Współdzielenie wymaga, żeby programy pól wszystkich `Q` monitorów były **identyczne
co do tokenów**. `Sqrt(A[0]*A[0]+B[0]*B[0])` i `Sqrt(B[0]*B[0]+A[0]*A[0])` to dla
odcisku **dwa różne programy** — kanonizacja R2 dotyczy węzła `STREAM_ADD` w drzewie
`FROM`, a nie wyrażeń arytmetycznych w programie pola.

Ośmiu niezależnych autorów napisze tę samą formułę w tej samej kolejności składników
tylko wtedy, gdy przepisują ją ze specyfikacji. Scenariusz z §2 to zakłada (droga 3),
ale trzeba zapisać jawnie: **K23 bada przemienność operatora strumieniowego, a nie
przemienność wyrażeń arytmetycznych** — te drugie kompilator normalizuje w takim
zakresie, jakiego ta kampania nie dotyka.

Gdyby recenzent zapytał „a jeżeli jeden z ośmiu napisze składniki w innej
kolejności?”, uczciwa odpowiedź brzmi: ten monitor wypadnie z klasy równoważności
i będzie liczony jako osobna instancja. To osłabia efekt liniowo z liczbą takich
autorów i nie unieważnia mechanizmu.

---

## 4. Test własnego szkicu kryterium dyskwalifikującym — podsumowanie

| Rodzina | Postać | Czy autor w izolacji by ją napisał | Werdykt |
|---|---|---|---|
| F9-R2 | `FROM A+B` | tak, arbitralna kolejność symetrycznych osi | ✅ |
| F9-R2 | `FROM B+A` | tak, ta sama arbitralność | ✅ |
| F9-R1 | `(A>2)#(B>1)` | tak, zapis „kompensuj tor, potem zestawiaj” | ✅ |
| F9-R1 | `(A#B)>3` | tak, ale wymaga rachunku w slotach przeplotu | ⚠️ §3.2 |
| F9-X | inline `((A>2)#(B>1)) + ((C>2)#(D>1))` | **wątpliwe** — autor nazwałby pośrednie | ❌ §3.3 |
| wszystkie | identyczny program pól co do tokenów | tak, przy przepisywaniu ze specyfikacji | ⚠️ §3.4 |

Dwa ⚠️ i jedno ❌. Żadne z nich nie jest defektem aparatury ani mechanizmu — to
są granice **twierdzenia**, które K23 będzie mogła postawić. Zapisuję je tutaj,
przed pilotem i przed predeklaracją, dokładnie po to, żeby nie powstały po
wynikach.

## 5. Co musi trafić do predeklaracji z tego pliku

1. Scenariusz z §2 w całości, wraz z akapitem o Flinku (co reprezentuje
   `FLINK_NATURAL`, a czego `FLINK_MANUAL`).
2. Argument per rodzina z §3, wraz z **zastrzeżeniami** — nie w wersji
   wygładzonej.
3. Kryterium dyskwalifikujące i tabela z §4 jako zapis, że szkic został tym
   kryterium sprawdzony, a nie tylko nim zadeklarowany.
4. Rozstrzygnięcia człowieka: §3.2 (wariant 1/2/3) i §3.3 (wariant 1/2/3).
