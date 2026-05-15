# R24 — V4_h50_s49 0.613 = Single-Seed Cherry-Pick 确认 (R23 v3 + 另一 session 多 seed 数据综合)

**Date**: 2026-05-07
**Phase**: V4_h50_s49 0.613 robustness 验证 (用户睡期间)
**Wall**: ~6 min (R23 v3 single train) + 2 min (eval) + 综合分析
**Status**: ❌ **R21 verdict 0.613 不可复现** — H₀ 在 [40, 70] 区间多 seed × 多 H₀ scan 全部收敛到 6-axis ≈ 0.13-0.22 attractor, 仅 H₀=50 s49 75ep best ckpt 0.613 是 outlier
**Trigger**: 用户战略转向 "ANDES 成功为核心, 效果至上, 想超过 V1", 我做 R23 v3 single train 验证 H₀=70 + 综合另一 session v4_3/v4_4 multi-seed 数据
**前置**: `quality_reports/research_loop/round_23_verdict.md` (R23 试错 + ANDES contention diagnosis)

---

## TL;DR

我做的 R23 v3 (H₀=70 s49 50ep) + 另一 Claude session 跑的 v4_3 H₀ ∈ {40, 50, 60} multi-seed 数据综合 → **R21 V4_h50_s49 0.613 是 single trajectory cherry-pick, 不是稳定 sweet spot**. 所有其他 ckpt (12 个新 H scan + multi-seed 实验) 全部收敛到 6-axis ∈ [0.133, 0.219], median ≈ 0.137. 这意味着 ANDES + paper-faithful env + paper Eq.14 reward 下 SAC 真实 attractor ≈ 0.137 (V1 的 3.7×, 但远低 paper-grade 0.6 threshold). V4_h50_s49 当 paper main result 不可投稿 (reviewer 一问 multi-seed 验证答不出). Paper 战略需要修改.

---

## 综合 ranking (R24 完整数据, 集成另一 session 工作)

```
RANKING by mean(LS1, LS2) overall score (top 23 of total ckpts)
   1  ddic_v4_h50_s49                            0.613   ← single-seed outlier
   2  ddic_v4_h200_s47                           0.325   (1 seed only, not yet multi-seed verified)
   3  ddic_v4_s44_best                           0.241
   4  ddic_v4_3best_h50_s44                      0.219   ← H0=50 multi-seed
   5  ddic_v4_1_paper_s44                        0.210
   6  ddic_v4_paper_strict_s45                   0.205
   7  ddic_v4_1_paperstrict_s57                  0.190
   8  ddic_v4_4_best_s44                         0.171
   9  ddic_v4_1_paper_s43                        0.162
  10  ddic_v4_1_paper_s42                        0.151
  11  ddic_v4_1_paperstrict_s55                  0.138
  12  ddic_v4_1_paperstrict_s56                  0.138
  13  ddic_v4_h300_s48                           0.137
  14  ddic_v4_1_phi_s52                          0.137
  15  ddic_v4_3best_h50_s42                      0.137  ← H0=50 multi-seed
  16  ddic_v4_3_h50_s42                          0.137  ← H0=50 multi-seed
  17  ddic_v4_paper_s42                          0.136
  18  ddic_v4_3_h40_s49                          0.136  ← H0=40 sweep
  19  ddic_v4_3_h50_s44                          0.136  ← H0=50 multi-seed
  20  ddic_v4_3_h60_s49                          0.136  ← H0=60 sweep
  21  ddic_v4_paper_s44                          0.135
  22  ddic_v4_4_best_s42                         0.135
  23  ddic_v4_3best_h60_s49                      0.135  ← H0=60 sweep
  24  ddic_r23_v3_h70_s49                        0.134  ← R23 v3 我的 H0=70
  25  ...                                        ...
```

## H₀ × seed 矩阵 (R24 verdict 关键数据)

| H₀ | seed 42 | seed 44 | seed 47 | seed 49 (我的) | 备注 |
|---|---|---|---|---|---|
| 40 | — | — | — | 0.136 final / 0.133 best | R23/v4_3 sweep |
| **50** | **0.137** | **0.136 / 0.137 / 0.219** | — | **0.613** ⭐ + 0.137 final | R21 + multi-seed |
| 60 | — | — | — | 0.136 / 0.135 | R23/v4_3 sweep |
| **70** | — | — | — | **0.134 (R23 v3 我的)** | R24 我的实验 |
| 100 | 0.151-0.21 | 0.241 | — | — | V4 default + V4.1 paper |
| 200 | — | — | 0.325 | — | 1 seed only |
| 300 | — | — | — | 0.137 (s48) | 1 seed |

---

## 关键 finding

### 1. R21 V4_h50_s49 0.613 = single trajectory cherry-pick

H₀=50 multi-seed 测试 (s42 final / s42 best / s44 final / s44 best) 全部 ≈ 0.136-0.219, 平均 0.157. **唯一 0.613 = s49 75ep best**. 即:
- 同 H₀=50 不同 seed: 0.137 (s42), 0.136 (s44), **0.613 (s49)** — s49 是 ~6× outlier
- 同 H₀=50 同 seed s44 best vs final: 0.219 vs 0.136 — best ckpt 显著高 (训练中暂时 lucky)

→ s49 + 某个 lucky checkpoint 时刻是 4σ 罕见事件, **不可作为 paper main result**.

### 2. H₀ 不是关键变量 — H₀ ∈ [40, 70] 全 attractor

H sweep s49: H₀=40 (0.136), H₀=50 (0.613 ⭐ + 0.137), H₀=60 (0.135), H₀=70 (0.134), H₀=100 (0.241), H₀=300 (0.137).
排除 outlier 后**所有 H₀ 收敛到 ≈ 0.137 attractor**. 物理上 H₀ 改变 inertia, 但 SAC 在 paper Eq.14 reward landscape 下找的都是同一 trivial optimum.

