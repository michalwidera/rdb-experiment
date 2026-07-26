# K2/G3 — niezależny oracle shift-matching

- commit silnika: `5c3f32adb2ff8d377a3188c2b1f9ab2f6c3f707f`
- worktree silnika: **dirty**, diff SHA-256: `ca5f15ce98a1cafa036071c307b76452b9439b6864e8830941bb00f5e476f36c`
- commit repozytorium eksperymentów przed kampanią: `b51f7afd5f3c31380d86f1fa7035f23acdc89694`
- worktree eksperymentu: **dirty**, diff SHA-256: `4f81e640458f07c3fdb9dc50ec723a2f9231a4045314312d6c35a5de64aab5b5`
- wygenerowano: 2026-07-26T18:51:13.620024+00:00
- wynik oracle'a: **OK**
- wynik mostu do silnika: **OK**

## 1. Kwalifikacja mutacji

| mutacja/kontrola | wykryta jako różnica | warstwy | werdykt |
|---|---:|---|---|
| `rhs_shift_plus_one` | tak | tail, records | OK |
| `lhs_shift_off_by_one` | tak | tail, records | OK |
| `swapped_arguments` | tak | records | OK |
| `tie_to_b` | tak | records | OK |
| `null_map_dropped` | tak | records | OK |
| `null_as_zero` | tak | records | OK |
| `injected_gap` | tak | gaps | OK |
| `changed_schema` | tak | schema | OK |
| `legacy_first_b_tail` | tak | tail | OK |
| `unreduced_6_4_equals_3_2` | nie | — | OK (kontrola benign) |

## 2. Macierz czysto modelowa

| kampania | przypadków | pozycji | rozbieżności | czas [s] | checksum64 |
|---|---:|---:|---:|---:|---|
| exhaustive<=256 | 65536 | 123053540 | 0 | 20.796 | `51f914e0aa831b74` |
| property<=1e6 | 10000 | 19987962 | 0 | 3.653 | `83c63ba051847a78` |
| special | 12 | 24420 | 0 | 0.004 | `46584b8195ef2596` |

Łącznie: **75548 przypadków**, **143065922 pozycji**, **0 rozbieżności**.

Jawna kontrola dziedziny rekordów:

- bez NULL: 714;
- częściowy NULL: 264;
- all-null: 22.

Niedopasowane przesunięcia odrzucone: **12/12**.

## 3. Most oracle — RetractorDB

| przypadek | min Δ [ms] | ΔA/ΔB | i+k | W | ogon # legacy/bezpieczny | rekordy opt/blocked/rhs | błędy blocked | wynik |
|---|---:|---|---:|---:|---|---|---:|---|
| p2_equal | 10 | 1 | 2 | 3 | 1/1 | 86/86/86 | 0 | OK |
| p3_regression | 100 | 1/2 | 3 | 5 | 2/2 | 47/47/47 | 0 | OK |
| p3_reverse | 10 | 2 | 3 | 4 | 1/1 | 55/55/55 | 0 | OK |
| p4_skew | 10 | 1/3 | 4 | 7 | 3/3 | 52/52/52 | 0 | OK |
| p5_remainder1 | 10 | 2/3 | 5 | 7 | 2/2 | 55/55/55 | 0 | OK |
| p7_remainder1 | 10 | 3/4 | 7 | 9 | 2/2 | 55/55/55 | 0 | OK |
| p8_remainder2 | 10 | 3/5 | 8 | 11 | 2/3 | 57/57/57 | 0 | OK |
| p5_fast | 2 | 3/2 | 10 | 12 | 1/2 | 69/69/69 | 0 | OK |
| p5_slow | 20 | 3/2 | 10 | 12 | 1/2 | 31/31/31 | 0 | OK |
| p18_fast | 2 | 7/11 | 18 | 21 | 2/3 | 74/74/74 | 0 | OK |
| p18_slow | 20 | 7/11 | 18 | 21 | 2/3 | 26/26/26 | 0 | OK |
| p3_unreduced | 10 | 3/2 | 5 | 7 | 1/2 | 49/49/49 | 0 | OK |
| p307_audio | 2 | 160/147 | 307 | 309 | 1/2 | 217/217/217 | 0 | OK |

Każdy przypadek wykonuje trzy postacie planu: LHS przepisaną przez R1, LHS zablokowaną przez publiczne strumienie przesunięcia oraz jawną RHS. Każda z nich jest porównywana bezpośrednio z oracle'em.

`ogon # bezpieczny` jest maksimum wymaganego wyprzedzenia B po wszystkich fazach jednego okresu. Różnica względem dawnego `ceil(delta_B/delta_A)` przewidywała dokładnie przypadki z rekordami all-null w nieprzepisanej LHS.

## 4. Semantyka luk

W bieżącym runtime detekcja luk nie zapisuje markerów dla strumieni obliczanych, więc obserwowalny ślad luk wyników R1 wynosi `G_S = ∅`. Macierz mutacyjna potwierdza, że komparator wykrywa wstrzyknięty marker. Włączenie propagacji luk byłoby zmianą semantyki należącą do K19/G16.

## 5. Werdykt

**K2/G3 spełnia kryterium eksperymentalne: zero niewyjaśnionych rozbieżności.**
