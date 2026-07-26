---
round: R278
state: completed
opened: '2026-07-26'
closed: '2026-07-26'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R278 plan — ICEMS one-dimensional shared MARL pilot

**Status**: COMPLETED — `PILOT-NO-GO`
**Opened**: 2026-07-26
**Driver**: Q-0038 after R277 established `LEARNING-GAP-PRESENT`
**Parents**: CLM-0580, CLM-0585, CLM-0590, CLM-0595

## TL;DR

Implement and test exactly one memoryless parameter-shared TD3 controller whose
only executed learned degree of freedom is a scalar coefficient on
`[+1,+1,-1,-1]`. Run one prospectively gated development seed against the
immutable R274+R275 reference. A failed pilot closes this route without
algorithm, reward, seed, HAWE, recurrent, or baseline rescue.

## Snapshot at plan-time (oracle as of 2026-07-26)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-run render.py if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0038 [opened R275] Does one learned zero-sum inertia allocator outperform the frozen reference on unseen disturbances?

## Recently Closed (last 3)

- Q-0040 closed-positive @ R277, by CLM-0595 — Is there an attainable disturbance-adaptive differential-inertia margin above the sealed classical reference?
- Q-0039 closed-negative @ R276, by CLM-0590 — Is the validated fast/slow benefit non-additive, or only the sum of two classical layers?
- Q-0037 closed-positive @ R275, by CLM-0585 — Does a frozen fast M/D law add independent transient value under the validated slow active-power controller?

## Methodology

### Frozen plant and classical reference

- Reuse `AndesMultiVSGEnvV4Storage`, the R274 BESS contract and the exact R274
  droop+PI gains.
- Reuse the R275 common-inertia action `0.25` for steps 0–14 and zero
  thereafter.
- The immutable measured reference is
  `results/r275_fast_md_authority/formal_traces` with summary
  `results/r275_fast_md_authority/fast_md_authority_summary.json`
  (baseline run: `r275_fast_md_authority`).
- Keep the solver, 0.2-s control interval, 60-s formal horizon, physical
  60-Hz endpoints, storage and completion guards unchanged.
- R274–R277's 24 scenarios are development-only because their outcomes have
  been viewed. They cannot be called unseen formal evidence.

### Frozen learned action

One shared actor maps each agent's local observation to `z_i in [-1,1]`.
The only executed learned coordinate is

`q_raw = 0.25 * 0.5 * (mean(z_0,z_1) - mean(z_2,z_3))`.

Apply a scalar magnitude limit `|q| <= 0.25` and scalar slew limit
`|q_t-q_(t-1)| <= 0.25`. The executed residual is

`q_t * [+1,+1,-1,-1]`.

During steps 0–14 it is added to the frozen R275 common action, so all executed
M actions remain in `[0,0.5]`; from step 15 onward the learned residual and
common pulse are both zero. D action is always zero. Audit the physical
residual fleet mean exactly, not merely the normalized action sum, because V4
has asymmetric positive/negative action decoding.

### Frozen observation

Seven float32 values per agent:

1. local physical frequency deviation divided by `0.1 Hz`;
2. common physical frequency deviation divided by `0.1 Hz`;
3. local-minus-common deviation divided by `0.05 Hz`;
4. local physical RoCoF divided by `0.5 Hz/s`;
5. previous signed local residual divided by `0.25`;
6. local electrical-power change from reset divided by `0.1 pu`;
7. area sign (`+1` for agents 0–1, `-1` for agents 2–3).

Clip only observations to `[-5,5]`; do not clip executed residual elements
independently.

### Frozen training loss and algorithm

Use one deterministic memoryless parameter-shared TD3 actor and one centralized
twin critic. The critic consumes all four observations and the executed scalar
`q/0.25`. This avoids applying SAC entropy claims to a rank-deficient
four-to-one action projection.

For each 15-step training episode, use the identical team reward

`-0.5*sync_hz2/0.05^2 - 0.5*area_diff_hz^2/0.05^2`
`- 0.01*(delta_q/0.25)^2`.

Freeze seed 49, 300 episodes, 4,500 environment steps, hidden sizes 64/64,
actor and critic learning rates `3e-4`, gamma `0.99`, tau `0.005`, batch 256,
warmup 512, replay capacity 100,000, target noise 0.1, noise clip 0.2,
policy delay 2, and exploration noise 0.1. Do not run a hyperparameter or
algorithm sweep.

### Implementation and verification

Add:

- `control/area_inertia_residual.py` for NumPy and Torch projection;
- `env/andes/icems_residual_env.py` for the frozen slow/common/learned stack;
- `agents/shared_area_td3.py` for one shared actor and centralized twin critic;
- `scripts/train_icems_residual.py`;
- one residual-aware full-horizon pilot evaluator;
- unit, reload, zero-residual, projection and WSL smoke tests.

The training script must save the source hashes, controller contract, complete
episode monitor, one shared actor, one centralized critic pair and the exact
command before the first episode.

## Gate

### Pre-training gate

- NumPy/Torch projectors agree.
- Area permutation and area-swap equivariance pass.
- Physical fleet-mean residual is zero at every active step.
- D is zero, action magnitude/slew/window/reset are exact.
- Zero residual reproduces the R274+R275 controller step by step.
- There is exactly one actor parameter object and one actor optimizer step.
- Checkpoint reload is deterministic.
- Windows full tests, WSL targeted tests, `validate.py`, `render.py`,
  `dual_metric_lint.py`, and `round_preflight.py` pass.

### Single-seed pilot gate

Evaluate the frozen seed-49 checkpoint for 60 s on the viewed 24-case R277 bank
against the immutable R275 combined traces. Continue to a later three-seed
round only if all conditions hold:

- mean normalized synchronization loss improves by at least 2%;
- mean first-3-s inter-area IAE improves by at least 2%;
- paired 95% intervals for both improvements have upper bound below zero;
- RoCoF and peak are each no worse than +5%;
- full-horizon IAE and final-window common error are each no worse than +2%;
- 24/24 completion, no TDS failure, exact action contract, no storage
  constraint violation, power/SOC/energy and tail-risk guards pass.

The tail and storage clauses are frozen before any seed-49 pilot endpoint is
evaluated: empirical CVaR90 may worsen by at most +5% for the two co-primary
and two fast safety endpoints, and by at most +2% for the two slow endpoints.
Mean command L1, command total variation, charge energy and discharge energy
may each worsen by at most +5%; commanded/actual power must remain within
0.36 pu, SOC within `[0.20,0.80]`, with zero saturation reasons and zero
constraint violations.

Any other valid result is `PILOT-NO-GO` and closes Q-0038 as
`NO-ADAPTIVE-MARL-VALUE`. Contract/provenance failure is `INVALID`. There is no
second seed, algorithm, reward, amplitude, observation or baseline rescue
inside R278.

## 资产保护契约

- Do not mutate R274–R277 seals, summaries, traces, scripts or verdicts.
- Do not overwrite any historical checkpoint or result directory.
- Keep HAWE and all recurrent checkpoints out of training and headline tables.
- Preserve existing untracked user material outside the explicit R278 paths.
- Use WSL `/home/wya/andes_venv/bin/python` for every real ANDES trajectory.

## Cross-references

- CLM-0580 — validated slow active-power authority.
- CLM-0585 — validated common fast-inertia value.
- CLM-0590 — fast/slow interaction is additive-only.
- CLM-0595 — optimistic differential learning margin exists.
- Q-0038 — the only active ICEMS learning question.
