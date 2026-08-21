---
round: R386
state: completed
manuscript_line: converter-vsg-pq-decoupling
opened: '2026-08-14'
closed: '2026-08-14'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R386 plan — pre-init static-reference capture correction

**Opened**: 2026-08-14
**Driver**: R385 is analysis-invalid because its runner read linked static-generator `p/q` after TDS replacement; execute one separately sealed correction that freezes the source immediately after power flow and before TDS initialization.
**Parent**: Q-0105; CLM-1070; R385; ADR-0017

## TL;DR

工作量：`evidence`。保持 R385 的 ANDES、Kundur static-only construction、四台
REGCV1、device card、threshold、0.2 s zero-input job 和全部判据不变；只把
reference source capture 移到 PFlow 成功后、`TDS.init()` 前，并保存 capture
phase proof。唯一正式记录 PASS 才开放另轮 signed authority；科学失败 STOP；
任何 capture/provenance/diagnostic 缺陷 INVALID。无本轮重试、控制器或训练。

## Snapshot at plan-time (oracle as of 2026-08-14)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0105 [opened R385] Can the same four-device REGCV1 card pass native initialization and a zero-input short TDS when the unchanged packaged Kundur static tables are reconstructed with no legacy synchronous-machine, governor, or exciter records?

## Recently Closed (last 3)

- Q-0104 closed-negative @ R384, by CLM-1065 — Can four ANDES REGCV1 converter-level VSG devices replace the four dynamic generator chains on the unchanged Kundur network, preserve exact one-to-one static-generator ownership and mutable Pref/Qref interfaces, and complete zero-input initialization and short TDS without numerical drift or non-finite electrical variables?
- Q-0103 closed-negative @ R369, by CLM-0990 — Does one globally fixed local-neighbour per-VSG M/D controller clear the deterministic efficacy and no-harm gate on the balanced development bank, while a bounded non-learning outcome oracle shows at least five percent additional headroom with nonconstant direct actions?
- Q-0102 closed-positive @ R366, by CLM-0980 — Can the fixed-title line freeze a 60-Hz, permission-matched per-VSG inertia/damping comparison contract and a deterministic baseline family that leaves a falsifiable learning gate without importing the old action-object mismatch or claiming storage feasibility?

## Methodology

### Single correction and falsifiable objective

- Keep ANDES 2.0.0, the exact packaged Kundur XLSX/JSON static tables, the
  canonical static-only derived input, the four `(REGCV1_i,bus=i,gen=i)`
  bindings, and the complete R384/R385 REGCV1 parameter card unchanged.
- Keep zero `GENROU/TGOV1/EXDC2/Toggler` records and require no forbidden DAE
  name token after initialization.
- After `PFlow.run()` returns success and before calling `TDS.init()`, capture
  each linked StaticGen's actual `p/q` into an immutable `reference_source`
  table. Record `phase=post_pflow_pre_tds_init`,
  `pflow_converged_at_capture=true`, and `tds_initialized_at_capture=false`.
- After TDS initialization, compare each REGCV1 `Pref/Qref` with that captured
  row using the unchanged absolute tolerance `1e-12`. Do not read the replaced
  StaticGen as the source after TDS initialization.
- Run the unchanged native zero-input `tf=0.2 s` trajectory only after native
  initialization succeeds. Preserve equation-level residuals, limit rows,
  finite guards, and `Pe/Qe/dw/omega/v` drift against native tolerance.
- No disturbance, write probe, controller, reward, training, parameter tuning,
  threshold change, topology change, converter substitution, or R385 result
  reuse enters this round.

### Integrity and invalidity precedence

- Bind the exact runner, thin R386 classifier, reused R385 lifecycle module,
  builder, tests, plan, question, line/route state, parent claim/feed/verdict,
  installed ANDES/REGCV1 source, packaged cases, rehearsal, capacity record,
  and contract in a create-only formal seal.
- The R386 classifier must validate its own contract digest, then fail closed
  unless the four-row source snapshot is finite, uniquely mapped, captured at
  the required lifecycle boundary, and used verbatim in every comparison row.
- Instrumentation/API/runtime/capture exceptions are `ANALYSIS-INVALID`.
  Only expected native solver failure or a complete scientific guard failure
  can be `STOP-REGCV1-CLEAN-INITIALIZATION`.
- `trajectory_attempted` is distinct from an executed trajectory; count one
  only after observed simulation-time advancement.

