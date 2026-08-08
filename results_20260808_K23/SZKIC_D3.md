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

**Zastrzeżenie — w postaci zawężonej (korekta 2026-08-08).** Pierwsza wersja tego
akapitu twierdziła, że P2 wymaga kroku rachunkowego, którego P1 nie wymaga. To
było postawione za mocno. Skoro `i·Δ_A = k·Δ_B = τ`, to `i = τ·r_A`,
`k = τ·r_B`, a zatem `i + k = τ·(r_A + r_B) = τ / Δ_h`. Liczba slotów w postaci
P2 to zwykłe **„opóźnienie razy takt strumienia”** — ta sama reguła, której autor
używa przy każdym innym przesunięciu, tyle że zastosowana do strumienia
przeplecionego. Żadnej arytmetyki specjalnego przeznaczenia tu nie ma.

Prawdziwe zastrzeżenie jest więc węższe: nie chodzi o **trudność rachunku**, lecz
o to, czy autor w ogóle **myśli w slotach strumienia przeplecionego**, zamiast
w opóźnieniach poszczególnych torów. To jest różnica modeli myślowych — autor
sygnałowy (takt wyniku jest wielkością pierwotną) wobec autora czujnikowego
(pierwotne są karty katalogowe torów). Obaj istnieją w scenariuszu z §2; drugi
napisze P1, pierwszy P2.

**Rozstrzygnięcie człowieka 2026-08-08:** stałe przyjęte bez zmian
(`Δ_A = 1/100`, `Δ_B = 1/50`, `i = 2`, `k = 1`, `>3`), a przypisanie postaci P2
autorowi myślącemu sygnałowo wchodzi do predeklaracji **jawnie**, jako założenie,
a nie jako rzecz przyjęta milcząco. Dobierania „okrąglejszych” stałych zaniechano
świadomie: po powyższej korekcie nie kupuje nic (`20 ms × 150 Hz = 3` nie jest
trudniejsze niż `20 ms × 200 Hz = 4`), a wyglądałoby na strojenie rodziny pod
tezę. Wariantu „odrzucić F9-R1” nie wybrano — zostawiłby najwyżej 2/3 rodzin,
czyli próg bez zapasu.

### 3.3. F9-X — złożenie inline

**Werdykt: przechodzi warunkowo. Postać inline jest idiomem tego języka dla
podwyrażeń jednorazowego użytku; trzy ograniczenia zapisane niżej wprost.**
(Rozstrzygnięcie człowieka 2026-08-08, po pilocie i po sprawdzeniu korpusu.)

Cztery postacie W1–W4 powstają z dwóch niezależnych, arbitralnych decyzji (postać
R1 każdej pary × kolejność par w sumie), i **ta część** argumentu jest tak mocna
jak w §3.1 i §3.2: żadna z tych decyzji nie ma uzasadnienia merytorycznego.

Pytanie dotyczy **składni, której rodzina wymaga**:

```
FROM ((A>2)#(B>1)) + ((C>2)#(D>1))
```

Alternatywą jest nazwanie strumieni pośrednich — czytelniejsze, dające się
podejrzeć osobno i odpowiadające temu, jak autor myśli o maszynie (przód/tył):

```
SELECT * STREAM front FROM (A>2)#(B>1)
SELECT * STREAM rear  FROM (C>2)#(D>1)
SELECT Sqrt(…) STREAM m1 FROM front+rear
```

Nazwanie **zabija warstwę R2**: odcisk równoważności widzi strumień publiczny
jako `SOURCE{nazwa}`, a dwaj niezależni autorzy nadadzą różne nazwy. Pierwsza
wersja tego akapitu wyciągała stąd wniosek, że rodzina nie przechodzi kryterium,
bo „autor prawdopodobnie nazwałby pośrednie”. **Ta teza została postawiona bez
sprawdzenia korpusu i jest nietrafna.**

**Co mówi korpus tego projektu.** Złożenia inline nad podwyrażeniami
jednorazowego użytku są w nim normą:

| Kształt | Miejsce |
|---|---|
| `FROM s3+((s1+s2)>1)` | `test/IntegrationTest_serial/issue167_dedup_cascaded` — trzy piętra, ten sam miks operatorów |
| `FROM (core0#core1)+core2` | `examples/rmpy/query4.rql` — materiał **przykładowy**, nie test |
| `FROM (s1#s2)#s3` z polami `s1[0]+s2[0]+s3[0]` | `test/IntegrationTest_serial/issue167_triarg` — odwołania do źródeł pod złożonym `FROM` |
| `FROM (core0+core1)>5`, `FROM (A>2)#(B>1)` | kilkanaście miejsc w testach i przykładach |

Naprzeciw stoi `examples/ecg` (Pan-Tompkins), który nazywa wszystkie 13 etapów —
ale **każdy z nich ma konsumenta w następnym kroku**, część ma kilku. Podział
w tym języku jest więc czytelny: **podwyrażenie jednorazowego użytku pisze się
inline, etap wielokonsumencki dostaje nazwę.** Para złożona w F9-X jest
z punktu widzenia izolowanego autora jednorazowa — używa jej dokładnie jeden
monitor, jego własny. Postać inline nie jest zatem obejściem znanym komuś, kto
wie o mechanizmie; jest zwykłym zapisem tego przypadku.

