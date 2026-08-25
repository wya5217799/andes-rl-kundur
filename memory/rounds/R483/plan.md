---
round: R483
state: active
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-25'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R483 plan — fail-closed adaptive-stop source factorial

**Opened**: 2026-08-25
**Driver**: owner stopped R482 after two complete fixed-budget waves and requested the remaining factorial as automatic convergence detection plus immediate 16-slot refill to reduce wall time without hiding failures.
**Parent**: R482 aborted EXECUTION-INCOMPLETE; its 32 valid training cells are retained but excluded from R483 inference. R481 CLM-1505 remains the corrected-card physical gate.

## TL;DR

Train a complete new adaptive factorial: 8 arms x 26 seeds = 208 cells. Each cell runs at least 30,000 and at most 43,200 interaction steps. From 30,000 onward it is checked every 2,000 steps and stops only after three consecutive all-gate passes. A dynamic 16-slot driver immediately admits the next unique cell. R482 trained checkpoints are never pooled with R483; only R482's sealed per-seed corrected-card base states are reused as prospectively declared inputs.

## Snapshot at plan-time (oracle as of 2026-08-25)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] finite-bank information-level margin program — not addressed by this round.

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375.
- Q-0004 closed-negative @ R442, by CLM-1370.
- Q-0111 closed-negative @ R397, by CLM-1130.

## Frozen scientific object

- Inference units: seeds 501..526, all present in every arm. Arms: actor {N,P} x critic {N,P} x reward access {0,1}; 208 new adaptive cells. Missing or substituted cells make execution incomplete.
- Training family/card/projector/reward/profile definitions: byte-bound R482 corrected-card sources. R482 donor base states and manifests are reused only as matched initial conditions; their seal and base-audit anchors must verify before every cell.
- R482's 26 penalty cells and 6 factorial cells are fixed-budget historical objects. They are preserved and reported separately; none can fill an R483 roster position or enter R483 factorial statistics.
- Adaptive final checkpoint: the first qualifying checkpoint in {34,000, 36,000, 38,000, 40,000, 42,000, 43,200}, otherwise 43,200 with `converged=false`. The 21,600-step half checkpoint remains fixed for descriptive direction checks.
- Primary analysis: the R482-registered four factorial effects at materiality boundary log(1.10), exact one-sided Wilcoxon plus the registered symmetry/sign-flip fallback, Holm family of four at FWER 0.05. The estimand is explicitly the adaptive-stop training protocol, not the abandoned fixed-43,200-step R482 estimand.
- Pre-registered classifications: ADAPTIVE-MATERIAL-MAIN-EFFECT / ADAPTIVE-MATERIAL-INTERACTION / ADAPTIVE-MATERIAL-EFFECT-NOT-ESTABLISHED / DESIGN-INVALID / EXECUTION-INCOMPLETE / INTEGRITY-INVALID. Never claim zero effect or equivalence.

## Adaptive stop contract

- Frozen defaults: `min_steps=30000`, `max_steps=43200`, `check_interval=2000`, `window_updates=2000`, `required_checks=3`; first-to-last confirmation span = 4,000 steps.
- At each eligible check, all must pass simultaneously: finite actor loss, critic loss, alpha and actor-gradient histories; actor and critic adjacent-window median absolute change <=10%; alpha either at 0.005 floor or changes <=5%; actor-gradient median remains >=1e-6 and changes <=25%; zero TDS failures; deterministic fixed-state executed-action drift <=2%.
- Action stability uses the worse of adjacent-check drift and cumulative drift from the 28,000-step baseline, and the worst physical probe state rather than a cross-state average. The probe bank covers every development scenario, five deterministic time samples, and zero plus alternating previous-action contexts; its definition and bytes are seal-bound.
- Missing, short, non-finite or malformed evidence fails closed and resets the consecutive-pass counter. Maximum budget stops the cell but does not label convergence unless every gate also passes.
- Runtime records every decision, executed steps, stop reason and hashes. Fixed-budget and adaptive manifests carry distinct training-mode identities and cannot be silently pooled.

## Execution and recovery

