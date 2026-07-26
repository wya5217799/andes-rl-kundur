---
round: R277
state: completed
opened: '2026-07-26'
closed: '2026-07-26'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R277 plan — sealed zero-sum inertia learning-margin upper bound

**Status**: ACTIVE
**Opened**: 2026-07-26
**Driver**: Diagnose one physically explicit differential learning gap before
spending compute on parallel MARL training.
**Parent**: CLM-0555, CLM-0585, CLM-0590
**Question**: Q-0040
**Reserved claim**: CLM-0595

## TL;DR

R277 gives the proposed learned zero-sum inertia allocator an intentionally
optimistic upper bound. It reuses the 24 immutable R275 combined traces and
runs six prospectively frozen signed zero-sum inertia schedules on the same
24-case bank. An outcome-seeing development oracle may choose the best guarded
schedule or fall back to the baseline for every scenario.

The strict new-trajectory budget is `24 × 6 = 144`. The measured host has an
AMD Ryzen 9 8940HX (16 cores/32 threads), 31.22 GiB host RAM, a 23-GiB WSL
limit with 18 GiB currently available, and no competing ANDES process. Eight
disjoint WSL shards therefore run 18 trajectories each. No neural model is
trained and no candidate endpoint may be inspected until all 144 traces
exist.

## Snapshot at plan-time (oracle as of 2026-07-26)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0038 [opened R275] Does one learned zero-sum inertia allocator outperform the frozen reference on unseen disturbances?
- Q-0040 [opened R276] Is there an attainable disturbance-adaptive differential-inertia margin above the sealed classical reference?

## Recently Closed (last 3)

- Q-0039 closed-negative @ R276, by CLM-0590 — Is the validated fast/slow benefit non-additive, or only the sum of two classical layers?
- Q-0037 closed-positive @ R275, by CLM-0585 — Does a frozen fast M/D law add independent transient value under the validated slow active-power controller?
- Q-0036 closed-positive @ R274, by CLM-0580 — Can active-power authority be tested validly on a prospectively completion-screened bank?

## Methodology

### Frozen baseline, plant, and bank

The baseline is the exact R275 slow droop+PI/storage controller plus frozen
3-s common positive-inertia pulse. Its 24 traces, R274 formal bank, R275
formal seal/summary/provenance, plant, BESS contract, solver, 300-step/60-s
horizon, seed 42, 0.2-s control interval, and 60-Hz physical endpoints are
reused by immutable hash.

### Complete zero-sum spatial basis

During steps 0 through 14, the unchanged common inertia action is
`c=[0.25,0.25,0.25,0.25]`. Add one signed differential action
`0.25*b`, where `b` is drawn from:

1. `h1_pos`: `[+1,+1,-1,-1]`;
2. `h1_neg`: `[-1,-1,+1,+1]`;
3. `h2_pos`: `[+1,-1,+1,-1]`;
4. `h2_neg`: `[-1,+1,-1,+1]`;
5. `h3_pos`: `[+1,-1,-1,+1]`;
6. `h3_neg`: `[-1,+1,+1,-1]`.

The three unsigned Hadamard directions are mutually orthogonal, each sums to
zero, and span the full three-dimensional zero-sum subspace for four agents.
The executed first-window normalized M action is therefore two entries at
0.5 and two at 0.0; D action is zero. Physical M is two devices at 500 and
two at 200, versus baseline 350 on all four, so fleet-mean inertia stays
exactly 350. After step 14 all M/D actions return to zero (M/D=200/100).

The 0.25 differential amplitude and 15-step window are inherited from R270's
development-only attainable-oracle basis and R275's validated common pulse;
they are not tuned in R277. No second amplitude, duration, damping direction,
combination, continuous optimizer, or adaptive law is permitted.

### Outcome-seeing oracle

For each scenario, start with the immutable R275 baseline. A new schedule is
eligible only if:

- it completes 300/300 steps with no TDS or constraint failure;
- both differential endpoints are individually no worse than baseline:
  normalized synchronization loss and first-3-s inter-area IAE;
- max RoCoF and worst-bus peak are no worse than +5%;
- full-horizon VSG-mean IAE and final-window common error are no worse than
  +2%;
- BESS power, SOC, energy, ramp/capability, saturation, and the exact M/D
  action contract pass.

Among eligible schedules, choose the minimum
`0.5*(sync/base_sync + fast_interarea/base_fast_interarea)`. Ties prefer the
baseline, then the fixed candidate order above. The selector sees the entire
trajectory and is deliberately stronger than a deployable policy; it is only
an attainable-margin upper bound.

### Registered inference and guards

Use one shared-index paired bootstrap over the 24 scenarios (10,000
resamples, seed 2026072606). Lower is better. The two primary endpoints are:

