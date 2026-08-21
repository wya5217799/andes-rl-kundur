---
round: R459
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-21'
closed: '2026-08-21'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R459 plan — U1–U8 shared model and protocol export

**Opened**: 2026-08-21
**Driver**: Freeze the complete, auditable Object A/Object B model, unit, input/output, controller, headroom, and perturbation contracts required by the owner-authorized GPT Pro U1–U8 advisory program before any new certificate or training claim is attempted.
**Parent**: CLM-1430 (R458 fixed-perturbation algebraic certificate); external request `gpt-pro-additional-data-request-2026-08-21` is design input only and is not repository evidence.

## TL;DR

One create-only composite export will reconstruct the already-governed R446 direct-M/D Object A and R447 nominal energy-port Object B, emit raw continuous/pre-ZOH/post-ZOH matrices plus provenance and protocol contracts, and pass an independent checker that recomputes dimensions, equilibrium/reduction residuals, ZOH identities, units, and content hashes. This round makes no U1, U2, or U5–U8 mathematical conclusion.

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

- Work class: **evidence**. One formal WSL composite job; no training and no parameter search.
- Formal output root: `results/research_loop/r459_u1_u8_shared_export` (create-only).
- Reusable implementation: `src/andes_rl_kundur/evaluation/u1_u8_shared_export.py`.
- Formal runner: `scripts/run_r459_u1_u8_shared_export.py` through `scripts/andes_scratch.py` and `/home/wya/andes_venv/bin/python` only.
- The round exports shared inputs for later successors. It does not certify Q/Y10, total sensitivity, fractional delay, mixed-block scaling, separation bounds, or any learned controller.

### Object B: sampled energy-port source

Reconstruct the R447 nominal source at the same initialized Kundur energy-port operating point:

- four system-pu control inputs, three frozen PQ disturbance inputs, and four 60-Hz output channels;
- nominal sample period `0.2 s`;
- the governed `K=3.5` band-pass controller, local PI controller, and R272 headroom contract;
- the selected joint finite-difference bridge and its step ladder (`1e-4`, `1e-5`, `1e-6`);
- raw initialized DAE snapshot, input bridges, zero-time-constant fold, reduced continuous model, pre-step ZOH realization, and post-step sampled realization;
- exact state/algebraic/input/output names, equilibrium values and residuals, units, controller definitions, disturbance profiles, reference conventions, and guard thresholds.

The export includes `E_d`, `F_x`, `F_a`, `G_x`, `G_a`, `F_u`, `G_u`, continuous `A/B`, pre-step `A_d/B_d/C/D`, and post-step `A_d/B_d/C/D`. Linear solves/SVD are used; explicit matrix inversion is forbidden.

### Object A: direct M/D authority contract

Reconstruct the R446 nominal four-GENCLS direct-M/D callback at the same initialized Kundur case and export:

- all eight normalized input columns and exact normalized-to-physical M/D mapping;
- baseline/equilibrium state and algebraic vectors, `f_y/g_y`, finite-difference `f_u/g_u`, and derived reduced continuous input matrix;
- action slew/previous-action semantics, bounds, state/input names, units, finite-difference steps, and solver/guard configuration;
- source/runtime/case hashes sufficient to reproduce the export.

### Independent verification

An independent checker reads only the emitted machine artifacts and source contracts, not the generator's pass summary. It verifies:

1. array shapes, finite values, labels, and unit cardinality;
2. equilibrium and descriptor-reduction residual thresholds;
3. pre-/post-step sampled-output identities;
4. Object A eight-column mapping and Object B `4+3 -> 4` channel contract;
5. SHA-256 entries for every required file and the provenance manifest.

### Prospective outcomes

- `SHARED-MODEL-EXPORT-VALID`: every required artifact and identity is present, all values are finite, dimensions/labels/units match, equilibrium and reduction residuals are within the frozen source tolerances, pre-/post-step ZOH identities reproduce within `1e-10` absolute error, and all hashes pass. The exported objects may then be used only as inputs to separately reserved U1/U3–U8 successors.
- `SHARED-MODEL-EXPORT-INVALID`: the job terminates but any required check above fails. Preserve all artifacts; do not use the export for mathematics or experiments; open a successor only after identifying the engineering cause.
- `ENGINEERING-INVALID`: source/runtime/case identity drift, pre-existing output, solver/resource failure, missing terminal artifact, or checker execution failure. Preserve the attempt and make no scientific inference.

