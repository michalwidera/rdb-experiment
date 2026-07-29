# K5 — workload wielozapytaniowy `Q = 1,2,4,8,16,32`, punkt go/no-go

**Predeklaracja.** Ten plik powstaje i jest commitowany **przed** wygenerowaniem
jakichkolwiek danych. Reguła decyzyjna z sekcji „Kryterium" jest zamrożona:
po pierwszym przebiegu nie wolno jej zmienić, doprecyzować ani uzupełnić o
dodatkowy warunek. Jeżeli okaże się źle postawiona, kampania kończy się
werdyktem „reguła nieadekwatna", a nie nową regułą.

## Cel

Odpowiedzieć na pytanie go/no-go z `paper-arXiv/debs/research_plan.md` §K5:

> Czy `ALGSTRUCT` usuwa węzły, których `STRUCT` nie usuwa?

oraz na pytanie recenzenta z luki G6: *jak korzyść skaluje się z liczbą
zapytań?* Kampania odpowiada na oba **w trybie compile-only, bez pomiaru
czasu**.

## Czego ta kampania świadomie nie mierzy

Nie mierzy **żadnej** wielkości czasowej — ani czasu kompilacji, ani czasu CPU,
ani throughputu, ani opóźnień. Metryki czasowe z §9.2 należą do K6 i wymagają
workera pod PREEMPT_RT (`REQUIREMENTS.md` R7). K5 jest strukturalna, więc
wykonuje się lokalnie na nadzorcy i nie korzysta z nadzorcy pomiarowego
(`REQUIREMENTS.md`, akapit „Zakres").

Konsekwencja jest wiążąca: gdyby do wyników K5 dopisać choć jedną metrykę
czasową, kampania przestałaby spełniać własne warunki wykonania i byłaby
nieważna.

## Profile

Pięć profili z K4, bez zmian (`profiles.tsv`). Kryterium porównuje `STRUCT`
z `ALGSTRUCT`; trzy pozostałe służą wyłącznie atrybucji, który człon odpowiada
za zaobserwowaną różnicę.

| Profil | dedup | share | commutative (R2) | factor (R1) |
|---|---|---|---|---|
| `OFF` | OFF | OFF | OFF | OFF |
| `STRUCT` | ON | ON | OFF | OFF |
| `STRUCT+R1` | ON | ON | OFF | ON |
| `STRUCT+R2` | ON | ON | ON | OFF |
| `ALGSTRUCT` | ON | ON | ON | ON |

Wszystkie budowane w Release z `RDB_BENCH_PROBE=ON`; `--build-info` jest
porównywane bajtowo z oczekiwaniem i rozbieżność zatrzymuje przebieg.

## Rodziny workloadów

Rodziny odpowiadają liście z §9.2. Kolumna „mechanizm" podaje, dlaczego dana
rodzina ma dać taki, a nie inny wynik — zapisana **przed** przebiegiem, żeby
wynik niezgodny z przewidywaniem był rozpoznawalny jako niespodzianka, a nie
dopasowany po fakcie.

| | Rodzina | Konstrukcja | Parametr | Przewidywanie i mechanizm |
|---|---|---|---|---|
| W1 | pojedyncza instancja reguły | `(A>2)#(B>1)` | — | R1 odpala raz; dwa substraty przesunięć zastąpione jednym węzłem przeplotu |
| W2 | **`Q` zapytań ze wspólnym `phi(A,B)`** | `Q` × `(A>2)#(B>1)` | `Q` | rdzeń K5; `r1 = Q`, jeden wspólny przeplot dla wszystkich konsumentów |
| W3 | głębokość wspólnego podplanu | zagnieżdżone `((phi>2)#(C>1))` | `d = 1,2,3` | każdy poziom zagnieżdżenia daje własne przepisanie |
| W4 | kosztowny operator za wspólnym podplanem | okno `@(1,30)` + `.avg` nad `phi` | `Q` | struktura jak W2; rodzina istotna dopiero dla K6 |
| W5 | **kontrola negatywna — brak wspólności** | `Q` × `A_j#B_j`, bez przesunięć | `Q` | brak `STREAM_TIMEMOVE` ⇒ wzorzec R1 niedopasowany; oczekiwane `net = 0` |
| W6 | near-miss | `(A>1)#(B>1)`, `i·Δ_A ≠ k·Δ_B` | `Q` | warunek wymierności niespełniony; oczekiwane `net = 0` |
| W7 | materializacja blokuje rewrite | przesunięcia jako **publiczne** strumienie | `Q` | `matchTimeMove` wymaga `isSubstrat`; oczekiwane `net = 0` |
| W8 | **umotywowana zewnętrznie** | potok Pan-Tompkins `rec205` + `Q` pochodnych monitorów nad `(mlii>29)#(mwi>29)` | `Q` | wspólny wyrównany przeplot powstaje z konstrukcji zapytań, nie z konstruktora benchmarku |

`Q ∈ {1, 2, 4, 8, 16, 32}`.

W8 odpowiada na lukę G7 (*„czy to nie jest benchmark skonstruowany pod waszą
optymalizację?"*). Opóźnienie 29 próbek to sumaryczne opóźnienie grupowe potoku
Pan-Tompkins (filtr 25-tap → 12, różniczka 5-tap → 2, okno całkujące 30 → 15).
Monitor porównujący surowy sygnał z obwiednią **musi** wyrównać oba kanały o tę
wartość, więc przesunięty przeplot nie jest tu wyborem autora workloadu.

## Metryki

Wyłącznie strukturalne, wszystkie odczytywane z kompilacji `xretractor w.rql -c`:

1. **Zbiór nazw węzłów** planu wyjściowego, wyodrębniony ze zrzutu planu.
   Jest to metryka pierwotna, bo pytanie K5 dotyczy węzłów, nie liczb.
2. Czwórka `PLAN bench`: publiczne / substraty / tokeny-from / tokeny-pól,
   w czterech punktach potoku kompilacji (wejście, przed dedup, po dedup,
   wyjście).
3. Liczniki `REWRITE_APPLIED r1 / r2`.

Wyjście kompilatora **nie** jest hashowane w całości: zawiera ścieżki
bezwzględne katalogu roboczego, przez co jest nieodtwarzalne między
przebiegami (skaza `results_20260728_K4/collect.py` odnotowana w `JOURNAL.md`).
Hashowany jest znormalizowany zbiór nazw węzłów.

## Kryterium — reguła decyzyjna

Dla każdej pary (workload `w`, parametr `Q`) i profilu `P` niech `N_P(w,Q)`
będzie zbiorem nazw węzłów planu wyjściowego (strumienie publiczne i substraty;
dyrektywy `:STORAGE` i `:SUBSTRAT` wyłączone). Definiujemy:

```
usuniete(w,Q) = N_STRUCT(w,Q) \ N_ALGSTRUCT(w,Q)
dodane(w,Q)   = N_ALGSTRUCT(w,Q) \ N_STRUCT(w,Q)
net(w,Q)      = |N_ALGSTRUCT(w,Q)| - |N_STRUCT(w,Q)|
```

**GO** wtedy i tylko wtedy, gdy zachodzą łącznie:

- **(a)** istnieje `(w,Q)` z `net(w,Q) < 0`, przy czym zbiór `usuniete(w,Q)`
  jest wypisany imiennie w wynikach;
- **(b)** dla każdego takiego `(w,Q)` kontrola semantyczna daje wynik **bajtowo
  identyczny** pod `STRUCT` i `ALGSTRUCT`;
- **(c)** `net(w,Q) = 0` dla wszystkich `Q` w rodzinach W5, W6 i W7.

**NO-GO** w każdym innym przypadku.

Warunek (c) jest warunkiem koniecznym GO: reguła, która „usuwa węzły" także
tam, gdzie nie ma czego usuwać, usuwa je niepoprawnie.

**Kwalifikator zewnętrznej motywacji.** Jeżeli GO zachodzi, ale **żadne**
`(w,Q)` spełniające (a) nie należy do rodziny W8, werdykt jest zapisywany jako
**„GO warunkowe"** wraz z jawnym stwierdzeniem, że korzyść wykazano wyłącznie
na workloadach syntetycznych i luka G7 pozostaje otwarta.

**Skalowanie (G6)** — raportowane, ale **nieuwzględniane** w regule
decyzyjnej: czy `|net(w,Q)|` oraz oszczędność tokenów rosną z `Q`. Brak
wzrostu nie jest podstawą do NO-GO; jest wynikiem, który należy zaraportować
tak samo jak wzrost.

**Próg istotności praktycznej** nie ma tu zastosowania: metryki są dokładnymi
licznościami, a nie wielkościami obarczonymi szumem. Próg 10 % z §K6 dotyczy
kampanii czasowej.

## Kontrola semantyczna

Sama redukcja liczby węzłów nie odróżnia optymalizacji od zepsucia planu, więc
dla reprezentatywnych przypadków wykonywany jest krótki przebieg
(`xretractor w.rql -r -k -m N`) pod `STRUCT` i `ALGSTRUCT`, a artefakty
wynikowe są porównywane bajtowo. Pliki `.meta` porównywane są bez ośmiobajtowego
nagłówka, który zawiera znacznik czasu utworzenia.

## Wynik negatywny

Werdykt NO-GO jest wynikiem, nie porażką kampanii, i zostaje zapisany w
`JOURNAL.md` na równi z pozytywnym. Zgodnie z §K5 planu badawczego pociąga za
sobą przeprofilowanie artykułu na experience paper o determinizmie
i egzaktności na edge.

## Higiena procesu

- Repozytorium kodu jest wyłącznie źródłem; żaden plik wynikowy nie powstaje
  wewnątrz niego (`REQUIREMENTS.md` R2). Kompilacje idą w kopii roboczej poza
  repozytorium, a przebieg weryfikuje czystość `git status` przed i po.
- Commit kodu jest przypięty w `run.sh` i sprawdzany; jego zmiana zatrzymuje
  przebieg.
- Wyniki, manifest i wpis dziennika trafiają wyłącznie na branch
  `experiment/20260729_K5` repozytorium `rdb-experiment`.
