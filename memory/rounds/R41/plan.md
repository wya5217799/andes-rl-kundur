# R41 plan — three-part follow-up to CLM-0044

**Date**: 2026-05-17
**Type**: experiment (A) + experiment (C) + implementation (B)
**Trigger**: R40 confirmed CLM-0043's reward-asymmetry hypothesis.
R40 used the extreme PHI=0 ablation; R41 explores three follow-on
questions:

## Part A — SAC phi=0 ablation

**Question**: Is the action-cost trap algorithm-agnostic, or does
SAC's entropy bonus change the picture?

**Method**: 3 seeds × 75 episodes, SAC `--phi-h 0 --phi-d 0`.

**Prediction**: SAC phi=0 should also escape the 0.137 attractor
and reach 0.20+ if the trap is purely reward-shape.

## Part C — Extended-training ceiling

**Question**: Does TD3 phi=0 saturate at ~0.26 (R40 ceiling) or
continue improving with longer training?

**Method**: 3 + 2 seeds × 200 episodes, TD3 `--phi-h 0 --phi-d 0`.

**Prediction**: 6-axis pushes toward R21's 0.444 if there's
training signal left at 75 ep; plateaus near 0.26 if not.

## Part B — Implement proper normalized action penalty

**Question**: Can we keep PHI_H/PHI_D > 0 (paper Eq.14 semantics)
but rescale the action-cost magnitude to O(1)?

**Method**: Add `V4Config.action_penalty_mode = "normalized"`
that penalizes the [-1, 1] normalized action instead of physical
ΔM/ΔD. Default remains `"physical"` for bit-identical paper
reproducibility.

**Validation**: Sweep TD3 with `--normalize-actions` and compare
against the R40 phi=0 ablation. If normalized-mode reaches similar
6-axis (≥0.20), it's the recommended production setting going
forward.
