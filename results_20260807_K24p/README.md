# K24p — przebieg po przestemplowaniu okna i przeniesieniu `>N` do origin

Krok 3 planu `paper-arXiv/debs/research_plan.md` §16.1, wymuszony powtórnie
przez zmianę silnika z 2026-08-06. Badanie deterministyczne, compile-only
w części kampanijnej, bez workera i bez pomiaru czasu; bramka odwzorowania
uruchamia silnik na tej samej maszynie co K24, K24r i K24b.

| Dokument | Zawartość |
|---|---|
| [PIN.md](PIN.md) | punkt odniesienia: SHA silnika, `ctest` Debug i Release, sumy plików rachunku, lista zmian aparatury |
| [PREDECLARATION.md](PREDECLARATION.md) | predeklaracja zamrożona **przed** kampanią: ziarna, kryteria, predykcja negatywna dla `>N` |
| [VERDICT.md](VERDICT.md) | werdykt na ziarnie porównawczym `20260804` (ten sam korpus co potwierdzenie K24r) |
| [VERDICT_oos.md](VERDICT_oos.md) | werdykt na ziarnie potwierdzającym `20260807` (out-of-sample) |
| [REPORT.md](REPORT.md) | zestawienie „przed/po” wobec K24r, wyprowadzenia i wnioski |

## Wynik w jednym zdaniu

Po przestemplowaniu **początek logiczny jest dokładny w 100% węzłów wszystkich
dziewięciu klas na obu ziarnach**, ogon pozostaje dokładny dla `PASS`, `@`, `+`
i redukcji, **żadna klasa nie zaniża** ani ogona, ani origin, a `>N` przechodzi
z reżimu dokładnego do zawyżającego o predeklarowaną wartość `min(W_src, N)` —
co jest ceną adresowania offsetem względnym w `dataModel::fetchBack`, nie
brakiem postaci zamkniętej.

Człon (b) — **wsparty również po przestemplowaniu** (2310/2310, kontrole
negatywne czyste). Bramka odwzorowania: zero rozbieżności treści i zero awarii
na obu ziarnach.

## Czym to NIE jest

To **nie jest** unieważnienie K24, K24r ani K24b. Tamte kampanie opisują stan
silnika sprzed 2026-08-06 i pozostają w mocy dla tamtego stanu. K24p odpowiada
na jedno pytanie: **co z ich wyników zostaje po zmianie mierzonej wielkości**.

To **nie jest** test prospektywny. Postacie zamknięte silnika były znane przed
zamrożeniem predeklaracji; predeklarowane są ziarno potwierdzające, kryteria
i predykcja negatywna dla `>N` (§3 predeklaracji).

## Relacja do katalogów poprzedników

[`../results_20260803_K24/`](../results_20260803_K24/),
[`../results_20260804_K24r/`](../results_20260804_K24r/) oraz
[`../results_20260804_K24b/`](../results_20260804_K24b/) są **zamrożonymi
punktami odniesienia** i nie zostały tu w żaden sposób zmienione.

`generator.py` jest **bajtowo identyczny** z generatorem K24 — to warunek
porównywalności czterech kampanii. Zmiany w `oracle/`, `capacity.py`
i skryptach są wymuszone zmianą mierzonej wielkości i wyliczone w PIN.md
oraz uzasadnione w REPORT.md §1.

## Układ katalogu

```
oracle/          model zdarzeniowy (origin + ogon), most do silnika, wykonanie,
                 replika rachunku silnika (za silnikiem, dla bramki mutantów)
tests/           cztery bramki wykonywane przed kampanią
generator.py     zamrożony generator korpusu (bez zmian wobec K24)
run_campaign.py  kampania compile-only
verdict.py       werdykt automatyczny per klasa operatora, osobno ogon i origin
capacity.py      kontrola modelu pojemności historii
run_mapping_gate.py  bramka odwzorowania (end-to-end, dwie skale)
run_member_b.py  kontrola członu (b) na aparaturze K24b
check_agse_capacity.py  celowana kontrola przewidywanego niedomiaru pojemności `@`
repro_plan38.py  reproducer jedynego zgłoszenia bramki odwzorowania
raw/             surowe CSV wszystkich przebiegów
```

## Odtworzenie

```bash
# silnik: retractordb @ db4a360, build Debug (patrz PIN.md)
python3 tests/test_independence.py
python3 tests/test_oracle.py
python3 tests/test_mutants.py
python3 tests/test_closedform.py

python3 run_campaign.py --seed 20260804 --out raw/campaign_seed20260804.csv
python3 run_campaign.py --seed 20260807 --out raw/campaign_seed20260807.csv
python3 verdict.py --raw raw/campaign_seed20260804.csv --out VERDICT.md \
        --seed 20260804 --engine db4a360
python3 verdict.py --raw raw/campaign_seed20260807.csv --out VERDICT_oos.md \
        --seed 20260807 --engine db4a360

python3 capacity.py --seed 20260804 --out raw/capacity_seed20260804.csv
python3 capacity.py --seed 20260807 --out raw/capacity_seed20260807.csv
python3 run_mapping_gate.py --seed 20260807 --out raw/mapping_gate_seed20260807.csv
python3 run_member_b.py --seed 20260805
python3 check_agse_capacity.py --seed 20260804 --limit 60
python3 repro_plan38.py
```
