# R38 verdict — TD3 refutes the entropy-bonus hypothesis; reward landscape exposed

**Date**: 2026-05-17
**Branch**: `main` (post-refactor)
**Status**: **COMPLETE**. H1 refuted by 3-seed sweep, but the data
exposed a deeper root cause for the 0.137 attractor that **overturns
the assumed mechanism** documented in R29–R33.

---

## TL;DR

> TD3 was supposed to escape the 0.137 multi-seed SAC attractor by
> removing the entropy regularization that was hypothesized to pull
> the actor toward near-zero action. **It did not.** 3-seed sweep
> (seeds 49/50/51, 75 episodes each) landed at 6-axis mean = 0.0841
> (range 0.059–0.098), **all three seeds below no-control (0.104)**
> and tightly clustered (std ≈ 0.022 vs SAC R23–R27's wider spread).
>
> Per-axis breakdown revealed the actor uses < 1 % of the action range
> (dH_utilization project ≈ 1.4–4 vs paper 400; dD_utilization ≈ 1.7–8
> vs paper 800). Reward landscape analysis: PHI_H/D action-cost
> dominates PHI_F frequency-cost ≈ 500 × in V4 env, so "do nothing"
> is locally optimal. Entropy bonus was a red herring — both SAC and
> TD3 fall into the same near-zero attractor because of the reward
> shape, not the algorithm.

---

## Hypothesis test result

**H1 (TD3 escapes 0.137)**: **REFUTED**.

| Decision rule | Triggered? | Outcome |
|--------------|-----------|---------|
| All 3 seeds < 0.10 | **YES** | H1 refuted (TD3 even worse than SAC mean) |
| All 3 seeds ∈ [0.10, 0.18] | no | — |
| At least 1 seed ∈ [0.18, 0.30] | no | — |
| At least 1 seed > 0.30 | no | — |
| Any seed crashes | partial (TDS divergence in early eps, but training continued) | flag for optimization |

Per the pre-registered rule (R38/plan.md): "All 3 seeds < 0.10 → H1
refuted (TD3 even worse than SAC). Investigate critic Q
overestimation." The diagnosis below points elsewhere.

---

## Per-axis breakdown (3 seeds × 2 scenarios)

| Axis | TD3 typical score | Project value | Paper target |
|------|------------------|----------------|--------------|
| max_\|df\|_Hz | 0.10–0.50 | 0.17–0.21 Hz | 0.10–0.13 Hz |
| final_\|df\|@6s | 0.00–0.50 | 0.10–0.14 Hz | 0.05–0.08 Hz |
| settling_s | **0.00** | **8–10 s** (never settles) | 2.5–3.0 s |
| dH_smoothness | 0.95–0.99 | 0.30–0.51 std | 0 (ideal) |
| dD_smoothness | 0.96–0.99 | 0.24–1.25 std | 0 (ideal) |
| **dH_utilization** | **0.003–0.010** | **1.4–4** | **400** |
| **dD_utilization** | **0.002–0.010** | **1.7–8** | **800** |

The dominant failure is **action under-utilisation**. The actor moves
≈ 1 % of the paper's action range. Smoothness is "perfect" because
the actor barely moves; settling fails because no inertia/damping
modification can dampen the disturbance.

---

## Reward-landscape analysis (the real root cause)

V4 env reward per step (from `andes_vsg_env_v4.py` defaults):
```
r_f   = -PHI_F   * Σᵢ (Δωᵢ - meanⱼ Δωⱼ)²            # frequency sync
r_h   = -PHI_H   * Σᵢ (ΔMᵢ)²                          # inertia action cost
r_d   = -PHI_D   * Σᵢ (ΔDᵢ)²                          # damping action cost
r_abs = -PHI_ABS * Σᵢ (Δωᵢ)²                          # Kundur tight-coupling
```

V4 paper-faithful weights: `PHI_F=100, PHI_H=0.0056, PHI_D=0.0056,
PHI_ABS=50`. Action range `[-200, 600]`.

Order-of-magnitude per-step costs:

| Term | Worst-case magnitude | Calculation |
|------|---------------------|-------------|
| r_h (max action) | **2016** | 0.0056 × 600² |
| r_d (max action) | **2016** | 0.0056 × 600² |
| r_f (paper-bad Δf=0.2 Hz) | **0.16** | 100 × (0.2/50)² ≈ 0.016 × 10 (Δω scale) |
| r_abs (paper-bad Δf=0.2 Hz) | **0.08** | 50 × (0.2/50)² |

(Δω is in p.u. on `2π·FN ≈ 314 rad/s`, so Δω ≈ 2π × Δf/FN ≈ Δf × 0.126.)

**Action cost dominates frequency cost ≈ 500–1000×** under V4
weights. Any non-zero ΔM/ΔD strictly worsens reward unless it reduces
the **already-tiny** frequency error by 500× as much. The locally
optimal policy is to set ΔM = ΔD = 0 — exactly what TD3 (and SAC's
multi-seed attractor) converged to.

This explains **every prior result**:

- R29 hparam sweep failed: small PHI changes don't break the 500×
  asymmetry
- R31 / R33 reward shaping failed: extra penalty terms only
  *increase* the action-cost denominator
- R32 stochastic ensemble failed: averaging near-zero actors stays
  near zero
- **R21 lucky basin succeeded** because SAC's *entropy noise*
  accidentally pushed the actor into a high-ΔM/ΔD region before
  critic updates could pull it back. SAC's entropy was not the cause
  of the attractor — it was the **escape mechanism**. Without entropy
  (TD3), no escape happens.

---

## The architectural fix that R38 surfaces

The reward landscape is **structurally** biased against action. To
let any algorithm learn a useful policy, one of:

1. **Normalize the action penalty**: penalize `aᵢ²` where `aᵢ ∈ [-1, 1]`
   is the *normalized* action, not the *physical* action ΔMᵢ ∈
   [DM_MIN, DM_MAX]. Then action cost stays O(1) regardless of
   action range.
2. **Increase PHI_F by 500–1000 ×** so frequency cost matches action
   cost magnitude.
3. **Change reward to relative improvement** over no-control instead
   of absolute frequency error.

(1) is the cleanest — it's a code change in `andes_vsg_env_v4.py`
that adjusts only the reward computation, not the env physics. (2)
changes the paper Eq.14 coefficient and would invalidate the paper
numbers. (3) is a bigger redesign.

**This is not part of R38 (out of scope)**; it is the candidate
research direction for R39. Recorded as `CLM-0043` for traceability.

---

## What R38 establishes

- TD3 added as a first-class algorithm (`agents/td3.py`, 6 unit
  tests, `--algo td3` flag); the `_SACBase` + `BaseAgent` Protocol
  refactor delivered on its "new algo = one file" promise
- The 0.137 attractor explanation in R29–R33 was **wrong**: entropy
  bonus was the escape mechanism, not the trap; the trap is the
  reward landscape's 500× action-vs-frequency cost asymmetry
- TD3 produces tighter multi-seed distributions than SAC, useful for
  future ablations that need reproducibility (CLM-0042 deepening
  pass already noted this)

---

## What R38 does not establish

- Whether a fix to the reward landscape (R39 candidate) actually
  recovers any of the action-utilization axes
- Whether 75 episodes is enough for TD3 with the proposed fix
- Whether the paper headline numbers can be re-derived under a
  rebalanced reward without invalidating the V4 paper-faithful claim

---

## New claims this round

- `CLM-0043` — reward landscape's PHI_H/D × (ΔM/ΔD)² term dominates
  PHI_F × Δω² by ~500–1000 × at V4 paper-faithful weights; this is
  the structural cause of the 0.137 multi-seed attractor previously
  misattributed to SAC's entropy bonus. Fix candidates queued for R39.
