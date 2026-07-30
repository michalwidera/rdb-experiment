# Pomiar: klient `xqry` kończy się przed silnikiem

Sekwencja odtworzona dokładnie jak w `worker/run_ablation_study.sh`
(`sleep 2` → start `xqry -s <stream> -r` → `sleep 1` → kontrola), w `/dev/shm`,
poza oboma repozytoriami. Profil `STRUCT`, o ile nie zaznaczono inaczej.

| komórka | `slots` | czas silnika | stan klienta po 3 s | kod wyjścia klienta | silnik w tym momencie |
|---|---:|---:|---|---:|---|
| `W2_Q32` | 720 | 6131 ms | żyje | — | działa |
| `W3_d1` | 2880 | 6098 ms | żyje | — | działa |
| `W3_d3` | 2880 | 3053 ms | martwy | 10 | **już skończył** |
| `W4_Q08` | 400 | 6806 ms | żyje | — | działa |
| `W9_Q32` | 720 | 12174 ms | żyje | — | działa |
| `W8_Q01` | 2880 | 4108 ms | żyje | — | działa |
| `W8_Q08` | 2880 | 6419 ms | **martwy** | **4** | **działa** |
| `W8_Q32` | 2880 | 10647 ms | **martwy** | **4** | **działa** |
| `W8_Q32` (`ALGSTRUCT`) | 2880 | 12170 ms | **martwy** | **0** | **działa** |

## Dwa różne zjawiska

**`W3_d3` — koniec krótkiego przebiegu, nie awaria.** Silnik kończy 2880 slotów
w 3,05 s i zdejmuje pamięć współdzieloną; klient dostaje
`IPC::interprocess_exception` i wychodzi kodem 10 (`no_child_process`,
`qryLauncher.cpp:180`). Sonda ma komplet 2880 slotów — pomiar jest kompletny.

**`W8_Q08` i `W8_Q32` — klient ginie przy DZIAŁAJĄCYM silniku.** Silnik pracuje
jeszcze 3–9 sekund po zniknięciu klienta. Kod wyjścia nie jest stały: 4
(`interrupted`, gałąź `catch (std::exception)`, `qryLauncher.cpp:183`) albo 0.
`W8_Q01` przeżył. Zjawisko zależy od `Q` i jest niedeterministyczne.

## Dlaczego to nie jest oczekiwane zachowanie klienta

`xqry -s <stream> -r` nie jest klientem krótkotrwałym: `-r` to wyłącznie tryb
wyjścia („raw output mode", `qryLauncher.cpp:75`), a limit elementów `-m`
domyślnie wynosi **0**, czyli **brak limitu** (`qryLauncher.cpp:69`). Klient ma
czytać, dopóki serwer żyje. Wyjście po ~3 s przy serwerze pracującym 12 s nie
ma uzasadnienia w interfejsie.

## Konsekwencja dla pomiaru

Predeklaracja wymaga dokładnie jednego klienta `xqry` na przebieg, a
`e2e_ns` jest zdefiniowane jako queue-emission latency **do tego klienta**
(R10). Jeżeli klient znika po 3 sekundach przebiegu trwającego 12 sekund, to
przez pozostałe 9 sekund ścieżka emisji nie jest tym, co predeklaracja opisuje.
Metryka główna `compute_ns` jest mierzona wokół `processRows()` i tego nie
dotyczy, ale `e2e_ns` — owszem.

Dotyczy to **rodziny umotywowanej zewnętrznie (W8)**, czyli tej jedynej, która
zamyka lukę G7.

## Czego ten plik NIE rozstrzyga

Nie ustalono, czy przyczyna leży w kliencie, w warstwie IPC silnika, czy
w środowisku. Pełna diagnoza należy do osobnego `issue_NNN` z badaniem
higienicznym, nie do wnętrza kampanii.
