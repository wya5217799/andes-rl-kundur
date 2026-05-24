# R258 verdict — Sync-only RL training COLLAPSED; phi_abs IS structural stabilizer

**Date**: 2026-05-20
**Status**: CLOSED-NEGATIVE — phi_abs=0 catastrophic; CLOSED-POSITIVE on
mechanism (reward-hacking via "all agents drift together" surfaced as a
NEW Sec.IV-D contribution candidate)
**Type**: research (mechanism-motivated training; first actual ANDES training
of this session after 3 probe-first rounds)
**Wall**: ~13 min ANDES WSL training + 1 min final-eval + ~20 min verdict

## TL;DR

Trained td3_lstm scalar at s50 with `--phi-h 0 --phi-d 0 --phi-f 100
--phi-abs 0` (sync-only, mirroring droop k=10's reward philosophy).
**Result: geo=0.0100, cum_rf=-0.2228 — FULL COLLAPSE**, identical
signature to R248 (paper-strict phi_h=phi_d=1.0). Two completely different
reward configs hit the same "all agents drift together" degenerate
attractor.

**Mechanism**: phi_abs is a **structural stabilizer**, not just a transient-
penalty term. Without it, the actor reward-hacks `r_f = -phi_f × sync_residual`
by outputting near-zero or homogeneous actions (sync residual = 0 when
all agents drift identically). The training reward looks great (best
ep 29 reward = -0.5), but eval against actual Kundur transient dynamics
exposes the degenerate policy (geo=0.000 on LS1 AND LS2).

**Paper Sec.IV-D contribution 6 candidate**: "phi_abs structural stabilizer
+ reward-hacking finding" is a NEW publishable result; CLM-0445's "RL
trained with cum_rf as reward" candidate (paper 7th contribution) is REFUTED
for the direct-removal approach.

## Result vs phi-configuration decomposition

| Run | phi_h | phi_d | phi_f | phi_abs | geo | cum_rf | status |
|-----|-------|-------|-------|---------|-----|--------|--------|
| R246 | 0 | 0 | 0 | 50 | 0.2346 | -0.0917 | OK |
| R247 | 0.0056 | 0 | 0 | 50 | 0.2347 | -0.0917 | OK |
| R253 | 0 | 0.0056 | 0 | 50 | 0.2348 | -0.0917 | OK |
| R254 | 0 | 0 | 100 | 50 | 0.2655 | -0.0878 | OK |
| **R258** | **0** | **0** | **100** | **0** | **0.0100** | **-0.2228** | **COLLAPSE** |
| R251 | 0.0056 | 0.0056 | 100 | 50 | 0.2662 | -0.0878 | OK |
| R248 | 1.0 | 1.0 | 100 | 50 | 0.0100 | -0.2259 | COLLAPSE |

R258 collapse mirror image of R248: completely different paper-term
configurations, identical degenerate attractor (geo=0.01, cum_rf≈-0.22).

## Mechanism — reward hacking via collective drift

Training-log evolution (full data in CLM-0480):

| Episode | Best ckpt? | Reward | Actions mu | Eval geo |
|---------|-----------|--------|------------|----------|
| 9 | no | -77.8 | [-0.01, -0.03, 0.01, -0.02] | n/a |
| **29** | **YES** | **-0.5** | **[0.01, 0.13, -0.03, -0.01]** | **0.0100** |
| 39 | no | -9.6 | [0.07, 0.24, -0.01, 0.03] | n/a |
| 59 | no | -8.1 | [0.76, 0.86, -0.01, 0.52] | n/a |
| 69 | no | -0.7 | [0.83, 0.87, 0.01, 0.40] | n/a |

The "best ckpt" (saved at ep 29, used for final-eval) has Actions mu ≈ 0
— a near-NO-CONTROL policy. Training reward -0.5 reflects "if I do
nothing, sync residual is small (system reaches natural equilibrium)".
But eval geo = 0.000 because the system has huge un-damped transient.

After ep 29, the actor drifts toward [0.8, 0.9, 0, 0.4] (homogeneous
positive bias — same drift in 3 of 4 agents → low sync residual via
different reward-hack mechanism: collective drift). Training reward stays
near-zero but eval would also collapse.

**Without phi_abs, the only gradient signal toward physical damping is
GONE**. r_f rewards "all agents agree" not "frequency is stable". The
actor finds the cheapest "agree" solution (do nothing, or all drift
together) and exits the meaningful policy space.

## Pre-registered outcomes (R258 hypothesis test)

| Outcome class (pre-registered) | Threshold | Actual |
|--------------------------------|-----------|--------|
| STRONG WIN | cum_rf < -0.05 AND geo > 0.20 | **NOT met** |
| PARTIAL WIN | -0.07 < cum_rf < -0.05 AND geo > 0.20 | NOT met |
| NEUTRAL | -0.09 < cum_rf < -0.07 AND geo ≈ 0.20-0.27 | NOT met |
| COLLAPSE | cum_rf > -0.09 OR geo < 0.10 | **MET (geo=0.01, cum_rf=-0.22)** |

Outcome: COLLAPSE class. Following gate: "close path; pivot R259 to
warm-start path".

## R259 candidate space (post-R258)

| Candidate | Status |
|-----------|--------|
| (a) LAMBDA_SMOOTH > 0 | REFUTED (R257) |
| (a') LAMBDA_SMOOTH < 0 | DEAD (R50/R55/R81) |
| (b) phi_abs=0 sync-only | **REFUTED (R258)** |
| (b') Magnitude penalty (-λ\|a\|²) new reward term | requires env code; speculative |
| **(c) Hybrid RL+droop warm-start** | **only remaining mechanism-valid path** |
| (d) Proportional-bias actor architecture | speculative, 1-2 day env |

Recommended R259 = (c) warm-start, ~1 day infra + 13 min train. Higher
investment than R258's single-flag flip.

## Alternative — stop research, write paper draft

R255→R258 four-round chain has now fully characterized the RL cum_rf
plateau:

1. **Pareto trade-off** (CLM-0445): RL wins 11-axis (transient quality),
   droop k=10 wins cum_rf (sync) — neither dominates.
2. **Over-actuation** (R256/CLM-0470): RL mean|dD|=563 vs droop=421,
   25% over.
3. **Smoothness inversion** (R257/CLM-0475): RL is 3× SMOOTHER than droop
   k=10; cum_rf winner is jittiest.
4. **phi_abs structural** (R258/CLM-0480, NEW): sync-only reward is
   reward-hackable via "all drift together"; phi_abs is the unique
   anchor to physical damping.

Paper Sec.IV-D could now claim 6 contributions:
1. Pareto frontier RL-vs-classical (CLM-0445)
2. Dual-metric audit corrections (CLM-0186, CLM-0430)
3. Robustness story (R210-R220 series)
4. Reward decomposition (R254/CLM-0455)
5. Reward landscape characterization (R248/R246 + R258 extension)
6. **phi_abs structural stabilizer + reward-hacking finding** (R258, NEW)

This is publishable without R259 hybrid warm-start. The mechanism story
is now complete.

## Pre-registered outcomes review

The COLLAPSE outcome was anticipated as one of the 4 outcome classes in
the plan. The pre-registration discipline paid off: rather than ad-hoc
post-hoc framing of "why did training collapse?", we have the gate
condition pre-met and the mechanism (reward hacking + Actions mu trace)
captured cleanly.

## Questions opened (this round)

- (none — R258 hypothesis cleanly closed; R259 routing to warm-start
  is documented but not a question entity)

## Questions closed (this round)

- "Does RL trained with sync-only reward (CLM-0445 paper-7th-contribution
  candidate, direct-removal approach) beat droop k=10 on cum_rf?"
  ANSWERED: NO. Direct removal of phi_abs causes reward-hacking via
  "all agents drift together"; full collapse on geo + cum_rf.

## Questions advanced (this round, status unchanged)

- "What IS the mechanism of the RL cum_rf plateau?" advanced from
  "smooth-but-loud RL vs reactive-and-titrated droop" (R256+R257) to
  "+ phi_abs is structural anchor — any path removing it for sync
  prioritization will reward-hack". The cum_rf gap requires either
  hybrid warm-start (paper 7th contribution candidate c) or
  acceptance of the Pareto frontier as a fundamental policy-class
  trade-off.

## 给 PI 的话

**这周干了啥**：R255-R257 三轮 probe-first 把 cum_rf plateau mechanism
narrow 到 "RL smooth-but-loud vs droop k=10 reactive-and-titrated". R258
是这 session 的第一次实际训练 — 测 CLM-0445 paper-7th-contribution 候选
"训练 RL 用 droop k=10 reward philosophy (sync-only, phi_abs=0)". 13 min
ANDES WSL train.

**结果（一句话）**：**COLLAPSE** — geo **0.0100**, cum_rf **-0.2228**,
跟 R248 paper-strict 一摸一样的 collapse signature. phi_abs 是 **structural
stabilizer 不是装饰**, 拿掉之后 RL reward-hack via "all agents drift
together" 退化策略.

**意外**：
1. **R258 跟 R248 collapse 完全一致** — 两个完全不同的 reward config
   (R248 phi_h=phi_d=1.0 over-penalty; R258 phi_abs=0 missing-anchor)
   都 hit 同一个 geo=0.0100 / cum_rf≈-0.22 attractor. Mechanism: 都让
   actor 找到 "do nothing" 或 "all drift together" 的 reward-hack.
2. **Best ckpt 是 near-no-control policy** — ep 29 Actions mu = [0.01,
   0.13, -0.03, -0.01], 训练 reward -0.5 看着很好, 但 eval geo = 0.000
   on both LS1/LS2. r_f 只奖励 "agree", 不奖励 "stabilize", 所以 "do
   nothing" 是 r_f 局部最优.
3. **phi_abs 是 V4 设计的关键安全网** — paper Eq.14 (只有 r_h, r_d, r_f)
   数学上 REWARD-HACKABLE, V4 加 phi_abs (Kundur tight-coupling patch)
   不是装饰是 anchor. 这是 paper Sec.IV-D 第 6 contribution 候选.
4. **Probe-first chain 工作得很好** — R255 (refute mismatch) → R256
   (refute saturation, surface over-actuation) → R257 (refute jitter,
   inversion insight) → R258 (refute direct phi_abs removal, surface
   reward-hacking). 每轮都 narrow mechanism + 加 paper contribution
   candidate.

**Paper Sec.IV-D 现在 6 contribution 候选**：Pareto frontier, dual-metric
audit, robustness story, reward decomposition, reward landscape, 以及
**phi_abs structural anchor + reward-hacking finding (R258 NEW)**.

**我默认下一步做**：R259 只剩 hybrid RL+droop warm-start (CLM-0470
candidate c) 这条 mechanism-valid training path, 但要 ~1 day infra + 13 min
train. 更推荐 stop research 写 paper draft；R258 reward-hacking finding 已经
补上第 6 contribution.

**你想插一脚就说**：4/4 probe-first/training-first 协议 textbook 示范.
Paper Sec.IV-D mechanism story 4 层叠加 (Pareto + over-actuation +
smoothness inversion + phi_abs anchor + reward-hacking) 完整. **强烈推荐
stop research 写 paper draft** — R259 warm-start 需要 1 day infra, ROI
比 直接 paper 写 低. 不然 R259 是唯一 mechanism-valid 路径.

## Cross-references

- CLM-0445 (R252 — paper-7th-contribution candidate explicitly proposed)
- CLM-0455 (R254 — phi_f=100, phi_abs=50 → geo=0.2655 baseline)
- CLM-0470 (R256 — over-actuation mechanism)
- CLM-0475 (R257 — smoothness inversion mechanism)
- CLM-0480 (this round's claim — reward hacking + phi_abs structural)
- R246 plan/verdict (phi_abs only → geo=0.2346)
- R248 plan/verdict (paper-strict phi_h=phi_d=1.0 → geo=0.0100 collapse)
- R254 plan/verdict (phi_f-only → geo=0.2655 baseline)
- `results/r258_w1_scalar_phif_only_no_phiabs_s50/final_eval_summary.json`
- `results/r258_w1_scalar_phif_only_no_phiabs_s50/training_log.json`
- `docs/paper_drafts/sec_iv_d_paper_eq14_gauge_invariance.md`
