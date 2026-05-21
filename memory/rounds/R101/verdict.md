# R101 verdict — Multi-seed MLP D3 rigorously closes CLM-0168 retraction

**Date**: 2026-05-19
**Status**: DONE
**Type**: methodology-rigor follow-up to R96 retraction
**Wall**: ~17s ANDES + 60s MLP fits = ~81s total

## TL;DR

R101-W1 ran 10 torch-seed × 4 γ × 4 agent = 160 obs→return MLP fits +
40 obs→action MLP fits on a single R72_w4 SOTA rollout. **γ=0.99
median R² = +0.643** (not −0.41 as [[CLM-0163]] reported, not +0.66 as
[[CLM-0168]]/R96 reported). Both single-fit numbers were within the
noisy distribution, with **mean R² pulled to −0.59 by outlier MLP
failures (R² down to −24.6)**.

CLM-0168 retraction of CLM-0163's headline **stands**: the value-horizon
mismatch mechanism story is empirically dead. But CLM-0168's
"obs sufficient at all γ" claim was also overconfident — γ ∈ (0, 1)
median R² is 0.29-0.67 (moderately positive, not the +0.66 cross-ckpt
suggested as universal).

CLM-0169 records the multi-seed evidence + methodology lesson.

## Methodology

`scripts/r101_d3_multiseed_mlp.py`. 1 deterministic SOTA rollout
(LS1+LS2, 50 steps, seed=42), then per (γ, agent, MLP-seed) triple:
seed torch RNG, init MLP, train 300 epochs, report test R². 10 MLP
seeds × 4 γ × 4 agents = 160 R² values for the R1 (obs→return)
diagnostic. Same loop for R2 (obs→action) = 40 R² values.

Train/test split also re-seeded per MLP seed (split_seed = 2000+s*19),
so each (s, γ, agent) tuple has its own data partition.

Median computed via `probes/r101_median_analysis.py` since the in-script
verdict logic used mean (misleading under MLP-failure outliers).

ANDES occupancy: 17s in 1 slot, no contention with R94/R103 training.

## Results

### Per-γ test R² (40 fits each, 10 seeds × 4 agents)

| γ | median | p25 | p75 | min | max | %neg | %< −1 |
|---|---|---|---|---|---|---|---|
| 0.0  | +0.907 | +0.687 | +0.962 |  −0.04  | +0.991 | 5%  | 0%  |
| 0.9  | +0.286 | −0.131 | +0.405 | **−29.76** | +0.687 | 28% | 12% |
| 0.99 | **+0.643** | −0.009 | +0.772 | **−24.61** | +0.885 | 25% | 7%  |
| 1.0  | +0.666 | +0.083 | +0.800 | −18.53     | +0.909 | 20% | 7%  |

### R2 obs→action (40 fits)

median +0.909, range [−0.06, +0.99], 5% catastrophic.

### Reading the numbers

- **γ=0 median R²=0.91**: obs is near-perfect predictor of instant reward.
- **γ=0.9-1.0 median R²=0.29-0.67**: discounted returns are still
  predictable from obs, but moderately less than instant reward.
- **MLP fits have 5-28% catastrophic failure rate** (R²<0) depending on γ
  — this is the methodology floor, not signal.
- **R72_w4 single-fit R² could be anywhere in [−29, +0.89]** at γ=0.99 with
  the wrong torch RNG seed. CLM-0163 saw −0.41, R96 saw +0.66; both
  inside the noise.

### What stands, what falls

**Stands**:
- Policy near-memoryless (obs→action median 0.91 here, 0.97 cross-ckpt
  R96). This was R91's robust finding.
- CLM-0160 on-manifold critic concave-around-a_sota. Independent
  measurement, untouched.

**Falls**:
- CLM-0163's "γ=0.99 specifically negative R² → value-horizon mismatch
  is the plateau mechanism" — refuted by R101 multi-seed median.
- "Discounted return at paper γ specifically can't be predicted" —
  γ=0.9 is actually slightly worse than γ=0.99 (median 0.29 vs 0.64).
  Effect is graded across γ, not paper-γ-specific.

**Open mechanism candidates after R101**:
- Env stochasticity floor (R84-D4, never run)
- Reward shape ablation (R103, in-flight as of R101 closure)
- Policy class / non-convex landscape (untouched)
- Long-horizon credit assignment (Q-0008)

## Infrastructure changes (R101)

