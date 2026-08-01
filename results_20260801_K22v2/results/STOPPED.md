# K22v2 — zatrzymanie

- etap: pierwszy przebieg kontrolny `base/F1`;
- dane wynikowe: brak;
- błąd: `xretractor` wywołany pełną ścieżką użył absolutnego `argv[0]` do
  nazwy blokady i próbował pisać w `/home/michal/.local/bin`;
- kod procesu: 37 (`no_lock_available`);
- dowód: `../evidence/raw/base_F1/rql_run.log` oraz log systemu;
- decyzja: nie zmieniać zamrożonej aparatury K22v2, przejść do K22v3.
