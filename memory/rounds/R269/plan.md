---
round: R269
state: completed
opened: '2026-07-25'
closed: '2026-07-25'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R269 plan — objective-validity audit before any second residual training

**Status**: ACTIVE
**Opened**: 2026-07-25
**Driver**: Q-0031 after the clean R268 residual-interface NO-GO
**Parent**: CLM-0540
**Prospective claim slot**: CLM-0545

## TL;DR

Use only synthetic arrays and the existing R268 trajectories to test one
simple, dimensionless residual-learning loss.  It must distinguish common and
differential frequency modes, charge the learned residual rather than the
fixed droop prior, expose temporal movement, and reproduce the ordering of the
project's physical endpoints.  No new ANDES trajectory or controller training
is allowed in this round.

## Falsifiable objective

Determine whether a simple auditable residual-learning objective can align
physical common-mode restoration, differential synchronization, and
residual-specific effort/variation before authorizing a second controller
training run.

## Methodology

## Frozen candidate contract

For physical 60-Hz deviations `df_i` and normalized raw residual actions
`r_i=[r_M_i,r_D_i]`, define four lower-is-better per-step terms:

1. `common = abs(mean_i(df_i)) / 0.05`;
2. `differential = mean_i((df_i - mean_i(df_i))^2) / 0.05^2`;
3. `residual_effort = mean_i(sum_c(abs(r_i,c))) / 2`;
4. `residual_variation =
   mean_i(sum_c(abs(r_i,c-r_prev_i,c))) / 4`.

The scalar loss is the unweighted sum of the four dimensionless terms.
The divisors are fixed before the audit:

- `0.05 Hz` is the existing conservative physical settling band;
- a two-component residual in `[-1,1]` has maximum L1 effort `2`;
- a two-component residual can move at most `4` from `-1` to `+1`.

The first residual action has zero variation cost, matching the project's
action-total-variation endpoint, which starts from the first inter-step
difference.  A future implementation must return the same cooperative scalar
reward to all agents; the four terms remain separately logged and physical
safety/failure endpoints remain external guards.

This round audits the contract; it does not yet modify the environment reward
or train a policy.

## Source-level diagnosis to test

The audit must verify from the existing V4 configuration and reward source:

- `PHI_ABS=0` in the R268 training log, so uniform/common-mode frequency error
  is absent from the learning objective;
- the synchronization reward is invariant to a uniform frequency shift;
- inertia/damping action penalties use fleet/neighborhood averages of executed
  action, so opposing learned residuals can cancel before squaring;
- the residual adapter currently delegates reward computation to the base V4
  environment and therefore does not add residual-specific effort or
  variation terms.

## Prospective validity checks

### Synthetic sign and unit checks

All must pass:

1. a uniform `+0.05 Hz` four-agent shift produces
   `common=1`, `differential=0`;
2. `[+0.05,-0.05,+0.05,-0.05] Hz` produces
   `common=0`, `differential=1`;
3. a zero residual has zero effort and zero variation;
4. opposing nonzero residuals have positive effort even when their fleet mean
   is zero;
5. a constant residual has zero inter-step variation, while a sign switch has
   positive variation;
6. non-finite, wrongly shaped, or out-of-bound residual input is rejected.

### Archived-trajectory checks

Using only the 16 R268 JSON traces:

1. the audit's accumulated common term must be exactly proportional to
   `vsg_mean_iae_hz_s` and preserve its controller ordering for every
   scenario;
2. the accumulated differential term must be exactly proportional to
   `normalized_sync_loss_hz2` and preserve its controller ordering for every
   scenario;
3. reconstructing raw residual actions from the recorded executed action,
   prior law, previous local frequency, `k=10`, and `beta=0.10` must stay
   inside `[-1,1]` and reproduce recorded actions within `1e-5`; step zero is
   excluded because the reset observation was not recorded;
4. droop must have zero residual effort/variation by definition;
5. the audited R268 residual-minus-droop physical common and differential mean
   directions must both remain worse, reproducing the registered NO-GO rather
   than reversing it through scalarization.

## Pre-registered outcomes and decision gate

### PASS

All source, synthetic, and archived-trajectory checks pass.  Close Q-0031
positive only as an **objective-contract feasibility** result.  This authorizes
one separately planned training pilot using the frozen loss; it is not
controller-performance evidence.

### FAIL

Any check fails or requires selecting a scale/weight after inspecting the R268
effects.  Close Q-0031 negative and pivot away from learned residual control
on this environment rather than trying another objective or architecture.

There is no intermediate category: all enumerated semantic checks either pass
or fail.  The existing R268 `cum_rf_total` synchronization-only diagnostic is
reported alongside the two physical endpoints to expose the old reward's
ranking, but has no rescue threshold because it is blind to common-mode
frequency error.  The audit does not use or optimize `geo`.

## Asset protection and scope limits

- Reuse `physical_endpoints.py`, R268 traces, and residual composition
  semantics; do not mutate R268 evidence.
- Add one pure objective module, one audit script, and focused tests.
- Do not change `base_env.py`, `residual_adapter.py`, TD3/SAC, V4 defaults,
  training scripts, checkpoints, historical traces, paper metrics, manuscript
  files, or figures.
- Do not run ANDES, train, tune weights, sweep algorithms/seeds/horizons/scales,
  or claim topology, stability, cross-simulator, or publication readiness.

## Verification

- `python memory/tools/round_preflight.py R269 --json`;
- focused objective tests;
- `python -m pytest tests -q`;
- `python scripts/audit_residual_objective.py`;
- `python memory/tools/dual_metric_lint.py --claim CLM-0545`;
- `python memory/tools/validate.py`;
- `python memory/tools/render.py`.

## Planned outputs

- `src/andes_rl_kundur/evaluation/residual_objective.py`;
- `scripts/audit_residual_objective.py`;
- `tests/test_residual_objective.py`;
- `results/r269_objective_audit/objective_audit.json`;
- `results/r269_objective_audit/objective_audit.md`;
- CLM-0545, R269 verdict, Q-0031 update;
- no new simulation/training or manuscript artifacts.

## Cross-references

- CLM-0495: recurrent-target correctness defect; no legacy recurrent result is
  treated as corrected evidence.
- CLM-0540 and `results/r268_residual_pilot_eval`: measured R268 NO-GO and the
  only trajectory bank used here.
- Q-0031: objective/interface validity must precede a second training run.
