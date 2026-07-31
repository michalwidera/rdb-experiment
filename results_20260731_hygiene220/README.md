# Badanie higieniczne `abe075e`: czy sonda E4 zmienia zachowanie silnika

**Predeklaracja.** Napisana i commitowana **przed** jakimkolwiek pomiarem.

## Cel

`abe075e` („sonda (#220)") dodaje liczniki pracy na slot (E4): odwiedziny elementów
okna, odczyty źródła, wykonania tokenów, wybory przeplotu, scalenia sum. Pytanie:

> **Czy ta zmiana unieważnia wyniki kampanii K6c zmierzone na `1bb2d2c`?**

Odpowiedź jest **warunkiem wstępnym** badania `results_20260731_instrument`, które
zestawia cechy zebrane na `abe075e` z celami `p99` zmierzonymi na `1bb2d2c`. Bez
wykazanego braku wpływu tamto zestawienie nie ma podstawy.

## Dlaczego to badanie ma kształt „równości artefaktów"

W tej kampanii badania higieniczne mają dwa kształty i wybór między nimi jest
merytoryczny, nie techniczny:

- `e1e5181` — **równość artefaktów**: zmiana mogła zmienić to, co silnik wylicza.
- `1bb2d2c` — **statystyka rozkładów czasów**: zmiana nie dotykała artefaktów,
  dotykała tego, co pracuje na mierzonym rdzeniu. Porównanie bajtów odpowiedziałoby
  „brak wpływu" i byłoby bezużyteczne.

Sonda E4 należy do **pierwszego** kształtu, i to z konkretnego powodu: badanie
`results_20260731_instrument` używa cech, które są **pochodną planu** (liczba
odwiedzin elementów wynika z geometrii okna). Zagrożeniem dla niego jest zmiana
planu albo wyliczanych wartości, a nie przesunięcie rozkładu czasu. Dlatego
mierzymy równość, a nie rozkłady.

**Czego to badanie świadomie NIE sprawdza — i dlaczego to jest w porządku tutaj.**
Liczniki inkrementują się wewnątrz mierzonej ścieżki (`processRows`), więc w buildzie
z sondą **dokładają pracę do budżetu slotu**. Tego narzutu to badanie nie mierzy.
Nie jest to potrzebne, bo `results_20260731_instrument` **nie mierzy czasu** — bierze
cele z K6c. Narzut sondy staje się pytaniem dopiero dla przyszłej kampanii, która
mierzyłaby czas na buildzie z E4, i wtedy wymaga badania drugiego kształtu
(statystycznego). Zapisane tutaj, żeby nikt nie wziął zielonego werdyktu tego
badania za dowód, że sonda jest darmowa czasowo. **Nie jest to wykazane.**

## Trzy warstwy porównania

| warstwa | co porównuje | status |
|---|---|---|
| 1. korpus | plany skompilowane z korpusu RQL: kształt planu, liczniki `R1`/`R2`, kody odrzuceń | przedmiot badania |
| 2. potoki | artefakty binarne i `.meta` po przebiegach | przedmiot badania |
| 3. klient | dwie wersje `xqry` przy stałym silniku | **kontrola** |

Warstwa 3 jest tu **kontrolą, nie przedmiotem**: `abe075e` nie dotyka klienta, więc
obie strony mają identyczny kod `xqry`. Wynik musi być identyczny. Gdyby nie był,
oznaczałoby to niedeterminizm harnessu — i wtedy zielonych warstw 1 i 2 też nie
wolno byłoby czytać. Ta warstwa nie jest pozostawiona przez zaniedbanie.

## Warunek ważności

Wejścia silnika (`*.rql`, `examples/`) muszą być identyczne między `1bb2d2c`
a `abe075e`. Sprawdzane przez `build_trees.sh` przed budową; różnica zatrzymuje
badanie, bo przestaje ono być porównaniem kodu silnika.

Oba drzewa budowane z `RDB_BENCH_PROBE=ON` — to build, którego faktycznie używa
kampania i badanie E4. Porównanie buildów bez sondy nie odpowiadałoby na zadane
pytanie, bo bez sondy liczniki nie istnieją.

## Kryterium — zamrożone

**Brak wpływu** wtedy i tylko wtedy, gdy jednocześnie:

1. zero różnic planu w korpusie, przy **niezerowej** liczbie porównanych plików,
2. zero zmian statusu kompilacji (nic, co kompilowało się, nie przestaje; nic
   odrzuconego nie zaczyna),
3. zero różnic liczników `R1`/`R2`,
4. zero różnic artefaktów w potokach, przy **niezerowej** liczbie ocenionych,
5. warstwa kontrolna klienta identyczna, przy **niezerowej** liczbie porównanych.

**Każde porównanie raportuje LICZBĘ porównanych rzeczy; zero jest błędem, nie
zgodnością.** Reguła wprowadzona po tym, jak wcześniejsze badanie przeszło
w milczeniu na pustym zbiorze.

**Przewidywanie zapisane przed pomiarem:** brak wpływu we wszystkich pięciu
punktach. Liczniki są zapisywane i nigdy nie czytane przez logikę silnika, a bez
`RDB_BENCH_PROBE` makro rozwija się do `((void)0)`. Przewidywanie jest częścią
predeklaracji i zostanie skonfrontowane z wynikiem niezależnie od tego, czy się
sprawdzi. **Wynik negatywny zatrzymuje badanie E4**, a nie prowadzi do korekty
sondy w locie.
