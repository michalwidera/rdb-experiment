# R618 K18c - kotwica bieżącej rewizji na rewizji silnika R = `16c516f9`

Powtórzenie R593 K18b (`results_20261107_R593_K18b/`, silnik `dev/muro@e389edd3`) na silniku `dev/muro@16c516f9eb76c473d5ff8510a2a812b8c23a893d`, w ramach retractordb #618, droga (b), etap 3. Decyzja człowieka 2026-11-11 (komentarz #618 6791719096, D2): pin silnika artefaktu przechodzi z `e389edd3` na R, a kotwica czasowa, którą artykuł nazywa kotwicą bieżącej rewizji, jest mierzona ponownie na R protokołem K18b bez zmian. Ten katalog nie poprawia K18, R593 K18 ani R593 K18b i nie zastępuje ich liczb: każda zostaje wynikiem swojej rewizji. Wynik porównania korpusu na R wobec `e389edd3` (K24e, K24f, kontrola zgodności, przykłady) jest w `results_20261111_R618/`.

Powód pomiaru: między `e389edd3` a R w `src/` zmieniły się dwa pliki, oba w #617: `src/include/SOperations.hpp` (`HashStartupLatency()` liczy ogon przeplotu `#` postacią zamkniętą zamiast przeglądu okresu fazowego) i `src/retractor/lib/compiler.cpp` (straż zakresu ogona w `computeStartupLatency()`). To rachunek kompilatora, nie ścieżka IPC, którą obsługuje queue-emission latency; kotwica jest jednak opisana w artykule jako pomiar rewizji pinu, więc liczb R593 K18b nie przypisuję R bez pomiaru. Spośród planów tego pomiaru `#` występuje tylko w `config/exactness-roundtrip-read.rql` (`c = a#b`); wydruk `-c` tych trzech planów jest na R bajtowo taki sam jak na `e389edd3` (`config/migration.tsv`).

## Kryteria - zapisane przed pomiarem

Takie same jak w R593 K18b. Wynik jest **POTWIERDZONY**, gdy wszystkie trzy warunki zachodzą jednocześnie:

1. **exactness/replay**: dwa przebiegi potoku 17 strumieni tworzą ten sam zbiór 67 plików artefaktów; dane, deskryptory i cienie są bitowo identyczne, pliki `.meta` identyczne po pominięciu 8-bajtowego czasu utworzenia (reguła K18, część porównawcza `run.sh` bez zmian);
2. **round-trip**: `a2 == a` i `b2 == b` na wspólnych prefiksach, bez rekordu zastępczego, z prefiksami co najmniej `samples - 10`; `c[2i] == b[i]`, `c[2i+1] == a[i]`;
3. **360 Hz**: jeden przebieg (`config/campaign_rate_r618k18c.csv` = wiersz K18 `1,360,1,20000`), sonda z dokładnie 19 999 interwałami (`validate_probe_csv`: żaden rekord nie zaginął), jeden klient `xqry`, harness kończy się sukcesem.

Każdy inny wynik jest niepotwierdzony i idzie do człowieka z surowymi danymi; nie jest powtarzany ani poprawiany po cichu. Czerwony wynik niczego nie psuje w artefakcie: droga powrotu do (a) w #618 jest otwarta do etapu 6.

