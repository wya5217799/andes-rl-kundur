---
round: R479
state: queued
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-24'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R479 plan — corrected-card uniform-H zero-action sensitivity

**Opened**: 2026-08-24
**Driver**: owner-authorized cheap check of whether the frozen `H0=100 s` card hides material open-loop dynamic sensitivity after the R478 base-conversion correction.
**Parent**: R478 sealed corrected M/D implementation; `md_parameter_card_20260824.json`.
**Workload**: `evidence`

**Queue status**: R478 remains the sole active owner of this manuscript line. While
R479 is queued, one owner-authorized six-worker development screen may run under
`tmp/`; it is explicitly non-claim-bearing and cannot substitute for the sealed
formal bank after R478 closes and R479 is activated.

## TL;DR

Run one prospective, zero-action, all-trace bank at device-base `H0={10,100,300} s`, with `D0=100` fixed, on the two registered load steps. One 30 s run per cell supplies both the paper-facing first 6 s window and a long-tail check. This round tests open-loop H sensitivity only. It does not validate D realism, controller ordering, learning robustness, or the Yang paper's unspecified baseline.

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

## Frozen scientific contract

- Factor: uniform device-base `H0 in {10,100,300} s`; `M0=2H0`; runtime M is converted exactly once to system base.
- Fixed: corrected R478 source, four VSGs, `D0=100` device base, zero action, LS1/LS2, seed 42, `dt=0.2 s`, topology, governors, loads, solver, telemetry, frequency estimator, and all non-M settings. Record both the paper-facing 50-Hz controller coordinate and the ANDES physical-frequency coordinate; never pool them.
- Identity: six cells = three H levels x two load steps; each cell runs 150 control steps (30 s). First 30 steps are the frozen 6 s paper-comparison window.
- `H=300 s` is a stress point, not a Yang absolute bound. The Yang paper gives action increments but no baseline H/D card.
- Primary unit: one deterministic scenario-card cell. No probability, inference, controller, stability-certificate, or generalization claim.

## Methodology

1. Rehearse one `H=100 s`, LS1, 30-step cell through the same pre-attempt path. Verify source closure, installed package/case, output absence, TDS, finite values, and constant corrected M/D readback.
2. Seal runner, analysis, contract, R478 parent hashes, rehearsal, owner authorization, worker budget, and output schema; commit before formal attempt.
3. Execute six independent cells with six workers and one launcher. Store full per-bus frequency and M/D traces create-only, each with SHA-256.
4. Derive per cell: 0-6 s peak and endpoint, 0-30 s peak and endpoint, late 6-30 s span, and time entering/staying within 0.02 Hz of its 30 s endpoint.
5. Compare each H level with H=100 by signed and absolute ratios. The 10% bar is a prospective engineering screen borrowed from the parent programme's materiality scale; it is not a significance test.

## Gate

- `ENGINEERING-INVALID`: missing/duplicate cell; any TDS/nonfinite failure; wrong step count; M/D drift; seal/hash mismatch; or H=100 rehearsal/formal mismatch above `1e-9` for the 6 s peak/final values.
- `OPEN-LOOP-H-SENSITIVE`: valid bank and any H=10 or H=300 cell changes a primary 6 s peak/final endpoint by at least 10% versus H=100, changes the 30 s settling-status class, or changes finite/guard status.
- `NO-MATERIAL-OPEN-LOOP-H-SENSITIVITY-DETECTED`: valid bank and none of the above triggers.
- Either valid outcome is bounded to zero action on LS1/LS2. It cannot establish that learned or deterministic controller ordering is stable. A controller-ordering check, if still wanted, must wait for the R478 corrected deterministic bank and use a successor contract with clamp/saturation reporting.

## Development screen result — decision input, not formal evidence

The owner-authorized queued screen completed all six unique cells with six
independent worker processes in 73.46 s. All cells were finite, kept the frozen
device-base M/D readback, and passed the deterministic analysis checks. The
create-only record is `development_screen.json`, SHA-256
`1579aaf998d6d0592b51c8ca5103b737ad1dadd5ad91051fb25a0290cc13192e`.

