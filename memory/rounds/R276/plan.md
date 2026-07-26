---
round: R276
state: completed
opened: '2026-07-26'
closed: '2026-07-26'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R276 plan — sealed four-arm fast/slow factorial gate

**Status**: ACTIVE
**Opened**: 2026-07-26
**Driver**: Test Gate 3 non-additivity with the single missing fast-only arm
before authorizing any learned residual.
**Parent**: CLM-0580, CLM-0585
**Question**: Q-0039
**Reserved claim**: CLM-0590

## TL;DR

R276 reuses 72 immutable real-ANDES trajectories and runs only 24 new ones:

| Arm | BESS slow active power | R275 fast M pulse | Source |
|---|---|---|---|
| `zero` | zero | off | R274 screen |
| `slow` | R274 droop+PI | off | R274 formal |
| `fast` | zero | on | R276 new |
| `combined` | R274 droop+PI | on | R275 formal |

The only new arm executes the exact R275 `common_M_pos` schedule on the
identical storage DAE while requested BESS power is exactly zero.  Three
disjoint WSL shards run eight scenarios each.  No existing arm is rerun and
no learning is trained.

The concrete reused runs are `r274_prospective_active_power_authority` and
`r275_fast_md_authority`; their summaries, provenance files, seals, and every
trace hash are formal R276 inputs.

## Snapshot at plan-time (oracle as of 2026-07-26)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — this is the plan-time research-state snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01)
- Q-0026 [opened R260] Archive Index lazy-extraction signal
- Q-0038 [opened R275] learned zero-sum inertia residual; blocked by Q-0039
- Q-0039 [opened R275] fast/slow non-additivity

## Recently Closed (last 3)

- Q-0037 closed-positive @ R275 by CLM-0585
- Q-0036 closed-positive @ R274 by CLM-0580
- Q-0035 closed-positive @ R273 by CLM-0575

## Methodology

### Frozen plant, bank, controller, and action contract

All four arms use the exact R274 24-case formal bank, storage-enhanced V4
plant, disturbance order, seed 42, solver, 300 steps/60 s, 0.2-s control
interval, physical 60-Hz endpoints, and failure retention.

Reused trace identities are frozen before the first R276 trajectory:

- R274 zero-support traces and R274 slow droop+PI traces come from
  `results/r274_prospective_active_power_authority/provenance.json`;
- R275 combined traces come from
  `results/r275_fast_md_authority/provenance.json`;
- every reused path and SHA-256 is embedded in the R276 formal seal.

The new fast-only arm uses zero requested BESS power on every step and the
unchanged R275 M/D contract:

```text
a_M[i,t] = +0.25 for all four agents and t=0,...,14
a_M[i,t] = 0 for t>=15
a_D[i,t] = 0 for all i,t
```

Thus M is 350 for 3.0 s and 200 afterwards; D is always 100.  Exact R275
amplitude, slew, L1, TV, range, and saturation budgets are reused.

### Registered endpoints

Lower is better for all six endpoint metrics:

- `max_abs_rocof_hz_s`;
- `worst_bus_peak_abs_hz`;
- `normalized_sync_loss_hz2`;
- `fast_inter_area_iae_hz_s` over the first 15 steps;
- `vsg_mean_iae_hz_s`;
- `final_window_common_abs_mean_hz`.

Completion, TDS failure, terminal common error, action amplitude/slew/L1/TV,
BESS requested/commanded/actual power, SOC, charge/discharge energy,
saturation, constraints, and empirical upper tails are mandatory guards.

### Frozen factorial estimand

For each endpoint and paired scenario, define the absolute interaction

`interaction = combined - slow - fast + zero`.

Negative interaction means the combined controller is better than the
additive prediction.  Report its mean and shared-index paired-bootstrap 95%
interval over the 24 scenarios.  Normalize only for the materiality display:

`interaction_percent_of_zero = 100 * mean(interaction) / mean(zero)`.

An endpoint has material beneficial interaction only if this normalized point
is at most -2.0% and the absolute interaction 95% upper bound is below zero.

Also form a deliberately strong per-scenario oracle
`best_single = min(slow, fast)` for each endpoint.  The combined arm clears
best-single value only if its ratio-of-means effect versus this oracle is at
most -2.0% and the paired 95% upper bound is below zero.

