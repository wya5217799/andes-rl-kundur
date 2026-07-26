---
round: R275
state: completed
opened: '2026-07-26'
closed: '2026-07-26'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R275 plan — sealed fast-inertia value gate above R274 droop+PI

**Status**: ACTIVE
**Opened**: 2026-07-26
**Driver**: Resolve Q-0037 with the cheapest valid experiment before spending
GPU time on residual learning.
**Parent**: CLM-0555, CLM-0565, CLM-0580
**Question**: Q-0037
**Reserved claim**: CLM-0585

## TL;DR

Reuse the immutable 24 R274 `droop_pi` traces as the matched baseline and run
only 24 new candidate trajectories.  The candidate adds the single
development-selected `common_M_pos` schedule from R270 to the unchanged R274
slow droop+PI/storage controller: all four normalized M actions are +0.25 for
the first 15 steps (3.0 s), then zero; D is always zero.  No amplitude,
duration, shape, gain, bank, endpoint, or threshold search is allowed.

The candidate is sealed before its first trajectory.  Two disjoint WSL shards
may execute the 24 independent ANDES trajectories concurrently; every trace
is written once to a unique path and analysis waits for both shards.  This
halves the new trajectory count by reusing R274 and improves wall-clock time
without changing the statistical unit or simulator contract.

## Snapshot at plan-time (oracle as of 2026-07-26)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — render.py may refresh STATE.md, but this block records the
plan-time research state. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify
  1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried
  (lazy-extraction loop signal)?
- Q-0037 [opened R274] Does a frozen fast M/D law add independent transient
  value under the validated slow active-power controller?

## Recently Closed (last 3)

- Q-0036 closed-positive @ R274, by CLM-0580 — prospective active-power
  authority re-test
- Q-0035 closed-positive @ R273, by CLM-0575 — storage-DAE feasibility
  diagnosis
- Q-0034 closed-partial @ R272, by CLM-0570 — active-power authority proxy

## Falsifiable objective

Determine whether one bounded fast inertia schedule provides independent
physical transient value above the already validated R274 slow active-power
controller, without weakening common-frequency restoration, numerical
completion, storage safety, or action/energy guards.

This is an actuator/value gate, not a learning experiment.  A non-positive
result closes the current fast M/D branch and prevents architecture or reward
search from consuming more compute.

## Methodology

The measured baseline is the completed
`r274_prospective_active_power_authority` run.  Its formal bank, droop+PI
traces, seal, summary, and provenance are immutable inputs to R275.  R275 adds
one sealed candidate arm and uses paired scenario-level inference; it does not
rerun, replace, or reinterpret the baseline arm.

## Frozen arms and physical contract

Both arms use:

- the exact R274 24-case formal bank, SHA-256
  `9d028e8a0e990fbea6585c674b471dba4d41ea27c1e0b7ecb5d8389092b31f44`;
- the exact R274 storage plant, four 36-MVA/28-MWh ESD1 devices, placement,
  SOC, power, ramp, efficiency, converter projection, and 0.02-s lag;
- equal-sharing physical-60-Hz droop+PI with Kp=2.0
  system-pu/Hz/device and Ki=0.2 system-pu/(Hz s)/device;
- V4 M0/D0=200/100, seed 42, 300 steps, 0.2 s/step, 60-s horizon,
  final 50-step/10-s window, and identical solver/failure retention;
- physical 60-Hz endpoint reporting, separate from frozen V4 50-Hz control
  semantics.

The baseline is the immutable R274 `droop_pi` trace for each scenario.  Its
path and SHA-256 are copied from and checked against R274 provenance before
sealing R275.  No baseline is rerun.

The candidate executes the identical slow controller plus exactly:

```text
for agent i in {0,1,2,3}:
    a_M[i,t] = +0.25  for t = 0,...,14
    a_M[i,t] =  0.00  for t >= 15
    a_D[i,t] =  0.00  for all t
```

This is the R270 development-only `common_M_pos` winner (selected in 5/8
oracle scenarios).  It is not chosen from R274/R275 candidate endpoint
performance.  In V4 it maps to delta-M=+150 and M=350 during the pulse, then
returns to M=200; D remains 100.  The environment interpolates each target
over the existing five ANDES substeps.

### Frozen fast-action budgets

- maximum normalized amplitude: `|a_M| <= 0.25`, `a_D == 0`;
- maximum boundary-aware normalized slew: 0.25 per 0.2-s control step;
- maximum physical target change: 150 M-units per control step
  (750 M-units/s during the existing substep interpolation);
- pulse duration: exactly 15 steps / 3.0 s;
- normalized L1: exactly 0.75 agent-s per completed trace under the repository
  physical summarizer;
- in-trace normalized total variation: exactly 0.25; boundary-aware total
  variation including the initial zero-to-pulse edge: exactly 0.50;
- action saturation fraction: zero;
- physical target range: M in [200, 350], D exactly 100.

Any deviation is a contract failure, not a tunable result.

## Registered endpoints

For every complete matched pair, report:

### Fast-layer endpoints

1. maximum sampled physical RoCoF, `max_abs_rocof_hz_s`;
2. worst-bus physical peak deviation, `worst_bus_peak_abs_hz`;
3. full-horizon normalized synchronization loss,
   `normalized_sync_loss_hz2`;
4. first-15-step physical inter-area IAE,
   `fast_inter_area_iae_hz_s`, where the mode is
   `mean(df[agents 0,1]) - mean(df[agents 2,3])`.

An endpoint clears materiality only when the candidate/baseline
ratio-of-means effect is at most -2.0% and the paired-bootstrap 95% interval
upper bound is below 0%.

