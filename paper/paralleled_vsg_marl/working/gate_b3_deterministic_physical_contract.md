# Gate B-3 prospective deterministic physical contract (successor)

## Status and authority

- Working title remains exactly **Decoupling-Oriented Coordination of
  Paralleled VSGs With Multi-Agent Reinforcement Learning**.
- This is a prospective experiment contract in the `scratch` lane. It
  authorizes no ANDES execution and no training. Every value is frozen here
  before any trajectory; a separately reserved evidence round seals this
  contract before rehearsal and execution.
- R378/CLM-1035 stopped the high-pass damping law family at alpha 0.60
  (`STOP-NO-DIFFERENTIAL-BENEFIT`: held-out differential-energy ratio 0.962x
  local vs 0.95 threshold; probe cross 0.79x local). This successor contract
  is the registered next eligible action: a genuinely different deterministic
  law justified by spectral diagnosis, not a gain sweep of the stopped family.
- R376/CLM-1025, R377/CLM-1030, R378/CLM-1035 remain authoritative for their
  stopped formulations. This contract reuses only registered endpoint
  definitions, guards, and execution discipline as design donors.

## Decision

Freeze the **low-corner high-pass filtered mutual-damping** law: the same
first-order high-pass structure as R378 but with the corner frequency placed
at least five times below the measured dominant differential-oscillation
mode, so the damping channel passes the oscillation it is designed to damp
while still attenuating the sustained action-domain probe.

### Spectral diagnosis (scratch, from immutable R378 held-out records)

- All three differential modes (inter-area, local area 1, local area 2)
  oscillate at a dominant frequency of approximately 0.4 Hz on the
  disturbance bank (Hanning-windowed FFT over the 50-step, 10 s window;
  peak, f50, and f80 all at 0.4 Hz, f95 at 0.5 Hz).
- The R378 high-pass pole `alpha = 0.60` with dt = 0.2 s gives a corner
  frequency `f_c = -ln(alpha) / (2*pi*dt) ~= 0.41 Hz`, essentially on top of
  the dominant mode. At the corner the filter halves the passed power, so
  the damping channel attenuates the very differential oscillation it should
  reduce. This explains the R378 outcome: probe cross-response improved
  (0.79x local) because the DC probe component is attenuated, while mean
  differential-frequency energy improved only to 0.962x local because the
  filter simultaneously cut the 0.4 Hz oscillation energy.
- The successor therefore moves the corner well below the mode:
  `alpha = 0.90` gives `f_c ~= 0.084 Hz`, about 4.8x below 0.4 Hz, passing
  essentially all of the 0.4 Hz modal energy (gain ~1 well above corner)
  while still decaying the sustained probe component.

This is a mechanism change justified by measured plant spectra, not a
threshold change: the damping channel is frequency-selective in the band
where the measured oscillation actually lives.

## Frozen physical object and action seam

- Environment: `AndesVSGEnergyPortEnv` over `AndesMultiVSGEnvV4`
  (modified-Kundur, `ZERO_G4_INERTIA=True`, `DISABLE_TOGGLER=1`), four VSG
  indices at buses `[12, 16, 14, 15]`, legacy M/D action path pinned to zero.
- Energy contract: `r272_frozen_bess_contract()` (100 MVA system base, four
  devices of 36 MW / 28 MWh, SOC `[0.20, 0.80]`, initial `0.50`).
- Action map: `FeasibilityNativeVSGActionMap.map_action` (zero-anchored
  path), unchanged; outer projection identity-only.
- Control update: 0.2 s, 50 steps per trajectory, seed 42, nominal 60 Hz.

## Frozen deterministic control laws

### Common structure

`e_i(t) = 60 - f_i(t)`; every law produces `a_i(t) = clip(u_i(t), -0.70,
0.70)`. Probe magnitude 0.25 keeps `|a_probed| <= 0.95`.

### `zero_feedback`

`u_i(t) = 0`.

### `local_feasibility_native` (unchanged)

`I_i(t) = I_i(t-1) + ki_n * e_i(t-1) * dt`, `u_i(t) = kp_n * e_i(t) +
I_i(t)`, `kp_n = 4.0 /Hz`, `ki_n = 0.8 /(Hz*s)`, clamp anti-windup.

### `distributed_lowhp_damping_ks<ks>_kc<kc>_alpha0p9` (successor law)

Common channel identical to R378 (dynamic-average estimator, `kc_n`).
Differential channel: first-order high-pass on the Laplacian frequency
difference sum with the frozen pole `alpha = 0.90`:

```text
s_i(0) = 0,
s_i(t) = alpha * ( s_i(t-1) + m_i(t) - m_i(t-1) ),
m_i(t) = sum_{j in N_i} ( f_i(t) - f_j(t) ),
u_d,i(t) = -ks_n * s_i(t).
```

Frozen candidate grid (four candidates, same budget size):

```text
ks_n in {0.5, 1.0} /Hz
kc_n in {0.5, 1.0} /s
alpha = 0.90        (frozen, all candidates; corner ~0.084 Hz)
```

Information set: local `f_i(t)`, local estimator/integrator states, frozen
one-hop neighbour messages `(f_j, c_j)` on the ring.

## Frozen banks

All conditions untouched by R374-R378.

### Development bank (60 records)

