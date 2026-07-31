# Badanie higieniczne `1bb2d2c`: czy rozdzielenie wątków unieważnia Tier B

Predeklaracja. Napisana **przed** jakimkolwiek pomiarem.

## Cel

`1bb2d2c` („engine rt - issue separation of client thered") przenosi wątek
komunikacyjny silnika poza rdzenie, na których pracuje wątek czasu
rzeczywistego. Pytanie: **czy ta zmiana unieważnia 540 przebiegów Tier B
zmierzonych na `e1c13bb`?**

## Dlaczego to badanie ma inny kształt niż poprzednie

Badanie higieniczne `e1e5181` porównywało **równość artefaktów** — zrzuty planu,
bajty potoków, wyjście klienta. To było właściwe pytanie dla tamtej zmiany
i było rozstrzygalne binarnie.

Tu tak się nie da. `1bb2d2c` **nie zmienia żadnego artefaktu** — zmienia to, co
pracuje na mierzonym rdzeniu. Porównanie bajtów odpowiedziałoby „brak wpływu"
i byłoby bezużyteczne, dokładnie tak jak badanie `e1e5181` orzekło „brak wpływu"
o defekcie, którego konstrukcyjnie nie mogło zobaczyć. **Pytanie jest z natury
statystyczne i dotyczy rozkładów czasów.**

## Co dokładnie się zmieniło i gdzie może to zaboleć

Przed `1bb2d2c` wątek komunikacyjny (SCHED_OTHER) dzielił izolowany rdzeń 3
z wątkiem przetwarzania (SCHED_FIFO 50), bo `taskset -c 3` przypina cały proces.

- **Wywłaszczenia nie ma i nie było.** SCHED_OTHER nigdy nie wywłaszczy
  SCHED_FIFO, więc wątek komunikacyjny nie mógł przerwać `processRows()`.
- **Ale zaśmiecanie cache było.** Przy duty poniżej 100 % wątek RT oddaje rdzeń
  między slotami, a wątek komunikacyjny budzi się tam co 1 ms i wykonuje
  `try_receive`. Po `1bb2d2c` go tam nie ma. To przesunięcie systematyczne
  i jednokierunkowe, nie szum.
- **`e2e_ns` dochodzi ruch koherencji** — `boradcast()` pisze do kolejki
  czytanej teraz z innego rdzenia.

## Warunek ważności — dlaczego mierzymy ILORAZ, a nie czas

To jest sedno projektu tego badania i powód, dla którego pomiar samych czasów
odpowiedziałby na niewłaściwe pytanie.

Werdykt kampanii nie orzeka o wartościach bezwzględnych. Orzeka o
`r(c) = mediana₁₅(ALGSTRUCT) / mediana₁₅(STRUCT)`, przy progu istotności
praktycznej **10 %** (reguła decyzyjna K6c, zamrożona). Oba człony ilorazu są
mierzone **na tej samej aparaturze**, więc systematyczne przesunięcie wspólne dla
obu profili **skraca się w ilorazie**.

Stąd dwa wnioski, które trzeba rozdzielić:

1. **Wewnątrz zamkniętego badania nie ma problemu.** Każde badanie Tier B
   obejmuje wszystkie cztery profile × 15 powtórzeń w jednym przebiegu, na
   jednej aparaturze. Ilorazy W2–W7 są więc wewnętrznie spójne niezależnie od
   tego, jaka to była aparatura.
2. **Problem jest w zestawianiu rodzin.** W8 i W9 zostaną zmierzone na
   `1bb2d2c`, a W2–W7 na `e1c13bb`. Jeżeli przesunięcie NIE jest wspólne dla
   profili, ilorazy z różnych aparatur nie są porównywalne i Tier B trzeba
   powtórzyć w całości.

Badanie odpowiada zatem na pytanie: **czy przesunięcie aparatury jest wspólne
dla profili, czyli czy `r(c)` jest zachowane.**

## Metoda

Dwie binarki silnika, identyczna konfiguracja profilu (`RDB_OPT_*`,
`RDB_BENCH_PROBE=ON`, `setcap`), różniące się **wyłącznie commitem**:

| oznaczenie | commit |
|---|---|
| `PRZED` | `e1c13bb` |
| `PO` | `1bb2d2c` |

- **Komórki:** `W2_Q32` (180 Hz, duty 47 %) i `W3_d3` (405 Hz, duty 45 %).
  Obie pochodzą z **zamkniętych** badań Tier B, których ważność jest przedmiotem
  sporu, i rozpinają zakres częstotliwości slotu. Komórki o duty ≥ 100 % są
  nieprzydatne: tam wątek komunikacyjny i tak nie dostawał CPU, więc nie było
  czego przenosić.
- **Profile:** `ALGSTRUCT` i `STRUCT` — dokładnie licznik i mianownik `r(c)`.
- **Powtórzenia:** 30 na (komórka × profil × commit) = **240 przebiegów**.
  Liczba wyznaczona analizą mocy, nie przyjęta z kampanii — patrz niżej.
- **Przeplot.** Kolejność `PRZED`/`PO` naprzemienna w obrębie każdej pary
  (komórka, profil, powtórzenie). Protokół R8 (reboot między badaniami) jest tu
  niestosowalny — 240 rebootów nie wchodzi w grę — więc dryf termiczny
  kontrolujemy przeplotem, a nie odstępem. To jest świadome odstępstwo i musi
  zostać zapisane w `JOURNAL.md`.
- **Governor CPU:** `performance` na czas pomiaru, przywracany zawsze —
  ten sam warunek, co `set_performance_governor` w harnessie kampanii.
  Bez tego pomiar biegnie na `ondemand`, gdzie skalowanie częstotliwości
  dokłada wariancji: `W2_Q32` STRUCT dało 3,18 ms wobec 2,46 ms w kampanii.
- **Metryka główna:** `compute_ns`. Uboczne, raportowane bez mocy decyzyjnej:
  `e2e_ns` (p50, p99).

## Liczba powtórzeń — wyznaczona, nie odziedziczona

Kampania używa 15 powtórzeń. Przepisanie tej liczby tutaj byłoby założeniem, bo
kryterium jest inne: kampania wykrywa efekty ≥ 10 %, a to badanie ma **wykazać
równoważność** z marginesem 0,02, co jest wymaganiem pięciokrotnie ostrzejszym.

Moc policzona **przed pomiarem**, na niezależnych danych — zamkniętych badaniach
Tier B (`study_01_W2`, `study_02_W3`, po 15 powtórzeń na profil). Symulacja
zakłada, że hipoteza zerowa jest PRAWDZIWA (obie strony losowane z tej samej
populacji) i podaje szerokość `CI(c)`, jakiej należy się spodziewać:

| komórka | reps=15 | reps=30 | reps=45 |
|---|---|---|---|
| `W2_Q32` | (−0,0127; +0,0127) | (−0,0070; +0,0073) | (−0,0033; +0,0033) |
| `W3_d3` | (−0,0047; +0,0047) | (−0,0034; +0,0035) | (−0,0030; +0,0030) |

Realne CV median `compute_ns` między przebiegami: `W2_Q32` 1,42 % (STRUCT)
i 0,63 % (ALGSTRUCT).

Przy 15 powtórzeniach `W2_Q32` mieści się w marginesie, ale zostaje **0,007
zapasu** z każdej strony — prawdziwy efekt tej wielkości dałby werdykt
„nierozstrzygnięte", czyli 25 minut pomiaru bez odpowiedzi. **Przyjmujemy 30**;
zapas rośnie trzykrotnie, a koszt z ~25 do ~50 minut. 45 powtórzeń nie kupuje
już nic istotnego dla `W3_d3`.

Ta zmiana została wprowadzona **przed jakimkolwiek pomiarem** i wyłącznie na
podstawie danych już istniejących. Po pierwszym przebiegu liczba powtórzeń jest
zamrożona.

## Kryterium — zamrożone przed pomiarem

Dla każdej komórki `c`:

```
r_PRZED(c) = mediana₃₀(ALGSTRUCT, e1c13bb) / mediana₃₀(STRUCT, e1c13bb)
r_PO(c)    = mediana₃₀(ALGSTRUCT, 1bb2d2c) / mediana₃₀(STRUCT, 1bb2d2c)
Δ(c)       = r_PO(c) − r_PRZED(c)
```

`CI(c)` — bootstrapowy przedział 95 % dla `Δ(c)`, **10 000 replikacji, ziarno
`20260731`, percentyle 2,5 i 97,5**. Ziarno i liczba replikacji przejęte
z reguły decyzyjnej kampanii, żeby nie mnożyć konwencji.

**Margines równoważności: ±0,02**, czyli jedna piąta progu istotności
praktycznej kampanii (10 %). Uzasadnienie marginesu: przesunięcie aparatury
mniejsze niż jedna piąta najmniejszego efektu, o którym kampania cokolwiek
orzeka, nie jest w stanie przenieść żadnej komórki przez granicę klasy.

| Werdykt | Warunek |
|---|---|
| **BRAK WPŁYWU** | dla **każdej** komórki `CI(c)` zawiera się w całości w `(−0,02; +0,02)` |
| **JEST WPŁYW** | dla **choćby jednej** komórki `CI(c)` wychodzi poza `(−0,02; +0,02)` |
| **NIEROZSTRZYGNIĘTE** | `CI(c)` przecina granicę marginesu, nie zawierając się w nim ani nie leżąc poza |

To jest test **równoważności**, nie test różnicy. Brak istotnej różnicy nie jest
dowodem równoważności i nie zostanie za taki uznany — dokładnie ten błąd
popełniło badanie `e1e5181`, orzekając „brak wpływu" z nieumiejętności zobaczenia
efektu.

## Skutki werdyktu — zapisane z góry, żeby nie negocjować po fakcie

- **BRAK WPŁYWU** → 540 przebiegów Tier B (W2, W3, W4, W5, W7) zostaje ważne.
  Domierzamy tylko W8 (bez `Q32`) i W9 na `1bb2d2c`. Kampania zapisuje trzy
  przypięcia i uzasadnienie.
- **JEST WPŁYW** → Tier B powtarzamy w **całości**, w nowym katalogu wyników,
  na `1bb2d2c`. 540 przebiegów przechodzi do materiału historycznego.
- **NIEROZSTRZYGNIĘTE** → zwiększamy liczbę powtórzeń do 60 i powtarzamy
  badanie; jeżeli nadal nierozstrzygnięte, traktujemy jak **JEST WPŁYW**,
  bo ciężar dowodu leży po stronie twierdzenia o ważności.

## Czego to badanie NIE mierzy

Wypisane wprost, bo poprzednie badanie higieniczne upadło właśnie na
przemilczanym ograniczeniu.

- **Nie mierzy komórek o duty ≥ 100 %** (`W8_Q32`, `W8_Q08` w p99). Tam wątek
  komunikacyjny nie dostawał CPU w ogóle, więc jego przeniesienie ma inny
  charakter niż mierzone tutaj i nie wolno ekstrapolować.
- **Nie orzeka o `e2e_ns`.** Ta metryka jest raportowana, ale margines
  równoważności jest wyznaczony dla `compute_ns`, bo to metryka główna kampanii.
- **Nie zastępuje werdyktu kampanii** i nie wchodzi do żadnej tabeli artykułu.
- **Nie mierzy Tier A ani kalibracji.** Kompilacja kończy się przed
  `rtActivate`, więc zmiana powinowactwa nie może ich dotknąć — to argument,
  nie pomiar, i jako argument jest zapisany.

### Ograniczenie doliczone po starcie pomiaru (2026-07-31, przebieg 57/240)

Kryterium ani zestaw komórek NIE zostały zmienione — to jest zapis słabości
wyboru, nie jego korekta. Człowiek zdecydował o pozostawieniu zestawu.

Wybierając `W2_Q32` i `W3_d3` uzasadniłem je m.in. „rozpięciem zakresu
częstotliwości slotu" (180 i 405 Hz). To uzasadnienie było błędne. Wątek
komunikacyjny budzi się co 1 ms, więc jego ekspozycja na mierzony rdzeń zależy
od **długości luki** między końcem obliczeń a końcem slotu, nie od
częstotliwości slotu:

| komórka | slot | p99 | luka | pobudek IPC w luce |
|---|---:|---:|---:|---:|
| `W4_Q32` | 66 667 µs | 33 022 | 33 645 | **33,6** |
| `W7_Q32` | 11 111 | 3 267 | 7 845 | 7,8 |
| `W9_Q32` | 8 333 | 3 370 | 4 964 | 5,0 |
| `W2_Q32` | 5 556 | 2 603 | 2 952 | 3,0 |
| `W3_d3` | 2 469 | 1 114 | 1 355 | **1,4** |

Mierzone komórki mają więc **najmniejszą** ekspozycję spośród wszystkich
z duty < 100 %; `W3_d3` bywa slotem bez ani jednej pobudki.

**Co to znaczy dla werdyktu.** Werdykt `BRAK WPŁYWU` z tego zestawu jest
słabszy, niż byłby z `W4_Q32`: mówi „przy ekspozycji 1,4–3,0 pobudki na slot
iloraz jest zachowany", a nie „przy dowolnej ekspozycji". Werdykt `JEST WPŁYW`
byłby natomiast **mocniejszy** — efekt widoczny przy najmniejszej ekspozycji
tym bardziej wystąpi przy większej.

Przeciwwaga, dla której zestaw uznano za wystarczający: metryką jest iloraz,
a zaśmiecenie cache jest wspólne dla obu profili i skraca się w nim. Zaburzy go
tylko nierówne skrócenie, czyli różnica **zbiorów roboczych** profili. Ta jest
największa tam, gdzie dedup ma najwięcej do usunięcia — a `W2_Q32` (32 identyczne
selekty) jest pod tym względem przypadkiem skrajnym w całej kampanii.

## Zdarzenia w trakcie pomiaru

**2026-07-31, przebieg ~57–94: dołożone zewnętrzne chłodzenie workera
(wentylator).** Zmiana aparatury w trakcie pomiaru, odnotowana obowiązkowo.

Sprawdzone, czy zostawiła ślad w danych — nie zostawiła:

| blok | pierwsza połowa | druga połowa | różnica |
|---|---:|---:|---:|
| `W2_Q32` STRUCT (60 przebiegów) | 2391,7 µs | 2390,9 µs | 0,03 % |
| `W2_Q32` ALGSTRUCT (38 przebiegów) | 2374,7 µs | 2375,3 µs | 0,03 % |

Wentylator wszedł na styku obu bloków, więc gdyby działał, skok byłby widoczny
właśnie tam. Przyczyna braku efektu: `vcgencmd get_throttled` zwraca `0x0` —
bity **trwałe** również zerowe, więc dławienia termicznego nie było ani razu,
a rdzeń 3 pracował na 1 800 000 kHz przez cały pomiar. Temperatura wpływa na
czas obliczeń przez częstotliwość; skoro ta się nie zmieniła, spadek 45 → 37 °C
tylko powiększył zapas do progu.

Pomiar nie został wznowiony. Gdyby dławienie wystąpiło (`get_throttled` ≠ 0),
decyzja byłaby odwrotna.

**Zabezpieczenie konstrukcyjne, niezależne od powyższego.** Nawet gdyby warunki
zmieniły się skokowo, statystyką decyzyjną jest `Δ = r_PO − r_PRZED`, a nie sam
iloraz. Przesunięcie wspólne dla obu stron skraca się w różnicy, bo w obrębie
każdego bloku profilu strony są przeplecione co powtórzenie. Bias przeżyłby
tylko wtedy, gdyby dotknął stron NIERÓWNO — czemu przeplot właśnie zapobiega.

## Higiena artefaktów (R14)

Surowe artefakty w `/dev/shm`, do repo `tar.gz` + indeks SHA-256. Repozytorium
kodu tylko do odczytu w trakcie pomiaru; obie binarki budowane **przed**
rozpoczęciem pomiaru, do osobnych katalogów `build/H217-*`, żeby profile
kampanii K6 pozostały nietknięte.

Każde porównanie raportuje LICZBĘ porównanych rzeczy; zero porównań jest błędem,
nie zgodą.
