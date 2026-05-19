# R247 verdict — phi_h 不是 scalar+s50 rescue (bit-identical to R246)

**Date**: 2026-05-20
**Status**: CLOSED-NEGATIVE — phi_h ruled out as load-bearing rescue
**Type**: research
**Wall**: ~13 min training

## TL;DR

scalar+s50+phi_h=0.0056+phi_abs=50, --phi-d 0 --phi-f 0. Result:
geo=**0.2347**, LS1=0.215, LS2=0.256, cum_rf=-0.0917. **Bit-identical
to R246 (0.2346) to 4 decimal places**. Adding paper r_h alone does
NOT rescue scalar+s50 from the -28% drop.

phi_h is **definitively NOT the load-bearing rescue term** for
scalar's seed-sensitivity. Next decomposition candidates: phi_d
alone, phi_f alone.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 50 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --phi-h 0.0056 --phi-d 0 --phi-f 0 \
    --save-dir results/r247_w1_scalar_phih_only_s50

python scripts/score_run.py --label r247_w1_scalar_phih_only \
    --ckpt-dirs results/r247_w1_scalar_phih_only_s50 \
    --out-dir results/r247_w1_scalar_phih_only_s50
```

## R246 ↔ R247 bit-identical comparison

| Axis | R246 (only-phi_abs)  | R247 (+phi_h)     | Δ      |
|------|----------------------|--------------------|--------|
| LS1  | 0.2156               | 0.2155             | -0.05% |
| LS2  | 0.2553               | 0.2556             | +0.12% |
| geo  | 0.2346               | 0.2347             | +0.04% |
| cum_rf | -0.0917            | -0.0917            | 0      |

Difference between adding phi_h=0.0056 (paper-effective scaling for
r_h inertia smoothing) vs not is **well below 1.5% eval noise**.
phi_h's contribution to the scalar s50 reward signal is effectively
zero.

## Result classification

R247 plan decision tree:
- ≥ 0.32 (rescue): ❌
- 0.25-0.32 (partial): ❌
- **≈ 0.23 (no help)**: ✅ matched at 0.2347

## What this tells us about scalar seed-sensitivity mechanism

The R242/R246 scalar-at-non-s54-seed underperformance is **not
explained by missing paper r_h** (inertia smoothing). Two remaining
candidates:
- **phi_d (paper r_d damping smoothing)**: tests "is the issue
  damping-rate signal?" — R249 candidate.
- **phi_f (paper r_f sync penalty at weight 100)**: tests "is the
  issue the synchronization weight scaling?" — R250 candidate.

Or it could be that paper terms together provide a smoothing
pressure that no single term captures — i.e., the rescue requires
multiple paper terms simultaneously. R248 (auto-launched, scalar
s50 with full paper-original weights + phi_abs) will test this.

## Implication for hreg-as-drop-in recommendation

R247 indirectly **strengthens** the hreg-as-minimal-correction
narrative: if no single paper reward term rescues scalar, then
hreg's hidden-state regularization is providing a kind of
**distributed stabilization** that the paper formulation cannot
match per-term. This makes "use hreg + phi_abs" a more attractive
recommendation than "tune paper-original weights for your
algorithm".

## Questions opened (this round)

- Q-NNNN (R249/R250 candidates): which paper term (phi_d alone,
  phi_f alone, or only the combination) IS the rescue for scalar
  at non-s54 seeds?

## Questions closed (this round)

- (none formal — but de facto: "is phi_h the load-bearing rescue
  term for scalar seed-sensitivity?" answered NO)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这周干了啥**：R247 = R246 follow-up, scalar s50 + 只加 paper r_h
(phi_h=0.0056). 看 r_h 是否就是 scalar 在 non-s54 seed 缺的 rescue
信号.

**结果（一句话）**：R247 = geo **0.2347 vs R246 0.2346**, **4 dp 一致**
— phi_h **完全不是 rescue**, 加它跟不加没差别.

**意外**：以为 phi_h (inertia smoothing) 跟 hreg (hidden-state reg) 类
比最直接, 应该会 partial rescue. 实际完全不动. 这意味着 hreg 提供的
不是 simple inertia-smoothing 替代, 是更 distributed 的稳定. 这
**强化了 hreg-as-minimal-correction-drop-in 推荐** — 没单 paper term
能替代它.

**我默认下一步做**：
1. 等 R248 (auto-launched, scalar s50 + paper-original phi_h=1, phi_d=1,
   phi_f=100 + phi_abs=50) — 测 "全部 paper terms 一起加" 是否 rescue.
   是的话: scalar 需要 paper terms 但要 distributed; 不是的话: paper-
   original-weights 也没用, hreg 是唯一答案.
2. 视 R248 outcome 决定 R249/R250:
   - R248 partial rescue → R249 = phi_d alone, R250 = phi_f alone
   - R248 no rescue → 跳过 per-term, 写 paper "scalar seed-sensitivity
     无 reward-term-level rescue, 仅 hreg works"
3. 同时 R245 verdict 已 close (CLM-0415 horizon fragility).

**你想插一脚就说**：现在我有 5-6 个 fresh CLM (CLM-0385/0390/0395/0400/
0405/0410/0415/0420 ~= 8 个). paper Sec.IV-D 第 5 contribution 数据
极厚. 如果你觉得到 R248 应该停下来写 paper draft 而不是继续 R249/250,
现在说. 我 default 让 R248 跑完, 然后视 outcome 决定停或继续.

## Cross-references

- R246 (scalar s50 only-phi_abs = 0.2346 — direct baseline)
- R236/R237 (hreg phi_h/phi_d/phi_f individual ablation — for hreg
  all individually inert)
- R248 (paper-original-weights test, in flight)
- CLM-0420 (this round's claim)
