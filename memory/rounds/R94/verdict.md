# R94 verdict — Widen action bounds 单独不补救 plateau (confirms R93 h-drift mechanism)

**Date**: 2026-05-19
**Status**: DONE — W1 RED -0.243 vs baseline, confirms R93 finding LSTM h-drift is plateau cause not bound
**Type**: experiment (1 wave smoke, R72_w4 hyper + DM_MAX/DD_MAX widened 2.5×)
**Wall**: ~13 min train (740 s) + final_eval

## TL;DR

R92 (CLM-0170) 提议 widen action bounds (2-3×) 作 PRIORITY 1 验证 "bang-bang
saturation = plateau ceiling" hypothesis. R93-W0+W0b (CLM-0181 之前 parallel
session) refine 该 mechanism: **真正 root cause = LSTM-cell hidden-state
self-drift (||h|| 0.25 → 5.0 in 50 steps even on constant-zero obs,
pre-tanh logit |z| → 2.6 saturating tanh)** — R93 W1 widen-bound 因此 hold
pending PI direction. R94-W1 拿原 R92 推荐配方 (dm_max/dd_max 600 → 1500)
跑 R72_w4 hyper × s54 × 75 ep 完成 hold experiment, 结果 **geo = 0.148**
(-0.243 vs baseline 0.391, -62%) — 大幅退化. **R93 mechanism 由此再确认**:
widen bound 不补救因为 h-drift 仍 saturate at 新 boundary, 物理 action
过激 → eval 6-axis 退化更差. Real fix path = td3_lstm_hreg (R100/R101+,
hidden-state norm 正则) suppress h-drift, **不是 widen bound**.

## Methodology

R94-W1 = R72_w4_lstm_tau001_warmup5_s54 baseline + **only** dm_max/dd_max
widened 2.5×:
- DM_MAX: 600 → **1500** (paper Sec.IV-B ΔH ∈ [-100, +300] 即 ΔM 上限 600, 现 1500)
- DD_MAX: 600 → **1500**
- DM_MIN / DD_MIN: -200 不动

其他 hyper 严格 R72_w4 baseline (td3_lstm h64 tau=0.001 lstm-lr-warmup-eps=5
normalize-actions, 75 ep s54).

Paper-deviation framing: 跟 ADR-0004 / 0005 同类 ANDES-side 工程探索. paper
writeup 留作 ablation chart "widening action bounds 单独不补救".

## Results

```
W1 geo = 0.1485
W1 LS1 = 0.1073, LS2 = 0.2054
W1 cum_rf = -0.0385
W1 vs baseline 0.391: Δ = -0.243 (-62%)
```

Training 数据矛盾的 surface:
- Best training reward **-2 @ ep 66** (vs baseline -8.2 @ ep 6) — **更好**
- Final training reward -3 @ ep 74 (vs baseline -39) — **不退化**
- Critic loss 0.473 → 0.149 单调降, TDS failures 1/75 = 1.3%
- 但 deterministic eval 6-axis 大幅退化 -62%

→ **Training reward improvement ≠ eval 6-axis improvement**. agent 在 widened
bound 下学到更大 |action| 让 reward (含 action-cost 项) 改善, 但 paper_grade_axes
评估的物理量 (max_df, settling, ΔH range) 在 widened bound 下被过激 action
惩罚: action 飙到 |ΔM|=1500 → frequency overshoot 增大 → max_df axis 0 分.

## R93 mechanism 再确认

R93-W0b CLM-0181 (parallel session 2026-05-19): R72_w4 LSTM hidden state
self-drifts from ||h||=0.25 to ||h||≈5.0 in 50 steps **regardless of obs**
(constant zero / random / real obs 都一样). pre-tanh logit reach |z|=2.6,
saturating tanh in 38-82% of action steps.

R94-W1 widen-bound 测试 R92 hypothesis "bound is the ceiling":
- 如果 widen bound 让 geo > 0.391 → hypothesis 验证, R92/R93 W1 path 是正解
- **实际 geo = 0.148** → widen bound **不补救** even though training reward 改善
- R93 mechanism 解释: bang-bang 由 LSTM h-drift internal driven, 不依赖 external
  bound. widen bound 只是把 saturation 推到更大幅 action, **eval 物理上更差**.

