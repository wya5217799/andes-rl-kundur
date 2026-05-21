# R103 verdict — paper_strict_pure × R72_w4 hyper = catastrophic collapse (-97% geo)

**Date**: 2026-05-19
**Status**: DONE — single-wave decisive RED
**Type**: reward shape ablation
**Wall**: ~15 min training (under 3-slot ANDES contention) + final_eval

## TL;DR

`paper_strict_pure` reward (PHI_H=PHI_D=1.0, PHI_ABS=0) × R72_w4 hyper
× 75 ep s54 final_eval **geo = 0.010** vs baseline 0.391. LS1=0,
LS2=0 → floor. PHI_H/D=1.0 is 180× larger than paper_faithful's 0.0056
rescale → policy gradient dominated by action penalty → near-zero
action everywhere → no control. [[CLM-0203]] records this.

**Direct implication**: PHI_ABS=50 + PHI_H/D=0.0056 rescale (the
project's R18-era reward recipe) is **load-bearing** for the SOTA
basin, not a tunable suggestion. paper_strict_pure is NOT a paper-honesty
upgrade for our pipeline.

## Methodology

```bash
python scripts/train.py --algo td3_lstm \
  --reward-config paper_strict_pure \
  --episodes 75 --seed 54 --hidden-size 64 --tau 0.001 \
  --lstm-lr-warmup-eps 5 --normalize-actions \
  --save-dir results/r103_w1_paper_strict_pure_s54 \
  --final-eval
```

Single-axis ablation vs R72_w4 baseline. Only difference: `--reward-config
paper_strict_pure`.

## Training health

- 75 ep completed.
- 2 transient TDS divergences early (t=2.38s, t=3.58s), episode boundary
  cleanup recovered.
- Reward improved modestly (ep 0: -27.05; ep 74: -20.92). Looks like
  normal training trajectory.
- best.pt saved ~ep 27 (visible in monitor_data.csv).

But final_eval reveals the basin found is degenerate:

## Final eval

| metric | value |
|---|---|
| LS1 11-axis | 0.0000 |
| LS2 11-axis | 0.0000 |
| geo | **0.010** (floor) |
| cum_rf | -0.183 (note: different reward scale → not directly comparable) |

vs R72_w4 baseline (paper_faithful reward): geo = 0.391 → **−97% collapse**.

## Mechanism

PHI_H/D = 1.0 in paper_strict_pure vs 0.0056 in paper_faithful = **180×
larger penalty** on action magnitude (per step, per agent). With
R72_w4 LSTM hyper, the TD3 policy gradient is dominated by the
action-penalty term → policy collapses to ||a|| ≈ 0 at all steps.
No control → frequency oscillation unhindered → 6-axis goes to floor.

This **confirms R18's verdict** ([[CLM-0073]] R58 sanity): under
paper-strict reward, SAC/TD3-MLP also produce 6-axis ≈ 0. R103 extends
that to TD3-LSTM.

## Cross-references

- [[CLM-0144]] (91-round algo plateau)
- [[CLM-0168]] / [[CLM-0169]] (value-horizon refuted)
- [[CLM-0200]] (synthesis — reward shape was "open candidate", R103
  makes it "load-bearing recipe, narrow perturbation band")
- [[CLM-0203]] (this round's claim)
- [[CLM-0073]] (R58 paper_strict_pure on SAC/TD3-MLP — same result)
- R58 / ADR-0002 (paper_strict_pure infrastructure)

## Questions opened (this round)

- (none — finding is decisive RED)

## Questions closed (this round)

- (none directly)

## Questions advanced (this round, status unchanged)

- **Q-0014** (algo backlog) — reward shape candidate downgraded from
  "untouched" to "load-bearing-recipe; switch breaks". paper_strict
  variants of paper_faithful are not safe to swap. Future reward
  exploration should perturb individual coefficients (PHI_ABS ∈
  {25, 50, 100}; PHI_H/D ∈ {0.003, 0.0056, 0.01}) within narrow band.

## 给 PI 的话

**这周干了啥**：[[CLM-0168]] retraction 后, R85+ PRIORITY 2 = reward
shape ablation. R72_w4 hyper × `V4Config.paper_strict_pure` (paper Eq.14
nominal, PHI_H=PHI_D=1.0, PHI_ABS=0) × 75 ep s54. 单轴 ablation, R58
infrastructure 已就位.

**结果（一句话）**：**Catastrophic collapse geo=0.010 (-97%)**. paper_strict_pure
的 PHI_H/D=1.0 比 paper_faithful 的 0.0056 大 180×, policy 梯度被 action
penalty 主导, 训出 zero-action 退化策略, LS1=LS2=0.

**意外**：(1) Training 没 crash, reward 看似在缓慢改善 (-27 → -21), 但
best.pt 锁的 basin 是 "do nothing" 的 trivial 解. 这跟 R58 SAC/TD3-MLP
paper_strict_pure 给 6-axis ≈ 0 (CLM-0073) 同 pattern. (2) 我们 V4
paper-faithful reward 的 PHI_ABS=50 + R18 PHI_H/D=0.0056 **是 load-bearing
recipe**, 不是"可以丢掉的非 paper 多余项". CLM-0200 synthesis 更新: reward
shape 不是 open candidate, 是 narrow-window 的 fixed recipe. (3) 这意味着
paper 写作时不能 sweep "去掉 PHI_ABS 看 paper-honest 结果如何" — 那个实验
答案是 -97%, 直接否决论文 paper-Eq.14-strict 路径.

**我默认下一步做**：(1) R103 closure + CLM-0203 入库 ✓. (2) R85+ 列表
更新: paper_strict_pure RULED OUT. 推荐候选 = **R113 magnitude-randomised
training** (R106 / CLM-0202 finding 提供 motivation) 或 narrow-PHI
sweep (PHI_ABS ∈ {25, 50, 100} 同 R72 其他 hyper). 沉默 = 等 R112 warm-h_0
eval 出来 (跑中 ~80s wall) 再决定.

**你想插一脚就说**：(a) 想 narrow-PHI sweep (PHI_ABS=25 / 100 跑 75 ep s54,
2 training run, ~1h total wall) — 测 PHI_ABS sensitivity; (b) 直接开
R113 magnitude-randomised training; (c) 等 R112 warm-h_0 + R113 magnitude
决策一起跑. 推荐 (默认) (c).
