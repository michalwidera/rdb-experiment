# Kampania G1/K1 — obserwowalność planu i status prefiksu

**Data:** 2026-07-26 · **Rodzina:** eksperyment semantyczny (bez pomiaru czasu,
bez workera — jak `results_20260725`, patrz `REQUIREMENTS.md`, zakres).

## Cel

Dostarczyć dane rozstrzygające lukę **G1** planu badawczego
(`paper-arXiv/debs/research_plan.md`, §4 i krok **K1**):

> „Relacja obserwowalnej równoważności planów nie jest zdefiniowana; status
> zerowego prefiksu początku strumienia jest nierozstrzygnięty.”

Trzy pytania K1:

1. **D1** — co dokładnie jest obserwowalne i jaki status ma zerowy prefiks;
2. **D2** — **która strona tożsamości R1 jest w implementacji stroną
   odniesienia**;
3. **D3** — czy nazwy pól są obserwowalne (dowieść nieobserwowalności albo
   rozszerzyć porównanie w deduplikacji).

Kampania **nie** weryfikuje poprawności bezwzględnej względem oracle'a — to
zakres K2. Porównuje **pary planów** o tej samej denotacji matematycznej.

## Metoda

`probe.py` uruchamia rodzinę zapytań różniących się wyłącznie kształtem planu
i zbiera dla każdego pełny obserwowalny artefakt strumienia `probe`:

| warstwa | źródło | jak odczytana |
|---|---|---|
| sekwencja wartości | plik binarny | dekodowanie int32 LE |
| status `null` per rekord | plik `.meta` | dekodowanie wpisów RLE `IndexRecord` |
| schemat i nazwy pól | plik `.desc` | tekst |
| kształt planu | `xretractor -c` | tekst |

Kodowanie źródła w wartościach: `A[k] = k+1`, `B[j] = 1000000+j`, więc każdy
rekord wyniku jednoznacznie wskazuje źródło i indeks rekordu źródłowego.

**Kontrole (reguła R-a, §4 planu).** Para `shift_declared` ↔
`shift_declared_copy` (ten sam plan dwa razy) i para `add_declared` ↔
`add_computed` muszą wyjść zgodne w warstwie wartości i mapy `null`. Jeżeli
rozejdą się także one, sonda mierzy artefakt środowiska i wynik jest nieważny —
`probe.py` kończy się wtedy kodem 1.

### Przypadki

Wymiar badany to **klasa wejścia operatora**: źródło *deklarowane*
(`DECLARE … FILE`) kontra strumień *obliczany* (wynik `SELECT`).

- `shift_declared` / `shift_computed` — operator `>N` nad każdą z klas;
- `hash_declared` / `hash_computed` — operator `#` nad każdą z klas;
- `add_declared` / `add_computed` — operator `+` nad każdą z klas (kontrola);
- tożsamość R1 `phi(tau_i A, tau_k B) = tau_{i+k} phi(A,B)` w trzech
  wariantach: `r1_lhs_auto` (lewa strona, przebieg faktoryzacji ją przepisuje),
  `r1_lhs_blocked` (lewa strona z przesunięciami jako strumieniami użytkownika —
  przebieg wymaga substratów, więc **się nie odpala**; to jest wykonanie planu
  nieprzepisanego bez konieczności przebudowy binarki), `r1_rhs` (prawa strona
  zapisana wprost w RQL).

## Uruchomienie

```bash
./run.sh                      # sonda na bieżącej binarce (domyślnie Debug)
./build_profiles.sh           # pełna macierz OFF / STRUCT / ALGSTRUCT (wymaga Release)
```

Wyniki: `results/probe*.json` (surowe), `results/summary.md` (tabele).

## Stan wykonania

- [x] Sonda w konfiguracji **domyślnej** (wszystkie `RDB_OPT_*` = ON),
      `build/Debug`, gałąź `master` @ `a50284f`. Wynik:
      `results/probe-before-W1.json` — stan **przed** naprawą defektu
      kolejności planu (W1).
- [x] Powtórzenie po naprawie W1 (bezwarunkowy `topologicalSort()` na końcu
      `compiler::compile()`): `results/probe.json`, `results/summary.md`.
      Para `hash_computed ↔ hash_computed_sorted` z rozbieżnej stała się
      zgodna — semantyka planu przestała zależeć od odpalenia niezwiązanej
      optymalizacji. Residuum 12/35 rekordów all-null to gałąź drugiego
      argumentu `#` (defekt W2, otwarty).
