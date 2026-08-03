# K24r — potwierdzenie poza próbą po naprawie postaci zamkniętych

Krok 5.1 planu `paper-arXiv/debs/plan-naprawy-defektow.md` §7. Badanie
deterministyczne, compile-only w części kampanijnej, bez workera i bez pomiaru
czasu; bramka odwzorowania uruchamia silnik na tej samej maszynie co K24.

| Dokument | Zawartość |
|---|---|
| [PIN.md](PIN.md) | punkt odniesienia: SHA silnika, `ctest`, sumy plików postaci zamkniętej |
| [PREDECLARATION.md](PREDECLARATION.md) | predeklaracja zamrożona **przed** kampanią potwierdzającą: ziarno, kryteria |
| [VERDICT.md](VERDICT.md) | werdykt na ziarnie porównawczym `20260803` |
| [VERDICT_oos.md](VERDICT_oos.md) | werdykt na ziarnie potwierdzającym `20260804` (out-of-sample) |
| [REPORT.md](REPORT.md) | zestawienie „przed/po” per klasa i wnioski |

## Wynik w jednym zdaniu

Nowe postacie zamknięte ogona dla `+` i `@` zgadzają się z granicą zdarzeniową
w **100%** węzłów obu klas na korpusie niewidzianym podczas ich wyprowadzania,
a bramka odwzorowania na tym korpusie nie wykazuje rozbieżności treści —
falsyfikacja H10a w tych dwóch klasach była defektem wzorów, nie brakiem postaci
zamkniętej. Klasy `#`, `-`, `Θ` i `~Θ` pozostają sfalsyfikowane.

## Czym to NIE jest

To **nie jest** powtórzenie K24 ani jej unieważnienie. K24 zmierzyła postać
zamkniętą zaimplementowaną 2026-08-03 i jej werdykt pozostaje w mocy dla tamtego
stanu silnika. K24r odpowiada na jedno pytanie: czy poprawione wzory działają
poza korpusem, z którego zostały wyprowadzone.

## Relacja do katalogu K24

Katalog [`../results_20260803_K24/`](../results_20260803_K24/) jest **zamrożonym
punktem odniesienia** i nie został tu w żaden sposób zmieniony. Aparatura
(`oracle/`, `tests/`, `generator.py`, skrypty) jest jego kopią **bez zmian
merytorycznych** — jedyną różnicą jest replika postaci zamkniętej
`oracle/closedform.py`, która musi iść za silnikiem, bo służy bramce mutantów
i bramce wierności repliki.

## Układ katalogu

```
oracle/          model zdarzeniowy, most do silnika, bramka odwzorowania,
                 replika postaci zamkniętej (za silnikiem po naprawie)
tests/           bramki wykonywane przed kampanią
generator.py     zamrożony generator korpusu (bez zmian wobec K24)
run_campaign.py  kampania compile-only
verdict.py       werdykt automatyczny per klasa operatora
capacity.py      kontrola modelu pojemności historii
run_mapping_gate.py  bramka odwzorowania (end-to-end, dwie skale)
raw/             surowe CSV obu ziaren
```
