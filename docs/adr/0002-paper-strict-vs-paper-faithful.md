# ADR-0002: Split `paper-faithful` term — introduce `paper-strict-pure` / `paper-strict-rescaled`

- **Status:** Accepted
- **Date:** 2026-05-17
- **Deciders:** repository owner (during R58 `/grill-with-docs` session)
- **Supersedes:** none (clarifies CONTEXT.md `paper-faithful` definition)

---

## Context

Through R56–R57 (May 2026), `CONTEXT.md:85-87` defined `paper-faithful`
as "matches the original paper's equations and parameter regime
(H₀=100, Eq.14 strict)" and asserted that the `V4` env is paper-faithful.

A late-R57 audit (using the `critic` agent, briefed with
`docs/paper/kd_4agent_paper_facts.md`) revealed that the `V4` env
materially deviates from Yang et al., IEEE TPWRS 2023 in three
CRITICAL ways:

1. **Non-paper reward term `PHI_ABS=50`**: `base_env.py:79` adds
   `r_abs = -(d_omega_i)²` with weight 50 to every agent's reward.
   Paper Eq.14 strictly is `r_i = φ_f·r^f + φ_h·r^h + φ_d·r^d`. The
   `r_abs` term changes the optimization objective from frequency
   *synchronization* (paper's `r^f` is zero when all nodes share
   any offset) to frequency *restoration*. At typical `df=0.1 Hz`,
   `PHI_ABS·r_abs` dominates `PHI_F·r^f` since the latter is near-zero
   for synchronized nodes.
2. **Rescaled action penalties `PHI_H=PHI_D=0.0056`**: paper Eq.14
   nominal is 1.0. The 1/178 rescale was introduced in R18 (verdict
   `memory/rounds/R18/verdict.md`) to prevent `r_h/r_f ≈ 36000:1`
   divergence given V4's 17× wider action range than the paper's
   nominal box. The rescale makes the parameter-conservation
   constraint (paper §0.5 dual objective) effectively vestigial.
3. **Project-invented eval metric**: `paper_grade_axes.py` scores on
   a geometric mean of 6-8 axes (max_df, settling, smoothness,
   utilization, improvement). Paper Sec.IV-C scores on cumulative
   global frequency reward `-Σ_t Σ_i (f_i,t - f̄_t)²` over 50 random
   test scenarios. The 6-axis metric is not directly comparable to
   the paper's `-8.04` headline.

Each deviation is documented (R18 verdict, `paper_grade_axes.py`
docstrings) but the CONTEXT.md `paper-faithful` label glossed over
this — when a reader asks "is V4 paper-faithful?", the honest answer
is "yes for topology + obs space + action space + algorithm choice
SAC; no for reward shape + eval metric."

The audit recommended (Top-3 fixes in audit verdict): (1) implement
paper's eval metric, (2) implement a config with `PHI_ABS=0` +
`PHI_H/D=1.0`, (3) train to paper convergence horizon. R58 implements
(1) and (2) at 75-ep training to validate whether existing R56/R57
algorithm ranking conclusions are robust to the reward + eval changes.

## Decision

Split the `paper-faithful` term in `CONTEXT.md` into three levels and
introduce two new V4Config classmethods for the two new strict levels.

### Term definitions

| Term | Reward | Eval | What it claims |
|---|---|---|---|
| **`paper-faithful-modified`** (was: `paper-faithful`) | `100·r^f + 50·r_abs + 0.0056·r^h + 0.0056·r^d` | 6-axis composite on LS1/LS2 | V4 env from R30 onwards — topology + obs + action space match paper, reward + eval are project-modified for ANDES numerical stability + project research questions |
| **`paper-strict-pure`** | `100·r^f + 1·r^h + 1·r^d` (paper Eq.14 nominal) | global cum-rf paper Sec.IV-C formula | Direct paper config; expected to diverge per R18 mechanism. Used to verify R18 verdict empirically |
| **`paper-strict-rescaled`** | `100·r^f + 0.0056·r^h + 0.0056·r^d` (no PHI_ABS, but PHI_H/D rescale retained) | global cum-rf paper Sec.IV-C formula | Halfway between paper-strict-pure and paper-faithful-modified. Used to isolate whether algorithm ranking depends on PHI_ABS vs depends on the H/D rescale |

