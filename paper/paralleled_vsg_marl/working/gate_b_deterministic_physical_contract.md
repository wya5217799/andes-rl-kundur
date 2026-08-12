# Gate B prospective deterministic physical contract

## Status and authority

- Working title remains exactly **Decoupling-Oriented Coordination of
  Paralleled VSGs With Multi-Agent Reinforcement Learning**.
- This document is a prospective experiment contract in the `scratch` lane.
  It authorizes no ANDES execution and no training. Every value below is
  frozen here before any trajectory; a separately reserved evidence round
  seals this contract before rehearsal and execution.
- R375/CLM-1020 remains authoritative for the stopped power-reference
  formulation. This contract does not reuse its gains, controller, guard
  results, or endpoint diagnostics as evidence; it reuses only the registered
  endpoint definitions and the audit discipline listed in the reuse boundary.
- Gate A (`working/feasibility_native_four_vsg_contract.md`) is qualified by
  the focused action tests. This contract is the Gate B plan required by
  `ROUTE.md#current-gate`.

## Decision

Execute one physical deterministic comparison on the four VSG-owned
energy-constrained active-power-reference ports using the selected
feasibility-native seam: every controller arm outputs one scalar normalized
action per VSG inside `[-1, 1]`, and the same per-node map
(`FeasibilityNativeVSGActionMap.map_action`) converts it into that VSG's
current feasible power interval. The outer VSG-energy-port projection must be
identity on every step of every trajectory; any outer repair is a terminal
invalidity.

The comparison arms are:

1. `zero_feedback` — four zero normalized actions (no-control reference);
2. `local_feasibility_native` — four independent normalized PI laws using
   only each VSG's own frequency;
3. `distributed_feasibility_native` (four frozen candidate gain pairs) — the
   same normalized PI laws plus a dynamic-average common channel and a
   zero-sum Laplacian sync channel driven by frozen one-hop neighbour
   messages on the four-node ring.

This is a genuinely different formulation from R375: the controller output is
a fraction of current feasible headroom, so feasibility is structural instead
of repaired by the external ramp/energy projection. It is also different from
the Model-First line: four VSG node actors on the object-gated VSG-owned
ports, not edge actors or ESD1 devices.

## Frozen physical object and action seam

- Environment: `AndesVSGEnergyPortEnv` over `AndesMultiVSGEnvV4`
  (modified-Kundur, `ZERO_G4_INERTIA=True`, `DISABLE_TOGGLER=1`), four VSG
  indices at buses `[12, 16, 14, 15]`, legacy M/D action path pinned to zero.
- Energy contract: `r272_frozen_bess_contract()` — 100 MVA system base,
  four devices of 36 MW / 28 MWh, SOC `[0.20, 0.80]`, initial `0.50`,
  full-scale ramp 1.0 s, capability and energy rules unchanged.
- Action map: `src/andes_rl_kundur/control/feasibility_native_vsg_action.py`,
  zero-anchored path only for Gate B. Execution contract:
  `actor_count=4`, `per_actor_action_dimension=1`,
  `executed_node_action_dimension=4`,
  `action_coordinates="per_vsg_normalized_feasible_power"`,
  `central_action_aggregation=False`,
  `external_projection_role="identity_guard_only"`,
  `training_authorized=False`.
- Control update: one action per 0.2 s environment step (`dt_seconds=0.2`),
  50 steps per trajectory (10 s horizon), matching R374/R375 timing.
- Nominal frequency: 60 Hz. Power units: system per-unit on 100 MVA.

## Frozen deterministic control laws

### Common structure

For VSG `i` with measured frequency `f_i(t)` (Hz), define frequency error

```text
e_i(t) = f_nom - f_i(t).
```

Every deterministic law produces a raw request `u_i(t)` and then applies the
frozen internal saturation

```text
a_i(t) = clip(u_i(t), -0.70, 0.70).
```

The internal `0.70` bound guarantees that a paired probe of magnitude `0.25`
(see Banks) cannot drive `|a_i|` past `1.0` after superposition, keeping the
outer projection structurally identity. Bound contact with the `0.70` limit
is a registered control-stress endpoint, not a failure.

### `zero_feedback`

