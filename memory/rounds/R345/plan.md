---
round: R345
state: aborted
manuscript_line: decoupling-marl-model-first
opened: '2026-08-06'
closed: '2026-08-06'
supersedes_rounds: []
superseded_by_round: null
abort_reason: 'sealed create-only analysis invalid: at least one outcome-seeing residual
  optimizer failed the frozen validity gate; retry forbidden'
superseded_note: null
---
# R345 plan - create-only residual-headroom analysis

**Opened**: 2026-08-06
**Driver**: Decide whether the frozen deterministic bridge leaves enough
observable and physically usable residual for one non-learning physical probe.
**Parent**: CLM-0910; Q-0091

## TL;DR

Read the existing R344 paired traces only. Build one frozen, outcome-seeing
edge-residual upper bound and one causal neighbour-local reconstruction. Never
run ANDES or training. The only positive outcome is eligibility for a separate
sealed non-learning residual probe; neural training remains blocked.

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

**Lane**: evidence. The analysis changes Q-0091 disposition and therefore owns
one round even though it creates no physical trajectory.

**Frozen inputs**:

- `memory/rounds/R344/formal_seal.json`, SHA-256
  `eec71696276e45ead9f85bd2f7c932f4a2aeae37f6ceabe3d570871e3c129a8d`;
- `results/r344_deterministic_bridge/formal_execution.json`, SHA-256
  `8a82763ce1b3f777c4e7a1429f92651eb88d94d0bc238ee0c06664be6676bbd1`;
- `results/r344_deterministic_bridge/formal_analysis.json`, SHA-256
  `41c8e73deadbf30d0352dc5a20f82938ad3723ca7f2467a86f2d8f494996ad72`;
- `results/r344_deterministic_bridge/formal_manifest.json`, SHA-256
  `3752b735536c599bc920b2f792ca1d677876436421858614c046707ab66e8b24`;
- `results/r341_staged_fresh_model_validation/candidate_models.json`, SHA-256
  `7a74cb78dca8c5e30f32a344ca43704079a1549c966ff21de492eba7a3f1e32e`.

The reader must recover exactly 16 scenario pairs, 32 complete guarded
records, 25 samples per trace, all manifest-bound trace hashes, and the two
point-specific order-12 separate-input models. Any mismatch is engineering
invalidity, not a scientific result.

**Residual estimand**: add a zero-common, three-edge residual sequence on top
of each frozen-controller command. Use the R341 control impulse response and
the actual R344 controlled frequency-coordinate trace to form an optimistic
linear counterfactual. For each scenario, solve the minimum-L2 edge sequence
that reduces both frozen primary endpoints by at least 2%. Enforce the frozen
node-power and node-ramp limits throughout; recompute the full counterfactual
SOC path with the frozen storage efficiencies and bounds. The 2% threshold is
the existing manuscript contract, not selected from R344 outcomes.

Before the minimum-L2 solve, run one fixed feasibility relaxation whose only
two slack variables are the shortfalls from the two frozen endpoint targets.
The zero-residual baseline and its exact target shortfalls provide a feasible
initial point. A valid optimum with nonzero target shortfall is a physical or
material residual-headroom negative, not an optimizer failure; its best
feasible edge sequence remains in the complete oracle bank. A failed,
non-finite, or constraint-invalid relaxation or minimum-norm solve is
`ANALYSIS-INVALID`. The relaxation adds no threshold, estimator, or candidate
selection.

**Model-error separation**: retain the nominal counterfactual and a conservative
mismatch bound separately. For each scenario and coordinate, use the maximum
absolute frozen-controller innovation observed in that scenario as an
additive envelope at every sample. Recompute worst-case common-coordinate IAE
and differential-coordinate energy from `abs(counterfactual)+envelope`.

**Neighbour-local information test**: the oracle action is a target only; it
is never an executable controller. For every action edge and sample, causal
features contain only the two endpoint devices' current physical-frequency
deviation, previous achieved power, and previous commanded power. They contain
no point, disturbance location, sign, scenario identifier, future value, joint
coordinate, or oracle endpoint. Fit deterministic standardized ordinary least
squares independently per edge. Use leave-one-scenario-out folds. Project each
held-out predicted edge sequence to the same node-power, ramp, and SOC-feasible
set before scoring it through the same linear counterfactual and mismatch
bound. No hyperparameter or architecture selection is permitted.

**Statistics and subgroups**: for each candidate and endpoint use per-scenario
signed relative change `(candidate-base)/base`. Require mean improvement at
least 2% and a one-sided 95% paired Student-t upper bound below zero. Require
directional mean improvement separately for both operating points, all four
disturbance locations, and both signs. Include every scenario; no subgroup may
be dropped or pooled after outcome visibility.

