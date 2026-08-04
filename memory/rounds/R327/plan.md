---
round: R327
state: completed
opened: '2026-08-04'
closed: '2026-08-04'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R327 plan - sealed legacy-reference recovery amendment

## TL;DR

Close the remaining numerical part of Q-0080 without rerunning the R326
candidate development bank. Keep R326 immutable. Recompute only its eight
missing R325 successful prefixes in two fresh, isolated executions that rebuild
each arm's design locally and preserve the original R325 per-arm synthesis
order. Combine those recovered comparisons with the immutable R326 candidate
and 56 already-admitted reference rows, then apply the unchanged R326 solver
and development gates. Never access the conditional holdout in R327.

## Why this amendment is bounded

- R326 already seals valid candidate completion, residual, constraint, and
  deterministic-development records for all 64 development cases. Repeating
  them would add cost without changing the missing evidence object.
- R326 fails only because five retained-cross and three cross-deleted legacy
  references terminate before their registered R325 successful-prefix targets
  after the synthesized designs are serialized to parallel workers.
- Scratch diagnosis is motivation only, not evidence: one canary's failure
  followed the `filter_gain` memory layout while all array values remained
  byte-identical, and all eight missing prefixes recovered when designs were
  rebuilt and consumed in the original per-arm synthesis order. These
  observations choose the prospective harness but determine no R327 verdict.
- The R326 candidate development ratios are outcome-known. R327 performs no
  weight, threshold, case, solver, or conclusion search. It may only restore
  the preregistered admission ordering and mechanically apply the already
  frozen development gates; no newly prospective performance-effect claim is
  created.

## Methodology

### Frozen implementation contract

- Immutable parents: the R325 seal/execution and the R326 seal, execution,
  analysis, provenance, and run manifest, all verified by their recorded
  SHA-256 digests.
- Exact missing inventory: the eight `(arm, case, nominal-mismatch)` keys
  recorded with `reference_status_matches_r325=false` in R326. No other case is
  eligible for recovery or replacement.
- Each recovery pass starts in one fresh spawned process. The process sets the
  native numerical thread count to the recorded local default of 24, loads the
  sealed parents itself, synthesizes the retained-cross design, recovers its
  five rows, then synthesizes the cross-deleted design and recovers its three
  rows. No synthesized design crosses a process boundary.
- The old SLSQP and candidate sparse-QP implementations, tolerances, horizon,
  state correction, action map, limits, warm starts, and comparison fields are
  exactly those sealed in R326. R327 changes only reference-harness placement
  and ordering.
- Two complete fresh-process passes must be byte-identical after removal of the
  declared creation timestamp. Workers write nothing; the parent writes one
  canonical ordered artifact.

## Scientific acceptance criterion

- Every one of the eight exact reference keys must reach its registered R325
  successful-prefix target in both fresh passes, with no legacy or candidate
  failure and no missing sample.
- On the recovered samples, candidate node and coordinate action plans must
  agree within the frozen `2e-5` absolute bound and predicted outputs within
  `1e-6`.
- Combining the recovered rows with the 56 immutable R326 admitted rows must
  produce 64 complete reference cases and preserve the R326 candidate gates:
  zero candidate solver failures, execution errors, explicit-constraint
  violations, or non-finite values; maximum explicit residual `1e-8`; maximum
  normalized primal and dual residual ratio one; strictly positive action
  Hessian; deterministic execution and analysis replay.
- Only after this combined solver-adequacy gate passes may the analysis read and
  mechanically apply the unchanged R326 development mean/worst performance
  gates. R327 never reads or executes the conditional holdout.

## Comparison-identifiability gate

Decision: QUALIFY.

- Numerical equivalence is identifiable because the mathematical program,
  model state, information, action, limits, solver implementations, successful
  target prefixes, and comparison tolerances are unchanged. R327 changes only
  where and when the legacy reference design is constructed so the comparison
  object matches the R325 execution path.
- The eight recovery cases and harness were selected after observing the R326
  reference failures. They can repair evidence completeness but cannot support
  optimizer-family superiority, runtime portability, or a fresh causal claim
  about numerical layout.
- Any development classification is a mechanical amendment over the
  prospectively generated, immutable R326 candidate outcomes and its already
  frozen gates. Stay out: post-amendment effect estimation, controller
  superiority, general decoupling value, physical behavior, distributed
  execution, agents, learning, topology generalization, stability, and safety.

## Red-green implementation order

1. Add a pure-decision test that fails because no R327 reference-recovery probe
   exists. Cover complete recovery, missing-key rejection, threshold rejection,
   and holdout non-access.
2. Implement the smallest pure probe that validates the eight rows, combines
   them with immutable R326 summaries, and applies the frozen decision tree.
3. Add a thin sealed adapter whose fresh worker rebuilds designs locally in the
   exact arm order; test that no design object is passed into the worker and no
   holdout function is reachable.
4. Run targeted and related regression tests, preflight, seal, execute, analyse,
   independently audit, publish the feed, and close the round.

## Formal outcome tree

- `INVALID-REFERENCE-RECOVERY`: any source hash, parent status, exact-key,
  trace, deterministic replay, R326 validity, or holdout-protection guard fails.
- `REFERENCE-RECOVERY-NO-GO`: the recovery is validly executed but any of the
  eight prefixes is incomplete or any recovered/combined action-output bound
  or candidate solver-residual gate fails.
- `DEVELOPMENT-NO-GO`: combined solver adequacy passes, but either unchanged
  R326 development mean/worst gate fails. Q-0080 may close positive only for
  solver adequacy; the controller remains rejected and holdout stays sealed.
- `DEVELOPMENT-ADMISSION-PASS-HOLDOUT-SEALED`: combined solver adequacy and
  unchanged development gates pass. R327 still does not access the holdout; a
  separately prospective round would be required.

## Scope limits and stopping conditions

- Model-only Windows execution. No ANDES, physical closed loop, plant change,
  new candidate development execution, holdout access, reward, distributed
  runtime, agent implementation, or neural training.
- No source, case, threshold, solver setting, comparison, or classification
  change after the formal seal. R325 and R326 remain byte-immutable.
- EVAL is not applicable because no trained policy or physical trajectory is
  executed.
- The conference title remains exactly `Decoupling-Oriented Coordination of
  Paralleled VSGs With Multi-Agent Reinforcement Learning`; R327 cannot support
  its coordination, distributed-agent, or learning terms.

## Cross-references

- Direct question: `memory/questions/Q-0080.md`.
- Blocking result: `memory/claims/CLM-0840.md` and
  `paper/decoupling_marl_model_first/reports/R326.md`.
- Immutable candidate evidence: `results/r326_solver_adequacy/`.
- Original legacy status authority: `results/r325_constrained_horizon/execution.json`.