```text
u_i(t) = 0        for all i, t.
```

### `local_feasibility_native`

```text
I_i(t) = I_i(t-1) + ki_n * e_i(t-1) * dt,      I_i(0) = 0,
u_i(t) = kp_n * e_i(t) + I_i(t).
```

Integrator anti-windup: when `clip(u_i, -0.70, 0.70) != u_i` after the
previous update, the integrator increment is set to zero for that step
(clamp-based freezing; no external projection is ever consulted).

Frozen gains:

```text
kp_n = 4.0 /Hz
ki_n = 0.8 /(Hz*s)
```

Information set: `f_i(t)` and the local integrator only. No neighbour value,
no fleet statistic.

### `distributed_feasibility_native_ks<ks>_kc<kc>`

Same local terms plus two neighbour channels on the frozen ring adjacency

```text
0: [1, 3], 1: [0, 2], 2: [1, 3], 3: [2, 0].
```

Dynamic-average common estimate `c_i(t)` (Hz):

```text
c_i(0) = e_i(0),
c_i(t) = c_i(t-1) + e_i(t) - e_i(t-1)
         - kc_n * dt * sum_{j in N_i} (c_i(t-1) - c_j(t-1)).
```

Common channel:

```text
I_c,i(t) = I_c,i(t-1) + ki_n * c_i(t-1) * dt,      I_c,i(0) = 0,
u_c,i(t) = kp_n * c_i(t) + I_c,i(t).
```

Sync channel (zero-sum by construction):

```text
u_d,i(t) = -ks_n * sum_{j in N_i} (f_i(t) - f_j(t)).
```

Total raw request:

```text
u_i(t) = u_c,i(t) + u_d,i(t).
```

Same anti-windup rule as the local law, applied to `u_i`.

Frozen candidate grid (four candidates, matching the R375 tuning budget):

```text
ks_n in {0.5, 1.0} /Hz
kc_n in {0.5, 1.0} /s
```

Information set: local `f_i(t)`, the local estimator/integrator states, and
frozen one-hop neighbour messages `(f_j, c_j)` on the ring. No two-hop
message, no centralized state, no fleet-average statistic beyond what the
ring consensus can compute.

## Frozen banks

All banks are untouched by R374/R375: every `(device, magnitude, sign)`
combination below differs from the R374/R375 conditions
(`PQ_0 +0.35/-0.75`, `PQ_1 +0.75`, `PQ_Bus14 -0.55/+0.85`,
`PQ_Bus15 -0.85`).

### Development bank (selection phase)

| Kind | Condition | `delta_u` |
|---|---|---|
| Probe condition | `dev_probe_pq15_minus_0p40` | `{"PQ_Bus15": -0.40}` |
| Disturbance 1 | `dev_disturbance_pq0_plus_0p55` | `{"PQ_0": +0.55}` |
| Disturbance 2 | `dev_disturbance_bus14_plus_0p50` | `{"PQ_Bus14": +0.50}` |

Arms: `zero_feedback`, `local_feasibility_native`, and the four
`distributed_feasibility_native_ks<ks>_kc<kc>` candidates.
Per arm: 8 paired probe records (4 modes x 2 signs) + 2 disturbance records.
Total: `6 arms x 10 = 60` records.

### Held-out bank (selection-blinded evaluation phase)

| Kind | Condition | `delta_u` |
|---|---|---|
| Probe condition | `eval_probe_pq1_plus_0p35` | `{"PQ_1": +0.35}` |
| Disturbance 1 | `eval_disturbance_bus14_minus_0p45` | `{"PQ_Bus14": -0.45}` |
| Disturbance 2 | `eval_disturbance_pq0_minus_0p65` | `{"PQ_0": -0.65}` |

Arms: `zero_feedback`, `local_feasibility_native`, and the development-
selected distributed candidate. Total: `3 arms x 10 = 30` records.

### Paired probe injection

The probe is injected in the normalized-action domain, in the registered
arithmetic mode coordinates:

```text
common      [1, 1, 1, 1]
inter_area  [1, 1, -1, -1]
local_area_1 [1, -1, 0, 0]
local_area_2 [0, 0, 1, -1]
```

with frozen magnitude `probe_component_action = 0.25`:

