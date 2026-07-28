# K18 — rewalidacja minimalnego zestawu danych artykułu po G1

Eksperyment jest wykonywany na kodzie RetractorDB z brancha `master`,
commit `bc37186ac87cb944d76cf74c7be92706a4a3a87f`
(`K19 - fix (#210)`). K18 nie używa osobnego brancha kodu silnika.

Branch wyników: `experiment/20260728_K18` w repozytorium
`rdb-experiment`.

## Cel

Na jednym przypiętym commicie silnika należy powtórzyć:

1. exactness/replay dwóch przebiegów potoku obejmującego 17 strumieni;
2. round-trip dwóch kanałów, w którym `a2 == a` i `b2 == b` bez rekordu
   zastępczego `Theta`;
3. jeden reprezentatywny przebieg czasowy 360 Hz.

Most SDF/CSDF wraz z `tail=` został już powtórzony przez K2/G3. K18 nie
powtarza tej zakończonej części.

## Realizacja

- harness exactness/replay zapisuje wyłącznie do tego repozytorium;
- preflight wymaga czystego `master` dokładnie na commicie `bc37186`;
- binarka musi być profilem Release-Probe z kompletem optymalizacji;
- stare oczekiwanie `a2[1:] == a` zostało zastąpione przez `a2 == a`;
- etap czasowy 360 Hz ma osobną, jednowierszową konfigurację
  `config/campaign_rate_k18.csv` (SHA-256:
  `69f82adac208cd1d3c05f8ef5d8eb5f01de220a774f9a9842a256bbe8d0eafaf`)
  i został wykonany przez nadzorcę.

## Wynik 2026-07-28

- exactness/replay: 67 artefaktów, zero różnic;
- round-trip: `a2 == a` i `b2 == b`, bez rekordu zastępczego;
- 360 Hz: 19 999 zmierzonych interwałów, jeden klient;
- E1: mediana 1312,4 µs, p99 1617,9 µs, maksimum 1838,5 µs;
- queue-emission latency: mediana 1372,8 µs, p99,9 1832,5 µs,
  maksimum 1944,0 µs;
- maksymalna queue-emission latency zajęła 70,0% budżetu slotu.

## Uruchomienie exactness/replay

Na workerze, po zbudowaniu `master@bc37186` profilem
`scripts/buildrdb.sh probe`:

```bash
./results_20260728_K18/run.sh --preflight-only
./results_20260728_K18/run.sh
```

Można wskazać niestandardowe ścieżki:

```bash
./results_20260728_K18/run.sh \
  --code-repo /home/michal/retractordb \
  --xretractor /home/michal/retractordb/build/Release-Probe/src/retractor/xretractor
```

Harness nie wykonuje `commit`, `push` ani operacji zmieniających repozytorium
kodu. Wyniki publikuje dopiero po przejściu wszystkich porównań.

## Uruchomienie reprezentatywnego przebiegu 360 Hz

Po zatwierdzeniu exactness/replay nadzorca uruchamia dokładnie jeden wiersz
konfiguracji K18:

```bash
./start_supervisor.sh rate_k18 \
  --experiment-id 20260728_K18 \
  --experiment-branch experiment/20260728_K18 \
  --code-branch master
```

Nadzorca ponownie przypina pełny commit kodu i zapisuje do README kampanii
zarówno branch `master`, jak i commit
`bc37186ac87cb944d76cf74c7be92706a4a3a87f`.
