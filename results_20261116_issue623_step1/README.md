# RetractorDB #623 - krok 1, 2026-11-16

## Wynik i decyzja

**Wyższa mediana czasu slotu została odtworzona. Jej przyczyną jest rozkład
pracy między fazami osi czasu, a nie wykazany dodatkowy koszt całego cyklu.**
R1 przenosi zapisy substratów z taktów źródeł na takt przeplotu. W tej rodzinie
podnosi to koszt typowego slotu, ale odciąża najcięższą fazę. Liczba zapisów
w pełnym okresie pozostaje taka sama. Callgrind nie pokazuje wzrostu całkowitej
liczby instrukcji, odczytów historii ani kopii rekordu odpowiadającego
historycznym 60 mikrosekundom.

**Rekomendacja po kroku 1: zachować obecne R1 do czasu doprecyzowania celu #623.
Nie wdrażać kroku 2 wyłącznie na podstawie kryterium mediany.** Pomijanie R1
obniżyłoby medianę, lecz w tych samych danych zwiększa koszt najcięższej fazy,
historyczne p99 oraz opóźnienie startowe. Jeśli intencją pozostaje optymalizacja
samej mediany, warunek w kompilatorze jest świadomą polityką wyboru planu z tym
kompromisem, a nie usunięciem wykazanego nadmiaru pracy.

Nie wskazano lokalnej poprawki wykonania, którą uzasadniałyby te pomiary.
Dokładny podział czasu pojedynczego zapisu między alokacje, kopiowanie,
metadane i operacje systemowe pozostaje nieustalony. Historycznych 60 us
nie przypisujemy w całości żadnej z tych operacji.

