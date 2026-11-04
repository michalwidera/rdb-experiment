# Manifest eksperymentu 20261104_R593_K18

- utworzono: 2026-11-04T09:53:43+01:00
- branch wynikow: `experiment/20261103_R593`
- baza repozytorium wynikow: `3d5c26b6d6454e2f2c0e04726df98428fd615d6f`
- repozytorium kodu: `git@github.com:michalwidera/retractordb.git`
- branch kodu: `dev/muro`
- commit kodu: `dfcc42d2a5fee2efa0b531d682766e4b7b9b73bb`
- worker: `192.168.88.13:22` (hostname: `pi400`)
- adres zadany nadzorcy: `192.168.88.13`
- siec wykrywania: `automatycznie wywnioskowana /24`

Katalog jest docelowy. Wyniki nie podlegaja rotacji ani przenoszeniu.

## Podejscie 1 - przerwane przed buildem

- 2026-11-04T09:53:48+01:00: nadzorca zatrzymal sie na strazniku `grep -q 'build/Release-Probe' scripts/buildrdb.sh`; w `dfcc42d2` kod profilu jest w `scripts/buildrdb/research.sh`, wiec straznik nie znajduje napisu, choc `scripts/buildrdb.sh probe` buduje `build/Release-Probe`. Nic nie zostalo zmierzone ani zainstalowane; katalog `rate_r593k18/` z commita przygotowawczego `2993d98` usuniety, zeby nadzorca mogl ruszyc ponownie.
- Zamiast galezi buildu nadzorcy: ten sam `build/Release-Probe` z `~/R593` @ `dfcc42d2` (zbudowany 08:40-09:45 przez `scripts/buildrdb.sh conan ninja probe`, `ninja: no work to do`) zainstalowany recznie `cmake --install build/Release-Probe`; `xretractor`, `xqry`, `xtrdb` w `~/.local/bin` bajt w bajt rowne buildowi, `verify_probe_binary` OK, SHA-256 `xretractor` `014cb89fea5bd17b...`, `xqry` `a720ac4f59d79419...`. Podejscie 2: `start_supervisor.sh ... --skip-build`.
