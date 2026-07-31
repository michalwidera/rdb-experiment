# Badanie higieniczne: czy `e1e5181` unieważnił którykolwiek zapisany wynik

## Cel

`e1e5181` („Poprawka klienta po eksperymencie (#216)") naprawił defekt wykryty
przez zatrzymaną kampanię K6b: `xqry` kończył się przed silnikiem i meldował
przy tym sukces. Zmiany dotknęły sześciu plików — pięciu w `src/qry/` (klient)
i jednego w `src/common/` (`_kbhit`, kod wspólny dla wszystkich binarek).

Badanie odpowiada na jedno pytanie:

> Czy `e1e5181` zmienił zachowanie silnika albo klienta na jakiejkolwiek
> ścieżce, która przed nim kończyła się sukcesem?

## Dlaczego to badanie ma inny kształt niż dwa poprzednie

Poprzednie badania higieniczne (`results_20260729_hygiene`,
`results_20260730_hygiene`) porównywały **wyłącznie silnik**, bo tam siedziały
badane poprawki. Tutaj rozkład jest odwrotny:

| Obszar | Zmiana |
|---|---|
| `src/qry/` — klient | 5 plików, 164 linie |
| `src/common/uxSysTermTools.cpp` — `_kbhit` | 7 linii |
| `test/UnitTest/` | 3 pliki, 256 linii (nie wchodzi do żadnej binarki kampanii) |

Warstwa porównująca tylko silnik odpowiedziałaby więc na pytanie, którego nikt
nie zadaje, i przeszłaby w ciszy. Dlatego badanie ma **trzy** warstwy, z czego
trzecia — nowa — porównuje klienta.

## Warunek ważności

Korpus musi być identyczny po obu stronach porównania. Sprawdzane przez skrypt:
`git diff` między commitami nie może obejmować żadnego pliku `.rql` ani pliku
danych w `examples/`. Zmiany w `test/` są raportowane, ale nie unieważniają
badania — to badanie nie uruchamia `ctest`.

## Metoda

Dwa drzewa, budowane tym samym toolchainem i z **identycznymi** przełącznikami
optymalizatora, weryfikowanymi porównaniem `--build-info`; rozbieżność zatrzymuje
badanie. Oba z `RDB_BENCH_PROBE=ON`, bo kampanie pomiarowe budują właśnie tak
(`REQUIREMENTS.md` R6). Każde drzewo daje **dwie** binarki: `xretractor` i `xqry`.

| Drzewo | Commit | Źródło |
|---|---|---|
| `HISTORICAL` | `bb3a521` | klon repozytorium kodu (repozytorium źródłowe nietknięte, R2) |
| `FIXED` | `e1e5181` | repozytorium kodu, katalog `build/HYG3-FIXED` |

Kontrola pozytywna: skrypt przerywa, jeżeli drzewo historyczne stoi na commicie
docelowym — inaczej badanie porównywałoby silnik sam ze sobą i przechodziło
zawsze.

### Warstwa 1 — korpus planów (`corpus_diff.py`)

Wszystkie pliki RQL z `test/IntegrationTest_serial`,
`test/IntegrationTest_parallel` i `examples` kompilowane compile-only przez oba
silniki, każdy w osobnym katalogu roboczym w `/dev/shm`. Porównywane: zrzut
planu po normalizacji, kod zakończenia i liczniki `REWRITE_APPLIED`.

### Warstwa 2 — artefakty wykonania (`artifact_diff.py`)

Cztery potoki uruchamiane realnie, ze wszystkimi artefaktami porównywanymi
bajtowo. Każdy potok dostaje **trzeci** przebieg (`HISTORICAL` po raz drugi) —
kontrola determinizmu: potok, którego dwa przebiegi tym samym silnikiem się
różnią, nie może służyć za wyrocznię i jest wyłączany z kryterium.

Dla tego commitu warstwa 2 ma konkretny sens, mimo że silnik zmienił się
w jednym miejscu. `_kbhit` jest wołane **raz na obrót pętli** przez każdą
binarkę, więc leży na ścieżce, którą K6 mierzy. Zmiana dodaje tam wywołanie
`isatty(STDIN_FILENO)`.

### Warstwa 3 — klient (`client_diff.py`), nowa

Silnik trzymany **stały** (binarka `FIXED`), żeby każda różnica była
przypisywalna klientowi. Równoważność samego silnika rozstrzygają warstwy 1 i 2.

Porównywane są dwie klasy poleceń:

1. **Deterministyczne z definicji** — `-l`, `-d`, `-y`, `-t <strumień>`. Ich
   wyjście jest funkcją skompilowanego planu, nie chwili podłączenia. Wśród nich
   `-t` ma tu własny, konkretny powód: kalibracja K6c czyta z niego pole `delta`,
   więc zmiana formatu tego wyjścia zepsułaby całą kampanię, nie dając ani
   jednego komunikatu.
2. **Zależne od chwili podłączenia** — `-s <strumień> -m 20`. Rozstrzyga
   kontrola determinizmu: `HISTORICAL` biegnie dwa razy i jeżeli sam ze sobą się
   nie zgadza, polecenie jest **wyłączane z kryterium** i raportowane, zamiast
   udawać wynik.

#### Dlaczego sześć poleceń wypadło z kryterium

Wyłączenie bez podanej przyczyny jest tylko przyznaniem się do niewiedzy.
Przyczyny są tu znane i sprawdzone w surowych danych:

| Polecenie | Przyczyna |
|---|---|
| `-s bp_acc`, `-s bp_out`, `-s bp_win` (`rec205`) | wartości zależą od chwili podłączenia — dwa przebiegi tego samego klienta dają `456, 456, 455` i `459, 458, 457` |
| `-d`, `-y` (`rec205`) | ostatnia kolumna tabeli to **licznik wierszy**, który rośnie w trakcie pracy silnika (`1`, `181`, `26` …) |
| `-y` (`optimizer_ablation`) | jak wyżej |

W `optimizer_ablation` polecenie `-d` przeszło do kryterium, bo tamten potok
zdążył ustabilizować liczniki przed sondą. To nie jest niekonsekwencja
instrumentu, tylko własność potoków: kontrola determinizmu rozstrzyga
per polecenie i per potok, a nie z góry.

Wyłączenia nie osłabiają odpowiedzi na pytanie, dla którego ta warstwa powstała.
`-t` — jedyne polecenie, od którego zależy kalibracja K6c — zostało porównane
**70 razy** i za każdym razem wyszło identycznie.

Dwa potoki: `optimizer_ablation` (obie reguły przepisywania) i `rec205-qrs`
(potok umotywowany zewnętrznie — ten sam, który mierzy rodzina W8).

#### Pierwszy przebieg warstwy 3 był nieważny — instrument, nie wynik

Zapisane, bo bez tego liczby w `summary.md` byłyby nieporównywalne z pierwszym
przebiegiem, a ten jest w historii repozytorium.

Pierwsza wersja `client_diff.py` wyciągała nazwy strumieni z `xqry -d` przez
podział po białych znakach. Tabela `-d` jest jednak rozdzielana pionowymi
kreskami, a nazwa wyrównana do prawej — dla wiersza
`|                    FA|1/10|…|` pierwszym tokenem jest `|`. Warstwa porównała
przez to **66 razy polecenie `-t |`**, czyli 66 razy to samo nic, i zaraportowała
66 zgodności. Jest to dokładnie ten tryb porażki, przed którym ma bronić reguła
zliczania z K5h/K5i: instrument nie milczał, tylko liczył głośno puste
porównania.

Drugą wadą było traktowanie ścieżek porażki. Predeklaracja mówi „odstępstwem
jest przejście z zera na niezero: polecenie, które działało, przestało działać",
ale kod zawężał tę zasadę do samego **kodu wyjścia** i zgłaszał jako wpływ
zamierzony komunikat diagnostyczny dodany przez poprawkę na ścieżce, która już
przedtem zawodziła. To nie jest zmiana reguły po zobaczeniu danych — to
uzgodnienie kodu z regułą już zadeklarowaną; sekcja niżej precyzuje ją tak, żeby
rozbieżność nie mogła wrócić.

Trzecia rzecz nie była wadą, tylko brakującym ustaleniem: kolejność wierszy
w `-d` i `-y` różni się między przebiegami **tego samego** klienta. Nie jest
częścią kontraktu, więc porównywany jest zbiór wierszy, nie ich kolejność —
inaczej oba polecenia wypadają z kryterium i warstwa milczy o tym, o co pytamy.

Wyniki pierwszego przebiegu warstwy 3 są **odrzucone w całości**. Warstwy 1 i 2
nie były dotknięte żadną z tych wad, ale badanie powtórzono w komplecie, żeby
`summary.md` opisywał jeden spójny przebieg.

#### Kody wyjścia i komunikaty mają osobne traktowanie

Treścią poprawki jest właśnie to, że tryby porażki przestały być
nierozróżnialne: `streamNotFound` → 2, `serverNoResponse` → 110,
`clientQueueMissing` → 60, `noData` → 61, każdy z własnym komunikatem. Podział
przebiega więc po tym, **co polecenie robiło przed poprawką**:

| Stan przed poprawką | Co porównujemy | Różnica znaczy |
|---|---|---|
| `rc = 0` — polecenie działało | wyjście **i** kod, ściśle | **odstępstwo** |
| `rc ≠ 0` — polecenie już zawodziło | kod i komunikat, raportowane osobno | **treść poprawki** |

Odstępstwem jest wyłącznie przejście **z zera na niezero**: polecenie, które
działało, przestało działać. Bez tego podziału badanie musiałoby albo uznać
zamierzoną zmianę za wpływ, albo przemilczeć wszystkie zmiany na ścieżkach
porażki — obie odpowiedzi byłyby fałszywe.

## Kryterium

Wynik **„brak wpływu"** wtedy i tylko wtedy, gdy łącznie:

1. zero różnic w zrzutach planu na całym korpusie;
2. zero regresji kodu zakończenia kompilacji (zmiana porażka → sukces nie jest
   odstępstwem; zmiana w drugą stronę jest);
3. zero różnic w licznikach `r1` / `r2`;
4. wszystkie deterministyczne potoki dają bajtowo identyczne artefakty, przy
   niezerowej liczbie porównanych artefaktów w każdym;
5. każde rozstrzygalne polecenie klienta, które **przed poprawką kończyło się
   zerem**, daje identyczne wyjście i identyczny kod, przy **niezerowej** liczbie
   porównanych poleceń; zmiany na ścieżkach, które już zawodziły, są raportowane
   osobno i nie wchodzą do kryterium.

Każde odstępstwo jest raportowane imiennie i wskazuje, który zapisany wynik
wymaga ponownego rozpatrzenia.

## Czego badanie nie mierzy

Żadnej wielkości czasowej. W szczególności **nie mierzy narzutu** wywołania
`isatty` w `_kbhit` — to jest pytanie do K6 i wymaga workera pod R7. Tutaj
sprawdzana jest wyłącznie równoważność zachowania.

Nie mierzy też tego, czy poprawka **działa**: że działa, wykazano dziesięcioma
regresjami w `test/UnitTest/`, o których pokazano, że czerwienią się po
cofnięciu naprawy. Badanie higieniczne pyta o coś przeciwnego — czy naprawa
zepsuła coś, co działało.

## Higiena artefaktów (R14)

`results/raw` jest pakowany do deterministycznego archiwum z indeksem `SHA-256`
przez pułapkę `EXIT`, **również gdy badanie zawiedzie**. Artefakty imiennie
wskazane w werdykcie negatywnym są wcześniej kopiowane do `results/evidence/`;
lista jest zapisywana w `results/evidence_list.txt` także wtedy, gdy jest pusta.

Katalog roboczy z klonem drzewa historycznego leży **poza** katalogiem wyników,
w `<repo_kodu>/build/HYG3-trees` (nadpisywalne przez `HYG3_TREES`). Katalog
roboczy jest buildem, nie wynikiem.

## Znaczenie dla K6c

K6c jest przypięta do `e1e5181`. Predeklaracja v3 stwierdza, że ścieżka
pomiarowa silnika jest nietknięta, bo kampania uruchamia go z `-k`
(`noanykey`), więc `_kbhit` zwraca `false` w pierwszej linii. To badanie
sprawdza tę tezę **pomiarem, nie rozumowaniem** — a przy okazji odpowiada na
pytanie, którego samo rozumowanie nie obejmowało: czy klient, którego kampania
używa do odczytu interwałów strumieni, zachowuje się tak samo.
