# K23 / H9 — prospektywny test automatycznego współdzielenia materializacji

Kampania eksperymentu K23 z `paper-arXiv/debs/research_plan.md` §10.
Plan wykonania: `paper-arXiv/debs/plan-realizacji-K23.md`.

**Faza: P3 (szkielet kampanii). Predeklaracja NIEZAMROŻONA.**
Dopóki `freeze_check.sh` nie przechodzi, **żaden pomiar kosztowy nie jest
dozwolony** (STOP-5, bramka nieprzekraczalna: pomiar wykonany wcześniej
unieważnia kampanię).

| Pole | Wartość |
|---|---|
| Gałąź | `experiment/20260808_K23` (zgłoszona jako STOP-3) |
| SHA silnika | **niezamrożone**; kampania przypnie `1cfccf9` albo późniejszy |
| Ostatni zamknięty STOP | STOP-2 (instrument logicznych zapisów w `master`) |
| Najbliższy STOP | STOP-4 — pilot compile-only, bramka GO/NO-GO |
| Worker | niepotrzebny w tej fazie; nie budzony |

## Zawartość

| Plik | Co to jest | Stan |
|---|---|---|
| `profiles.tsv` | cztery profile ablacyjne K23 | gotowe, zweryfikowane wobec §10 |
| `build_profiles.sh` | budowa i weryfikacja profili | przeniesiony z K6c, dwie zmiany (niżej) |
| `freeze_check.sh` | bramka zamrożenia i proweniencji | **szkielet** — celowo nie przechodzi |
| `SZKIC_RODZIN.md` | trzy rodziny: RQL, granice podplanu, przewidywane liczby mechanizmu | szkic do przeglądu |
| `SZKIC_D3.md` | uzasadnienie scenariusza (motivational validity) | szkic do przeglądu |

Czego jeszcze nie ma: generatorów danych, RQL jako plików, oracle’a, mutantów,
skryptu werdyktu, całej strony Flinka (czeka na **D-2**), `matrix.tsv`,
`analyze.py`. Wchodzą w P4–P6.

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

pilot compile-only → predeklaracja → testy oracle’a/liczników/mutantów →
kalibracja bez porównania efektu → pełna macierz → automatyczny werdykt → raport.

## Zakazy obowiązujące w tej fazie

* nie mierzyć kosztu, nie używać danych głównych, nie dobierać progu ani rate’u;
* nie uruchamiać pilota bez decyzji o szkicu rodzin (STOP-4 jest bramką GO/NO-GO);
* nie ruszać strony Flinka (**D-2**);
* w `retractordb` asystent nie commituje i nie pushuje;
* przed serią na workerze: governor `performance`, praca odczepiona, wzorce
  `[x]retractor` w `pgrep`/`pkill`.
