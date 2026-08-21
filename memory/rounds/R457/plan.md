---
round: R457
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-20'
closed: '2026-08-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R457 plan — M2 critic-head 稳定化、动作梯度校准与物理因果审计

**Opened**: 2026-08-20  
**Workload**: `evidence`; fixed-replay mechanism experiment plus independent
online physical evaluation, not a replacement production training run.  
**Driver**: R427 suppressed aggregate critic-loss growth without closing any
common-frequency/worst-peak guard, so loss divergence is not sufficient; M2
requires a head-selective intervention, gradient mediation and physical
confirmation before any causal attribution.  
**Parents**: CLM-1265 (R421), CLM-1290 (R425), CLM-1300 (R427), CLM-1320
(R432), CLM-1335 (R435), M2 advisory.

## TL;DR

For each CD information pattern and seed 401..405, create one closed 24-episode
development replay (720 transitions) from a prospectively seeded, fixed fresh
behavior actor. Four cells start from byte-identical fresh weights and consume
identical replay rows, minibatch indices and target-noise seeds:
`none`, `differential_only`, `common_only`, `both`. Phase 1 freezes actors for
512 critic updates; Phase 2 runs 256 further critic updates and 128 delayed
actor updates. Selected heads receive true output-preserving PopArt; all other
learner/reward/dual/mapper/slew settings are R425.

Each of 40 policies is then evaluated on four independent evaluation profiles
× six scenarios × 30 steps (960 trajectories). A separate two-scenario
symmetric calibration uses three fixed amplitudes (0.02/0.05/0.10) along two
common and six orthonormal differential action directions (3 for M, 3 for D):
40 × 2 × (1 + 8×3×2) = 3,920 trajectories. Calibration compares centered
physical return slopes to saved per-head critic action gradients, including
return/cost sign, slew and projection activity.

R427 is an immutable historical anchor. Its running-stat update does not remap
the last layer, so it is not output-preserving PopArt; R457 records that semantic
fact and does not require the new `differential_only` cell to be numerically
identical to the legacy update. This correction changes the new intervention,
not any R427 bytes or observations.

## Snapshot at plan-time (oracle as of 2026-08-20)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] finite-bank information-level margin program; R457 does
  not answer it.

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375.
- Q-0004 closed-negative @ R442, by CLM-1370.
- Q-0111 closed-negative @ R397, by CLM-1130.

## Methodology

### Frozen objects and identities

- Arms: `cd_matd3_no_message`, `cd_matd3_message`; seeds 401..405; cells exactly
  `none`, `differential_only`, `common_only`, `both`.
- Replay for one arm/seed is generated once from the same R425 architecture at
  fresh seeded initialization, constant exploration noise 0.1 and the frozen
  four development profiles/six scenarios. It stores joint/next observations,
  previous and executed actions, two signed rewards, done, profile/scenario,
  episode boundaries, initial frequency and physical action/readback metadata.
- Profiles A-C (540 rows) are learner replay; profile D (180 rows) is held-out
  diagnostics only. Batch size 256; phase counts 512/256. Ordered batch-index
  arrays and one target-noise seed per update are stored inside the closed
  replay and reused by all four cells.
- Every cell is constructed after identical Python/NumPy/Torch seeding. Initial
  actor, target actor, critic and target critic tensors must hash identically.
  Lagrange and RMS/TV duals replay the same 24 episode totals before learning
  and are frozen thereafter. Optimizer, target schedule and hyperparameters are
  identical; no evaluation endpoint is available until all policies close.

### Head-selective stabilization semantics

- Differential = critic column 0; common = column 1. For a selected head,
  target running mean/variance uses beta 1e-3 and sigma floor 1e-4.
- Before the loss, changing `(mu_old,sigma_old)` to `(mu_new,sigma_new)` remaps
  each online/target twin output row:
  `W_new=(sigma_old/sigma_new)W_old`,
  `b_new=(sigma_old*b_old+mu_old-mu_new)/sigma_new`.
  Original output `sigma*q+mu` must remain within 2e-5 relative/absolute error.
  Adam moments on remapped online rows are transformed in the corresponding
  coordinate system. Unselected output rows and stats must remain exact.
- Bootstrap, target noise, twin minimum, normalized regression, original-scale
  readout and actor critic read are symmetric between heads. `none` applies no
  normalization; `both` applies the same rule independently to both columns.

### Two-phase and mediation measurements

- Phase 1: actor and actor target hashes must remain exact while critics and
  critic targets update. At updates 0/32/.../512, record per-head/twin original
  and normalized held-out TD RMSE, target/value quantiles, min-active fractions,
  stats, finiteness and original-scale Q4/Q1.
- Phase 2: continue critics; actor updates only on the frozen delayed schedule.
  At the same cadence record separate differential/common/guard gradient norms,
  differential-common cosine, applied parameter/action displacement, and the
  phase-1-to-phase-2 ordering. No replay-dependent online rollout occurs.
- `normalization_semantics_probe` must verify the formulas, invariant remap,
  unselected byte equality, checkpoint roundtrip, and the legacy R427
  non-preservation fact. `penalty_direction_probe` must verify differential and
  common value signs plus the R425 RMS/TV penalty direction.

### Physical confirmation and calibration

