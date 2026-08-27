---
round: R484
state: active
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-27'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R484 plan — 30-second full-guard evaluation of frozen R483 policies

**Opened**: 2026-08-27
**Driver**: owner explicitly authorized the necessary low-hardware supplemental
evaluation on 2026-08-27; no retraining, tuning, or broader experiment is
authorized.
**Parent**: CLM-1515/R483 (all-fresh adaptive factorial), CLM-1505/R481
(corrected-card deterministic winner), CLM-1500/R480 (30-second horizon
sensitivity requirement).

## TL;DR

Evaluation-only successor. Run every one of the 208 sealed R483 final
checkpoints for 150 steps (30 s at 0.2 s) on the same four registered
`canary_eval` profiles, together with frozen zero and deterministic comparators.
Also rerun the two comparators on the four R481 fresh evaluation profiles so
the direct-M/D feasibility claim receives the same tail check. Recompute the
four source-factor effects as a separate 30-second sensitivity and apply the
complete pre-existing physical/action guard set to every learned
policy-profile block. No half checkpoints, training, model selection, H0 scan,
new topology, or parameter change. Expected formal wall: 2 h 50 min to 3 h 30
min on 16 workers; about 650 MB new output.

## Snapshot at plan-time (oracle as of 2026-08-27)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] Does the finite-bank information-level margin program (shared action variables per non-anticipative info class, solution section 5.4) certify or refute INFORMATION-LIMITED for the 2% joint target under the exact R352/R353 observation histories?

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375 — Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0004 closed-negative @ R442, by CLM-1370 — AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?

## Methodology

### Frozen scientific object

- **R483 policy roster**: exactly eight arms x seeds 501-526 = 208 final
  checkpoints from `results/research_loop/r483_adaptive_u2/train/`. Every
  checkpoint must match its R483 training manifest, sidecar, source base, and
  the sealed R483 manifest. No outcome-based subset is allowed.
- **Comparator roster**: `zero` plus the R481 frozen development-selected law
  `local_neighbour_md_km2_kd2`. Comparator definitions and thresholds are
  imported by hash, not copied or retuned.
- **Canary bank**: four R483 evaluation profiles (`canary_eval_a..d`), six
  signed common/differential/localized scenarios each. Every R483 policy and
  both comparators run here.
- **Fresh deterministic bank**: the four R481 `fresh_eva_a..d` evaluation
  profiles, six signed scenarios each. Only zero and the frozen deterministic
  law run here; this bank is not pooled with the canary bank.
- **Horizon/card**: 150 steps x 0.2 s = 30 s, corrected project calibration,
  device-base H0=100 s and D0=100 unless a frozen profile supplies its declared
  heterogeneous values, one 50/60-Hz conversion, protected V4 execution and
  action decoder unchanged.
- **Work units**: 208 x 4 x 6 = 4,992 learned trajectories; 2 x 4 x 6 = 48
  canary comparator trajectories; 2 x 4 x 6 = 48 fresh comparator
  trajectories; total 5,088 trajectories and 763,200 TDS steps. Sixteen
  balanced shards each own exactly 13 learned policy cells; comparator blocks
  are distributed deterministically across shards.

### Pre-registered estimands and guards

1. **Horizon sensitivity of the source factorial**: on the canary bank,
   recompute actor main, critic main, actor-by-critic, and critic-by-reward
   seed effects on final-checkpoint `disturbance_differential_energy` using the
   exact R483 formulas. Test each directly at `log(1.10)` with the same
   Wilcoxon/sign-flip validity switch and Holm family of four. This is a
   prospective 30-second sensitivity; it is never pooled with or substituted
   for the six-second R483 primary result.
