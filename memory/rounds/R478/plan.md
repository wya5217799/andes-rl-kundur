---
round: R478
state: active
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-24'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R478 plan — corrected M/D base-convention revalidation: Phase 0 build + Phase 1 banks, owner review gate before formal execution

**Opened**: 2026-08-24
**Driver**: Corrected-M/D revalidation program, Phase 0 + Phase 1. `GENCLS.M/D` are base-converted power parameters; the V4 reset path records the unconverted M baseline as the interpolation anchor, so a zero first action can change runtime inertia while the reported action increment is zero. One device/system-base convention is enforced, invariants proven, deterministic banks rebuilt under the corrected card; no formal attempt before the owner reviews the frozen program.
**Parent**: corrected_md_revalidation_experiment_plan_20260824.md (authority); ADR-0019.

## TL;DR

R478 freezes the physical parameter card (device/system-base convention with primary-source justification), implements the single conversion fix in the shared reset/anchor path, proves the seven 0C invariants, adapts the frozen deterministic direct-M/D and energy-port banks to the corrected card with unchanged profiles/guards/split, seals and rehearses, then STOPS. The owner reviews the frozen program; only after approval does R478 create formal attempts and close.

## Frozen scientific contract

- One scientific change: M/D initialization, runtime application, telemetry, and interpolation anchors use one declared device/system-base convention; conversion happens exactly once. Everything else (laws, gains, profiles, split, window, endpoint definitions, guards, topology list, exclusion gates) unchanged.
- Parameter card fields: `S_n,i`; `S_b`; device-base `H_i`, `M_i=2H_i`, `D_i`; runtime system-base M/D; normalized-to-physical action map; clamps + slew rule; units + conversion equation per field.
- Physical card chosen from model semantics + primary-source engineering justification (Yang2023 benchmark card + primary VSG literature), never from controller performance.
- Old artifacts preserved as historical evidence, byte-for-byte; the corrected bank has distinct identity and result root; old and corrected numbers are never pooled.
- Deterministic banks: selection uses development profiles once; evaluation profiles remain unseen; no retune after evaluation visibility.

## Engineering correction contract

1. Fix lands in the shared reset/anchor path (`base_env.py` / `andes_vsg_env_v4.py`; NOTES_ANDES.md read before edits). Anchor = declared system-base runtime value; reported action increments use the same convention; telemetry readback compared in that convention.
2. V4 regression expectations re-locked to the corrected semantics inside this round; documented as the single deliberate change; historical checkpoints stay historical and are never imported into the corrected bank.
3. Card + conversion helpers = reusable implementation in `src/andes_rl_kundur/`; invariant tests in `tests/`; bank adapters as stable scripts; governance shell (seal verification, fail-closed classification, dual review of one identical final source map, mutation tests) reused from the R477 pattern.
4. Comparison identifiability: corrected vs historical numbers are compared only in the manuscript/review layer; within-bank comparisons are corrected-only.

## Methodology

1. 0A/0B: audit primary sources; write + register the parameter card and justification note in ARTIFACTS.
2. 0C: write the seven invariant tests red-first (zero action; telemetry; round trip; heterogeneous card; nonzero-action branch/clamp/slew units; energy-port slow channel; reset repeatability). Confirm the zero-action invariant fails pre-fix (bug reproduced).
3. Implement the conversion fix; all invariants green; V4 regression re-locked green.
4. Locate the registered frozen banks (zero-action, nine-law, dev/eval schedule, energy-port unseen/extra-condition, topology variants) and re-point them at the corrected card via `scripts/run_r478_md_revalidation.py`: parent sealed runners stay byte-identical (frozen sha256 table), the adapter patches round id + output root only, records a rekey sidecar per dispatch, and runs the zero-action trace bank directly. Guards/profiles/split/windows unchanged. Trace capture (1C) = per-step rows of every re-run bank + the zero-action records.
5. Freeze-then-review: two independent reviews of the frozen commit + file hashes; P0/P1 repaired before seal.
6. Seal + commit; capacity ladder on representative deterministic jobs (rung sizes per CLAUDE.md); rehearsal through the formal entry's same-pre-attempt path (source_hash, parent_hash, installed_package, installed_case, output_absence); no formal attempt created.
7. STOP — owner review gate. No formal attempt, retry, or result inspection until the owner approves. Post-approval: formal banks execute; gates decide; round closes with feed/claim/verdict.

