# CLM-0138 drafts — E3 bisection finding

Three drafts matching §VII-C scenarios. Pick one once `collect.py`
output is in `results/r77_phase3/score_bisect.log`. Then write
`memory/claims/CLM-0138.md` with the chosen body. After write, run
`python memory/tools/validate.py` and `python memory/tools/render.py`.

Reference (already established):
- Topological order: R58 e8427df → R60 2752a8f → R61 1a3a4ad → R62 48c466c → R63 6671e8d → R64 6c27ae1 → R65 4c5327a → R59 43d203b
- Smoke-test endpoints: R58 = R59 = `geo=0.3584, cum_rf=-0.0693, LS1=0.3222, LS2=0.3987` under v3.1 (11-axis), seed 51, wu=5, τ=0.005
- v3.1 ranker is the current main-worktree `paper_grade_axes.py` (R75+ multiplicative gating, 11-axis)
- CLM-0104 baseline used 6-axis ranker (R57=0.526 → R66=0.4259, -19%)

---

## Scenario A draft — flat (no cliff under v3.1)

```yaml
---
id: CLM-0138
type: finding
trust: V
status: current
statement: |
  R77 Phase 3 E3 — Code-drift bisection over R58 (e8427df) →
  R59 (43d203b) (topological order through R60..R65) under the
  current v3.1 11-axis ranker shows no commit-localised cliff:
  all 8 commits trained with td3_lstm s51 wu=5 τ=0.005 reproduce
  to v3.1 = 0.358 ± 0.0X (adjacent-pair |Δgeo| ≤ Y for all 7 pairs).
  This neither confirms nor refutes CLM-0104's 6-axis -19% drift —
  v3.1's multiplicative gating may dampen what 6-axis exposes. The
  cliff (if any) lies either outside the R58..R65 range or is
  6-axis-specific.

  ### Per-commit numbers (topological order, v3.1)

  | round | SHA | geo | cum_rf | LS1 | LS2 |
  |---|---|---|---|---|---|
  | R58 | e8427df | 0.3584 | -0.0693 | 0.3222 | 0.3987 |
  | R60 | 2752a8f | ?     | ?       | ?      | ?      |
  | R61 | 1a3a4ad | ?     | ?       | ?      | ?      |
  | R62 | 48c466c | ?     | ?       | ?      | ?      |
  | R63 | 6671e8d | ?     | ?       | ?      | ?      |
  | R64 | 6c27ae1 | ?     | ?       | ?      | ?      |
  | R65 | 4c5327a | ?     | ?       | ?      | ?      |
  | R59 | 43d203b | 0.3584 | -0.0693 | 0.3222 | 0.3987 |

  ### Implications for paper

  §VII-C "Code-drift caveat" (Scenario A draft) replaces the
  "remains open" closer with explicit statement that on v3.1, no
  single commit on R58..R65 introduced the drift, leaving the
  6-axis 0.526→0.426 drift attributable to either ranker
  sensitivity or commits earlier than R58.

round: R77
provenance:
  - results/r77_phase3/e3_bisect_R58_e8427df/final_eval_summary.json
  - results/r77_phase3/e3_bisect_R59_43d203b/final_eval_summary.json
  - results/r77_phase3/e3_bisect_R60_2752a8f/final_eval_summary.json
  - results/r77_phase3/e3_bisect_R61_1a3a4ad/final_eval_summary.json
  - results/r77_phase3/e3_bisect_R62_48c466c/final_eval_summary.json
  - results/r77_phase3/e3_bisect_R63_6671e8d/final_eval_summary.json
  - results/r77_phase3/e3_bisect_R64_6c27ae1/final_eval_summary.json
  - results/r77_phase3/e3_bisect_R65_4c5327a/final_eval_summary.json
  - artifacts/paper_r77/phase3/bisect.sh
  - artifacts/paper_r77/phase3/score_bisect.py
  - artifacts/paper_r77/phase3/collect.py
  - artifacts/paper_r77/main.tex
tags: [finding, code-drift, lstm-only, bisection-flat, 6-axis-only-drift, ranker-comparison]
metric:
  name: e3_max_adjacent_delta_v31
  value: 0.0X
---
```

## Scenario B draft — single cliff between R$X$ and R$Y$

