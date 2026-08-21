---
round: R431
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-18'
closed: '2026-08-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R431 plan — SAC 执行层 slew 投影 + 五种子（R430 科学后继，owner 并行批令）

**Opened**: 2026-08-18
**Driver**: owner direct order in the current task ("启动所有补充实验，尽量并行"):
R430 (CLM-1310) showed the adapted SAC trains stably but every eval row fails
`action_slew_violation` (no slew projection — preregistered validity risk).
This round adds the same execution-layer slew projection the scalar arm uses
to the SAC arms (training + eval) and extends seeds 401-403 -> 401-405
(merging the proposed "slew retest" and "5-seed expansion" supplementary
experiments into one sealed contract).
**Parents**: R430/CLM-1310 (invalid-bank endpoint), R428/CLM-1305 (exact
interface collapse), R425/CLM-1290 (CD family), R429 engineering failure
(aborted; preserved).

## TL;DR

Workload: `evidence`; frozen training + evaluation. R431 is the direct
successor of R430 with one scientific factor change — the SAC arms execute
through the byte-unchanged `PerVSGMDActionProjector` (0.25/step slew limit,
per-actor rowwise clip + slew, stateful, reset per episode) in training and
evaluation — plus a declared statistical scale change (5 seeds 401-405;
401-403 subset stays directly comparable to R430/R428/R425). Reward,
learner, bundle, classifier, scalar anchor rule (401-403 byte-identical to
R419; 404/405 fresh with no anchor), eval protocol, and no-tuning rules are
R430-identical.

## Methodology

- Import the frozen R430 runner chain (R430 -> R429 -> R428) without editing
  any frozen source.
- Rebind round/result/lifecycle paths to R431; `training_seeds` becomes
  [401, 402, 403, 404, 405] in the R431 contract (classifier is
  data-driven; the R430/R428 authority checks that pin 3 seeds are
  overridden by the R431 adapter, matching the R429/R430 adapter pattern).
- Two verbatim-copied execution functions from the frozen R428 source with a
  single declared seam each:
  - SAC training loop: `raw = agent.act(...)` then
    `action = projector.project(raw)` before decode/step; the
    per-step saturation diagnostic counts executed-delta saturation
    (`|action - previous| >= limit - 1e-6`) instead of raw tanh magnitude;
    the policy observation stays the 7-slot row (projector state is not in
    the observation; the policy must adapt through state feedback — declared
    design, not a repair).
  - Eval loop: the SAC branch becomes
    `action = projector.project(agent.act(joint, deterministic=True))`, and
    `action_norm` records the projected action (matching the scalar branch),
    so `summarise_profile` sees the physically executed actions.
  - Drift guard: a unit test strips the seam lines and asserts the copies
    are byte-identical to the frozen R428 source.
- Scalar dispatch: seeds 401-403 keep `record_scalar_anchor=True`
  (byte-identical to R419 required); seeds 404/405 run the same frozen core
  with `record_scalar_anchor=False` (no R419 counterpart; manifest field
  stays null).
- Capacity: reuse the R429 v3 ladder (measured rungs 1/2/4/8/12/16 on the
  identical SAC representative task) after a fresh no-other-process host
  snapshot; R431 selects 15 workers (one under the measured rung-16
  envelope, sharing the machine with the sibling round R432 per the owner's
  parallel order and the total-process/memory accounting).

## Frozen scientific contract

R430 plan and seal remain the scientific contract with two declared deltas:

1. **Slew projection on the SAC arms** (the single scientific factor):
   `PerVSGMDActionProjector(action_slew_limit=0.25)` applied per step in
   training and evaluation, reset per episode, identical to the scalar-arm
   execution path. The reward formula (100 r_f + 50 r_abs + 0.0056 r_H +
   0.0056 r_D, normalized denominators 600/600, rebuilt from the obs row)
   is unchanged; rewards now reflect physically feasible executed deltas.
2. **Seed scale**: training_seeds = [401, 402, 403, 404, 405]; all SAC
   checkpoints trained fresh (no reuse); scalar 401-403 byte-anchor
   required, scalar 404/405 fresh.

All other fields inherited from R430/R428: eight profiles, 43,200
interactions/run, deterministic SAC evaluation (projected), frozen
classifier, frozen estimators, direct bounded delta-M/delta-D decoder, no
warm start, no checkpoint reuse, no tuning, no outcome-based selection.

## Pre-registered decision tree

1. Any missing/corrupt/non-finite shard or evaluation TDS failure =>
   `CANARY-INVALID`; preserve artifacts, no in-round retry.
2. Otherwise run the frozen classifier. The expected outcome is that all
   SAC rows become row-valid (the projector enforces |delta| <= 0.25), so
   the classification is decided by the physical guards. If any adapted-SAC
   arm passes every physical guard or the classification flips to
   CANARY-PASS, stop at the claim gate and ask the owner (pause branch,
   program B1-style) — no promotion to a universal SAC claim without
   review.
