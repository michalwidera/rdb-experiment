# K18 — exactness/replay

Ta część eksperymentu używa RetractorDB z brancha `master`, commit
`bc37186ac87cb944d76cf74c7be92706a4a3a87f`.

## Zakres

- dwa identyczne przebiegi potoku QRS;
- 17 strumieni i 67 odpowiadających im plików artefaktów;
- dane, deskryptory i cienie porównywane bitowo;
- pliki `.meta` porównywane po pominięciu 8-bajtowego czasu utworzenia;
- round-trip `a#b`, a następnie `&` i `%`;
- wymagane `a2 == a` oraz `b2 == b` na wspólnych prefiksach.

`Theta` ma jednoslotowy ogon przyczynowy. Ogon wstrzymuje emisję i nie jest
rekordem zerowym ani rekordem all-null.

## Konfiguracja

Harness używa:

- `config/exactness-replay.rql` —
  `79098d5b193640f6aaaf7152cc37ae64b2f17f7f5ef8dfa49bc61711864e7135`;
- `config/exactness-roundtrip-write.rql` —
  `33345f14b8d1ddbc880792f91dd116ab684d6d2c2239d8f41f136a0e3f8eaf5f`;
- `config/exactness-roundtrip-read.rql` —
  `46636e4ad9c8e2b07b20ad2bbb4df830df6a4cfd0c3aea0a2a3891f81a3b3fd7`.

SHA-256 konfiguracji jest zapisywane przez `run.sh` do
`configuration.sha256` razem z surowymi logami, identyfikatorem binarki,
porównaniami i migawkami stanu.
