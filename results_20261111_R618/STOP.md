# R618 - zatrzymanie na błędzie aparatury kontroli zgodności (iteracja 1)

**Data:** 2026-11-11. Dotyczy: [`README.md`](README.md), kryterium 3 (i pośrednio 1, 2, 4).

## 1. Co się stało

Przebieg `check_backward_corpus_compatibility.sh` (start 10:13, silnik pod testem `build/R618-Release` SHA-256 `955fdc71e75a…`, odniesienie binarka pinu `e389edd3` SHA-256 `a72e641e1a05…`, korpus `84fee50`) zakończył się kodem **2** (błąd środowiska) w grupie `artifacts`:

```
BLAD: ecg: pin nie ma jednego wyjscia qrs_out VOLATILE
```

Do tej chwili przeszły grupy `plans` (682 plany, `odrzucane_na_obu=36`, `przyjete_dopiero_teraz=0`) i `runs` (67 przebiegów, bez rozbieżności), a w `artifacts` replay K18 (67 plików, pin = silnik, plan pinu = plan po S1/S2, dwa przebiegi silnika: OK) i 48 obciążeń K6c. Grupa `plans` zgłosiła **54 rozbieżności** `kopia rozna od planu silnika pod testem po migracji` (`kopie_current_zgodne=170` z 224). Grupy `g3`, `k24e`, `k24f` i `ecg` **nie biegły**; kryteria 1, 2 i 4 nie były sprawdzane. Zgodnie z README kampania jest zatrzymana i idzie do człowieka.

## 2. Diagnoza - obie przyczyny leżą w zmianie odniesienia, nie w R

Skrypt był pisany dla pinu `40c28dbe`; ten przebieg pierwszy raz bierze za odniesienie `e389edd3`.

**(a) 54 kopie `current/`.** Migracja M1 zawija wynik `SUMC`/`AVG`/`MIN`/`MAX` w `to_integer(...)` tylko tam, gdzie **pin** typuje pole jako INTEGER, a silnik pod testem jako RATIONAL. Pin `40c28dbe` typował INTEGER, `e389edd3` typuje już RATIONAL, więc M1 jest teraz pusta (`SAME=646`, wobec `MIGRATED=126` w przebiegu 2026-11-07). Kopie `current/` powstały wobec `40c28dbe` i niosą `to_integer(...)`. Sprawdzenie: zbiór 54 rozbieżnych ścieżek jest **równy** zbiorowi `m1_status=MIGRATED` w `current/INDEX.tsv` (54 = „M1 w 54” z commita `085bbdb`), a w każdej z 54 par jedyną różnicą jest zawinięcie `to_integer(...)`: po jego zdjęciu kopia jest bajtowo równa planowi silnika pod testem po migracji (54/54, 0 innych). Pozostałe 170 kopii są bajtowo równe.

**(b) `ecg`.** `persist_qrs` zdejmuje `VOLATILE` z zapytania `qrs_out` planu z drzewa pinu (`examples/ecg/rec205/rec205-qrs.rql`), bo pin `40c28dbe` nie znał `PERSISTENT`. W drzewie `e389edd3` plan ma postać `DEFAULT VOLATILE` (zmiana sprzed `e389edd3`, nie z #613 ani #617), więc wyrażenie regularne nie znajduje wiersza `... STREAM qrs_out FROM ... VOLATILE` i skrypt kończy się błędem środowiska.

Trzy plany odrzucane dotąd tylko przez silnik pod testem (wpisy pliku akceptacji) są teraz odrzucane przez oba silniki (`odrzucane_na_obu` 33 -> 36), więc wpisy akceptacji nie zostały użyte.

Rzeczy, którymi to zatrzymanie **nie jest**: nie jest rozbieżnością wartości ani wydruku planu R wobec `e389edd3` (grupa `plans` bez rozbieżności poza kopiami, `runs` 67/67), nie dotyczy rachunku ogona `#` (#617).

## 3. Stan

Kampania zatrzymana; aparatura, plik akceptacji i kryteria bez zmian. Dalszy krok (poprawka aparatury z nową predeklaracją, inne odniesienie albo powrót do drogi (a)) należy do człowieka. Log: `paper-arXiv/measurment-tool/run/compat-20261111-16c516f9.log`, katalog roboczy `run/compat-20261111-16c516f9/`.
