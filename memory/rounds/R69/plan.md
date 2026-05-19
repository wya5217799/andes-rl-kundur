---
round: R69
state: active
opened: '2026-05-18'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R69 plan — paper_grade_axes 升级到 11-axis (加 per-agent + oscillation gating)

**Date**: 2026-05-18
**Type**: evaluator extension (Asset 4 升级, per ADR-0001 paper-cited 改动)
**Wall budget**: ~1.5 hr (code + test + re-rank + plot)

## Trigger

R68 LSTM warmup sweep peak +13% (warmup=30 s51 = 0.4823 vs R57 选 5 = 0.4259).
用户问"画图评估在我们标准中吗"，我答：6-8 axes 覆盖 80%，漏 3 个 gap:

1. **agent collapse** — 1/4 agent 死，cross-agent **mean** 的 dH/dD range/utilization 仍 looks reasonable
2. **late-time oscillation** — max/final/settling 抓不到持续小幅震荡
3. **per-agent ΔP imbalance** — paper Fig 7 关键，ranker 没覆盖

用户决策："**优化六轴评估，保证只要六轴评估好，论文评估也好，一定能画好图，等最好 agent 再画图**"

= 升级 ranker 内部覆盖 3 gap，避免每 sweep 都画图。最好 agent 时才画 paper figure。

## 设计：新增 3 axes (8 → 11)

### Axis 9: `agent_min_activity` (gate agent collapse)
```python
per_agent_activity = max_t(|dH_i| + |dD_i|)  # shape (N,)
min_act = min over agents
score = clip(min_act / threshold, 0, 1)  # threshold = 50 (engineering)
```
- 1.0 = 4 agent 都活 (min activity > 50)
- 0.0 = ≥1 agent 死 (min activity = 0)
- 几何均值放大: 任 1 agent collapse → 该 axis 0 → overall 拉到 ~0.5×

### Axis 10: `late_oscillation_inv` (gate persistent oscillation)
```python
late_mask = t >= t[0] + 3.0  # after initial transient
df_avg_late = df[late_mask].mean(axis=1)
late_std = std(df_avg_late)
score = 1 - clip(late_std / 0.01, 0, 1)  # threshold = 0.01 Hz (paper ~0.005)
```
- 1.0 = 后段平稳 (std < 0.001 Hz)
- 0.0 = 持续震荡 (std ≥ 0.01 Hz)
- 加 axis 而不替换 final_|df| 因为 final 是单点，oscillation 是 distribution

### Axis 11: `agent_P_balance` (gate per-agent ΔP imbalance)
```python
P_final = mean(P[-10:], axis=0)  # last 10 steps mean per agent
P_abs = |P_final|
score = 1 - (max - min) / (mean + eps) of P_abs   # clipped [0, 1]
```
- 1.0 = 4 agent ΔP final 完全均衡
- 0.0 = 1 agent 干所有事 (max >> min)
- paper Fig 7 ideal: 4 agent ΔP ≈ 1:1:1:1 (DDIC ensemble)

## 合并

`overall = geo_mean(11 axes)` with soft-clamp 0.01 per axis (preserves R30 fix).

**保留 8 个老 axes 不变** — 1.0% backwards-compat: 新 ranker 默认包含 3 新 axes, 但 11-axis vs 8-axis 是显式 version 标记 (CLM-0109 记录 ranker v3.0)。

## 风险

1. **Ranker 改 → 历史 SOTA 排名可能洗牌**:
   - R67 TD3 paper-metric SOTA -0.119 在 11-axis 下可能被罚 (因为 1-2 agent dominant pattern)
   - R57-α LSTM 0.526 可能 hold (因为多 agent 设计)
   - R68 LSTM warmup=30 s51 0.4823 是否真 SOTA 待重 rank
2. **Asset 4 paper-cited**: 必须新 round + 新 claim 文档 + ADR (考虑)
3. **threshold 调参**: agent_min_activity=50, late_std=0.01 — 用工程判断初设, 必要时调

## 任务流

1. ✅ R68 完成 (W3a 3-seed verify warmup=30 跑中) → commit R68 (前置依赖)
2. 🆕 修改 `src/andes_rl_kundur/evaluation/paper_grade_axes.py`:
   - 加 3 个 helper functions
   - `evaluate_trace` 加 axes 9/10/11 (require trace 含 delta_P_es)
3. 🆕 写 `tests/test_paper_grade_axes_11axis.py` (新 axes 单元测试)
4. 🆕 跑 `python -m pytest tests/` 确认全过 (含旧 ranker tests)
5. 🆕 用 11-axis 重 rank 所有 SOTA:
   - R57-α LSTM (R56/R57 historical) — s49/s50/s51
   - R64 TD3 combo
   - R65 SAC combo
   - R67 TD3 tau=0.001
   - R68 LSTM warmup sweep (s51 全部)
   - R68 W3 LSTM warmup=30 3-seed (待 R68 完成)
6. 🆕 选 11-axis 真 SOTA → 画 paper figures:
   - per-agent ΔH/ΔD/ΔP bar chart (Gap 1 visualize)
   - Δf(t) per-generator + cross-mean (Gap 2 visualize)
   - ΔP(t) per agent (Gap 3 visualize)
7. 🆕 写 R69 verdict + CLM-0109 (ranker v3.0 spec) + commit

## Schema plan

- **CLM-0109** (decision/S) — paper_grade_axes ranker v3.0: 加 3 axes (agent_min_activity, late_oscillation_inv, agent_P_balance); 历史 8-axis 结果标记为 v2.x for backwards-trace
- **CLM-0110** (finding/V) — 11-axis re-rank: who is the true SOTA across all 3 modes
- **CLM-0111** (finding/V) — paper figure verification: best agent 的 per-agent + time-domain visual check

## ADR consideration

如果用户同意，写 ADR-0004: ranker v3.0 evolution doctrine (即 paper-cited ranker 的版本化策略)。

## Out of scope

- LSTM 架构 refactor (Q-0013 / R66, deferred R70+)
- Code drift bisect (CLM-0104, deferred R70+)
- Q-0008 500-ep convergence (deferred R70+)