```yaml
---
id: CLM-0138
type: finding
trust: V
status: current
statement: |
  R77 Phase 3 E3 — Code-drift bisection over R58 (e8427df) →
  R59 (43d203b) (topological order through R60..R65) under the
  current v3.1 11-axis ranker localises a Δv_3.1 cliff to commit
  pair R$X$ (SHA_a) → R$Y$ (SHA_b): v_3.1 drops from a to b
  (Δ = -0.0XX) within one commit, then recovers downstream to
  v_3.1 = 0.358 at R59. The cliff is V-shaped because R58 and R59
  reproduce identically (geo=0.3584). The introducing commit added
  <one-line summary of the diff>; this is consistent with the
  RNG-state-shift hypothesis (CLM-0104) — adding an os.environ.get
  read or atexit handler before LSTM hidden-state init perturbs the
  numpy/torch RNG by one draw, which BPTT amplifies. The 6-axis
  ranker likely amplifies this perturbation while v3.1's
  multiplicative gating dampens it, explaining why the headline
  6-axis -19% (CLM-0104) is steeper than the v3.1 cliff measured
  here.

  ### Per-commit numbers (topological order, v3.1)

  | round | SHA | geo | cum_rf | LS1 | LS2 |
  |---|---|---|---|---|---|
  | R58 | e8427df | 0.3584 | -0.0693 | 0.3222 | 0.3987 |
  | R60 | 2752a8f | ?     | ?       | ?      | ?      |
  | ... | ... |
  | R59 | 43d203b | 0.3584 | -0.0693 | 0.3222 | 0.3987 |

  ### Implications

  §VII-C is updated to name the introducing commit and the recovery
  commit. CLM-0104's "leading suspect: R61 monitor extension" is
  <confirmed | refuted>. The numbers in this paper are pinned to
  the post-cliff state.

round: R77
provenance:
  - results/r77_phase3/e3_bisect_*/final_eval_summary.json (8 dirs)
  - artifacts/paper_r77/phase3/bisect.sh
  - artifacts/paper_r77/phase3/score_bisect.py
  - artifacts/paper_r77/phase3/collect.py
  - memory/claims/CLM-0104.md
  - artifacts/paper_r77/main.tex
tags: [finding, code-drift, lstm-only, bisection-cliff-located, rng-state-shift, v-shaped]
metric:
  name: e3_cliff_delta_v31
  value: -0.0X  # the |Δ| at the cliff
---
```

## Scenario C draft — gradient drift, no single cliff

```yaml
---
id: CLM-0138
type: finding
trust: V
status: current
statement: |
  R77 Phase 3 E3 — Code-drift bisection over R58 (e8427df) →
  R59 (43d203b) (topological order through R60..R65) under the
  current v3.1 11-axis ranker shows cumulative drift, not a single
  cliff: v_3.1 fluctuates within [min, max] across the 8 commits
  with adjacent-pair |Δgeo| ≤ Y (all below the 0.05 cliff threshold).
  R58 and R59 endpoints both reproduce at 0.358, so the cumulative
  trajectory of micro-changes (monitor extension, env-var reads,
  paper-strict-eval scaffold) sums to a zero-mean random walk under
  v3.1. The 6-axis ranker (CLM-0104) likely amplifies this walk
  into the -19% headline. No single commit can be flagged as the
  offender on the bisected range.

  ### Per-commit numbers (topological order, v3.1)

  | round | SHA | geo | cum_rf | LS1 | LS2 | Δ_geo vs prev |
  |---|---|---|---|---|---|---|
  | R58 | e8427df | 0.3584 | -0.0693 | 0.3222 | 0.3987 | --- |
  | ... | ... |
  | R59 | 43d203b | 0.3584 | -0.0693 | 0.3222 | 0.3987 | ? |

  ### Implications

  §VII-C is updated to state that bisection did not localise the
  drift to a single commit; remediation requires either an
  RNG-state freeze at LSTM train entry or a switch to v3.1 as the
  paper ranker (already done — v3.1 is the project standard).

round: R77
provenance:
  - results/r77_phase3/e3_bisect_*/final_eval_summary.json (8 dirs)
  - artifacts/paper_r77/phase3/bisect.sh
  - artifacts/paper_r77/phase3/score_bisect.py
  - artifacts/paper_r77/phase3/collect.py
  - memory/claims/CLM-0104.md
tags: [finding, code-drift, lstm-only, bisection-no-single-cliff, cumulative-drift, ranker-dependent]
metric:
  name: e3_range_v31
  value: 0.0X  # max - min across 8 commits
---
```
