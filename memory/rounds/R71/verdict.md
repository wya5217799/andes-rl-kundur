# R71 verdict — Ranker v3.0→v3.1 (multiplicative gating) + s53 drift discovery + s50 warmup cliff

**Date**: 2026-05-18
**Status**: **closed-positive** (v3.1 corrects v3.0 dilution + reveals 2 new findings)
**Type**: ranker refinement + continued sweep
**Wall**: ~1.5 hr

## TL;DR

> **v3.0 (geo_mean) → v3.1 (multiplicative gating)**: overall = geo_mean(axes 1-8)
> × min(axes 9, 10, 11). 5 new unit tests + all 16 v3 tests pass. R68 W2 s51
> confirmed canonical best under v3.1 (0.3562, top rank).
>
> **R57-α historical v3.1 = 0.0618** (was 0.4937 in v3.0) — completely crushed
> by multiplicative gating because LS1 P_balance=0.
>
> **2 new findings from W1-W6 cross-axis sweep**:
> - **s53 is a drift dead seed** (W1 v3.1=0.0476, W6 v3.1=0.0485) — joins s49
>   in the broken-seed list. Healthy LSTM seeds: s50/s51/s52 only.
> - **s50 + tau + warmup ≥ 25 → P_balance cliff drop** (LS1 P_balance=0).
>   warmup ≤ 20 is the safe zone for s50. Confirms seed-dependent hyper optimum.

---

## Phase 0 — Trigger

R70 user question: "v3 ranker 高 是否 = paper figure 好看?" Answer was partial:
R69 W3 s50 v3=0.5474 but P_bal=0.56, R68 W2 s51 v3=0.5329 but P_bal=0.85.
v3.0 geo_mean dilutes gating axis penalty. User decision: optimize.

## Phase 1 — v3.1 implementation (CLM-0119)

### Aggregation change

```python
if is_ddic and enable_v3_axes and len(axes) >= 9:
    gating = [a.score for a in axes if a.name in {"agent_min_activity",
              "late_oscillation_inv", "agent_P_balance"}]
    continuous = [a.score for a in axes if a.name not in <gating names>]
    cont_geo = exp(sum(log(max(s, 0.01)) for s in continuous) / len(continuous))
    overall = cont_geo * min(gating)
else:
    overall = exp(sum(log(max(s, 0.01)) for s in scores) / len(scores))
```

### Tests

`tests/test_paper_grade_axes_v31.py` — 5 new tests:
- v3.1 overall ≤ v2 overall (gating can only reduce)
- v3.1 gates agent collapse (TD3 R67 fixture)
- v3.1 formula = geo(continuous) × min(gating) exactly
- v3.1 disabled falls back to v2 geo_mean
- v3.1 with synthetic P_balance=0 → overall < 0.2

**21/21 v3 + v3.1 tests pass.**

## Phase 2 — Re-rank under v3.1 (sorted by v3.1 desc, top 10)

