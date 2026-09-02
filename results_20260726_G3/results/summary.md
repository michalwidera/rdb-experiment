# K2/G3 — independent shift-matching oracle

- engine commit: `5c3f32adb2ff8d377a3188c2b1f9ab2f6c3f707f`
- engine worktree: **dirty**, diff SHA-256: `ca5f15ce98a1cafa036071c307b76452b9439b6864e8830941bb00f5e476f36c`
- experiment repository commit before the campaign: `b51f7afd5f3c31380d86f1fa7035f23acdc89694`
- experiment worktree: **dirty**, diff SHA-256: `4f81e640458f07c3fdb9dc50ec723a2f9231a4045314312d6c35a5de64aab5b5`
- generated: 2026-09-02T12:31:57.163733+00:00
- oracle result: **OK**
- engine bridge result: **OK**

## 1. Mutation qualification

| mutation/control | detected as a difference | layers | verdict |
|---|---:|---|---|
| `rhs_shift_plus_one` | yes | tail, records | OK |
| `lhs_shift_off_by_one` | yes | tail, records | OK |
| `swapped_arguments` | yes | records | OK |
| `tie_to_b` | yes | records | OK |
| `null_map_dropped` | yes | records | OK |
| `null_as_zero` | yes | records | OK |
| `injected_gap` | yes | gaps | OK |
| `changed_schema` | yes | schema | OK |
| `legacy_first_b_tail` | yes | tail | OK |
| `unreduced_6_4_equals_3_2` | no | — | OK (kontrola benign) |

## 2. Purely model-level matrix

| campaign | cases | positions | mismatches | time [s] | checksum64 |
|---|---:|---:|---:|---:|---|
| exhaustive<=256 | 65536 | 123053540 | 0 | 20.796 | `51f914e0aa831b74` |
| property<=1e6 | 10000 | 19987962 | 0 | 3.653 | `83c63ba051847a78` |
| special | 12 | 24420 | 0 | 0.004 | `46584b8195ef2596` |

In total: **75548 cases**, **143065922 positions**, **0 mismatches**.

Explicit check of the record domain:

- no NULL: 714;
- partial NULL: 264;
- all-null: 22.

Unmatched shifts rejected: **12/12**.

## 3. Oracle — RetractorDB bridge

| case | min Δ [ms] | ΔA/ΔB | i+k | W | # tail legacy/safe | records opt/blocked/rhs | blocked errors | result |
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

Every case executes three plan forms: the LHS rewritten by R1, the LHS blocked by public shift streams, and the explicit RHS. Each of them is compared directly against the oracle.

`# tail safe` is the maximum required lookahead of B over all phases of one period. The difference against the former `ceil(delta_B/delta_A)` predicted exactly the cases with all-null records in the non-rewritten LHS.

## 4. Gap semantics

In the current runtime, gap detection writes no markers for computed streams, so the observable gap trace of R1 results is `G_S = ∅`. The mutation matrix confirms that the comparator detects an injected marker. Enabling gap propagation would be a semantic change belonging to K19/G16.

## 5. Verdict

**K2/G3 meets the experimental criterion: zero unexplained mismatches.**