**Execution**: implementation and synthetic tests precede the analysis seal.
The sealed run is create-only, reads the frozen inputs once, and writes one
attempt record, one analysis JSON, one manifest, and SHA-256 sidecars under
`results/r345_residual_headroom/`. Sixteen scenario-oracle jobs and sixteen
held-out reconstruction jobs may use at most 16 single-thread worker processes;
the ready-job count is the binding cap, below the already measured 32-process
whole-host capacity, with no other manuscript process reserved. There is no
WSL, simulator, accelerator, training, distributed runtime, reward, policy, or
evaluation entry point.

## Experiment efficiency card

- **Execution readiness**: RUN-READY.
- **Decision and stage**: frozen create-only offline analysis of Q-0091; the
  active R345 plan is the scientific authority.
- **Cheapest decisive work**: exactly 16 oracle jobs followed by 16 local
  projection jobs; no simulator or training work is needed for this decision.
- **Completion and stop rules**: completion is the create-only attempt,
  analysis, manifest, and sidecars. Any input drift, corrupt artifact,
  optimizer invalidity, or projection invalidity writes `ANALYSIS-INVALID` and
  forbids retry in R345. There is no scientific early stop.
- **Resource evidence**: R344's accepted whole-host ladder completed 32 jobs at
  16, 24, and 32 single-thread workers without swap and selected 32 by measured
  throughput. No other manuscript execution is reserved. R345 has only 16
  simultaneously ready jobs, so ready work is the binding cap.
- **Plumbing check**: a pre-seal synthetic 25-sample rehearsal reused one
  16-worker Windows process pool across both waves, admitted all 16 jobs,
  completed them validly, and pinned OMP, OpenBLAS, MKL, and NumExpr to one
  native thread. The 1.453-second oracle wave used 11 distinct processes
  because its synthetic jobs were shorter than lazy process startup; all 16
  processes were warm for the 0.038-second local wave. Forcing artificial work
  solely to raise utilization is forbidden.
- **Capacity classification**: 16 workers is a derived ready-job cap, below
  the measured 32-process whole-host capacity. The runner offers every ready
  job to the pool and reuses it across the dependency boundary; process
  startup, not a lower configured cap, limits very short synthetic work.
- **ETA and observation**: the representative numerical work is seconds-scale;
  allow up to the quick-run five-minute envelope for real-case conditioning,
  input verification, process startup, serialization, and finalization. Wait
  event-driven for the terminal artifact; do not resize or tune after sealing.
- **Authorized action**: after source closure, focused checks, and round
  preflight pass, create the seal and execute exactly one analysis attempt.

## Gate

`RESIDUAL-PROBE-ELIGIBLE` requires all source/integrity guards, every oracle
solve and physical-headroom guard, and both the oracle and held-out
neighbour-local candidates to pass the nominal, mismatch-bounded, statistical,
and subgroup tests for both endpoints. It authorizes only one separately
sealed non-learning physical residual intervention.

Otherwise classify `NO-TRAINING`. Distinguish an infeasible/immaterial
residual, inadequate neighbour-local reconstruction, model-error-dominated
benefit, and absent physical headroom. Optimizer failure or corrupt input is
`ANALYSIS-INVALID`, aborts the round, and cannot be interpreted as
`NO-TRAINING`.

Every classification sets `training_authorized=false`,
`distributed_runtime_authorized=false`, and `eval_authorized=false`. After the
attempt record exists there is no retry, overwrite, threshold change, subgroup
change, or alternate estimator in R345.

## Engineering seam and test-first return contract

The public seams are the pure residual-analysis functions and the stable
adapter commands `prepare` and `analyse`. Contract tests must establish the
three-edge response map, both-endpoint constrained solve, causal edge-local
feature boundary, deterministic estimator, physical projection, paired gate,
valid target-infeasibility versus optimizer-failure separation, create-only
seal, frozen execution exclusions, and absence of training or EVAL commands.
These tests verify implementation behavior only; they cannot authorize the
sealed analysis or strengthen Q-0091.

## 资产保护契约

R341/R344 seals, traces, manifests, results, controller, thresholds, and
manuscript evidence stay byte-unchanged. Add only the R345 probe, stable
adapter, targeted tests, seal, create-only result root, feed, claim/question
disposition, verdict, and line-navigation reconciliation. No public push.

## Cross-references

- CLM-0910
- Q-0091
- `paper/decoupling_marl_model_first/working/model_contract.md#modeling-and-simulation-workflow`
- `paper/decoupling_marl_model_first/working/model_contract.md#training-and-eval-gates`
