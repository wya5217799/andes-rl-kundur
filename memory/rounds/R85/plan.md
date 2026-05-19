---
round: R85
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R85 plan — Classical PI / Droop baseline (paper-mandatory comparison)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: PI confirmed "启动, 别问我了, 干就完了". R57-R82 共 91 round 全部 skip classical baseline, paper reviewer 必问 "RL vs PI/Droop"; 不补这一块 paper claim 站不住. R83 (obs space) + R84 (mechanism diagnostic) 在另一窗口并行运行, R85 严格正交.
**Parent**: R72_w4 LSTM s54 SOTA geo=0.391 (CLM-0094 + R80 cross-eval) 没有 classical reference

## TL;DR

实现两个 paper-mandatory classical baseline (分布式 PI + 频率 droop), 在跟 R72_w4
SOTA cross-eval 完全相同的 setup (V4 paper-faithful + LS1/LS2 + steps=150 + seed=42)
下报 11-axis geo, 跟 R72_w4 (0.391) + no_control (0.104) 对比. 不动 V4 /
V4Config / base_env / paper_grade_axes / agents/ / train.py / 任何 R57+ ckpt.

**两侧都 paper-publishable**:
- classical ≥ 0.391 → 🚨 RL claim 颠覆, 整个 R57-R82 sweep 努力被 undercut
- classical 显著 < 0.391 → RL paper claim 终于有 quantitative defense

## 历史 + 立论

- R57-R82 共 **91 round algo / hyper trials** 全部 ≤ 0.391, plateau 真实 (CLM-0144)
- 但 91 round **0 次** 跟 classical control 对比 — paper 关键 baseline gap
- R30 no_control 0.104 不是 controller, 是 "什么都不做" reference
- paper 在 Sec.IV-C 暗示 "RL 比传统 droop 好", 但没给数字 — 这正是 R85 要补的

## 设计

### Controller 1: DroopController (1 hyperparameter)

```
ΔM_norm[i] = 0  # 不动 inertia
ΔD_norm[i] = clip(K_droop * |Δω_local[i]|, 0.0, 1.0)
```

- Input: `obs[i][1]` (= d_omega[i] / 3.0, normalized rad/s)
- 物理含义: 频率偏越大, damping 加越多 (传统 governor 频率 droop 在 ESS 上的等价)
- 不需积分状态, 完全 memoryless

### Controller 2: PIController (4 hyperparameters)

```
err_i = obs[i][1]              # local normalized Δω
integral[i] += err_i * DT
ΔM_norm[i] = clip(-Kp_M * err_i - Ki_M * integral[i], -1.0, 1.0)
ΔD_norm[i] = clip(-Kp_D * err_i - Ki_D * integral[i], -1.0, 1.0)
```

- 4 instance, 每 ESS 1 个 (跟 RL agent topology 对齐)
- 单 PI 状态 = scalar integral, episode reset 时清零
- 没 anti-windup (Kundur scenario 50 step × DT=0.2 = 10s, integral 不至于过深爆)
- 不读 neighbor obs (distributed local control, classical fair 假设)

### Action space 对齐契约

V4 env (`base_env.step` line 309): action 是 dict[int, np.ndarray(2,)] in [-1, 1]^2.
经过 line 332-333 解码: `delta_M[i] = a[0] * DM_MAX (a[0]≥0) or a[0] * (-DM_MIN)`.
Classical controller 输出 (dM, dD) ∈ [-1, 1]^2 走完全相同的 decoding path, 跟 RL
agent action 是 apples-to-apples (CLM-0146 will assert this).

## Tuning protocol

- Hand-tuned 初始 gain 基于 Kundur dynamics literature (~ω_n=2π, ζ=0.3 prototype)
- Small grid scan: K_droop ∈ {0.5, 1.0, 2.0, 5.0, 10.0, 20.0}; PI gain grid
  Kp_M / Ki_M / Kp_D / Ki_D 各 3-4 value = 36-256 combo (LS1 + LS2 各 2 scenario,
  对 droop 共 12 eval, 对 PI 共 72-512 eval).
- **数据公平**: classical 在完整 eval set 上 tune (跟 RL ckpt 选 best 的标准对等),
  报最佳 gains 的 geo. classical 拿到 upper-bound 优势; 如果仍输给 RL, RL win
  绝对; 如果赢, RL 立论彻底崩.

## Wave 顺序

| Wave | 内容 | Wall |
|---|---|---|
| **W0** | Implement r85_classical_baseline.py + droop/PI class | ~30 min code |
| **W1** | Droop K_droop 6-grid × 2 scenario = 12 eval | ~5 min |
| **W2** | PI 4D coarse grid (3^4 = 81 combo) × 2 scen = 162 eval | ~80 min |
| **W3** | PI 4D fine grid around W2 best ± 1 step = 16 eval | ~10 min |
| **W4** | 写 verdict + 3 claim + chat brief | ~30 min |

Sequential, total wall ~2.5h.

## Resource conflict gate

- R83 (obs space training): 占 WSL ANDES TDS slot, train.py 全力跑 75 ep × 4 agent
  × 3 wave. R85 是 eval, 不训练, 单 process. 用户 CLAUDE.md "max 3 parallel WSL
  python", 我数: R83 W2 1个 + R84 (未跑) + R85 1 个 = 2. 安全.
- R84 (mechanism diagnostic): 没在 WSL 跑, 用 read-only ckpt + 纯 Python. 跟
  R85 完全不重叠.
- R85 输出: `results/r85_classical_baseline/{droop,pi}_<scen>.json` (新 namespace).
- R85 写代码: 仅新建 `scripts/r85_classical_baseline.py`. 0 mutation 在 src/.

## Gate

Pass criteria for geo (R72_w4 SOTA = 0.391, no_control = 0.104):

| Best droop geo | Best PI geo | Decision |
|---|---|---|
| ≥ 0.391 OR ≥ 0.391 | — | 🚨 RL 颠覆 finding, paper 危机 |
| ∈ [0.30, 0.39] | ∈ [0.30, 0.39] | RL marginal advantage (<10%), paper 立论弱 |
| ∈ [0.15, 0.30] | ∈ [0.15, 0.30] | RL has clear advantage, paper claim 稳 |
| ≤ 0.104 | ≤ 0.104 | tuning 失败, 必须重 tune (gain 范围错) |

## 资产保护契约

不动: V4 / V4Config / base_env / paper_grade_axes / agents/ / scripts/train.py /
任何 R57+ ckpt / any test.

新建: `scripts/r85_classical_baseline.py`, `results/r85_classical_baseline/` 输出 dir.

## 测试不变量

- V4 regression `tests/test_v4_env_regression.py` **不需重跑** (零 V4 改动)
- R57+ SOTA ckpt 完全不读 / 不改

## Cross-references

- R72_w4_lstm_tau001_warmup5_s54 (SOTA baseline, R85 比对参照)
- CLM-0144 (91 round algo plateau)
- R80 cross-eval (V4 paper-faithful eval pattern 直接复用)
- R30 no_control baseline (LS1+LS2 eval 0.104 是 floor)
- ADR-0001 (src layout) / ADR-0002 (V4 SSOT)
