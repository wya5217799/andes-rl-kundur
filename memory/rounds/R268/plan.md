---
round: R268
state: completed
opened: '2026-07-25'
closed: '2026-07-25'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R268 plan — corrected bounded-droop residual feasibility pilot

**Status**: ACTIVE
**Opened**: 2026-07-25
**Driver**: Q-0030 correctness-first pilot after the hand-designed gate family closed
**Parent**: CLM-0495, CLM-0515, CLM-0535
**Prospective claim slot**: CLM-0540

## TL;DR

Add one reusable normalized-action composition:

`u_exec = clip(u_droop(k=10) + 0.10 * u_residual, -1, 1)`.

The same function must run inside training and deterministic evaluation.
Train one memoryless TD3 seed under the existing V4 normalized-action reward
for 75 episodes, then compare it with droop on eight fixed, reference-feasible
development disturbances.  If the pilot misses either physical direction or
an action/failure guard, stop and close this exact residual contract.  Only a
passing pilot may trigger seeds 50/51 and a new sealed bank.

## Snapshot at plan-time (oracle as of 2026-07-25)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0030 [opened R267] Can a corrected bounded residual around droop show a reproducible mechanism benefit?

## Recently Closed (last 3)

- Q-0029 closed-negative @ R267, by CLM-0535 — Can temporal regularisation make the state selector deployable?
- Q-0028 closed-negative @ R265, by CLM-0525 — Will prospectively unseen load cases reproduce the candidate effect?
- Q-0027 closed-partial @ R264, by CLM-0520 — Can a state-dependent droop residual policy advance both dual metrics?

## Methodology

### Correctness contract

- Actor action means residual command, not absolute V4 command.
- Physical prior is the existing R85 law:
  `u_droop=[0, clip(10*abs(obs[i][1]), 0, 1)]`.
- Residual scale is fixed at `beta=0.10` before training.
- Executed action is
  `clip(u_droop + beta*u_residual, -1, 1)`.
- The 0.10 scale is a conservative feasibility cap, not tuned from a test
  bank.  It limits the learned correction to 10% of normalized action travel
  while preserving the droop prior as the dominant controller.
- A single ANDES-independent composer is called by both:
  1. a training environment adapter that stores raw residual actions in replay
     while the base V4 environment receives executed actions; and
  2. a deterministic evaluation action function.
- Base V4 reward, dynamics, physical clipping, failure semantics, frequency
  provenance, and checkpoint networks remain unchanged.
- Training sidecar must record controller mode, `k`, `beta`, algorithm,
  seed, reward config, source hashes, and command.
- Tests must cover exact composition, residual/executed bounds, reset and
  current-observation semantics, info telemetry, default absolute-training
  compatibility, checkpoint reload, and deterministic evaluator parity.

### Reference-feasible envelope

- Training uses native V4 random disturbances only:
  absolute magnitude in `[0.5, 2.0]`.
- Pilot evaluation uses exactly eight fixed development cases:
  each of `PQ_0`, `PQ_1`, `PQ_Bus14`, `PQ_Bus15` at `-1.5` and `+1.5`.
- This envelope is fixed from the native training contract before the pilot.
  It excludes R267's common-infeasible positive Bus14 cases at `+2.7000` and
  `+2.9946`.
- No failed row may be dropped.  Common droop/residual failure and
  residual-specific failure are reported separately.
- The pilot bank is development evidence, not a sealed confirmatory bank.

### Pilot training

- Algorithm: memoryless TD3; no recurrent state and no legacy checkpoint.
- Seed: 49, the first canonical R41/R48 TD3 seed, chosen by ordering rather
  than residual performance.
- Episodes: 75; hidden layers `64,64,64,64`; normalized action penalty;
  tau `0.005`; default TD3 learning rate, replay, batch, target smoothing,
  exploration noise and delayed update.
- V4 paper-faithful base config; communication failure probability 0.1.
- Disable legacy automatic `final_eval` because it interprets actor output as
  absolute action; use only the residual-aware evaluator.