## Gate

- INVARIANT-GATE: all seven 0C invariants green before any simulator bank; any failure = engineering invalidity, no scientific run follows.
- GATE-1A: at least one frozen deterministic comparator finite and guard-valid on its registered scope; else stop direct-M/D learner training and revise the paper route.
- GATE-1B: frozen energy-port controller passes its registered contract; else drop/redesign the constructive companion in a new plan; no tuning in this run.
- GATE-1C: complete frequency/M-D/action/topology/disturbance traces retained for every valid record.
- Integrity: paper-facing EIG passes TDS.test_ok + exit_code=0 + init residuals + finite spectrum + positive-real guard (CLM-0665).
- Claim hygiene: any paper-reward-ablation headline must cite geo + cum_rf (dual_metric_lint at claim time).

## Theory intake

No external mathematical theory this round; the base convention is primary-source engineering. external_theory_intake_lint N/A.

## Experiment efficiency card

- execution_class: non-quick
- job_count: symbolic (`N_det` + `N_port`) until the frozen bank list is located and re-pointed
- concurrent_jobs: derived budget 4 workers + 1 launcher, pending the pre-launch capacity ladder; not a hard cap
- waves: `ceil(J/5)`, recomputed at seal
- eta_range: unset until corrected rehearsal/first-wave timing exists (do not invent)
- artifact_budget: symbolic; hard review stop set at seal from rehearsal disk telemetry
- completion_rule: every registered bank job valid + trace bank complete + manifest hash-valid
- stop_rule: any invariant/seal/review/routing/rehearsal/hash failure, nonfinite output, failed TDS, or missing sidecar stops the pipeline; no in-round patch or retry
- retry_rule: no silent retry; failed attempts preserved; post-seal source or contract change requires a successor round
- interruption_rule: operator shutdown may terminate processes; partial artifacts are never scientific; resume requires a successor that prospectively declares reuse
- owner_review_gate: after seal+rehearsal, formal attempts are BLOCKED until the owner approves the frozen program (pre-registered, not a gate-lifecycle change)

## Formal launch contract

- formal_entry: scripts/run_r478_md_revalidation.py <family> <phase> (families: zero|ninelaw|schedule|port_unseen|port_extra_k35|port_extra_k4|topology; parent runners stay byte-identical, rekey sidecar per dispatch)
- rehearsal_command: /home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r478_md_revalidation.py <family> rehearse
- rehearsal_scope: same-pre-attempt-path
- rehearsal_checks: source_hash,parent_hash,installed_package,installed_case,output_absence
- capacity_evidence: memory/rounds/R478/capacity_evidence.json (produced by the pre-launch ladder)
- wsl_python_processes: 5 (4 workers + 1 launcher; derived, re-measured before formal launch)
- native_threads_per_process: 1
- host_process_budget: 5
- other_reserved_processes: 0

## 资产保护契约

Preserve R398-R477 artifacts, all imported external-review material, and every historical checkpoint byte-for-byte. Add only: parameter card + justification, conversion fix + invariant tests, corrected bank adapters + trace capture, reviews, seal/rehearsal artifacts, corrected result root (distinct identity), feed/claim/verdict. Historical results are never pooled with corrected results.

## Cross-references

- paper/yang_md_decoupling_marl/working/corrected_md_revalidation_experiment_plan_20260824.md (authority)
- docs/adr/0019-separate-yang-md-decoupling-marl-successor.md
- docs/eng-notes/NOTES_ANDES.md (required before env edits)
- CLM-0665 topology/EIG hard gate; R477 structure template (plan, efficiency card, launch contract)

## Snapshot at plan-time (oracle as of 2026-08-24)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] Does the finite-bank information-level margin program (shared action variables per non-anticipative info class, solution section 5.4) certify or refute INFORMATION-LIMITED for the 2% joint target under the exact R352/R353 observation histories?

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375 — Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0004 closed-negative @ R442, by CLM-1370 — AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?
