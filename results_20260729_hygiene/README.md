# Badanie higieniczne: czy `Fix (#214)` unieważnił którykolwiek zapisany wynik

## Cel

`Fix (#214)` naprawił `compiler::resolveStreamIntervals` — kod **wspólny dla
wszystkich profili ablacyjnych i wszystkich zapytań**. Wyniki K4, K18 i K19 są
zapisane na wcześniejszych rewizjach silnika. Twierdzenie „żaden zapisany wynik
nie został unieważniony" musi mieć pokrycie w danych, a nie w rozumowaniu
autora poprawki.

Badanie odpowiada na jedno pytanie:

> Czy poprawka zmieniła zachowanie silnika dla **jakiegokolwiek** planu, który
> kompilował się przed nią?

Oczekiwana odpowiedź brzmi „nie" — poprawka miała zamieniać porażki w sukcesy,
a nie zmieniać wyniki. Badanie ma szansę tę odpowiedź obalić; jeżeli tego nie
zrobi, jest to wynik, a nie formalność.

## Dlaczego mimo przesłanek

Przesłanka istnieje i jest mocna: obie kampanie K5 kompilowały te same
workloady tymi samymi pięcioma profilami, różniąc się wyłącznie commitem
silnika, i dały **170/170 identycznych zrzutów planu**. Obejmuje to rodzinę W8,
czyli pełny potok Pan-Tompkins — a więc `STREAM_AGSE`, programy
jednoelementowe i agregaty, dokładnie te ścieżki, które poprawka zmienia.

Przesłanka nie wystarcza z dwóch powodów:

1. Korpus zawiera konstrukcje, których rodziny K5 nie dotykają — `DEHASH`,
   `SUBTRACT`, dzielenie modulo, tablice, źródła wieloargumentowe. Idą one
   innymi gałęziami `switch`, ale **dzielą zmieniony warunek zakończenia**
   pętli rozwiązywania interwałów.
2. Zgodność zrzutu planu nie jest zgodnością zachowania. Poprawka dotyczy
   interwałów, a te karmią `computeStartupLatency` i
   `computeRequiredCapacities`, czyli pojemności buforów w czasie wykonania.

## Warunek ważności

Korpus musi być identyczny po obu stronach porównania. Sprawdzone:
`git diff 0e0f701 2a5aa86` obejmuje wyłącznie `src/retractor/lib/compiler.cpp`
i `test/UnitTest/test_compiler.cpp`. **Żaden plik `.rql` ani plik danych nie
zmienił się**, więc różnica między drzewami to wyłącznie kod silnika.

## Metoda

Dwa drzewa silnika, budowane tym samym toolchainem i z **identycznymi**
przełącznikami optymalizatora (weryfikowane porównaniem `--build-info`;
rozbieżność zatrzymuje badanie, bo porównywałoby wtedy profile, a nie skutek
poprawki):

| Drzewo | Commit | Źródło |
|---|---|---|
| `HISTORICAL` | `0e0f701` | klon repozytorium kodu (repozytorium źródłowe nietknięte, R2) |
| `FIXED` | `2a5aa86` | repozytorium kodu, katalog `build/HYG-FIXED` |

Kontrola pozytywna: skrypt przerywa, jeżeli drzewo historyczne stoi na commicie
z poprawką — inaczej badanie porównywałoby silnik sam ze sobą i przeszłoby
zawsze.

### Warstwa 1 — korpus planów (`corpus_diff.py`)

Wszystkie **81 plików RQL** z `test/IntegrationTest_serial`,
`test/IntegrationTest_parallel` i `examples` kompilowane compile-only
(`xretractor <plik> -c`) przez oba silniki, każdy w osobnym katalogu roboczym
w `/dev/shm`. Porównywane:

- **zrzut planu** po normalizacji, co do bajtu;
- **kod zakończenia** kompilacji;
- **liczniki `REWRITE_APPLIED r1 / r2`**.

Ostatni punkt weryfikuje wprost liczby zapisane w K4: jeżeli liczniki są
identyczne po obu stronach, atrybucja reguł z K4 obowiązuje nadal.

**Normalizacja** zastępuje ścieżkę katalogu roboczego stałym znacznikiem
`<WORK>` **przed** policzeniem hasha. Zamyka to dług odnotowany w `JOURNAL.md`
przy K4: `results_20260728_K4/collect.py` hashował surowe wyjście zawierające
ścieżkę bezwzględną katalogu tymczasowego, przez co hash był nieodtwarzalny
między przebiegami.

### Warstwa 2 — artefakty wykonania (`artifact_diff.py`)

Cztery potoki uruchamiane realnie (`-r -k -m N`) pod oboma silnikami, ze
wszystkimi artefaktami porównywanymi bajtowo:

| Potok | Cykli | Co pokrywa |
|---|---|---|
| `examples/ecg/rec205/rec205-qrs.rql` | 4000 | pełny Pan-Tompkins: okna, agregaty, polityka `MEMORY` |
| `test/IntegrationTest_parallel/dsp/query.rql` | 400 | splot FIR, `STREAM_ADD` |
| `test/IntegrationTest_serial/optimizer_ablation/query.rql` | 200 | wszystkie ścieżki obu reguł |
| `test/IntegrationTest_serial/agse_volatile/query.rql` | 200 | `AGSE` nad źródłem obliczanym, polityka `MEMORY` |

Nagłówek `.meta` (8 bajtów) jest wyłączony z porównania — zawiera znacznik
czasu utworzenia, więc różniłby się w każdym przebiegu z definicji.

## Kryterium

Badanie kończy się wynikiem **„brak wpływu"** wtedy i tylko wtedy, gdy łącznie:

1. zero różnic w zrzutach planu na całym korpusie;
2. zero zmian kodu zakończenia kompilacji;
3. zero różnic w licznikach `r1` / `r2`;
4. wszystkie cztery potoki dają bajtowo identyczne artefakty.

Każde odstępstwo jest raportowane imiennie i pociąga za sobą wskazanie, który
zapisany wynik wymaga ponownego rozpatrzenia.

**Zmiana statusu z porażki na sukces nie jest odstępstwem** — jest treścią
poprawki. Byłaby nim natomiast zmiana w drugą stronę albo zmiana planu przy
niezmienionym statusie.

## Czego badanie nie mierzy

Żadnej wielkości czasowej. Nie zastępuje K6 ani powtórki kampanii czasowych
K18. Odpowiada wyłącznie na pytanie o równoważność zachowania między dwiema
rewizjami silnika.