2. **Complete learned-policy guard**: for each learned policy, seed, and
   canary profile, require a valid complete trajectory summary, actuator
   mapping pass, no normalized action-box violation, no 0.25 slew violation,
   common-frequency IAE/worst-unit peak/worst RoCoF no worse than 103% of the
   same-profile deterministic comparator, action RMS/total variation no worse
   than 110% of that comparator, saturation fraction <=0.05, minimum
   per-record action variation >1e-6, and minimum per-record per-VSG action
   dispersion >1e-6. A frozen policy passes the complete tested-bank guard
   only if all four canary profiles pass those per-profile guards **and** its
   equal-weight aggregate off-diagonal response energy and disturbance-
   differential energy across the four profiles are each at least 5% below
   the matching deterministic aggregate (the frozen R399
   `minimum_joint_improvement=0.05` target). Per-profile endpoint ratios are
   report lines, not gates. Report all 832 profile blocks and all 208 policy
   decisions; no probability claim. This learned-policy verdict is
   interpretable only if the deterministic reference itself passes the exact
   R481 Phase-1A validity/no-harm gate against zero on all four canary
   profiles; otherwise report `REFERENCE-INVALID` and suppress the learned
   pass/fail claim.
3. **Deterministic 30-second feasibility sensitivity**: apply the exact R481
   Phase-1A validity/mapping/box/slew/common-no-harm/saturation/variation/
   dispersion gate to the frozen deterministic winner against zero on all
   four R481 fresh evaluation profiles. Repeat descriptively on the canary
   profiles. Endpoint ratios are report lines, not gate inputs.
4. Reward, training loss, six-second results, and manuscript prose never gate
   the new evaluation.

### Pre-registered outcomes

- Any missing/duplicate trajectory, checkpoint/manifest/hash mismatch,
  nonfinite row, TDS failure, invalid mapping, output collision, or incomplete
  shard -> `ENGINEERING-INVALID` or `INTEGRITY-INVALID`; no scientific
  performance verdict.
- The separate 30-second four-effect sensitivity is classified
  `TAIL-MATERIAL-MAIN-EFFECT`, `TAIL-MATERIAL-INTERACTION`, their combined
  form, or `TAIL-MATERIAL-EFFECT-NOT-ESTABLISHED`. Absence of rejection is
  never zero or equivalence.
- Learned full guard: `R483-FROZEN-POLICIES-ALL-FAIL-COMPLETE-GUARD` iff zero
  of 208 frozen policies passes all four canary profiles; otherwise
  `R483-FROZEN-POLICIES-SOME-PASS-COMPLETE-GUARD` with the exact passing roster.
  Either outcome is limited to these frozen policies and this tested bank,
  never the MARL algorithm family. Neither learned outcome is issued when the
  deterministic canary reference fails its own 4/4 Phase-1A gate; that case is
  `LEARNED-COMPLETE-GUARD-REFERENCE-INVALID` and carries no learned pass/fail
  claim.
- Deterministic tail sensitivity:
  `DIRECT-MD-30S-FRESH-PASS` iff the frozen winner passes all four R481 fresh
  evaluation profiles; otherwise `DIRECT-MD-30S-FRESH-FAIL`. The separate
  canary-bank count is descriptive.

### Execution and verification order

1. Implement a new successor analysis module, stable runner, config, 16-shard
   roster, focused unit tests, and create-only/hash-sidecar I/O. Do not edit
   the sealed R483 runner, checkpoints, manifests, or scientific artifacts.
2. Run focused tests, `round_preflight.py R484`, and two independent frozen
   code/design reviews. Owner approval is recorded before any WSL command.
3. Run the formal entry's same-path rehearsal: verify R483/R481 parents,
   sources, all checkpoint identities, installed ANDES/case, output absence,
   one representative 150-step zero trajectory, and no formal-attempt output.
   Before scientific aggregation, also require prefix isolation: every learned
   150-step record must reproduce the frozen R483 30-step prefix, and every
   fresh comparator record must reproduce the matching frozen R481 prefix,
   for time, frequency, executed/raw action, and decoded delta-M/delta-D at the
   frozen tolerance (horizon-dependent `done` is excluded). The stored R483
   raw system-base M/D fields are not compared to R484's corrected device-base
   telemetry; R484 mapping validity is checked independently. Prefix drift is
   `INTEGRITY-INVALID`, never a tail effect.
4. Run one 16-worker x 8-job capacity confirmation, bind the result, config,
   shard list, reviews, rehearsal, and source hashes into the formal seal, then
   commit the seal point with only R483/R484-owned files staged.
