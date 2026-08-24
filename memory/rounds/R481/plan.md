---
round: R481
state: active
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-25'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R481 plan — corrected-card fresh-holdout direct-M/D deterministic formal bank

**Opened**: 2026-08-25
**Driver**: owner accepted abandonment of the bounded positive energy-port claim and selected the direct-M/D main-line re-verification (prospective decision OWNER-APPROVED 2026-08-25, conditions 2-7 binding). This formal deterministic direct-M/D bank is the first gate of that route; training, MARL attribution, topology expansion, and manuscript-number replacement stay closed until it passes.
**Parent**: R480 completed (CLM-1500 OPEN-LOOP-H-SENSITIVE, CLM-1495 reuse decision); R478 repair6 corrected-M/D chain; R399 headroom contract as the reused mechanism (module unchanged; fresh profiles passed via the `contract` argument).

## TL;DR

Re-run the frozen nine-law + zero deterministic bank (10 arms x 6 profiles x 6 scenarios = 360 records, 30 steps @ 0.2 s) under the corrected card with six prospectively frozen genuinely fresh profile rows (2 development + 4 evaluation; every R399/R401 viewed row excluded). Development selection picks one winner by the frozen R399 rule; the Phase-1A gate then requires the winner to be finite and guard-valid on all four fresh evaluation profiles. Outcomes: `ENGINEERING-INVALID` / `DIRECT-MD-FORMAL-PASS` / `DIRECT-MD-FORMAL-FAIL`; R399 ratio and oracle-improvement numbers are registered secondary report lines.

## Snapshot at plan-time (oracle as of 2026-08-25)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] Does the finite-bank information-level margin program (shared action variables per non-anticipative info class, solution section 5.4) certify or refute INFORMATION-LIMITED for the 2% joint target under the exact R352/R353 observation histories?

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375 — Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0004 closed-negative @ R442, by CLM-1370 — AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?

## Frozen scientific contract

- Card: corrected project calibration, device-base H0=100 s (M0=200 s), D0=100, one-convention conversion applied exactly once (R478 repair6 chain). H-anchor registered from CLM-1500: the 6 s window is the primary paper-facing metric; the 30 s tail caveat is registered in the claim boundary (this bank keeps the frozen R399 30-step schema).
- Arms: zero + nine local_neighbour_md candidates (3x3 gain grid {0.5,1.0,2.0}^2, slew 0.25, bounds [-1,1], decoder M/D +/- {600,200}, clamps M>=20 D>=10).
- Profiles: six fresh rows (2 dev + 4 eval), R399 schema (baseline_m0[4], baseline_d0[4], steady_loads, probe_magnitude, localized_location, localized_magnitude); generation + exclusion spec in `tmp/yang_md_decoupling_marl/successor_authority_gen_dsh/03_holdout_generation_design.md`; frozen create-only JSON + sha256 before any execution.
- Scenarios: per profile 3 pair kinds {common,differential,localized} x 2 signs = 6; delta_u maps as R399.
- Records: 30 steps, dt 0.2 s, physical 60-Hz frequency coordinate (never pooled with the 50-Hz controller coordinate), executed M/D readback, seed 42, four-VSG GENCLS object, corrected runner path.
- Thresholds: minimum_joint_improvement 0.05; maximum_common_harm 0.03; maximum_action_stress_harm 0.10; maximum_action_saturation_fraction 0.05; nonconstant_action_variation_floor 1e-6; independent_action_dispersion_floor 1e-6; ratio-to-zero <= 0.95 is a REGISTERED REPORT LINE (canary 2A bar), not a pass/fail gate (open item O1, recommended default).
- Selection: development profiles used once; winner = R399 frozen rule (eligible candidate with smallest (worst_ratio, ratio_sum, aggregate_action_rms, arm_id)); positive zero reference required.

## Pre-registered outcomes (预期 vs 实际)