不动 V4 / V4Config / base_env / paper_grade_axes / agents/ / R57+ ckpt.
新建:
- `scripts/r101_d3_multiseed_mlp.py`
- `probes/r101_median_analysis.py` (median extractor)
- `results/r101_d3_multiseed_mlp/summary.json`
- `results/r101_d3_multiseed_mlp_stdout.log`
- `memory/rounds/R101/{plan.md, verdict.md}`
- `memory/claims/CLM-0169.md`

## Cross-references

- [[CLM-0163]] (retracted; multi-seed evidence confirms left-tail outlier reading)
- [[CLM-0168]] (retraction claim; partially confirmed, partially refined)
- [[CLM-0169]] (this round's finding)
- [[CLM-0160]] (on-manifold critic Q-landscape; orthogonal, still stands)
- R103 plan (reward shape ablation, in-flight — next plateau mechanism candidate)
- R96 plan (cross-ckpt single-fit; methodology now criticised but data
  preserved)

## Questions opened (this round)

- (none — methodology lesson is in CLM-0169, not Q-form)

## Questions closed (this round)

- (none directly — Q-0014 plateau mechanism still open after 2 retractions)

## Questions advanced (this round, status unchanged)

- **Q-0014** (algo backlog / plateau mechanism) — value-horizon
  hypothesis empirically dead. Surviving candidates narrow to reward
  shape (R103 in-flight) + env floor (unrun) + policy class.

## 给 PI 的话

**这周干了啥**：你说 "继续研究, 一直干活". 完成 CLM-0168 retraction
PRIORITY 1 (multi-seed MLP redo, 自己 in CLM-0168 列的). R72_w4 ckpt × 10
torch seed × 4 γ × 4 agent × 80/20 split = 160 R1 obs→return fit + 40
R2 obs→action fit. Wall 81s.

**结果（一句话）**：**Median R²(γ=0.99) = +0.643 (positive)**, mean
−0.591 是被 outlier R²=−24 拉的。CLM-0163 的 −0.41 跟 CLM-0168 的 +0.66
都是同一分布的 single-fit samples, 都不可靠. 真信号: obs ARE moderately
predictive of paper γ return; γ ∈ (0, 1) 的 R² 比 γ ∈ {0, 1} 低但 graded,
**不是 paper γ=0.99 specifically 的 mismatch**.

**意外**：(1) γ=0.9 median R²=0.286 比 γ=0.99 median R²=0.643 **更低** —
"paper γ 是最坏" 这个 narrative 错了, discounting in (0, 1) 通通让 obs
预测变难, 跟 paper 选哪个值无关. (2) **MLP regressor 在 N_train=80 +
64×2 hidden 下有 5-28% catastrophic fit rate** (R²<0) 跨所有 γ. 单 fit
R² 在 [-29, +0.89] 之间, 任何单 fit 结论都不可靠. 这是 R96/R91 的根本
methodology debt. (3) **obs → action median 0.91, 但 range [-0.06, 0.99]**
— 看似 robust 的 "policy memoryless" finding 也有 5% MLP fit 撞坏, 不过
median 跟 cross-ckpt R96 的 0.97 一致 → 这条 finding 实际是 universal solid.

**我默认下一步做**：(1) R101 closure + CLM-0169 已写 ✓, 多 seed
methodology lesson 在 CLM-0169 body. (2) R103 reward shape ablation
(paper_strict_pure × R72_w4 hyper × 75 ep s54) 训练已在跑, ~30 min wall,
等结果. (3) R103 出来后看 paper_strict_pure geo 跟 baseline 0.391 比:
- 显著高 (>0.45) → reward shape 是 plateau lever, 写 CLM-0170 + 开 R104 reward 探索
- 同量级 (0.34-0.42) → reward shape 也不是, 开 R105 = R84-D4 env stochasticity floor
- 显著低 / 训练 crash → strict reward 不适配 R72 LSTM 基, 写 negative
(4) 沉默 = R103 完成立刻读、写 verdict、继续 R104 或 R105.

**你想插一脚就说**：(a) 想我立刻把 D4 env stochasticity floor 也写脚
本等 R103 出来一起 launch — 现在写, 不抢 ANDES slot 反正 R103 训练占
着. (b) 想我也写 ridge regression 版本的 D3 (R²=0.643 应该用 ridge
也能复现, 是 sanity check 是不是 model class 问题) — 1 行 sklearn diff,
~10 min wall. (c) 等 R103 verdict 出来再决策. 沉默 = 同时 (a)+(c), 我
现在写 D4 driver 等 R103.