- Deterministic evaluation uses the full R425 evaluation bank and unchanged
  `summarise_profile`. Physical guards relative to each cell's matched `none`
  policy: common IAE, worst peak and RoCoF <=1.03×; action RMS/TV <=1.10×;
  saturation <=0.05; variation and per-VSG dispersion >1e-6.
- Calibration scenarios are frozen to `canary_eval_a_common_positive` and
  `canary_eval_d_localized_negative`. Directions use normalized Helmert columns
  over four VSGs, separately in M and D, plus normalized all-one M/D directions.
  The first raw policy action is shifted before the unchanged runtime projector;
  later actions follow the unshifted policy, matching an initial-action Q gradient.
  Three amplitudes are reported independently; no amplitude is selected.
- Centered slopes use complete discounted (gamma=.99) differential/common
  signed returns from the implemented physical cost seam. Critic directional
  derivatives are taken at the matching initial state/action. Report sign
  agreement, normalized magnitude error, amplitude consistency and realized
  executed-direction Jacobian. Projection/slew degeneracy invalidates that
  direction rather than being interpreted as gradient error.

## Theory intake

```
observable: heldout_head_td_error
  source: results/research_loop/r457_m2_head_causality/learn/*/*/seed*/diagnostics.json
  predicts: common_only improves common original-scale held-out TD RMSE >=20% vs none in >=4/5 seeds per arm
observable: head_gradient_calibration
  source: results/research_loop/r457_m2_head_causality/calibration/*/*/seed*.json
  predicts: common_only raises common-direction sign agreement >=0.25 and lowers normalized magnitude error >=20% vs none and differential_only in >=4/5 seeds per arm
observable: actor_mediation
  source: results/research_loop/r457_m2_head_causality/learn/*/*/seed*/diagnostics.json
  predicts: phase-1 common-error improvement precedes >=1% fixed-validation actor-action displacement with a material common gradient in >=4/5 seeds per arm
observable: selective_physical_response
  source: results/research_loop/r457_m2_head_causality/formal_analysis.json
  predicts: common_only improves aggregate common IAE and worst peak >=5% vs none and >=3% vs differential_only in >=4/5 seeds per arm without disqualifying differential/action guards
```

## Gate

Integrity failure (source/seal/sidecar drift, replay/count/minibatch/noise mismatch,
initial-weight mismatch, incomplete phase, actor movement in phase 1, PopArt
invariance/unselected-row failure, nonfinite values/gradients, physical TDS or
calibration degeneracy/completeness failure) => `CANARY-INVALID` and no retry.

Valid outcome, paired within arm/seed:

1. `COMMON-HEAD-CAUSAL-SUPPORTED` requires all four Theory-intake predictions
   and the selective guard condition in >=4/5 seeds of both arms.
2. `NONSELECTIVE-CRITIC-COFACTOR` requires >=20% held-out improvement and >=5%
   physical common/peak improvement for `both` or `common_only` in >=4/5 seeds
   of both arms, but the common-only selectivity/gradient mediation gate fails.
3. `CRITIC-DIAGNOSTIC-ONLY` requires held-out or calibration improvement in
   >=4/5 seeds of either arm while no stabilization cell obtains >=5% common/
   peak physical improvement in >=4/5 seeds.
4. `COMMON-HEAD-HYPOTHESIS-REFUTED` requires valid complete measurements and
   common-only fails the 20% common held-out improvement in both arms, or
   differential-only matches/beats common-only common/peak physical response in
   >=4/5 seeds of both arms while common calibration is not better.
5. Otherwise `M2-INCONCLUSIVE`. Multiple first-three tags may coexist; the
   refuted tag is exclusive. No result authorizes retuning, replay regeneration,
   online training, bank expansion or universal critic claims.

## Formal launch contract

- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r457_m2_head_causality.py rehearse`
- formal sequence: `prepare`; replay shared-driver launch over 10 shards;
  `close-replay`; learner launch over 40 shards; `close-learn`; evaluation launch
  over 40 shards; calibration launch over 40 shards; `aggregate`.
- all shared-driver launches call the sealed runner as `shard <id>`. Fresh R457
  capacity selected 8 workers because learner throughput peaked there while
  12/16 workers regressed, although physical throughput still rose; every formal
  stage therefore uses the joint-safe selected 8, never a per-stage best-of rung.
- capacity_evidence: `memory/rounds/R457/capacity_evidence.json`
- host_process_budget: 9
- wsl_python_processes: 9
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- R421/R425/R427/R432/R435/R456 code, checkpoints, results, plans and feeds are
  read-only. No old checkpoint or replay is rewritten.
- New only: R457 head-selective module/tests/runner/tests, R457 ledger files,
  create-only `results/research_loop/r457_m2_head_causality/`, and normal
  feed/claim/manifest closeout.
- Seal freezes plan, sources, thresholds, all replay/learner/evaluation/
  calibration inventories and parent hashes. Formal failure preserves bytes and
  closes the round; no automatic retry or tuning.

## Cross-references

- `paper/yang_md_decoupling_marl/working/vsg_failure_math_advisory_20260820/problems/M2_critic_divergence_causality.md`
- `tmp/yang_md_decoupling_marl/m2_head_specific_critic_execution_draft.md`
- R421/R425/R427/R432/R435 feeds and CLM-1265/1290/1300/1320/1335.
