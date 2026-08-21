---
round: R432
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-18'
closed: '2026-08-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R432 plan — B3 诊断插桩轮（R410 冻结 learner 只记录不改算法，bit-comparable）

**Opened**: 2026-08-18
**Driver**: owner direct order in the current task ("启动所有补充实验，尽量并行")
and the registered soft-spot program item B3
(`paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md` §B3,
"Diagnostics-instrumented rerun", the next queued deck item). R427/R430
closeouts left the CD-family frequency-restoration gap (common-frequency /
worst-peak no-harm guards) with only final-20 cost/multiplier traces, so no
failure mechanism can be identified from the retained record.
**Parents**: R427 (critic divergence suppressed; no-harm gap persists),
R425/CLM-1290, R410 (frozen learner), program B3 protocol.

## TL;DR

Workload: `evidence` (program item B3). A log-only wrapper around the
frozen R410 runner re-runs the repaired no-message and message arms at
seeds 401-403 (6 runs) and persists per-step/per-episode training
diagnostics (critic loss, actor loss, lagrange multiplier, replay fill,
policy-update flag; per-episode common cost and multiplier) as per-run CSVs
+ hashed summary JSON. Zero RNG consumption in the logging seam — a
rehearsal-stage bitcheck compares frozen vs wrapped short-budget runs and
requires byte-identical final checkpoints. No evaluation, no classifier:
this round is reporting-only diagnostics for mechanism hypotheses.

## Methodology

- Import the frozen R410 runner (`scripts/run_r410_message_repair.py`)
  without editing it; rebind round/result/lifecycle paths to R432.
- `train_arm_seed` is a verbatim copy of the frozen loop with persistence
  lines only (no RNG calls): per step, persist the diagnostics dict
  returned by `agent.update()` (`critic_loss`, `actor_loss_mean`,
  `lagrange`, `policy_updated`) plus `agent.buffer.size` fill fraction;
  per episode, persist `episode_common` cost and the lagrange multiplier.
  All added reads are pure-Python/torch reads; no `np.random`/`torch.rand`/
  `random` call is added.
- Bitcheck (`bitcheck` command, rehearsal scope only): run the frozen
  `base.train_arm_seed` and the wrapped copy for the same short budget
  (patched tmp contract, tmp OUT, no-op seal load) on the same arm/seed and
  require byte-identical `final.pt` hashes — proving the logging seam is
  RNG-transparent. Creates no formal artifact.
- Shard command for the shared driver: `shard train|cd_matd3_no_message|401`
  grammar, 6 shards, one wave of 4 plus a tail wave of 2.
- Drift guard: unit test strips the persistence lines and asserts the copy
  is byte-identical to the frozen R410 source.
- Capacity: reuse the R429 v3 ladder rung-4 measurement for the identical
  CD-family representative task after a fresh no-other-process snapshot;
  share the host with sibling round R431 per the owner's parallel order.

## Frozen protocol (program B3, verbatim)

- Rerun the repaired no-message and message arms at seeds 401-403 with the
  unchanged R410 learner; logging never consumes the RNG stream
  (bit-comparable to R410).
- Completion criterion: per-run diagnostic CSVs + hashed summary JSON; a
  bounded mechanism-hypothesis note in the feed (hypotheses, not causes).
- Cost anchor: 6 runs; at 4 workers two waves ~4.5-5 h.

## Pre-registered decision tree

1. Any missing/corrupt/non-finite run => engineering failure; preserve
   artifacts, no in-round retry.
2. Bitcheck mismatch (frozen vs wrapped checkpoint hash differs) => BLOCK:
   the logging seam is not RNG-transparent; stop before formal runs and
   diagnose (no formal artifact is created before bitcheck passes).
3. Otherwise complete the 6 runs, hash the summaries, and write the feed
   with bounded mechanism hypotheses only — no causal claim, no guard
   verdict, no classification, no tuning, no learner change.

## Capacity and execution card

- Prior representative evidence: R429 v3 ladder rung 4 measured valid
  (32 tasks) on the CD-family training task; R430's fresh no-load snapshot
  (0 research processes, 19 GiB available, 32 logical CPUs) reused here.
- Frozen budget: `host_process_budget: 21`,
  `wsl_python_processes: 5` (4 workers + 1 driver),
  `native_threads_per_process: 1`,
  `other_reserved_processes: 16` (sibling round R431: 15 workers + 1
  driver). Total 21 <= 32 logical CPUs; total-memory accounting:
  19 concurrent workers x 0.944 GiB + 3 GiB OS floor ~= 21 GiB <= 27 GiB.
- Ready jobs: six training shards in two waves (4 + 2) at workers=4
  (~4.5-5 h), then serial summary hashing.
- Monitor process count, completed manifest count, memory/disk, engineering
  failures only; no intermediate scientific returns.

Execution readiness is `MEASURE-FIRST` until capacity reuse, targeted
tests, preflight, rehearsal (incl. bitcheck) pass; then `RUN-READY`.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r432_b3_diagnostics.py --shards tmp/andes/r432_train_shards.json --workers 4 --round R432`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r432_b3_diagnostics.py rehearse` (includes the bitcheck)
- rehearsal_scope: same-pre-attempt-path; source/parent/runtime/output
  guards, one real physical step + batch update per arm, short-budget
  frozen-vs-wrapped bitcheck (byte-identical final checkpoint), output
  absence; creates no formal artifact
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
  (additionally: bitcheck_byte_identity)
- capacity_evidence: memory/rounds/R432/capacity_evidence.json
- host_process_budget: 21
- wsl_python_processes: 5
- native_threads_per_process: 1
- other_reserved_processes: 16

## 资产保护契约

- Byte-unchanged/read-only: R410 runner, R410 results/claims/feeds,
  `cd_matd3.py` learner, V4 environment, classifier, estimators.
- New only: R432 wrapper runner/tests, R432 lifecycle artifacts,
  create-only R432 diagnostic CSVs/summaries and closeout ledger/feed.
- Dirty worktree preserved; no reset/clean/stage/commit; no manuscript
  prose.

## Gate calibration target

At closeout record whether the bitcheck, the verbatim-copy drift test, and
the shared-host budget declaration were too hard/soft/right. No gate is
relaxed inside the attempt.

## Cross-references

- Program item: `paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md` §B3.
- Family state: R427 verdict (no-harm gap), R425/CLM-1290, R430/CLM-1310.
- Parallel sibling round: R431 (`other_reserved_processes` declared above).
- Workflow authority: `paper/yang_md_decoupling_marl/LINE.md`, the owner
  order in this task, `CLAUDE.md`, `skills/kundur-round/SKILL.md`.
