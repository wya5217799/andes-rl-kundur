---
round: R348
state: aborted
manuscript_line: decoupling-marl-model-first
opened: '2026-08-06'
closed: '2026-08-06'
supersedes_rounds: []
superseded_by_round: null
abort_reason: 'sealed analysis invalid: six fully normalized minimum-norm solves returned
  feasible original-unit points but no solver success certificate; retry forbidden'
superseded_note: null
---
# R348 plan - fully normalized residual-headroom analysis

**Opened**: 2026-08-06
**Driver**: Answer Q-0091 after R347 proved the relative-slack stage valid but
localized one remaining numerical divergence to the minimum-norm stage.
**Parent**: CLM-0910; Q-0091; aborted R345/R346/R347

## TL;DR

Run the unchanged R345/R347 scientific analysis once under a fresh seal. Keep
R347's relative feasibility slacks, and make the minimum-norm optimizer fully
dimensionless by scaling edge variables with the frozen node-ramp limit and
normalizing constraint residuals with their frozen physical or endpoint
scales. This changes neither the feasible set nor the minimizer. No simulator,
reward, policy, EVAL, distributed runtime, or neural training is allowed.

## Snapshot at plan-time (oracle as of 2026-08-06)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0091 [opened R344] Does the frozen deterministic bridge leave material, observable, and physically usable residual headroom before neural training?

## Recently Closed (last 3)

- Q-0090 closed-positive @ R344, by CLM-0910 — Can the fresh-qualified predictor support a deterministic physical bridge before any distributed or learning experiment?
- Q-0089 closed-positive @ R341, by CLM-0900 — Does the selected predictor preserve its registered waveform envelope on an untouched operating-point bank?
- Q-0087 closed-partial @ R339, by CLM-0890 — Which location-dependent input dynamics explain the upstream-load mismatch before any bridge repair?

## Methodology

**Lane**: evidence. R348 reads the protected R344 outcome bank and may dispose
Q-0091, so it owns one prospective create-only attempt and the complete
publication lifecycle if scientifically valid.

**Frozen parent chain**:

- R345 scientific contract payload SHA-256
  `6492c9a8b087eabcd41222b3bb246c167936e1e82f8de33b5de3a6daf41fd1ab`;
- R345 seal/failure SHA-256
  `47f1b287316f1475725a2c844f470016058ec06f5759d1d743829c74afbc04f4` /
  `8a519fb736151ea793f18cff2b0d08de65d810dd8f49425104cd9f68de08c9a3`;
- R346 diagnostic SHA-256
  `8d3e9482b55167622b81f0e574b29a968d427fa944afe65ddc7383f51c1b3d41`;
- R347 seal SHA-256
  `f91a223aac0d96435230ebc371ae398a7e300e9e9327fbf1320fbe02790e22e7`;
- R347 oracle diagnostic SHA-256
  `608169c63d5bd5eb16c7b01fa753d5dc49d2b6b705b1f333ed72608d0c914399`;
- R347 failure SHA-256
  `feb8ea6f9b4d2dacbd0584b8afb0342a0857f4a45897a98530a1db45747b6a69`.

R346/R347 per-case status, residual, iteration, and objective fields authorize
only the numerical repair below. They cannot change a threshold, case,
estimator, subgroup, or scientific interpretation.

**Unchanged science**: use exactly the same R344/R341 frozen inputs, sixteen
paired scenarios, 32 complete records, 25 samples, zero-common three-edge
residual, optimistic response map, mismatch envelope, physical limits,
neighbour-local causal features, independent per-edge standardized ordinary
least squares, leave-one-scenario-out folds, projection, endpoints, 2% mean
improvement floor, one-sided 95% paired Student-t bound, and point/location/sign
directionality gates declared by R345 and repeated by R347. Include every
scenario. R348 does not add a candidate or tuning parameter.

**Single numerical repair**:

1. retain R347's two nonnegative relative endpoint-shortfall variables,
   initialized at exactly `0.02` and minimized by their squared norm;
2. optimize dimensionless edge variables `z`, decoding physical edge action as
   `node_ramp * z`, where `node_ramp` is the already frozen physical limit;
3. divide endpoint constraint residuals by that scenario's positive baseline
   endpoint; divide node-power and node-ramp residuals by their frozen limits;
   divide state-of-charge residuals by the frozen state-of-charge span;
4. after each solve, recompute feasibility in original physical units and
   enforce the unchanged absolute `1e-8` validity tolerance.

Multiplying the objective by the fixed positive node-ramp factor and scaling
each inequality by a fixed positive quantity preserves the exact feasible set
and minimizer. Synthetic tests must verify original-unit feasibility,
reachable/unreachable separation, output-scale stability, and invariance of
the decoded minimum-norm solution against an analytically worked case.

**Execution**: implementation/tests precede the seal. Write a create-only
attempt, execute sixteen oracle jobs and sixteen local projection jobs with at
most sixteen single-thread Windows workers in one reused process pool, and
persist a metadata-only oracle diagnostic before any invalidity stop. A valid
attempt writes analysis and manifest sidecars. There is no retry, overwrite,
resizing, threshold edit, case drop, alternate estimator, or further repair in
R348.

**Execution readiness**: RUN-READY. The host has valid measured capacity for
32 single-thread processes; R348 has only sixteen ready jobs and no other
manuscript execution reservation. Prior waves ended within eleven seconds.
Allow the quick-run five-minute envelope and observe only the terminal
artifact.

**Engineering seam**: public fully normalized solver plus adapter `prepare`
and `analyse`. Tests freeze the numerical equivalence, source closure,
create-only persistence, sixteen-worker budget, unchanged nested scientific
contract, and absence of simulation/training/EVAL/reward/distributed commands.

## Gate

Use the exact R345/R347 decision tree. `RESIDUAL-PROBE-ELIGIBLE` requires every
valid oracle target solve and physical-headroom guard plus oracle and held-out
local passes for both endpoints under nominal, mismatch-bounded, paired, and
subgroup gates. It authorizes only one separately sealed non-learning physical
probe. Otherwise return `NO-TRAINING` with failed gates. Any optimizer,
projection, source, or integrity invalidity is `ANALYSIS-INVALID` and has no
scientific meaning. Training, distributed runtime, and EVAL remain false in
every branch.

## 资产保护契约

R341/R344/R345/R346/R347 sources, seals, attempts, failures, diagnostics,
traces, manifests, thresholds, controller, and paper evidence remain
byte-unchanged. Add only R348 plan/probe/adapter/tests, seal, create-only
results, and, if scientifically valid, feed, claim/question disposition,
verdict, and manuscript navigation reconciliation. No public push.

## Cross-references

- CLM-0910
- Q-0091
- R345/R347 `ANALYSIS-INVALID`
- R346 `RELAXATION-INVALID`
