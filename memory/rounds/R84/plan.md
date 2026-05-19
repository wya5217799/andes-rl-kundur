---
round: R84
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R84 plan — Plateau Mechanism Diagnostic (信息论 + Q-landscape 诊断)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: R57-R82 共 91 round algo/hyper trials 全 ≤ R72_w4 baseline 0.391 (CLM-0144). PI: "想想有什么更有意义的研究...启动". R83 走 obs space refactor (并行 session) — R84 必须**正交**.
**Parent**: R82 verdict 选项 (e) — diagnose plateau mechanism (新增, 非原列表)

## 立论 (Why this is more meaningful than another sweep)

研究问题已经从 "**能不能**突破 0.391" 变成 "**为什么不能**". 91 round 实证后:

- 单代理 algo 维度 (SAC MLP / TD3 MLP / TD3 LSTMCell / TD3 multi-layer LSTM / TD3 Transformer): 全 RED
- Hyper 维度 (lr / batch / tau / warmup / hidden / gamma): 全 RED
- Obs aug 单元 (R49-α own_action / R52 time / R81-W1 time+R72hyper): 全 RED
- R83 obs space refactor 跑中 (另一 session) — **如果 R83 也 RED, 我们 96 round 全 RED 仍不知道为什么**

R84 不再 sweep, 改诊断:

> "If 我们能用信息论+Q-landscape 工具量化 R72_w4 SOTA 的 plateau 来自哪个 ingredient
> (obs 信息熵不够 / reward signal 不够 discriminative / Q-function 局部极小 /
> env stochasticity floor), 那么 R85+ 的实验方向就有目标; 否则继续盲 sweep 是
> diminishing return."

这是 paper 级的 **failure-mode analysis contribution**, 跟 paper-grade ranking 一样重要.

## 跟 R83 不冲突的设计