### Slow-restoration and physical guards

- full-horizon `vsg_mean_iae_hz_s`;
- final-10-s `final_window_common_abs_mean_hz`;
- terminal common-frequency absolute error;
- completion/TDS-failure pairing;
- BESS requested/commanded/actual power, L1, TV, saturation reasons;
- min/max/terminal SOC and charge/discharge energy;
- every storage constraint violation;
- M/D L1, TV, amplitude, slew, M/D ranges, and saturation.

The two slow-restoration point effects must each be no worse than +2%; their
paired 95% upper bounds must be below +5%.  BESS command L1, TV, charge
energy, and discharge energy point effects must each be no worse than +5%.
All SOC/power/constraint limits and the exact M/D budgets must pass.

For the four fast endpoints and the two slow-restoration endpoints, also
report the empirical upper-tail/CVaR-style summaries in both arms.  A
candidate upper-tail increase above +5% on any registered endpoint blocks a
positive verdict.

## Paired inference

- statistical unit: one of the 24 sealed scenarios;
- contrast: `slow_droop_pi_plus_common_M_pos - slow_droop_pi_fixed_MD`;
- shared-index paired bootstrap: 10,000 resamples, seed 2026072604;
- incomplete/failed scenarios remain in completion denominators and cannot
  enter continuous endpoint means;
- zero missing, replaced, redrawn, or retried scenarios;
- all raw traces, seals, source hashes, package versions, and commands are
  retained.

## Gate

### FAST-LAYER-POSITIVE

All must hold:

- at least two of four fast endpoints clear materiality;
- at least one clearing endpoint is common-frequency
  (`RoCoF` or worst-bus peak);
- at least one clearing endpoint is differential
  (synchronization loss or fast inter-area IAE);
- every other fast endpoint point effect is no worse than +5%;
- both slow-restoration guards pass;
- all endpoint upper-tail increases are no worse than +5%;
- candidate completion is 24/24 and no worse than baseline;
- every M/D action budget and every storage power/SOC/energy/constraint guard
  passes;
- bank, baseline, plan, contract, code, package, solver, seal, and trace hashes
  verify.

### FAST-LAYER-PARTIAL

The experiment and physical/action/safety contracts are valid, at least one
fast endpoint clears materiality, and no fast endpoint worsens by more than
5%, but the positive common-plus-differential joint gate, slow-restoration
guard, or tail guard does not fully pass.

### NO-INDEPENDENT-FAST-VALUE

The experiment is valid but no fast endpoint clears materiality, or a
registered fast/slow endpoint worsens by more than 5%.  Close Q-0037
non-positively and remove the current fast-layer learning branch; do not
rescue it with another pulse, amplitude, model, reward, or seed.

### INVALID

Any bank/baseline/source/seal/trace mismatch, non-finite endpoint, missing
scenario, candidate completion loss, M/D budget violation, storage-contract
violation, or execution outside the registered real-ANDES contract prevents
performance interpretation.  Only the integrity defect may be repaired; no
law or threshold changes are allowed after the seal.

## Execution and compute budget

1. Implement the frozen pulse, trace summarizer/classifier, immutable seal,
   resumable sharded runner, and focused tests.
2. Run Windows tests, WSL focused tests, dual-metric lint, validation, and
   `round_preflight.py R275 --json`.
3. Run one real-ANDES smoke trajectory in a disposable path; smoke output is
   excluded from the formal bank and cannot tune the law.
4. Freeze the formal seal while candidate trace count is zero.
5. Execute exactly 24 formal candidate trajectories.  Use two disjoint WSL
   shards (`index mod 2`) on this 16-core/32-thread, 24-GiB WSL host.  Do not
   exceed three concurrent ANDES processes.
6. Analyse once after both shards finish; issue one of the four verdicts,
   update CLM-0585 and Q-0037, close R275, validate, render, and rerun the
   selector.

New real-ANDES budget: 1 smoke + 24 formal candidate trajectories.  Formal
baseline cost is zero because the 24 R274 traces are reused by immutable hash.
GPU training remains forbidden in R275.  Only a positive or scientifically
useful partial gate may motivate a separately pre-registered learning round,
where the 8-GiB GPU budget can be split across at most two small workers.

## Asset protection

- Preserve every pre-R275 tracked/untracked user change and every R261-R274
  artifact.  Do not stage, commit, push, or open a PR.
- Add only R275-specific code, tests, seals, logs, and result namespaces.
- Do not alter V4 defaults, storage/active-power controller constants,
  topology, disturbance bank, solver, historical traces, checkpoints, paper,
  or manuscript artifacts.
- Real ANDES uses `/home/wya/andes_venv/bin/python` in WSL only.
- No RL/GNN training, topology claim, stability certificate, EMT,
  cross-simulator, HIL, deployment, or paper claim is in scope.

## Planned outputs

- `src/andes_rl_kundur/evaluation/fast_md_authority.py`
- `scripts/eval_fast_md_authority.py`
- `tests/test_fast_md_authority.py`
- `memory/rounds/R275/formal_seal.json`
- `results/r275_fast_md_authority/`
- `memory/rounds/R275/verdict.md`
- CLM-0585 and Q-0037 updates

## Cross-references

- CLM-0555 / R270: common positive inertia was the dominant eligible
  development schedule but the library oracle missed its full material gate.
- CLM-0565 / R271: M/D affects fast transients but cannot independently
  restore common frequency.
- CLM-0580 / R274: slow droop+PI/storage authority is valid on the frozen
  24-case bank.
- `memory/rounds/R272/actuator_contract.json`
- `results/r274_prospective_active_power_authority/provenance.json`
