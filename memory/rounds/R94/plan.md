---
round: R94
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R94 plan — Widen action bounds (R92 finding direct test)

**Status**: ACTIVE (W1 will launch)
**Opened**: 2026-05-19
**Driver**: R92 verdict CLM-0170 finding (R72_w4 SOTA = bang-bang 256-action quantised policy pinning ±1 boundary 70% of episode). PI 简报 "默认走 R93 widen-bound", R93 race-leftover, R94 拿.
**Parent**: R92 (action-saturation finding) + CLM-0144 (R57-R82 91 round plateau evidence)

## TL;DR

R92 实证 R72_w4 SOTA 是 bang-bang policy, **0.391 plateau = action-saturation
+ bang-bang quantisation 联合 ceiling**, 跟 critic / obs / algo 都无关. R57-R86
91+ round 都没动的**唯一 axis** = DM_MAX/DD_MAX = 600 (paper Sec.IV-B). R94-W1
直接 widen: dm_max 600→1500, dd_max 600→1500 (2.5×), R72_w4 same hyper + same
seed. Falsifiable single wave: 如果 plateau bound-limited → geo > 0.391;
如果 跟 bound 无关 → geo ≤ 0.391, R92 mechanism 解释也错.

## Methodology

R94-W1 = R72_w4_lstm_tau001_warmup5_s54 baseline + **only** dm_max/dd_max widened.
保持: algo td3_lstm, hidden=64, tau=0.001, lstm-lr-warmup-eps=5, normalize-actions,
episodes=75, seed=54. 这是 R72_w4 exact recipe, 仅 action bounds 改.

Paper-deviation: paper Sec.IV-B ΔH ∈ [-100, +300] (即 ΔM ∈ [-200, +600]).
R94 widen 到 ΔM ∈ [-200, +1500] = 5× paper upper. Framing 跟 ADR-0004 / 0005 同类
("ANDES-side 工程探索, paper-deviation, 不假装 paper-faithful"). 留 paper writeup
作 ablation chart.

CLI:
```bash
python3 scripts/train.py --algo td3_lstm --episodes 75 --seed 54 \
  --hidden-size 64 --tau 0.001 --lstm-lr-warmup-eps 5 --normalize-actions \
  --dm-max 1500 --dd-max 1500 \
  --save-dir results/r94_w1_widen_bound_x2p5_s54 --final-eval
```

## Gate

- **geo > 0.45** (well above baseline + threshold) → bound 是 ceiling 确认,
  R95+ multi-seed × 500 ep paper-grade
- **0.40 ≤ geo ≤ 0.45** → marginal, R94-W2 试 dm_max=2000 看是否再 climb
- **0.38 ≤ geo ≤ 0.40** → bound 不是 ceiling 或 75 ep budget 不够, 写 verdict
  "widen 1 没显著 break plateau, 试 W2 longer ep 或 更大 widen"
- **geo < 0.38** → R92 mechanism 解释错, plateau 有其他 root cause, 大幅退档

## Stopping rules

- 训练 NaN / TDS fail > 50% → 记 negative finding 即停
- W1 geo > 0.45 → R95 multi-seed × 500 ep
- W1 ∈ [0.38, 0.45] → W2 dm_max=2000 试更激进 widen
- W1 < 0.38 → 写 R94 verdict negative, R92 mechanism 假设证伪

## 资产保护契约

不动 V4 / V4Config default field / paper_grade_axes / R57+ ckpt / V5 env.
action bounds 通过 CLI --dm-max --dd-max override 路径, V4Config default 不变.
new ckpt `results/r94_*_s54/`, 不污染 V4 / V5 ckpt 区.