3. If both SAC arms remain invalid despite the projector, report the
   bounded endpoint: execution-layer slew projection did not make the
   bundle valid.
4. Compare only same-contract endpoints/guard distributions: R431 vs R430
   (invalid-bank descriptive endpoints), R428 (collapse), R425 (CD
   family). The key readout: whether the R430 message-arm descriptive
   advantage (0.670/0.688x deterministic, context-only) survives on
   physically valid trajectories, and whether the message contrast
   (+55.2%/+71.6% vs no-message on invalid rows) becomes a real
   measurement.
5. No rate projection, reward retuning, alpha tuning, architecture change,
   fresh bank, or third attempt is authorized by any outcome.
6. Reward-family closeout reports the project multi-axis readout; the paper
   `cum_rf` readout is not produced by this bank (`reward_used_for_gate`
   false) — reported as unavailable, disagreement not collapsed, no
   threshold used to release or retry.

## Capacity and execution card

- Prior representative evidence: R429 v3 ladder (all rungs 1/2/4/8/12/16
  valid, 32 tasks/rung, selected 16 workers / 17 processes); R430 reused it
  cleanly (9/9 train, 10/10 eval exit 0).
- R431 reuse gate: fresh no-other-process snapshot (measured: 0 research
  processes), matching logical CPU/memory rule, identical representative
  task (SAC learner; the projection seam adds only per-step numpy ops),
  current source/runtime hashes.
- Frozen budget: `host_process_budget: 21`,
  `wsl_python_processes: 16` (15 workers + 1 driver),
  `native_threads_per_process: 1`,
  `other_reserved_processes: 5` (sibling round R432: 4 workers + 1
  driver). Total 21 <= 32 logical CPUs; total-memory accounting:
  19 concurrent workers x 0.944 GiB (R429 measured floor) + 3 GiB OS floor
  ~= 21 GiB <= 27 GiB WSL MemTotal.
- Ready jobs: fifteen training shards (3 arms x 5 seeds) in one wave at
  workers=15 (~2.2 h + tail; user-provided per-run ETA), then sixteen
  evaluation shards (15 learned arm-seeds + deterministic) in one wave
  (~3-4 min), then serial classify.
- Monitor process count, completed manifest count, memory/disk, engineering
  failures only; no intermediate scientific returns.

Execution readiness is `MEASURE-FIRST` until capacity reuse, targeted
tests, preflight, and rehearsal pass; then `RUN-READY`. Sealed concurrency
is immutable.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r431_sac_slew.py --shards tmp/andes/r431_train_shards.json --workers 15 --round R431`, then the same driver with `tmp/andes/r431_eval_shards.json`, then `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r431_sac_slew.py classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r431_sac_slew.py rehearse`
- rehearsal_scope: same-pre-attempt-path; source/parent/runtime/output
  guards, one real physical step and batch update per arm through the
  projected path, SAC semantics probe, save/load, explicit R431 output-root
  resolution, and a projection-seam probe (short projected rollout:
  executed deltas never exceed limit + 1e-6; copied-loop diff pinned by the
  drift test); creates no formal artifact
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
  (additionally: adapted_sac_semantics_probe, successor_output_root_probe,
  projection_seam_probe)
- capacity_evidence: memory/rounds/R431/capacity_evidence.json
- host_process_budget: 21
- wsl_python_processes: 16
- native_threads_per_process: 1
- other_reserved_processes: 5

## 资产保护契约

- Byte-unchanged/read-only: R419-R430 sources, seals, results, claims,
  feeds; `sac.py`, V4 environment, classifier, decoder, estimators,
  `per_vsg_md.py`.
- New only: R431 runner/tests (verbatim-copied loops with the declared
  seam + drift test), R431 lifecycle artifacts, create-only R431 results
  and closeout ledger/feed/claim.
- Dirty worktree preserved; no reset/clean/stage/commit; no manuscript
  prose.

## Gate calibration target

At closeout record whether the projection-seam probe, the 5-seed scale, and
the shared-host budget declaration were too hard/soft/right. No gate is
relaxed inside the attempt.

## Cross-references

- R430 invalid-bank endpoint: `paper/yang_md_decoupling_marl/reports/R430.md`, CLM-1310.
- Same-contract comparison endpoints: R428/CLM-1305, R425/CLM-1290.
- Parallel sibling round: R432 (B3 diagnostics; `other_reserved_processes`
  declared above).
- Workflow authority: `paper/yang_md_decoupling_marl/LINE.md`, the owner
  order in this task, `CLAUDE.md`, `skills/kundur-round/SKILL.md`.
