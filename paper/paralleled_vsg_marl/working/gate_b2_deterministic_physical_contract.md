# Gate B-2 prospective deterministic physical contract (successor)

## Status and authority

- Working title remains exactly **Decoupling-Oriented Coordination of
  Paralleled VSGs With Multi-Agent Reinforcement Learning**.
- This is a prospective experiment contract in the `scratch` lane. It
  authorizes no ANDES execution and no training. Every value is frozen here
  before any trajectory; a separately reserved evidence round seals this
  contract before rehearsal and execution.
- R376/CLM-1025 stopped the feasibility-native deterministic law family
  (`STOP-DEVELOPMENT-NO-CANDIDATE`): the four frozen distributed gain pairs
  with Laplacian sync + dynamic-average consensus amplified probe
  cross-response (1.12-1.19x local) while mildly reducing disturbance
  differential energy (best 0.91x local at `ks1_kc0p5`). This successor
  contract is the registered next eligible action: a genuinely different
  deterministic law, not a gain sweep of the stopped family.
- R375/CLM-1020 and R376/CLM-1025 remain authoritative for their stopped
  formulations. This contract reuses only the registered endpoint
  definitions, guards, and execution discipline as design donors.

## Decision

Freeze a **high-pass filtered mutual-damping** distributed law whose neighbour
messages act only on the oscillatory component of neighbour frequency
differences, and freeze the **disturbance-driven differential-oscillation
energy and settling time** as the Gate B-2 primary decoupling endpoints, with
probe cross-response promoted to a no-harm guard.

Justification, from the R376 development bank (CLM-1025):

1. ROUTE.md defines `decoupling` narrowly as suppression of inter-VSG dynamic
   coupling and differential oscillation caused by heterogeneous inertia,
   droop, and disturbance distribution. Electromagnetic P/Q channel
   decoupling is explicitly outside the first paper.
2. R376 showed the Laplacian sync term reduces differential oscillation
   energy (0.91x local) but amplifies probe cross-response (1.13-1.19x
   local). The probe is a sustained step in the action domain; a high-pass
   filter on the sync input attenuates exactly that sustained component while
   retaining oscillatory differential damping. This is a mechanism change,
   not a threshold change.
3. The primary endpoints therefore measure the mechanism the title claims
   (differential oscillation suppression); the probe cross-response remains a
   registered no-harm guard so that a damping channel cannot trade one
   coupling for another.

This is structurally different from R376 in three ways: the sync channel is
frequency-selective (high-pass), the neighbour message enters only the
differential channel (the common channel keeps the R376 dynamic-average
estimator), and the decoupling primary endpoints are the differential
oscillation family. All arms still use the same feasibility-native map and the
same identity-only outer projection.

## Frozen physical object and action seam

- Environment: `AndesVSGEnergyPortEnv` over `AndesMultiVSGEnvV4`
  (modified-Kundur, `ZERO_G4_INERTIA=True`, `DISABLE_TOGGLER=1`), four VSG
  indices at buses `[12, 16, 14, 15]`, legacy M/D action path pinned to zero.
- Energy contract: `r272_frozen_bess_contract()` (100 MVA system base, four
  devices of 36 MW / 28 MWh, SOC `[0.20, 0.80]`, initial `0.50`, full-scale
  ramp 1.0 s).
- Action map: `FeasibilityNativeVSGActionMap.map_action` (zero-anchored
  path), unchanged. Execution contract: four actors, one scalar per VSG,
  `external_projection_role="identity_guard_only"`,
  `training_authorized=False`.
- Control update: 0.2 s, 50 steps per trajectory, seed 42, nominal 60 Hz,
  system per-unit on 100 MVA.

## Frozen deterministic control laws

### Common structure

For VSG `i`, frequency error `e_i(t) = 60 - f_i(t)`. Every law produces a raw
request `u_i(t)` saturated at the frozen internal bound:

```text
a_i(t) = clip(u_i(t), -0.70, 0.70).
```

Bound contact with `0.70` is a registered stress endpoint. Probe magnitude
`0.25` keeps `|a_probed| <= 0.95`, so the outer projection stays identity.

### `zero_feedback`

```text
u_i(t) = 0.
```

### `local_feasibility_native` (unchanged from R376)

```text
I_i(t) = I_i(t-1) + ki_n * e_i(t-1) * dt,      I_i(0) = 0,
u_i(t) = kp_n * e_i(t) + I_i(t),               kp_n = 4.0 /Hz, ki_n = 0.8 /(Hz*s),
```

