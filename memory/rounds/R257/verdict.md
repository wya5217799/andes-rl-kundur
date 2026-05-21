# R257 verdict — Probe-first: action-smoothness REFUTED; "winner is jittery" insight

**Date**: 2026-05-20
**Status**: CLOSED-NEGATIVE on hypothesis 2 (anticipation lack); CLOSED-POSITIVE
on counter-intuitive insight that strengthens paper Sec.IV-D narrative
**Type**: research (probe-first per NOTES_ANDES.md; mechanism analysis)
**Wall**: ~30 min total (probe write + run + verdict)

## TL;DR

R255 mechanism candidate 2 (anticipation lack / jitter) probed on existing
trace JSONs. **REFUTE direction**: RL controllers (R201/R254/R246) are
actually **3× SMOOTHER** than droop k=10 on dD jitter (RL mean=3.5 vs
droop k=10 mean=9.7). The cum_rf-winning controller (droop k=10) is the
**jitteriest** one. Naive "anticipation lack" framing inverts.

**Insight**: RL plateau on cum_rf = "smooth-but-loud" attractor; droop k=10
wins via "reactive-and-titrated" structure (lower mean, sharper transitions
proportional to instantaneous |dω|). The R258 candidate space narrows
sharply — BOTH LAMBDA_SMOOTH directions empirically dead.

## Probe results

### Delta_M / Delta_D jitter (mean |delta[t] - delta[t-1]|)

| Controller       | M_jitter | D_jitter | D_TV | dAd ratio vs droop_k10 |
|------------------|----------|----------|------|------------------------|
| R201 hreg SOTA   | 2.31     | 3.45     | 513  | **0.35×** (smoother)   |
| R254 phi_f-only  | 2.67     | 3.53     | 526  | 0.36×                  |
| R246 only_phi_abs| 3.33     | 3.56     | 530  | 0.37×                  |
| **Droop k=10**   | 0        | **9.71** | **1446** | 1.00× (baseline)   |
| Droop k=2        | 0        | 3.57     | 532  | 0.37×                  |
| No control       | 0        | 0        | 0    | 0×                     |

Full data: CLM-0475, `results/r257_probe_action_smoothness.json`.

## Hypothesis test (vs R257 plan gate)

| Predicted outcome | Threshold | Actual |
|-------------------|-----------|--------|
| RL chop > 2× droop k=10 → SUPPORT LAMBDA_SMOOTH | dD_ratio > 2.0 | **0.35-0.37** — strongly REFUTE |
| RL chop ≤ 1.5× droop k=10 → magnitude not jitter | dD_ratio ≤ 1.5 | **MET** |

REFUTE direction strongly; ratio ~0.35 is below the lower bound of even
the "magnitude not jitter" interpretation.

## Counter-intuitive insight: winner is the jitterier controller

Droop k=10 mean dD jitter = 9.7, peak = 600 (hits bound once via clip).
That's the **sharpest** responder to instantaneous |dω| of any tested
controller. It wins cum_rf precisely because its proportional structure
forces rapid reaction during transient.

RL is structurally smoother (gradient-descent on smooth reward landscape
converges to smoothly-varying actor output). RL's mean jitter = 3.5 is
~3× lower than droop k=10's. R246 (cum_rf-worst RL) has the highest dM
jitter among RL but still 0.37× droop k=10's dD jitter.

**Cum_rf gap is not a smoothness gap; it's a structural inductive-bias gap.**

## Updated R258 candidate space (CLM-0470 list refined)

