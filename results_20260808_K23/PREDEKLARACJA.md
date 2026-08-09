# PREDEKLARACJA K23 / H9 — zamrożenie przed pomiarem kosztowym

**Data zamrożenia: 2026-08-08. Faza P5, punkt zatrzymania STOP-5.**

Ten dokument jest bramką. Do chwili jego zamknięcia commitem **żaden pomiar
kosztowy nie był dozwolony**; od tej chwili żadna pozycja poniżej nie może się
zmienić bez **nowej predeklaracji i nowego katalogu wyników**, a danych między
iteracjami nie wolno łączyć (§10).

Źródło normatywne: `paper-arXiv/debs/research_plan.md` §10/K23. Przy rozbieżności
z tym dokumentem wygrywa §10. Treść §10/K23 jest przypięta sumą kontrolną
(§1.3) — nie jego HEAD, bo `paper-arXiv` legalnie rusza się co sesję.

Co ten dokument zastępuje: `SZKIC_RODZIN.md` i `SZKIC_D3.md` przestają być
szkicami do przeglądu — ich treść wchodzi tutaj jako zamrożona (rodziny w §3,
uzasadnienie scenariusza w §5). Oba pliki zostają **nietknięte** jako zapis tego,
co było wiadomo przed rozstrzygnięciami; obowiązuje ta wersja.

---

## 0. Trzy rzeczy rozstrzygnięte świadomie w tej sesji

Zapisane osobno, bo są to decyzje, które łatwo odziedziczyć milcząco.

### 0.1. Defekt `pilot/mechanism_table.py` — naprawiony w nowym pliku, artefakt pilota nietknięty

Skrypt pilota rozpoznaje substraty po **konwencji nazw**
(`re.fullmatch(r"(m|q|n|d|x|i|h|mm|collide_user)\d*", …)`), więc publiczny
strumień, którego autor nazwał zgodnie z konwencją kompilatora — dokładnie
kontrola „granica obserwowalności" z `F9_R1_controls.rql` — wpada u niego do
substratów. Defekt dotyczy wyłącznie planów kontrolnych; żadnej liczby
z `RAPORT_PILOTA.md` §2 nie zmienia.

**Rozstrzygnięcie:** `pilot/mechanism_table.py` **zostaje bez zmian**. Jest
zamkniętym zapisem, na którym stoi przejrzany raport pilota; podmiana artefaktu
pod zamkniętym raportem zamazałaby, co wtedy policzono. Do aparatury werdyktu
wchodzi **nowy plik** `mechanism_table.py` w katalogu kampanii, klasyfikujący nie
po nazwie, lecz po **źródle nazwy**: substratem jest strumień obecny w planie,
którego nazwy nie ma w `.rql`. To odwzorowuje granicę, którą naprawdę rozróżnia
silnik (`qry.isSubstrat` → `storage::markAsSubstrate()`).

Poprawka jest **dowiedziona bramką** (`./mechanism_table.py --gate`), a nie
zadeklarowana. Bramka wymaga dwóch rzeczy naraz:

* **(a)** na sześciu planach pilota nowa klasyfikacja daje liczby **identyczne**
  ze starą — 12 komórek planów głównych bez jednej zmiany, więc `RAPORT_PILOTA.md`
  §2 pozostaje w mocy;
* **(b)** na planach kontrolnych nowa klasyfikacja **różni się** od starej
  i różni się **dokładnie** o publiczny `STREAM_HASH_CA_CB`. Gdyby nie różniła
  się niczym, „poprawka" nie byłaby dowiedziona — i to jest ten warunek, którego
  brak przepuścił defekt.

Dodatkowo **(c)**: publiczny strumień o nazwie konwencji kompilatora musi trafić
do **mianownika** metryki, a nie zniknąć z rachunku.

### 0.2. Rate wobec kalibracji — predeklaracja zamraża protokół, wartość wchodzi aneksem

§10 wymienia rate wśród pozycji zamrażanych w predeklaracji, ale umieszcza
kalibrację **po** predeklaracji i jednocześnie mówi, że nowy rate wymaga nowej
predeklaracji. Trzeciej możliwości nie ma: albo kalibracja biegnie przed
zamrożeniem, albo wartość dochodzi później.

