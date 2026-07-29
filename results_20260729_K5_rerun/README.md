# K5 (powtórka) — workload wielozapytaniowy `Q = 1,2,4,8,16,32`, punkt go/no-go

**Predeklaracja.** Ten plik powstaje i jest commitowany **przed** wygenerowaniem
jakichkolwiek danych tej kampanii. Reguła decyzyjna jest zamrożona: po pierwszym
przebiegu nie wolno jej zmienić ani doprecyzować.

## Dlaczego powtórka

Pierwsza kampania (`results_20260729_K5/`) została **zatrzymana decyzją
człowieka przed rozstrzygnięciem go/no-go**, ponieważ ujawniła wadę silnika
niezależną od badanych reguł: `resolveStreamIntervals` odrzucał plany
bezcykliczne zależnie od kolejności w planie. Wada została naprawiona
(branch `issue_213-defect-interval`, scalona do `master` jako `Fix (#214)`),
a eksperyment powtórzony na naprawionym kodzie.

Katalog pierwszej kampanii pozostaje nietknięty (`REQUIREMENTS.md` R3). Jego
wyniki **nie** są przenoszone tutaj — ta kampania rozstrzyga od nowa.

### Co zmienia się względem pierwszej kampanii

1. **Commit kodu:** `2a5aa86` zamiast `0e0f701`.
2. **Rodzina W4 wraca do pierwotnej postaci** wymaganej przez §9.2 —
   „kosztowny operator **za** wspólnym podplanem", czyli okno `@(1,30)`
   i agregat `.avg` w osobnych strumieniach pochodnych. W pierwszej kampanii
   musiała być przekonstruowana, bo trafiała w naprawioną już wadę.
3. **Warunek (b) jest zdefiniowany precyzyjnie** — patrz niżej.

## Czego ta kampania świadomie nie mierzy

Nie mierzy żadnej wielkości czasowej. Metryki czasowe z §9.2 należą do K6
i wymagają workera pod PREEMPT_RT (`REQUIREMENTS.md` R7). K5 jest strukturalna,
wykonuje się lokalnie i nie korzysta z nadzorcy pomiarowego.

## Profile

Pięć profili z K4, bez zmian (`profiles.tsv`). Kryterium porównuje `STRUCT`
z `ALGSTRUCT`; pozostałe służą atrybucji.

| Profil | dedup | share | commutative (R2) | factor (R1) |
|---|---|---|---|---|
| `OFF` | OFF | OFF | OFF | OFF |
| `STRUCT` | ON | ON | OFF | OFF |
| `STRUCT+R1` | ON | ON | OFF | ON |
| `STRUCT+R2` | ON | ON | ON | OFF |
| `ALGSTRUCT` | ON | ON | ON | ON |

Wszystkie w Release z `RDB_BENCH_PROBE=ON`; `--build-info` weryfikowane
bajtowo. Katalogi budowy mają przedrostek `K5r-`, żeby nie użyć binarki
zbudowanej ze starego commitu.

## Rodziny workloadów

| | Rodzina | Konstrukcja | Parametr | Przewidywanie i mechanizm |
|---|---|---|---|---|
| W1 | pojedyncza instancja reguły | `(A>2)#(B>1)` | — | R1 odpala raz |
| W2 | **`Q` zapytań ze wspólnym `phi(A,B)`** | `Q` × `(A>2)#(B>1)` | `Q` | rdzeń K5; `r1 = Q`, jeden wspólny przeplot |
| W3 | głębokość wspólnego podplanu | zagnieżdżone `((phi>2)#(S>1))` | `d = 1,2,3` | każdy poziom daje własne przepisanie |
| W4 | kosztowny operator za wspólnym podplanem | `phi → projekcja → @(1,30) → .avg` | `Q` | struktura jak W2; rodzina istotna dla K6 |
| W5 | **kontrola negatywna — brak wspólności** | `Q` × `A_j#B_j`, bez przesunięć | `Q` | brak `STREAM_TIMEMOVE` ⇒ wzorzec niedopasowany; `net = 0` |
| W6 | near-miss | `(A>1)#(B>1)`, `i·Δ_A ≠ k·Δ_B` | `Q` | warunek wymierności niespełniony; `net = 0` |
| W7 | materializacja blokuje rewrite | przesunięcia jako **publiczne** strumienie | `Q` | `matchTimeMove` wymaga `isSubstrat`; `net = 0` |
| W8 | **umotywowana zewnętrznie** | potok Pan-Tompkins `rec205` + `Q` monitorów nad `(mlii>29)#(mwi>29)` | `Q` | wspólny wyrównany przeplot wynika z konstrukcji zapytań |

`Q ∈ {1, 2, 4, 8, 16, 32}`. Opóźnienie 29 próbek w W8 to sumaryczne opóźnienie
grupowe potoku (25-tap → 12, 5-tap → 2, okno 30 → 15).

## Metryki

Wyłącznie strukturalne, z kompilacji `xretractor w.rql -c`:

1. **Zbiór nazw węzłów** planu wyjściowego — metryka pierwotna.
2. Czwórka `PLAN bench` w czterech punktach potoku kompilacji.
3. Liczniki `REWRITE_APPLIED r1 / r2`.

Hashowany jest znormalizowany zbiór nazw węzłów, nie całe wyjście — to ostatnie
zawiera ścieżki bezwzględne katalogu roboczego.

## Kryterium — reguła decyzyjna

Dla pary (workload `w`, parametr `Q`) i profilu `P` niech `N_P(w,Q)` będzie
zbiorem nazw węzłów planu wyjściowego (strumienie publiczne i substraty;
dyrektywy wyłączone):

```
usuniete(w,Q) = N_STRUCT(w,Q) \ N_ALGSTRUCT(w,Q)
dodane(w,Q)   = N_ALGSTRUCT(w,Q) \ N_STRUCT(w,Q)
net(w,Q)      = |N_ALGSTRUCT(w,Q)| - |N_STRUCT(w,Q)|
```

**GO** wtedy i tylko wtedy, gdy łącznie:

- **(a)** istnieje `(w,Q)` z `net(w,Q) < 0`, a zbiór `usuniete(w,Q)` jest
  wypisany imiennie;
- **(b)** dla każdego takiego `(w,Q)` **wynik jest zachowany** w rozumieniu
  zdefiniowanym poniżej;
- **(c)** `net(w,Q) = 0` dla wszystkich `Q` w rodzinach W5, W6 i W7.

**NO-GO** w każdym innym przypadku.

**Kwalifikator zewnętrznej motywacji.** Jeżeli GO zachodzi, ale żadne `(w,Q)`
spełniające (a) nie należy do W8, werdykt brzmi **„GO warunkowe"** z jawnym
stwierdzeniem, że luka G7 pozostaje otwarta.

### Definicja „wynik zachowany" w warunku (b)

Porównaniu podlegają artefakty strumieni **nazwanych przez użytkownika**
(źródła `DECLARE` i wyjścia `SELECT`). Substraty są wyłączone: ich nazwy
generuje kompilator i to właśnie ich zmiana **jest** optymalizacją, więc
wymaganie ich zgodności czyniłoby (b) niespełnialnym zawsze, gdy reguła
zadziała.

Warunek (b) jest spełniony dla `(w,Q)`, gdy łącznie:

1. zbiór artefaktów strumieni nazwanych przez użytkownika jest identyczny pod
   `STRUCT` i `ALGSTRUCT`;
2. **pliki danych** tych strumieni są identyczne co do bajtu;
3. **pliki `.meta`** są identyczne co do bajtu po pominięciu ośmiobajtowego
   nagłówka zawierającego znacznik czasu utworzenia;
4. **pliki `.desc`** są identyczne co do bajtu **z jednym wyjątkiem**: różnica
   wyłącznie w wartości pola `RETMEMORY` nie narusza (b), ale **musi zostać
   wypisana imiennie** w wynikach. Różnica w jakimkolwiek innym miejscu `.desc`
   — nazwie pola, typie, długości, liczności, polityce `TYPE` — narusza (b).

**Ujawnienie.** Punkt 4 jest doprecyzowaniem wprowadzonym **po** pierwszej
kampanii i **z jej powodu**. Ujawniła ona, że `RETMEMORY` to wyliczona
pojemność historii (`computeRequiredCapacities`) — parametr zasobowy, który
z definicji zmienia się, gdy zmienia się kształt planu, i który trafia do
deskryptora strumienia widocznego dla użytkownika. Pierwsza kampania nie
rozstrzygnęła, czy należy on do „wyniku"; rozstrzygnięcie zapada **tutaj,
przed danymi**, i brzmi: nie należy. Kontekst i oba czytania:
`../results_20260729_K5/verdict_open_question.md`.

Doprecyzowanie zawęża warunek (b) w jednym, nazwanym z góry miejscu i w niczym
innym. Każda inna rozbieżność — łącznie z dowolną inną zmianą w `.desc` —
nadal daje NO-GO.

**Skalowanie (G6)** — raportowane, ale **nieuwzględniane** w regule decyzyjnej:
czy `|net|` oraz oszczędność tokenów rosną z `Q`. Brak wzrostu jest wynikiem do
zaraportowania, nie podstawą do NO-GO.

**Próg istotności praktycznej** nie ma zastosowania — metryki są dokładnymi
licznościami, nie wielkościami z szumem.

## Wynik negatywny

NO-GO jest wynikiem, nie porażką kampanii, i trafia do `JOURNAL.md` na równi
z pozytywnym. Zgodnie z §K5 pociąga za sobą przeprofilowanie artykułu na
experience paper.

## Higiena procesu

- Repozytorium kodu jest wyłącznie źródłem; kompilacje idą w kopii roboczej
  poza nim, a przebieg weryfikuje czystość `git status` przed i po
  (`REQUIREMENTS.md` R2).
- Commit kodu przypięty w `run.sh`; jego zmiana zatrzymuje przebieg.
- Wyniki trafiają wyłącznie na branch `experiment/20260729_K5`.
