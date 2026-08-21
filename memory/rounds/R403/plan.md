---
round: R403
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-15'
closed: '2026-08-15'
supersedes_rounds: []
superseded_by_round: null
abort_reason: diagnostic sentinel misclassified before first policy update; no algorithm
  efficacy tested
superseded_note: null
---
# R403 plan — CD-MATD3 repaired-successor development gate

**Opened**: 2026-08-15
**Driver**: R402 exposed a dead common-mode weight, missing action effort,
and unauditable convergence diagnostics; the owner explicitly authorized a
same-family repair and continued experiment through a small-fast gate.
**Parent**: CLM-1155 and CLM-1160 (R402); successor decision
`paper/yang_md_decoupling_marl/working/route_successor_design_r403.md`

## TL;DR

Workload: `evidence`, because the final gate includes new WSL ANDES training
on disclosed development profiles. Preserve the frozen R402 learner as a
historical object, add a same-family fixed-weight successor, prove the two
identified defects red/green offline, then run exactly one 1200-step paired
development canary. This round does not open a fresh unseen bank and cannot
support the paper title.

## Snapshot at plan-time (oracle as of 2026-08-15)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?
- Q-0110 closed-positive @ R396, by CLM-1125 — Does the projected-passive dual-droop VSM (PPVSM1) two-unit diagnostic cell pass clean native initialization, a 0.2-second zero-input stationarity gate, and a spectrum guard with no positive-real mode and no neutral degeneracy beyond the network common-angle reference, thereby opening only a separately registered signed P/Q authority gate?
- Q-0109 closed-positive @ R392, by CLM-1105 — Which installed REGF2 feedback path or parameter carries the two reproducible positive-real local modes of the exact R391 four-REGF2 equilibrium, under prospectively frozen one-variable-at-a-time parameter-perturbation EIG arms?

## Methodology

### Frozen repair

- Preserve `CDMATD3` and all R402 artifacts unchanged as the failed frozen
  bundle.
- Add `FixedWeightCDMATD3`: same four actors, observation/action contract,
  twin joint critic and memoryless execution; actor objective is
  `-(Q_d + 1.0 Q_c)` and no adaptive dual update can change that weight.
- Add normalized action effort to the differential training cost:
  `c_d' = c_d + mean_i ||a_i||^2`; common cost is unchanged.
- Store complete per-episode differential/common/effort/return/action
  summaries and complete critic/actor-loss histories for every run.
- No family swap, hyperparameter sweep, new message pattern, or threshold
  relaxation.

### Tight feedback loop

- Offline regression command:
  `python -m pytest tests/test_cd_matd3_successor.py -q -p no:cacheprovider`.
- It must fail against the R402 implementation on both exact defects, then
  pass after the repair while `tests/test_cd_matd3_learner.py` remains green.

### Disclosed-profile development canary

- Arms: repaired `cd_matd3_message` and repaired
  `cd_matd3_no_message`; one fixed scratch seed `4030` each.
- Bank: only the four already-disclosed R402 development profiles and their
  registered scenario order; no R399 profile and no R402 evaluation profile.
- Budget: exactly 1200 executed interaction steps per arm, sequential runs,
  followed by deterministic evaluation of the repaired policies, the frozen
  R402 `cd_matd3_message` seed-403 checkpoint under
  `results/research_loop/r402_cd_matd3_canary/`, and the deterministic
  reference on the same disclosed profiles.
- Outputs: create-only under `tmp/r403_cd_matd3_successor/`; development-only,
  not a formal result root and not manuscript evidence.

## Gate

`SCRATCH-PASS` only if both repaired arms have finite complete diagnostics,
slew-bound hit fraction < 0.05, mean action magnitude below the matched frozen
R402 message policy, common cost no greater than 1.5 times the deterministic
reference, and differential cost no worse than the matched frozen R402
message policy on the disclosed profiles. Otherwise `SCRATCH-FAIL` and stop
without tuning, retry, or unseen execution. A pass authorizes only closing
R403 and prospectively reserving a separate successor-canary round; it is not
scientific evidence.

### Outcomes

- `SCRATCH-PASS`: both repaired arms pass every registered guard; close R403
  and only then reserve a separate fresh-bank evidence canary.
- `SCRATCH-FAIL`: either repaired arm misses any registered guard; stop this
  learner route without tuning, retry, threshold repair, or unseen execution.
- `SCRATCH-INVALID`: a required run/metric/diagnostic is absent, nonfinite, or
  physically invalid; retain the failed attempt and stop R403 for diagnosis.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r403_cd_matd3_successor.py run`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r403_cd_matd3_successor.py rehearse`
- rehearsal_scope: same-pre-attempt-path for authority/source/runtime/case/parent/output-absence checks, then one real environment step per repaired arm; no training artifact
- rehearsal_checks: source_hash, parent_hash, active_plan, active_line, installed_package, installed_case, output_absence
- capacity_evidence: `memory/rounds/R402/capacity_evidence_v2.json`
- host_process_budget: 9
- wsl_python_processes: 2
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- 保留 dirty worktree；不 reset/clean/stage/commit。
- R398-R402 plans, seals, results, checkpoints, feeds, claims and verdicts
  read-only; no historical artifact overwrite or reclassification.
- Do not modify paper-cited V4 environment, base environment, training entry,
  or paper-grade ranker.
- Reusable repair code/tests and one stable R403 adapter may be added; physical
  development output is create-only under the declared tmp root.
- The R402 evaluation bank is excluded from all repair selection and scratch
  acceptance.

## Cross-references

- CLM-1155: R402 sealed canary failure and learner-route stop.
- CLM-1160: bounded route disposition after the failed canary.
- `paper/yang_md_decoupling_marl/working/canary_failure_forensics_r402.md`:
  read-only causal analysis input.
- `paper/yang_md_decoupling_marl/working/route_successor_design_r403.md`:
  owner-authorized same-family successor decision.