**Co zostało zmierzone, zamiast założone** (`RAPORT_PILOTA.md` §6a,
`pilot/diag_X_named.rql`, wariant z nazwanymi pośrednimi, profil `DEFAULT`):

1. `STREAM_SELECT_* = 0` — nazwanie kasuje warstwę R2 w całości. Premisa
   potwierdzona na działającym planie, nie tylko z lektury kodu.
2. **Warstwa R1 przeżywa nazwanie** — `front1` i `przod2` zostały przepisane na
   wspólny `STREAM_HASH_A_B`. Zależność od postaci inline dotyczy więc wyłącznie
   warstwy R2 w F9-X; rodzina F9-R1 jest odporna na styl nazewniczy.
3. **Nazwanie przenosi materializację do strumieni publicznych**, czyli
   w metryce K23 z licznika do **mianownika**. Populacja mieszana nie osłabia
   efektu liniowo — zmienia to, co metryka mierzy.

**Decyzja: rodzina zostaje, z postacią inline zamrożoną dla wszystkich `Q`
monitorów.** Trzy ograniczenia, do zapisania w predeklaracji i w artykule bez
wygładzania:

* postać symetryczna, w której **oba** operandy `+` są złożone, jest o krok
  głębsza niż cokolwiek w korpusie; krok polega na symetrii, nie na nowej
  konstrukcji, ale nie jest wprost udokumentowany;
* zaświadczone złożenia inline siedzą głównie w testach pisanych przez autora
  silnika — materiałem przykładowym jest tylko `examples/rmpy`. Korpusu kodu
  użytkowników nie ma, i to ograniczenie dotyczy **całego** scenariusza z §2, nie
  samego F9-X;
* postać zapisu jest **zamrożona** dla wszystkich `Q` monitorów; populacja
  mieszana zmienia metrykę w sposób zmierzony w punkcie 3 powyżej.

Monitory generowane z szablonu albo z konfiguracji (typowe przy `Q` najemcach
obsługiwanych jednym narzędziem) zostają jako droga **wspierająca**, a nie jako
podstawa uzasadnienia — oparcie rodziny wyłącznie na nich zawężałoby twierdzenie
do niszy, w której nie musi ono siedzieć.

Wariantu „nie robić F9-X” nie wybrano: jest to jedyna rodzina badająca
**współdziałanie** przejść, pilot pokazał, że mechanizm działa, a układ 2×2
wyszedł dokładnie jak predeklarowano. Rezygnacja zamieniłaby twierdzenie
„kompilator składa przejścia” na „każde przejście działa osobno”.

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
| F9-R1 | `(A#B)>3` | tak, jeżeli autor myśli taktem strumienia wynikowego | ⚠️ §3.2, zawężone |
| F9-X | inline `((A>2)#(B>1)) + ((C>2)#(D>1))` | tak dla podwyrażenia jednorazowego użytku — idiom potwierdzony korpusem | ⚠️ §3.3, trzy ograniczenia |
| wszystkie | identyczny program pól co do tokenów | tak, przy przepisywaniu ze specyfikacji | ⚠️ §3.4 |

Trzy ⚠️, zero ❌ (pierwsza wersja tabeli miała tu ❌ przy F9-X — zdjęte po
sprawdzeniu korpusu i po pomiarze z `RAPORT_PILOTA.md` §6a). Żadne z zastrzeżeń
nie jest defektem aparatury ani mechanizmu — to są granice **twierdzenia**, które
K23 będzie mogła postawić. Zapisuję je tutaj, przed predeklaracją, dokładnie po
to, żeby nie powstały po wynikach.

## 5. Co musi trafić do predeklaracji z tego pliku

1. Scenariusz z §2 w całości, wraz z akapitem o Flinku (co reprezentuje
   `FLINK_NATURAL`, a czego `FLINK_MANUAL`).
2. Argument per rodzina z §3, wraz z **zastrzeżeniami** — nie w wersji
   wygładzonej.
3. Kryterium dyskwalifikujące i tabela z §4 jako zapis, że szkic został tym
   kryterium sprawdzony, a nie tylko nim zadeklarowany.
4. Rozstrzygnięcia człowieka:
   * **§3.2 — zamknięte 2026-08-08.** Stałe przyjęte, zastrzeżenie zawężone do
     modelu myślowego autora i zapisywane jawnie.
   * **§3.3 — zamknięte 2026-08-08.** Rodzina zostaje, postać inline zamrożona
     dla wszystkich `Q` monitorów i uzasadniona idiomem języka dla podwyrażeń
     jednorazowego użytku; trzy ograniczenia z §3.3 wchodzą do predeklaracji
     i do artykułu w postaci niewygładzonej. Monitory generowane pozostają drogą
     wspierającą, nie podstawą.

**D-3 jest tym samym zamknięte w całości.** Przed P5 zostaje wyłącznie **D-2**
(strona Flinka).
