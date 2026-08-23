---
round: R476
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-23'
closed: '2026-08-23'
supersedes_rounds: []
superseded_by_round: null
abort_reason: 'execution incomplete: pipeline exited after training wave 1 because
  the driver-result lookup searched the repository tree while the driver wrote under
  its scratch dir; waves 2-3 and evaluation never started; 16 complete hash-valid
  wave-1 training shards preserved for prospective reuse by a successor'
superseded_note: null
---
# R476 plan — R475 governance-correct successor for the all-fresh U2 confirmatory factorial

**Opened**: 2026-08-23
**Driver**: R475 was aborted after review proved that formal phases verified the inherited R470 seal, two reviewers did not cover one identical final source set, the terminal truth table was hard-coded, and integrity failure could not reach its registered classifier branch.
**Parent**: R475 aborted verdict; R474 external redesign; CLM-1475/R473 scientific parent only.
- Workload: `evidence`

## TL;DR

R476 repeats no R475 result and changes no scientific factor. It freezes the same row-permuted same-time placebo, all-fresh `2x2 x reward x 6 seeds` design and direct materiality Holm analysis, but replaces the unsafe execution shell with a thin adapter over a reusable integrity/classification module. Before launch, one R476 verifier must re-hash the plan, power, routing gate, rehearsal, capacity, both reviews, every sealed source, and both exact shard lists at every formal phase. Both reviewers must cover one identical final hash map. Terminal cases execute the real predicate. Any design, execution, or integrity failure makes `material_effect=NOT_TESTED`.

## Snapshot at plan-time (oracle as of 2026-08-23)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — refresh through render.py only. -->

## Open Questions

- Q-0112 remains open; this round does not certify the finite-bank information-level margin.

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375.
- Q-0004 closed-negative @ R442, by CLM-1370.
- Q-0111 closed-negative @ R397, by CLM-1130.

## Frozen scientific contract

- Placebo `P`: for each same-time joint observation, keep recipient columns `0:3` and set neighbour columns `3:7` to the authentic `N` row selected by `rho(i)=(i+1) mod 4`. No exogenous donor trajectory and no R474 diagonal-copy wiring.
- Arms: `an_cn, an_cp, ap_cn, ap_cp` x `r0,r1`; seeds `401..406`; exactly 48 fresh training shards, 43,200 interaction steps each; zero R473/R474/R475 training or evaluation reuse. Only the six sealed R473 base states are imported by hash-identical hardlink.
- Evaluation: half/final checkpoints for all 48 trained cells, using this round's evaluator only; 16 arm-stage jobs, each covering six seeds.
- Effects: profile-paired per-seed `log(P/N)` main effects for actor and critic. Test `H0: effect <= log(1.10)` by complete `2^6` sign-flip enumeration and Holm across the two factors. Exact `6^6` bootstrap CI is descriptive only.
- Wording: total algorithm effect of authentic-neighbour source versus the pre-registered same-time row-permuted placebo; never pure semantic value or a universal intrinsic communication claim.

## Engineering correction contract

1. A reusable deep module owns full R476 seal verification, executable terminal completion truth, and fail-closed confirmatory classification. The round runner is an adapter that binds R476 paths and delegates.
2. `load_seal` verifies the R476 sidecar, round, contract, plan, power, base audit, routing gate, rehearsal, capacity, both review artifacts, every source entry, and exact train/eval shard-list contents. Calling any inherited R470/R475 seal verifier is a test failure.
3. Review A and Review B each record `reviewed_commit` and the same complete `reviewed_files` mapping. Prepare fails unless those maps are byte-identical and equal the final source hashes sealed for runner, tests, deep module, and module tests.
4. Rehearsal calls the real terminal predicate on normal nonterminal, normal final-step `done=True`, premature `done=True`, and `tds_failed=True`; no truth-table value is a literal stand-in.
5. Classification precedence is `DESIGN-INVALID`, `EXECUTION-INCOMPLETE`, `INTEGRITY-INVALID`, then effect result. In the first three states, `material_effect=NOT_TESTED`, `training_dynamics=NOT_ASSESSED` when execution/integrity prevents assessment, and no ESTABLISHED/NOT_ESTABLISHED wording is emitted.
6. Mutation tests must independently kill R475's inherited-seal call, one changed sealed source, one changed shard list, mismatched reviewer maps, each terminal mutation, and integrity errors with otherwise complete outputs.

## Methodology