- [ ] Macierz profili `OFF` / `STRUCT` / `ALGSTRUCT` — skrypt gotowy
      (`build_profiles.sh`), wymaga trzech przebudów Release. Sprawdza, czy
      rozbieżności odtwarzają się także tam, gdzie ujawnia je
      `it_optimizer_ablation` (etykiety `factor_runtime_semantic_divergence`,
      `dedup_startup_prefix_divergence`).
- [ ] Rozszerzenie o `dedup_startup_prefix_divergence` — obecna sonda pokrywa
      oś faktoryzacji; oś deduplikacji wymaga przypadku z `(DA+DB)>1`
      i profilu z wyłączonymi jednocześnie dedup, faktoryzacją i
      współdzieleniem `SELECT`.

## Wynik — konfiguracja domyślna

Pełne tabele: `results/summary.md`. Trzy ustalenia:

1. **`>N` nad źródłem deklarowanym jest operacją pustą.** `A>3` daje
   `1,2,3,…` — bez przesunięcia i bez prefiksu. To samo `>3` nad strumieniem
   obliczanym daje `0,0,0,1,2,3,…`. Mechanizm: `dataModel::getPayload()` wywołuje
   `revRead(offset)` wyłącznie dla `!isDeclared()`.
2. **`#` nad strumieniami obliczanymi degeneruje.** `A#B` (deklarowane) daje
   poprawny przeplot; ten sam przeplot nad dwoma strumieniami obliczanymi daje
   23 z 35 rekordów **all-null**. Kontrola `+` przechodzi w obu klasach, więc
   nie jest to artefakt konstrukcji sondy. Mechanizm: `dataModel::fetchForward()`
   liczy `rev = count - 1 - forwardIndex` względem liczby rekordów **już
   zapisanych** przez strumień obliczany; dla przeplotu ten indeks wyprzedza
   `count` i odczyt trafia poza zakres → rekord all-null.

   *Krok K1.1 rozłożył to na dwie przyczyny:* **W1** — plan był sortowany
   rosnąco po interwale, co stawiało `#` przed jego producentami (naprawione,
   `results/probe.json` vs `results/probe-before-W1.json`); **W2** — drugi
   argument `#` jest wymagany `⌈Δb/Δa⌉` slotów zanim producent go wyprodukuje
   (otwarte). Analiza: `paper-arXiv/debs/G1/04-k1.1-ocena.md`.

   Przypadek `hash_computed_sorted` rozdziela to na dwie przyczyny. Dołożenie
   **niezwiązanego** zapytania, które wyzwala regułę R1 (a ta kończy się
   `topologicalSort()`), przywraca porządek zależności zniszczony przez
   sortowanie po interwale w `resolveStreamIntervals()`. Wynik badanego
   strumienia zmienia się wtedy z `–,a0,–,–,a2,–` na `–,a0,a1,–,a2,a3`:
   **gałąź pierwszego argumentu zaczyna działać w całości, gałąź drugiego
   pozostaje all-null**. Wycena obu przyczyn: `paper-arXiv/debs/G1/04-k1.1-ocena.md`.
3. **Prefiks zerowy i rekord niedostępny to dwie różne konwencje.** Prefiks
   z `>N` jest zapisany jako rekordy o wartości `0` z mapą `null` pustą
   (`xtrdb -n -s work/r1_lhs_auto/probe` → „35 records, no nulls”, mimo
   trzyrekordowego prefiksu zerowego) — nieodróżnialne od prawdziwego
   zera. Rekord niedostępny z `fetchForward()` jest oznaczony all-null. Ta sama
   sytuacja logiczna („wartość jeszcze niezdefiniowana”) ma w silniku dwie
   reprezentacje.

Konsekwencja dla D2: `r1_lhs_auto` = `r1_rhs` co do bitu we wszystkich czterech
warstwach, a `r1_lhs_blocked` (plan nieprzepisany) rozchodzi się z obiema.
Przepisanie R1 nie zachowuje wykonania planu nieprzepisanego — **naprawia je**,
przenosząc `#` z wejść obliczanych na deklarowane.

Interpretacja, decyzje i wnioski redakcyjne: `paper-arXiv/debs/G1/`.