- Dynamic queue: 16 worker slots + one launcher, immediate refill on normal completion, no duplicate shards. A nonzero cell halts further admissions while already-running cells finish and are inventoried.
- Recovery policy: `preserve_partial_new_attempt_reuse_completed`. Hash-valid completed cells may be skipped after interruption. Abrupt partial attempts remain under `recovery_attempts/` and a new attempt may run. Initialization, scientific, numerical, code or integrity failures remain visible and block automatic retry.
- Power loss therefore preserves completed results, partial attempts, queue state and logs. No path overwrites a previous attempt or R482 asset.
- Evaluation: deterministic reward-free evaluation of half and adaptive-final checkpoints for all 8 arms x 26 seeds on the frozen profiles; 16 arm-stage jobs. Analysis and formal manifest run only after all 208 training cells and all 16 evaluation jobs validate.

## Methodology

1. Finish implementation: reusable adaptive monitor and cell trainer; R483 runner; dynamic queue; adaptive-aware evaluation, four-effect aggregation, result audit and formal manifest.
2. Run focused tests, R482 regression, preflight and a committed preliminary code review. Record owner approval before any WSL probe.
3. Generate the deterministic physical probe, then freeze exact config, balanced train/evaluation shard lists, power artifact, recovery policy and result root. No R482 learned checkpoint is an input.
4. Run the seal-authoritative two independent reviews over this final committed snapshot. Both name the exact commit and cover the plan, config, power, probe, exact shard lists, source/implementation/test files. Post-review routing, rehearsal, capacity, seal and the review records themselves are semantic-validated and hash-bound; they are not self-reviewed. Any P0/P1 blocks.
5. Run the same-entry WSL rehearsal covering source hashes, installed package/case, probe semantics, one simulated early stop, one max-budget fallback, interruption recovery and output absence; then one 16x8 capacity confirmation.
6. Generate formal seal through the shared verifier and commit the seal point. Any post-seal source/config change aborts R483 and requires a successor.
7. Only after a separate launch notification, start the detached dynamic queue. No result-driven threshold or roster change.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_adaptive_u2_successor.py --config memory/rounds/R483/adaptive_config.json <command>`; training launch command = `launch-train`, evaluation launch command = `launch-eval`; both read seal-bound shard paths, log roots and exactly 16 workers from the config, with `--resume` permitted only under the frozen recovery policy.
- rehearsal_command: same formal entry `rehearse`; same pre-attempt verification path; no formal attempt/result creation.
- rehearsal_scope: R483 runner, config, probe, queue, R482 sealed source inputs, installed ANDES case/package, recovery and adaptive-stop semantics.
- rehearsal_checks: source/plan/config/probe/review hashes; R482 terminal state and seal/base audit; installed package/case; output absence; action-probe definition; convergence and max-budget decisions; recoverable abrupt partial versus blocking scientific failure.
- capacity_evidence: new `memory/rounds/R483/capacity_evidence.json`, using the R452-R482 16-worker history plus one 16x8 quick confirmation after rehearsal.
- wsl_python_processes: 17; native_threads_per_process: 1; host_process_budget: 17; other_reserved_processes: 0.

## Completion and stop rules

- Completion: 208 valid adaptive training manifests, 16 complete arm-stage evaluations, hash-valid adaptive analysis and formal manifest, then feed/publication/claim/verdict close-out.
- Stop immediately: authority/seal/source drift; unbalanced roster; duplicate admission; nonfinite/TDS/scientific failure; invalid sidecar; probe/config drift; artifact budget breach; any retry not allowed by the frozen recovery policy.
- No outcome-based stopping of the factorial batch. Adaptive stopping applies within a cell only; every registered arm-seed cell remains required.

## Gate

- Preflight, committed dual review, owner approval, rehearsal, capacity and formal seal must all pass before long execution. Current planning and focused tests do not authorize training.
- R482 fixed-budget results remain an excluded historical object. R483 may support only claims about the prospectively frozen adaptive protocol.

## 资产保护契约

- Byte-preserve R470-R482 plans, seals, code-bound sources, results, logs and sidecars. Never edit, delete, rename, overwrite or resume an R482 training path.
- Add only R483 code/tests/governance, `memory/rounds/R483/`, `results/research_loop/r483_adaptive_u2/` and `tmp/andes/r483_*` orchestration traces.
- Preserve unrelated user work and `.codex/`; close and seal commits must stage only audited R482 close-out plus R483-owned files.

## Cross-references

- `memory/rounds/R482/plan.md`, `formal_seal.json`, `base_audit.json`
- `scripts/run_r482_u2_confirmatory.py`
- `src/andes_rl_kundur/training/adaptive_stop.py`
- `src/andes_rl_kundur/training/adaptive_u2.py`
- `scripts/adaptive_shard_driver.py`
- `paper/yang_md_decoupling_marl/working/source_factorial_power_plan.json`