1. Write red tests at the deep-module interface, then implement seal verification, terminal truth, and classifier.
2. Add the thin R476 adapter and tests proving the R475 scientific contract is unchanged except round/path/provenance fields.
3. Run code compile, module/runner/source-factorial tests, R476 preflight, and repository health.
4. Obtain two independent reviews of the same final source map. Any P0/P1 blocks repair before rehearsal; repaired code is reviewed again.
5. Re-run base audit, routing gate, real ANDES rehearsal, and prepare. Seal only the final reviewed sources and exact shard lists; commit the seal before formal launch.
6. Launch detached pipeline once. A nonzero phase stops the pipeline. No in-round patch, retune, retry, result inspection, or partial-shard promotion.

## Experiment efficiency card

- execution_class: non-quick
- job_count: 64 logical jobs = 48 training shards + 16 arm-stage evaluation jobs
- concurrent_jobs: 16; one launcher; one native numerical thread per process
- waves: 3 training waves + 1 evaluation wave
- eta_range: 8-12 hours wall time after launch
- eta_basis: R473 used the same learner/host/16-worker bundle and needed about 9.3 hours for 12 fresh training shards plus the larger 216-checkpoint evaluation; R475's first wave had no completed shard at 52 minutes, so a sub-hour promise is excluded
- eta_recalibration: after the first 16 training shards complete, recompute remaining ETA from their observed wall range; do not change scope or concurrency
- artifact_budget: approximately 520 MiB expected; hard stop for review above 650 MiB before manifest finalization
- completion_rule: 48 valid 43,200-step training manifests, all half/final evaluation records complete, aggregate and formal manifest hash-valid
- stop_rule: any seal/review/routing/rehearsal/hash/shard failure, nonfinite learner output, failed TDS, missing sidecar, or artifact budget overrun stops the pipeline
- retry_rule: no retry inside R476; a scientific or integrity failure requires a successor
- interruption_rule: operator shutdown may terminate processes, but mid-shard files are incomplete and never scientific; no promise of complete data after an early stop
- interruption_artifacts: completed hash-valid shards and all partial/log files remain preserved and inventoried; partial shards are excluded
- resume_policy: no same-round resume after a mid-shard interruption; resume requires a successor that prospectively declares any completed-shard reuse

## Formal launch contract

- formal_entry: scripts/run_r476_u2_confirmatory.py <phase>
- rehearsal_command: /home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r476_u2_confirmatory.py rehearse
- rehearsal_scope: same-pre-attempt-path
- rehearsal_checks: source_hash,parent_hash,installed_package,installed_case,output_absence
- capacity_evidence: memory/rounds/R476/capacity_evidence.json
- wsl_python_processes: 17
- native_threads_per_process: 1
- host_process_budget: 17
- other_reserved_processes: 0

## Gate

- `MATERIAL-EFFECT-ESTABLISHED`: design valid, execution complete, integrity pass, and at least one direct materiality test rejects under Holm.
- `MATERIAL-EFFECT-NOT-ESTABLISHED`: all three validity gates pass but neither factor rejects; never rewrite as no effect.
- `DESIGN-INVALID`, `EXECUTION-INCOMPLETE`, or `INTEGRITY-INVALID`: no effect verdict; `material_effect=NOT_TESTED`.
- Unstable dynamics retain a fixed-budget estimate only after design/execution/integrity pass and prohibit optimization-resolved wording.

## Theory intake

- External redesign prediction: the clean row-permuted placebo either establishes an actor or critic effect above 10% under the direct Holm, or the effect is not established at that bar.
- Observables: per-seed paired log effects, Holm rows, half/final direction, curve stability, routing mutation flags, and every integrity field.
- Boundary: positive remains a total source effect; optimization gap and residual self/diagonal structure are not isolated.

## 资产保护契约

Preserve R431/R438/R451/R460/R470-R475 and all imported external-review material byte-for-byte. Add only R476 plan/runner/tests, reusable integrity module/tests, structured reviews, base/routing/rehearsal/seal artifacts, detached adapter, result root, feed/claim/verdict/final package. R475 partial output stays excluded and unchanged.

## Cross-references

- `memory/rounds/R475/verdict.md`
- `paper/yang_md_decoupling_marl/working/gpt_pro_r474_placebo_review_deep_20260823/02_MANDATORY_REDESIGN.md`
- `skills/kundur-round/references/experiment-design-guardrails.md` sections A/E/F/G
- CLM-1315 endpoint definitions; CLM-1360 capacity; CLM-1440 executed-action semantics; CLM-1475 scientific parent boundary.