- Output: `results/r268_residual_td3_s49`.

### Pilot evaluation

Compare exactly:

1. `droop_k10`;
2. `residual_td3_s49_b0p10`.

Use V4 paper-faithful defaults, environment seed 42, 150 steps, real ANDES in
WSL, cyclic controller-order rotation, immutable per-scenario trace JSON, and
the existing physical endpoint summarizer.

Co-primary lower-is-better means:

1. `vsg_mean_iae_hz_s`;
2. `normalized_sync_loss_hz2`.

Guards:

- completion/failure and paired completion;
- worst-bus peak and max sampled RoCoF mean and worst;
- 0.05-Hz settling success;
- action L1, total variation and saturation;
- residual action magnitude and executed clipping telemetry.

No interval-qualified or population claim is permitted at `n=8`.

## Pre-registered outcomes and decision gate

Classify INVALID on contract/source/checkpoint drift, runner error, missing
trace/endpoint, non-finite value, or failed verification.

For a valid pilot:

### GO

- all 16 traces complete;
- residual-vs-droop point effect `<0` on both co-primary means;
- residual failure not higher and settling success not lower;
- worst-bus peak and max RoCoF mean and bank worst not worse by `>5%`;
- mean and worst action-TV not worse by `>25%`;
- action saturation not higher;
- deterministic checkpoint reload reproduces actions exactly.

### NO-GO

Every other valid result.  Stop without a second residual scale, reward,
algorithm, seed, or training horizon.  Close the exact memoryless
TD3/k10/beta0.10 contract and diagnose the blocker.

### Conditional multi-seed stage

Only after GO:

- train identical seeds 50 and 51;
- generate a new 20-scenario no-anchor bank constrained prospectively to the
  same absolute magnitude envelope `[0.5,2.0]`, seed `20260726`;
- seal bank, controller contracts, checkpoints, endpoints and source hashes
  before trajectories;
- compare droop and all three residual seeds on the same bank;
- require at least two of three seeds to improve both co-primary means, with
  no seed-specific failure and the same safety/action guards.

The conditional stage will be fully materialised in an addendum and preflighted
before any such trajectory.  Failure of the pilot means it is never opened.

## 资产保护契约

- Do not change `base_env.py`, V4 dynamics/config defaults, TD3/SAC update
  equations, recurrent agents, historical checkpoints, R267/R265 artifacts,
  paper metrics, manuscript files, or figures.
- Add one composition module, one thin training adapter/CLI mode, one pilot
  evaluator, tests, and machine-readable sidecars.
- Default `scripts/train.py` absolute-action mode must remain bit-compatible in
  constructed agents/environment behavior.
- Use `apply_patch`; preserve unrelated dirty-worktree changes.
- Run no ANDES or training before preflight and focused/full tests pass.
- Write no paper section, submission prose, or paper figure.

## Cross-references

- CLM-0495: recurrent target alignment defect; historical recurrent models are
  legacy evidence.
- CLM-0515: programme decision to pivot toward bounded residual control around
  droop.
- CLM-0525: raw selector retained small physical gains but failed action-TV.
- CLM-0530: alpha switching caused the raw gate's variation.
- CLM-0535: the only permitted slew reduced raw variation but failed the
  physical/action contract; hand-designed family closed.

## Verification before launch

- `python memory/tools/round_preflight.py R268 --json`;
- focused residual-composition and train-CLI tests;
- `python -m pytest tests -q`;
- WSL residual-wrapper smoke with real ANDES;
- `python memory/tools/dual_metric_lint.py`;
- `python memory/tools/validate.py`;
- `python memory/tools/render.py`.

## Planned outputs

- reusable bounded residual composer and training adapter;
- deterministic residual-aware pilot evaluator;
- `results/r268_residual_td3_s49/`;
- `results/r268_residual_pilot_eval/`;
- CLM-0540, R268 verdict, Q-0030 update;
- no manuscript artifacts.