Shared-index bootstrap: 10,000 resamples, seed 2026072605.  Failed/incomplete
arms remain in completion denominators and do not enter continuous means.

### Tail and no-harm rules

- No endpoint interaction point may exceed +5% of the zero-arm mean.
- Combined versus best-single point effect may not exceed +5%.
- The empirical upper 10% tail of combined may not exceed best-single by
  more than +5% on any registered endpoint.
- All four arms must complete 24/24 with zero physical/provenance violations.
- The fast-only arm must have exactly zero BESS request/command/actual power,
  SOC exactly 0.5, zero storage energy, and the exact R275 M/D action budget.
- Reused slow/combined storage limits and hashes must remain valid.

## Gate

### NONADDITIVE-POSITIVE

All provenance/completion/action/storage/tail/no-harm guards pass, and at
least one fast endpoint plus at least one slow endpoint clear both the
factorial-interaction and combined-versus-best-single materiality gates.

### NONADDITIVE-PARTIAL

The experiment is valid and at least one registered endpoint clears both
materiality gates, with no registered harm, but the joint fast-plus-slow
criterion does not pass.

### ADDITIVE-ONLY

The experiment is valid but no registered endpoint clears both gates, or a
putative gain is offset by more than +5% harm.  Keep the two layers as a strong
classical benchmark, remove non-additive novelty, and block Q-0038 until a
separate classical learning-gap diagnosis justifies training.

### INVALID

Any reused/new trace hash mismatch, missing arm/scenario, non-finite endpoint,
completion loss, factorial implementation error, M/D action-budget drift,
nonzero fast-only storage power/energy/SOC drift, or source/seal/provenance
failure prevents interpretation.

## Outcomes

- Interaction `<= -2%` of zero, interaction 95% upper bound `< 0`, and
  combined-versus-best-single `<= -2%` with 95% upper bound `< 0` means that
  endpoint clears the non-additive gate.
- At least one fast and one slow endpoint clearing, with every guard passing,
  means `NONADDITIVE-POSITIVE`.
- Only one side or a subset clearing without harm means
  `NONADDITIVE-PARTIAL`.
- No endpoint clearing both tests, or any registered point harm above `+5%`,
  means `ADDITIVE-ONLY`.
- Any trace/source/contract/completion/action/storage/factorial integrity
  failure means `INVALID`, regardless of apparent performance.

## Execution and compute budget

1. Implement tests first for fast-only action/storage behavior, factorial
   bootstrap, best-single contrast, and classification.
2. Run Windows full tests, WSL focused tests, Ruff, dual-metric lint,
   validation, and R276 preflight.
3. Run one disposable 20-step real-ANDES smoke; do not inspect/tune endpoint
   performance.
4. Freeze the R276 formal seal at zero fast-only formal traces.
5. Execute exactly 24 fast-only trajectories with three disjoint WSL shards
   (`bank_index mod 3`), eight trajectories per shard.  Do not exceed three
   concurrent ANDES processes.
6. Analyse once after all shards exit, issue the four-way verdict, update
   CLM-0590/Q-0039, validate, render, and rerun the selector.

Expected new formal wall time is roughly 28–32 minutes from R275's measured
two-shard 42-minute run.  GPU remains unused because ANDES is CPU/DAE-bound.

## 资产保护契约

- Preserve every pre-R276 tracked/untracked user change and every R261-R275
  artifact; do not stage, commit, push, or open a PR.
- Add only R276-specific module, runner, tests, seal, results, logs, claim,
  question update, and verdict.
- Do not alter V4/storage/controller defaults, R274/R275 code or evidence,
  topology, bank, solver, endpoints, learning code, checkpoints, or paper.
- Real ANDES uses `/home/wya/andes_venv/bin/python` in WSL only.

## Planned outputs

- `src/andes_rl_kundur/evaluation/fast_slow_factorial.py`
- `scripts/eval_fast_slow_factorial.py`
- `tests/test_fast_slow_factorial.py`
- `memory/rounds/R276/formal_seal.json`
- `results/r276_fast_slow_factorial/`
- `memory/rounds/R276/verdict.md`
- CLM-0590 and Q-0039 updates

## Cross-references

- CLM-0580 / R274 slow authority
- CLM-0585 / R275 independent fast value
- Q-0039
- `docs/research/2026-07-25_energy_feasible_multitimescale_vsg_execution_plan.md`
