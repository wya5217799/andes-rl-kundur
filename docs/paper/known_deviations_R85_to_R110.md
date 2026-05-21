# Known paper-implementation deviations — R85→R110 audit consolidation

**Date**: 2026-05-19
**Audit rounds**: R85 (classical baseline), R89 (ANDES Kundur audit),
R105 (reward audit), R110 (disturbance profile audit)
**Status**: 4 audited deviation categories; some quantified, some pending
ablation
**Maintained for**: paper write-up "Implementation Notes" /
"Limitations" section, plus future paper-faithful re-baselining (R114+)

This document consolidates the four substantive paper-implementation
deviations discovered in the R85→R110 audit sweep. Each entry cites
the canonical claim, severity, current status, and recommended paper
write-up disposition.

---

## D1. R72_w4 SOTA training reward ≠ paper Eq.14-18 (CLM-0191 / R105)

**Severity**: CRITICAL (effective training objective differs from paper)
**Locked in**: R72_w4 `training_log.json::env_config`

R72_w4 LSTM SOTA was trained with:
| Component | Paper Sec.IV-B | R72_w4 SOTA training |
|---|---|---|
| φ_f (sync) | 100 | 100 ✓ |
| φ_h (ΔH penalty) | 1 | **0.0056** (÷178) |
| φ_d (ΔD penalty) | 1 | **0.0056** (÷178) |
| φ_abs (Δω² restoration) | (not in paper) | **50** (+50% of φ_f) |
| action_penalty_mode | physical (Eq.17-18 literal) | normalized |

R72_w4 is effectively a "restoration-first" agent (r_abs term ~-0.25
contribution dominates r_f ~-0.10), not paper's "sync-only" DDIC.

**Paper write-up disposition**: must disclose in §Implementation. Frame
as engineering choice (R18 historical empirical tuning), cite
[CLM-0191](../../memory/claims/CLM-0191.md). For paper-faithful
comparison, `V4Config.paper_strict_pure()` exists (phi_abs=0,
phi_h=phi_d=1, paper Eq.14 literal). Q-0024 / R103 (in progress by
another window) tests whether paper_strict_pure retrain matches geo
0.391.

---

## D2. ANDES Kundur physical parameters ≠ paper Sec.IV-A (CLM-0171/0172/0173 / R89)

**Severity**: CRITICAL through MEDIUM (multi-finding)

| # | Finding | Severity | Source |
|---|---|---|---|
| F1 | fn=60 Hz ANDES vs FN=50 Hz env (env underreports max_df by 17%) | CRITICAL | [CLM-0171](../../memory/claims/CLM-0171.md) |
| F2 | Loads at Bus 7+8 (ANDES default) not Bus 14/15 (paper) | HIGH | [CLM-0172](../../memory/claims/CLM-0172.md) |
| F3 | GENROU D=0 (paper Eq.1 D ≠ 0) | MEDIUM | [CLM-0173](../../memory/claims/CLM-0173.md) |
| F4 | TGOV1 u=1 active (paper §II-A neglects inner loop) | NEEDS VERIFY → Q-0021 | [CLM-0173](../../memory/claims/CLM-0173.md) |
| F5 | PQ q0<0 capacitive injection (unusual load record) | LOW | [CLM-0172](../../memory/claims/CLM-0172.md) |

GENROU H/M parameters MATCH paper exactly (H=6.5/6.175 s, Sn=900 MVA).
The 2× max_df residual (R08 Finding 2) cannot be attributed to small-H
hypothesis.

**Paper write-up disposition**: §Implementation Notes lists deviations
F1-F5. F1 is a documented bug (locked by
[tests/test_v4_fn_consistency.py](../../tests/test_v4_fn_consistency.py)
xfail strict). F4 requires R90+ TGOV1 ablation (Q-0021). F2 requires
ADR-0006 framing.

---

## D3. Toggler Line_8 trip at t=2s (CLM-0194 / R110)

**Severity**: CRITICAL — likely R09 2× residual's missing piece

ANDES default `kundur_full` ships with `Toggler` entry that trips
`Line_8` (Bus 8 → Bus 9, Area 2 internal, 1 of 2 parallel paths)
at simulation time t=2.0s. V4 env never removes it.

**Compound disturbance profile in every V4 LS1/LS2 scenario**:
- t=0.5s : load step (paper-intended)
- **t=2.0s : Line_8 trip (paper-UNINTENDED, ANDES default)**

R57-R85 91-round training + eval ALL on compound scenario; paper
Sec.IV-C is single-event → NOT apples-to-apples to paper cum_rf.
The Line trip likely adds ~50-100ms extra transient that the max_df
metric captures, partially explaining the 2× residual that R89 F1-F5
couldn't.

**Paper write-up disposition**: must disclose; the unintended Toggler
existing throughout R57-R85 training is significant. Either:
- (a) Re-baseline on DISABLE_TOGGLER=1 V4 (R114 testing this now)
- (b) Document compound scenario in §Implementation + adjust paper claims

R114 (this conversation, td3_lstm 75 ep s54 retrain with DISABLE_TOGGLER=1)
tests whether trained agent breaks SOTA 0.391 on cleaner problem.
Q-0025 plans the cheaper zero-action ablation.

---

## D4. RL has 1.5× advantage over classical (updated; CLM-0184/0186/0230/0232 / R85+R102)

**Severity**: POSITIVE (paper-claim support, but narrower than earlier framing)