5. Launch exactly once through a durable Windows scheduled task holding WSL;
   stdout/stderr/exit code go under `tmp/andes/r484_*`. No automatic retry or
   parameter change. All sixteen shards are admitted at launch. A shard-level
   trajectory TDS or engineering failure is recorded and the worker rebuilds
   the environment for the next registered trajectory; it must not skip the
   remaining policy/profile work in that shard or kill, pause, or cancel any
   other running shard. Only an unrecoverable worker/process failure may leave
   a shard incomplete. Any such failure blocks aggregate/claim steps after the
   remaining shards finish naturally. Formal outputs are create-only with
   SHA-256 sidecars.
6. After natural completion, verify 16/16 shards, aggregate once, create the
   formal manifest, then follow the normal feed/claim/verdict close-out.

## Experiment efficiency card

- execution_class: non-quick evaluation-only
- unique_trajectories: 5,088
- tds_steps: 763,200
- concurrent_workers: 16; launcher: 1; native threads: 1 each
- eta_formal: 2 h 50 min to 3 h 30 min
- eta_basis: R483 299,520 evaluation steps took 3,621-3,645 s; R484 is 2.548x
  the same workload plus bounded comparator and long-tail overhead
- artifact_budget: expected about 650 MB; notify the owner at 900 MB if the
  formal attempt has not already naturally completed, but do not terminate,
  pause, or modify the running attempt without separate owner authorization
- memory_contract: CPU-only; write each six-trajectory policy-profile block
  create-only with a sidecar, close/release each environment immediately, and
  stream one block at a time during aggregation while retaining summaries
  only. The capacity confirmation records worker peak RSS, host/WSL free RAM,
  and output rate; unsafe pre-formal memory headroom is a launch blocker, not
  authority to resize or stop a sealed attempt.
- completion_rule: exactly 16 valid shards covering all 5,088 trajectories,
  aggregate/check/manifest all zero-exit and hash-valid
- retry_rule: none automatically; a failed formal attempt is preserved and
  any recovery needs separate owner authorization under the frozen seal

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r484_30s_tail_guard.py --config memory/rounds/R484/config.json <command>`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r484_30s_tail_guard.py --config memory/rounds/R484/config.json rehearse`
- rehearsal_scope: same-pre-attempt verification path plus one representative
  150-step zero-action trajectory; no formal attempt or result root
- rehearsal_checks: source_hash, parent_hash, checkpoint_inventory,
  installed_package, installed_case, output_absence, representative_valid
- capacity_evidence: `memory/rounds/R484/capacity_evidence_v2.json`
- wsl_python_processes: 18
- native_threads_per_process: 1
- host_process_budget: 18
- other_reserved_processes: 0

## Gate

PASS to formal execution only when the frozen plan, owner approval, config,
shard roster, focused tests, preflight, same-path rehearsal, 16-worker capacity
confirmation, two independent reviews, and formal seal all agree byte-for-byte
and no R483/R481 source drift or pre-existing R484 output exists. Any failed
gate remains visible and stops before the next step.

## 资产保护契约

- R483 plan/seal/config/runner, all training/evaluation artifacts, checkpoints,
  manifests, and sidecars remain byte-identical and read-only.
- R481/R480 contracts, deterministic controller, fresh profiles, guards, and
  results remain read-only. The successor imports semantics by hash and writes
  only its own results.
- Add only R484 plan/approval/config/shards/rehearsal/capacity/reviews/seal,
  `src/andes_rl_kundur/evaluation/r484_tail_guard.py`,
  `scripts/run_r484_30s_tail_guard.py`, focused tests, R484 result root, and
  `tmp/andes/r484_*` orchestration traces.
- Preserve unrelated untracked notes, scratch scripts, `.codex/`, dirty
  manuscript work, and every failed historical attempt; never stage or edit
  them.

## Cross-references

- `memory/claims/CLM-1515.md`, `paper/yang_md_decoupling_marl/reports/R483.md`
- `memory/claims/CLM-1505.md`, `paper/yang_md_decoupling_marl/reports/R481.md`
- `memory/claims/CLM-1500.md`, `paper/yang_md_decoupling_marl/reports/R480.md`
- `src/andes_rl_kundur/evaluation/cd_matd3_canary.py`
- `src/andes_rl_kundur/evaluation/r481_fresh_profiles.py`
- `src/andes_rl_kundur/evaluation/md_decoupling_headroom.py`
- `scripts/run_adaptive_u2_successor.py`, `scripts/run_r481_direct_md.py`