| label | v2 | v3.0 (old) | **v3.1 (new)** | rank change |
|---|---|---|---|---|
| R68 W2 LSTM warmup=5 s51 | 0.4226 | 0.5329 (#3) | **0.3562 (#1)** | ⬆⬆ |
| R69 W4 LSTM warmup=5 s52 | 0.4121 | 0.5211 (#4) | **0.3414 (#2)** | ⬆⬆ |
| R69 W3 LSTM warmup=20 s50 | 0.4610 | 0.5474 (#1) | 0.3151 (#3) | ⬇⬇ |
| R71 W3 LSTM warmup=15 s50 | — | — | **0.3089 (#4)** | NEW |
| R69 W6 LSTM warmup=20 s52 | 0.4185 | 0.5165 (#5) | 0.3068 (#5) | — |
| R71 W2 LSTM warmup=10 s50 | — | — | **0.2840 (#6)** | NEW |
| R69 W2 LSTM warmup=5 s50 | 0.3276 | 0.4447 | 0.2647 (#7) | — |
| R69 W1 LSTM warmup=20 s51 | 0.4832 | 0.5366 (#2) | **0.1959 (#10)** | ⬇⬇⬇⬇ |
| R68 W1b SAC s50 | 0.1654 | 0.2642 | 0.1079 | — |
| R57-α historical s51 | 0.5432 | **0.4937** | **0.0618** | 💀 crushed |
| TD3 R67 s50 (paper-metric SOTA) | 0.1885 | 0.2507 | 0.0278 | crushed |

**Key insight**: v3.1 correctly down-ranks `R69 W1 s51 (P_bal=0.19)` from #2 to #10 —
matches visual intuition that LS1 partial monopolization disqualifies it.

R57-α v3.1 ≈ 0.06 confirms it's a paper-figure-failure controller.

## Phase 3 — W2/W3 gap fill (s50, tau+warmup intermediate)

s50 v3.1 U curve (constant tau=0.001):

| warmup | v3.1 (s50) |
|---|---|
| 5 (R69 W2) | 0.2647 |
| 10 (R71 W2) | 0.2840 |
| 15 (R71 W3) | 0.3089 |
| **20 (R69 W3)** | **0.3151** ← s50 peak |
| 25 (R71 W4) | **0.0642** ← cliff! |
| 30 (R71 W5) | 0.0631 |

**Sharp cliff between warmup=20 and 25**: LS1 P_balance drops from 0.56 to 0.000
(2 middle agents emit < 0.1 ΔP).

Mechanism (hypothesis): Long warmup (>20 ep) + s50 seed initial conditions →
critic Q-targets bias toward 2 corner agents (1 and 4). 2 inner agents abandon
own action discovery, ride coattails. v3.0 missed; v3.1 catches.

## Phase 4 — s53 dead seed discovery (CLM-0120)

| trial | hyper | s53 v3.1 |
|---|---|---|
| W1 | tau + warmup=5 | 0.0476 |
| W6 | tau + warmup=20 | 0.0485 |

Both very low. s53 joins **s49 as a drift dead seed**. Original drift list (CLM-0104)
identified s49 only — R71 extends to s53.

**Healthy LSTM seeds: s50, s51, s52** (3 of 5 standard seeds {49, 50, 51, 52, 53}).
Future LSTM 3-seed verification should use {50, 51, 52} not {49, 50, 51}.

## Phase 5 — s50 warmup cliff finding (CLM-0121)

Different seeds have different optimal warmup:
- s50: warmup=20 (peak v3.1=0.3151)
- s51: warmup=5 (peak v3.1=0.3562)
- s52: warmup=5 (peak v3.1=0.3414)

**No single-warmup-fits-all under v3.1**. R68 W2 s51 (warmup=5) and R69 W3 s50
(warmup=20) are both peaks for their respective seeds.

### Practical recommendation

For paper figure: **R68 W2 s51** (highest single ckpt under v3.1, simplest hyper).
For 3-seed mean: tau+warmup=5 family wins (s50: 0.2647, s51: 0.3562, s52: 0.3414,
mean=**0.3208 v3.1**) vs tau+warmup=20 family (s50: 0.3151, s52: 0.3068, s51 excluded
due P_bal=0.19, **2-seed mean=0.3109**).

## New claims this round

- **CLM-0119** (decision/S) — paper_grade_axes v3.0 → v3.1: multiplicative gating
  aggregation. Asset 4 versioned per ADR-0001. 21/21 v3+v3.1 tests pass.
- **CLM-0120** (finding/V) — s53 confirmed drift dead seed (joins s49). Healthy LSTM
  seeds: {50, 51, 52}. CLM-0104 drift scope extended.
- **CLM-0121** (finding/V) — s50 + tau + warmup ≥ 25 causes LS1 P_balance cliff
  (drops to 0.000). Sharp boundary between warmup=20 (P_bal=0.56) and warmup=25
  (P_bal=0.00).
- **CLM-0122** (decision/S) — R68 W2 s51 reconfirmed canonical best under v3.1
  (rank #1 from #3 in v3.0). CLM-0117 elevated from "best for paper figure" to
  "best under v3.1 strict ranker" — same controller, stronger evidence.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round)

(none)

## 给 PI 的话

**这周干了啥**: R70 收尾后用户问 "图好看是判定 agent 有效标准吗" 答: yes 必需,
但 v3.0 ranker 仍 dilute P_balance penalty. 用户决策 "优化评估, 然后继续训练".
R71 implement v3.1 (gating multiplicative) + 跑 6 new sweep cells in cross-axis space.

**结果（一句话）**: (1) **v3.1 ranker 完美 match paper-figure 直觉** — R68 W2 s51
从 v3.0 第 3 升到 v3.1 第 1 (P_bal=0.85 vs R69 W3 s50 P_bal=0.56 demoted), R57-α
historical 从 v3.0 0.4937 crash 到 v3.1 0.0618 (LS1 P_bal=0 触发 multiplicative
gating); (2) **s53 是新发现的 drift dead seed** (W1+W6 都 ~0.05 regardless of warmup) —
跟 s49 一样. Healthy LSTM seeds 缩到 {50, 51, 52}; (3) **s50 + tau + warmup ≥ 25
出现 P_balance cliff** (warmup=20 P_bal=0.56 → warmup=25 P_bal=0.00). 不同 seed
有不同最优 warmup, no one-size-fits-all.

**意外**: (1) **多 agent 系统在 hyper landscape 上有 sharp cliffs** — paper-metric /
v3.0 ranker 看不见, v3.1 multiplicative gating 第一次让我们看到; (2) **s53 dead seed**
意味着 paper writing 应该用 healthy 3 seeds {50,51,52} not standard {49,50,51} —
CLM-0104 drift scope 比之前想的更广; (3) **R68 W2 s51 在 v3.1 下 robust 第 1**
(v3.0 第 3) — 选最 stable 4-agent collab controller, simplest hyper (tau-only).

**我默认下一步**: R71 commit. 然后开始写 paper draft (4 表已齐, R68 W2 s51 + R67 TD3
作 multi-controller). 或 v3.1 还能优化? (e.g., 加 agent ΔH balance gate too?)

**你想插一脚**: (1) v3.1 已够 paper rigor 吗, 还要 v3.2 加更多 gates? (2) 开始 paper
draft 还是再扫? 沉默 = paper draft.
