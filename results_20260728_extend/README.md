# 20260728_extend — audyt regresji pojemności AGSE i domknięcie luki pokrycia

## Powód powstania eksperymentu

Po zamknięciu K19, K18 i K4 w przykładzie `examples/ecg/rec205` wykryto, że
`ninja ecg-qrs` rysuje płaski sygnał detekcji QRS. Bisekcja wskazała commit
`bc37186ac87cb944d76cf74c7be92706a4a3a87f` (`K19 - fix (#210)`) — czyli
dokładnie tę rewizję, na której przypięto K18.

Błąd: w `compiler::computeRequiredCapacities`, gałąź `STREAM_AGSE`, pojemność
bufora źródła liczono jako `ceilR(retained)`, gdzie `retained` jest **odległością**
od rekordu najnowszego do najstarszego pola okna. Bufor musi pomieścić oba końce
zakresu, więc poprawna pojemność to odległość + 1. Gdy odległość wypada
całkowita — a wypada zawsze dla źródła o szerokości 1, bo dla AGSE zachodzi
`ratio = step/F` — pojemność była o jeden rekord za mała. Kołowy bufor `MEMORY`
nadpisywał wtedy najstarsze pole okna, a operator czytał w jego miejsce rekord
najnowszy. Poprawka: commit `3db781711a84c08ce794c3924aab533dba6fcbd1`.

Regresja jest obserwowalna wyłącznie w planach łączących politykę `MEMORY`
(`VOLATILE`) z oknem nad strumieniem **obliczanym**. Strumienie plikowe czytają
pełną historię z dysku, co defekt maskuje — i to jest powód, dla którego most
K19 go przepuścił.

Eksperyment nie jest powtórką K18/K19/K4. Odpowiada na trzy pytania:

1. czy wyniki zapisane 2026-07-28 są dotknięte i wymagają powtórki;
2. dlaczego zestaw, którym K19 uzasadnił twierdzenie o pojemności historii,
   nie wykrył błędu pojemności;
3. czy metryki czasowe zmierzone na wadliwej rewizji zmieniają się po poprawce.

## Badania

| Katalog | Worker | Pytanie |
|---|---|---|
| `coverage_gap/` | nie | Moc detekcyjna mostu K19 wobec realnego mutanta historycznego. |
| `artifact_diff/` | nie | Które artefakty z 2026-07-28 regresja zmieniła, a których nie tknęła. |
| `rate_extend/` | tak | Powtórka kampanii 360 Hz na poprawionej rewizji i porównanie z K18. |
| `exactness/` | tak | Determinizm artefaktów na poprawionej rewizji, w reżimie K18. |

`coverage_gap` i `artifact_diff` nie mierzą czasu, mają własny `run.sh` i nie
korzystają z nadzorcy. Budują trzy drzewa Debug z klonów repozytorium kodu
(`lib/build_trees.sh`), poza samym repozytorium kodu (R2):

- `FIXED` — commit `3db7817`;
- `MUTANT` — ten sam commit z **odwróconą wyłącznie silnikową** częścią poprawki;
- `HISTORICAL` — commit-rodzic `7942b78` bez zmian, czyli stan z epoki K19.

`MUTANT` i `HISTORICAL` mają bajtowo identyczny kod silnika i różnią się wyłącznie
zestawem testów. Różnica ich wyników jest więc różnicą mocy detekcyjnej testów,
a nie wersji kodu. Mutacja nie jest przepisana ręcznie: powstaje przez odwrotne
nałożenie różnicy commita poprawki ograniczonej do pliku silnika, więc nie może
rozjechać się z historią.

## Uruchomienie

Część semantyczna, na nadzorcy:

```bash
./results_20260728_extend/coverage_gap/run.sh
./results_20260728_extend/artifact_diff/run.sh
```

Kampania czasowa, przez nadzorcę:

```bash
./start_supervisor.sh rate_extend \
  --experiment-id 20260728_extend \
  --experiment-branch experiment/20260728_extend \
  --worker 192.168.88.21
```

Determinizm artefaktów, na workerze, po zbudowaniu profilu probe:

```bash
./results_20260728_extend/run_exactness.sh --preflight-only
./results_20260728_extend/run_exactness.sh
```
