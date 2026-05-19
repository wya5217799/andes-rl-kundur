---
round: R110
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R110 plan — Disturbance profile audit: ANDES Toggler Line_8 trip at t=2s

**Status**: ACTIVE → DONE in same session (single-finding audit)
**Opened**: 2026-05-19
**Driver**: Following R105 reward audit + R89 ANDES Kundur audit + R85 classical baseline, the only remaining piece of the R09 2× max_df residual mystery is the **disturbance injection profile**. R105 found V4 inherits ANDES kundur_full unchanged; today's discovery: ANDES default has a **Toggler trip on Line_8 at t=2s** that V4 env never removes.
**Parent**: CLM-0173 (R09 audit, F1-F5 didn't include disturbance profile);
R08 §2 Finding 2 (2× max_df residual still partly unexplained).

## TL;DR

**🚨 Critical finding**: ANDES default `kundur_full.json` ships with a
`Toggler` entry that trips `Line_8` (Bus 8 → Bus 9, Area 2 internal, one
of two parallel paths) at simulation time t=2.0s. V4 env never removes
this Toggler in `_build_system()`. Therefore **every LS1/LS2 scenario
actually has TWO disturbances**:

| t (s) | Event | Source | Paper-intended? |
|---|---|---|---|
| 0.0 | Warm-up TDS starts | base_env.reset | ✓ |
| 0.5 | Load step (LS1 or LS2) applied | V4._apply_disturbance | ✓ |
| 0.7 | First agent control step | agent loop | ✓ |
| **2.0** | **Line_8 trip (Area 2 internal)** | **ANDES default Toggler** | **❌ UNINTENDED** |
| 10.5 | Agent control ends (50 × DT) | base_env.STEPS_PER_EPISODE | ✓ |

paper Sec.IV-C says LS1/LS2 is a SINGLE load step. V4 evaluates each
scenario with one load step + one line trip = compound disturbance.

This likely explains a meaningful chunk of R08 Finding 2's 2× max_df
residual (V4 H=300 no_ctrl LS1 max_df=0.266 vs paper 0.13). Line trip
adds extra frequency excursion + voltage transient on top of the load
step. Paper benchmarks assume single-event scenarios.

## Methodology (zero compute)

100% file-inspection. No ANDES TDS needed for the finding itself.

1. Read `probes/r89_andes_kundur_full.json::Toggler` (cached) — confirmed:
   ```json
   {"idx": 1, "u": 1.0, "name": "Toggler_1", "model": "Line",
    "dev": "Line_8", "t": 2.0}
   ```
2. Grep `src/andes_rl_kundur/env/andes/*.py` for "Toggler|trip|Line_8" —
   no removal code, V4 inherits unchanged.
3. Cross-ref `base_env.reset` warm-up to t=0.5s + `_apply_disturbance`
   PQ.Ppf modification at t=0.5s + agent control window 0.7s-10.5s →
   Toggler at t=2s falls INSIDE the agent control window.
4. Identify Line_8: Bus 8 (idx 8 = name 13, Area 2, 230 kV) → Bus 9
   (idx 9 = name 112, Area 2, 230 kV). Area-2 internal, one of TWO
   parallel paths (Line_7 stays). Moderate-severity trip, not catastrophic.

## Findings

### F1 (CRITICAL): unintended second disturbance at t=2s in every scenario

ANDES default Toggler trips Line_8 at t=2.0s. V4 env does NOT remove
it (no `ss.Toggler.remove(...)` or `u=0` override anywhere). Every
LS1/LS2 eval (and every training scenario) has this **compound
disturbance profile**:

- 0.5s : load step (paper-intended)
- 2.0s : Line_8 trip (paper-UNINTENDED, ANDES default)

R85 classical baseline (CLM-0184) tuned droop K=2 to geo 0.197 on this
compound scenario. R72_w4 SOTA (CLM-0094) geo 0.391 also trained/eval'd
on compound scenario. R57-R85 91-round plateau is on compound scenario.

If Toggler were removed, the dynamics would be cleaner (just one
event at t=0.5s). max_df should drop closer to paper benchmarks
(0.13 / 0.10 Hz for LS1/LS2).

### F2 (HIGH): partial explanation of R08 Finding 2 2× max_df residual

R08 §2 Finding 2 reported H=300 no_ctrl max_df=0.266 vs paper 0.13 =
**2× too large**. R89 audit (CLM-0173) attributed to F1 fn=60/50, F2
load topology, F3 D=0, F4 TGOV1 active — but F1 correction makes
residual LARGER (1.45×→1.75×), so F1/F2/F3/F4 didn't fully close
the gap.

R110 F1 (Toggler) is the **missing piece**: Line_8 trip at t=2s adds
~50-100ms extra transient in addition to the load-step transient. For
LS1 (Bus 14 load reduction), the 6s window contains BOTH events;
max_df is the max over the whole window, likely picking up the Line
trip's contribution.

Quantitative R90+ test (Q-NEW): run V4 with Toggler removed
(`ss.Toggler.set('u', 1, 0.0, attr='v')` after setup), zero action,
LS1+LS2. If max_df drops by ≥30%, the Toggler is the dominant
remaining residual cause.

### F3 (MEDIUM): training-time exposure to compound disturbance

R57-R85 91-round trained on **compound** disturbance profile. Trained
policies have learned to handle Line trip + load step jointly. If
Toggler is removed for paper-faithful eval, those policies may
**under-perform** on the cleaner setting (over-specialized for compound).
Counter-argument: removing Toggler reduces max_df (easier scenario),
likely improves any reasonable controller's geo. Net direction TBD.

## Claims to write

- CLM-0194: Toggler Line_8 trip @ t=2s unintended in V4 (this round)

## Cross-references

- CLM-0173 (R89 audit) — F1-F5 didn't cover Toggler; R110 F1 is the missing F6
- CLM-0094 (R72_w4 SOTA) — geo 0.391 conditional on compound scenario
- CLM-0184/0186 (R85 droop best) — geo 0.197 conditional on compound scenario
- CLM-0191/0192 (R105 reward audit) — separate paper-deviation thread
- R08 §2 Finding 2 (2× max_df residual)
- paper §IV-C (LS1/LS2 = single load step)
- `probes/r89_andes_kundur_full.json::Toggler`

## 资产保护契约

零 V4/V4Config/base_env/agents/ckpt mutation. 仅写 verdict + claim + plan.
零 ANDES TDS. 零 conflict with R102 (running).

## Outcome categories

| outcome | next |
|---|---|
| Toggler is confirmed unintended in V4 (audit only) | document as CLM-0194, future round to ablate |
| (future R-NEXT) Toggler removal ablation: max_df drops ≥30% | R09 2× residual primarily Toggler-induced; remove or document |
| (future) Toggler removal: max_df drops <10% | Toggler not dominant; F2/F3 (R89) more important |
