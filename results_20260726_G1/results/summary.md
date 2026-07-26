# G1/K1 — obserwowalność planu: wyniki sondy

Wygenerowane przez `make_summary.py`. Nie edytować ręcznie.
Legenda: `=` warstwa zgodna między planami, `≠` rozbieżna.

### Przypadki — profil `default (przed naprawą W1)`

Konfiguracja binarki: `RDB_OPT_DEDUP_SUBSTRATES=ON RDB_OPT_SHARE_EQUIVALENT_SELECTS=ON RDB_OPT_COMMUTATIVE_ADD=ON RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=ON RDB_BENCH_PROBE=OFF`

| przypadek | nazwy pól | prefiks zer | rekordy all-null | wpisy gap | pierwsze wartości |
|---|---|---:|---|---|---|
| `shift_declared` | `value` | 0 | 0/47 | 0 | 1, 2, 3, 4, 5, 6, 7, 8, 9 … |
| `shift_declared_copy` | `value` | 0 | 0/47 | 0 | 1, 2, 3, 4, 5, 6, 7, 8, 9 … |
| `shift_computed` | `mid_0` | 3 | 0/47 | 0 | 0, 0, 0, 1, 2, 3, 4, 5, 6 … |
| `hash_declared` | `value` | 0 | 0/35 | 0 | 1000000, 1, 2, 1000001, 3, 4, 1000002, 5, 6 … |
| `hash_computed` | `midA_0` | 1 | 23/35 | 0 | 0, 1, 0, 0, 3, 0, 0, 5, 0 … |
| `hash_computed_sorted` | `midA_0` | 1 | 12/35 | 0 | 0, 1, 2, 0, 3, 4, 0, 5, 6 … |
| `add_declared` | `A_0, B_1` | 0 | 0/47 | 0 | 1/1000000, 2/1000001, 3/1000002, 4/1000003, 5/1000004, 6/1000005, 7/1000006, 8/1000007, 9/1000008 … |
| `add_computed` | `midA_0, midB_1` | 0 | 0/47 | 0 | 1/1000000, 2/1000001, 3/1000002, 4/1000003, 5/1000004, 6/1000005, 7/1000006, 8/1000007, 9/1000008 … |
| `r1_lhs_auto` | `value` | 3 | 0/35 | 0 | 0, 0, 0, 1000000, 1, 2, 1000001, 3, 4 … |
| `r1_lhs_blocked` | `value` | 1 | 23/35 | 0 | 0, 1, 0, 0, 3, 0, 0, 5, 0 … |
| `r1_rhs` | `value` | 3 | 0/35 | 0 | 0, 0, 0, 1000000, 1, 2, 1000001, 3, 4 … |

### Pary planów — profil `default (przed naprawą W1)`

| rola | para | wartości | mapa null | prefiks zer | nazwy pól | luki | uwaga |
|---|---|---|---|---|---|---|---|
| control | `shift_declared` ↔ `shift_declared_copy` | = | = | = | = | — | ten sam plan dwa razy |
| control | `add_declared` ↔ `add_computed` | = | = | = | **≠** | — | + nad wejściem deklarowanym vs obliczanym |
| question | `shift_declared` ↔ `shift_computed` | **≠** | = | **≠** | **≠** | — | >N nad wejściem deklarowanym vs obliczanym |
| question | `hash_declared` ↔ `hash_computed` | **≠** | **≠** | **≠** | **≠** | — | # nad wejściem deklarowanym vs obliczanym |
| question | `hash_computed` ↔ `hash_computed_sorted` | **≠** | **≠** | = | = | — | wpływ SAMEJ kolejności planu: to samo zapytanie, dołożone niezwiązane zapytanie wyzwala topologicalSort |
| question | `hash_declared` ↔ `hash_computed_sorted` | **≠** | **≠** | **≠** | **≠** | — | residuum po przywróceniu porządku: co zostaje niezgodne |
| question | `r1_lhs_auto` ↔ `r1_rhs` | = | = | = | = | — | R1: plan przepisany vs prawa strona tożsamości |
| question | `r1_lhs_blocked` ↔ `r1_rhs` | **≠** | **≠** | **≠** | = | — | R1: plan nieprzepisany vs prawa strona tożsamości |
| question | `r1_lhs_auto` ↔ `r1_lhs_blocked` | **≠** | **≠** | **≠** | = | — | R1: plan przepisany vs nieprzepisany |

### Przypadki — profil `default`

Konfiguracja binarki: `RDB_OPT_DEDUP_SUBSTRATES=ON RDB_OPT_SHARE_EQUIVALENT_SELECTS=ON RDB_OPT_COMMUTATIVE_ADD=ON RDB_OPT_FACTOR_MATCHED_HASH_TIMEMOVES=ON RDB_BENCH_PROBE=OFF`

