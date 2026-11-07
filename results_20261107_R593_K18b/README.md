# R593 K18b - kotwica bieżącej rewizji na pinie silnika `e389edd3`

Powtórzenie R593 K18 (`results_20261104_R593_K18/`, silnik `dev/muro@dfcc42d2`) na silniku `dev/muro@e389edd3596e4b83b6f3f4a9e238905a91c667b4`, w ramach retractordb #593 krok 8. Decyzje człowieka 2026-11-07: pin silnika artefaktu przechodzi z `40c28dbe` na `e389edd3` (bieżący `master`), a kotwica czasowa, którą artykuł nazywa kotwicą bieżącej rewizji, jest mierzona ponownie na tym silniku (wariant b), zamiast zostać przy `dfcc42d2`. Ten katalog nie poprawia R593 K18 ani K18 i nie zastępuje ich liczb: obie zostają wynikami swoich rewizji.

Powód pomiaru: między `dfcc42d2` a `e389edd3` w `src/` zmieniło się 13 plików, głównie `ipcServer.*` (retractordb #599, #600, #603, #607: porzucone kolejki klientów, drenaż, sonda życia subskrybentów rozłożona na obroty) oraz podniesienie `RLIMIT_NOFILE` przy starcie (#610). Kotwica podaje queue-emission latency, którą ta ścieżka obsługuje, więc liczb R593 K18 nie można przypisać silnikowi `e389edd3` bez pomiaru.

## Kryteria - zapisane przed pomiarem

Takie same jak w R593 K18. Wynik jest **POTWIERDZONY**, gdy wszystkie trzy warunki zachodzą jednocześnie:

1. **exactness/replay**: dwa przebiegi potoku 17 strumieni tworzą ten sam zbiór 67 plików artefaktów; dane, deskryptory i cienie są bitowo identyczne, pliki `.meta` identyczne po pominięciu 8-bajtowego czasu utworzenia (reguła K18, część porównawcza `run.sh` bez zmian);
2. **round-trip**: `a2 == a` i `b2 == b` na wspólnych prefiksach, bez rekordu zastępczego, z prefiksami co najmniej `samples - 10`; `c[2i] == b[i]`, `c[2i+1] == a[i]`;
3. **360 Hz**: jeden przebieg (`config/campaign_rate_r593k18b.csv` = wiersz K18 `1,360,1,20000`), sonda z dokładnie 19 999 interwałami (`validate_probe_csv`: żaden rekord nie zaginął), jeden klient `xqry`, harness kończy się sukcesem.

Każdy inny wynik jest niepotwierdzony i idzie do człowieka z surowymi danymi; nie jest powtarzany ani poprawiany po cichu.

**Kryterium czasowe jest opisowe**, bez progu: raport podaje E1 (mediana, p99, max), queue-emission latency (mediana, p99, p99,9, max), wake-lag max i udział maksimum w budżecie slotu 2777,8 µs, obok wartości R593 K18 i K18. Liczby nie są korygowane po fakcie. W odróżnieniu od pary K18 / R593 K18 plan 360 Hz jest tu tym samym tekstem co w R593 K18 (`examples/ecg/rec205/rec205-detect.rql`, SHA-256 `8c03d0051285ca39…` w `dfcc42d2` i w `e389edd3`), więc różnica wobec R593 K18 dotyczy silnika i przebiegu, nie obciążenia. Jeden przebieg nie wystarcza do przypisania różnicy silnikowi; raport jej tak nie nazywa.

## Różnice wobec R593 K18

| Element | R593 K18 | R593 K18b | Powód |
|---|---|---|---|
| Silnik | `dev/muro@dfcc42d2` | `dev/muro@e389edd3` | przedmiot pomiaru |
| Gałąź wyników | `experiment/20261103_R593` | `experiment/20261107_R593b` | gałąź kroku 8 #593 (założona za zgodą człowieka 2026-11-07) |
| Repozytorium kodu na workerze | `/home/michal/R593` | `/home/michal/R593b` (świeży klon `dev/muro`) | `~/R593` usunięty przy sprzątaniu Pi |
| Kampania wykonawcza | `config/campaign_rate_r593k18.csv` | `config/campaign_rate_r593k18b.csv` (ten sam wiersz) | osobny identyfikator kampanii |

`run.sh` jest kopią `results_20261104_R593_K18/run.sh`; zmienione są wyłącznie pin (`e389edd3…`, skrót `e389edd3`), gałąź wyników i tekst pomocy. Plany `config/exactness-*.rql` są bajtowo równe planom R593 K18 (bieżąca składnia, migracja S1/S2 opisana w `results_20261104_R593_K18/README.md`); dowód migracji powtórzony na `e389edd3` jest w `config/migration.tsv`.

## Stan

Przygotowanie: aparatura i kryteria przed pomiarem. Wynik zostanie dopisany tutaj po pomiarze.
