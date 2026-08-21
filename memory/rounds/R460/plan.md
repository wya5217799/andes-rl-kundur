---
round: R460
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-21'
closed: '2026-08-21'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R460 plan — U3 executed-action Bellman semantics

**Opened**: 2026-08-21
**Driver**: Repair and formally verify the raw-action, stateful projection, replay, critic, target-action, and augmented-state semantics that must pass before any new U2 training is admissible.
**Parent**: CLM-1435 (R459 shared Object A contract); R451 algorithm audit findings are diagnosis inputs, not positive policy evidence.

## TL;DR

Build a successor-only SAC seam in which the actor state contains the previous executed action, replay preserves raw and executed actions, every critic consumes the actually executed/projected action, and the target projection uses the current executed action as the next state's previous action. Verify it with exact NumPy/Torch projector parity, Markov/aliasing tests, a deterministic multi-step toy MDP, a content-hashed retrospective R431 checkpoint diagnostic, and one complete 24-trajectory R431 evaluation bank traced step by step. No training is authorized in this round.

## Snapshot at plan-time (oracle as of 2026-08-21)

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

### Classification and scope

- Work class: **evidence**. The implementation is a successor-only execution seam; R431/R451 source, checkpoints, results, and verdicts remain immutable.
- Formal output root: `results/research_loop/r460_u3_execution_semantics` (create-only).
- Reusable implementation: `src/andes_rl_kundur/agents/executed_action_sac.py`.
- Formal runner: `scripts/run_r460_u3_execution_semantics.py`, executed only through `scripts/andes_scratch.py` with `/home/wya/andes_venv/bin/python`.
- No policy training, hyperparameter search, U2 factorial cell, U4 guard conclusion, or historical-checkpoint repair is in scope.

### Corrected successor semantics

For each per-VSG transition, define the Markov actor/critic state as `z_t = [obs_t, previous_executed_action_t]`. The runtime executes

1. actor raw tanh action;
2. amplitude clipping to `[-1, 1]`;
3. stateful slew projection about `previous_executed_action_t`;
4. Object A normalized-to-physical M/D mapping;
5. environment transition and reward;
6. replay storage of `obs_t`, `previous_executed_action_t`, raw action, executed action, reward, `next_obs`, and terminal flag.

The current critic consumes replay `executed_action`; the actor-loss critic input is the differentiably projected current actor action; the target actor action is projected about the replay `executed_action`, which is the next state's previous action; and the target critic consumes that projected target. Entropy is explicitly labelled `raw_policy_entropy_regularizer`; no executed-action density or physical-exploration entropy claim is made.

### Formal evidence bundles

1. **Static historical audit**: content-hashed source locations showing R431 stored raw actions while the environment executed projected actions, plus an exhaustive inventory of R431 replay artifacts. If no original replay exists, emit exactly `historical_bias_not_reconstructible` with reason `original replay transitions unavailable`; never report an exact historical training-bias number.
2. **Projector and Markov tests**: boundary/random NumPy-versus-Torch cases; full multi-step reconstruction; `next_prev_action == executed_action`; same full `(z,u)` determinism under a frozen exogenous seed; and an explicit two-valued transition counterexample after deleting previous executed action.
3. **Toy Bellman bank**: deterministic finite-horizon transitions with a hand-computed return and independently recomputed TD target, absolute error at most `1e-6`; record actor-loss, replay-current, and target critic action inputs.
4. **Retrospective checkpoint diagnostic**: use one hash-verified R431 checkpoint on the newly frozen state/observation bank to quantify one-step raw-versus-executed action/target discrepancies only. Label it retrospective and not an exact historical replay-bias estimate.
5. **Complete physical evaluation bank**: the frozen R431 evaluation profiles, all 24 signed/localized scenarios, 30 steps each, using a single deterministic initialized successor-policy checkpoint. Emit every transition, including observation, prior executed action, raw/amplitude/executed action, physical M/D command, reward components, next observation, completion/valid/failure flags, active projection mode, actuator state, replay fields, target actions, critic inputs, Q values, TD target, and content identity. Invalid or failed rows remain present.
6. **Independent checker**: read only emitted artifacts and source contracts; recompute schema/cardinality, projector parity, Markov continuity, action-to-physical mapping, toy returns/targets, critic-input identities, hashes, and the distinction between historical and successor diagnostics.

### Prospective outcomes

- `EXECUTION-SEMANTICS-VALID`: all required artifacts/hashes exist; NumPy/Torch and multi-step projection errors are `<=1e-7`; replay next-previous identity is exact within `1e-7`; the Markov determinism and aliasing counterexample pass; toy hand return/TD error is `<=1e-6`; all current/actor/target critics receive executed/projected actions; all 24 physical trajectories and their rows are retained; and the historical-replay availability statement is truthful.
- `EXECUTION-SEMANTICS-INVALID`: the run terminates but any semantic, parity, Markov, Bellman, trace, or independent-check condition fails. Preserve all outputs and block U2 training.
- `ENGINEERING-INVALID`: source/runtime/case/checkpoint drift, pre-existing output, missing terminal artifacts, launcher/resource failure, or checker failure. Preserve the attempt and draw no scientific conclusion.

