# K24e — kampania na silniku po wyprowadzeniu postaci dokładnych

Faza 4 planu `paper-arXiv/debs/plan-realizacji-k24h10.md`. Badanie
deterministyczne, compile-only w części kampanijnej, **bez workera i bez pomiaru
czasu**; bramka odwzorowania uruchamia silnik na tej samej maszynie co K24, K24p
i K24d.

| Dokument | Zawartość |
|---|---|
| [PREDECLARATION.md](PREDECLARATION.md) | predeklaracja iteracji 1 — zamrożona przed przebiegiem, **unieważniona** przez STOP.md |
| [STOP.md](STOP.md) | zatrzymanie iteracji 1: sufit `ORIGIN_LIMIT` w oracle'u, diagnoza i naprawa |
| [PREDECLARATION-2.md](PREDECLARATION-2.md) | **predeklaracja obowiązująca** — nowe ziarna, korekta P6, przewidywania P7 i P8 |
| [PIN.md](PIN.md) | punkt odniesienia: SHA silnika, `ctest` Debug i Release, sumy plików rachunku |
| [VERDICT.md](VERDICT.md) | werdykt na ziarnie `20260818` (w próbie) |
| [VERDICT_oos.md](VERDICT_oos.md) | werdykt na ziarnie `20260820` (poza próbą) |
| [REPORT.md](REPORT.md) | zestawienie wobec K24d, rozliczenie przewidywań, status epistemiczny |

## Wynik w jednym zdaniu

Na silniku `e2a61ff` **dziewięć klas operatorów na dziewięć ma ogon dokładny**,
zero zawyżających, zero zaniżających, początek logiczny dokładny w 9/9 —
na obu ziarnach, w atrybucji izolowanej i propagowanej. H10b pozostaje wsparta
(2310/2310).

## Czym to NIE jest

To **nie jest** unieważnienie K24, K24r, K24b, K24p ani K24d. Każda z nich
opisuje inny stan silnika i pozostaje w mocy dla swojego stanu. Łańcuch jest
dziś sześcioogniwowy, a reguła się nie zmienia: **kampania semantyczna jest ważna
wyłącznie dla przypiętego SHA.**

To także **nie jest** test prospektywny — patrz REPORT.md §7.
