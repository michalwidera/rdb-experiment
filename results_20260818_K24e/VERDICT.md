# K24d / H10 — verdict

Corpus: **10010 plans**, **35835 node observations**, zero apparatus errors. Seed 20260818, engine `e2a61ff` (PIN.md).

The verdict is reported per operator class. 100% agreement is the only
support for H10a in a class; one mismatch falsifies H10a in that class.

## 1. H10a — exactness, per operator class

The **isolated** column is the verdict: the closed form computed from the
component tails taken from the oracle, so a mismatch originates in this
node's own rule. The **propagated** column is the agreement of the engine's
plan dump with the oracle over the whole plan — it carries the effects of
mismatches inherited from children.

| Class | Nodes | Isolated C1 | Isolated C2 | Propagated C1 | Regime | H10a verdict |
|---|---:|---:|---:|---:|---|---|
| `HASH` | 5953 | 100.0% | 49.5% | 100.0% | exact | **supported** |
| `SHIFT` | 5440 | 100.0% | 95.6% | 100.0% | exact | **supported** |
| `PASS` | 4735 | 100.0% | 0.0% | 100.0% | exact | **supported** |
| `SUB` | 4433 | 100.0% | 72.1% | 100.0% | exact | **supported** |
| `AGSE` | 4361 | 100.0% | 43.1% | 100.0% | exact | **supported** |
| `REDUCE` | 3297 | 100.0% | 0.0% | 100.0% | exact | **supported** |
| `THETA` | 2567 | 100.0% | 66.3% | 100.0% | exact | **supported** |
| `NTHETA` | 2559 | 100.0% | 99.4% | 100.0% | exact | **supported** |
| `ADD` | 2490 | 100.0% | 44.9% | 100.0% | exact | **supported** |

### The three regimes

* **exact** (closed form == oracle everywhere): `HASH`, `SHIFT`, `PASS`, `SUB`, `AGSE`, `REDUCE`, `THETA`, `NTHETA`, `ADD`;
* **over-approximating** (never under-approximates; safe, but not equal): none;
* **under-approximating** (tail shorter than the event model requires): none.

The under-approximating regime is qualitatively different from the
over-approximating one: over-approximation delays emission by a slot,
under-approximation means a record emitted before all its dependencies
are determined.

### Difference distribution (closed form − oracle C1)

| Class | Distribution |
|---|---|
| `HASH` | `+0`: 5953 (100.0%) |
| `SHIFT` | `+0`: 5440 (100.0%) |
| `PASS` | `+0`: 4735 (100.0%) |
| `SUB` | `+0`: 4433 (100.0%) |
| `AGSE` | `+0`: 4361 (100.0%) |
| `REDUCE` | `+0`: 3297 (100.0%) |
| `THETA` | `+0`: 2567 (100.0%) |
| `NTHETA` | `+0`: 2559 (100.0%) |
| `ADD` | `+0`: 2490 (100.0%) |

### Witnesses

| Class | Direction | Plan | Node | Interval | Engine | Closed form (isol.) | Oracle C1 |
|---|---|---:|---|---|---:|---:|---:|

## 1b. H10a — logical origin, per operator class

A quantity introduced by the re-stamping of 2026-08-06 and absent from
the K24/K24r campaigns. The **sum** column compares origin+tail — the
only quantity shared with the campaigns predating that change.

| Class | Nodes | Isolated | Propagated | Sum (origin+tail) | Regime | Verdict |
|---|---:|---:|---:|---:|---|---|
| `HASH` | 5953 | 100.0% | 100.0% | 100.0% | exact | **supported** |
| `SHIFT` | 5440 | 100.0% | 100.0% | 100.0% | exact | **supported** |
| `PASS` | 4735 | 100.0% | 100.0% | 100.0% | exact | **supported** |
| `SUB` | 4433 | 100.0% | 100.0% | 100.0% | exact | **supported** |
| `AGSE` | 4361 | 100.0% | 100.0% | 100.0% | exact | **supported** |
| `REDUCE` | 3297 | 100.0% | 100.0% | 100.0% | exact | **supported** |
| `THETA` | 2567 | 100.0% | 100.0% | 100.0% | exact | **supported** |
| `NTHETA` | 2559 | 100.0% | 100.0% | 100.0% | exact | **supported** |
| `ADD` | 2490 | 100.0% | 100.0% | 100.0% | exact | **supported** |

### Origin difference distribution (engine calculus − oracle)

| Class | Distribution |
|---|---|
| `HASH` | `+0`: 5953 (100.0%) |
| `SHIFT` | `+0`: 5440 (100.0%) |
| `PASS` | `+0`: 4735 (100.0%) |
| `SUB` | `+0`: 4433 (100.0%) |
| `AGSE` | `+0`: 4361 (100.0%) |
| `REDUCE` | `+0`: 3297 (100.0%) |
| `THETA` | `+0`: 2567 (100.0%) |
| `NTHETA` | `+0`: 2559 (100.0%) |
| `ADD` | `+0`: 2490 (100.0%) |

Origin under-approximated (a read before the source's origin): **none**.

## 2. H10b — non-locality

* divergence of local rule A from the exact one: **5275 of 10010 plans = 52.7%** (pre-declared threshold: >= 5%)
* pre-declared population (exactly one `#`, otherwise `PASS`/`>N`): **461 plans**, positive divergences **335**
* divergences of the pre-declared form `ceil((p+q-1)/p)`: **335 of 335** (100.0%; threshold: 100%)

## 3. Negative controls

| Control | Nodes | Divergences | State |
|---|---:|---:|---|
| HC_SINGLE (literal) | 4038 | 0 | **passed** |
| HC_SINGLE (operators with no tail of their own) | 3789 | 0 | **passed** |
| HC_INT (literal) | 6832 | 3163 | **BROKEN** |
| HC_INT (`#` nodes, local rule B) | 2922 | 351 | **BROKEN** |

Both pre-declared controls **are broken in their literal form**.
Under PREDECLARATION.md §6 this means an ill-defined local rule rather
than a result — therefore **part (b) is not assessable on this
apparatus** and the H10b figures above do not constitute a verdict.
Diagnosis of the contradiction in part (b)'s specification: REPORT.md §5.