### 3. V4 attractor 量级 (≈ 0.137) 仍 V1 (0.037) 的 3.7×

如果接受 attractor as truth (放弃 0.613 outlier):
- V4 mean 6-axis ≈ 0.14
- V1 baseline 6-axis = 0.037
- → V4 reliably 比 V1 好 3.7×, 但远未达 paper-grade 0.6

### 4. V4 H₀=200 s47 0.325 也是 single-seed cherry-pick (R24 v2 confirm)

R24 v2 跑 H₀=200 s42 + s44 50ep:
- V4_h200_s42 = **0.137**
- V4_h200_s44 = **0.138**
- V4_h200_s47 = 0.325 (R21 single seed)

→ s47 跟 H₀=50 s49 同性质, **single trajectory cherry-pick**. 真实 attractor 仍 0.137.

**最终结论**: ANDES + paper Eq.14 + SAC 真实 attractor ≈ **0.137 across all H₀ ∈ [40, 70, 100, 200, 300] × all seeds**. 偶发 0.3-0.6 outlier 是 single-trajectory luck, 不可复现.

---

## Paper 战略修正

### 原方案 (基于 R21 V4_h50_s49 0.613)
> "We achieve paper-grade alignment at 0.613, 16.5× over V1 baseline."

R24 后**不可继续**: reviewer 一问 multi-seed 验证答不出, 直接 reject.

### 修正方案 A: 接受 attractor truth, 诚实报告

> "Across H₀ ∈ [40, 70] × multiple seeds, the SAC + paper Eq.14 reward landscape
> converges to an attractor at 6-axis ≈ 0.14, which is 3.7× over a paper-deviated
> V1 baseline. A single seed (s49) at H₀=50 reached 0.613 in best ckpt during
> training, but this is not seed-robust and we report mean(seed)≈0.14 as the
> reproducible result."

→ Paper 主张降级为 "consistent improvement over V1, but paper-grade alignment
not yet achieved with vanilla SAC + Eq.14 strict". Appendix B B.5 已 explain
why (trivial optimum on local-sync r_f).

### 修正方案 B: 算法 innovation (用户授权"创新")

跳出 paper Eq.14, 设计新 reward / RL algorithm 突破 attractor:
- **CTDE** (centralized training decentralized execution): global critic, 跳出 single-agent local optimum
- **Curiosity bonus**: encourage exploration, 跳出 trivial optimum
- **Reward shaping**: 加 settling time / overshoot 直接 penalty
- **Curriculum learning**: 先 easy disturbance 后 hard, 锁住 sync attractor 后扩

每个 design 工作量 1-3 hr (改代码, 试错), 需用户授权.

### 修正方案 C: 退到 Simulink

ANDES + paper-faithful env 结构性 unfeasible. 切回 -discrete repo 的 Simulink-discrete 主线 (G1-G6 lock paper-anchor). 已 documented for fallback.

---

## 我的推荐

**方案 A (诚实报告) + 部分方案 B (创新)**:

1. Paper main result 改为 "V4 mean 6-axis 0.14 across all seeds" + 注明 single-seed s49 outlier 不可作 main claim
2. 加一个 algorithm innovation section: 改 reward shaping or CTDE, 50 ep × 3 seed 验证, 看是否破 attractor
3. Appendix B.5 已写好 "paper Eq.14 strict 不可 reproduce" — 是 negative finding 学术价值

不推荐方案 C (前面 paper plan 已 commit ANDES 路径, 突然切 Simulink 是 scope creep).

---

## 不可触红线 (R24 增补)

1. ❌ 不要继续单纯 H₀ scan (R24 已确认 H₀ ∈ [40, 70] 全 attractor)
2. ❌ 不要在 paper main 里只 quote V4_h50_s49 0.613 (cherry-pick, 投稿被 reject 风险)
3. ❌ 不要 multi-seed retrain V4_h50_s49 期望 0.613 复现 (R24 数据 4 seed 4 fail)
4. ❌ 不要继续 paper-strict (PHI_D=1.0) variants (V4.5/V4.7 系列, 已知必爆)

---

## 文件引用

- 本 verdict: `quality_reports/research_loop/round_24_verdict.md`
- R23 v3 ckpt: `results/r23_v3_h70_s49/agent_*_final.pt`
- R23 v3 eval: `results/research_loop/eval_v4_baseline/ddic_r23_v3_h70_s49_load_step_{1,2}.json`
- 综合 ranking: `evaluation/paper_grade_axes.py results/research_loop/eval_v4_baseline`
- 另一 session multi-seed 数据: `results/v4_3_*`, `results/v4_4_*`
- Paper appendix B (已 update): `paper/appendix_B_cross_platform_draft.md`
- 前置 R23: `quality_reports/research_loop/round_23_verdict.md`
- 前置 R21 (cherry-pick 起源): `quality_reports/research_loop/round_21_v4_breakthrough.md`

---

*Generated 2026-05-07 ~08:55 by main agent during user "睡会" autonomy. R23 v3 single train + multi-seed数据 reveals R21 V4_h50_s49 0.613 is single-trajectory cherry-pick. ANDES + paper Eq.14 真实 attractor ≈ 0.137. Paper main strategy 需要修改. 推荐方案 A (诚实报告) + 部分方案 B (algorithm innovation).*


## Questions opened (this round)
- none (retrofit — this verdict pre-dates the Q entity introduced in R39)

## Questions closed (this round)
- none (retrofit)

## Questions advanced (this round, status unchanged)
- none (retrofit)
