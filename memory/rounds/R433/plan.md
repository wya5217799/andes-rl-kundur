---
round: R433
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-19'
closed: '2026-08-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R433 plan — SAC 动作应力惩罚（R431 唯一剩余守卫缺口的 reward-shaping 修复，owner 并行批令）

**Opened**: 2026-08-19
**Driver**: owner direct order 2026-08-19 ("cpu 不饱和，启动任务，尽量堆满硬件"):
R431 (CLM-1315) closed the slew-validity gap (all_rows_valid) but both SAC
arms still fail the action-stress guards (action_rms/action_variation
20/20 blocks) while the message arm passes the common-frequency and
worst-peak no-harm guards — the remaining single guard class is the
learned policy's action energy vs the deterministic reference. This round
adds an action-stress penalty term to the SAC reward (reward shaping, the
R86-approved break-out axis), keeps everything else R431-verbatim, and
re-tests the same five seeds. R431 plan gate 5 (no third SAC attempt by
that round's outcome) binds R431 only; this is a new round re-contracted
by the owner's explicit order.
**Parent**: R431/CLM-1315 (CANARY-FAIL, action-stress gap), R430/CLM-1310,
R428/CLM-1305, R419/CLM-1245 (scalar anchor).

## TL;DR

Workload: `evidence`; frozen training + evaluation. Single scientific
factor vs R431: the SAC arms' per-step reward gains an action-stress
penalty term `p_i = -mean_j(a_ij^2)` (projected executed action vector,
per agent, normalized M/D components) with a pre-registered coefficient
`lambda_p` selected on declared development data before sealing; training
and evaluation otherwise R431-verbatim (slew projector 0.25/step, seeds
401-405, scalar 401-403 byte-anchor, frozen classifier/estimators, no
tuning, no outcome-based selection on the holdout).

## Methodology

- Import the frozen R431 runner chain verbatim; rebind round/result/
  lifecycle paths to R433.  New runner `scripts/run_r433_sac_stress_penalty.py`
  = R431 runner with one declared seam: the reward builder
  `adapted_step_rewards` gains the penalty term (marked `R433-SEAM`),
  drift-pinned by a unit test that strips the seam and asserts
  byte-identity with the frozen R431 source (R431/R428 pattern).
- **Exact formula (semantic-gate requirement, verbatim)**:
  `r_i' = r_i + lambda_p * p_i`, where
  `r_i = 100*r_f,i + 50*r_abs,i + 0.0056*r_h + 0.0056*r_d` (R431-verbatim,
  rebuilt from the obs row, normalized denominators 600/600) and
  `p_i = -mean_j(a_ij^2)` over j in {normalized delta-M, normalized
  delta-D}, `a_ij` = the i-th agent's j-th component of the **projected
  executed** action (the same action `env.step` receives).  `p_i <= 0`
  always; per-step, per-agent, no discounting change, no state change.
- `lambda_p` selection (development, pre-seal, declared identity): short
  development trainings (one dev profile partition, seed 401, 8,640
  steps) at lambda_p in {1.0, 5.0, 10.0, 20.0} measure the per-step
  action-RMS trend vs the R431 no-penalty baseline; the smallest
  lambda_p whose training action-RMS drops >= 20 % vs the R431 baseline
  is frozen in the seal.  The formal holdout (8-profile matched bundle,
  seeds 401-405) is never used for selection.
- Semantic gate (R424): plan carries the exact formula above; rehearsal
  runs a gradient-direction probe on the real learner (the penalty-term
  gradient must align with decreasing `mean_j(a_ij^2)` — penalty means
  descent); a targeted unit test pins the same direction on the reward
  builder.  Run `objective_semantics_lint.py R433` before close.
- Scalar dispatch: seeds 401-403 keep `record_scalar_anchor=True`
  (byte-identical to R419 required); 404/405 fresh with no anchor.
- Capacity: reuse the R429 v3 / R431 ladder after a fresh host snapshot;
  R433 selects 16 workers (measured envelope; sibling R432 in flight
  declared below; total-memory accounting per CLAUDE.md).

## Frozen scientific contract

R431 plan and seal remain the scientific contract with one declared delta:

1. **Action-stress penalty on the SAC reward** (the single scientific
   factor): `r_i' = r_i + lambda_p * p_i`, `p_i = -mean_j(a_ij^2)` on the
   projected executed action, per step, per agent, applied in training
   only (evaluation protocol unchanged; the eval reward is not consumed).
2. Seeds 401-405, scalar 401-403 byte-anchor required, 404/405 fresh.

All other fields inherited from R431/R430: eight profiles, 43,200
interactions/run, deterministic SAC evaluation (projected), frozen
classifier, frozen estimators, direct bounded delta-M/delta-D decoder,
no warm start, no checkpoint reuse, no tuning, no outcome-based
selection on the holdout.

## Pre-registered decision tree

1. Any missing/corrupt/non-finite shard or evaluation TDS failure =>
   `CANARY-INVALID`; preserve artifacts, no in-round retry.
2. Otherwise run the frozen classifier.  If any adapted-SAC arm passes
   every physical guard or the classification flips to CANARY-PASS, stop
   at the claim gate and ask the owner (pause branch) — no promotion to a
   universal SAC claim without review.
3. If both SAC arms remain invalid on the action-stress guards despite
   the penalty, report the bounded endpoint: action-energy shaping at
   lambda_p did not make the bundle valid; the message arm's
   frequency-restoration passes and endpoint contrast are re-measured on
   valid rows.
4. Compare only same-contract endpoints/guard distributions: R433 vs
   R431 (action-stress gap), R430 (invalid bank), R428 (collapse).
   The key readout: whether the message arm can hold its
   common-frequency/worst-peak passes AND the valid-trajectory endpoint
   advantage (0.635/0.590x, +25.0%/+34.1%) while the action-stress
   guards pass.
5. No rate projection, reward retuning beyond the frozen lambda_p, alpha
   tuning, architecture change, fresh bank, or third attempt is
   authorized by any outcome of this round.
6. Reward-family closeout reports the project multi-axis readout; the
   paper `cum_rf` readout is not produced by this bank
   (`reward_used_for_gate` false) — reported as unavailable, no dual
   metric disagreement to collapse.

## Capacity and execution card

- Prior representative evidence: R429 v3 ladder (rung 16 valid), R431
  fresh reuse (15 workers, 3.5 h wall, healthy); R433 reuses after a
  fresh no-other-process snapshot and live-load check (owner rule
  2026-08-19: check hardware at task start/end, saturate the host).
  Preflight enforces budget <= measured successful rung (16) + reserved
  (5), so R433 freezes 15 workers (wsl 16, budget 21) — the measured
  envelope, one worker under the rung-16 anchor.
- Frozen budget: `host_process_budget: 21`,
  `wsl_python_processes: 16` (15 workers + 1 driver),
  `native_threads_per_process: 1`,
  `other_reserved_processes: 5` (sibling round R432: 4 workers + 1
  driver; R432 closed 2026-08-19 01:43 local, budget now fully owned by
  R433 while the sibling declaration stays frozen).  Total 21 <= 32
  logical CPUs; total-memory accounting:
  19 concurrent workers x 0.944 GiB (R429 measured floor) + 3 GiB OS
  floor ~= 21 GiB <= 27 GiB WSL MemTotal.
- Ready jobs: fifteen training shards (3 arms x 5 seeds) in one wave at
  workers=15 (~3.5-4 h), then sixteen evaluation shards in one wave
  (~4 min), then serial classify.

Execution readiness is `MEASURE-FIRST` until capacity reuse, targeted
tests, preflight, and rehearsal (incl. the gradient-direction probe)
pass; then `RUN-READY`.  Sealed concurrency is immutable.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r433_sac_stress_penalty.py --shards tmp/andes/r433_train_shards.json --workers 15 --round R433`, then the same driver with `tmp/andes/r433_eval_shards.json`, then `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r433_sac_stress_penalty.py classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r433_sac_stress_penalty.py rehearse`
- rehearsal_scope: same-pre-attempt-path; source/parent/runtime/output
  guards, one real physical step and batch update per arm through the
  projected + penalized path, SAC semantics probe, penalty gradient-
  direction probe + penalty-exactness probe (semantic gate), save/load,
  explicit R433 output-root resolution; creates no formal artifact
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence, penalty_direction_probe
- capacity_evidence: memory/rounds/R433/capacity_evidence.json
- host_process_budget: 21
- wsl_python_processes: 16
- native_threads_per_process: 1
- other_reserved_processes: 5

## 资产保护契约

- Byte-unchanged/read-only: R419-R431 sources, seals, results, claims,
  feeds; `sac.py`, V4 environment, classifier, decoder, estimators,
  `per_vsg_md.py`, the R431 runner (drift parent).
- New only: R433 runner/tests (verbatim copies with the declared reward
  seam + drift test + direction test), R433 lifecycle artifacts,
  create-only R433 results and closeout ledger/feed/claim.
- Dirty worktree preserved; no reset/clean/stage/commit; no manuscript
  prose.

## Gate calibration target

At closeout record whether the penalty-formula semantic gate, the
dev-lambda selection, and the saturated-host budget declaration were too
hard/soft/right.  No gate is relaxed inside the attempt.

## Cross-references

- R431/CLM-1315 (action-stress gap), R430/CLM-1310 (invalid bank),
  R428/CLM-1305 (collapse), R419/CLM-1245 (scalar anchor).
- Parallel sibling round: R432 (B3 diagnostics; `other_reserved_processes`
  declared above).
- Workflow authority: `paper/yang_md_decoupling_marl/LINE.md`, the owner
  order in this task, `CLAUDE.md`, `skills/kundur-round/SKILL.md`.
