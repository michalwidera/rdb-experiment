# Manifest badania K22 (`REQUIREMENTS.md` R12)

| Pole | Wartość |
|---|---|
| Identyfikator eksperymentu | `results_20260801_K22` |
| Etap na dzień spisania | K22a — audyt i predeklaracja |
| Data | 2026-08-01 |
| Commit kodu (`retractordb`) | `dd733e3` (`master`, drzewo czyste) |
| Branch kodu | `master` |
| Bazowy commit wyników (`rdb-experiment`) | `91352d3` (`main`, drzewo czyste) |
| Branch wyników | `main`, commit K22a `3a46171` — **odstępstwo od R4**, patrz niżej |
| Commit planu (`paper-arXiv`) | `6375de5` (`main`, potomek `3d3e95a`) |
| Worker pomiarowy | **nieużywany** — K22 nie mierzy czasu |
| Adres workera | nie dotyczy |
| Hostname workera | nie dotyczy |
| Sieć wykrywania | nie dotyczy |

## Dlaczego brak workera

K22 jest badaniem **statycznym**: liczy konstrukcje w tekście programów
i porównuje strumienie kanoniczne. Nie mierzy czasu, przepustowości ani
zachowania real-time. Warunki wejściowe `REQUIREMENTS.md` R5 dotyczące workera,
`/dev/shm` i budowy pomiarowej **nie mają tu zastosowania**; obowiązują
natomiast warunki czystości obu repozytoriów, sprawdzone i spełnione.

Build pomiarowy (R6, `RDB_BENCH_PROBE=ON`) nie jest wymagany. Silnik będzie
potrzebny w K22b wyłącznie do dwóch rzeczy: wygenerowania strumieni kanonicznych
i odczytania `tail` przez `xretractor -t`.

## Provenance programów wejściowych

SHA-256 w chwili zamrożenia; pełna tabela z rolami w `PREDECLARATION.md` §1.

```text
8f55a162b7986fc77367f17b481c4ca45898578be5b15d6beb550e98356e13b3  retractordb:examples/ecg/rec205/rec205-qrs.rql
f0fbe8fce36851a49987e5535e08a35c7c1eb8caf5de36417153d18ff8574232  retractordb:examples/ecg/rec205/rec205-detect.rql
99e4619a07797822c5afd34bf9cb88d9bff8f9cd808b0faa0667d07645f978c2  retractordb:examples/ecg/rec205/bp_coef.txt
39c0f3bc6135e87acf72ebc0aa159dce329436665251fc2a9dc50d0625aa1c6c  retractordb:examples/ecg/rec205/d_coef.txt
81f7b58b81d0cee15590470b109a163e3102ae8755c253d1c26bdf99dddaa4cc  rdb-experiment:config/dsp-simple-fir.rql
88e1697a65428904ee1e8738b6be2eaf4f4fc3e3bc4e80f31cb7c233f8426a18  rdb-experiment:config/pan_tompkins_numpy.py
4cbb0f6105f7e65a6c1e73a391bcd8c25b6ee86fbe66f18129cbcbf6a0108b06  rdb-experiment:config/PanTompkinsFlinkJob.java
b7627f132146f0fc94f32319df921eeaf02e6b1b02937b3f2a9d6b31b3794b04  rdb-experiment:results_20260730_K6c/generate.py
```

## Semantyka odczytana z kodu silnika

Predeklaracja opiera arytmetykę na `retractordb@dd733e3`, z odniesieniami
plik:linia (`PREDECLARATION.md` §4). Odniesienia są częścią manifestu, bo
stanowią podstawę tabeli równoważności — recenzent musi móc je sprawdzić
bez uruchamiania kampanii.

Odnotowana i **naprawiona** rozbieżność dokumentacyjna w silniku: komentarz
`src/retractor/lib/compiler.cpp:958-960` twierdził, że wyciszenie emisji
w slotach ogona jest „osobnym krokiem", podczas gdy
`src/retractor/lib/dataModel.cpp:167` już je realizuje. Audyt K22a poprawił
**sam komentarz**; zmiana jest wyłącznie dokumentacyjna (bez wpływu na
zachowanie, `ut_compiler` i `ut_presenter` przechodzą) i nie narusza zakazu
zmiany silnika dla ułatwienia GO. Fakt o ogonie i tak ustala pomiar
(`xretractor -t`), nie komentarz.

**Skutek dla manifestu — rozliczony.** Poprawka jest w `retractordb` jako
`dd733e3` („fix comment", wypchnięte na `origin/master`), więc rewizja wejściowa
kampanii to `dd733e3`, nie `abe075e`. Wszystkie odwołania w tym katalogu zostały
przestawione na nowy SHA.

Sprawdzone przy przestawianiu: poprawka dodała jedną linię wewnątrz cytowanego
bloku komentarza, więc **żadne z pozostałych cytowań `plik:linia` nie uległo
przesunięciu**. Zweryfikowano wszystkie 17 odwołań (`expressionEvaluator.cpp`,
`streamInstance.cpp`, `dataModel.cpp`, `presenter.cpp`, `fldType.hpp`) — każde
nadal wskazuje tę samą konstrukcję. Zmienił się wyłącznie zakres samego
komentarza: był `compiler.cpp:958-959`, jest `compiler.cpp:958-960`.

## Odstępstwo od R4 (branch wyników)

`REQUIREMENTS.md` R4 przewiduje branch `experiment/YYYYMMDD_typ` i jeden commit
wyników scalany do `main` po przeglądzie — tak powstały wszystkie poprzednie
kampanie (ostatnia: `experiment/20260731_instrument`, PR #9). K22a został
scommitowany bezpośrednio na `main` jako `3a46171`.

Odnotowane, nie ukryte. Skutek jest ograniczony: K22a nie zawiera **żadnych
danych pomiarowych** — wyłącznie predeklarację, podręcznik i aparaturę — więc
reguła „jeden commit z kompletem wyników" nie ma tu czego chronić. Dla etapów
K22b–K22d, które wytworzą strumienie kanoniczne i tabele, R4 obowiązuje bez
zmian: osobny branch, jeden commit wyników, merge po przeglądzie.

## Artefakty surowe (`REQUIREMENTS.md` R14)

Etap K22a nie wytwarza artefaktów surowych: nie uruchamia silnika ani
kampanii. Wszystkie pliki tego katalogu są źródłami lub aparaturą i są
wersjonowane wprost. Reguła „sukces jest skrótem, reszta jest jednym
archiwum" zacznie obowiązywać od K22b, gdy powstaną strumienie kanoniczne.

## Odtworzenie stanu K22a od zera

```bash
cd /home/michal/github/rdb-experiment/results_20260801_K22
./tests/test_k22a.sh     # 3 zestawy, 61 kontroli
./oracle/run.sh          # bramka etapowa — zatrzyma sie na pustym korpusie
```

Aparatura nie ma zależności spoza biblioteki standardowej Pythona 3.
