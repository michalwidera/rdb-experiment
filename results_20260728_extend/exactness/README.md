# exactness/replay na rewizji z poprawką pojemności AGSE

Badanie powtarza procedurę `results_20260728_K18/exactness` na commicie
`3db781711a84c08ce794c3924aab533dba6fcbd1`, w tym samym reżimie: binarka
Release-Probe, katalog roboczy w `/dev/shm`, 20 000 próbek, dwa niezależne
przebiegi potoku `config/exactness-replay.rql` (17 strumieni, 67 artefaktów).

Poza determinizmem na nowej rewizji wykonywane jest **porównanie między
rewizjami**: hashe artefaktów są zestawiane wprost z zapisanymi w
`results_20260728_K18/exactness/replay_hashes_run1.txt`. To jest właściwy dowód,
że poprawka nie ruszyła artefaktów plikowych — mocniejszy niż lokalny audyt
Debug w `artifact_diff/`, bo wykonany w tym samym reżimie pomiarowym i na tej
samej liczbie próbek co oryginał.

Pliki `.meta` są z porównania międzyrewizyjnego wyłączone z konstrukcji: ich
nagłówek zawiera znacznik czasu utworzenia, więc różnią się między dowolnymi
dwoma przebiegami. Determinizm `.meta` jest sprawdzany osobno, wewnątrz jednej
rewizji, przez porównanie run1/run2 po odcięciu 8 bajtów nagłówka.

Uruchomienie na workerze, po zbudowaniu profilu probe przez nadzorcę:

```bash
./results_20260728_extend/run_exactness.sh --preflight-only
./results_20260728_extend/run_exactness.sh
```