**Kryterium czasowe jest opisowe**, bez progu: raport podaje E1 (mediana, p99, max), queue-emission latency (mediana, p99, p99,9, max), wake-lag mediana i max oraz udział maksimum w budżecie slotu 2777,8 µs, obok wartości R593 K18b, R593 K18 i K18. Liczby nie są korygowane po fakcie. Plan 360 Hz jest tym samym tekstem co w R593 K18b i R593 K18 (`examples/ecg/rec205/rec205-detect.rql`, SHA-256 `8c03d0051285ca397e69ea9158e89119f6be52d734b6a2b2e975e6f19e7a35ab` w `dfcc42d2`, `e389edd3` i R; #613 zmieniło inne przykłady), a dane wejściowe `examples/ecg/rec205/` są bez zmian między `e389edd3` a R. Jeden przebieg nie wystarcza do przypisania różnicy silnikowi; raport jej tak nie nazywa.

## Różnice wobec R593 K18b

| Element | R593 K18b | R618 K18c | Powód |
|---|---|---|---|
| Silnik | `dev/muro@e389edd3` | `dev/muro@16c516f9` | przedmiot pomiaru |
| Gałąź wyników | `experiment/20261107_R593b` | `experiment/20261111_R618` | gałąź etapu 3 #618 (założona za zgodą człowieka 2026-11-11) |
| Repozytorium kodu na workerze | `/home/michal/R593b` | `/home/michal/R618` (świeży klon `dev/muro`) | osobny klon na rewizję |
| Kampania wykonawcza | `config/campaign_rate_r593k18b.csv` | `config/campaign_rate_r618k18c.csv` (ten sam wiersz, ten sam SHA-256 `69f82ada…`) | osobny identyfikator kampanii |

`run.sh` jest kopią `results_20261107_R593_K18b/run.sh`; zmienione są wyłącznie pin (`16c516f9…`, skrót `16c516f9`), gałąź wyników i tekst pomocy (komentarz nagłówka i `usage`). Plany `config/exactness-*.rql` są bajtowo równe planom R593 K18b i R593 K18. Dowód migracji S1/S2 powtórzony na R jest w `config/migration.tsv`: `paper-arXiv/measurment-tool/migrate_corpus.py` z binarką `build/R618-Release` (R, czyste drzewo, SHA-256 `xretractor` `955fdc71e75aa21889fadcd6bb869d62f5c49c6ac3f784b4ead657ae813685c7`) jako odniesieniem i silnikiem pod testem, oryginały to zamrożone `config/exactness-*.rql`; plik jest bajtowo równy `results_20261107_R593_K18b/config/migration.tsv` (M1 `SAME`, S `MIGRATED` 3+4 / 1 / 2, wydruk `-c` przed i po migracji identyczny, `--verbose` po migracji bez ostrzeżenia `is deprecated`). Metoda sum wydruku `-c` (stdout i stderr `xretractor p.rql -c` w katalogu tymczasowym) odtwarza przed użyciem kolumny `c_*` pliku K18b na binarce pinu `e389edd3`.

## Uruchomienie

Na workerze (`~/R618` na `dev/muro` = R, build ręczny `scripts/buildrdb.sh conan ninja probe`, `cmake --install build/Release-Probe`, bo strażnik buildu nadzorcy nie zna `scripts/buildrdb/research.sh`):

```bash
./results_20261111_R618_K18c/run.sh --code-repo /home/michal/R618 --preflight-only
./results_20261111_R618_K18c/run.sh --code-repo /home/michal/R618
```

Na nadzorcy, po zatwierdzeniu exactness/replay:

```bash
./start_supervisor.sh rate_r618k18c \
  --experiment-id 20261111_R618_K18c \
  --experiment-branch experiment/20261111_R618 \
  --code-branch dev/muro \
  --code-repo <świeży klon dev/muro> \
  --worker 192.168.88.13 \
  --worker-code-repo /home/michal/R618 \
  --skip-build
```

## Stan

**POTWIERDZONY 2026-11-11** - wszystkie trzy warunki z kryteriów zachodzą na `dev/muro@16c516f9`, binarka Release-Probe z `~/R618` (SHA-256 `xretractor` `4c02e5c8571ea73512d5544829f3b09208925a9de6addb06fd0b012d968615ea`, `xqry` `20e80fe07537839ff7db1a5f641c2b842eb5dee621f3770a0b21c18450ed79ed`, `xtrdb` `763b911b2c68e90a52fa8b9ec1a59634a8ab391214f15c79b20db8953222416a`; binarki w `~/.local/bin` bajt w bajt równe buildowi; `--build-info`: 5 × `RDB_OPT_*=ON`, `RDB_BENCH_PROBE=ON`; `--help`: `Branch: dev/muro:16c516f9`, GCC 14.2.0).

1. exactness/replay (`exactness/`, commit `380b95f`): 2 przebiegi, 67 artefaktów, 51 identycznych bitowo, 16 `.meta` identycznych po pominięciu czasu utworzenia; zero różnic. Opisowo, poza kryterium: artefakty bez `.meta` są bajt w bajt równe artefaktom R593 K18b na `e389edd3`, a `configuration.sha256` jest ten sam;
2. round-trip: `a2 == a`, `b2 == b` bez rekordu zastępczego, `c[2i] == b[i]`, `c[2i+1] == a[i]`; rekordy a=19 999, b=19 999, c=39 994, a2=19 996, b2=19 997 (prefiksy >= 19 990), te same liczby co w R593 K18b i R593 K18 (`roundtrip_compare.txt` bajtowo równy K18b);
3. 360 Hz (`rate_r618k18c/study_01/`, commit `46555ab`): 19 999 interwałów w sondzie (żaden rekord nie zaginął), jeden klient `xqry` (pusty `xqry_1.err`), harness zakończony sukcesem, governor `performance` w czasie badania, `throttled=0x0`.

Liczby czasowe (opisowo, jeden przebieg na każdej rewizji). Plan 360 Hz jest tym samym tekstem co w R593 K18b i R593 K18, ale jeden przebieg nie wystarcza, by różnicę wobec nich przypisać silnikowi; w K18 plan był innym tekstem.

| Metryka | K18 `bc37186` | R593 K18 `dfcc42d2` | R593 K18b `e389edd3` | R618 K18c `16c516f9` |
|---|---|---|---|---|
| E1 mediana | 1312,4 µs | 885,7 µs | 916,4 µs | 851,6 µs |
| E1 p99 | 1617,9 µs | 1105,6 µs | 1115,7 µs | 1064,8 µs |
| E1 max | 1838,5 µs | 1303,0 µs | 1284,8 µs | 1225,9 µs |
| max E1 / budżet 2777,8 µs | - | 46,9% | 46,3% | 44,1% |
| queue-emission mediana | 1372,8 µs | 937,2 µs | 970,8 µs | 906,6 µs |
| queue-emission p99 | 1718,6 µs | 1211,1 µs | 1215,0 µs | 1168,8 µs |
| queue-emission p99,9 | 1832,5 µs | 1291,4 µs | 1276,5 µs | 1229,4 µs |
| queue-emission max | 1944,0 µs | 1420,3 µs | 1426,1 µs | 1351,5 µs |
| max queue-emission / budżet 2777,8 µs | 70,0% | 51,1% | 51,3% | 48,7% |
| wake_lag mediana / max | 20,7 / 54,3 µs | 22,2 / 71,2 µs | 22,3 / 69,6 µs | 22,3 / 106,0 µs |

Wobec R593 K18b wszystkie podane kwantyle E1 i queue-emission są niższe o 3,7-7,1%, a maksimum wake_lag wyższe (106,0 wobec 69,6 µs przy tej samej medianie 22,3 µs). Delta silnika (#617) dotyczy rachunku kompilatora, nie ścieżki wykonania ani IPC, a pomiar to jeden przebieg na każdej rewizji, więc tych różnic nie przypisuję silnikowi.

Stan workera: ostatni start ok. 10:05 (2026-11-11), potem build Release-Probe w `~/R618` (10:41-11:48), exactness 12:11-12:18 i badanie 360 Hz 12:22-12:23. Kampania ma jedno badanie, więc nadzorca nie restartował workera. W trakcie exactness i badania nikt poza nadzorcą nie łączył się z workerem: start `run.sh` przez `timeout 30 ssh` z procesem odczepionym, oczekiwanie lokalnym `sleep`, jedno logowanie po końcu (12:21), potem tylko sesje nadzorcy. Kolejność jak w R593 K18b (build, exactness, badanie).

Odstępstwa w przebiegu: brak poza znanym z R593 K18 i K18b - strażnik buildu nadzorcy (`grep 'build/Release-Probe' scripts/buildrdb.sh`) nadal nie zna `scripts/buildrdb/research.sh`, więc build był ręczny (`scripts/buildrdb.sh conan ninja probe`, `cmake --install build/Release-Probe`), a nadzorca szedł z `--skip-build` i weryfikacją zainstalowanej binarki. Wyniki exactness skopiowane z workera na nadzorcę i zacommitowane tam (`380b95f`); kopie na workerze porównane bajtowo z commitem przed synchronizacją gałęzi.