**Rozstrzygnięcie: kalibracji przed zamrożeniem NIE uruchamiamy.** Kolejność
z §10 i §5 („pilot → predeklaracja → bramki → kalibracja → macierz") jest
narzucona wprost i jej złamanie byłoby cięższe niż aneks. Predeklaracja zamraża
**protokół** kalibracji (§8), a **wartość** rate wchodzi jako **ANEKS-1**,
podpisany przed macierzą (P7 → STOP-7).

Jak to się godzi z klauzulą „nowy rate wymaga nowej predeklaracji": klauzula
dotyczy **zmiany rate'u po starcie macierzy** — to jest przypadek STOP-8
(przekroczenie 80% slotu albo zgubiony rekord), gdzie §10 mówi wprost o nowej
predeklaracji, nowym katalogu i zakazie łączenia danych. Pierwsze ustalenie
wartości nie jest zmianą.

Aneks jest bramkowany maszynowo: `freeze_check.sh macierz` nie przechodzi bez
`ANEKS-1_rate.tsv`, a ten musi zawierać pole `calibration_saw_effect=no`.

### 0.3. Wielkość rozdzielająca pracy — osobno dla każdej rodziny

W F9-R1 program pola **nie rozdziela**: każdy z `Q` monitorów liczy swój kwadrat
w każdym profilu i wariancie, więc ta wielkość daje **0,0%**. Współdzielenie
dotyczy tam przeplotu. Czytanie zdania §10 „wykonań kosztownego programu na slot"
literalnie jako programu **pola** pokazałoby F9-R1 jako rodzinę bez efektu.

| Rodzina | Wielkość rozdzielająca | Licznik | Wielkości wspierające |
|---|---|---|---|
| F9-R2 | wykonania programu 8-tokenowego | `evalCalls` programu `STREAM_SELECT_*` | `addMerges` |
| F9-R1 | **wybory przeplotu** | `hashPicks` | — (program pola z założenia 0,0%) |
| F9-X | wykonania programu 8-tokenowego | `evalCalls` programu `STREAM_SELECT_*` | `hashPicks`, `addMerges` |

Skrypt werdyktu czyta nazwę kolumny z tej tabeli (`RESOLVING_WORK`), zamiast mieć
jedną regułę na trzy różne mechanizmy. Praca jest **raportowana, nie progowa**:
§10 stawia próg wyłącznie na metryce pierwotnej, a dokładanie tu drugiego progu
byłoby progiem spoza §10.

---

## 1. Przypięcia i proweniencja

### 1.1. Repozytoria

| Pozycja | Wartość |
|---|---|
| Silnik `retractordb` | `1cfccf97e954025d5fb055f1cfd4f1fa9aff05e8` (`master`), drzewo czyste |
| Gałąź kampanii `rdb-experiment` | `experiment/20260808_K23` |
| Katalog kampanii | `results_20260808_K23/` |

SHA silnika obejmuje instrument logicznych zapisów (`probe::logicalWriteCounters`,
`probe::canonicalRecordBytes`, rola strumienia przez `storage::markAsSubstrate()`)
oraz bramkę **36 przypadków o znanej odpowiedzi** (14 na liczniku, 22 prowadzone
przez prawdziwą ścieżkę `storage::write()`).

Commit zamrożenia w `rdb-experiment` jest **przodkiem** każdego commitu kampanii;
treść jest przypięta manifestem `manifest.sha256`, a nie samym SHA commitu.

### 1.2. Środowisko hosta (Flink — D-2)

| Pozycja | Wartość |
|---|---|
| host | `B850MDESK`, Ubuntu 26.04 LTS, kernel `6.18.33.2-microsoft-standard-WSL2`, AMD Ryzen 9 9900X, 24 CPU |
| JDK **przypięty ścieżką** | `/usr/lib/jvm/java-17-openjdk-amd64`, `openjdk 17.0.19` |
| SHA-256 `java` / `javac` | `a89ad12dc799a14a…` / `9a4eedebe503abd0…` |
| Flink | `/home/michal/opt/flink-2.3.0`, `flink-dist-2.3.0.jar` SHA-256 `7c51cba8e3f2b35d…` |

**Domyślne `java` z `PATH` na tym hoście to 25.0.3.** Cała aparatura przypina JDK
ścieżką, nigdy przez `PATH`; bramka sprawdza **ścieżkę i sumę**, nie `java -version`.

### 1.3. Źródło normatywne

Treść §10/K23 z `research_plan.md` przypięta sumą
`d99518e12c0bc2b315c4227cc7922a6b0f4412feb27c8c46ce78f539de56b39f`
(278 wierszy, od `#### K23.` do wiersza przed `#### K24.`).

Zamrażamy treść sekcji, **nie HEAD `paper-arXiv`**: §9.1 planu realizacji jest
aktualizowane na końcu każdej sesji, więc bramka na HEAD byłaby bramką, którą
trzeba wyłączać, żeby pracować — a taka bramka nie jest bramką.

### 1.4. Binaria profili — host

| Profil | SHA-256 | `--build-info` |
|---|---|---|
| `DEFAULT` | `9e1cec8ac707ff33…` | dedup ON, share ON, commutative ON, factor ON, PROBE ON |
| `NO_R2_CANON` | `8d6d795e998410ec…` | commutative **OFF**, reszta ON |
| `NO_R1_FACTOR` | `46d5b367c047830e…` | factor **OFF**, reszta ON |
| `NO_R1_NO_R2` | `6159f5d3b070595c…` | commutative **OFF**, factor **OFF** |

Binaria **workera** są innej architektury, więc mają własne sumy. Predeklaracja
zamraża **przepis budowy** (SHA silnika + `build_profiles.sh` + oczekiwany
`--build-info`); sumy binariów workera wchodzą jako **ANEKS-2** w pierwszej
sesji, która budzi workera (P6), i od tego momentu są niezmienne.

---

## 2. Definicja metryki i granica badanego podplanu

**Metryka pierwotna:** logiczne bajty zapisów do badanego pośredniego podplanu na
**jeden publiczny rekord wyjściowy**. Jednostką jest rzeczywisty zapis jednego
rekordu pośredniego podczas wykonania planu — nie zaalokowana pojemność, nie
liczba węzłów, nie natywny rozmiar backendu.

Szerokość kanoniczna: `probe::canonicalRecordBytes` — całkowite i podwójna
precyzja 8 B, pojedyncza 4 B, bajt 1 B, `RATIONAL`/`INTPAIR` 16 B, napis =
szerokość zadeklarowana, pola konfiguracyjne i `NULLTYPE` 0 B, plus mapa
`NULL`/luk `ceil(wartości/8)`. Zależy **wyłącznie od deskryptora**.

**Deskryptor wszystkich trzech rodzin: jedno pole `INTEGER` → 9 B** (8 B wartości
+ 1 B mapy). Ta sama liczba po obu stronach porównania.

**Granica podplanu — RetractorDB:** badany podplan = wszystkie strumienie planu
z `isSubstrat == true`. Operacyjnie jest to granica, którą rozróżnia instrument:
`storage::markAsSubstrate()` z `qry.isSubstrat`, a `probe::onLogicalWrite`
rozdziela `substrateBytes` od `publicBytes`.

**Granica podplanu — Flink:** odwzorowanie planu RQL **węzeł w węzeł**. Każdy
węzeł substratu → jeden operator, którego rekordy idą do licznika
(`Canon.onSubstrateWrite`); szczytowy węzeł `FROM` monitora **razem z programem
pól** → jeden operator końcowy, którego wynik jest rekordem publicznym
(mianownik). Granica sprawdzalna maszynowo konwencją nazw
`SUB:` / `PUB:` / `SINK:` / `SRC:`; `PlanDump` odrzuca operator poza konwencją.

**Ta granulacja jest konserwatywna, czyli działa przeciw H9, i jest wybrana
świadomie.** Idiomatyczny DataStream rozbiłby operator monitora na osobne kroki;
dla F9-R2 dałoby to `FLINK_NATURAL` 8 × 17 B na slot wobec 9 B w `DEFAULT`, czyli
**93,4%** zamiast 87,5%. Wybrano wariant dający liczbę **niższą o 5,9 pp**.

**Wyłączone z licznika** (§10): ingress źródeł, bufory transportowe, checkpointy,
publiczne wyniki i ich metadane. Publiczne wyniki wchodzą wyłącznie do
**mianownika**, który musi być niezerowy.

**Metryki drugorzędne** (raportowane, nie progowe): `compute_p99_ns`,
`compute_sum_ns`, czas kompilacji, peak RSS, CPU ticks, `mat_mem_bytes`, trwałe
`mat_bytes`, natywny stan Flinka, rozmiar publicznych artefaktów. Nie wolno
tworzyć jednego indeksu z bajtów i czasu ani porównywać bezpośrednio czasu
RetractorDB z czasem JVM.

---

## 3. Trzy rodziny

Postacie i stałe zamrożone. Plany generuje `gen_corpus.py` — 18 planów rodzin
(3 × siatka `Q`) i 3 plany kontrolne; ręczna edycja jest wykrywana przez
`gen_corpus.py --check`.

### 3.1. Reguła alokacji monitorów na postacie

> `F(Q) = min(F_max, floor(Q/2))`, minimum 1; monitory rozdzielone równo między
> pierwsze `F(Q)` postaci w zamrożonej kolejności.

`F_max` = 2 (F9-R2, F9-R1), 4 (F9-X). Ta sama reguła po obu stronach:
`K23Ops.formOf` w jobach Flinka i `formOf` w `gen_corpus.py`.

Powód, dla którego liczba postaci nigdy nie przekracza `Q/2`:
`shareEquivalentSelectComputations()` tworzy substrat tylko dla grupy o
`queryIds.size() >= 2`. Postać z jednym monitorem nie dostaje substratu wcale, więc
ablacja materializowałaby **zero**, a `DEFAULT` jedną instancję — metryka
**odwróciłaby się** przy w pełni działającym mechanizmie.

### 3.2. F9-R2 — przemienny multi-sensor feature

Dwuosiowy czujnik drgań: `A` = oś X, `B` = oś Y, oba `1/100`. Monitor liczy
`Sqrt(A[0]*A[0]+B[0]*B[0])`. Dwie postacie: `FROM A+B` i `FROM B+A`.

Badany podplan: jeden węzeł `STREAM_SELECT_*` o programie `{PUSH A, PUSH B,
STREAM_ADD}`, schemat `[INTEGER]` → 9 B, interwał `1/100`.

Mechanizm: ograniczona kanonizacja pojedynczego `STREAM_ADD` +
`shareEquivalentSelectComputations()`. Bez reasocjacji, bez zmiany kolejności pól.

**Kontrola pusta: `NO_R1_FACTOR` musi dać liczby identyczne z `DEFAULT`** — R1 nie
ma tu czego dopasować. Różnica jest dowodem, że plan nie izoluje mechanizmu, czyli
przypadkiem **STOP-6**, a nie słabszym wynikiem.

### 3.3. F9-R1 — rational-rate delayed fusion

`A` = drgania `1/100`, `B` = prąd `1/50`, oba tory opóźnione o 20 ms.
Stałe: `Δ_A = 1/100`, `Δ_B = 1/50`, `i = 2`, `k = 1`; `i·Δ_A = k·Δ_B = 1/50`,
przesunięcie łączne `i + k = 3` slotu strumienia przeplecionego (`Δ_h = 1/150`).

Postacie: `FROM (A>2)#(B>1)` („skompensuj tor, potem przeplataj") oraz
`FROM (A#B)>3` („przeplataj, potem skompensuj wspólne 20 ms"). Program pola
odwołuje się do własnego strumienia (`m[0]*m[0]`) — zamierzone: współdzielenie
realizuje R1 + dedup substratów, więc przejście R2 jest w tej rodzinie bezczynne.

**Wymóg: `A` i `B` mają identyczny deskryptor.** Bez tego `schemasMatch` w R1 może
nie przejść, a rachunek szerokości przestaje być domknięty. Węzeł przeplotu
dziedziczy szerokość substratu przesunięcia (kopia lewego przesunięcia
z podmienionym programem), więc kanoniczna szerokość rekordu przeplotu jest
szerokością źródła, a nie jego sumą.

**Kontrola pusta: `NO_R2_CANON` musi dać liczby identyczne z `DEFAULT`.**

### 3.4. F9-X — złożenie R1 → R2

Dwie pary czujników: `(A, B)` łożysko przednie, `(C, D)` tylne; w każdej parze
układ taktów i opóźnień jak w F9-R1. Monitor:
`Sqrt(A[0]*C[0]+B[0]*D[0])`.

Cztery postacie = dwie niezależne, arbitralne decyzje autora (postać R1 każdej
pary × kolejność par w sumie), w **zamrożonej kolejności W1, W4, W2, W3**:

```
W1  FROM ((A>2)#(B>1)) + ((C>2)#(D>1))
W4  FROM ((C#D)>3) + ((A#B)>3)
W2  FROM ((C>2)#(D>1)) + ((A>2)#(B>1))
W3  FROM ((A#B)>3) + ((C#D)>3)
```

Kolejność jest zamrożona tak, żeby przy `Q=4` (dwie czynne postacie) rodzina
dotykała **obu** mechanizmów naraz.

**Postać `FROM` jest zamrożona jako inline dla wszystkich `Q` monitorów.** Powód
jest zmierzony, nie założony: wariant z nazwanymi strumieniami pośrednimi
(`pilot/diag_X_named.rql`) daje `STREAM_SELECT_* = 0` — nazwanie kasuje warstwę R2
w całości — a materializację **przenosi z licznika do mianownika**. Populacja
mieszana nie osłabiałaby efektu liniowo; zmieniałaby to, co metryka mierzy.
Warstwa R1 nazwanie **przeżywa**, więc F9-R1 jest odporna na styl nazewniczy.

---

## 4. Dane

| Pozycja | Wartość |
|---|---|
| Generator | `gen_corpus.py` (SplitMix64 zapisany w pliku — bez `random` i bez zależności od wersji Pythona) |
| Ziarno danych głównych | `20260808_0001` |
| Ziarno danych kalibracyjnych | `20260808_0002` (**rozdzielone** — kalibracja nie może biec na danych głównych) |
| Zakres wartości | `[0, 1000]`, jedno pole `INTEGER` na źródło |
| **Rekordy źródła szybkiego taktu** | **3000** |
| **Rekordy źródła wolnego taktu** | **1500** (dokładnie połowa) |
| Rekordy kalibracyjne | 600 / 300 |
| Ta sama liczba po stronie Flinka | `--slots 3000` (job sam bierze połowę dla źródeł `1/50`) |

**Dlaczego liczba rekordów musi być zamrożona i wspólna dla obu maszyn:**
w Kroku 2 liczba zapisów substratu wahała się między uruchomieniami (19 wobec 15)
wyłącznie od długości źródła i timingu odczytu. Metryka bajtowa jest
deterministyczna **przy ustalonej liczbie rekordów** — i tylko wtedy.

**Dlaczego akurat 3000:** bramka poprawności (§7.1) wymaga co najmniej **2000**
publicznych rekordów **każdego nazwanego wyniku**. Monitory F9-R2 pracują na
`1/100`, więc dają 3000 rekordów; F9-R1 i F9-X pracują na `1/150`
(`n_h = 3000 + 1500 = 4500`). Wiążąca jest F9-R2 z zapasem 1,5×.

**Budżet czasu, świadomie zapisany przed pomiarem:** macierz to
`3 rodziny × 20 bloków × 6 wartości Q × 4 profile = 1440` przebiegów. Przy
takcie deklarowanym `1/100` jeden przebieg trwa 30 s, czyli ≈ 12 h czystego
liczenia plus rozgrzewki i reboot między rodzinami. Kalibracja może takt
**spowolnić** (§8), a wtedy budżet rośnie proporcjonalnie do skali.

---

## 5. Uzasadnienie scenariusza (D-3) — motivational validity

§10 żąda, żeby ten tekst istniał **przed wynikami**: „inaczej cały układ czyta się
jako skonstruowany pod tezę". Poniższe jest tą odpowiedzią, w wersji
**niewygładzonej** — z zastrzeżeniami, nie bez nich.

### 5.1. Dlaczego to pytanie decyduje

`FLINK_NATURAL` nie tworzy `Q` instancji dlatego, że Flink jest gorszy, tylko
dlatego, że monitory są **równoważne, lecz strukturalnie różne**, a DataStream nie
ma normalizacji algebraicznej. Ciężar przenosi się z internal validity na
**motivational validity**: pierwsze pytanie recenzenta brzmi „kto pisze to samo
obliczenie w ośmiu różnych, równoważnych postaciach?".

**Kryterium dyskwalifikujące, przyjmowane wprost:** każda użyta postać musi być tą,
którą wybrałby autor piszący **wyłącznie swój** monitor, bez wiedzy o pozostałych
`Q−1`. Postać, której nikt nie napisałby w izolacji, dyskwalifikuje rodzinę.

### 5.2. Scenariusz

Linia produkcyjna z kilkoma maszynami, wspólna magistrala telemetrii. Strumienie
źródłowe są **infrastrukturą**: deklaruje je zespół platformy, każdy zespół
aplikacyjny czyta je pod tymi samymi nazwami. Monitory **nie są** infrastrukturą —
pisze je ten, kto ich potrzebuje. Trzy drogi, wszystkie obecne jednocześnie:

1. **Wielu najemców nad wspólnym źródłem** — utrzymanie ruchu, jakość i zespół
   procesowy monitorują tę samą maszynę do innych celów. Każdy ma własną regułę,
   retencję i odbiorcę; żaden nie czyta RQL pozostałych.
2. **Monitory dziedziczone i kopiowane między wdrożeniami** — kopia zachowuje
   postać składniową źródła kopiowania, nie postać kanoniczną.
3. **Ta sama specyfikacja zapisana przez różne osoby** — specyfikacja mówi *co*,
   nie *w jakiej kolejności wymienić wejścia*; ta decyzja jest arbitralna.

Czego scenariusz **nie zakłada**: że ktokolwiek pisze osiem wariantów celowo, że
istnieje przegląd kodu wymuszający jedną postać, ani że autorzy wiedzą o sobie.

**Konsekwencja dla Flinka, zapisana uczciwie:** w tym samym scenariuszu autor jobu
Flinka **też** nie widzi pozostałych `Q−1` monitorów, więc `FLINK_NATURAL` jest
wierną, a nie osłabioną reprezentacją. `FLINK_MANUAL` odpowiada sytuacji, w której
ktoś **zobaczył wszystkie `Q`** — czyli wiedzy, której scenariusz autorom odmawia.
Dlatego `FLINK_MANUAL` jest kontrolą best-case **poza progiem**.

### 5.3. Per rodzina, z zastrzeżeniami

| Rodzina | Postać | Werdykt kryterium |
|---|---|---|
| F9-R2 | `FROM A+B` / `FROM B+A` | ✅ obie równie prawdopodobne; osie symetryczne, żadna nie jest „pierwsza" |
| F9-R1 | `(A>2)#(B>1)` | ✅ zapis „kompensuj tor, potem zestawiaj" |
| F9-R1 | `(A#B)>3` | ⚠️ tak, **jeżeli autor myśli taktem strumienia wynikowego** |
| F9-X | inline `((A>2)#(B>1)) + ((C>2)#(D>1))` | ⚠️ idiom języka dla podwyrażeń jednorazowego użytku, trzy ograniczenia |
| wszystkie | identyczny program pól co do tokenów | ⚠️ przy przepisywaniu ze specyfikacji |

**F9-R1 (⚠️).** Postać P2 nie wymaga arytmetyki specjalnego przeznaczenia:
skoro `i·Δ_A = k·Δ_B = τ`, to `i + k = τ/Δ_h`, czyli zwykłe „opóźnienie razy takt
strumienia". Zastrzeżenie jest węższe: chodzi o to, czy autor **myśli w slotach
strumienia przeplecionego**, zamiast w opóźnieniach torów. To różnica modeli
myślowych — autor sygnałowy napisze P2, autor czujnikowy P1. **Przypisanie
postaci P2 autorowi myślącemu sygnałowo wchodzi tu jako założenie jawne.**
Dobierania „okrąglejszych" stałych zaniechano świadomie: nic nie kupuje
(`20 ms × 150 Hz = 3` nie jest trudniejsze niż `20 ms × 200 Hz = 4`), a wyglądałoby
na strojenie rodziny pod tezę.

**F9-X (⚠️), trzy ograniczenia zapisane bez wygładzania:**

* postać symetryczna, w której **oba** operandy `+` są złożone, jest o krok
  głębsza niż cokolwiek w korpusie projektu; krok polega na symetrii, nie na
  nowej konstrukcji, ale nie jest wprost udokumentowany;
* zaświadczone złożenia inline siedzą głównie w testach pisanych przez autora
  silnika; materiałem przykładowym jest tylko `examples/rmpy`. **Korpusu kodu
  użytkowników nie ma** — i to ograniczenie dotyczy całego scenariusza z §5.2,
  nie samego F9-X;
* postać zapisu jest zamrożona dla wszystkich `Q` monitorów; populacja mieszana
  zmienia to, co metryka mierzy (§3.4).

Podział w tym języku jest czytelny i potwierdzony korpusem: **podwyrażenie
jednorazowego użytku pisze się inline, etap wielokonsumencki dostaje nazwę**
(`issue167_dedup_cascaded`, `issue167_triarg`, `examples/rmpy/query4.rql` wobec
`examples/ecg`, gdzie każdy z 13 nazwanych etapów ma konsumenta).

**Zastrzeżenie wspólne (⚠️).** K23 bada przemienność **operatora strumieniowego**,
nie przemienność wyrażeń arytmetycznych: `Sqrt(A[0]*A[0]+B[0]*B[0])` i
`Sqrt(B[0]*B[0]+A[0]*A[0])` to dla odcisku dwa różne programy. Gdyby jeden z ośmiu
autorów napisał składniki w innej kolejności, jego monitor wypadłby z klasy
równoważności i liczyłby się jako osobna instancja — efekt słabnie **liniowo**
z liczbą takich autorów i mechanizmu to nie unieważnia.

Trzy ⚠️, zero ❌. Żadne z zastrzeżeń nie jest defektem aparatury ani mechanizmu —
to są **granice twierdzenia**, które K23 będzie mogła postawić.

---

## 6. Profile i strona Flinka

### 6.1. Cztery profile RetractorDB (pełny układ 2×2)

| Profil | dedup | share | commutative (R2) | factor (R1) | Rola |
|---|---|---|---|---|---|
| `DEFAULT` | ON | ON | ON | ON | wszystkie mechanizmy |
| `NO_R2_CANON` | ON | ON | **OFF** | ON | ablacja minimalna F9-R2 |
| `NO_R1_FACTOR` | ON | ON | ON | **OFF** | ablacja minimalna F9-R1 |
| `NO_R1_NO_R2` | ON | ON | **OFF** | **OFF** | komórka kontrolna 2×2 dla F9-X |

`RDB_OPT_DEDUP_SUBSTRATES` zostaje **ON we wszystkich** profilach — §10 żąda
ablacji minimalnych, a dedup nie jest badanym mechanizmem żadnej rodziny.
**Przywrócenie 87,5% przez wyłączenie deduplikacji w ablacji jest zakazane**:
dałoby ablację nieminimalną, czyli dokładnie to, co dyskwalifikuje profil `OFF`.

Profil `OFF` z K6c **nie wchodzi** do macierzy (zmienia kilka mechanizmów naraz
i dawał inną semantykę natywnych liczników); może być pokazany wyłącznie
diagnostycznie, poza werdyktem.

### 6.2. Dwa warianty Flinka

`FLINK_NATURAL` — idiomatyczny DataStream z `Q` niezależnie nazwanymi monitorami,
**bez ani jednego** ręcznego wydzielenia. `FLINK_MANUAL` — ten sam job po ręcznym
wydzieleniu wspólnego podplanu; kontrola best case, **niewchodząca do progu**.

Optymalizacja Flinka **nie jest blokowana**: łańcuchowanie włączone,
`disableOperatorChaining()` nie występuje. Odczyt z planu fizycznego: Flink
wciągnął identyczne operatory do jednego wierzchołka (60 węzłów → 28 w F9-X), ale
**nie scalił ich w jeden operator**. DataStream nie ma eliminacji wspólnych
podwyrażeń nawet dla podplanów **identycznych składniowo**. Ryzyko osi kampanii
(„naturalny Flink sam współdzieli i obala H9") w tej postaci nie zmaterializowało
się — gdyby się zmaterializowało, wynik zostawał w kampanii i działał przeciw H9.

**`FLINK_MANUAL` nie jest best case przy `Q ≤ 2`** — w F9-X przy `Q=1` jest gorszy
o 25%, bo ręczne wydzielenie materializuje węzeł, który pojedynczy monitor
policzyłby w swoim etapie publicznym. Progu to nie dotyczy.

### 6.3. Serializer kanoniczny

`Canon.recordBytes` po stronie Flinka jest portem `rdb::probe::canonicalRecordBytes`
z podwójną bramką: 18 wektorów o znanej odpowiedzi **oraz** porównanie z
`oracle/canonical_oracle` — programem bez własnej implementacji, linkującym
`librdb.a` i wołającym funkcję silnika. Punkt drugi jest ważniejszy: wyklucza
sytuację, w której oba przepisania specyfikacji zgadzają się ze sobą i **oba**
rozjeżdżają z kodem. Wynik: `wektory=18 porownane_z_oracle=18 bledy=0`.

### 6.4. Przewidywane wartości (arytmetyka planu, nie odczyt licznika)

Jednostka `n_h·w`. Wartości `DEFAULT` i ablacji potwierdzone pilotem
compile-only; wartości Flinka wyprowadzone ze zbudowanych planów.

| Rodzina | `DEFAULT` | ablacja min. | `FLINK_NATURAL` | `FLINK_MANUAL` | red. wobec ablacji | red. wobec Flinka |
|---|---|---|---|---|---|---|
| F9-R2 | 0,667 | 1,333 | 5,333 | 0,667 | **50,0%** | **87,5%** |
| F9-R1 | 1,000 | 2,000 | 8,000 | 1,000 | **50,0%** | **87,5%** |
| F9-X | 5,000 | 12,000 | 32,000 | 5,000 | **58,3%** | **84,4%** |

**Poprawka wobec `SZKIC_RODZIN.md` §7 i `RAPORT_PILOTA.md` §2, wchodząca tutaj:**
wiersz zbiorczy „każda rodzina wobec `FLINK_NATURAL`: 1 → 8 instancji, 87,5%" jest
poprawny dla F9-R2 i F9-R1, ale **nie dla F9-X**, gdzie jest to **84,4%**
(5 → 40 instancji, nie 1 → 8). Wiersz zbiorczy był uproszczeniem policzonym dla
rodzin jednowęzłowych. Szkic i raport pilota zostają nietknięte.

**Dwie różne krzywe, nie jedna.** Redukcja wewnętrzna **nasyca się** na `1 − 1/F`
powyżej progu postaci; redukcja wobec Flinka rośnie liniowo jak `1 − 1/Q`
(a dla F9-X `1 − 5/(4Q)`). Skrypt werdyktu nie ma prawa oczekiwać trendu po
stronie ablacji.

| `Q` | 1 | 2 | 4 | 8 | 16 | 32 |
|---|---|---|---|---|---|---|
| F9-R2, F9-R1 wobec ablacji | 0% | 0% | 50% | **50%** | 50% | 50% |
| F9-X wobec ablacji | 0% | 0% | 50% | **58,3%** | 58,3% | 58,3% |
| F9-R2, F9-R1 wobec `FLINK_NATURAL` | 0% | 50% | 75% | **87,5%** | 93,75% | 96,875% |
| F9-X wobec `FLINK_NATURAL` | **−25%** | 37,5% | 68,75% | **84,375%** | 92,19% | 96,09% |

Wartość **ujemna przy `Q=1` w F9-X jest predeklarowana**, nie jest usterką:
`FLINK_NATURAL` ma tam 4 jednostki wobec 5 w `DEFAULT`, z tego samego powodu, dla
którego `FLINK_MANUAL` nie jest tam best case.

**Zapas nad progiem 40% wynosi 10 pp, a nie 47 pp.** Wiążącym porównaniem jest
ablacja wewnętrzna. Metryka bajtowa jest deterministyczna, więc tego zapasu nie
zagraża rozrzut — zagraża mu wyłącznie **błąd w projekcie rodziny**.

---

## 7. Progi, bramki i skrypt werdyktu

### 7.1. Bramka poprawności (przed odczytem kosztów)

Wspólny oracle na co najmniej **2000 publicznych rekordach każdego nazwanego
wyniku** po ogonie. Porównanie obejmuje liczbę i nazwy wyników, deskryptory,
kolejność, wartości, `NULL`, luki oraz brak rekordów ogona. Dla RetractorDB także
identyczność publicznych artefaktów **między profilami**. Dla każdego mechanizmu
co najmniej **trzy mutanty**: zmieniona faza/shift, kolejność pola, mapa
`NULL`/luka — oracle ma wykryć wszystkie.

Klasyfikacja rozbieżności jest **obowiązkowa i należy do człowieka** (STOP-6):
rozbieżność przypisana silnikowi lub profilowi = **brak wsparcia H9 w rodzinie**;
defekt portu, oracle'a albo harnessu = **zatrzymanie iteracji, nowa wersja, bez
łączenia danych**. Skrypt werdyktu czyta tę klasyfikację z `gates.tsv` i odmawia
wydania werdyktu, gdy jej nie ma.

### 7.2. Kontrole negatywne (każda rodzina)

`Q=1` (brak klasy równoważności → brak redukcji **wewnętrznej**); ten sam program
bez etapu materializowanego (oczekiwane **zero** bajtów substratów — wynik zerowy
oczekiwany, nie dowód niedziałania aparatury); niezgodne przesunięcie
`i·Δ_A ≠ k·Δ_B` dla R1; zmieniona kolejność pól i inne grupowanie źródeł dla R2;
publiczny strumień blokujący bezpieczne scalenie.

Nieoczekiwane scalenie kontroli nierównoważności przy poprawnej aparaturze =
**brak wsparcia H9 w rodzinie** (nie unieważnienie iteracji).

### 7.3. Próg H9 — cztery warunki łącznie

Punktem rozstrzygającym jest **`Q = 8`**. `Q = 1,2,4` są kontrolą trendu,
`Q = 16,32` pomiarem skalowania — **nie dodatkowymi szansami na zaliczenie**.

1. wszystkie bramki poprawności, mechanizmu i kontroli są czyste;
2. `DEFAULT` zmniejsza metrykę pierwotną o co najmniej **40%** względem ablacji
   minimalnej **oraz** względem `FLINK_NATURAL`;
3. górna granica bootstrap 95% CI ilorazu czasu `DEFAULT/minimal_ablation` nie
   przekracza **1,05**;
4. publiczne wyniki i ich materializacja pozostają identyczne.

**H9 otrzymuje wsparcie, gdy próg przejdą co najmniej 2/3 rodzin.** W ważnej,
kompletnej rodzinie remis albo niespełnienie dowolnego progu liczy się **przeciw**
H9; iteracja technicznie nieważna lub niepełna **nie wydaje werdyktu** i musi
zostać powtórzona w nowym katalogu. Rodziny nie zastępuje się po otwarciu wyników.

**Gdzie naprawdę siedzi treść H9:** nie w „redukcji o ponad 40%", lecz w koniunkcji
(i) `DEFAULT` bije `FLINK_NATURAL` przy `DEFAULT ≈ FLINK_MANUAL` — przewagą jest
**automatyczne wykrycie**, nie zdolność niedostępna Flinkowi — oraz (ii) górna
granica CI ilorazu czasu ≤ 1,05, czyli mechanizm jest **darmowy**. Punkt (ii) jest
po K6c najbardziej zagrożony i to on decyduje o wartości wyniku. Identyczność
`DEFAULT` i `FLINK_MANUAL` jest przy tym **konstrukcyjna** (MANUAL zbudowano jako
odtworzenie węzłów planu `DEFAULT`) i wolno ją nazwać wyłącznie tak.

### 7.4. Bootstrap

| Pozycja | Wartość |
|---|---|
| Statystyka | iloraz median po blokach, `DEFAULT / minimal_ablation`, na `compute_median_ns` |
| Sparowanie | replikacja losuje **indeksy bloków**, nie wartości osobno per profil |
| Bloki | 20 |
| Replikacje | 10 000 |
| CI | percentylowe, dwustronne, 2,5% / 97,5% |
| Ziarno | `20260808_0003` |
| PRNG | SplitMix64 zapisany w `verdict.py` |

Bootstrap dotyczy **wyłącznie zmiennego czasu**. Metryka bajtowa jest
deterministycznym wynikiem mechanizmu i nie podlega bootstrapowi.

### 7.5. Skrypt werdyktu

`verdict.py` — **wykonywalny**, wydaje werdykt bez interpretacji człowieka. Progi,
ablacje minimalne, komórka rozstrzygająca, reguła 2/3 i wielkości rozdzielające są
w nim **stałymi**, nie parametrami wiersza poleceń.

Kody wyjścia: `0` H9 wsparta, `1` H9 bez wsparcia, `2` **brak werdyktu** (iteracja
technicznie nieważna albo niepełna).

**Skrypt werdyktu jest aparaturą i podlega regule „bramka musi umieć odróżnić
wersję obaloną".** `./verdict.py --selftest` uruchamia go na sztucznych danych
o znanej odpowiedzi — **18 przypadków**, w tym wersje celowo obalone: poniżej
progu bajtowego (1 i 2 rodziny — sprawdza regułę 2/3 w obie strony), dokładnie na
progu czasowym 1,05 i tuż nad nim, defekt aparatury, rozbieżność przypisana
silnikowi, brak wpisu bramki, przekroczenie 80% slotu, zgubiony rekord, scalenie
przy `Q=1`, kontrola pusta rozjechana z `DEFAULT`, zerowy mianownik, brak całej
rodziny oraz pułapka **„instancje spadają, bajty nie"** — potwierdzona w tym łuku
niezależnie po obu stronach porównania.

Rozgraniczenie, które skrypt utrzymuje świadomie: **odchylenie od predeklarowanej
krzywej nie unieważnia iteracji**, tylko jest raportowane; o wyniku rozstrzyga
próg. §10 mówi to wprost dla najważniejszego przypadku („jeśli naturalny Flink sam
współdzieli, taki wynik pozostaje w kampanii i działa przeciw H9"). Bramka
unieważniająca iterację za samo odejście od przewidywania uniemożliwiałaby wynik
negatywny — czyli byłaby dokładnie tą postacią bramki, która w tym projekcie
zawiodła czterokrotnie.

---

## 8. Wykonanie pomiarów

### 8.1. Protokół kalibracji rate (wartość → ANEKS-1)

Na **osobnych danych kalibracyjnych** (`data/calib/`, ziarno `20260808_0002`),
**bez porównywania `DEFAULT` z ablacją**. Kryterium: najgorszy profil RetractorDB
przy `Q = 32` ma `p99 ≤ 50%` logicznego slotu. Kalibracja skaluje **wszystkie**
interwały wspólnym czynnikiem, zachowując ich stosunki — stałe `i = 2`, `k = 1`,
`>3` pozostają nienaruszone. Rate jest potem **stały dla wszystkich profili danej
rodziny**.

`ANEKS-1_rate.tsv` musi zawierać `rate_scale` oraz `calibration_saw_effect=no`;
`freeze_check.sh macierz` bez tego nie przechodzi.

### 8.2. Macierz

20 powtórzeń na komórkę w **20 sparowanych blokach** obejmujących wszystkie
profile. Kolejność profili wewnątrz bloku wylosowana z ziarna `20260808_0004`
i zapisana w `blocks.tsv` (**1440 przebiegów**). Kolejność rodzin stała (między
rodzinami idzie reboot), kolejność `Q` rosnąca. Przed blokami każdy profil dostaje
**osobny przebieg rozgrzewkowy, niewchodzący do wyniku**.

Kontrola: temperatura, governor `performance`, przypięcie CPU, wersja kernela.
Reboot między rodzinami formą `ssh michal@192.168.88.13 'sync; sudo -n reboot'`.
Flink wykonuje **tę samą liczbę rekordów**; powtórzenia czasu Flinka są opisowe
i nie służą do między-systemowego twierdzenia o szybkości.

### 8.3. Warunki zatrzymania

| Warunek | Skutek |
|---|---|
| komórka przekracza **80%** slotu albo gubi rekord | **STOP-8** — cała iteracja rodziny zatrzymana **bez werdyktu**; komórki nie wolno po cichu wykluczyć. Nowy, niższy rate wymaga **nowej predeklaracji i nowego katalogu**; danych między iteracjami nie wolno łączyć |
| rozbieżność na bramce poprawności | **STOP-6** — klasyfikacja przez człowieka: silnik/profil = brak wsparcia H9 w rodzinie; aparatura = nowa iteracja |
| złożenie F9-X przestaje działać | K23 zatrzymuje się; rodziny **nie** zastępuje się inną |
| jakakolwiek pozycja tej predeklaracji wymaga zmiany | nowa predeklaracja, nowy katalog |

---

## 9. Aparatura zamrożona tym dokumentem

| Artefakt | Rola | Bramka własna |
|---|---|---|
| `gen_corpus.py` | dane główne, kalibracyjne, 21 planów RQL | `--check` |
| `gen_blocks.py`, `blocks.tsv` | kolejność 1440 przebiegów | `--check` |
| `verdict.py` | **skrypt werdyktu** | `--selftest`, 18 przypadków |
| `mechanism_table.py` | klasyfikator substratów (poprawiony, §0.1) | `--gate`, 3 warunki |
| `build_profiles.sh`, `profiles.tsv` | budowa i weryfikacja czterech profili | `--build-info` bajtowo |
| `flink/java/*.java` | sześć jobów, serializer, `PlanDump` | 18 wektorów + oracle C++ |
| `flink/canonical_vectors.tsv`, `flink/oracle/` | bramka serializera wobec kodu silnika | 18/18 |
| `pilot/` | zamknięty zapis P4 — **nietykany** | — |
| `freeze_check.sh` | bramka niezmienności, trzy zakresy | — |
| `manifest.sha256` | sumy wszystkich powyższych | `sha256sum -c` |

**Aneksy** (wchodzą po zamrożeniu, każdy przed fazą, którą odblokowuje):

| Aneks | Treść | Przed |
|---|---|---|
| `ANEKS-1_rate.tsv` | skalibrowany rate + potwierdzenie, że kalibracja nie oglądała efektu | P8 |
| `ANEKS-2_worker_binaria.tsv` | SHA-256 czterech binariów workera (inna architektura) | P6 |
| `ANEKS-3_worker_srodowisko.tsv` | kernel, governor, przypięcie CPU, liczba rdzeni | P6 |

### 9.1. Zakresy bramki niezmienności

```bash
./freeze_check.sh predeklaracja   # STOP-5 — host; workera NIE budzi
./freeze_check.sh worker          # przed P6 — środowisko i binaria workera
./freeze_check.sh macierz         # przed P8 — wszystko + ANEKS-1
```

**Zakres jest obowiązkowy; skrypt bez argumentu kończy się kodem 2.** Bramka,
która sama wybiera sobie łatwiejszy zakres, jest tą samą klasą usterki co bramka
przechodząca z niewypełnionymi polami.

---

## 10. Czego ta kampania nie będzie mogła twierdzić

Sukces **nie upoważnia** do zdań „RetractorDB jest szybszy od Flinka", „zawsze
zużywa mniej pamięci" ani „Flink nie potrafi współdzielić". Wniosek przy wsparciu
H9 dotyczy **automatyzacji współdzielenia materializacji w klasie `Q = 8`**, nie
ogólnej szybkości przetwarzania strumieni. Do czasu zakończenia K23 H9 **nie jest
contribution artykułu**.

W raporcie i w artykule liczbę bajtową podaje się jako **potwierdzenie
mechanizmu**, a nie jako nagłówek; nagłówkiem jest koniunkcja z §7.3.
