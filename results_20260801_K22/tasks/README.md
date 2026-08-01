# Zadania modyfikacyjne K22 — pełna macierz 3×4

**Stan: pusty. Warianty powstają w etapie K22c.**

```text
tasks/
  M1/{F1_fir,F2_ecg,F3_multirate}/{rql,python,flink}/
  M2/  M3/  M4/   — tak samo
```

Każda rodzina otrzymuje **wszystkie cztery** zadania: 12 wariantów na model,
36 łącznie. Powód wyboru pełnej macierzy zamiast przypisania 1:1 —
`PREDECLARATION.md` §6: kryterium go/no-go czyta się wtedy dosłownie, a autor
nie ma swobody przypisania zadania do rodziny wygodnej dla RQL.

| | F1_fir | F2_ecg | F3_multirate |
|---|---|---|---|
| **M1** drugi kanał w nazwanym wyniku | drugie źródło w `f1_out` | `ecg.V1` w wyniku | drugie pole z `B` w `f3_out` |
| **M2** szerokość okna | `@(1,25)` → `@(1,45)` | MWI `@(1,30)` → `@(1,45)` | okno `@(1,30)` → `@(1,45)` |
| **M3** interwał źródła i wyrównanie | `1/1000` → `1/750` | `1/360` → `1/250` | `Δ_A: 1/10 → 1/12` |
| **M4** `Q=8` nazwanych monitorów | 8 monitorów nad FIR | 8 monitorów nad `mwi` | 8 monitorów nad `(A>2)#(B>1)` |

## Reguły, których złamanie unieważnia komórkę

1. **Każdy wariant powstaje z czystej bazy, nie kumulatywnie.** `tasks/M2/...`
   jest diffem wobec `corpus/...`, nigdy wobec `tasks/M1/...`. Inaczej
   kolejność zadań zmieniałaby wielkość diffu.

2. **Zadanie opisuje zmianę zachowania, nie sposób implementacji.** Tabela
   mówi, co ma być inne w wyniku; nie mówi, jak to osiągnąć w którymkolwiek
   z modeli.

3. **Test musi porównywać obserwowalny wynik.** Test sprawdzający `grep` po
   treści programu jest z definicji nieważny i unieważnia komórkę.

## Test fail-before / pass-after

Każde z 36 zadań ma test, który **zawodzi** na niezmodyfikowanej bazie
i **przechodzi** na wariancie, porównując kanoniczny CSV. Wynik obu przebiegów
trafia do `results/modifications.csv` w kolumnach `test_fail_before`
i `test_pass_after`. Zadanie, którego test przechodzi już na bazie, nie mierzy
niczego — jest błędem aparatury, nie wynikiem.

## Co zmienia się razem z zadaniem

- **M2 zmienia ogon** (F1, F2). Nowy `tail` jest **odczytywany z silnika**
  (`xretractor -t`), nie wyliczany. Zakres porównania przesuwa się razem z nim.
- **M3 zmienia gęstość slotów.** Zakres porównania pozostaje 2000 **slotów**,
  nie 2000 sekund.
- **M4 nie wolno realizować ręcznym sharingiem** w wersji porównawczej ani
  ręczną duplikacją w wersji RQL.
