---
round: R404
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-15'
closed: '2026-08-15'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R404 plan — R403 diagnostic-sentinel correction successor

**Opened**: 2026-08-15
**Driver**: R403 was SCRATCH-INVALID before the first policy update because an
intentional no-update NaN sentinel was misclassified as learner divergence;
the owner authorized one science-identical correction successor.
**Parent**: CLM-1165 (same-family successor decision); CLM-1170 (R403
instrumentation invalidity); R403 development contract sha256
`dad9b0e5775982c67c478acb178ccfc1befc05ea081c3aed5aea95309b5bae02`

## TL;DR

Workload: `evidence`. Change only diagnostic representation and pre-attempt
coverage. Reuse the exact R403 repaired learner, disclosed profile bank, seed,
1200-step budget, baselines, weights, metrics, and thresholds under a new seal;
then execute one create-only attempt.

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

### Science-identical contract

- Import the complete R403 successor development contract byte-identically;
  assert its canonical hash equals the parent value above.
- Arms, actor/critic architecture, observations, messages, actions, fixed
  common weight 1.0, action-effort weight 1.0, scratch seed 4030, four disclosed
  development profiles, 1200 steps, R402 message seed-403 comparator,
  deterministic comparator, and every SCRATCH gate remain unchanged.
- No evaluation profile, unseen bank, tuning, threshold change, algorithm
  replacement, extra seed, retry, or best-checkpoint selection.

### Only permitted correction

- `FixedWeightCDMATD3.update()` returns an explicit numeric
  `policy_updated` flag. On critic-only updates `actor_loss_mean` is a finite
  placeholder consumed only when `policy_updated == 0`; policy-update steps
  retain the measured finite actor loss.
- Full diagnostics keep both fields so downstream analysis never treats the
  placeholder as a measured actor loss.
- Regression feedback command:
  `python -m pytest tests/test_cd_matd3_successor.py tests/test_run_r404_cd_matd3_successor.py -q -p no:cacheprovider`.

### Deeper rehearsal

- Before any physical attempt, fill the real replay seam through its registered
  batch size, execute one critic-only and one actor-update call, require explicit
  update-state fields and strict JSON serialization with `allow_nan=False`.
- Then exercise the same WSL authority/source/parent/runtime/case/output-absence
  path plus one real physical step per repaired arm and checkpoint round-trip.

## Gate

Use the unchanged R403 development classifier. No missing/nonfinite diagnostic,
TDS failure, or absent checkpoint is admissible. Both repaired arms must have
slew-bound hit fraction <0.05, mean absolute action below the matched R402
message policy, common cost <=1.5 times the deterministic reference, and
differential cost <= the matched R402 message policy.

### Outcomes

- `SCRATCH-PASS`: both arms pass every unchanged guard; close R404 and only
  then reserve a separately frozen fresh-bank successor canary.
- `SCRATCH-FAIL`: either arm misses any unchanged scientific guard; stop this
  successor without tuning, retry, or unseen execution.
- `SCRATCH-INVALID`: any required artifact/metric/diagnostic is missing,
  nonfinite, or physically invalid; retain the attempt and stop the route.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r404_cd_matd3_successor.py run`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r404_cd_matd3_successor.py rehearse`
- rehearsal_scope: same-pre-attempt-path for active authority, exact parent contract hash, source closure, installed runtime/case and output absence; explicit critic-only plus actor-update diagnostic serialization; one physical step per arm
- rehearsal_checks: source_hash, parent_hash, active_plan, active_line, installed_package, installed_case, output_absence
- capacity_evidence: `memory/rounds/R402/capacity_evidence_v2.json`
- host_process_budget: 9
- wsl_python_processes: 2
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- 保留 dirty worktree；不 reset/clean/stage/commit。
- R398-R403 plans, seals, attempts, results, feeds, claims and verdicts read-only;
  do not delete or overwrite the invalid R403 tmp attempt.
- Do not modify paper-cited environment, base environment, training entry, or
  ranker; no cross-line write.
- New R404 rehearsal/seal and create-only output root
  `tmp/r404_cd_matd3_successor/`; failed attempt is retained and never retried.

## Cross-references

- CLM-1165: owner-authorized repaired same-family successor boundary.
- CLM-1170: R403 sentinel misclassification and correction-only authority.
- `memory/rounds/R403/development_seal.json`: exact parent scientific contract.
- `paper/yang_md_decoupling_marl/reports/R403.md`: invalid-attempt feed and
  publication stay-out.
