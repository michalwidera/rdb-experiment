# Wada instrumentu w pierwszym przebiegu kontroli semantycznej

**Data:** 2026-07-29. **Dotyczy:** warunku (b) reguły decyzyjnej.
**Reguła decyzyjna NIE została zmieniona.** Zmieniono wyłącznie skrypt, który
ją wylicza.

Ten plik powstaje, ponieważ poprawka została wprowadzona **po** zobaczeniu
werdyktu NO-GO. Taka kolejność zawsze jest podejrzana i musi być
udokumentowana, żeby czytelnik mógł ocenić ją sam, a nie przyjąć na słowo.

## Co się stało

Pierwszy przebieg `run.sh` dał **NO-GO**: warunki (a) i (c) spełnione,
kwalifikator W8 spełniony, warunek (b) niespełniony dla wszystkich 22
przypadków z `net < 0`. Surowy wynik tego przebiegu jest zachowany w
`results/semantic_run1_instrument_defect.json`.

Przyczyną nie była żadna rozbieżność wyniku, tylko zbyt szeroki zakres
porównania. `semantic.py` porównywał **wszystkie** pliki w katalogu wyjściowym,
łącznie z sidecarami `.desc` i `.meta` substratów. Dla `W2_Q04`:

| STRUCT | ALGSTRUCT |
|---|---|
| `A.desc`, `B.desc` | `A.desc`, `B.desc` |
| `STREAM_TIMEMOVE_A.desc`, `STREAM_TIMEMOVE_A.meta` | `STREAM_HASH_A_B.desc`, `STREAM_HASH_A_B.meta` |
| `STREAM_TIMEMOVE_B.desc`, `STREAM_TIMEMOVE_B.meta` | — |
| `w2_out_000..003` + `.desc` + `.meta` + `.shadow` | `w2_out_000..003` + `.desc` + `.meta` + `.shadow` |

Strumienie publiczne są po obu stronach identyczne co do zestawu. Różnią się
wyłącznie nazwy substratów — a zastąpienie `STREAM_TIMEMOVE_A` i
`STREAM_TIMEMOVE_B` węzłem `STREAM_HASH_A_B` **jest** treścią reguły R1.

## Dlaczego to jest wada, a nie przesuwanie bramki

Porównanie obejmujące substraty czyni warunek (b) **niespełnialnym z definicji
zawsze wtedy, gdy reguła w ogóle zadziała**. Każdy przypadek z `net < 0` musi
mieć inny zestaw węzłów wewnętrznych — inaczej `net` nie byłby ujemny. Test
skonstruowany tak, że zawodzi dokładnie wtedy, gdy mierzone zjawisko wystąpi,
nie mierzy zachowania wyniku; mierzy sam siebie.

Sprawdzianem jest kierunek błędu. Wadliwy instrument dawał NO-GO tam, gdzie
optymalizacja działała — czyli **przeciw** hipotezie autora. Poprawka usuwa
błąd systematyczny, którego znak jest niekorzystny dla poprawiającego, co jest
sytuacją odwrotną do przesuwania bramki. Gdyby wada działała w drugą stronę —
przepuszczała rozbieżności — poprawianie jej po zobaczeniu wyniku byłoby
nieuprawnione bez powtórzenia całej kampanii.

Dodatkowo: błędne założenie było zapisane wprost w docstringu skryptu
(„substraty nie trafiają na dysk, `SUBSTRAT 'memory'`"), czyli istniało
**przed** przebiegiem i było falsyfikowalne. Nie zostało dobrane pod wynik.

## Poprawka

`compare()` porównuje artefakty strumieni **nazwanych przez użytkownika** —
źródeł `DECLARE` i wyjść `SELECT`, wydobytych z `query.rql` wyrażeniem
`\bSTREAM\s+([A-Za-z_]\w*)`. Zbiór tych plików musi być identyczny, a każdy
plik zgodny co do bajtu (`.meta` bez ośmiobajtowego nagłówka z czasem
utworzenia). Liczba pominiętych artefaktów wewnętrznych jest raportowana po
obu stronach, żeby pominięcie było widoczne, a nie ciche.

Substraty pozostają poza porównaniem bajtowym, ale **nie** poza kontrolą:
ich zbiór jest metryką pierwotną kampanii i to on wyznacza `net`,
`usuniete` i `dodane` w `comparison.csv`.

## Co pozostało nietknięte

Kolektor, metryki strukturalne i dane z pierwszego przebiegu nie zmieniły się —
poprawka dotyczy wyłącznie `semantic.py`. Warunki (a) i (c) oraz kwalifikator
W8 mają w obu przebiegach identyczne wartości.
