# K26v3 / H9 - English summary

This file is an English summary of the campaign behind `tab:h9-primary` (families F9-R2, F9-R1 and F9-X). It was added on 2026-11-18, after the campaign, and is not part of the frozen apparatus: it is outside `manifest.sha256`, and no gate reads it. The binding texts are the Polish originals, [`PREDEKLARACJA.md`](PREDEKLARACJA.md) (pre-registration) and [`WERDYKT.md`](WERDYKT.md) (verdict). Where this summary and those files disagree, they win.

## Status

The campaign is complete. The cost matrix ran from 2026-08-14 to 2026-08-16, and the frozen `verdict.py` issued its verdict on 2026-08-16.

The status lines at the top of [`README.md`](README.md) (lines 10-11: "P6 not started", "the K26v3 cost measurement has not been performed") and of `PREDEKLARACJA.md` describe the directory at the moment of freezing, before the measurement. Both files are listed in `manifest.sha256`, and `freeze_check.sh` verifies that manifest, so they were deliberately left unchanged. The result is in `WERDYKT.md` and in this summary.

**Verdict: H9 supported in the class `Q=8`, 3 of 3 families** (the threshold rule required 2 of 3).

## Pre-registration (frozen before the measurement)

Question: does automatic recognition of a common materialized subplan give at least a 40% reduction of the logical substrate bytes per public record, against both the family's minimal ablation and Flink's natural plan, without a time cost above 5%?

- **Decisive cell: `Q=8`.** `Q={1,2,4}` are trend controls and `Q={16,32}` measure scaling (`PREDEKLARACJA.md` section 2, line 91). They are not additional chances to pass. `Q` is the number of equivalent monitors in one program.
- **Thresholds**, all required for a family to support H9:
  1. the seven gates of section 7 pass: `corpus_validity`, `oracle_values`, `oracle_mutants`, `counter_known_answer`, `public_identity`, `near_miss_controls` and `no_materialization`;
  2. the reduction of the primary metric is at least 40% against the minimal ablation **and** against `FLINK_NATURAL`;
  3. the upper bound of the paired bootstrap 95% CI of the ratio `DEFAULT/minimal ablation` of `compute_median_ns` is at most 1.05.
- **Decision rule:** H9 is supported when at least 2 of 3 families pass. The thresholds, the 2/3 rule, 20 blocks, 10 000 bootstrap replications and the bootstrap seed `20260809_2603` are constants of `verdict.py`, not command-line parameters.
- **Work counter**, reported but not part of the threshold, chosen per family before the measurement (section 2.1): `work_costly_evals` for F9-R2 and F9-X, `work_hash_picks` for F9-R1.
- **Profiles:** `DEFAULT` (both passes on; `ALGSTRUCT` in the paper), `NO_R2_CANON`, `NO_R1_FACTOR`, `NO_R1_NO_R2`. Minimal ablation per family: `NO_R2_CANON` for F9-R2, `NO_R1_FACTOR` for F9-R1, `NO_R1_NO_R2` for F9-X.
- **Families** (section 3): F9-R2 isolates canonicalization of the commutative `+` (pass R2); F9-R1 isolates the interleave factorization `(A>2)#(B>1)` versus `(A#B)>3` (pass R1); F9-X needs R1 followed by R2 over two interleaves.
- **Claim boundary** (section 11): even if H9 is supported, it only warrants the statement that in the three studied families and at `Q=8` automatic sharing reached the declared threshold without the declared time cost. It does not show a general advantage of RetractorDB over Flink or a universal memory reduction.

## Verdict at `Q=8`

| Family | Minimal ablation | Reduction vs ablation | Reduction vs `FLINK_NATURAL` | Time ratio, point [95% CI] | Family verdict |
|---|---|---:|---:|---|---|
| F9-R2 | `NO_R2_CANON` | 50.000% | 87.500% | 0.9170 [0.9150, 0.9274] | SUPPORT |
| F9-R1 | `NO_R1_FACTOR` | 50.000% | 87.497% | 0.9799 [0.9495, 0.9934] | SUPPORT |
| F9-X | `NO_R1_NO_R2` | 58.333% | 84.374% | 0.7399 [0.7207, 0.7437] | SUPPORT |

- Gates 21/21 `PASS`, classification `clean`; negative controls clean; public results identical in every family.
- Work counter against `FLINK_NATURAL`: 87.504% (F9-R2), 87.508% (F9-R1), 87.511% (F9-X).
- Matrix: 1440/1440 cells (3 families x 6 values of `Q` x 4 profiles x 20 blocks), `lost_records` 0, no cell over its slot budget; the worst p99 share was 34.5% of the slot (F9-R1, `NO_R1_FACTOR`, `Q=32`, block 20).
- Two point predictions for `Q=1` missed and are reported, not hidden: the reduction against `FLINK_NATURAL` was 100.000% in F9-R2 (predicted 0.000%) and -0.011% in F9-X (predicted -25.000%). `Q=1` is outside the decisive cell, so the verdict stands.

## Claim boundaries (`WERDYKT.md`, "Granice twierdzenia")

1. The result is about automated sharing of materialization, not general speed. "RetractorDB is faster than Flink", "always uses less memory" and "Flink cannot share" are not supported.
2. The result holds for the class `Q=8` and this corpus. `Q=16,32` measure scaling only.
3. The byte metric is nearly binary: with full deduplication it falls by `1-1/Q`, without the mechanism by 0%. It confirms the mechanism and is not a headline number.
4. `DEFAULT` and `FLINK_MANUAL` are identical by construction, since `FLINK_MANUAL` reproduces the nodes of the `DEFAULT` plan. It is not independent confirmation.
5. Motivational validity remains the main risk: the question "who writes the same computation in eight forms?" was recorded in the pre-registration before the results.
6. K26v3 repeats the decision procedure on a repaired apparatus. It is not an independent replication of the byte side: corpus and seeds are those of K26v2, and only the time measurement is new.
7. The time ratio came out below 1 in every family. The threshold did not require it, and it is not generalized beyond the studied query class.

## Where things are

| What | Where |
|---|---|
| RQL programs, full `Q` grid | `rql/F9_{R1,R2,X}_Q{1,2,4,8,16,32}.rql`, controls in `rql/F9_*_controls.rql`. File names use `_` where the paper writes `-` (`F9_R2_Q8.rql` is family F9-R2 at `Q=8`). |
| Verdict inputs | `matrix/mechanism.tsv` (108 rows), `matrix/timing.tsv` (1440 rows, all `Q` values), `matrix/gates.tsv` (21 rows) |
| Plan dumps per profile | `corpus_validation/plans/<profile>/` |
| Flink ports and plans | `flink/` (plans at `Q=8` in `flink/plans/`, `Q` curve in `flink/results/flink_q_curve.tsv`) |
| Raw probes of the cost matrix | `../artifacts/K26v3/k26v3_archives/K26v3-P8-F9-{R1,R2,X}.tar.gz`, checksums in [`K26v3-P8_raw.index.tsv`](K26v3-P8_raw.index.tsv) |
| Frozen apparatus | `manifest.sha256` (438 entries), checked by `freeze_check.sh` |
| Pins | engine `856ee54b0f4ab450a6b61e3c08e045f404a79488`; experiment `81bf4bea00efb922678862c90462fb3c0dfe5fda` (tag `campaign/H9-K26v3`, the frozen apparatus before the measurement; the verdict and `matrix/` were committed afterwards) |
| Control replication on a later engine | `../results_20261103_R593_H9/`: 3 of 3 families supported at `Q=8`, Flink side not repeated |
