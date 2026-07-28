# S2 — audyt roznicowy regresji pojemnosci AGSE

- data: 2026-07-28T20:51:40+02:00
- FIXED: `3db781711a84c08ce794c3924aab533dba6fcbd1` (Debug)
- MUTANT: ten sam commit z odwrocona silnikowa czescia poprawki (Debug)
- samples: 4000

## A. Korpus RQL — plan i kod zakonczenia

```

plikow RQL: 81
identyczny plan + rc: 81
rozne: 0 []
```

## B. Artefakty potoku exactness-replay (17 strumieni)

- porownanych plikow: 67
- roznych: 0

Pelna lista: `raw/replay_compare.txt`.

## C. Plan z polityka MEMORY (rec205-qrs.rql)

```
rekordow: fixed=3759 mutant=3759
mlii-900     fixed[min=5 max=310]  mutant[min=5 max=310]
mwi*5        fixed[min=0 max=15]  mutant[min=0 max=0]
detekcja*5   fixed[min=0 max=15]  mutant[min=0 max=0]
probek z detekcja>0: fixed=563 mutant=0
```
