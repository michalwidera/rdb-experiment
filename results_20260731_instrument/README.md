# E4 — sonda pracy na slot i przeliczenie modelu kosztu (K20 etap 1b)

**Predeklaracja.** Ten plik powstaje i jest commitowany **przed** wygenerowaniem
jakichkolwiek danych tego badania. Podział uczenie/test, postać modelu, kryterium
sukcesu i lista zagrożeń trafności są zamrożone. Po pierwszym przebiegu nie wolno
ich zmienić ani doprecyzować. Jedyną dopuszczalną reakcją na niespodziankę jest
**zatrzymanie badania i nowy katalog** (`REQUIREMENTS.md` R3).

Kampania `results_20260730_K6c` jest **zamknięta**. Nic w niej nie wolno edytować.
To badanie tylko z niej **czyta**.

## Pytanie

Model kosztu slotu K20 etap 1 (`results_20260730_K6c/results/cost_model.md`) upadł:
**MAE_test = 258,3 %** na rodzinach niewidzianych przy dopasowaniu, oba współczynniki
bajtowe ujemne. Analiza po fakcie wskazała przyczynę: koszt tokena różni się **12,4×**
między rodzinami, bo istniejące liczniki opisują **strukturę planu**, a nie **pracę
wykonywaną w slocie**. Okno `@(1,30)` odwiedza 30 elementów w każdym slocie i jest
w planie jednym tokenem.

> **Pytanie badania:** czy licznik odwiedzin elementów na slot (`agseElements`)
> obniża błąd predykcji kosztu slotu na rodzinach niewidzianych przy dopasowaniu?

To jest pytanie o **cechę**, nie o wartość kosztu. Dlatego badanie nie powtarza
pomiarów czasowych — patrz „Odstępstwo" niżej.

## Instrumentacja (silnik, `issue_219-instrument`)

Sonda E4, kompilowana wyłącznie przy `RDB_BENCH_PROBE=ON`, raportowana na stderr
po zakończeniu mierzonej pętli przy ustawionym `RDB_BENCH_WORK`:

```
WORK agse: okna=N elementy=N odczyty=N  eval: wywolania=N tokeny=N  hash: wybory=N  add: scalenia=N
```

| licznik | znaczenie |
|---|---|
| `agseWindows` | konstrukcje okna agregatu |
| **`agseElements`** | **odwiedziny elementów okna — cecha badana** |
| `agseReads` | odczyty rekordu źródła (`revRead`); mniej niż odwiedzin, gdy trafia cache |
| `evalCalls`, `evalTokens` | wywołania ewaluatora i wykonania tokenów RPN |
| `hashPicks`, `addMerges` | wybory przeplotu, scalenia sum strumieni |

Liczniki są procesowe i nieatomowe (inkrementacja wyłącznie na wątku przetwarzania,
odczyt po pętli), więc sonda nie obciąża mierzonego budżetu slotu atomikami.

**Kontrola instrumentu — testy o znanej odpowiedzi, nie o „jakiejś liczbie":**
`test_dataModel.cpp`, przypadki `probe_e4_agse_window_work_counts`
i `probe_e4_agse_elements_scale_with_window_length`. Dla okna `@(1,4)` nad strumieniem
o trzech rekordach po dwa pola geometria wymusza dokładnie: 1 okno, **4 odwiedziny**,
**2 odczyty** (cache oszczędza dwa). Test przypina też akumulację między wywołaniami
i działanie `workReset()`.

## Odstępstwo od pełnej rekalibracji — jawne założenie

Cechy E4 są **deterministyczne**: liczba odwiedzin elementów wynika z planu i geometrii
okna, nie z zegara. Dlatego badanie:

- **zbiera cechy** krótkimi przebiegami instrumentowanymi (`-m N`) na buildzie
  `issue_219-instrument`,
- **cele `p99` bierze z K6c** (`results_20260730_K6c/results/rate.json`), gdzie zostały
  zmierzone rytuałem kampanii (PREEMPT_RT, governor `performance`, reboot).

**Założenie, od którego zależy ważność badania:** plan i praca na slot są identyczne
na `1bb2d2c` i na buildzie instrumentowanym, więc cechę wolno zestawić z celem
zmierzonym na `1bb2d2c`. Założenie jest **sprawdzane, nie zakładane** — badanie
higieniczne niżej jest warunkiem wstępnym i jego negatywny wynik unieważnia całe
badanie.

**Zagrożenie trafności nr 1, które z tego zostaje i musi trafić do raportu:** cechy
i cele pochodzą z różnych drzew kodu. Nawet przy przechodzącym badaniu higienicznym
jest to słabsze niż pomiar z jednego drzewa i tak ma być opisane. Wariant mocniejszy
(pełna rekalibracja czasowa na buildzie instrumentowanym) był rozważony i **świadomie
odrzucony** ze względu na koszt — decyzja człowieka 2026-07-31.

