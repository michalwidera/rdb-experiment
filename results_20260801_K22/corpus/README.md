# Korpus K22 — układ i zasady

**Stan: pusty. Programy powstają w etapie K22b, po akceptacji predeklaracji.**

```text
corpus/
  F1_fir/{rql,python,flink}/         FIR z oknem i redukcja
  F2_ecg/{rql,python,flink}/         niekliniczny potok cech ECG
  F3_multirate/{rql,python,flink}/   monitor wieloczestotliwosciowy
```

Każdy katalog modelu zawiera po wykonaniu K22b:

| Plik | Rola |
|---|---|
| `core.<ext>` | rdzeń zadania ze znacznikami `CORE_BEGIN` / `CORE_END` |
| `harness.<ext>` | ładowanie danych, emisja kanoniczna — **poza** metrykami |
| `provenance/` | niezmieniona kopia pliku źródłowego, jeśli rdzeń z niego pochodzi |
| `CLEANUP.md` | uzasadnienie każdego usunięcia: `harness` / `arytmetyka` / `format wyjścia` |

## Trzy zasady, które łatwo złamać po cichu

1. **Granica rdzenia jest w plikach, nie w głowie.** Metryki liczą wyłącznie
   tekst między znacznikami (`PREDECLARATION.md` §2). Pacing należy do rdzenia;
   emisja i pomiar czasu nie należą.

2. **Oczyszczenie musi być semantyczne, nie redakcyjne.** Każda linia usunięta
   z pliku provenance trafia do `CLEANUP.md` z jednym z trzech uzasadnień.
   Usunięcie bez uzasadnienia jest błędem aparatury i musi zostać cofnięte.

3. **Wersja porównawcza to najprostsza poprawna, nie najgorsza możliwa.**
   Reguła rozstrzygająca: autor pisze ją tak, jak napisałby kompetentny
   programista tego modelu **nieznający wyniku K22**. Zakaz obejmuje oba
   kierunki: ani sztucznego rozdmuchania Pythona/Flinka, ani ręcznego sharingu
   wpisanego po to, by pomóc RQL.

## Arytmetyka

Rdzenie Python i Flink liczą w **liczbach całkowitych** wg semantyki silnika
(`PREDECLARATION.md` §4), nie w `float64`. Rdzeń Pythona importuje
`oracle/refsem.py`; rdzeń Javy odwzorowuje te same reguły ręcznie.

Trzy pułapki, na których port rozjedzie się po cichu:

- `//` Pythona zaokrągla w dół, silnik obcina do zera (`-7/2` → `-3`, nie `-4`);
- dzielenie przez zero daje `NULL`, nie wyjątek;
- `.avg` dzieli przez liczbę pól **nie-`NULL`**, nie przez szerokość okna —
  dlatego zero-fill okien (`np.zeros`, `new double[N]`) jest **zakazany**.

Wszystkie trzy są przypięte testami w `oracle/test_refsem.py`.