- `normalized_sync_loss_hz2`;
- `fast_inter_area_iae_hz_s`.

Report max RoCoF, worst-bus peak, full-horizon VSG-mean IAE, final-window
common error, completion, terminal common error, empirical upper 10% tails,
M/D action amplitude/slew/L1/TV/ranges, BESS request/command/actual power,
SOC, charge/discharge energy, saturation and constraints.

Primary materiality requires ratio-of-means effect `<= -2%` and paired 95%
upper bound `< 0`. Common/restoration point effects must be `<= +2%` with 95%
upper bound `< +5%`. Every registered upper-tail effect must be `<= +5%`.
Selected storage command/TV/charge/discharge-energy means must not worsen by
more than +5%; BESS command/actual power must stay within 0.36 system pu and
SOC within `[0.20,0.80]`.

## Gate

### LEARNING-GAP-PRESENT

Both primary differential endpoints clear materiality and uncertainty, the
oracle selects a non-baseline action in at least one scenario, and every
common/restoration, tail, action, storage, completion, and provenance guard
passes. This freezes one learning target but does not validate MARL.

### LEARNING-GAP-PARTIAL

The experiment is valid and exactly one primary endpoint clears, with no
registered harm and every integrity/action/storage guard passing. Do not train
until the failed differential mechanism is resolved prospectively.

### NO-RL-NEEDED

The valid optimistic oracle clears neither primary endpoint, or an apparent
gain is offset by a registered common/restoration/tail harm. Close or abandon
Q-0038 on this fixed topology without neural training.

### INVALID

Any source/bank/baseline/seal hash drift, missing or duplicate task, trace
overwrite, incomplete analysis input, non-finite endpoint, exact zero-sum
action failure, storage-contract failure, bootstrap/oracle bug, or provenance
failure prevents interpretation. Repair only integrity and resume the same
sealed contract.

## Outcomes

- Exactly 144 unique candidate traces, plus 24 immutable baselines.
- A paired physical endpoint table and 95% intervals for oracle versus
  baseline.
- Per-scenario selection and ineligibility-reason accounting.
- Exact action, storage, tail, completion, and provenance audits.
- One of the four registered classifications, with no threshold or library
  change after endpoint visibility.

## Execution and compute budget

1. Implement focused tests for the six-direction contract, zero-sum/fleet-mean
   invariants, deterministic oracle selection, bootstrap gate, and WSL smoke.
2. Run focused and full Windows tests, focused WSL tests, Ruff, dual-metric
   lint, validation, and R277 preflight.
3. Run one disposable 20-step real-ANDES smoke. Inspect only execution,
   exact action/storage contracts, and completion.
4. Recheck host/WSL CPU and memory. Eight shards are allowed only if at least
   12 GiB WSL memory is available and no other ANDES batch is active;
   otherwise seal four shards.
5. Freeze the formal seal at zero R277 candidate traces.
6. Run eight disjoint resumable shards, 18 tasks each, with stderr logs kept
   separately. Do not inspect endpoint summaries during generation.
7. Analyse once after every shard exits; then close CLM-0595/Q-0040/R277,
   validate, render, and rerun the selector.

Based on R276's measured 28-minute three-shard wall for 24 trajectories, 144
trajectories at eight shards should take roughly 60–70 minutes. GPU remains
unused because real ANDES is CPU/DAE-bound.

## 资产保护契约

- Preserve all pre-R277 tracked/untracked user edits and R261-R276 artifacts;
  do not stage, commit, push, clean, or open a PR.
- Add only the R277 module, runner, tests, smoke/seal/results/logs, verdict,
  CLM-0595, and Q-0040 update.
- Do not alter V4/storage/controller defaults, R274/R275/R276 code or
  evidence, the bank, solver, endpoints, learning code/checkpoints, topology,
  actuator model, or manuscript.
- Real ANDES uses `/home/wya/andes_venv/bin/python` in WSL only.

## Planned outputs

- `src/andes_rl_kundur/evaluation/learning_gap_oracle.py`
- `scripts/eval_learning_gap_oracle.py`
- `tests/test_learning_gap_oracle.py`
- `memory/rounds/R277/formal_seal.json`
- `results/r277_learning_gap_oracle/`
- `memory/rounds/R277/verdict.md`
- CLM-0595 and Q-0040 updates

## Cross-references

- CLM-0555 / R270 M/D-only optimistic oracle
- CLM-0585 / R275 validated common fast-inertia value
- CLM-0590 / R276 additive-only factorial result
- Q-0038 and Q-0040
- `docs/research/2026-07-25_energy_feasible_multitimescale_vsg_execution_plan.md`
