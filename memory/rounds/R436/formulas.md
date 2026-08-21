# R436 frozen formulas (objective-semantics gate)

Exact formulas frozen at plan time (2026-08-19). Every term's sign, unit,
and aggregation is literal; rehearsal runs a gradient-direction probe on
the real learner and the directed tests pin the same direction.

## 1. Observation row (per agent, 7 slots, float32)

o_i = [ f_dev_i, rocof_i, p_es_i, n1_f_dev_i, n2_f_dev_i, prev_residual_i, 1.0 ]

- f_dev_i = (freq_hz_physical[i] - 60.0) / 60.0            # unitless, Hz-normalized
- rocof_i  = (freq_hz_physical[i] - prev_freq_hz[i]) / (0.2 * 60.0)  # per-unit per 0.2s
- p_es_i   = P_es[i] / 600.0                                # normalized by the 600 MW base
- n1_f_dev_i, n2_f_dev_i = f_dev of the two ring neighbours
  (adjacency {0:[1,3], 1:[0,2], 2:[1,3], 3:[2,0]}); no-message arm
  zeroes slots 3-4 (honest zeros, R410 mask semantics).
- prev_residual_i = previous executed normalized residual (stateful, reset 0
  per episode; zero-initialized at episode start).
- slot 6 = constant 1.0 (bias).

OBS_DIM = 7, ACTION_DIM = 1 (per agent).

## 2. Residual action mapping (executed command)

- SAC actor output a_i ∈ (-1, 1) (tanh).
- normalized_residual_i = 0.70 * a_i     # same scale as the baseline clip
- baseline_power = map_action(controller_action) with
  controller_action = bandpass_k3p5.act(freq_hz - 60) clipped to ±0.70
  (R409 verbatim structure), mapped through the feasibility-native map.
- executed_power = map_residual_action(
      normalized_residual_actions = normalized_residual,
      baseline_power_system_pu = baseline_power.feasible_power_system_pu,
      previous_power_system_pu, soc, voltage_pu, dt_seconds=0.2)
  Zero residual => exact baseline (identity guard enforces this: any
  projection saturation raises; outer projection must be identity).
- env.step(executed_power.feasible_power_system_pu)
- prev_residual_i (obs slot 5) = normalized_residual_i of the executed step.

## 3. Reward (per agent, per step)

r_i = 100 * r_f,i + 50 * r_abs,i + 0.0056 * r_H + 0.0056 * r_D

- d_omega_i  = f_dev_i                         # same normalized deviation
- omega_bar  = (d_omega_i + Σ_j η_j n_j_f_dev) / (1 + Σ_j η_j)
  with η_j = 1 for the message arm, 0 for the no-message arm.
- r_f,i = -(d_omega_i - omega_bar)^2 - Σ_j η_j (n_j_f_dev - omega_bar)^2   # ≤ 0
- r_abs,i = -(normalized_residual_i)^2          # ≤ 0, penalizes residual effort
- r_H = -(mean_i normalized_residual_i / 2)^2   # common-channel penalty, ≤ 0
- r_D = -(mean_i (normalized_residual_i - mean_i normalized_residual_i))^2
                                              # differential-channel penalty, ≤ 0
- TDS-failed step: r_i = -50.0 for all i (R428/R431 convention).

All reward terms are non-positive penalties (as in R431's family), so
higher reward = less cost; the gradient-direction probe checks:
d(r_abs)/d(a_i) aligns with -2*0.70*residual (penalty = descent on |residual|),
and d(r_D)/d(a_i) drives the differential residual toward zero.

## 4. Training protocol (frozen)

- Env: AndesVSGEnergyPortEnv over AndesMultiVSGEnvV4 (random_disturbance
  False, comm_fail_prob 0.0, comm_delay_steps 0, V4Config
  vsg_m0=200.0, d0_per_agent=(100,100,100,100) — nominal plant only for
  training; no variant exposure).
- Seed: env.seed(42) (R408/R409 object seed); torch/np/random seeded by
  training seed 401..405 (R431 statistical scale).
- 43,200 interaction steps per run, 50 steps per episode, scenario
  schedule over the frozen training conditions (below), 10 runs =
  2 arms x 5 seeds.
- Training conditions (frozen, from the R408 dev bank, nominal plant):
  dev3_probe_bus15_minus_0p45 (probe), dev3_disturbance_pq1_plus_0p65,
  dev3_disturbance_bus14_minus_0p55; schedule cycles in the registered
  order (probe, disturbance A, disturbance B, repeat).
- SACAgent hyperparameters: hidden 4x128, lr 3e-4, gamma 0.99, tau 0.005,
  buffer 10,000, batch 256, alpha [0.005, 5.0], grad cap 1.0, one update
  per env step (R430/R431 verbatim).
- Checkpoint: final.pt per (arm, seed) + per-240-episode snapshots +
  manifest with convergence_diagnostics_valid, tds_failed_episodes,
  critic loss trace (log-only readout, no RNG consumed).

## 5. Evaluation (frozen)

- Checkpoints: the 10 trained SAC policies (2 arms x 5 seeds), evaluated
  deterministically (mean action, no exploration noise).
- Bank: the 10 EIG-sound R413 variants (nominal + out_Line_4/5/7/8 +
  x0p5/x1p5 Line_4/7 + x1p5 Line_7_12; the two VSG-tie outage variants
  excluded by the sealed R413 case-level soundness verdict), each with
  the R408 dev bank condition set (8 paired probes + 2 disturbances,
  seed 42, 50 steps).
- Arms per variant: residual_sac_message (5-seed median), residual_sac_no_message
  (5-seed median), bandpass_k3p5 (re-run same-variant reference, R434
  precedent), zero_feedback.
- Endpoints: frozen R409 thresholds r_d <= 0.95, r_cross <= 1.10 (strict
  0.95 recorded), all R379 guards; per-variant candidate-versus-local.
- Nominal anchor: nominal variant must reproduce the R408 dev numbers
  (0.938947 / 0.539791) within 1e-6 relative for the bandpass arm.

## 6. Decision tree (pre-registered, from plan)

- LEARNED-BEYOND-DETERMINISTIC: any residual-SAC arm reaches r_d <= 0.95
  and r_cross <= 1.10 with all guards on >= 1 variant where the bandpass
  reference does not. Stop at the claim gate; owner re-evaluates title.
- MESSAGE-INCREMENT: message arm's 5-seed median r_d or r_cross improves
  >10% over the no-message arm with no guard deterioration.
- NO-LEARNING-INCREMENT: neither arm passes anywhere and no message
  increment. Bounded negative on the energy-port object.
- CANARY-INVALID: bank validity failure; no scientific conclusion.
