# Badanie higieniczne: czy `bb3a521` unieważnił którykolwiek zapisany wynik

## Cel

`bb3a521` („Scalenie modyfikacji sond testowych") dodał trzy instrumenty
wymagane przez K6 — pomiar czasu kompilacji, liczniki materializacji i raport
pojemności buforów. Zmiany dotknęły **kodu wspólnego dla wszystkich profili
ablacyjnych i wszystkich zapytań**: `compiler.cpp` (`compile()`) oraz
`storage.cc` (`storage::write`). Wyniki K4, K18, K19 i K5 są zapisane na
wcześniejszych rewizjach.

Badanie odpowiada na jedno pytanie:

> Czy `bb3a521` zmienił zachowanie silnika dla jakiegokolwiek planu, który
> kompilował się i wykonywał przed nim?

Oczekiwana odpowiedź brzmi „nie" — cała nowa instrumentacja siedzi za
`#ifdef RDB_BENCH_PROBE`, a w budowie produkcyjnej znika bez śladu. **To jest
jednak hipoteza, nie fakt**: `storage::write` to ścieżka gorąca wykonywana raz
na rekord, a zmiana w niej dotyczy każdego strumienia w każdym planie.

## Dlaczego nie wystarcza rozumowanie „to jest za `#ifdef`"

Trzy powody, dla których ten argument jest słabszy, niż wygląda:

1. Kampanie pomiarowe **budują z `RDB_BENCH_PROBE=ON`** (`REQUIREMENTS.md` R6),
   więc dla nich nowy kod nie jest wyłączony — jest właśnie tym, co działa.
   Porównanie musi obejmować konfigurację z sondą, nie tylko produkcyjną.
2. `isMemoryBackedStorage()` jest wywoływane przy **każdym** zapisie rekordu.
   Nawet jeśli nie zmienia wyniku, wchodzi w ścieżkę, którą K6 będzie mierzyć.
3. Poprzednie badanie higieniczne pokazało, że rozumowanie autora poprawki
   bywa poprawne, a jego instrument nie: dwa potoki porównywały wtedy pusty
   zbiór i przechodziły w milczeniu.

## Warunek ważności

Korpus musi być identyczny po obu stronach porównania. Sprawdzane przez skrypt:
`git diff` między commitami nie może obejmować żadnego pliku `.rql` ani pliku
danych. Jeżeli obejmuje — różnica przestaje być różnicą kodu silnika i badanie
traci sens.

## Metoda

Dwa drzewa silnika, budowane tym samym toolchainem i z **identycznymi**
przełącznikami optymalizatora, weryfikowanymi porównaniem `--build-info`;
rozbieżność zatrzymuje badanie, bo porównywałoby wtedy profile, a nie skutek
scalenia. Oba z `RDB_BENCH_PROBE=ON` — patrz punkt 1 powyżej.

| Drzewo | Commit | Źródło |
|---|---|---|
| `HISTORICAL` | `2a5aa86` | klon repozytorium kodu (repozytorium źródłowe nietknięte, R2) |
| `FIXED` | `bb3a521` | repozytorium kodu, katalog `build/HYG2-FIXED` |

Kontrola pozytywna: skrypt przerywa, jeżeli drzewo historyczne stoi na commicie
docelowym — inaczej badanie porównywałoby silnik sam ze sobą i przechodziło
zawsze.

### Warstwa 1 — korpus planów (`corpus_diff.py`)

Wszystkie pliki RQL z `test/IntegrationTest_serial`,
`test/IntegrationTest_parallel` i `examples` kompilowane compile-only przez oba
silniki, każdy w osobnym katalogu roboczym w `/dev/shm`. Porównywane: zrzut
planu po normalizacji, kod zakończenia i liczniki `REWRITE_APPLIED`.

Normalizacja zastępuje ścieżkę katalogu roboczego znacznikiem `<WORK>` **przed**
policzeniem hasha — bez tego hash jest nieodtwarzalny między przebiegami.

### Warstwa 2 — artefakty wykonania (`artifact_diff.py`)

Cztery potoki uruchamiane realnie, ze wszystkimi artefaktami porównywanymi
bajtowo. Każdy potok dostaje **trzeci** przebieg (`HISTORICAL` po raz drugi) —
to kontrola determinizmu: potok, którego dwa przebiegi tym samym silnikiem się
różnią, nie może służyć za wyrocznię i jest wyłączany z kryterium.

| Potok | Cykli | Co pokrywa |
|---|---|---|
| `examples/ecg/rec205/rec205-qrs.rql` | 4000 | pełny Pan-Tompkins: okna, agregaty, polityka `MEMORY` |
| `test/IntegrationTest_parallel/dsp/query.rql` | 400 | splot FIR; **niedeterministyczny** (`/dev/urandom`), wyłączany |
| `test/IntegrationTest_serial/optimizer_ablation/query.rql` | 200 | wszystkie ścieżki obu reguł |
| `test/IntegrationTest_serial/agse_volatile/query.rql` | 200 | `AGSE` nad źródłem obliczanym, polityka `MEMORY` |

Dwa z tych potoków (`rec205-qrs`, `agse_volatile`) nie mają dyrektywy
`STORAGE`, więc piszą do katalogu roboczego. Artefakt jest dlatego definiowany
**różnicowo** — snapshot hashy przed przebiegiem, zbieranie plików nowych
i zmienionych — a puste porównanie jest **porażką**, nie zgodnością.

## Kryterium

Wynik **„brak wpływu"** wtedy i tylko wtedy, gdy łącznie:

1. zero różnic w zrzutach planu na całym korpusie;
2. zero regresji kodu zakończenia kompilacji (zmiana porażka → sukces nie jest
   odstępstwem; zmiana w drugą stronę jest);
3. zero różnic w licznikach `r1` / `r2`;
4. wszystkie deterministyczne potoki dają bajtowo identyczne artefakty, przy
   niezerowej liczbie porównanych artefaktów w każdym.

Każde odstępstwo jest raportowane imiennie i wskazuje, który zapisany wynik
wymaga ponownego rozpatrzenia.

## Czego badanie nie mierzy

Żadnej wielkości czasowej. **W szczególności nie mierzy narzutu nowej
instrumentacji** — to jest pytanie do K6 i wymaga workera pod R7. Tutaj
sprawdzana jest wyłącznie równoważność zachowania.

## Higiena artefaktów (R14)

`results/raw` jest pakowany do deterministycznego archiwum z indeksem `SHA-256`
przez pułapkę `EXIT`, **również gdy badanie zawiedzie**. Artefakty imiennie
wskazane w werdykcie negatywnym są wcześniej kopiowane do `results/evidence/`;
lista jest zapisywana w `results/evidence_list.txt` także wtedy, gdy jest pusta.