with clamp-based integrator anti-windup. Local information only.

### `distributed_hp_damping_ks<ks>_kc<kc>_alpha<a>` (successor law)

Common channel (same dynamic-average estimator as R376):

```text
c_i(0) = e_i(0),
c_i(t) = c_i(t-1) + e_i(t) - e_i(t-1)
         - kc_n * dt * sum_{j in N_i} (c_i(t-1) - c_j(t-1)),
I_c,i(t) = I_c,i(t-1) + ki_n * c_i(t-1) * dt,   I_c,i(0) = 0,
u_c,i(t) = kp_n * c_i(t) + I_c,i(t).
```

High-pass filtered mutual-damping channel (neighbour messages enter only
here, and only through the high-pass state):

```text
s_i(0) = 0,
s_i(t) = alpha * ( s_i(t-1) + m_i(t) - m_i(t-1) ),
m_i(t) = sum_{j in N_i} ( f_i(t) - f_j(t) ),
u_d,i(t) = -ks_n * s_i(t).
```

This is the R376 Laplacian sync term with a first-order high-pass filter
(pole at `alpha`) applied to the neighbour frequency-difference sum. The
sustained probe-induced component is attenuated by `1 - alpha` per step;
oscillatory differential motion passes through. The channel remains zero-sum
in the sense that `sum_i u_d,i(t) = 0` for the undirected ring.

Total raw request:

```text
u_i(t) = u_c,i(t) + u_d,i(t).
```

Same anti-windup as the local law.

Frozen candidate grid (four candidates, same tuning budget size as R376):

```text
ks_n in {0.5, 1.0} /Hz
kc_n in {0.5, 1.0} /s
alpha = 0.60        (frozen, all candidates)
```

Information set: local `f_i(t)`, local estimator/integrator states, and
frozen one-hop neighbour messages `(f_j, c_j)` on the ring.

## Frozen banks

All conditions are untouched by R374/R375/R376.

### Development bank (60 records)

| Kind | Condition | `delta_u` |
|---|---|---|
| Probe condition | `dev2_probe_pq0_minus_0p45` | `{"PQ_0": -0.45}` |
| Disturbance 1 | `dev2_disturbance_pq1_plus_0p60` | `{"PQ_1": +0.60}` |
| Disturbance 2 | `dev2_disturbance_bus15_plus_0p50` | `{"PQ_Bus15": +0.50}` |

Arms: `zero_feedback`, `local_feasibility_native`, four
`distributed_hp_damping_ks<ks>_kc<kc>_alpha0p6`. Total 60 records.

### Held-out bank (30 records)

| Kind | Condition | `delta_u` |
|---|---|---|
| Probe condition | `eval2_probe_pq0_plus_0p40` | `{"PQ_0": +0.40}` |
| Disturbance 1 | `eval2_disturbance_bus14_minus_0p55` | `{"PQ_Bus14": -0.55}` |
| Disturbance 2 | `eval2_disturbance_pq1_minus_0p70` | `{"PQ_1": -0.70}` |

Arms: `zero_feedback`, `local_feasibility_native`, development-selected
distributed candidate. Total 30 records.

### Paired probe injection

Same as R376: action-domain injection in the four arithmetic modes at
magnitude 0.25, positive/negative paired per mode.

## Frozen endpoints

### Primary decoupling endpoints (per arm, disturbance bank)

1. Mean differential-frequency energy over the two conditions (Hz^2*s).
2. Mean differential settling time (band 0.01 Hz).

These are the registered ROUTE decoupling-family endpoints.

### Secondary / no-harm endpoints

- Common-frequency IAE, worst-unit peak, max RoCoF per condition.
- Probe cross-response: off-diagonal response energy and
  off-diagonal-to-diagonal ratio (reported; held to a no-harm ceiling, not a
  primary threshold).
- Control stress: mean |a|, headroom fraction, bound-contact steps, action
  L1, action total variation.
- Projection leakage (must be zero by guard).

## Frozen guards (per trajectory, hard)

Identical to R376: 50 completed steps, no TDS failure, external-projection
identity at `atol=1e-12` with empty saturation reasons, SOC bounds, zero-sum
differential action, action channel reconstruction, zero legacy M/D
telemetry, finite arrays, uniform timing, and full common-plus-three-
differential action rank across the eight paired probes. Fail-closed on any
malformed action or infeasible baseline.