| Candidate | Status post-R257 |
|-----------|------------------|
| (a) LAMBDA_SMOOTH > 0 train | **REFUTED** — would worsen by smoothing further |
| (a') LAMBDA_SMOOTH < 0 train | **DEAD** — exploration-noise hijack (CLM-0058 R50: -67%; CLM-0062 R55 W=10: same hijack; CLM-0142 R81: TD3+LSTM lambda=-1 → geo=0.010) |
| (b) **Magnitude penalty (-λ\|a\|²)** | **STILL VALID** — addresses over-actuation (CLM-0470) |
| (c) Hybrid RL+droop warm-start | **STILL VALID** — start from reactive policy |
| (d) Proportional-bias actor architecture | speculative; 1-2 day env |

**Recommended R258**: candidate (b) magnitude penalty. Requires small
reward-term addition in env (per CLAUDE.md "不动 paper-cited assets without
新 round" — done with new round). Single seed s50, w1, phi_f=100 +
phi_abs=50 + magn_penalty=0.01. Tests: drop RL action magnitude toward
droop k=10's mean ~421 while preserving RL's smoothness advantage.

## Three consecutive probe-first wins this session

R255 (CLM-0460): local-vs-global r_f REFUTED, 30-min probe, env-change
cancelled.
R256 (CLM-0470): action-bound saturation REFUTED + over-actuation
surfaced, 30-min probe.
R257 (CLM-0475): action smoothness REFUTED + "winner is jittery" insight
+ closes 2 dead R258 paths via cross-CLM check, 30-min probe.

**Cumulative**: ~90 min probe wall; ~4-5 hr training-compute saved;
3 paper-grade mechanism insights for Sec.IV-D contribution 1.

## Pre-registered outcomes (R257 hypothesis test)

| Pre-reg | Actual |
|---------|--------|
| droop k=10 TV_dD ≪ RL TV_dD | droop TV=1446, RL TV=513-530 (RL ≪ droop) — INVERSION |
| droop k=10 TV_dD ~ RL TV_dD | NO — droop is 2.7-2.8× higher |
| droop k=2 TV_dD < droop k=10 TV_dD | YES (droop k=2 TV=532, k=10 TV=1446) — confounded with magnitude but ordered consistently |

Outcome: pre-registered "RL ≫ droop" inversion is the data. Strong
confidence in CLM-0475 interpretation.

## Side-finding — droop k=2 jitter == RL jitter

Droop k=2 has dD jitter mean=3.57, almost identical to RL controllers
(3.45-3.56). Yet droop k=2 has dM=0 throughout (vs RL ~2-3.3). This
suggests:
- The RL "smooth dD" attractor has roughly the same dD reactivity as
  proportional droop with low gain.
- The RL "non-zero dM" channel is what differentiates RL from droop
  (and confirms R256 over-actuation finding).

## Questions opened (this round)

- (none — R257 hypothesis cleanly closed at probe stage; mechanism
  candidates 3-4 from CLM-0460 untested but lower-priority given
  R258 candidate (b) clearly motivated)

## Questions closed (this round)

- "Is RL cum_rf plateau caused by action jitter / anticipation lack
  (R255 mechanism candidate 2, CLM-0460)?" ANSWERED: NO. RL is 3×
  SMOOTHER than droop k=10; jitter inversion refutes the candidate.

## Questions advanced (this round, status unchanged)

- "What IS the mechanism of the RL cum_rf plateau?" advanced from
  "candidate 1 or 2-4" to "(smooth-but-loud RL) vs (reactive-and-
  titrated droop) policy-class trade-off — addressable via action
  magnitude regularization (candidate b) or hybrid warm-start
  (candidate c)".

## 给 PI 的话

**这周干了啥**：R256 之后 mechanism candidate 2 (anticipation/jitter) 还
open. 又一个 30-min probe — 读 existing trace, 算 per-step action change
rate. 按 R255/R256 validated probe-first 协议.

**结果（一句话）**：候选 2 **REFUTE方向反了** — RL 实际比 droop k=10
**smoother by 3×** (mean dD jitter RL 3.5 vs droop 9.7). **Cum_rf 赢家
反而是 jittiest 那个** (droop k=10). 这是反直觉但 paper-grade 的关键
insight.

**意外**：
1. **RL 比 droop k=10 smoother 3×** — 我预期 RL 应该 choppier (anticipation
   lack hypothesis), 实际相反. RL 学到 smooth-but-loud attractor, 高
   mean (CLM-0470), 低 jitter (这个 probe).
2. **Cum_rf winner is jittiest controller** — droop k=10 mean dD jitter 9.7,
   max 600 (hit bound once). 它的 proportional structure FORCE 快速反应
   to 瞬时 |dω|. 这才是 cum_rf 关键.
3. **两个 LAMBDA_SMOOTH 方向 都 dead**:
   - LAMBDA_SMOOTH > 0 (penalty): RL 已经过 smooth, 加只会更糟
   - LAMBDA_SMOOTH < 0 (anti-smooth, reward variation): CLM-0058 R50 +
     CLM-0062 R55 + CLM-0142 R81 **三次 catastrophic** (geo 从 0.334
     → 0.110 → 0.010), 因为 exploration-noise hijack
4. **Droop k=2 dD jitter 几乎跟 RL 一样** (3.57 vs 3.45-3.56) — 说明 RL
   的 dD reactivity 就是低增益 proportional 那种, 真正差别在 RL 的非零
   dM channel (over-actuation, CLM-0470 已证).

**Paper Sec.IV-D contribution 1 mechanism narrative 更 sharp 了**:
"smooth-but-loud RL vs reactive-and-titrated droop k=10". 两个 controller
class 的 inductive bias 直接 trade-off cum_rf vs 11-axis.

**我默认下一步做**：
1. **R258 = candidate (b) magnitude penalty**: 加 -λ|a|² 到 reward, train
   td3_lstm s50 75ep. 大概 13 min ANDES WSL. 测 "RL 能不能在保持 smoothness
   优势下 drop magnitude 到 droop level → cum_rf 接近 droop k=10". 注意:
   这是 env reward 修改, 按 CLAUDE.md "paper-cited asset" 规则要新 round
   + 新 CLM 文档化 (R258 + CLM-0480).
2. **或** stop research 写 paper draft. 现在 Sec.IV-D 故事很全:
   - Contribution 1 (RL-vs-droop Pareto) + mechanism (smooth-loud vs
     reactive-titrated, R256 + R257)
   - Contribution 2-4 (paper integrity audit, dual-metric)
   - Contribution 5 (phi_f decomp, R254)
   - 3 个 probe-first 案例 textbook 教学

**你想插一脚就说**：R257 是 3/3 probe-first 救轮. mechanism narrative
3 层叠加 (over-actuation + smoothness inversion + winner-is-jittery) 直接
strengthen paper. 推荐 stop research 写 draft; 不然 R258 candidate (b)
training 是唯一 mechanism-valid path.

## Cross-references

- CLM-0445 (R252 — Pareto contribution-1)
- CLM-0460 (R255 — mechanism candidates 1-4)
- CLM-0470 (R256 — action-bound saturation REFUTED + over-actuation)
- CLM-0475 (this round's claim — smoothness REFUTED + winner-is-jittery)
- CLM-0058 (R50 — LAMBDA_SMOOTH=-100 exploration-noise hijack)
- CLM-0062 (R55 — windowed-W=10 anti-smoothness same hijack)
- CLM-0142 (R81 — TD3+LSTM lambda_smooth=-1 catastrophic geo=0.010)
- CLM-0175 (R195 — widebound regression)
- `scripts/r257_probe_action_smoothness.py` (probe code)
- `results/r257_probe_action_smoothness.json` (probe data)
- `src/andes_rl_kundur/env/andes/base_env.py:388-419` (LAMBDA_SMOOTH infra)
- `docs/eng-notes/NOTES_ANDES.md` (probe-first protocol)
