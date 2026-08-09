# K23 / H9 — prospektywny test automatycznego współdzielenia materializacji

Kampania eksperymentu K23 z `paper-arXiv/debs/research_plan.md` §10.
Plan wykonania: `paper-arXiv/debs/plan-realizacji-K23.md`.

**Faza: P5 wykonana — predeklaracja ZAMROŻONA (`PREDEKLARACJA.md`).**
Od tego commitu pomiar kosztowy jest dozwolony **dopiero po** bramkach P6.
Żadna pozycja predeklaracji nie może się zmienić bez **nowej predeklaracji
i nowego katalogu wyników**; danych między iteracjami nie wolno łączyć (§10).

`freeze_check.sh predeklaracja` **przechodzi** — do tej sesji kończył się kodem 2
na znaczniku `@@CODE_SHA@@`.

| Pole | Wartość |
|---|---|
| Gałąź | `experiment/20260808_K23` (zgłoszona jako STOP-3) |
| SHA silnika | **`1cfccf97e954025d5fb055f1cfd4f1fa9aff05e8`** — przypięte przez predeklarację |
| Ostatni zamknięty STOP | **STOP-5** (predeklaracja zamknięta commitem); wcześniej STOP-0…STOP-4 |
| Najbliższy STOP | **STOP-6** — rozbieżność na bramkach P6 wymaga klasyfikacji przez człowieka |
| Worker | w P5 **nietykany**; potrzebny dopiero w P6 (`freeze_check.sh worker`) |
| Rozstrzygnięcia człowieka | wszystkie zamknięte 2026-08-08: cztery z `SZKIC_RODZIN.md` §9, oba z `SZKIC_D3.md` §5.4, **D-2 = Flink biegnie na hoście** (worker wyłącznie RetractorDB) |
| Rozstrzygnięcia P5 | trzy, zapisane jawnie w `PREDEKLARACJA.md` §0: defekt klasyfikatora, rate wobec kalibracji, wielkość rozdzielająca pracy per rodzina |
| Następny krok | **P6 — bramki przed odczytem kosztów** (oracle, mutanty, liczniki, kontrole negatywne); pierwsza faza wymagająca workera |

**Predeklaracja zastępuje szkice.** `SZKIC_RODZIN.md` i `SZKIC_D3.md` zostają
nietknięte jako zapis stanu wiedzy sprzed rozstrzygnięć — obowiązuje
`PREDEKLARACJA.md`.

**Kolejność pilota (rozstrzygnięta):** trzy rodziny w jednym przebiegu
compile-only, **F9-X czytany pierwszy jako bramka**, F9-R2 i F9-R1 jako kontekst
diagnostyczny. NO-GO na F9-X kończy K23 niezależnie od wyniku pozostałych i bez
szukania rodziny zastępczej.

## Zawartość

| Plik | Co to jest | Stan |
|---|---|---|
| `PREDEKLARACJA.md` | **produkt P5** — zamrożenie w jednym dokumencie | **zamrożone 2026-08-08** |
| `verdict.py` | **skrypt werdyktu**; progi są w nim stałymi, nie parametrami | gotowe, bramka `--selftest` 18/18 |
| `gen_corpus.py`, `data/`, `rql/` | dane główne i kalibracyjne, 21 planów RQL | gotowe, bramka `--check` |
| `gen_blocks.py`, `blocks.tsv` | zamrożona kolejność 1440 przebiegów | gotowe, bramka `--check` |
| `mechanism_table.py` | klasyfikator substratów **po źródle nazwy**, nie po konwencji | gotowe, bramka `--gate` |
| `gen_manifest.sh`, `manifest.sha256` | sumy 82 zamrożonych artefaktów | gotowe |
| `profiles.tsv` | cztery profile ablacyjne K23 | gotowe, zweryfikowane wobec §10 |
| `build_profiles.sh` | budowa i weryfikacja profili | przeniesiony z K6c, dwie zmiany (niżej) |
| `freeze_check.sh` | bramka zamrożenia i proweniencji, trzy zakresy | **wypełniona**, zakres `predeklaracja` przechodzi |
| `SZKIC_RODZIN.md` | trzy rodziny: RQL, granice podplanu, przewidywane liczby | zapis sprzed rozstrzygnięć — **zastąpiony** przez predeklarację |
| `SZKIC_D3.md` | uzasadnienie scenariusza (motivational validity) | jw. |
| `RAPORT_PILOTA.md` | **produkt P4** — wynik pilota compile-only, werdykt GO | gotowe, **nietykane** |
| `pilot/` | sześć planów RQL, dane miniaturowe, `run_pilot.sh`, `mechanism_table.py`, surowe listingi w `out/` | zamknięty zapis P4, **nietykany** |
| `flink/` | **strona Flinka**: kanoniczny serializer z bramką wobec kodu silnika, sześć jobów (3 rodziny × `natural`/`manual`), plany logiczny i fizyczny, instancje operatorów, krzywa po siatce `Q`; raport `flink/PLANY_FLINKA.md` | gotowe |

Czego jeszcze nie ma: oracle’a wartości i mutantów (P6), odczytu liczników po obu
stronach (P6), skalibrowanego rate’u (P7, `ANEKS-1`), środowiska i binariów
workera (P6, `ANEKS-2`/`ANEKS-3`) oraz raportu końcowego (P9).