| przypadek | nazwy pól | prefiks zer | rekordy all-null | wpisy gap | pierwsze wartości |
|---|---|---:|---|---|---|
| `shift_declared` | `value` | 0 | 0/44 | 0 | 1, 2, 3, 4, 5, 6, 7, 8, 9 … |
| `shift_declared_copy` | `value` | 0 | 0/44 | 0 | 1, 2, 3, 4, 5, 6, 7, 8, 9 … |
| `shift_computed` | `mid_0` | 0 | 0/44 | 0 | 1, 2, 3, 4, 5, 6, 7, 8, 9 … |
| `hash_declared` | `value` | 0 | 0/33 | 0 | 1000000, 1, 2, 1000001, 3, 4, 1000002, 5, 6 … |
| `hash_computed` | `midA_0` | 0 | 0/33 | 0 | 1000000, 1, 2, 1000001, 3, 4, 1000002, 5, 6 … |
| `hash_computed_sorted` | `midA_0` | 0 | 0/33 | 0 | 1000000, 1, 2, 1000001, 3, 4, 1000002, 5, 6 … |
| `null_r1_lhs_auto` | `value` | 0 | 6/30 | 0 | 1000000, 1, 0, 1000001, 3, 4, 0, 5, 0 … |
| `null_r1_lhs_blocked` | `value` | 0 | 6/30 | 0 | 1000000, 1, 0, 1000001, 3, 4, 0, 5, 0 … |
| `null_r1_rhs` | `value` | 0 | 6/30 | 0 | 1000000, 1, 0, 1000001, 3, 4, 0, 5, 0 … |
| `null_r1_rhs_copy` | `value` | 0 | 6/30 | 0 | 1000000, 1, 0, 1000001, 3, 4, 0, 5, 0 … |
| `add_declared` | `A_0, B_1` | 0 | 0/47 | 0 | 1/1000000, 2/1000001, 3/1000002, 4/1000003, 5/1000004, 6/1000005, 7/1000006, 8/1000007, 9/1000008 … |
| `add_computed` | `midA_0, midB_1` | 0 | 0/47 | 0 | 1/1000000, 2/1000001, 3/1000002, 4/1000003, 5/1000004, 6/1000005, 7/1000006, 8/1000007, 9/1000008 … |
| `r1_lhs_auto` | `value` | 0 | 0/30 | 0 | 1000000, 1, 2, 1000001, 3, 4, 1000002, 5, 6 … |
| `r1_lhs_blocked` | `value` | 0 | 0/30 | 0 | 1000000, 1, 2, 1000001, 3, 4, 1000002, 5, 6 … |
| `r1_rhs` | `value` | 0 | 0/30 | 0 | 1000000, 1, 2, 1000001, 3, 4, 1000002, 5, 6 … |

### Pary planów — profil `default`

| rola | para | wartości | mapa null | prefiks zer | nazwy pól | luki | uwaga |
|---|---|---|---|---|---|---|---|
| control | `shift_declared` ↔ `shift_declared_copy` | = | = | = | = | = | ten sam plan dwa razy |
| control | `add_declared` ↔ `add_computed` | = | = | = | **≠** | = | + nad wejściem deklarowanym vs obliczanym |
| question | `shift_declared` ↔ `shift_computed` | = | = | = | **≠** | = | >N nad wejściem deklarowanym vs obliczanym |
| question | `hash_declared` ↔ `hash_computed` | = | = | = | **≠** | = | # nad wejściem deklarowanym vs obliczanym |
| question | `hash_computed` ↔ `hash_computed_sorted` | = | = | = | = | = | wpływ SAMEJ kolejności planu: to samo zapytanie, dołożone niezwiązane zapytanie wyzwala topologicalSort |
| question | `hash_declared` ↔ `hash_computed_sorted` | = | = | = | **≠** | = | residuum po przywróceniu porządku: co zostaje niezgodne |
| control | `null_r1_rhs` ↔ `null_r1_rhs_copy` | = | = | = | = | = | dziedzina z NULL-ami: ten sam plan dwa razy |
| question | `null_r1_lhs_auto` ↔ `null_r1_rhs` | = | = | = | = | = | R1 nad danymi z NULL-ami: przepisany vs prawa strona |
| question | `null_r1_lhs_blocked` ↔ `null_r1_rhs` | = | = | = | = | = | R1 nad danymi z NULL-ami: nieprzepisany vs prawa strona |
| question | `r1_lhs_auto` ↔ `r1_rhs` | = | = | = | = | = | R1: plan przepisany vs prawa strona tożsamości |
| question | `r1_lhs_blocked` ↔ `r1_rhs` | = | = | = | = | = | R1: plan nieprzepisany vs prawa strona tożsamości |
| question | `r1_lhs_auto` ↔ `r1_lhs_blocked` | = | = | = | = | = | R1: plan przepisany vs nieprzepisany |