## Gdzie badanie jest wykonywane — i drugie zagrożenie

**Cechy zbierane na nadzorcy (x86-64), cele pochodzą z workera (aarch64, PREEMPT_RT).**
Worker jest potrzebny, gdy mierzy się czas; to badanie czasu nie mierzy, a liczniki E4
są funkcją geometrii planu — okno długości `L` daje `L` odwiedzin na slot niezależnie
od tego, jak szybko procesor je wykona. Potwierdzone empirycznie przy przygotowaniu:
liczniki wychodzą identyczne z `-t` (SCHED_FIFO + `taskset`) i bez niego, więc tryb
szeregowania na nie nie wpływa.

**Zagrożenie trafności nr 2:** zestawienie jest międzyplatformowe. Podstawą, że wolno,
jest wykazana wcześniej **bitowa identyczność artefaktów między architekturami**
(x86-64 vs aarch64) — skoro artefakty są bit w bit te same, plan i jego geometria też,
a liczniki są ich funkcją. **To jest argument z wcześniejszego wyniku, nie pomiar
wykonany w tym badaniu.** Kontrola empiryczna (zbudowanie `abe075e` z sondą na workerze
i porównanie liczników dla kilku komórek) była rozważona i **świadomie odrzucona** ze
względu na koszt budowy na Pi 400 — decyzja człowieka 2026-07-31. Gdyby wynik modelu
miał kiedykolwiek posłużyć za podstawę kontroli dopuszczenia planu w silniku, tę
kontrolę należy wykonać.

## Warunek wstępny — badanie higieniczne

Zmiana w kodzie wspólnym wymaga wykazania braku wpływu, zanim wcześniejsze wyniki
zostaną uznane za obowiązujące (reguła z K5h/K5i). Porównanie `1bb2d2c` wobec
`issue_219-instrument`, oba w wariancie **bez** sondy (`RDB_BENCH_PROBE=OFF`):

- plany skompilowane z korpusu RQL — identyczne,
- artefakty binarne i `.meta` — identyczne,
- **raportowana jest LICZBA porównanych rzeczy; zero jest błędem, nie zgodnością.**

Kryterium: zero różnic przy niezerowej liczbie porównań. Wynik negatywny → zatrzymanie.

## Model i podział — zamrożone

Podział rodzin jest **ten sam co w K6c** i nie wolno go zmienić:

- dopasowanie: `W2`, `W3`, `W5`, `W7`
- predykcja: `W4`, `W9`

Cel: `p99_ns` slotu, jak w etapie 1. Postać modelu bez wyrazu wolnego (koszt pustego
planu to zero, nie stała maszyny), dopasowanie metodą najmniejszych kwadratów.

Warianty cech policzone i raportowane **wszystkie**, żeby wybór nie był po fakcie:

| wariant | cechy |
|---|---|
| `v1` (odniesienie) | tokeny, bajty trwałe/slot, bajty pamięciowe/slot |
| `v2` | v1 + **elementy okna/slot** |
| `v3` | elementy okna/slot, odczyty/slot, tokeny eval/slot |
| `v4` | v3 + bajty trwałe/slot |

## Kryterium sukcesu — zamrożone przed danymi

**Sukces:** wariant zawierający `agseElements` osiąga **MAE_test ≤ 50 %** przy
MAE_train nie gorszym niż dwukrotność MAE_test (kontrola przeuczenia).

Próg 50 % nie jest ambitny i celowo: kontrola dopuszczenia planu potrzebuje ±20–30 %,
więc 50 % nie wystarcza do produktu — wystarcza natomiast do rozstrzygnięcia, czy
**kierunek jest właściwy**. Wynik między 50 % a 258 % zapisujemy jako poprawę bez
przydatności; wynik powyżej 258 % jako pogorszenie.

**Wynik ujemnego współczynnika przy dowolnej cesze jest raportowany jako ostrzeżenie
o współliniowości, nie chowany** — tak samo jak w etapie 1.

**Zapisane przed pomiarem przewidywanie:** `agseElements` obniży MAE_test poniżej
100 %, ale **nie** poniżej 20 %, bo trzy klasy operatorów nadal dzielą wspólny
współczynnik, a koszt zapisu przez `storage` zależy od typu magazynu, którego żadna
z cech nie rozróżnia. Przewidywanie jest częścią predeklaracji i będzie skonfrontowane
z wynikiem niezależnie od tego, czy się sprawdzi.

## Co to badanie NIE rozstrzyga

- **Nie** jest kampanią kosztową i nie zmienia werdyktu K6c (A=0, B=12, C=1).
- **Nie** mierzy narzutu samej sondy E4 — sonda jest w buildzie pomiarowym, więc
  narzut dotyczyłby przyszłych kampanii, nie tej analizy.
- **Nie** implementuje kontroli dopuszczenia w silniku (K20 etap 2). To osobna zmiana
  w `xretractor` z własnym badaniem higienicznym.
