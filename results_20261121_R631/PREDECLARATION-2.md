# R631 - predeklaracja, iteracja 2

**Data zamrożenia:** 2026-11-21, **przed** przebiegiem iteracji 2. **Powód iteracji:** pochodzenie binarki odniesienia (niżej). **Decyzja człowieka:** 2026-11-21, wariant (a): czyste odniesienie i pełny przebieg od zera. **Podstawa:** [`README.md`](README.md) - obowiązuje w całości poza pozycjami niżej.

## 1. Co się stało w iteracji 1

Iteracja 1 (2026-11-21 22:01-22:08, katalog `run/compat-20261121-758be53b`) skończyła się `WYNIK: ZGODNY`, kod 0, 0 rozbieżności w siedmiu grupach; wyciąg: [`compat-it1-summary.txt`](compat-it1-summary.txt). Nagłówek raportu pokazał jednak, że binarka odniesienia `paper-arXiv/measurment-tool/run/bin/16c516f9eb76c473d5ff8510a2a812b8c23a893d/xretractor` (SHA-256 `ef8ef4c4…`, zbudowana przez `trend.py` 2026-11-12) ma wbudowaną rewizję `e389edd3`, nie `16c516f9` (`Branch: :e389edd3`; w pliku nie ma ciągu `16c516f9`). Czy to nieaktualna etykieta budowy, czy kod `e389edd3`, nie jest rozstrzygnięte. Odniesienie z README nie jest więc udokumentowaną binarką pinu i **wynik iteracji 1 nie jest liczony** do kryteriów 1-3. Zostaje zapisany jako przebieg z wątpliwym odniesieniem.

## 2. Co się zmienia wobec iteracji 1

Wyłącznie odniesienie: `retractordb/build/R618-Release/src/retractor/xretractor`, SHA-256 `955fdc71e75aa21889fadcd6bb869d62f5c49c6ac3f784b4ead657ae813685c7` - binarka zbudowana z czystego drzewa na `16c516f9` i zapisana w `results_20261111_R618/README.md` (tabela binarek, wariant all-on), z wbudowaną rewizją `16c516f9`. Silnik pod testem (`build/R631-Release`, `9d5950c6…`), korpus, skrypt kontroli (`1540b712…`), migracja, plik akceptacji i kryteria bez zmian.

## 3. Kryteria iteracji 2

Kryteria 1-6 z README bez zmian. Przebieg od zera: nowy katalog roboczy `run/compat-20261121-758be53b-it2`, wszystkie siedem grup, `--ref` wskazuje binarkę z §2. Każda rozbieżność albo błąd środowiska zatrzymuje kampanię i idzie do człowieka; bez poprawki aparatury w tej iteracji.

Pochodzenie binarki `run/bin/16c516f9…` jest pozycją otwartą poza tą kampanią (`trend.py`), do zgłoszenia człowiekowi.