| Controller | geo on V4 compound + augmented reward | Δ vs R72_w4 SOTA |
|---|---|---|
| no_control (R30) | 0.104 | -0.287 |
| best droop K=2 magnitude (CLM-0184) | 0.197 | -0.194 |
| best PI naive (signed) (CLM-0185) | 0.058 (paradigm mismatch) | -0.333 |
| **best magnitude-PI (Kp_M=2, Kp_D=5, Ki=0) (CLM-0230)** | **0.260** | -0.131 |
| R72_w4 LSTM SOTA (CLM-0094) | **0.391** | 0 |

**Updated advantage**: R72_w4 LSTM SOTA / best magnitude-PI = 0.391/0.260
= **1.50× geo advantage**. Earlier "1.99× vs droop" was unfair: droop
is a degenerate 1-gain controller; magnitude-PI is the proper classical
baseline.

**Sign-paradigm finding (CLM-0185)**: naive signed PI catastrophically
fails (geo 0.058, LS1 TDS-crash). VSG parameter control needs
magnitude-symmetric law, not setpoint-tracking signed PI. RL learns
this implicitly; classical engineers need domain knowledge to write
the right form. Paper-worthy.

**Caveat**: comparison is on V4 compound scenario (D3) with augmented
reward (D1). R85/R102 magnitude-PI used V4 DEFAULT bounds (dm_max=300
per paper Eq.12); R72_w4 SOTA was trained at dm_max=600 (D5 below).
R133 re-evaluates magnitude-PI at D5-fair dm_max=600 for fully
apples-to-apples comparison.

---

## D5. Action bound expansion 2× paper Eq.12 (CLM-0233 / R102 follow-up)

**Severity**: HIGH — affects RL-vs-classical fairness

| Action bound | Paper Eq.12 | R72_w4 SOTA training |
|---|---|---|
| ΔH_min | -100 | **-200** (2× wider) |
| ΔH_max | +300 | **+600** (2× wider) |
| ΔD_min | -200 | -200 ✓ |
| ΔD_max | +600 | +600 ✓ |

ΔH bounds doubled from paper Eq.12; ΔD bounds match. R72_w4 SOTA action
trace (`results/r80_v5_cross_eval/v4_baseline/ckpt_R72w4_LSTM_s54_load_step_*.json`)
shows **96-97% of actions are saturated** above 50% magnitude. Effective
strategy = bang-bang within wider-than-paper bounds.

Per-agent asymmetry: agents 0/1 (area 1) |dM|≈185 (within paper +300
bound); agents 2/3 (area 2, near disturbance) |dM|≈565 (FAR exceed
paper +300). The agent profile is IMPOSSIBLE under paper Eq.12.

**Implication for D4 RL advantage**: R85/R102 magnitude-PI ran on
DEFAULT V4Config (dm_max=300 paper Eq.12) → classical was handicapped
with smaller action range. R133 re-evaluates at dm_max=600 to give
true apples-to-apples advantage number.

**Paper write-up disposition**: must disclose action bound expansion.
Either justify as engineering choice (project's empirical action range
maximises performance) or rerun SOTA at paper Eq.12 bounds for clean
comparison. R119 (parallel session) tests dm_max=1200 (4× paper).

---

---

## Combined disposition for paper write-up

Future paper write-up should structure §Implementation Notes / §Limitations as:

1. **Reward function adaptation** (D1): cite R72_w4 reward weights as
   "engineering augmentation motivated by Kundur tight coupling
   ([CLM-0191](../../memory/claims/CLM-0191.md))". Cite
   `V4Config.paper_strict_pure()` as the paper-literal alternative;
   note that Q-0024 retrain (R103) is forthcoming.

2. **ANDES Kundur replication** (D2): document F1-F5 deviations.
   F1 fn=60/50 is a documented calibration discrepancy (regression
   test `test_v4_fn_consistency.py` locks in). F4 TGOV1 governors
   active by default (Q-0021 pending ablation).

3. **Disturbance profile** (D3): document compound disturbance
   (load step + line trip) caused by ANDES default Toggler.
   R114 testing whether DISABLE_TOGGLER training matches/beats
   compound SOTA.

4. **RL vs classical comparison** (D4): present R85 droop and
   magnitude-PI (R102 pending) numbers, explicit that comparison is
   on V4 not paper-literal scenario.

---

## Outstanding ablations

| Question | Plan | Status |
|---|---|---|
| [Q-0021](../../memory/questions/Q-0021.md) | TGOV1 u=1 vs u=0 ablation | bundled in R102 W2 (in progress) |
| [Q-0023](../../memory/questions/Q-0023.md) | Magnitude-PI 4D Kp×Ki sweep | R102 W1 (in progress) |
| [Q-0024](../../memory/questions/Q-0024.md) | paper_strict_pure retrain | R103 (other window) |
| [Q-0025](../../memory/questions/Q-0025.md) | Toggler-OFF zero-action ablation | deferred — R114 tests retrain instead |

---

## Round-by-round audit chain

| Round | Date | Topic | Output |
|---|---|---|---|
| R08 | 2026-05-07 | H scan + governor + 2× residual | Finding 2 |
| R09 | (planned, never executed) | platform 2× residual audit | — |
| R85 | 2026-05-19 | Classical baseline (droop / PI) | CLM-0184/0185/0186 |
| R89 | 2026-05-19 | ANDES Kundur params F1-F5 | CLM-0171/0172/0173 |
| R102 | 2026-05-19 | magnitude-PI + TGOV1 ablation | in progress |
| R105 | 2026-05-19 | Reward function audit | CLM-0191/0192 |
| R110 | 2026-05-19 | Toggler disturbance audit | CLM-0194 |
| R114 | 2026-05-19 | Toggler-OFF retrain | in progress |