### TDD and review gate

- First add failing tests for: wrong capture phase, source/reference row drift,
  incomplete source rows, R386 contract digest, and the PFlow-before-capture-
  before-TDS-init call order.
- Then implement the smallest wrapper/classifier correction without editing
  any R385 sealed input or artifact.
- Run focused tests, lint, preflight, repository validation, and an independent
  launch review before rehearsal. The setup-only rehearsal may call `setup()`
  but not `PFlow.run()` or any TDS method.

### Resource contract

- One independent quick formal job; one WSL Python process and one native
  numerical thread. A capacity ladder or higher process count would add
  launcher overhead without parallel work.
- Rehearsal records current host/WSL memory, disk, competing research
  processes, source/parent/runtime hashes, static-table identity, derived-case
  determinism, structural absence, setup-only construction, and output absence.
- Formal output is create-only under
  `results/research_loop/r386_regcv1_reference_capture_gate/`.

## Formal launch contract

- `formal_entry`: `scripts/run_r386_regcv1_reference_capture_gate.py`.
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r386_regcv1_reference_capture_gate.py rehearse`.
- `rehearsal_scope`: `same-pre-attempt-path`; setup-only, with no PFlow or TDS
  call and `physical_trajectory_executed=false`.
- `rehearsal_checks`: `source_hash`, `parent_hash`, `installed_package`,
  `installed_cases`, `static_table_identity`, `derived_case_determinism`,
  `structural_absence`, `setup_only_canary`, `output_absence`,
  `question_in_flight`, `active_plan`, `no_competing_research_process`, and
  `physical_trajectory_executed=false`.
- `capacity_evidence`: `memory/rounds/R386/capacity_evidence.json`.
- `host_process_budget`: 1; `wsl_python_processes`: 1;
  `native_threads_per_process`: 1; `other_reserved_processes`: 0.
- `seal_command`: `/home/wya/andes_venv/bin/python scripts/run_r386_regcv1_reference_capture_gate.py prepare`.
- `seal_path`: `memory/rounds/R386/formal_seal.json`; it binds rehearsal,
  capacity evidence, contract, sources, parents, runtime, cases, and derived
  case before any formal attempt exists.
- `formal_execute_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r386_regcv1_reference_capture_gate.py execute --expected-seal-sha256 <sha256>`.
- `formal_output`: create-only
  `results/research_loop/r386_regcv1_reference_capture_gate/`; one attempt,
  no overwrite, retry, or post-seal source/card/threshold change.

## Gate

- `REGCV1-CLEAN-INIT-PASS`: all source, snapshot timing, structure, mapping,
  reference, native solver, residual, finite, and drift guards pass. This opens
  only a separately registered signed dynamic Pref/Qref authority question.
- `STOP-REGCV1-CLEAN-INITIALIZATION`: the record is complete and valid, but a
  scientific solver/reference/finite/drift guard fails. Close Q-0105 negative
  and stop REGCV1 without tuning or substitution.
- `ANALYSIS-INVALID`: provenance, capture timing/schema, source-to-comparison
  identity, diagnostics, execution, seal, or output integrity fails. Preserve
  the invalid record; no R386 retry or scientific conclusion.

## 资产保护契约

- Immutable: every R384/R385 seal, result, feed, claim, verdict, and sidecar;
  packaged ANDES cases and installation; Kundur topology/static data; REGCV1
  card; all earlier lines, checkpoints, results, and evidence.
- New/modified before seal: R386 plan, thin reference-timing classifier and
  runner, focused tests, Q/programme/line/route navigation, rehearsal,
  capacity evidence, and formal seal.
- New after seal: exactly one create-only formal result root, then normal
  feed/claim/verdict/manifest/navigation close-out.
- Forbidden: editing R385 files or artifacts, copying R385 values into the new
  record, post-outcome threshold/card changes, retry, controller, perturbation,
  training, topology/model substitution, or treating a setup/test pass as
  signed physical authority.

## Cross-references

- CLM-1070 / R385: endpoint capture occurred after TDS replacement, invalidating
  the apparent reference-mismatch STOP and allowing only this separately sealed
  timing correction.
- CLM-1065 / R384: status-disabled legacy-chain construction remains stopped;
  no result or diagnosis transfers as R386 evidence.
- ADR-0017 / CLM-1060: structural absence stays on the same manuscript line and
  preserves ANDES/Kundur, controlled locations, and physics-first gate order.