```text
a_probed(t) = a(t) + sign * 0.25 * mode_vector.
```

Because the internal saturation is `0.70`, `|a_probed| <= 0.95` on every
step, so every probed action passes through the same map with identity
guaranteed. Positive and negative probes are paired per mode and sign for the
signed-response estimate. The probe acts on the executed action coordinates,
not on the raw power request; this removes the R375 ramp-projection failure
mode by construction while keeping the paired-response estimator unchanged.

### Seeds and identity

- One seed: `seed = 42` for all trajectories, matching R374/R375.
- Per-trajectory identity payload: `n_agents=4`,
  `vsg_idx=["VSG_1","VSG_2","VSG_3","VSG_4"]`, `vsg_buses=[12,16,14,15]`,
  exactly as registered by CLM-0975/CLM-1005.
- The unit of analysis is one independently initialized trajectory on the
  modified-Kundur topology. There is no learned policy and no statistical
  population beyond the registered finite banks.

## Frozen endpoints

### Co-primary decoupling endpoints (per arm)

- Probe bank: paired `+/-` probe difference projected onto the four
  arithmetic frequency coordinates, integrated over the 50-step window;
  report the 4x4 response-energy matrix, diagonal energy, off-diagonal
  energy, and off-diagonal-to-diagonal ratio (definitions of R375,
  `src/andes_rl_kundur/evaluation/deterministic_decoupling.py`).
- Disturbance bank: mean differential-frequency energy (Hz^2*s) and mean
  differential settling time (band 0.01 Hz) over the two conditions.

### Secondary and no-harm endpoints (per arm)

- Common-frequency IAE (Hz*s), worst-unit peak (Hz), max RoCoF (Hz/s) per
  disturbance condition.
- Control stress (reported, never hidden): mean internal action magnitude,
  mean absolute headroom fraction used
  `|commanded - zero_anchor| / (upper - zero_anchor)` for `command >= 0` and
  `|commanded - zero_anchor| / (zero_anchor - lower)` for `command < 0`,
  bound-contact step count (`|a_i| >= 0.70 - 1e-12`), action L1
  (system-pu x s), and action total variation (system-pu).
- Projection leakage: maximum common and differential distortion between
  requested and commanded power (must be zero by guard, reported for audit),
  command L1 device-seconds, command total variation.

## Frozen guards (per trajectory, hard)

Every trajectory must satisfy, step by step:

1. 50 completed steps with no TDS failure and no execution exception.
2. `requested == commanded` at `atol=1e-12` and empty `saturation_reasons`
   on every step (external-projection identity guard).
3. SOC stays inside `[0.20, 0.80]` (with `atol=1e-9`).
4. Differential request is zero-sum (`zero_sum_atol=1e-12`).
5. Channel reconstruction: `requested == common + differential`
   (`atol=1e-9`).
6. Legacy M/D action telemetry is all zero (`atol=1e-9`).
7. Finite frequency and power arrays; correct uniform 0.2 s timing.
8. Action rank guard: across the eight paired probe records of each arm, the
   four executed action coordinates span the full common-plus-three-
   differential rank on the registered physical states (rank 4 within
   `1e-9` tolerance); a rank collapse is a terminal stop.

An infeasible baseline, a nonfinite action, or an out-of-range probe is
fail-closed: the record is marked failed and the arm's guard fails; nothing
is silently clipped.

## Frozen selection and classification rule

### Development selection

- Baseline: `local_feasibility_native`; it must itself pass all guards.
- Eligibility for each distributed candidate (ratios relative to the local
  arm, same threshold family as R375):
  - off-diagonal response energy ratio <= 0.98,
  - normalized cross-response ratio <= 0.98,
  - mean differential-frequency energy ratio <= 0.98,
  - common-frequency IAE ratio <= 1.05.
- Rank: `rank_score = offdiag_ratio * normalized_cross_ratio *
  differential_energy_ratio`, ascending; ties broken by `ks_n`, then `kc_n`.
- Outcomes: `DEVELOPMENT-CANDIDATE-SELECTED` or
  `STOP-DEVELOPMENT-NO-CANDIDATE`.

### Held-out classification (after selection only)

