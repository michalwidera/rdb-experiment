# K24e — punkt odniesienia

Przypięcie wykonane 2026-08-18, **przed** kampanią, po zamrożeniu
[`PREDECLARATION.md`](PREDECLARATION.md).

## 1. Silnik

| Pozycja | Wartość |
|---|---|
| repozytorium | `retractordb`, gałąź `issue_232-k24h10` |
| commit | **`e2a61ff`** („Fix K24H10-pozostale-klasy”) |
| rodzic | `0f273d5` („Issue 229 freeze (#231)”) |
| drzewo robocze | **czyste** (`git status --short` pusty) |
| binarka kampanii | `build/Debug/src/retractor/xretractor` |

Przełączniki optymalizatora w binarce (`--build-info`):
`RDB_OPT_DEDUP_SUBSTRATES=ON`, `RDB_OPT_SHARE_EQUIVALENT_SELECTS=ON`,
`RDB_OPT_COMMUTATIVE_ADD=ON`, `RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=ON`,
`RDB_OPT_SIMPLIFY_EXPRESSIONS=ON`, `RDB_BENCH_PROBE=OFF`.

Kampania jest **compile-only** (`xretractor -c`), więc nie zależy od trybu
budowy; przypięcie podaje binarkę Debug dla odtwarzalności.

## 2. Co zmienił przypięty commit

Trzy postacie ogona — `-`, `Θ`, `~Θ` — zastąpione postaciami dokładnymi
(`PhaseStartupLatency()` w `src/include/SOperations.hpp` plus trzy wejścia).
`SubtractStartupLatency()` stracił argument `sourceDeclared`. Rachunek początku
logicznego, klas `#`, `>N`, `+`, `@`, projekcji i redukcji — **nietknięty**.

Skutek uboczny, wymagany do odnotowania: pojemność historii źródła różnicy jest
funkcją ogona (`floor((1+W_out)*ratio) + prefetch`), więc **zmalała** wraz z nim
(w teście jednostkowym 4 -> 3). Przewidywanie P6 predeklaracji mierzy, czy nie
powstał przez to niedomiar.

## 3. Testy regresyjne silnika na przypiętym commicie

| Przebieg | Wynik |
|---|---|
| `ninja` + `ninja install` (Debug) | bez błędów |
| **`ctest` Debug** | **188/188 passed**, 389,7 s |
| `ninja` (Release) | bez błędów |
| **`ctest` Release** | **188/188 passed**, 213,6 s |

Liczba testów wzrosła ze 186 na 188: doszły
`xcompiler.exact_tail_for_subtract_and_dehash` (pięć przypadków ręcznych
o wartościach z modelu zdarzeniowego) i
`xSOperations.dehash_startup_latency_follows_the_phase_bound`.

**Obserwacja do odnotowania, nie zamiecenia.** Między dwoma czystymi przebiegami
Release jeden przebieg oblał na `it_issue6_adhoc-run` (187/188). Test przechodzi
w izolacji, jego zapytanie nie zawiera żadnej z trzech zmienionych klas
(`DECLARE` + projekcja), a jego oprawa synchronizuje się `sleep 0.1` przed
ubiciem serwera. Zjawisko ma własny plan —
`paper-arXiv/debs/done/plan-ad-hoc-flak.md` — i **w chwili startu kampanii nie
było zamknięte**. Wpisane tutaj, bo przypięcie ma mówić prawdę o stanie,
w którym kampania startowała.

## 4. Bramki aparatury (przed kampanią)

| Bramka | Wynik |
|---|---|
| `tests/test_independence.py` | PRZESZŁA |
| `tests/test_oracle.py` | PRZESZŁA — 45 przypadków ręcznych, 228 porównań |
| `tests/test_mutants.py` | PRZESZŁA — 100% wykrycia, w tym trzy mutanty dołożone w fazie 3 |
| `tests/test_closedform.py` | PRZESZŁA — wierność repliki potwierdzona na 57 węzłach |

## 5. Aparatura — co jest bajtowo bez zmian wobec K24d

| Plik | Stan |
|---|---|
| `generator.py` | **bez zmian** |
| `run_campaign.py` | **bez zmian** |
| `verdict.py` | **bez zmian** |
| `oracle/model.py` (model zdarzeniowy) | **bez zmian** |
| `oracle/plan.py`, `oracle/engine.py`, `oracle/execute.py` | **bez zmian** |
| `oracle/closedform.py` | zmieniony — replika nadąża za silnikiem (wspólna `phase_tail`, trzy wejścia) |
| `oracle/mutants.py` | zmieniony — trzy nowe mutanty: `subtract_declaration_slot`, `theta_constant_own`, `ntheta_rounds_source_tail` |
| `tests/hand_cases.py` | zmieniony — jeden nowy przypadek (`~Θ` nad składową o niezerowym ogonie) |

**Model zdarzeniowy, generator i procedura werdyktu są nietknięte.** To jest
warunek, przy którym K24e w ogóle może cokolwiek orzec: gdyby zmienił się oracle,
kampania mierzyłaby zgodność silnika z nową definicją, a nie z tą samą.

Zmiana repliki jest wymuszona i nie jest uznaniowa — replika ma z definicji
odzwierciedlać rachunek silnika, a jej wierność sprawdza `test_closedform.py`
wobec zrzutu planu. Trzy odchodzące reguły zostały mutantami tą samą zasadą,
którą K24d zapisała `shift_tail_keeps_source` i `hash_closed_form_o1`.

## 6. Sumy kontrolne plików rachunku

```
4e2dd7eee07e89f9b294f9d9378b157a089fe2ece2247dc7a6b8df365c58ffde  generator.py
338e6691ed2f1ae7697a88b25f098f67fd7c7cb49e20f4860c8fd6d447e995e8  verdict.py
786bddf1622e9007492e37b73078bd90a0619ad236839b172bb8c2279d5ffbf9  run_campaign.py
e225bfb884fd0bec731be5a877ab6bba2415a11ce435d367f07ad1c9e211f4be  oracle/closedform.py
a17ccbd6f7ae29527fcfc5be4be9807d92cdfcbf0b76973e579565359d8aa70d  oracle/engine.py
9d8fe6d22889f163bd20271f22ab3c4d5ab5b044c9e76653faa81d353f82c9d3  oracle/execute.py
a3a6bd266845ef84a2a595f9f1d8c7a0a383b6d43c23e62665a43e27a1ed80d1  oracle/model.py
d8b8117279cda2da07b8b175a7c1ebbad70be16306d1dfd0961a19964eeba287  oracle/mutants.py
e8791feb5b8c1adc76193b5d5da15794fe9fd78d8e0803027fafd47de7cf3928  oracle/plan.py
00abd5040ec77e42660ce4640032d6faa8a61fd0f1d3894b19c9c8ce68c6d5cc  tests/hand_cases.py
cd063225697d1c50f67fea9f9f9002ef63d951cd7d6dbba26cc0b39779699f87  tests/test_closedform.py
4657b84ae2ab9eff8f44799cb5adfd3892b01a24e92aa071016cab86a8c0265b  tests/test_independence.py
70f074ed5598faba3343b46003a96ced90c67c495db1a141fb3e15abea4f76b8  tests/test_mutants.py
0c03608bf5c4f7272aad36e5561f8b854d681326fe603107dfed4eaffdf637fa  tests/test_oracle.py
```