## Implication

- **R94 negative finding direct**: dm_max/dd_max widening alone (R94-W1 配方)
  is NOT the plateau breaker. R92 PRIORITY 1 hypothesis 部分证伪 (假设错的部分
  是 "bound = root cause"; "bang-bang = mechanism" 部分由 R93-W0b 进一步精化)
- **R100/R101 td3_lstm_hreg 是 correct counter-attack**: hidden-state norm
  regularization 直接 attack h-drift root, 而不是间接 widen bound. R100 path
  应是 R94+ 后续 priority 1
- **paper writeup 可加 ablation**: "we tested widen-bound (R94, dm_max ×2.5)
  and found geo degrades 62%, confirming the bang-bang attractor is NOT
  bound-limited but internally driven by LSTM hidden self-drift (R93)"

## Cross-references

- R92 verdict + CLM-0170 (R92 finding bang-bang at boundary 76% saturation)
- R93 verdict W0+W0b + CLM-0181 (LSTM h-drift mechanism refinement)
- R100/R101 (td3_lstm_hreg counter-attack)
- ADR-0004/0005 (paper-deviation framing for ANDES-side exploration)
- R72_w4_lstm_tau001_warmup5_s54 (baseline reference)

## Questions opened (this round)

- (none) — R94 既不开新 Q, mechanism 已由 R93 W0b 给出, hreg counter-attack 已由
  R100/R101 实施 in parallel

## Questions closed (this round)

- (none) — R94 数据 advances Q-0014 priority 但没 close

## Questions advanced (this round, status unchanged)

- **Q-0014** (open) — R72_w4 SOTA 0.391 plateau 突破路径. R94-W1 widen-bound RED
  排除 "bound 是 ceiling" hypothesis. Real path = R100/R101 hreg 正则 LSTM h.

## 给 PI 的话

**这周干了啥**: R92 verdict 推荐 PRIORITY 1 = widen action bounds (dm_max 600→1500, 2.5×). R94-W1 拿 R72_w4 baseline hyper × s54 × 75 ep 跑 hold experiment, 13 min wall.

**结果（一句话）**: **W1 geo = 0.148 大幅退化 (-62% vs baseline 0.391)**, 但 training reward 反而改善 (-3 final vs baseline -39) — widen bound 没破 plateau, **R93-W0b LSTM h-drift mechanism 由此再确认**: bang-bang 是 LSTM cell internal driven (||h|| 0.25→5.0), 跟 external bound 无关.

**意外**: (1) Training reward 在 widened bound 下**更好** (-3 vs baseline -39), 但 deterministic eval 6-axis **大幅退化** (-62%) — 经典 distribution-shift / objective-mismatch symptom, agent 学到大 |action| 在 reward 上加分, 在 paper_grade_axes 6-axis 上扣分. (2) 这给 paper writeup 一个干净 ablation chart 素材: "widen-bound 没补救 → 证实 LSTM h-drift 才是 root, 不是 action limit". (3) R93-W1 hold pending PI direction 是 prescient — parallel session 推进到 R100/R101 td3_lstm_hreg counter-attack (hidden-state norm 正则), 这才是真正 attack root cause 的 fix path.

**我默认下一步做**: 关 R94, 写 1 个 claim documenting R94-W1 widen-bound RED + retroactive R93 mechanism 确认. 不开 R95 — parallel session 已经在 R100/R101 hreg path 推进, 这才是 correct attack. 短期 idle 等 R100/R101 结果, 不再 widen-bound 路径冒泡.

**你想插一脚就说**: (a) 如果你想 R94-W2 试更激进 widen (dm_max=3000 5×) 反 R94-W1 数据 → 大概率更退化, 不推荐; (b) 如果你想我去 audit R100/R101 hreg path 当前进度 + 写 R94-aware verdict 让 R100 数据可信度更高 → say it; (c) 如果你直接 stop sweep + 让我去 cross-reference R93+R94+R100 写 paper "Plateau 是 LSTM h-drift + tanh saturation 联合 ceiling, paper Sec.IV-B action bounds 不是真 ceiling, hreg 是 correct break" 章节 → 这是诚实+学术价值的 contribution. 沉默 = 默认 idle 等 R100/R101 通知.