## Frozen selection and classification rule

### Development selection

- Baseline: `local_feasibility_native`; it must pass all guards.
- Eligibility for each distributed candidate (primary ratios relative to
  the local arm):
  - mean differential-frequency energy ratio <= 0.98,
  - mean differential settling time <= local settling - one dt,
  - common IAE ratio <= 1.05,
  - probe off-diagonal energy ratio <= 1.10 (no-harm ceiling),
  - probe normalized cross ratio <= 1.10 (no-harm ceiling).
- Rank: `rank_score = diff_energy_ratio * settling_ratio`, ascending; ties
  broken by `ks_n`, then `kc_n`.
- Outcomes: `DEVELOPMENT-CANDIDATE-SELECTED` or
  `STOP-DEVELOPMENT-NO-CANDIDATE`.

### Held-out classification (after selection only)

- Baselines: `zero_feedback` and `local_feasibility_native` (both must pass
  all guards).
- Primary checks: mean differential-energy ratio <= 0.95 against both
  baselines; every single-condition differential-energy ratio <= 1.10;
  settling time strictly below the local-arm value by at least one dt.
- No-harm checks: common IAE <= 1.05 x best baseline, worst peak and max
  RoCoF <= 1.10 x best baseline, probe off-diagonal energy and normalized
  cross ratio <= 1.10 against both baselines.
- Guards: all arms pass all hard guards.
- Classification (guard first): `STOP-UNSAFE-CONTROL`,
  `STOP-NO-DIFFERENTIAL-BENEFIT`, `STOP-COMMON-MODE-HARM`,
  `STOP-NO-HARM-EXCEEDED` (new: primary passes but no-harm ceiling fails),
  `STOP-DEVELOPMENT-NO-CANDIDATE`, or `DETERMINISTIC-DECOUPLING-PASS`.
- `training_authorized=false` in every branch. On pass, the next gate is the
  registered non-learning time-varying headroom oracle (Gate C of the
  feasibility-native contract).

## Terminal stop rules

1. Any deterministic baseline command infeasible or externally repaired
   (identity guard fails) -> STOP-UNSAFE-CONTROL.
2. Action rank collapse on the registered states -> STOP.
3. No candidate clears development eligibility -> STOP-DEVELOPMENT-NO-
   CANDIDATE (no held-out bank, no training).
4. Selected candidate fails any held-out guard, primary endpoint, or no-harm
   ceiling -> STOP-* (no retry, no gain change, no bank resize).
5. Probe superposition ever drives `|a_probed| > 1.0` -> fail-closed STOP.

A STOP-* outcome closes Gate B-2 without authorizing Gate C, tuning, random
arms, or MARL.

## Frozen capacity and execution discipline

Identical to R376: whole-host Python process budget 1, `wsl_python_processes
= 1`, `native_threads_per_process = 1`, `other_reserved_processes = 0`;
serial rehearsal -> create-only seal -> execution with expected seal SHA-256;
no retry, no parallel workers, no training; capacity evidence anchored on the
R374 60-record / 447.5 s serial anchor with 1.5x safety factor; results
register into `results/MANIFEST.md` with `.sha256` sidecars and the
`LOCAL-ONLY` archive class. The execution round is a manuscript evidence
round reserved through `reserve_round.py --strict-no-active --line
paralleled_vsg_marl --write-plan-stub`, prefight-checked, and gated by the
experiment-efficiency gate before any ANDES trajectory.

## Reuse boundary

Directly reusable: `active_power.py`, `vsg_energy_port.py`,
`vsg_energy_port_env.py`, `feasibility_native_vsg_action.py` (unchanged);
R376 guard/endpoint/selection structure adapted as registered;
sealed-bank/provenance/runner plumbing.

Adaptable design donors: R376 dynamic-average common estimator; R376
disturbance banks as condition-shape precedents.

Never transfer: R376 gain pairs or Laplacian sync law as evidence; R375
guard-failed trajectories; Model-First objects/results; old checkpoints,
rewards, training curves, or title evidence.

## Immediate decision

This contract is the prospective Gate B-2 plan required by the route after
R376. No physical run or training is authorized by this document. The next
steps are (a) a separately reserved evidence round that seals this contract
byte-for-byte, (b) experiment-efficiency-gate and capacity evidence, (c)
rehearsal, and only then conditional execution.