There is no magnitude-based rescue or partial-success band in this provenance round: all required contract checks are conjunctive. No measured-performance baseline comparison is planned.

### Theory-intake observables

- `object_b_complete_sampled_model`: complete continuous, pre-ZOH, post-ZOH, controller, headroom, unit, and perturbation export.
- `object_a_complete_md_input_contract`: complete direct-M/D input mapping and linearized authority export.
- `object_reference_separation`: explicit statement that Object A and Object B are distinct evidence objects and cannot be pooled.

No external theorem text is treated as evidence; external GPT material only specifies observables to test.

### Execution and capacity contract

- Current readiness begins at `MEASURE-FIRST`; non-authoritative native-thread probes at 1/4/8 threads may reconstruct the same representative composite solely to measure runtime/RSS. Select the fastest stable rung only if its output identities pass; then the same-entry rehearsal must measure runtime and peak RSS before sealing.
- Host ceiling anchor: R458 demonstrated 17 live WSL Python processes, but this round contains one ready composite job, so formal allocation is one WSL Python process with one compute thread.
- Required process fields: `host_process_budget=17`, `wsl_python_processes=1`, `threads_per_process=4`, `other_worker_processes=0`. The 1/4/8-thread representative ladder measured 1.831/1.251/1.278 seconds and selected four threads prospectively.
- Formal command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r459_u1_u8_shared_export.py <sealed-command>`.
- Rehearsal is in-memory or writes only to `memory/rounds/R459/`; it must not create the formal result root.
- No in-place resize, retry, parameter change, or scientific-result inspection is authorized after sealing.

### Formal launch contract

- formal_entry: `scripts/run_r459_u1_u8_shared_export.py run`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r459_u1_u8_shared_export.py rehearse`
- rehearsal_scope: `same-pre-attempt-path`
- rehearsal_checks: `source_hash,parent_hash,installed_package,case_hash,output_absence,array_finiteness,dimension_contract,unit_contract,equilibrium_guard,reduction_identity,zoh_identity,independent_checker`
- output_absence_check: `results/research_loop/r459_u1_u8_shared_export must not exist`
- formal_output: `results/research_loop/r459_u1_u8_shared_export`
- capacity_evidence: `memory/rounds/R459/capacity_evidence.json`
- host_process_budget: `17`
- wsl_python_processes: `1`
- threads_per_process: `4 (selected from measured 1/4/8 native-thread rung before sealing)`
- other_worker_processes: `0`
- retry_policy: `none; preserve terminal attempt and require a successor round`
- completion_rule: `verification_report verdict SHARED-MODEL-EXPORT-VALID and zero SHA-256 failures`

## Gate

Classify `SHARED-MODEL-EXPORT-VALID` only if the formal create-only run completes, all declared source/runtime/case identities match the seal, every required artifact is present and hashed, the independent checker passes, and all prospective dimension/unit/equilibrium/reduction/ZOH thresholds pass.

Classify engineering-invalid and preserve the attempt on any source/runtime/case drift, pre-existing formal output, missing or non-finite array, mapping/dimension/unit mismatch, equilibrium/reduction/ZOH failure, hash failure, solver failure, or resource-safety trigger. No scientific inference may be drawn from an invalid attempt. Any correction requires a separately reserved successor round.

## 资产保护契约

- Preserve R446, R447, R451, R458, their result roots, manifests, and sealed verdicts byte-for-byte.
- Do not overwrite the imported GPT Pro request; it remains non-authoritative design input.
- Add only R459-owned source, tests, round records, create-only result artifacts, feed/claim/domain registrations, and hashes.
- Preserve the dirty worktree; bind the formal attempt to both Git identity and content hashes for relevant uncommitted files.

## Cross-references

- CLM-1430 / R458: fixed-perturbation algebraic certificate, verification only; no rerun here.
- R446: Object A direct-M/D authority source contract.
- R447 and R272: Object B nominal energy-port source/controller/headroom contracts.
- R451: canary-invalid algorithm audit; no learned-policy evidence is inherited.
- `paper/yang_md_decoupling_marl/working/gpt_pro_additional_data_request_20260821/IMPORT_NOTE.md`: external-request disposition and stale-status corrections.
