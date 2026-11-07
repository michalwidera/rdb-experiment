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

**POTWIERDZONY 2026-11-07** - wszystkie trzy warunki z kryteriów zachodzą na `dev/muro@e389edd3`, binarka Release-Probe z `~/R593b` (SHA-256 `xretractor` `91e600251913661a…`, `xqry` `8aa4132fa4ac7314…`, binarki w `~/.local/bin` bajt w bajt równe buildowi; `--build-info`: 4 × `RDB_OPT_*=ON`, `RDB_BENCH_PROBE=ON`, `RDB_OPT_SIMPLIFY_EXPRESSIONS=ON`).

1. exactness/replay (`exactness/`, commit `bacd2c4`): 2 przebiegi, 67 artefaktów, 51 identycznych bitowo, 16 `.meta` identycznych po pominięciu czasu utworzenia; zero różnic. Opisowo, poza kryterium: artefakty bez `.meta` są bajt w bajt równe artefaktom R593 K18 na `dfcc42d2`, a `configuration.sha256` jest ten sam;
2. round-trip: `a2 == a`, `b2 == b` bez rekordu zastępczego, `c[2i] == b[i]`, `c[2i+1] == a[i]`; rekordy a=19 999, b=19 999, c=39 994, a2=19 996, b2=19 997 (prefiksy >= 19 990), te same liczby co w R593 K18;
3. 360 Hz (`rate_r593k18b/study_01/`, commit `8fcf07d`): 19 999 interwałów w sondzie (żaden rekord nie zaginął), jeden klient `xqry`, harness zakończony sukcesem, governor `performance`, `throttled=0x0`.

Liczby czasowe (opisowo, jeden przebieg na każdej rewizji). Plan 360 Hz jest tym samym tekstem co w R593 K18, ale jeden przebieg nie wystarcza, by różnicę wobec R593 K18 przypisać silnikowi; w K18 plan był innym tekstem.

| Metryka | K18 `bc37186` | R593 K18 `dfcc42d2` | R593 K18b `e389edd3` |
|---|---|---|---|
| E1 mediana | 1312,4 µs | 885,7 µs | 916,4 µs |
| E1 p99 | 1617,9 µs | 1105,6 µs | 1115,7 µs |
| E1 max | 1838,5 µs | 1303,0 µs | 1284,8 µs |
| max E1 / budżet 2777,8 µs | - | 46,9% | 46,3% |
| queue-emission mediana | 1372,8 µs | 937,2 µs | 970,8 µs |
| queue-emission p99 | 1718,6 µs | 1211,1 µs | 1215,0 µs |
| queue-emission p99,9 | 1832,5 µs | 1291,4 µs | 1276,5 µs |
| queue-emission max | 1944,0 µs | 1420,3 µs | 1426,1 µs |
| max queue-emission / budżet 2777,8 µs | 70,0% | 51,1% | 51,3% |
| wake_lag mediana / max | 20,7 / 54,3 µs | 22,2 / 71,2 µs | 22,3 / 69,6 µs |

Stan workera: ostatni start 2026-11-07 18:51:42, potem build Release-Probe (do 20:42), oba podejścia exactness i badanie 360 Hz o 21:13; nadzorca restartuje workera tylko między badaniami, a kampania ma jedno badanie. Kolejność jak w R593 K18 (build, exactness, badanie).

Odstępstwa w przebiegu:

- pierwsze podejście `run.sh` (20:43) przeszło replay i round-trip, ale zakończyło się błędem przy kopiowaniu wyników: katalog `exactness/` nie istniał, bo kopia aparatury pominęła `exactness/README.md`, które w R593 K18 przyszło z commitem przygotowawczym `875f571`. Nic nie zapisano, werdykty tego podejścia nie są liczone. Katalog dodany commitem `8e749a8`, `run.sh` bez zmian, drugie podejście 20:59-21:05 od zera;
- strażnik buildu nadzorcy (`grep 'build/Release-Probe' scripts/buildrdb.sh`) nadal nie zna `scripts/buildrdb/research.sh`, więc build był ręczny (`scripts/buildrdb.sh conan ninja probe`, `cmake --install build/Release-Probe`), a nadzorca szedł z `--skip-build` i weryfikacją zainstalowanej binarki, jak w drugim podejściu R593 K18.