- `ENGINEERING-INVALID`: any TDS/nonfinite/mapping/bound/slew failure, duplicate/missing record, hash/sidecar drift, wrong step count, M/D drift, fresh-profile bank tampering, or rehearsal/formal mismatch above 1e-9.
- `DIRECT-MD-FORMAL-PASS`: valid bank, winner exists, winner finite + guard-valid on all four fresh evaluation profiles (valid summary, mapping pass, no bound/slew violation, common no-harm vs zero at 3%, saturation <= 0.05, nonconstant variation, per-VSG dispersion). Secondary lines report the two ratios and the oracle improvement numbers.
- `DIRECT-MD-FORMAL-FAIL`: valid bank and the winner fails the 4/4 gate (one-to-three passing profiles cannot open; no fallback arm; stop direct-M/D learner training and revise the paper route).
- Bound: nothing downstream is authorized by this round; the 224-job source factorial remains a shelf plan.

## Methodology

1. Implementation (this round): fresh-profile generator + contract writer (`src/andes_rl_kundur/evaluation/r481_fresh_profiles.py`), successor runner adapting `scripts/run_r399_md_decoupling_headroom.py` to the corrected card + fresh contract + new output root, targeted tests (shape, exclusion vs the 14 viewed rows, contract roundtrip, create-only).
2. Freeze order: code -> review -> fresh-profile contract JSON + sha256 (create-only) -> preflight -> rehearsal via the SAME pre-attempt path (source/parent hash, installed package/case, output absence; one representative record) -> seal -> commit -> owner approval -> formal execute.
3. Execute: 16 workers + launcher, one native thread each, create-only records with sidecars under `results/research_loop/r481_direct_md/`.
4. Summarise (R399 summarise_profile) -> classify (R399 classify_bank with the fresh contract) -> Phase-1A 4/4 gate -> verify all hashes.
5. Close-out: claim -> feed -> publication gate -> verdict -> MANIFEST -> LINE evidence_refs -> close.

## Gate

- `ENGINEERING-INVALID` / `DIRECT-MD-FORMAL-PASS` / `DIRECT-MD-FORMAL-FAIL` as registered; the 4/4 rule is exact ("one-to-three passing profiles cannot open the gate"); no retry, partial artifacts preserved, any post-seal change requires a successor round.

## Formal launch contract (skeleton; filled at seal)

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r481_direct_md.py execute`
- rehearsal_command: same entry `rehearse`; rehearsal_scope: same-pre-attempt-path; rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: `memory/rounds/R481/capacity_evidence.json` (16-worker precedent reuse per `tmp/yang_md_decoupling_marl/successor_authority_gen_dsh/04_capacity_plan.md` + one 16x8 quick confirm)
- wsl_python_processes: 17 (16 workers + 1 launcher)
- native_threads_per_process: 1
- host_process_budget: 17
- other_reserved_processes: 0 (verified at reservation: no active rounds, no WSL jobs)

## 资产保护契约

R478 repair6 chain, R479 seal/rehearsal/orphan, R480 results, R399/R401 modules, and all historical evidence stay byte-identical. Add only: this round's plan/verdict/contract/seal/capacity/rehearsal, one fresh-profile contract JSON + sidecar, one successor runner + generator module + tests, and `results/research_loop/r481_direct_md`. Old profile rows are never re-used, pooled, or edited.

## Open items for owner review (before seal; recommended defaults registered)

- O1: guard set of the 4/4 gate — recommendation: Phase-1A + R399 full set; ratios (<=0.95) as report lines, not gate.
- O2: fresh-profile value ranges — recommendation: same schema ranges as the burned rows, new RNG draw seed 481, exclusion check against all 14 viewed rows.
- O3: bank completeness — recommendation: full 360-record bank so the R399 selection + ratio lines stay computable, even though Phase-1A only tests the winner on evaluation profiles.

## Cross-references

- paper/yang_md_decoupling_marl/working/prospective_direct_md_successor_decision_20260825.md
- paper/yang_md_decoupling_marl/working/corrected_md_revalidation_experiment_plan_20260824.md
- src/andes_rl_kundur/evaluation/md_decoupling_headroom.py
- src/andes_rl_kundur/control/per_vsg_md.py
- scripts/run_r399_md_decoupling_headroom.py
- memory/rounds/R478/formal_seal_r478_port_unseen_repair6.json
- memory/rounds/R479/formal_seal.json; memory/rounds/R480/plan.md
- tmp/yang_md_decoupling_marl/successor_authority_gen_dsh/01_design_facts.md
