# R618 - predeklaracja, iteracja 2

**Data zamrożenia:** 2026-11-11, **przed** przebiegami iteracji 2. **Powód iteracji:** [`STOP.md`](STOP.md) - błąd aparatury kontroli zgodności przy odniesieniu `e389edd3`. **Decyzja człowieka:** 2026-11-11, opcja (1): poprawka aparatury i iteracja 2 z pełnym przebiegiem od zera. **Podstawa:** [`README.md`](README.md) - obowiązuje w całości poza pozycjami niżej.

## 1. Co się zmienia wobec iteracji 1

Wyłącznie `paper-arXiv/measurment-tool/check_backward_corpus_compatibility.sh`: drzewo robocze na bazie `paper-arXiv` `e5bba09` (skrypt ostatnio zmieniony w `132648e`), poprawiony plik SHA-256 `1540b7127f11bcce85fe492472b1f7a52ddfa7ba61cbe77b2625b141d9de7834`. Zmiana nie jest jeszcze zacommitowana w `paper-arXiv` (commit robi człowiek); przebieg iteracji 2 używa pliku o tej sumie. Binarki, korpus, odniesienie, plik akceptacji, generatory i kryteria bez zmian.

1. **`persist_qrs` (grupy `artifacts` i `ecg`).** Dotychczasowa reguła (zdjęcie `VOLATILE` z jedynego zapytania `qrs_out`, bo `40c28dbe` nie znał `PERSISTENT`) zostaje. Gdy jej wzorzec nie występuje, a plan ma wiersz `DEFAULT VOLATILE` (postać z drzewa `e389edd3`), jedyne zapytanie `... STREAM qrs_out FROM <źródło>` dostaje przyrostek ` PERSISTENT`. Inny plan nadal kończy się błędem środowiska. Sprawdzenie przed iteracją, poza kryteriami: plan `e389edd3` po regule wykonany binarką pinu `e389edd3` (`-r -k -f -m 1671`) zostawia na dysku tylko dane `qrs_out` (12 900 B), bajtowo równe `qrs_out` z planu `40c28dbe` po starej regule na binarce `40c28dbe`.
2. **Kopie `current/` (grupa `plans`).** Kopia bajtowo równa planowi silnika pod testem po migracji jest zgodna jak dotąd. Kopia różna jest **zgodna modulo M1** tylko wtedy, gdy `current/INDEX.tsv` pinu korpusu zapisuje dla niej `m1_status=MIGRATED`, a zdjęcie z niej dokładnie `m1_wrapped` zawinięć `to_integer(...)` daje plan bajtowo równy planowi silnika pod testem; raport wypisuje każdą taką kopię wierszem `KOPIA M1` i liczy je osobno (`kopie_current_zgodne_modulo_m1`). Każda inna różnica pozostaje rozbieżnością. Uzasadnienie: kopie zapisują M1 wobec `40c28dbe`, a M1 wobec odniesienia `e389edd3` jest pusta (STOP.md §2a). Sprawdzenie przed iteracją: 54/54 kopii z iteracji 1 przechodzi regułę; kopia z jednym zmienionym bajtem i kopia bez `m1_status=MIGRATED` są odrzucane.

## 2. Kryteria iteracji 2

Kryteria 1-4 z README bez zmian, z jednym doprecyzowaniem kryterium 3: kopie `current/` są zgodne, gdy `kopie_current_zgodne + kopie_current_zgodne_modulo_m1 = 224` i żadna kopia nie jest rozbieżnością; oczekiwane z iteracji 1: 170 + 54.

Przebieg od zera: nowy katalog roboczy `run/compat-20261111-16c516f9-it2`, wszystkie siedem grup, potem kontrola przykładów (kryterium 4). Każda rozbieżność albo błąd środowiska zatrzymuje kampanię i idzie do człowieka; bez kolejnej poprawki aparatury w tej iteracji.

Wynik iteracji 1 zostaje zapisany jako zatrzymany; jego grupy `plans` i `runs` nie są liczone jako wynik iteracji 2.
