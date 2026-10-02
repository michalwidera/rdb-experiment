# G3b - poprawiony most oracle'a shift-matching do silnika (2026-10-02)

Poprawka aparatury mostu K2/G3 po korekcie ogona `>N` w silniku (`fcc5a444`, krok 3d z 2026-08-07). Rozstrzygnięcie i dowody: [retractordb #353](https://github.com/michalwidera/retractordb/issues/353), werdykt H1.

## Po co

Zamrożony most `results_20260726_G3/engine_check.py` (13 kontroli tożsamości silnika cytowanych w pakiecie artefaktów) daje 0/13 na każdym silniku od `fcc5a444`, w tym na pinie artykułu `40c28dbe`. Wartości wszystkich trzech wyjść są przy tym zgodne z oracle'em. Przyczyny leżą w aparaturze:

1. **Parser.** `plan_tail` czyta z wydruku planu samo `tail=`. Od `5f310515` (#228) plan drukuje osobno `origin=` i `tail=`, a brak pola oznacza 0.
2. **Oczekiwanie.** Oracle G3 zakłada, że trzy formy (`optimized`, `blocked`, `explicit_rhs`) mają ten sam ogon `interleave_tail + L`, czyli że przesunięcie przenosi ogon producenta. To reguła `W = W_src` sprzed `fcc5a444`. Od tej poprawki obowiązuje `W = max(0, W_src - N)`, a nad źródłami deklarowanymi forma sfaktoryzowana `(A#B)>L` ma ogon krótszy dokładnie o `min(W_hash, L) >= 1` od formy zablokowanej `(A>i)#(B>k)`.

Drugą przyczynę rozstrzyga twierdzenie `causal_shift_matching_declared` (`retractordb/math_proofs/Profs/InterleaveTailExact.lean`), w artykule wniosek `cor:shift-tail-gap` (`paper-arXiv/debs/main-debs.tex`).

## Co się zmieniło wobec G3

`engine_check.py` w tym katalogu **nie kopiuje** mostu, tylko importuje z `results_20260726_G3` funkcję `run_case` i wszystko, czego ona używa (szablon planu, źródła, dekodowanie, porównanie z oracle'em `reference.py`). Katalogu kampanii nie wolno zmieniać, więc import jest przypięty tak samo jak kopia, a przebieg silnika i porównanie wartości są identyczne z G3. Zmieniona jest tylko ocena przypadku:

- cisza wyjścia = `origin + tail` z wydruku planu;
- oczekiwana cisza każdej formy pochodzi z modelu zdarzeniowego K24 w konwencji C1 (`results_20260912_K24f/apparatus/oracle`): `blocked` ma kształt lewej strony, `explicit_rhs` prawej, a `optimized` prawej, gdy R1 przepisał plan;
- model K24 jest sprawdzany wobec twierdzenia: równy `origin`, `lhs.tail = W_hash >= 1`, `rhs.tail = max(0, W_hash - L)`. Sprzeczność kończy przebieg kodem 2 jako błąd aparatury;
- dodatkowo `rekordy + cisza` muszą być wspólne trzem wyjściom (ten sam interwał i ten sam przebieg);
- pozostałe warunki statusu G3 bez zmian: wartości i mapa `NULL` wobec oracle'a, `records == meta_records`, pusty ślad luk, schemat, interwał, zadziałanie R1, kształt `blocked`, niepusta dziedzina `NULL`.

Wynik zamrożonej oceny zostaje w JSON jako `frozen_status`.

## Uruchomienie

```bash
./run.sh <xretractor> <pełne SHA silnika>
```

Wynik: `results/engine-<8 znaków SHA>.json` i odświeżony `results/summary.md`. Binarka nie zna własnego SHA (napis `Branch:` w `--help` powstaje przy konfiguracji CMake), więc przypięcie podaje się jawnie. Katalog roboczy jest tymczasowy i znika po przebiegu.

## Wyniki

Przebiegi z 2026-10-02, binarki Release z przełącznikami produkcyjnymi (R1 włączony). Szczegóły przypadków: [`results/summary.md`](results/summary.md).

| silnik | rola | poprawiony most | zamrożona ocena G3 |
|---|---|---|---|
| `40c28dbefec8324df45365d863050fc577623768` | pin silnika artykułu (`rdb-artifact/MANIFEST.md`), binarka z `trend.py` | **13/13** | 0/13 |
| `1695ed8d1f3727c5393d9920c5059c3eaba0645f` | `origin/master` w chwili poprawki (`build/Release`) | **13/13** | 0/13 |
| `db4a3604bd31ad06e7cc89e95739f7f7e87597d6` | `fcc5a444^`, kontrola dodatnia: ostatni silnik z regułą `W = W_src` | **0/13**, wyłącznie `cisza` | 0/13 |

- Na obu silnikach po `fcc5a444` cisza `blocked` wynosi `L + W_hash`, a `optimized` i `explicit_rhs` wynoszą `L + max(0, W_hash - L) = L`. Liczba rekordów obu form sfaktoryzowanych jest większa dokładnie o `W_hash` (np. `p2_equal` 87/86/87). Rozbieżności wartości: 0 we wszystkich wyjściach.
- Na `fcc5a444^` wszystkie trzy formy mają ciszę `L + W_hash`, a liczby rekordów są równe zapisanym w lipcowym `results_20260726_G3/results/engine.json` (np. 86/86/86). Poprawiony most odrzuca ten silnik wyłącznie za ciszę form sfaktoryzowanych, a wartości są zgodne.
- Zamrożona ocena daje 0/13 także na `fcc5a444^`, bo ten silnik jest już po `5f310515` i drukuje `origin=` osobno. Sam parser wystarcza więc, żeby zamrożony most nie przeszedł na żadnym silniku od `5f310515`.
- JSON-y zapisują stan `rdb-experiment` z chwili przebiegu, gdy ten katalog nie był jeszcze zacommitowany (`dirty: true`).

## Granice

- Most sprawdza 13 przypadków G3 na źródłach plikowych, z zegarem (bez `-f`). To, że krótsza cisza nie oznacza emisji przed dostępnością wejść w środowisku wykonawczym, rozstrzyga sonda z kontrolą dodatnią opisana w #353, nie ten katalog.
- Ogon przeplotu powyżej progu przeglądu fazowego (`kHashPhaseScanLimit = 100000`, ograniczenie awaryjne) nie występuje w tych przypadkach (największy okres: 307); w Lean nie jest formalizowany.
- Pin `rdb-experiment` w `rdb-artifact` (`d319e88`) nie obejmuje tego katalogu. Przesunięcie pinu wymaga ponownego wskazania luster recenzenckich i jest osobną decyzją.