**Uwaga do `pilot/mechanism_table.py`:** ma znany defekt (klasyfikuje publiczny
strumień nazwany konwencją kompilatora jako substrat). Zostaje nietknięty jako
artefakt pod zamkniętym raportem; do aparatury werdyktu wchodzi poprawiony
`mechanism_table.py` w tym katalogu. Uzasadnienie: `PREDEKLARACJA.md` §0.1.

Zamrożenie obejmuje **dwa środowiska**: host (JDK 17.0.19, Flink 2.3.0,
jar SHA-256 `7c51cba8…`) i worker (kernel, governor, przypięcie CPU, cztery
binaria profili). `freeze_check.sh` sprawdza oba komplety, w osobnych zakresach:

```bash
./freeze_check.sh predeklaracja   # STOP-5 — host; workera NIE budzi
./freeze_check.sh worker          # przed P6 — środowisko i binaria workera
./freeze_check.sh macierz         # przed P8 — wszystko + skalibrowany rate
```

Zakres jest **obowiązkowy**: skrypt bez argumentu kończy się kodem 2. Komplet
hosta odczytany maszynowo w `flink/results/flink_environment.tsv`; **uwaga:
domyślne `java` na tym hoście to 25.0.3, więc JDK 17 jest przypięty ścieżką.**
Komplet workera wchodzi aneksem w P6 — P5 workera nie budzi.

## Profile — mapowanie i jego weryfikacja

`profiles.tsv` używa nazw z §10, nie z K6c. Kombinacje przełączników sprawdzono
wobec §10 (źródło normatywne) i wobec `results_20260730_K6c/profiles.tsv`:

| K23 | dedup | share | commutative (R2) | factor (R1) | wiersz K6c | rola wg §10 |
|---|---|---|---|---|---|---|
| `DEFAULT` | ON | ON | ON | ON | `ALGSTRUCT` | wszystkie cztery mechanizmy |
| `NO_R2_CANON` | ON | ON | **OFF** | ON | `STRUCT+R1` | ablacja minimalna dla F9-R2 |
| `NO_R1_FACTOR` | ON | ON | ON | **OFF** | `STRUCT+R2` | ablacja minimalna dla F9-R1 |
| `NO_R1_NO_R2` | ON | ON | **OFF** | **OFF** | `STRUCT` | komórka kontrolna 2×2 dla F9-X |

`DEFAULT` + `NO_R2_CANON` + `NO_R1_FACTOR` + `NO_R1_NO_R2` tworzą pełny układ
czynnikowy 2×2 `{R1 on/off} × {R2 canon on/off}` przy dedup i share włączonych —
dokładnie tak, jak żąda §10.

Profil `OFF` z K6c **nie wchodzi**: §10 mówi wprost, że nie jest kontrolą
przyczynową H9 (zmienia kilka mechanizmów naraz i w K6c dawał inną semantykę
natywnych liczników). Może zostać pokazany wyłącznie diagnostycznie, poza
werdyktem.

## Zmiany w przeniesionym harnessie

`build_profiles.sh` jest kopią `results_20260730_K6c/build_profiles.sh` z dwiema
zmianami — poza nagłówkiem `diff` pokazuje wyłącznie je:

1. **liczba profili** — oryginał kończył się `[ "$built" -eq 5 ]`, a K23 ma cztery
   profile, więc przeniesiony bez zmiany harness umierałby na ostatniej linii.
   Oczekiwana liczba pochodzi teraz z `profiles.tsv`; reguła „zero zbudowanych
   profili nie jest sukcesem” zachowana jako osobny warunek.
2. **prefiks katalogu builda** `build/K6-<slug>` → `build/K23-<slug>`, żeby
   kampania nie mieszała binariów z K6c w tym samym drzewie kodu.

Nazwy zmiennych środowiskowych zostają `K6_*`. Reszta — w tym
`verify_probe_binary_profile` i budowanie z `-DRDB_BENCH_PROBE=ON` — bez zmian.

## Kolejność zamrożenia (§10, nie wolno jej zmieniać)

pilot compile-only → **predeklaracja** → testy oracle’a/liczników/mutantów →
kalibracja bez porównania efektu → pełna macierz → automatyczny werdykt → raport.

Wykonane do `predeklaracja` włącznie. Następny krok: bramki P6.

## Zakazy obowiązujące w tej fazie

* nie otwierać kosztów przed klasyfikacją bramek P6 (STOP-6) — rozbieżność
  przypisana silnikowi/profilowi to brak wsparcia H9 w rodzinie, a defekt
  aparatury to nowa iteracja **bez łączenia danych**;
* nie dobierać rate’u „pod wynik”: kalibracja biegnie na osobnych danych
  i **nie porównuje** `DEFAULT` z ablacją (`ANEKS-1` musi to potwierdzić);
* nie zmieniać żadnej pozycji `PREDEKLARACJA.md` — zmiana wymaga **nowej
  predeklaracji i nowego katalogu**;
* nie podmieniać rodziny po otwarciu wyników;
* w `retractordb` asystent nie commituje i nie pushuje;
* przed serią na workerze: governor `performance`, praca odczepiona, wzorce
  `[x]retractor` w `pgrep`/`pkill` (jeden wyciekły proces wywrócił kiedyś
  22 kolejne testy, a każdy przechodził w izolacji).
