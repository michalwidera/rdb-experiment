# K24f — punkt odniesienia

Przypięcie wykonane 2026-09-12, **przed** kampanią, po zamrożeniu
[`PREDECLARATION.md`](PREDECLARATION.md) (commit `cfed5e5` w `rdb-experiment`).

## 1. Silnik

| Pozycja | Wartość |
|---|---|
| repozytorium | `retractordb`, gałąź **`master`** |
| commit | **`098e531e83d1f0b706561c1cb63672697a05ad34`** („DRIFT JOURNAL - clean") |
| rodzic | `351189782ad3f92f8067a35b47780429deb8fd38` („New extended campan - for H10") |
| drzewo robocze | **czyste** (`git status --short` pusty) |
| binarka kampanii | `build/Release/src/retractor/xretractor` |

Przełączniki optymalizatora w binarce (`--build-info`):
`RDB_OPT_DEDUP_SUBSTRATES=ON`, `RDB_OPT_SHARE_EQUIVALENT_SELECTS=ON`,
`RDB_OPT_COMMUTATIVE_ADD=ON`, `RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=ON`,
`RDB_OPT_SIMPLIFY_EXPRESSIONS=ON`, `RDB_BENCH_PROBE=OFF`.

**Kampania idzie na commicie osiągalnym na `master`.** Pole „mierzony" i pole
„osiągalny" to ten sam SHA, więc wyjątek z §2.4 manifestu artefaktu — który
powstał, bo K24e zmierzono na `e2a61ff`, a squash merge uczynił tę rewizję
nieosiągalną — tutaj nie powstaje.

**`src/` nie drgnął od `40d9bbb`**, czyli od commita naprawiającego wady 1 i 4;
sprawdzone `git diff 40d9bbb HEAD -- src/` (pusty), nie założone. Dwa commity
stojące pomiędzy ruszyły wyłącznie aparaturę badawczą i dziennik dryftu.

## 2. Wyniki wszystkich dziewięciu poziomów fazy 0

Poziomy 1-5 i 7-9 wykonane na **przypiętym** commicie `098e531` z czystym
drzewem. Poziom 6 — patrz zastrzeżenie pod tabelą.

| # | Poziom | Wynik | Liczby |
|---|---|---|---|
| 1 | `ninja cformat` na czystym drzewie | **ZALICZONY** | zero zmian po sformatowaniu |
| 2 | `ninja` + `ninja install` (Debug) | **ZALICZONY** | bez błędów |
| 3 | `ctest` Debug, pełny | **ZALICZONY** | **241/241**, 0 awarii, **0 `DISABLED`**, 2 pominięte (`st_api_fake`, `st_api_real`), `ctest` kod 0, 267,5 s |
| 4 | `ninja` + `ctest` Release, pełny | **ZALICZONY** | **241/241**, 0 awarii, `ctest` kod 0, 160,9 s |
| 5 | `ninja test_gate` | **ZALICZONY** | H10a **9/9** klas dokładnych i **9/9** origin dokładnych na obu zamrożonych ziarnach (`20260804`, `20260807`); H9 **84/84** kompilacji na czterech profilach ablacji + **4/4** odrzucone mutanty; „PRZESZLY na silniku 098e531", 62,2 s |
| 6 | `ninja test_drift` | **ZALICZONY** | patrz §2.1 |
| 7 | podłoga ablacji (pięć `RDB_OPT_*` = OFF, sonda OFF) | **ZALICZONY** | przełączniki potwierdzone przez `--build-info`; **232/232**, 0 awarii; **9** wyłączonych = dokładnie etykiety `expected_ablation_failure` |
| 8 | budowa `aggressive_expr_optimization=ON` | **ZALICZONY** | `ctest` **241/241**, 0 awarii, 300,9 s; **deskryptory 29/29 identyczne** wobec budowy domyślnej |
| 9 | kompilacja UC01-UC08 | **ZALICZONY** | **8/8**, zero błędów |

Żaden poziom nie jest NIEURUCHOMIONY.

Poziom 8 porównuje **deskryptory**, nie całe zrzuty planu: programy pól różnią
się w 21 z 29 planów, dokładnie tam, gdzie reguła R3 przepisuje `a*a` na `a^2`.
To jest zadanie tego przełącznika; deskryptor — nazwy, typy, długości, interwały,
`tail=` i `origin=` — jest niezmieniony.

### 2.1. Poziom 6 — zastrzeżenie co do rewizji

`ninja test_drift` wykonany na commicie **`3511897`** (rodzic przypiętego), drzewo
**czyste**, ziarno losowane **2037301320**:

| Poziom wewnętrzny | Wynik |
|---|---|
| H10a — rachunek początku i ogona | **ZGODNY**, **10/10 klas dokładnych** |
| H10b — wystarczalność reguły lokalnej | **WSPARTA** — rozjazd 53,7% (próg 5%), 2295/2295 dodatnich, 2295/2295 co do postaci |
| H9 — mechanizm współdzielenia | **ZGODNY** — 84/84 kompilacji, 4/4 mutanty |
| H9 — wartości wobec Apache Flink | **ZGODNY** — **siedem** bramek P6, proweniencja włącznie |
| H9 — próg czasowy | **NIESPRAWDZONY** |

**WYNIK: BEZ DRYFTU, zakres niepełny.** 2579,0 s. Wiersz w `DRIFT_JOURNAL.tsv`:

```
2026-09-12T16:39:32+02:00  3511897  czyste  2037301320  ZGODNY  WSPARTA  ZGODNY  ZGODNY  NIESPRAWDZONY  BEZ DRYFTU, zakres niepelny
```

Różnica między `3511897` i przypiętym `098e531` to **jeden wiersz w
`DRIFT_JOURNAL.tsv`** i nic więcej: `src/` i cała aparatura `test/research_gate/`
są bajtowo te same. Wynik poziomu 6 opisuje więc przypięty silnik, ale jego
stempel nazywa rodzica — i to jest zapisane tutaj, a nie przemilczane.

Próg czasowy H9 jest **NIESPRAWDZONY z konstrukcji**, nie przez pominięcie:
wymaga 1440 komórek na przypiętym pi400 pod `PREEMPT_RT`, ok. 48 h, i jest
wielkością mierzoną, nie obliczaną. K24f go nie dotyczy.

Ten przebieg jest **pierwszym**, w którym H10a ma dziesięć klas, a nie dziewięć,
i pierwszym, w którym kolumna wartości H9 mówi `ZGODNY`, a nie
`ZGODNY-bez-prow` — trzy wcześniejsze biegi tej sesji szły na brudnym drzewie.

## 3. Wady otwarte z §3.2 planu — zdanie o każdej

| Wada | Stan na przypiętym silniku |
|---|---|
| **Samoodwołanie zapętla kompilator** | **ZAMKNIĘTA** w `40d9bbb`. `SELECT * STREAM x FROM x` nie kończyło się w 120 s i rosło w pamięci do wyczerpania; pod `ulimit -v` dawało `std::bad_alloc`. Przyczyną nie był brak detekcji cyklu w `qTree::topologicalSort()` (tak mówił plan), a to, że `compiler::expandSchemaWildcards()` stoi PRZED `resolveStreamIntervals()` i przy pętli własnej iterowała po tej samej liście `lSchema`, do której dopisywała. Naprawa odrzuca plan w tej gałęzi; plan kompiluje się teraz z błędem w 109 ms. Zmierzone: **osiem pozostałych kształtów** samoodwołania (`x>1`, `x-2`, `x&2`, `x%2`, `x#x`, `x+x`, `x@(1,2)`, `x.sumc`) było i jest poprawnie odrzucanych przez detektor cyklu, z niezmienionym komunikatem — pilnuje tego zapadka `other_self_reference_shapes_stay_with_the_cycle_detector`. **Nie dotyczy korpusu:** generator buduje węzły wyłącznie nad już istniejącymi, więc każdy plan jest acykliczny i warunek naprawy nigdy nie jest prawdziwy. |
| **`SELECT *` gubi typ producenta** | **ZAMKNIĘTA** scaleniem `a35cd12`. `expandSchemaWildcards()` bierze `rlen` i `rtype` ze schematu producenta; do 2026-09-11 wpisywała `rField(name, 4, 1, INTEGER)`, więc `SELECT *` nad `DOUBLE` dawało `INTEGER` i przesunięte offsety kolejnych pól rekordu. §3.2 planu wymienia ją jako otwartą — dokument powstał przed scaleniem. **Nie perturbuje kampanii z drugiego powodu niż plan podawał:** korpus deklaruje wszystkie pola jako `INTEGER` (`plan.to_rql`), więc nie ma tu czego zgubić. |
| **`DRIFT_JOURNAL.tsv` blokuje drugi przebieg** | **ZAMKNIĘTA** w `40d9bbb`. Skutek był gorszy, niż opisuje §3.2: `run_drift.sh:137` liczy czystość drzewa z wykluczeniem dziennika, więc `--allow-dirty` nie było dodawane, a `validate_corpus.py` dziennika nie wykluczała i rzucała `engine worktree is dirty`. Poziom „H9 mechanizm" wpadał wtedy w gałąź `S_MECH="DRYFT"` — drugi przebieg z rzędu orzekał **fałszywy dryft**, awarię aparatury nieodróżnialną od regresji silnika. Naprawa stosuje to samo wykluczenie w obu miejscach. Potwierdzone **na żywo i w obie strony** na drzewie z niezacommitowanym wierszem dziennika: wersja przed naprawą `engine worktree is dirty`, wersja po naprawie zwraca czyste SHA. |
| **Funkcje o niewymiernej przeciwdziedzinie nad typami dokładnymi** | **OTWARTA, ZAWĘŻONA.** Commit `47a4743` (już na `master`) zamknął klasę CICHEJ ZŁEJ WARTOŚCI: siedem funkcji (`sqrt`, `sin`, `cos`, `exp`, `tan`, `log`, `log2`) jest odrzucanych nad `RATIONAL`, i w liście `SELECT`, i w warunkach `RULE` (`checkRuleConditionShapes()`). Otwarty został **kontrakt typu nad `INTEGER`**: `tan`, `log` i `log2` wracają na `INTEGER`, czyli obcinają część ułamkową — strata jawna i udokumentowana, nie przepełnienie. **Ustalenie tej sesji, którego notatka w kodzie nie zawiera:** `Sqrt` należy do tej samej klasy — jest jednocześnie w `hasIrrationalRange()` i w `typePreservingFunctions()`, więc `Sqrt(INTEGER)` też obcina. To jest istotne, bo **korpus H9 stoi na `Sqrt(A[0]*A[0]+B[0]*B[0])` nad polami `INTEGER` w 14 z 21 planów**, więc spójna naprawa tej wady zmienia deskryptory i układ bajtów rekordu w tych planach — czyli unieważnia zamrożone wyniki H9/K26v3 i rozjeżdża porównanie wartości z portem we Flinku. Naprawa jest zadaniem o zakresie „zmiana formatu artefaktu", z własnym przejściem przez bramki. Drzewo nosi jawną zapadkę na zrobienie tego mimochodem: `test_compiler.cpp`, `gating_tan_log_log2_leaves_their_result_type_alone`. **Nie dotyczy korpusu K24f:** `plan.node_expression` nie emituje ani jednej funkcji skalarnej. |

Wady zamknięte i nie wymagające działania: flak `it_issue6_adhoc-run` (zamknięty
2026-08-18, `acbb98b`), znalezisko A (zamknięte 2026-08-09, klasyfikacja
`apparatus`).

## 4. Sumy kontrolne plików rachunku

Silnik:

```
fc1c78ffa62f7972f3e1ece5dfde02d7cb2c6917d8c865b9e9c9b5b2950c6a50  src/retractor/lib/compiler.cpp
03b010b38bc1ee24b35661212bd6e9442407955dc2e4f629181ed560547049c6  src/include/SOperations.hpp
9a32eb8a13f8a14af71a30d8e3fffbd98de310a7aadd944621236a43fa8b0d61  src/retractor/lib/qTree.cpp
```

Aparatura (`test/research_gate/h10/`, pierwsze 16 znaków):

| Plik | sha256 |
|---|---|
| `generator.py` | `540ff689334e748b` |
| `oracle/plan.py` | `8d79c5ab83232fcf` |
| `oracle/model.py` | `29f9214e74739848` |
| `oracle/closedform.py` | `ff8885bfc08eb2b7` |
| `oracle/mutants.py` | `782d3ef382c780c1` |
| `oracle/engine.py` | `47d59a550825b7cf` |
| `oracle/execute.py` | `9d8fe6d22889f163` |
| `tests/hand_cases.py` | `a79123836a570563` |
| `run_campaign.py` | `aa91d9a189471503` |
| `decision_rule.py` | `86bdb32b025640ea` |
| `verdict.py` | `b47ed76f9bbf3e77` |
| `run_mapping_gate.py` | `13d0a62511e3751b` |

## 5. Co jest bajtowo bez zmian wobec K24e

**Odpowiedź na pytanie §8 planu jest przecząca i wymaga zdania wprost:
`generator.py` i `oracle/plan.py` NIE są nietknięte.** Faza 2 dołożyła do nich
stratę `WINDOW` i rodzaj węzła `WINDOW`. Na początku tej sesji oba były bajtowo
identyczne z kopiami K24e; teraz nie są.

| Plik | Wobec K24e | Wierszy różnych / z tego kod |
|---|---|---|
| `capacity.py` | **identyczny** | — |
| `compare_gates.py` | **identyczny** | — |
| `check_agse_capacity.py` | **identyczny** | — |
| `oracle/execute.py` | **identyczny** | — |
| `tests/test_closedform.py` | **identyczny** | — |
| `tests/test_independence.py` | **identyczny** | — |
| `tests/test_mutants.py` | **identyczny** | — |
| `tests/test_oracle.py` | **identyczny** | — |
| `oracle/plan.py` | różny (**Faza 2**) | 76 / 54 |
| `run_campaign.py` | różny (Faza 2 + zmiany po K24e) | 70 / 52 |
| `generator.py` | różny (**Faza 2**) | 66 / 37 |
| `tests/hand_cases.py` | różny (**Faza 2**) | 61 / 24 |
| `oracle/model.py` | różny (**Faza 2**) | 45 / 25 |
| `oracle/closedform.py` | różny (**Faza 2**) | 24 / 12 |
| `oracle/mutants.py` | różny (**Faza 2**) | 19 / **3** |
| `run_mapping_gate.py` | różny (Faza 2) | 17 / 13 |
| `verdict.py` | różny (**nie** Faza 2) | 215 / 188 |
| `run_member_b.py` | różny (**nie** Faza 2) | 50 / 35 |
| `oracle/engine.py` | różny (**nie** Faza 2) | 36 / 29 |
| `repro_plan38.py` | różny (**nie** Faza 2) | 10 / 8 |
| `decision_rule.py` | **nie istniał** w K24e | — |
| `tests/test_phase_forms.py` | **nie istniał** w K24e | — |
| `tests/test_h10b_population.py` | **nie istniał** w K24e | — |

### 5.1. Dowód, że zamrożony korpus mimo tego nie drgnął

Zmiana generatora i modelu planu nie jest wolna od podejrzenia i nie wystarczy
o niej zapewnić. Korpus 10 010 planów wyprodukowany **kodem K24e** i **kodem
przypiętym** daje tę samą sumę SHA-256 po konkatenacji `(strata, to_rql(plan))`
wszystkich planów, na oba zamrożone ziarna:

```
ziarno 20260804
  kod K24e : 3563fbb0ed2048fc0776c49478f21d7f92a228f63811242472ba658c573ab1b0
  kod dziś : 3563fbb0ed2048fc0776c49478f21d7f92a228f63811242472ba658c573ab1b0
ziarno 20260807
  kod K24e : 00fa240817c4f19b950345c9f6187970a449e6a962c87c50da69e7127bd06b08
  kod dziś : 00fa240817c4f19b950345c9f6187970a449e6a962c87c50da69e7127bd06b08
```

Mechanizm, który to gwarantuje: strata `WINDOW` **nie** należy do domyślnego
`STRATA` i wchodzi wyłącznie przez jawne `generate(..., strata=STRATA_WITH_WINDOW)`
albo `run_campaign.py --with-window`. Gdyby należała, przesunęłaby wszystkie
losowania — strata jest przydzielana rotacyjnie po indeksie planu, a każdy plan
ciągnie z tego samego `random.Random(seed)`. Skutkiem byłoby oblanie
`ninja test_gate` z powodu korpusu, nie silnika: `compare_regimes.py` zwraca kod 2
przy jakiejkolwiek zmianie zestawu klas.

Potwierdza to niezależnie poziom 5 fazy 0: `test_gate` daje na przypiętym silniku
dalej **9/9 i 9/9** na obu zamrożonych ziarnach.

### 5.2. Model zdarzeniowy a replika — rozdział zachowany

`oracle/model.py` dostał gałąź `WINDOW` w `dependencies()` i w `content()`, ale
**nie** dostał postaci zamkniętej: nie ma w nim ani `O_src + W - 1`, ani żadnego
wzoru na origin okna. Origin wychodzi ze skanu po liście zależności
`n-(W-1) … n`, tak samo jak dla każdej innej klasy. Bramka
`tests/test_independence.py` przeszła na przypiętym silniku, czyli oracle nadal
nie importuje repliki i nie zawiera nazw rachunku silnika.

Wierność repliki sprawdzona wobec zrzutu planu silnika na **67** węzłach
przypadków ręcznych, **8** z nich klasy `WINDOW`, zero niezgodności
(`tests/test_closedform.py`).

## 6. Parametry przebiegu kampanii

| Pozycja | Wartość |
|---|---|
| korpus | `STRATA_WITH_WINDOW`, **15** strat, wywołanie `run_campaign.py --with-window` |
| liczność | 10 010 planów na ziarno |
| **ziarno główne** | **`20260912`** |
| **ziarno potwierdzające** | **`20260913`** |
| konwencja werdyktu | C1 (nieostra); C2 jako kolumna wrażliwości |
| procedura decyzyjna | `decision_rule.py`, uruchamiana **raz** na ziarno |
| bramka odwzorowania | `run_mapping_gate.py --with-window`, dwie skale, budżet 8 s na przebieg |

Oba ziarna są **nieużyte**: nie występują w żadnym pliku `rdb-experiment`,
`retractordb/test/research_gate`, `paper-arXiv` ani `rdb-artifact`. Aparatura
Fazy 2 była budowana i uruchamiana wyłącznie na ziarnie **spalonym** `20260803`;
trzy przebiegi dryftu tej sesji losowały ziarna z innej przestrzeni
(678532947, 1859734341, 2037301320).

## 7. Znana nieścisłość aparatury, nienaprawiona przy przypięciu

Docstring `generator.py` mówi „przy N = 10 010 każda [strata] ma 715 instancji".
Jest to prawda dla korpusu domyślnego (14 strat) i **nieprawda** dla korpusu
z oknem: 15 strat daje 667 planów na stratę, a pięć pierwszych po 668. Właściwe
liczby stoją w `PREDECLARATION.md` §5. Docstring nie był poprawiany przed
przypięciem, żeby nie ruszać pliku aparatury po zamrożeniu predeklaracji;
poprawka należy do diffu fazy 4.

## 8. Zmiana aparatury PO przypięciu — `run_mapping_gate.py`

**Dopisane po kampanii, świadomie i z zachowaniem sumy sprzed zmiany.** Sekcja §4
przypina `run_mapping_gate.py` sumą `13d0a62511e3751b`. Ta suma jest **nieaktualna**
dla przebiegu powtórzonego bramki odwzorowania: po kampanii plik został naprawiony
i ma teraz `d8cdcaf4e0493ff1`.

Podmiana hasha w §4 byłaby zatarciem śladu, więc jej nie ma. Kolejność jest taka:

1. przypięcie (ta wersja: `13d0a62511e3751b`);
2. kampania na obu ziarnach i `decision_rule.py` uruchomiona **raz** na ziarno —
   werdykty H10a i H10b pochodzą **z tej** aparatury i są nietknięte;
3. pierwszy przebieg bramki odwzorowania — poziom zatrzymany, przyczyna
   zdiagnozowana jako `apparatus`;
4. decyzja człowieka o naprawie, naprawa, przebieg powtórzony bramki
   (ta wersja: `d8cdcaf4e0493ff1`).

Zmiana dotyczy **wyłącznie wymiarowania przebiegu** bramki odwzorowania: horyzontu
czasowego, budżetu slotów i kryterium odrzucenia „poza budżetem". Nie rusza
korpusu, modelu zdarzeniowego, repliki, mutantów, przypadków ręcznych ani
procedury decyzyjnej — ich sumy z §4 obowiązują bez zmian. Pełny zapis przyczyny,
decyzji i liczb przed i po: [`STOP.md`](STOP.md).