| 资源 | R83 (obs space) | R84 (diagnostic) |
|---|---|---|
| GPU | 训练新 ckpt (3 wave × 75 ep) | **零训练**, 只 load R72_w4 SOTA ckpt |
| 写代码 | scripts/train.py / V4Config / base_env | scripts/r84_*.py, **不动 V4 / V4Config / agents/** |
| 输出 | new ckpt + geo number | diagnostic report, 数据无 ckpt |
| Wall | ~45 min/wave × 3 | 数据收集 ~30 min, 分析 ~1 h |
| 锁文件冲突 | ANDES WSL session | 共享 R72_w4 ckpt (read-only) |

R84 用 R72_w4 SOTA ckpt 做 **read-only forensics**, R83 在前台训练. 互不抢资源.

## R84 诊断框架 (4 axes)

每个 axis 1 个脚本, 单 seed s54 (跟 SOTA training seed 对齐, 避免 OOD).

### Axis 1: **Reward landscape discriminability** (D1)

**Question**: 在 SOTA policy 的 state 分布上, reward 对 action 是否 discriminative?
如果 reward gradient 沿所有 action dimension 几乎为 0, 那 plateau 是 reward shape problem.

**方法**:
1. Load `r72_w4_lstm_tau001_warmup5_s54/agent_*_best.pt`, deterministic mode
2. 跑 N=20 fixed-disturbance episode, 记录 `(t, obs_t, sota_action_t, reward_t)`
3. 在每个采样 t 上, 把 sota_action_t 扰动 ±0.1, ±0.3, ±0.5 (相对 action_scale), 重置 ANDES 到 obs_t, run 1 step, 记录 perturbed reward
4. 画 reward(action_perturbation) 曲线 + 计算 |∂R/∂a| 的 distribution
5. **Pass criterion (plateau 不来自 reward)**: |∂R/∂a| 中位数 ≥ ε (TBD, 跟 reward magnitude 比较)

**输出**: `results/r84_d1_reward_landscape/{summary.json, perturbation_curves.png}`

### Axis 2: **Q-function epistemic uncertainty** (D2)

**Question**: SOTA critic 对 "应该选什么 action" 是否 confident?
如果 Q(s, a*) ≈ Q(s, a') 对很多 a' ≠ a*, 那 critic 没区分能力, plateau 来自 critic.

**方法**:
1. Load SOTA double-Q critic, deterministic mode
2. 对收集的 N=20 episode × 50 step = 1000 (s, a*) 样本, 在 s 固定时:
   - sample 100 random actions ∈ [-1, 1]^action_dim
   - compute Q1(s, a_i), Q2(s, a_i) for each
3. 量化 (per state):
   - Q(s, a*) - mean Q(s, a_random): "SOTA action advantage"
   - argmax_a Q(s, a) vs a*: 是否一致 (consistency)
   - Q1 vs Q2 disagreement: epistemic uncertainty
4. **Pass criterion (plateau 不来自 Q-function)**: SOTA action advantage > 0 且 Q1/Q2 一致

**输出**: `results/r84_d2_q_landscape/{summary.json, q_distributions.png}`

### Axis 3: **Observation sufficiency (mutual information lower bound)** (D3)

**Question**: 给定 SOTA observation, **可学习的** optimal action 上界是多少?
如果 obs 和 reward-to-go 之间 mutual information 低, 则 obs 信息不足, plateau 来自 obs.
**这是 R83 obs space 路径的 falsification target**.

**方法**:
1. 收集 N=50 episode 的 (obs_t, return_t = Σγ^k r_{t+k}) 样本 ≈ 2500 点
2. 训练一个简单 MLP regressor: obs → return, 用 80/20 split 测 R²
   - 这是 V*(s) 的 **可学习上界**, 跟 sota critic Q(s, a*) 的差衡量 obs 表征 ceiling
3. 同样训 (obs_t, action*_t) regressor, 测 BC (behavior cloning) loss 上界
4. 对比 BC loss 和 critic Q values, 用 V-trace 或类似估计 advantage variance
5. **Pass criterion (plateau 不来自 obs)**: BC R² > 0.7 且 V regressor R² > 0.5

**输出**: `results/r84_d3_obs_sufficiency/{summary.json, bc_curve.png}`

### Axis 4: **Env stochasticity / horizon floor** (D4)

**Question**: 同一 SOTA policy 跑 deterministic env, 100 个不同 seed 的 6-axis variance 多大?
如果 σ_geo / mean_geo > 0.3, 那 plateau 的"屋顶"是 env noise, 跟 RL 无关.

**方法**:
1. 跑 R72_w4 SOTA ckpt × deterministic eval × 100 不同 disturbance seed
2. 量化 (per axis): mean, std, P10, P90, max
3. 跟 V4 multi-seed attractor 0.137 (CLM-0144) + R72_w4 single seed 0.391 对比
4. **Pass criterion (plateau 不来自 env noise)**: σ_geo / mean_geo < 0.15

**输出**: `results/r84_d4_env_floor/{summary.json, seed_distribution.png}`

## Wave 顺序 + Gate

- **W1** = D4 (最快, 纯 eval × 100 seed, 0 写代码; 已有 `scripts/eval_all_seeds.py` 可改)
- **W2** = D2 (load critic + sample actions, ~2 h 写脚本)
- **W3** = D1 (reward landscape, 需 reset ANDES 到任意 obs 状态 — 可能要 V4 env feature; fallback: 只在 episode 头部采样)
- **W4** = D3 (BC regressor, ~3 h 写 + 1 h 训练)

Gate (R85 决策依据):
- D4 fails (σ_geo / mean_geo ≥ 0.15) → plateau 是 env floor → R85 = environment-level redesign (跟 R09 audit / SBASE 调整合并)
- D3 fails (obs 信息不足) → plateau 是 obs ceiling → **支持 R83 obs space 路径, 也指明应加哪类 feature**
- D2 fails (critic 不 confident) → plateau 是 RL signal noise → R85 = 长期 horizon 训练 (Q-0008) 或 critic 架构升级
- D1 fails (reward 不 discriminative) → plateau 是 reward shape → R85 = reward redesign (physics-informed)
- 全 pass → plateau **mystery**, 可能 policy class limit, 转 (b) CTDE structure

## 资产保护契约

不动: V4 / V4Config / base_env / paper_grade_axes / agents/ / scripts/train.py / 任何 R57+ ckpt.
新建: `scripts/r84_d1_reward_landscape.py`, `scripts/r84_d2_q_landscape.py`, `scripts/r84_d3_obs_sufficiency.py`, `scripts/r84_d4_env_floor.py`, results/r84_d*/ output dirs.
**Read-only** load: `results/r72_w4_lstm_tau001_warmup5_s54/agent_*_best.pt`.

## 测试不变量

- V4 regression `tests/test_v4_env_regression.py` **不需重跑** (零 env 改动)
- R72_w4 SOTA ckpt 仅 read-only load, 不重训不覆写

## Cross-references

- R82 verdict (91 round plateau evidence)
- CLM-0144 (cumulative algo plateau claim)
- Q-0014 (algo backlog, R84 不闭, 但提供 R85+ 的 informed 选择)
- R83 plan (obs space refactor, R84-D3 是其 falsification target)
- Q-0008 (paper convergence horizon, R84-D2 间接探测)
- R49-α / CLM-0057 (deterministic policy collapse, R84-D2 可能复现)
