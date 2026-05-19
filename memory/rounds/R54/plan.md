---
round: R54
state: active
opened: '2026-05-17'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R54 plan — Warmstart-shared probe (cross-agent shared init)

**Date**: 2026-05-17
**Type**: experiment (initialization probe)
**Trigger**: After R49/R50/R51/R52 (CLM-0057/58/59/60) all failed
to break the temporal-flatness ceiling at ~0.334, the remaining
cheap lever is the cross-agent-coordination sub-problem.
R49-R52 all touched obs/reward/algorithm but none attacked
**cross-agent uniformity directly**. R54 tests whether shared
initialization of all N agents from a single strong actor's
weights promotes coordinated policies that exceed the baseline.

Round number note: this work was originally numbered R53 in
session draft, but Codex landed R53 ("memory hygiene dogfood")
in parallel — commit `4e7a335` — while these trainings were
running. Renumbered to R54 to avoid collision; result JSONs
retain the `r53_*` prefix from when they were named.

## Setup

3 seeds × 75 ep,
`python scripts/train.py --algo td3 --normalize-actions
--episodes 75 --seed <S> --hidden-size 64
--warmstart-shared results/td3_norm_h64_s51/agent_0_best.pt
--warmstart-mode actor_and_critic
--save-dir results/td3_norm_h64_warmsh_s<S>`.

The `--warmstart-shared` flag (train.py:287-303) loads ONE actor
ckpt into ALL N agents of new training. After init, agents train
independently with their own per-agent gradients, so weights
diverge over time. The probe tests whether the shared-policy-space
starting point produces a more coordinated trained outcome than
fresh independent init.

**Source actor**: `results/td3_norm_h64_s51/agent_0_best.pt` —
agent_0 of the strongest single non-lucky seed (s51, geo 0.365).

**Seeds**: 49, 50, 52. (s49/s50 have R48-β fresh baselines for
direct per-seed comparison; s52 is fresh for additional data.
Did not use s51 because warmstart-from-self adds little signal.)

## Predictions

| outcome | 6-axis | interpretation |
|---|---:|---|
| ≥ 0.40 | strong win | shared init unlocks coordinated wide-action policy |
| 0.35-0.40 | meaningful win | partial unlock; structural ceiling moved |
| 0.32-0.35 | marginal | similar to baseline; symmetry doesn't persist long |
| 0.20-0.32 | small drop | shared init biases toward narrower policy space |
| ≪ 0.20 | catastrophic | divergence forces bad late-training drift |

**Diagnostic to watch**:
- cross-agent corr_dM / corr_dD (expect higher than baseline ~+0.15
  if shared init promotes coordination)
- per-agent dM_span / dD_span (expect comparable to baseline OR
  higher if uniformity helps)
- settling axis (s51's strength — does it propagate?)

## Out of scope

- True parameter sharing (one actor, all agents call it) — requires
  SharedTD3Agent wrapper (~1-2 hr impl). R54 tests shared init
  only, NOT permanent sharing.
- LSTM actor (~1 day)
- Windowed-horizon reward (~30 min impl)
- Curriculum disturbance (~2-3 hr)
- Combined warmstart + obs/reward variants

## Addresses

The cross-agent-coordination sub-mechanism untouched by R49-R52.
If this fails too, the structural ceiling at 0.334 is bounded by
SIX independent attacks (5 prior + this).
