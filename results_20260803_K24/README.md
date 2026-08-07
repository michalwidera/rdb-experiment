# K24 / H10 — prospektywny test dokładnej granicy określoności planu

Krok 3 ścieżki §16.1 [`research_plan.md`](../../paper-arXiv/debs/research_plan.md).
Badanie deterministyczne: **bez pomiaru czasu, bez workera, bez porównania
międzysystemowego**. Kampania główna działa w trybie compile-only.

| Dokument | Zawartość |
|---|---|
| [PIN.md](PIN.md) | punkt odniesienia: SHA obu repozytoriów, `ctest` Debug i Release |
| [PREDECLARATION.md](PREDECLARATION.md) | predeklaracja zamrożona przed kampanią: korpus, ziarno, progi, konwencje |
| [VERDICT.md](VERDICT.md) | werdykt automatyczny, per klasa operatora |
| [REPORT.md](REPORT.md) | raport: wynik, diagnoza członu (b), znaleziska poboczne, zagrożenia trafności |

## Wynik w jednym zdaniu

H10a wsparta w trzech klasach operatorów (`PASS`, `>N`, redukcje), sfalsyfikowana
w sześciu — z czego cztery zawyżają ogon o dokładnie jeden slot (bezpiecznie),
a dwie (`@`, `+`) zaniżają; człon (b) nieocenialny wskutek sprzeczności
w specyfikacji reguły lokalnej. Szczegóły i konsekwencje: [REPORT.md](REPORT.md).

## Układ katalogu

```
oracle/          model zdarzeniowy (model.py), most do silnika (engine.py),
                 wykonanie i bramka odwzorowania (execute.py), replika postaci
                 zamkniętej (closedform.py — tylko dla bramki mutantów),
                 reprezentacja planu (plan.py), mutanty (mutants.py)
tests/           bramki wykonywane przed kampanią
generator.py     zamrożony generator korpusu, ziarno 20260803
run_campaign.py  kampania compile-only nad całym korpusem
run_mapping_gate.py  podpróba end-to-end, dwie skale
verdict.py       automatyczny werdykt -> VERDICT.md
raw/             surowe CSV kampanii i bramki odwzorowania
evidence/        reproducery znalezisk pobocznych (§6 REPORT.md)
work/            katalogi robocze przebiegów — nie są artefaktem, można skasować
```

## Odtworzenie

Wymaga zbudowanego silnika w stanie z [PIN.md](PIN.md).

```bash
# 1. bramki — wszystkie muszą przejść przed kampanią
python3 tests/test_independence.py     # oracle nie zawiera postaci zamkniętej
python3 tests/test_oracle.py           # 37 przypadków ręcznych, 80 porównań
python3 tests/test_closedform.py       # wierność repliki wobec silnika
python3 tests/test_mutants.py          # wykrycie 100% mutantów

# 2. kampania (ok. 30 s, 8 procesów)
python3 run_campaign.py                # -> raw/campaign.csv

# 3. werdykt
python3 verdict.py                     # -> VERDICT.md

# 4. bramka odwzorowania (ok. 25 min — uruchamia silnik w czasie rzeczywistym)
python3 run_mapping_gate.py            # -> raw/mapping_gate.csv
```

Korpus jest odtwarzalny z ziarna; nie jest przechowywany w repozytorium.
Ścieżkę do binarium można podać przez `--xretractor`.

## Zasada, na której stoi to badanie

Oracle nie może używać postaci zamkniętej — inaczej test jest tautologią.
Odwzorowanie rekordów w czasie pochodzi **z definicji operatorów**, kodowanie
i orientacja pól — z obserwacji. Ten rozdział jest wymuszony mechanicznie
przez `tests/test_independence.py` i opisany w PREDECLARATION.md §4.3.