Zakres wykonany: [krok 1 zatwierdzonego planu](https://github.com/michalwidera/retractordb/issues/623#issuecomment-6925692623).
Kroki 2-6 nie zostały wykonane. Kod silnika, zamrożone H9 i K26v3 pozostały bez zmian.

## Pochodzenie i metoda

- Silnik: `d291d03c7269664fcb64f9e5e616431c7027df3d`, czyste `dev/muro`.
  Drzewo `src`: `65d27a7ae0cb9ad4a3c6894a3581f847451c9341`.
- Linux WSL2 x86_64, AMD Ryzen 9 9900X, GCC 15.2, Release `-O3 -DNDEBUG`,
  sondy ON, IPO wyłączone przez konfigurację builda z sondami. Przypięcie do CPU 15.
- Cztery profile H9 odbudowane kolejno w `build/R593-*`. Nazwy katalogów są
  historyczne; binaria są z powyższej bieżącej rewizji. Nie instalowano ich
  nad innym buildem. Końcowa odbudowa zgłosiła `no work to do`, a SHA-256
  każdego binarium pozostała niezmieniona.
- Flagi potwierdzono dokładnym porównaniem `--build-info`. DEDUP, SHARE oraz
  SIMPLIFY pozostają ON. R1/R2: DEFAULT = ON/ON, NO_R2_CANON = ON/OFF,
  NO_R1_FACTOR = OFF/ON, NO_R1_NO_R2 = OFF/OFF.
- Plany i dane: `test/research_gate/h9/rql` oraz `data/main`. W kopiach roboczych
  tylko `DECLARE ... FILE '*.txt'` zmieniono na aktualne `TEXTFILE`; źródła
  zamrożone zachowano. Skróty oryginalnych wejść są w [manifest.json](manifest.json).
- Każdy profil działał z tej samej ścieżki `work/xretractor`, pod tą samą nazwą,
  w świeżym `temp/`. Kopię binarium porównywano przez SHA-256 z celem builda.
  Jawna pusta konfiguracja, własny namespace oraz TMPDIR izolowały przebiegi.
- Bieżący pomiar: `--no-clock -r -k`, 6000 iteracji dla F9_R1/F9_X,
  3000 dla F9_R2. Odpowiednio 5999/2999 wierszy sondy. Jeden blok rozgrzewki
  i 20 sparowanych bloków, po 24 komórki, losowa kolejność z ziarnem
  `62320261116`. Łącznie 504 wykonania, z czego 480 w analizie.
- Z każdego przebiegu odrzucono pierwsze 10% slotów. Statystyka podstawowa
  jest medianą median bloków. Średnia oznacza medianę średnich bloków;
  p99 analogicznie medianę p99 bloków. Ilorazy i 95% CI liczy funkcja
  `paired_bootstrap_ratio` z H9: 10000 replikacji, zamrożone ziarno
  `20260809_2603`, wspólne indeksy bloków w liczniku i mianowniku.
- Callgrind: 12 osobnych wykonań, DEFAULT i NO_R1_FACTOR, wszystkie trzy
  rodziny przy Q=1,2. Zbieranie tylko wewnątrz `processRows()`,
  `--cache-sim=yes`, zdarzenia Ir/Dr/Dw oraz liczby wywołań. Czasu pod
  Valgrindem nie użyto jako pomiaru kosztu.

To lokalna diagnoza mechanizmu H9. Nie jest powtórzeniem kampanii RT na pi400
ani porównaniem wydajności całego silnika na korpusie UC01-UC08.

## Odtworzenie różnicy na bieżącym silniku

Iloraz DEFAULT / NO_R1_FACTOR; czas w us. Przy Q=1,2 wyłączenie R2 nie zmienia
żadnego z tych planów, więc dla F9_X NO_R1_FACTOR ma ten sam plan co NO_R1_NO_R2.

| Rodzina | Q | R1 ON | R1 OFF | Iloraz, 95% CI |
|---|---:|---:|---:|---|
| F9_R1 | 1 | 10,931 | 6,628 | 1,649 [1,636; 1,657] |
| F9_R1 | 2 | 17,248 | 12,860 | 1,341 [1,320; 1,349] |
| F9_X | 1 | 24,476 | 15,850 | 1,544 [1,532; 1,551] |
| F9_X | 2 | 35,242 | 26,555 | 1,327 [1,311; 1,336] |
| F9_R2 | 1 | 6,978 | 6,963 | 1,002 [0,995; 1,008] |
| F9_R2 | 2 | 17,508 | 17,468 | 1,002 [0,993; 1,011] |

Kontrole identycznych planów DEFAULT/NO_R2_CANON i
NO_R1_FACTOR/NO_R1_NO_R2 dały punktowe ilorazy median 0,993-1,005.
Zgodność listingów sprawdzono bajtowo, oddzielnie dla każdej rodziny i Q.
W F9_R2 zgodne są wszystkie cztery profile.

Pełne wyniki: [summary.tsv](summary.tsv),
[control-plans.json](control-plans.json), [slot-metrics.tsv](slot-metrics.tsv).

## Dlaczego mediana rośnie

W F9_R1 źródła mają okresy 1/100 i 1/50 s, a przeplot 1/150 s.
Unia taktów ma cztery fazy w okresie 1/50 s. Po rozruchu:

| Faza (`iter % 4`) | Chwila w okresie | Zapisane wyniki z R1 | Zapisane wyniki bez R1 |
|---|---|---|---|
| 0 | 1/150 s | substrat `A#B`, wynik publiczny | wynik publiczny |
| 1 | 1/100 s | brak | substrat `A>2` |
| 2 | 2/150 s | substrat `A#B`, wynik publiczny | wynik publiczny |
| 3 | 1/50 s | substrat `A#B`, wynik publiczny | substraty `A>2`, `B>1`, wynik publiczny |
| Cały okres | | 3 zapisy substratu + 3 publiczne | 3 zapisy substratów + 3 publiczne |

Przy Q=2 liczba zapisów publicznych podwaja się w obu profilach, natomiast
przeniesienie pracy substratów jest takie samo. F9_X ma dwie takie pary,
dlatego różnica median jest około dwukrotnie większa i prawie stała względem Q.

To tabela wynikająca z zapisanych planów i harmonogramu, zweryfikowana
rozkładem zmierzonych slotów. Źródła implementacyjne:
[TimeLine](../../retractordb/src/retractor/lib/CRSMath.cpp),
[maska i granice sondy](../../retractordb/src/retractor/lib/executorsm.cpp),
[wykonanie należnych węzłów i zapisów](../../retractordb/src/retractor/lib/dataModel.cpp).

Mediany faz F9_R1 Q=1, w us; mediana statystyki fazy z 20 bloków:

| Faza | Bieżący ON | Bieżący OFF | K26v3 ON | K26v3 OFF |
|---|---:|---:|---:|---:|
| 0 | 10,926 | 6,618 | 166,460 | 101,934 |
| 1 | 0,381 | 4,774 | 4,574 | 71,055 |
| 2 | 10,935 | 6,633 | 166,590 | 101,897 |
| 3 | 11,276 | 15,705 | 171,887 | 236,039 |

R1 dodaje pracę w dwóch fazach środkowych rozkładu, a odejmuje ją w fazie
źródła oraz w fazie wspólnej. Mediana pomija kosztowne skupienie pracy w fazie 3.
**Różnica median nie jest różnicą średniego kosztu ani dodatkowym czasem
obliczeń każdego slotu.**

## Kontrola bezpośrednio na surowym K26v3

Odczytano trzy oryginalne archiwa P8, bez ich modyfikacji: 480 komórek
Q=1,2, cztery profile i 20 bloków. Dla każdej komórki pełna mediana CSV
zgadza się z zamrożonym `matrix/timing.tsv` (480/480 asercji).
Archiwa i ich skróty: [historical-archives.json](historical-archives.json).

Poniżej analiza po jednakowym odrzuceniu pierwszych 10% slotów, zgodnie
z lokalną diagnozą; nie zastępuje zamrożonych statystyk kampanii.
Wartości w us, ON/OFF = DEFAULT/NO_R1_FACTOR.

| Rodzina | Q | Mediana ON/OFF | Średnia ON/OFF | p99 ON/OFF |
|---|---:|---|---|---|
| F9_R1 | 1 | 166,332 / 101,925 | 133,354 / 133,261 | 207,535 / 251,821 |
| F9_R1 | 2 | 260,923 / 200,905 | 205,491 / 208,988 | 303,644 / 352,950 |
| F9_X | 1 | 367,422 / 248,419 | 291,627 / 297,027 | 431,152 / 536,633 |
| F9_X | 2 | 521,272 / 401,551 | 407,315 / 411,353 | 599,332 / 694,288 |

Dla F9_R1 Q=1 iloraz średnich to 1,001 [0,984; 1,018], podczas gdy iloraz
median wynosi około 1,63. Dla czterech komórek ilorazy p99 ON/OFF to
0,824, 0,860, 0,803 i 0,863; wszystkie 95% CI są poniżej 1.
Zmniejszenie mediany przez wyłączenie R1 pogarsza zatem historyczne p99.

Na bieżącym hoście ilorazy średnich wyniosły 1,011, 0,993, 1,008 i 1,014;
wszystkie CI obejmują 1. Nie ustanawia to równoważności w granicy 2%:
średnie na WSL2 są bardziej podatne na odstające próbki. Nie widać jednak
dodatkowego kosztu całkowitego odpowiadającego wzrostowi mediany o 33-65%.

Dane: [phase-summary.tsv](phase-summary.tsv), [metric-ratios.tsv](metric-ratios.tsv).

## Profil pracy, materializacja i historia

Callgrind, F9_R1 Q=1, całość zebrana wewnątrz 5999 wywołań `processRows()`:

| Wielkość | R1 ON | R1 OFF |
|---|---:|---:|
| Instrukcje Ir `processRows`, z wywołaniami | 63 790 742 | 64 362 784 |
| Odczyty danych Dr | 18 292 174 | 18 405 797 |
| Zapisy danych Dw | 7 942 998 | 7 945 505 |
| Wywołania `storage::read` | 4 496 | 4 494 |
| Wywołania `memoryFile::read` | 4 496 | 4 494 |
| Wywołania kopiującego `payload::operator=` | 22 485 | 22 480 |
| Wywołania `storage::write` | 8 993 | 8 989 |
| Wywołania `memoryFile::write` | 4 497 | 4 495 |
| Wywołania `MetaIndexStore::overwriteLast` | 8 991 | 8 986 |

Różnice kilku rekordów odpowiadają różnym granicom rozruchu. R1 nie dodaje
tu nowej kategorii odczytu ani kopiowania. `STREAM_TIMEMOVE` i `STREAM_HASH`
korzystają z `fetchForward`; zapisany substrat w obu profilach jest czytany
przez `storage::revRead/read`, a źródło deklarowane przez bufor historii.
Sam zapis MEMORY jest częścią `storage::write` i obejmuje również obsługę
metadanych; nie wolno utożsamiać go wyłącznie z kopią bajtów rekordu.
Zobacz [storage.cc](../../retractordb/src/rdb/lib/storage.cc) i
[metaData.cc](../../retractordb/src/rdb/lib/metaData.cc).

W pozostałych komórkach F9_R1/F9_X całkowite Ir również maleje po włączeniu R1.
Dr/Dw są liczbami dostępów, nie objętością materializacji ani czasem wykonania.
Rozdział funkcji jest inkluzywny, więc wierszy tabeli nie należy sumować.
Pełny profil: [callgrind-functions.tsv](callgrind-functions.tsv).

Zapisano wszystkie liczniki WORK, MATERIALIZED oraz LOGICAL dla 24 komórek:
[runtime-counters.tsv](runtime-counters.tsv). Każdy z 504 przebiegów czasowych
ma dokładnie te same liczniki co odpowiadający mu przebieg bazowy.
Przykład F9_R1 Q=1: zapisy substratów ON/OFF = 4497/4495, publiczne =
4496/4494, wywołania ewaluatora = 8993/8989. Zmiana Q=1 na Q=2 nie zwiększa
liczby zapisów substratów w tej rodzinie.

Rzeczywiste listingi i tabele runtime są w `plans/`, a odczytane z nich
wymagania historii w [capacities.tsv](capacities.tsv). Dla F9_R1, obu Q:

- ON: A=4, B=4, `STREAM_HASH_A_B`=2.
- OFF: A=5, B=4, `STREAM_TIMEMOVE_2_A`=4, `STREAM_TIMEMOVE_1_B`=4.
- `Cap=0` przy publicznym wyniku oznacza brak żądanej historii przez
  konsumenta, nie zerową pojemność jego magazynu dyskowego.

F9_X zawiera dwie analogiczne pary i kolejne substraty; wszystkie są zapisane
w pliku TSV. Dla wyniku F9_R1 `origin=3` w obu profilach, `tail=0` z R1,
`tail=2` bez R1. Nie żądano identycznej długości plików po tym samym `-m`.

## Weryfikacja i granice

- Po sprawdzeniu konfiguracji builda, rzeczywistych poleceń CTest i kopii
  fixture'ów: `ctest --test-dir build/R593-DEFAULT --output-on-failure
  -R '^(ut_probe|ut_compiler|ut_dataModel)$'` - 6/6 wpisów CTest, w tym
  trzy setupy. 382 przypadki GTest przeszły; jeden został pominięty:
  `xschema.handleTable_stale_entry_is_caught`, ponieważ sprawdza asercję
  istniejącą tylko w Debug. Log: [baseline-ctest.log](baseline-ctest.log).
- 24 plany skompilowano i wykonano z licznikami; 504 pomiary oraz 12 profili
  zakończyło się kodem 0, bez błędów wykonania. Zachowano ostrzeżenia
  o nieograniczonym zapisie wyników dyskowych - jest to własność planów H9.
- Nie porównywano pełnego Val/NULL/metadanych wszystkich profili. Nie jest
  to dowód poprawności przyszłej zmiany optymalizatora.
- `ninja test`, `ninja test-valgrind`, `ninja test_gate`, floor all-off i
  wiązanie Pythona pominięto: nie zmieniono źródeł silnika, konfiguracji
  budowania ani niczego wykonywanego przez te zestawy. Są wymagane przy
  wdrożeniu, które obejmuje krok 6. UC01-UC08 pominięto: ten etap diagnozuje
  mechanizm `#` na H9, bez zmiany silnika i bez ogólnego werdyktu wydajności.
- Nie zmieniono dokumentacji zachowania, referencji H9 ani indeksu wiedzy.
  Nie wykonano commita, pushu, komentarza GitHub ani CI.
- Kontrola Layer A: 190 plików tekstowych, zero trafień; kod, konfiguracja
  i RQL w trybie ścisłym. Raport: [hygiene.txt](hygiene.txt).
  Wszystkie 2077 plików surowego archiwum odczytano ponownie i porównano
  przez SHA-256 z oryginałami przed przeniesieniem kopii do `work/raw/`.

## Odtworzenie i artefakty

[diagnose.py](diagnose.py) jest samodzielnym skryptem diagnostycznym.
Przygotowane buildy `R593-*` muszą odpowiadać konfiguracjom z `cache-*.txt`.
Manifest odmawia uznania profilu z innymi flagami lub zmieniającym się binarium.
Uruchomienia wymagają lokalnego IPC; nie należy prowadzić ich równolegle
z buildem, testami lub innym pomiarem silnika.

Nowy komplet w sąsiednim katalogu, z katalogu tego raportu:

```bash
python3 diagnose.py manifest --out ../results_20261116_issue623_step1_repeat
python3 diagnose.py plans --out ../results_20261116_issue623_step1_repeat
python3 diagnose.py timing --out ../results_20261116_issue623_step1_repeat
python3 diagnose.py profile --out ../results_20261116_issue623_step1_repeat
python3 diagnose.py summary --out ../results_20261116_issue623_step1_repeat
python3 diagnose.py analyze --out ../results_20261116_issue623_step1_repeat
```

`analyze` potrzebuje również trzech lokalnych archiwów K26v3 wskazanych
w `historical-archives.json`. Oryginały są otwierane tylko do odczytu.
Ponowny `timing` odmawia nadpisania istniejącej serii.

Surowe przebiegi i pełne profile zachowano w lokalnym `raw.tar.gz`, zgodnie
z polityką `.gitignore` repozytorium eksperymentów. Indeks plików i SHA-256
archiwum to `raw.index.tsv` oraz `raw.sha256`. Rozpakowane kopie pozostają
w ignorowanym `work/raw/`. Aby powtórzyć samą analizę w tym katalogu:

```bash
tar -xzf raw.tar.gz
python3 diagnose.py summary
python3 diagnose.py analyze
```

Indeks `evidence.sha256` obejmuje pliki oddawane do przeglądu. Surowego
archiwum nie należy zakładać jako obecnego w świeżym klonie repozytorium.
