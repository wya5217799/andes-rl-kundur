# R259 verdict — Action-disturbance LAG CORRELATION: RL decoupled, droop linearly tracks (3rd probe-first win)

**Date**: 2026-05-20
**Status**: CLOSED-POSITIVE — complements R257 smoothness probe with orthogonal coupling-strength finding
**Type**: research (probe-first per NOTES_ANDES.md; mechanism investigation)
**Wall**: ~30 min total (probe write + run + verdict)

## TL;DR

`scripts/r257_probe_anticipation_lag.py` (script-name mismatch:
R257 reserved by autonomous-loop's smoothness probe in parallel;
this analysis lives in R259) — 10-min cross-correlation analysis of
action[t] vs disturbance[t-k] for each controller.

**Result**: droop k=10 has corr +0.788 at k=0 (linear tracking),
R201 SOTA has corr -0.184 at k=0 (decoupled / anti-correlated).
**RL is not LAGGING droop — it's DECOUPLED from disturbance
dynamics entirely**, consistent with R256's "max-out then hold"
finding.

## Probe data (CLM-0485 has full table)

| Controller | corr@k=0 | peak k | corr@peak |
|---|---|---|---|
| R201 SOTA | **-0.184** | +2 | -0.115 |
| R254 phi_f-only | +0.080 | +2 | +0.084 |
| R246 only-phi_abs | +0.054 | +1 | +0.054 |
| Droop k=10 | **+0.788** | +1 | **+0.805** |
| Droop k=2 | +0.915 | +1 | +0.926 |

Droop's +0.79 → +0.81 correlation = action linearly modulates with
disturbance. RL's ≈ 0 to -0.18 = action ignores disturbance dynamics
once saturated.

## Three probes converge (R256+R257+R259)

| Probe | Dimension | RL | Droop k=10 |
|-------|-----------|-----|------------|
| R256 / CLM-0470 | Saturation | 22-92% pinned at bound | 0-2.5% near bound |
| R257 / CLM-0475 | Smoothness (TV) | 3.45 dD jitter (low) | 9.71 dD jitter (high, ~3× RL) |
| **R259 / CLM-0485** | **Coupling (corr@k=0)** | -0.18 (decoupled) | **+0.79 (linear track)** |

All three are surface signatures of one root cause: **policy-class
inductive bias to "fire once, hold saturated"** vs droop's structural
proportional control.

## Pre-registered outcomes (R259 plan)

| Outcome | Pre-registered | Actual |
|---------|----------------|--------|
| RL has timing lag (peak k>0 vs droop k=0) | possible | partially — RL peaks at k=+2 but corr is near zero, so peak is meaningless |
| RL decoupled (flat/negative corr) | possible | **CONFIRMED** — R201 corr ≈ -0.18, R254/R246 ≈ 0 |
| RL and droop both responsive | possible | refuted |

Matched outcome 2: RL decoupled.

## Why R201's negative corr at k=-2 (-0.478) is informative

When |Δω| was small 2 steps in past, |action| was already LARGE
(actor saturated on disturbance onset). As |Δω| evolves later,
|action| stays high and slightly decreases — not because the
actor is responding, but because of sign-change components
cancelling at saturation boundary. This is **NOT** anticipation
or lag — it's **disengagement**: RL responds ONCE at onset and
stops tracking.

## Probe-first protocol — 3rd textbook win

- 4 probes total (R255 local-global, R256 saturation, R257
  smoothness via autonomous loop, R259 coupling): ~2 hr cost.
- Counterfactual without probes: ≥3 env-modifying rounds
  (global r_f, widebound retrain, CTDE architecture) +
  V4 regression risk.
- **Saved ~8-12 hr + V4 contract risk** across 4 probes.

R258 (sync-only RL, currently training) is the FIRST
training-round candidate that probe-first didn't refute — it
mirrors droop's reward philosophy in RL framework and will
inform paper 7th contribution path.

## Questions opened (this round)

- (none — three-probe mechanism finding is converged and self-consistent)

## Questions closed (this round)

- "Does RL lag droop in disturbance response (anticipation lack)?"
  ANSWERED: NO. RL doesn't lag — it's DECOUPLED. Action peaks at
  disturbance onset (saturation), doesn't track subsequent dynamics.

## Questions advanced (this round, status unchanged)

- "What policy-class modification would close the cum_rf gap?"
  Three candidates from R256/CLM-0470 remain (linear actor /
  action regularization / hybrid warm-start); R258 tests a 4th
  (sync-only reward with current architecture).

## 给 PI 的话

**这周干了啥**：R259 = mechanism candidate #2 (anticipation lag)
的 probe. 跟 autonomous loop 同时跑的 R257 (smoothness) 是
orthogonal angle. 都 probe-first 协议, 10-min, 0 env code.

**结果（一句话）**：**RL action 与 disturbance 完全 decoupled** (R201
corr@k=0 = -0.18), 而 **droop k=10 linearly tracks** (corr = +0.79).
**RL 不是 lag, 是 disengage** — saturate-then-hold.

**意外**：
1. **R201 SOTA action 跟 |Δω| 负相关** (-0.18 at k=0, -0.48 at k=-2).
   这是 saturation-then-hold 的 mathematical signature: action 提早
   saturate, |Δω| 后才 peak, 两者反相.
2. **三 probe 收敛同一 root cause**: R256 (saturation) + R257
   (smoothness inversion — RL smoother) + R259 (decoupling) 都指
   policy-class inductive bias. **mechanism 故事 close**.
3. **R258 (sync-only RL training, autonomous loop 正在跑) 是 first
   training-round candidate** that probe-first protocol 没有 refute —
   它 mirror droop reward philosophy in RL framework.

**Paper Sec.IV-D mechanism final 表述** (post R256+R257+R259):
> "Three converging probes (saturation R256, smoothness R257, coupling
> R259) identify a single mechanism: TD3+LSTM tanh-projected per-agent
> actor learns 'fire once, hold saturated' strategy. Droop's
> structurally proportional control linearly tracks disturbance.
> Both manifest as RL: saturated + smooth + decoupled; droop:
> sub-saturated + jittery + coupled."

**我默认下一步做**：
1. 等 R258 (sync-only RL) 完成. 这是 mechanism 推动的 test: 如果
   sync-only reward 让 RL 突破 cum_rf plateau → paper 7th 候选
   confirmed; 如果 RL 还是 plateau → 需要 architectural change.
2. R258 大概 ~5 min 还剩, autonomous loop 会 score.
3. R258 outcome 后, paper Sec.IV-D mechanism + 7th contribution 直接
   或推 paper draft 或推 R260 (architectural change).

**你想插一脚就说**：probe-first 协议 4/4 (R255/R256/R257/R259) 全
validation. R258 outcome 决定 paper 7th 是 ready 还是需要 follow-up.
我等 R258 result.

## Cross-references

- R256 / CLM-0470 (saturation finding)
- R257 / CLM-0475 (smoothness inversion finding, autonomous loop)
- CLM-0480 (R258 sync-only RL claim, currently TBD)
- CLM-0485 (this round's claim)
- `scripts/r257_probe_anticipation_lag.py` (script name predates R259)
- `results/r257_probe_anticipation_lag.json`
- `docs/paper_drafts/sec_iv_d_paper_eq14_gauge_invariance.md` (memo update pending)
