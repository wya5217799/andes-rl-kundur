---
round: R461
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-21'
closed: '2026-08-21'
supersedes_rounds: []
superseded_by_round: null
abort_reason: formal JSONL serialization rejected positive-infinity residual for invalid
  R452 candidate after create-only output root was partially written; preserve attempt
  and repair only in successor
superseded_note: null
---
# R461 plan — U4 independent metric, guard, and finite-class phase-I audit

**Opened**: 2026-08-21
**Driver**: Independently recompute every requested endpoint and guard from retained raw traces, export the available constraint ledgers without invention, and solve the named 350-schedule finite-class maximum-violation problem by exact enumeration.
**Parent**: CLM-1440 (R460 complete executed-action trace bank); CLM-1390 (R452 complete 350-candidate-per-profile finite bank); CLM-1420 (R456 bounded frozen-network multiplier diagnostic).

## TL;DR

This is a deterministic evidence/export round. It does not rerun ANDES or train a policy. It recomputes the four R460 profile summaries from all 24 raw trajectories using an implementation independent of the canonical summariser, checks them against the canonical equations, exports all available R431/R456 cost and multiplier records with explicit missing-data labels, and enumerates all 350 R452 schedules over all four evaluation profiles to find the exact minimum possible worst normalized guard violation within that named finite class.

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

- Work class: **evidence**. Formal output root: `results/research_loop/r461_u4_guard_audit` (create-only).
- Inputs are immutable, content-hashed R460 raw trajectories, R452 per-profile candidate tables, R431 training manifests, and R456 intervention artifacts.
- No new physical trajectory, learner update, optimizer run, hyperparameter change, or historical reinterpretation is authorized.

### Independent raw-trace recomputation

For each of the four R460 evaluation profiles, retain each of the six signed scenarios separately and recompute: common-frequency IAE, worst-unit frequency peak, worst RoCoF including the initial-to-first-step boundary, off-diagonal response energy, disturbance differential energy, action RMS, boundary-aware action total variation, saturation fraction, amplitude/slew/mapping checks, completion, validity, and TDS status. The checker uses explicit NumPy equations and compares to the canonical summary function only after independently producing its result. All denominators are exported and must be finite and strictly above `1e-12`.

### Training-constraint export

- Inventory every R431 training manifest separately by arm and seed. Export raw episode costs, discount/normalization/budget definitions, multiplier traces, and update rules when present.
- If a field was never recorded by the original unconstrained learner, emit a machine-readable `not_recorded_in_original_training` status and the source-file hash; never synthesize values.
- Export the complete R456 intervention manifest and per-cell multiplier/update traces as a bounded post-hoc frozen-network diagnostic, explicitly labelled **not** original R431 training and **not** a KKT or global feasibility certificate.

### Exact finite-bank phase I

Use the same candidate ID across `eval_a` through `eval_d`; exactly 350 candidates are admissible. For every candidate and profile define dimensionless residuals, where feasibility is residual `<= 0`:

- endpoint residuals: `candidate / (0.95 * static) - 1` for disturbance differential energy and off-diagonal response energy;
- common-frequency residuals: `candidate / (1.03 * static) - 1` for IAE, worst peak, and RoCoF;
- action-stress residuals: `candidate / (1.10 * static) - 1` for RMS and boundary-aware total variation;
- saturation residual: `candidate_fraction / 0.05 - 1`;
- invalid, incomplete, mapping-failed, bound-violating, or slew-violating rows receive positive infinity and remain in the table.

For a candidate, `t` is the maximum residual across all profiles and guards. Enumerate every candidate exactly once, select the minimum `t`, and export its schedule, all residuals, active guards, runner-up margin, direct guard booleans, and an enumeration digest. `t <= 0` is an exact feasible witness for this finite 350-member, four-profile class. `t > 0` is exact infeasibility only for this named finite class; it is never evidence that the neural-policy class or the physical plant is infeasible.

### Independent acceptance checks

- exactly 24 R460 trajectories, four profiles, six distinct scenarios per profile, 30 steps per trajectory, with invalid/TDS rows retained rather than silently zeroed;
- independently recomputed and canonical numeric summaries agree within `1e-10`; boolean summaries match exactly;
- all physical and guard normalizers are positive and above `1e-12`;
- each R431 arm×seed manifest is a separate ledger row; all 30 R456 intervention cells are separately exported;
- exactly 350 shared schedule identities occur in every one of four R452 profiles, and direct residual signs reproduce the stored R452 guard booleans;
- a second read-only checker rebuilds the phase-I winner from emitted per-candidate residuals and verifies all output hashes.

External GPT material specifies requested observables and acceptance criteria only; it is not scientific evidence or theorem authority.

### Capacity and launch contract

- This round performs one dependency-ordered JSON reduction. It contains no independent simulator jobs; a single process with one native numerical thread is the measured efficient configuration because parallel parsing would duplicate large-file I/O and serialization.
- Hardware evidence records CPU, memory, GPU availability, input byte count, wall/CPU time, and peak RSS. The prior R460 15-worker result remains the applicable measured maximum for physical ANDES trajectory batches.
- rehearsal command: `python scripts/run_r461_u4_guard_audit.py rehearse`
- formal commands: `python scripts/run_r461_u4_guard_audit.py prepare` then `python scripts/run_r461_u4_guard_audit.py run`
- formal output: `results/research_loop/r461_u4_guard_audit`
- retry policy: none; preserve any terminal formal attempt and use a successor round for correction.
- formal sources and every immutable input are frozen by SHA-256 in `memory/rounds/R461/formal_seal.json` before `run`.

## Gate

Classify `U4-GUARD-AUDIT-VALID` only when every raw-trace, cardinality, formula, denominator, ledger, exact-enumeration, and hash check passes. Otherwise classify `U4-GUARD-AUDIT-INVALID` for a completed scientific mismatch or `ENGINEERING-INVALID` for source/input/runtime/output/checker failure. Report the finite-class phase-I result as a separate bounded subfinding.

## 资产保护契约

- Preserve R431, R452, R456, R458, R459, R460 and all imported GPT Pro material byte-for-byte.
- Add only R461-owned runner/tests, prospective ledger files, create-only formal outputs, and later feed/claim/manifest registrations.
- Preserve unrelated dirty-worktree changes.

## Cross-references

- CLM-1440 / R460: complete raw successor-policy trace bank and executed-action semantics.
- CLM-1390 / R452: complete finite 350-schedule candidate bank across four evaluation profiles.
- CLM-1420 / R456: bounded frozen-network multiplier diagnostic; not original training.
- `paper/yang_md_decoupling_marl/working/gpt_pro_additional_data_request_20260821/`: external request and acceptance rules.