| H0 (s) | LS1 peak, 0-6 s (Hz) | LS2 peak, 0-6 s (Hz) | settle to 30 s endpoint, LS1/LS2 (s) |
|---:|---:|---:|---:|
| 10 | 0.253903 | 0.180990 | 3.8 / 3.2 |
| 100 | 0.131610 | 0.095382 | 8.4 / 6.0 |
| 300 | 0.086095 | 0.062654 | 14.4 / 8.6 |

Decision-relevant interpretation:

- Open-loop transient shape is materially H-sensitive. Relative to H0=100 s,
  the 0-6 s peak rises by 92.9%/89.8% at H0=10 s and falls by 34.6%/34.3%
  at H0=300 s for LS1/LS2.
- H0=300 s reaches its 30 s peak after the paper-facing 6 s window: 0.101831 Hz
  versus 0.086095 Hz for LS1, and 0.076674 Hz versus 0.062654 Hz for LS2.
  A 6 s window therefore does not characterize the full high-inertia transient.
- The 30 s endpoints remain close across H, so this screen diagnoses transient
  timing/peak sensitivity rather than a materially different equilibrium.
- Keep H0=100 s and the 6 s metric as the benchmark anchor, but add a 30 s tail
  evaluation. Before any cross-H robustness claim, rerun the actual controllers
  at H0={10,100,300} s and check whether their ordering changes.
- This screen does not test D0 realism, learned-policy robustness, controller
  ordering, or Yang-baseline reproduction. It must not support manuscript claims
  until the queued formal bank reproduces it and closes through the evidence gate.
- No retry. Partial/failure artifacts stay preserved. Any post-seal change requires a successor round.

## Experiment efficiency card

- Execution readiness: MEASURE-FIRST until the one-cell rehearsal exists; RUN-READY only after rehearsal + seal.
- Decision and authority: owner authorized adding and running this check in the current task.
- Stage: formal quick evidence after one representative rehearsal.
- Jobs: six independent 150-step cells; six workers + one launcher; no other WSL research process is active at freeze time.
- Capacity: R478 measured nine concurrent one-thread processes valid on the same corrected ANDES family; seven total is the maximum useful budget because this bank has exactly six independent cells.
- ETA and artifact budget: the final rehearsal artifact owns measured seconds and serialized bytes. Use fivefold horizon scaling across one six-worker wave; the measured output is negligible against 46 GiB free disk. Recalibrate only after terminal execution.
- Progress: attempt marker, completed trace count, process count, resource failure, terminal manifest. Scientific endpoints stay unread until all six cells terminate.
- Completion: six valid trace files + sidecars + terminal execution manifest + analysis + sidecars.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r479_h_sensitivity.py execute`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r479_h_sensitivity.py rehearse`
- rehearsal_scope: `same-pre-attempt-path`
- rehearsal_checks: `source_hash,parent_hash,installed_package,installed_case,output_absence`
- capacity_evidence: `memory/rounds/R479/capacity_evidence.json`
- wsl_python_processes: 7
- native_threads_per_process: 1
- host_process_budget: 7
- other_reserved_processes: 0

## 资产保护契约

R478 seal, plan, code, rehearsal, and all historical evidence stay byte-identical. Add only R479 plan/approval/capacity/rehearsal/seal/verdict, one R479 runner + analysis module + tests, and `results/research_loop/r479_h_sensitivity`. Never edit or pool old H-scan artifacts. Do not add the obsolete absolute-`H` interpretation to `paper_constants.py`.

## Cross-references

- `memory/rounds/R478/formal_seal.json`
- `paper/yang_md_decoupling_marl/working/md_parameter_card_20260824.json`
- `tmp/yang_md_decoupling_marl/phase0_card_audit/card_justification.md`
- `src/andes_rl_kundur/probes/andes_common/paper_constants.py`