- Baselines: `zero_feedback` and `local_feasibility_native` (both must pass
  all guards).
- Decoupling checks (thresholds as in R375):
  - cross-coordinate: probe off-diagonal and normalized-cross ratios <= 0.95
    against both baselines;
  - differential motion and settling: mean differential-energy ratios
    <= 0.95 against both baselines, every single disturbance condition
    ratio <= 1.10, and settling time strictly below the local-arm value by
    at least one `dt`;
  - common-mode no-harm: common IAE <= 1.05 x best baseline, worst peak and
    max RoCoF <= 1.10 x best baseline;
  - physical/execution guards: all guards pass for the selected arm and both
    baselines.
- Classification (guard first, then endpoint precedence):
  `STOP-UNSAFE-CONTROL`, `STOP-NO-CROSS-DECOUPLING`,
  `STOP-NO-DIFFERENTIAL-BENEFIT`, `STOP-COMMON-MODE-HARM`, or
  `DETERMINISTIC-DECOUPLING-PASS`.
- `training_authorized` is `false` in every branch. On
  `DETERMINISTIC-DECOUPLING-PASS`, the next gate is
  `non_learning_time_varying_headroom` (Gate C of the feasibility-native
  contract); no other progression is permitted.

## Terminal stop rules

Stop this formulation before any learning if any of the following holds:

1. any deterministic baseline command is infeasible or requires external
   repair (identity guard fails on any step of any trajectory);
2. the common-plus-three-differential action rank collapses on the
   registered physical states;
3. no distributed candidate clears the development eligibility rule;
4. the selected candidate fails any held-out guard or endpoint threshold
   (no retry, no gain change, no bank resize, no threshold adjustment);
5. the probe superposition ever drives `|a_probed| > 1.0` (map fail-closed).

A `STOP-*` outcome closes Gate B without authorizing Gate C, tuning, random
arms, or MARL.

## Frozen capacity and execution discipline

- Whole-host Python process budget: 1; `wsl_python_processes = 1`;
  `native_threads_per_process = 1`; `other_reserved_processes = 0`.
- Serial execution only: rehearsal, then a create-only seal, then execution
  with the expected seal SHA-256. No retry, no parallel worker pool, no
  output override, no training.
- Capacity evidence must be collected before rehearsal and anchored on the
  R373 authority execution (30 records x 40 steps, serial, single thread),
  with the formal projection covering 60 + 30 records and a 1.5x wall-time
  safety factor and artifact-size projection per the R374 runner pattern.
- Results register into `results/MANIFEST.md` with `.sha256` sidecars and
  the `LOCAL-ONLY` archive class; no private second copy is claimed.
- The execution round is a manuscript evidence round: it is reserved through
  `reserve_round.py --strict-no-active --line paralleled_vsg_marl
  --write-plan-stub`, prefight-checked, and gated by the experiment-
  efficiency gate before any ANDES trajectory.

## Reuse boundary

Directly reusable implementation:

- `active_power.py` feasible-interval and projection machinery (unchanged);
- `vsg_energy_port.py` and `vsg_energy_port_env.py` object-gated port and
  achieved-power settlement (unchanged);
- `feasibility_native_vsg_action.py` map and identity guard (unchanged);
- R375 endpoint definitions and selection/classification structure as
  registered in `deterministic_decoupling.py` (adapted, not copied into a
  second truth);
- sealed-bank, provenance, failure-retention, and runner plumbing patterns.

Adaptable design donors only:

- R375 distributed controller structure (dynamic-average common channel +
  zero-sum Laplacian sync) re-parameterized in the normalized action space;
- R375 development/hold-out separation and threshold family as a tuning
  budget precedent.

Never transfer:

- R375 gains in power units, its guard-failed trajectories, or its
  saturation diagnostics as evidence;
- Model-First edge actors, ESD1 acting objects, residual labels, outcomes,
  or claims;
- old checkpoints, rewards, training curves, or title evidence.

## Immediate decision

This contract is the prospective Gate B plan required by the route. No
physical run or training is authorized by this document. The next steps are
(a) a separately reserved evidence round that seals this contract byte-for-
byte, (b) experiment-efficiency-gate and capacity evidence, (c) rehearsal,
and only then conditional execution.
