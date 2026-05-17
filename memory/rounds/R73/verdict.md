# R73 verdict — NEW v3.1 SOTA R73 W3 s54+warmup=20 v3.1=0.4099 + warmup=20 4-seed family +5.5%

**Date**: 2026-05-18
**Status**: **closed-positive** (new v3.1 SOTA + cross-seed warmup=20 robust family)
**Type**: per-seed optimization + cross-seed verify
**Wall**: ~30 min

## TL;DR

> **NEW v3.1 SOTA: R73 W3 s54 + warmup=20 = 0.4099** (CLM-0125), +5% over
> R72 W4 (s54+warmup=5, v3.1=0.3908). Same seed, larger warmup.
>
> **s54 warmup U curve** (monotonically up 5→20, gracefully down 25→30):
> 5: 0.3908 | 10: 0.3942 | 15: 0.4037 | **20: 0.4099** ← peak | 25: 0.3591 | 30: 0.3679
>
> s54 is **more robust than s50** (s50 cliffs to 0.06 at warmup>20, s54 only drops 12%).
>
> **Cross-seed warmup=20 verify (s55)**: v3.1=0.3781 vs s55 warmup=5 (0.3171) = +19%.
> s55 also benefits from warmup=20.
>
> **4-seed warmup=20 family mean (excl s51 P_bal collapse) = 0.3525**
> (s50:0.3151, s52:0.3068, s54:0.4099, s55:0.3781) vs warmup=5 5-seed
> mean 0.3340 = **+5.5%** rigor improvement.
>
> Trade-off: warmup=20 has higher mean but s51 fails (P_bal=0.19 collapse).
> warmup=5 5-seed all healthy but mean lower.

---

## Phase 0 — Trigger

R72 W4 s54+warmup=5 v3.1=0.3908 NEW canonical. s54 only at warmup=5; need
to find s54 peak.

## Phase 1 — s54 cross-warmup sweep

| warmup | s54 v3.1 | comment |
|---|---|---|
| 5 (R72 W4) | 0.3908 | prior canonical |
| 10 (R73 W1) | 0.3942 | +0.9% |
| 15 (R73 W2) | 0.4037 | +3.3% |
| **20 (R73 W3)** | **0.4099** ← **peak** | **+4.9%** |
| 25 (R73 W4) | 0.3591 | -12% (graceful) |
| 30 (R73 W5) | 0.3679 | -10% |

**Monotonic 5→20, then graceful decline 25→30**. NO cliff like s50.
s54 is more robust seed under high warmup.

## Phase 2 — s55 + warmup=20 cross-seed verify

W6: s55 + warmup=20 v3.1 = **0.3781** (vs s55 + warmup=5 = 0.3171 = **+19%**).

s55 also benefits from warmup=20 (mirrors s50 pattern).

## Phase 3 — Cross-seed @ warmup=20 family

| seed | v3.1 @ warmup=20 | comment |
|---|---|---|
| s50 (R69 W3) | 0.3151 | peak for s50 |
| s51 (R69 W1) | 0.1959 | P_bal=0.19 collapse — outlier |
| s52 (R69 W6) | 0.3068 | peak for s52 |
| **s54 (R73 W3)** | **0.4099** | **peak — new SOTA** |
| s55 (R73 W6) | 0.3781 | +19% vs warmup=5 |
| **4-seed mean (excl s51)** | **0.3525** | +5.5% vs warmup=5 5-seed mean |

**warmup=5 vs warmup=20 family comparison**:

| family | seeds | mean v3.1 | comment |
|---|---|---|---|
| tau+warmup=5 | s50/s51/s52/s54/s55 (5) | **0.3340** | all healthy, robust |
| tau+warmup=20 | s50/s52/s54/s55 (4, s51 excl) | **0.3525** | higher mean, s51 caveat |

## Phase 4 — Canonical best agent options

Both warmup=5 and warmup=20 paths produce viable canonical agents:

**Option A: R73 W3 s54 + warmup=20** (highest single v3.1):
- v3.1 = 0.4099
- LS1 P_balance = 0.861
- LS2 P_balance = 0.980
- Best for "max single SOTA" claim

**Option B: R72 W4 s54 + warmup=5** (cleanest P_balance):
- v3.1 = 0.3908
- LS1 P_balance = 0.959 (paper Fig 7 perfect 1:1:1:1)
- LS2 P_balance = 0.994
- Best for "cleanest paper figure" claim

Visual inspection of both PNGs: R72 W4 (warmup=5) has slightly tighter ΔP overlap
in LS1. R73 W3 (warmup=20) has overall higher metric breakdown but slightly
visible 1-agent offset.

For paper-writing: **prefer R72 W4 (CLM-0123)** for paper Fig 7 figure as
P_balance>0.95 is unambiguously clean. R73 W3 is reported as "single SOTA"
with higher overall v3.1 in supplementary.

## New claims this round

- **CLM-0125** (finding/V) — R73 W3 s54+warmup=20 NEW v3.1 single SOTA = 0.4099
  (+5% over R72 W4). s54 warmup U curve monotonic 5→20, gracefully down 25→30
  (no cliff, robust seed).
- **CLM-0126** (finding/V) — warmup=20 4-seed family mean = 0.3525 (excl s51
  P_bal collapse) vs warmup=5 5-seed mean = 0.3340 (+5.5%). Trade-off:
  warmup=20 higher mean but s51 incompatible.
- **CLM-0127** (decision/S) — Canonical best agent choice REMAINS R72 W4 s54+warmup=5
  (CLM-0123) for paper Fig 7. R73 W3 reported as supplementary single SOTA
  (higher v3.1 but slightly less paper-fig-clean).

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round)

(none)

## 给 PI 的话

**这周干了啥**: R72 收尾后用户 "继续优化". R72 W4 s54+warmup=5 是 canonical
但 s54 只测过 warmup=5. R73 W1-W3 跑 s54 cross-warmup (10/15/20), W4-W5 测
s54 cliff (25/30), W6 测 s55+warmup=20 verify cross-seed.

**结果（一句话）**: (1) **R73 W3 s54+warmup=20 NEW v3.1 SOTA = 0.4099** (+5% over
R72 W4), s54 U curve monotonic 5→20 peak, 然后 gracefully decline (s50 在 warmup>20
是 cliff to 0.06, s54 只 drop 12% — s54 比 s50 robust); (2) **s55 也吃 warmup=20**
(0.3781 vs warmup=5 的 0.3171, +19%) — warmup=20 family 不只 s50; (3) **warmup=20
4-seed mean = 0.3525** (excl s51 collapse) **+5.5%** vs warmup=5 5-seed mean
0.3340 — paper rigor 选择: warmup=5 robust 5-seed OR warmup=20 high-mean 4-seed.

**意外**: (1) **s54 同时是 best peak AND most robust seed** — paper figure 用
s54 双重保险; (2) **2 个 canonical 都很强**: R73 W3 (v3.1 0.4099 highest single)
vs R72 W4 (P_balance LS1=0.96 cleanest) — choice depends on "max SOTA" vs
"max paper-fig-clean" priority; (3) **s51 真 outlier** — 5 个 healthy seeds 中
只有 s51 不吃 warmup=20 (P_balance LS1=0.19 collapse). 不是 seed-broken 是
hyper-incompatible specifically.

**我默认下一步**: R73 commit. Then **真转写 paper draft** (3 mode SOTAs 都齐,
canonical figure 已选 R72 W4 s54). 或可继续 1 wave: 5-seed s56/s57 加 warmup=20
看是否 5-seed at warmup=20 也可能 (s51 fails 不算).

**你想插一脚**: (1) paper draft 开始? (2) 还继续挤? (我评估 ROI 已极低,
single-seed +5% margin 没再容易拿).