No partial-pass, magnitude rescue, rerun, or alternative learner is authorized. `historical_bias_not_reconstructible` is an expected bounded subfinding when original R431 replay is absent, not permission to infer a number.

### Theory-intake observables

- `projector_numpy_torch_max_abs_error`
- `multistep_projector_reconstruction_max_abs_error`
- `next_prev_identity_max_abs_error`
- `full_state_determinism_pass`
- `deleted_previous_action_aliasing_pass`
- `toy_hand_return_td_target_abs_error`
- `critic_current_uses_executed`, `actor_critic_uses_projected`, `critic_target_uses_projected`
- `historical_replay_status` and retrospective one-step discrepancy distributions
- complete-bank trajectory/transition cardinality and validity/failure counts

External GPT material specifies requested observables and acceptance tests only; it is not scientific evidence or theorem authority.

### Execution and capacity contract

- Readiness begins at `MEASURE-FIRST`. Capacity probes execute distinct representative physical trajectories in scratch-only paths at increasing worker rungs, measuring wall time, aggregate throughput, per-process peak RSS, host/WSL free memory, and failures. Select the fastest stable rung with at least 20% WSL-memory headroom; stop before pressure or throughput regression.
- R458's 17-live-WSL-process result is an upper-bound anchor, not automatic authority. The formal 24-trajectory bank contains 24 unique scientific jobs and no duplicates.
- GPU is not selected prospectively: the environment is CPU/DAE-bound, the per-step networks are tiny, and sharing a laptop GPU across many simulator processes would add transfer/contention without a measured throughput benefit. GPU availability/utilization is still recorded.
- Initial process declaration: `host_process_budget=17`, `wsl_python_processes=TBD from measured rung`, `threads_per_process=1`, `other_worker_processes=1 orchestrator`. The exact selected rung must be frozen in `capacity_evidence.json`, rehearsal, and the formal seal before launch.
- Rehearsal must run the same pre-attempt trace/check path on scratch output, verify source/runtime/case/checkpoint hashes and output absence, and record peak RSS/runtime. It must not create the formal result root.
- No in-place resize, retry, parameter change, or scientific-result inspection is authorized after sealing.

### Formal launch contract

- formal_entry: `scripts/run_r460_u3_execution_semantics.py prepare`, unique `trajectory` shards, then `consolidate`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r460_u3_execution_semantics.py rehearse-v2`; the first non-authoritative rehearsal is preserved and excluded from the seal because its reward-component ledger was corrected pre-seal in `rehearsal_amendment.json`
- rehearsal_scope: `same-pre-attempt-path with one representative trajectory plus all non-physical semantic tests`
- rehearsal_checks: `source_hash,parent_hash,installed_package,case_hash,r431_checkpoint_hash,output_absence,projector_parity,Markov tests,toy Bellman,trace schema,independent checker`
- output_absence_check: `results/research_loop/r460_u3_execution_semantics must not exist before prepare`
- formal_output: `results/research_loop/r460_u3_execution_semantics`
- capacity_evidence: `memory/rounds/R460/capacity_evidence.json`
- host_process_budget: `17`
- wsl_python_processes: `TBD from measured capacity ladder; maximum 16 trajectory workers plus one orchestrator`
- threads_per_process: `1`
- other_worker_processes: `1 orchestrator`
- retry_policy: `none; preserve terminal attempt and require a successor round`
- completion_rule: `independent verification verdict EXECUTION-SEMANTICS-VALID with zero hash failures`

## Gate

Classify `EXECUTION-SEMANTICS-VALID` only when the formal create-only bank is complete and independently verified against every conjunctive threshold above. U2 remains blocked on any invalid or engineering-invalid outcome. The absence of historical replay permits only the exact missing-data statement and a clearly labelled retrospective diagnostic.

## 资产保护契约

- Preserve R431, R451, R458, R459, their sources, checkpoints, result roots, manifests, seals, and verdicts byte-for-byte.
- Do not overwrite the imported GPT Pro request or the R459 shared model export.
- Add only R460-owned source, tests, round records, scratch capacity/rehearsal artifacts, create-only formal results, and later feed/claim/domain registrations.
- Preserve unrelated dirty-worktree changes and bind all formal inputs by content hash.

## Cross-references

- CLM-1435 / R459: complete Object A input/action/unit mapping used by the physical-command trace.
- R431 / CLM-1315: frozen SAC-slew result and checkpoint source; retrospective diagnosis only.
- R451: sealed canary-invalid algorithm audit showing raw-versus-executed replay/critic mismatch among other fatal confounds.
- `paper/yang_md_decoupling_marl/working/gpt_pro_additional_data_request_20260821/`: external requested-data specification and acceptance rules.