| Kind | Condition | `delta_u` |
|---|---|---|
| Probe condition | `dev3_probe_bus15_minus_0p45` | `{"PQ_Bus15": -0.45}` |
| Disturbance 1 | `dev3_disturbance_pq1_plus_0p65` | `{"PQ_1": +0.65}` |
| Disturbance 2 | `dev3_disturbance_bus14_minus_0p55` | `{"PQ_Bus14": -0.55}` |

Arms: `zero_feedback`, `local_feasibility_native`, four
`distributed_lowhp_damping_ks<ks>_kc<kc>_alpha0p9`. Total 60 records.

### Held-out bank (30 records)

| Kind | Condition | `delta_u` |
|---|---|---|
| Probe condition | `eval3_probe_pq0_minus_0p40` | `{"PQ_0": -0.40}` |
| Disturbance 1 | `eval3_disturbance_pq0_plus_0p60` | `{"PQ_0": +0.60}` |
| Disturbance 2 | `eval3_disturbance_bus15_plus_0p55` | `{"PQ_Bus15": +0.55}` |

Arms: `zero_feedback`, `local_feasibility_native`, development-selected
candidate. Total 30 records.

### Paired probe injection

Same action-domain injection, four arithmetic modes, magnitude 0.25.

## Frozen endpoints

### Primary (disturbance bank, per arm)

1. Mean differential-frequency energy (Hz^2*s).
2. Mean differential settling time (band 0.01 Hz).

### Secondary / no-harm

- Common IAE, worst peak, max RoCoF per condition.
- Probe off-diagonal response energy and normalized cross ratio (no-harm
  ceiling <= 1.10 vs baselines).
- Control stress: mean |a|, headroom fraction, bound contact, action L1,
  action total variation.
- Projection leakage (must be zero by guard).

## Frozen guards (per trajectory, hard)

Identical to R376-R378: 50 completed steps, no TDS failure, identity at
`atol=1e-12` with empty saturation reasons, SOC bounds, zero-sum differential
action, action channel reconstruction, zero legacy M/D telemetry, finite
arrays, uniform timing, full common-plus-three-differential action rank.
Fail-closed on malformed action or infeasible baseline.

## Frozen selection and classification rule

### Development selection (vs local arm)

- differential-energy ratio <= 0.98,
- settling no worse than local (corrected rule from R378),
- common IAE ratio <= 1.05,
- probe off-diagonal energy and normalized cross ratio <= 1.10.
- Rank by differential-energy ratio x settling ratio, ascending; ties by
  `ks_n`, then `kc_n`.

### Held-out classification (after selection)

- Baselines: `zero_feedback`, `local_feasibility_native` (guards pass).
- Primary: mean differential-energy ratio <= 0.95 vs both baselines; every
  single-condition ratio <= 1.10; settling no worse than local.
- No-harm: common IAE <= 1.05 x best, peak/RoCoF <= 1.10 x best, probe
  off-diagonal and normalized cross ratio <= 1.10 vs both baselines.
- Guards first; classes: `STOP-UNSAFE-CONTROL`, `STOP-NO-DIFFERENTIAL-BENEFIT`,
  `STOP-COMMON-MODE-HARM`, `STOP-NO-HARM-EXCEEDED`,
  `STOP-DEVELOPMENT-NO-CANDIDATE`, `DETERMINISTIC-DECOUPLING-PASS`.
- Pass authorises only the next registered Gate C (non-learning time-varying
  headroom); never training.

## Terminal stop rules

1. Identity guard failure on any step -> STOP-UNSAFE-CONTROL.
2. Action rank collapse -> STOP.
3. No development-eligible candidate -> STOP-DEVELOPMENT-NO-CANDIDATE.
4. Held-out guard/primary/no-harm failure -> STOP-* (no retry, no gain
   change, no bank resize).
5. Probe superposition beyond [-1, 1] -> fail-closed STOP.

A STOP-* outcome closes Gate B-3 without authorizing Gate C, tuning, random
arms, or MARL. If the low-corner law also fails to clear the 0.95 primary
threshold, the successive spectral-tuned damping laws R376-R379 jointly
support the registered no-differential-benefit conclusion for this
topology/action domain.

## Frozen capacity and execution discipline

Identical to R376-R378: one WSL Python process, one native thread, serial
rehearse -> create-only seal -> execute with expected seal SHA-256, no
retry, no parallel workers, no training; capacity anchored on the R374/R377
60-record serial anchor with 1.5x safety factor; results registered into
`results/MANIFEST.md` with `.sha256` sidecars, `LOCAL-ONLY`; evidence round
reserved via `reserve_round.py --strict-no-active --line paralleled_vsg_marl
--write-plan-stub`, prefight-checked, and gated by the experiment-efficiency
gate before any ANDES trajectory.

## Reuse boundary

Directly reusable: `active_power.py`, `vsg_energy_port.py`,
`vsg_energy_port_env.py`, `feasibility_native_vsg_action.py`; R378 guard /
endpoint / selection / classification structure; runner plumbing.

Adaptable donors: R378 HP controller with alpha re-frozen at 0.90; R377/R378
disturbance bank shapes.

Never transfer: R378 gains/law as evidence; R375 guard-failed trajectories;
Model-First objects/results; old checkpoints, rewards, training curves, or
title evidence.

## Immediate decision

This contract is the prospective Gate B-3 plan required by the route after
R378. No physical run or training is authorized by this document. The next
steps are (a) a separately reserved evidence round that seals this contract
byte-for-byte, (b) experiment-efficiency-gate and capacity evidence, (c)
rehearsal, and only then conditional execution.
