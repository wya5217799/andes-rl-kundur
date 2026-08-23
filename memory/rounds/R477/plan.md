---
round: R477
state: active
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-23'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R477 plan — R476 execution-completion successor (16 carried-over + 32 fresh)

**Opened**: 2026-08-23
**Driver**: R476 aborted after its first training wave because the pipeline searched for the driver result under the repository tree while the driver wrote under its scratch dir. The driver is fixed and regression-locked; R477 continues the identical scientific design.
**Parent**: R476 aborted (16 complete hash-valid wave-1 training shards preserved); scientific parent CLM-1475/R473.
- Workload: `evidence`

## TL;DR

R477 changes no scientific factor: same row-permuted same-time placebo, same 2x2 x reward x 6-seed arms, same 43,200-step training, same Holm materiality analysis. It prospectively reuses R476's 16 complete wave-1 training shards by hash-identical hardlink after per-shard scientific-identity verification, trains the remaining 32 cells in two sealed waves, runs the unchanged 16 arm-stage evaluation jobs, and aggregates all 48 manifests. Orchestration-only changes: R477 runner adapter, R477 pipeline (with the fixed driver), R477 reviews/seal, and the R476-warning lint.

## Frozen scientific contract

- Same as R476 verbatim: placebo `P` row permutation `rho(i)=(i+1) mod 4` on same-time neighbour columns `3:7`; arms `an_cn, an_cp, ap_cn, ap_cp` x `r0,r1`; seeds `401..406`; 43,200 interaction steps per cell; zero R473/R474/R475 training or evaluation reuse; only the six sealed R473 base states imported by hash-identical hardlink.
- Reuse: exactly R476 wave-1 cells (`an_cn_r0|401..406`, `an_cn_r1|401..406`, `an_cp_r0|401..404`). Each imported manifest must be `valid=True`, 43,200 steps, arm/seed directory match, `factors` equal R477 arm factors, `base_state_sha256` equal the R477 donor base-state file hash, and `reward_function_sha256` equal the R477 donor manifest field. Any mismatch stops the pipeline.
- Fresh: exactly the 32 remaining cells (R476 wave-2 + wave-3 lists), two waves of 16.
- Effects and wording unchanged from R476.

## Engineering correction contract

1. The R477 runner is a thin adapter over the frozen R476 runner: same scientific functions, R477 paths, 32 fresh + 16 reused cell split, and an extended import phase (R473 donors + R476 training shards, both hash-identical hardlinks with provenance).
2. Governance shell reused unchanged: seal verification, terminal truth, fail-closed classification, dual review of one identical final source map, mutation tests.
3. The shard driver fix (`_log_root` anchors relative `--log-dir` to the repository root) is already committed and regression-locked; the pipeline half is guarded by `memory/tools/detached_pipeline_lint.py`. R477 runs both locks.

## Methodology

1. Copy R476 power analysis and capacity evidence into R477 (hash sidecars included); they are unchanged pre-registered inputs.
2. Write red tests for the R477 adapter: cell split 32/16, import verification rejects a mutated manifest, shard lists exact, R476 scientific contract unchanged except round/path/provenance fields.
3. Add the R477 pipeline (import, 2 training waves + eta recalibration, completeness check on 48 manifests, evaluation wave, budget/aggregate/manifest).
4. Two independent reviews of the same final source map; P0/P1 blocks repair before rehearsal.
5. Base audit, routing gate, real ANDES rehearsal, prepare; seal only final reviewed sources and exact shard lists; commit the seal before formal launch.
6. Launch the detached pipeline once. A nonzero phase stops the pipeline. No in-round patch, retune, retry, result inspection, or partial-shard promotion.

## Experiment efficiency card

- execution_class: non-quick
- job_count: 48 logical jobs = 32 fresh training shards + 16 arm-stage evaluation jobs (16 reused shards are imported, not executed)
- concurrent_jobs: 16; one launcher; one native numerical thread per process
- waves: 2 training waves + 1 evaluation wave
- eta_range: 6-9 hours wall time after launch
- eta_basis: R476 wave-1 (16 parallel cells) needed about 3 hours; two fresh waves add about 6 hours, evaluation about 1-2 hours
- eta_recalibration: after the first 16 fresh training shards complete, recompute remaining ETA from their observed wall range; do not change scope or concurrency
- artifact_budget: approximately 520 MiB expected; hard stop for review above 650 MiB before manifest finalization
- completion_rule: 48 valid 43,200-step training manifests in the R477 output root (16 imported + 32 fresh), all half/final evaluation records complete, aggregate and formal manifest hash-valid
- stop_rule: any seal/review/routing/rehearsal/hash/shard/import-identity failure, nonfinite learner output, failed TDS, missing sidecar, or artifact budget overrun stops the pipeline
- retry_rule: no retry inside R477; a scientific or integrity failure requires a successor
- interruption_rule: operator shutdown may terminate processes, but mid-shard files are incomplete and never scientific; no promise of complete data after an early stop
- interruption_artifacts: completed hash-valid shards and all partial/log files remain preserved and inventoried; partial shards are excluded
- resume_policy: no same-round resume after a mid-shard interruption; resume requires a successor that prospectively declares any completed-shard reuse

## Formal launch contract

- formal_entry: scripts/run_r477_u2_confirmatory.py <phase>
- rehearsal_command: /home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r477_u2_confirmatory.py rehearse
- rehearsal_scope: same-pre-attempt-path
- rehearsal_checks: source_hash,parent_hash,installed_package,installed_case,output_absence
- capacity_evidence: memory/rounds/R477/capacity_evidence.json
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

- Same as R476; no new external theory.

## 资产保护契约

Preserve R431/R438/R451/R460/R470-R476 and all imported external-review material byte-for-byte. Add only R477 plan/runner/tests/pipeline, copied pre-registered power/capacity inputs, reviews, base/routing/rehearsal/seal artifacts, result root, feed/claim/verdict/final package. R476's 16 wave-1 shards are read-only imports, never modified; R476 partial output stays excluded and unchanged.

## Cross-references

- `memory/rounds/R476/plan.md` (aborted)
- `memory/rounds/R475/verdict.md`
- `docs/repo-hygiene/executables.md` (path discipline locks)
- `paper/yang_md_decoupling_marl/working/gpt_pro_r474_placebo_review_deep_20260823/02_MANDATORY_REDESIGN.md`
- CLM-1315 endpoint definitions; CLM-1360 capacity; CLM-1440 executed-action semantics; CLM-1475 scientific parent boundary.