### Code changes

1. `src/andes_rl_kundur/env/andes/v4_config.py`:
   - Existing `V4Config.paper_faithful()` classmethod **retained
     unchanged** (preserves R56/R57 ckpt reproducibility).
   - New `V4Config.paper_strict_pure()` returns config with
     `phi_abs=0.0, phi_h=1.0, phi_d=1.0`, all else paper-default.
   - New `V4Config.paper_strict_rescaled()` returns config with
     `phi_abs=0.0, phi_h=0.0056, phi_d=0.0056`, all else paper-default.

2. `CONTEXT.md:85-87`:
   - Rename `paper-faithful` term to `paper-faithful-modified` to
     reflect the documented deviations.
   - Add `paper-strict-pure` and `paper-strict-rescaled` to the
     terminology list.

3. `src/andes_rl_kundur/evaluation/paper_strict_eval.py` (new):
   - `compute_global_cum_rf(trace)` returning the paper Sec.IV-C
     formula value.

### Test set

`paper_strict_eval.generate_test_scenarios(n=20, seed=2026,
include_anchors=True)` returns a deterministic, JSON-serializable list
of 20 disturbance scenarios:
- 2 anchors: paper LS1 (`PQ_Bus14: -2.48`) + LS2 (`PQ_Bus15: +1.88`)
- 18 random PQ bus + uniform [-300, +300] MW (covers paper LS1/LS2
  magnitudes plus surrounding range)

## Alternatives considered

### A. Keep `paper-faithful` label, document deviations in CONTEXT.md amendments

**Rejected**: The label is what a reader sees first; embedding caveats
in adjacent paragraphs is fragile. Anyone scanning CONTEXT.md for
"which env matches the paper" would still pick V4.

### B. Rename `paper-faithful` to `paper-aligned` (soft language)

**Rejected**: "aligned" is too vague. The deviations are specific and
quantifiable; the new labels capture the specificity.

### C. Build a brand-new `V5` env to be paper-strict

**Rejected**: V4 topology / obs / action space / algorithm scaffolding
are all paper-faithful. Only reward + eval need to change. Building
V5 would force a full second env codebase and duplicate the maintenance
burden without buying anything beyond the new classmethods + new eval
module that R58 already produces.

### D. Implement paper's metric inside `paper_grade_axes.py` as a new axis

**Rejected**: The paper metric is not an axis; it's a scalar episode
reward. Adding it to a geo-mean composite would dilute its meaning.
Keep it in a separate module (`paper_strict_eval.py`).

## Consequences

### Positive

- Honest term for what V4 actually is (modified, not strict-faithful)
- Two new classmethods enable empirical verification of R18 mechanism
  and audit-flagged ranking-validity questions
- No breakage of R56/R57 ckpts or callers
- ADR + R58 verdict together document the audit + the resolution path

### Negative

- Three terms instead of one (cognitive overhead)
- Future code reading must distinguish which V4Config flavor a result
  was produced under
- R58 introduces additional ckpt result directories (`results/r58_*`),
  increasing local-disk footprint

### Risks

- If `paper-strict-pure` trains and `paper-strict-rescaled` doesn't,
  R18's verdict mechanism would be falsified. Acceptable: it's a
  testable hypothesis.
- If `paper-faithful-modified` results turn out comparable to
  `paper-strict-rescaled`, the value of PHI_ABS is questionable, and
  CLM-0067 production decision may need re-issue.

## References

- `memory/rounds/R18/verdict.md` — original PHI rescale rationale
- `memory/rounds/R58/plan.md` — this round's experiment
- `memory/rounds/R58/verdict.md` — audit findings + paper-strict results
- `docs/paper/kd_4agent_paper_facts.md` — paper canonical reference
