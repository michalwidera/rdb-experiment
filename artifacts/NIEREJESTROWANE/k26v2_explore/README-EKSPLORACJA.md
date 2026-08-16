# EKSPLORACJA — to NIE jest wynik kampanii

Katalog powstał 2026-08-14 wyłącznie po to, żeby odpowiedzieć na pytanie
decyzyjne: **czy warto wydać kolejne ~48 h pracy workera na K26v3.**

## Czego tu NIE wolno zrobić

1. **Nie wolno cytować tych liczb w artykule** ani nigdzie, gdzie mogłyby zostać
   odczytane jako wynik H9.
2. **Nie wolno wpisywać ich do dokumentów kampanii** w `paper-arXiv/debs/` jako
   rezultatu — kampania K26v2 ma jeden ważny werdykt i brzmi on
   **BRAK WERDYKTU** (`/home/michal/k26v2_p9/VERDICT.txt`).
3. **Nie wolno traktować zgodności tych liczb z K26v3 jako potwierdzenia.**
   Jeśli K26v3 da to samo, będzie to wynik K26v3 — nie „replikacja".

## Dlaczego to nie jest wynik

Reguły decyzyjne D7 i D8 zostały tu poprawione **po zobaczeniu werdyktu, który
one same wydały**, i ze znajomością kierunku, w którym każda poprawka przesuwa
konkretną rodzinę. To jest podręcznikowa definicja analizy eksploracyjnej.
Dane P8 są te same, więc powtórzenie analizy nie przywraca prospektywności.

## Co zostało zmienione wobec kampanii

Dwie łatki, obie poza zamrożonym katalogiem (`manifest` kampanii nietknięty):

| Defekt | Plik | Zmiana |
|---|---|---|
| D7 | `reduce_explore.py` | `rdb_instances()` w F9-R1 liczy `len(substrates)`, nie tylko węzły `STREAM_HASH_*` |
| D8 | `verdict_explore.py` | kontrola negatywna `Q=1` używa `abs(got_rdb) > CURVE_TOLERANCE` zamiast ścisłego `!= 0` |

Baza: `verdict_aneks4.py` (czyli z regułą podpisanego ANEKS-4).
`timing.tsv` i `gates.tsv` — bez zmian, skopiowane z `/home/michal/k26v2_p9/matrix/`.
`mechanism.tsv` przeliczony; różni się od kampanijnego **wyłącznie** kolumną
`instances` w wierszach ablacji F9-R1.

## Wynik eksploracji

`rc=0`, 3/3 rodziny `SUPPORT`. Pełny wypis: `VERDICT-EKSPLORACJA.txt`.

Znaczenie: przy naprawionej aparaturze **jest o co walczyć** — zmierzone dane
mieszczą się w predeklarowanych progach z zapasem, a nie na granicy. To jest
jedyny wniosek, jaki wolno z tego katalogu wyciągnąć.
