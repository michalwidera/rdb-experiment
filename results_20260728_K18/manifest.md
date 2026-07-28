# Manifest eksperymentu K18

- identyfikator: `20260728_K18`
- branch wyników: `experiment/20260728_K18`
- baza repozytorium wyników: `0b32781db94cc59ad51b71c399441044fbcd65e3`
- repozytorium kodu: `retractordb`
- branch kodu: `master`
- commit kodu: `bc37186ac87cb944d76cf74c7be92706a4a3a87f`
- profil binarki: `Release-Probe`, wszystkie optymalizacje `ON`
- stan: zakończony sukcesem 2026-07-28

Repozytorium kodu pozostało tylko do odczytu. Wyniki należą wyłącznie do
brancha `experiment/20260728_K18` w `rdb-experiment`.

## Uruchomienie kampanii rate_k18

- utworzono: 2026-07-28T15:05:48+02:00
- kampania wykonawcza: `rate_k18`
- worker: `192.168.88.21:22` (hostname: `pi400`)
- adres zadany nadzorcy: `192.168.88.21`
- siec wykrywania: `automatycznie wywnioskowana /24`

## Wynik

- exactness/replay: sukces, 67 artefaktów, zero różnic;
- round-trip: `a2 == a` i `b2 == b`, bez rekordu zastępczego;
- 360 Hz: sukces, 19 999 zmierzonych interwałów;
- E1: mediana 1312,4 µs, p99 1617,9 µs, maksimum 1838,5 µs;
- queue-emission latency: mediana 1372,8 µs, p99,9 1832,5 µs,
  maksimum 1944,0 µs;
- maksimum queue-emission latency wykorzystuje 70,0% budżetu 2777,8 µs.
