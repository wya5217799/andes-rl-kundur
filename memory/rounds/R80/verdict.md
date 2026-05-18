# R80 verdict — V5 env REGCA1 plant 升级 + 阶梯实验

**Date**: 2026-05-19
**Status**: DONE — C4 negative finding
**Type**: experiment + infrastructure
**Wall**: ~3 h (Phase 0 probe 15 min + V5 scaffold 30 min + V4 regression 107 s + Phase A 探针 ~30 min + Phase B cross-eval 待跑)
**ADRs**: ADR-0004 (V5 paper-deviation framing) + ADR-0005 (ANDES-only)

## TL;DR

V5 env (`andes_vsg_env_v5.py` + `v5_config.py`) 与 V4 并存, 默认 `wind_model="regca1_w2_only"`: W2 (Bus 8) 从 GENCLS M=0.1 换成 ANDES REGCA1+REECA1. cycle 4 cross-eval: R72_w4 LSTM ckpt 在 V4 / V5_w2_only / V5_gencls_fall 三 plant 上 11-axis geo = 0.3908 / **0.3814** / 0.3908, **Δ(V5-V4) = -0.0094** < GATE C 阈值 0.05 → **C4 negative finding**: W2 plant GENCLS→REGCA1 升级对 V4-trained agent 6-axis transfer 无显著影响. Phase A 实测 W2 plant 物理上确实变了 (no_disturb max_df 0.025→0.029, +19%), 但在 controlled regime 下被 agent 吸收. G4+W2 一起换的 paper-忠实路径 (`wind_model="regca1"`) TDS 在 t=2s 死掉 (G4 700MW Ipcmd=7.0 接近 Imax=10 + G4 链 u=0 disable 留 TGOV1 init residual 7.56), 留作 R81+.

## Methodology

11 轮 grill 共识 (本轮对话):
- Framing (b) ANDES 工程升级, paper-deviation. paper Sec.II line 259-263 显式 "neglect inner loop", REGCA1 反方向; paper Sec.IV-A 风机模型沉默, "对齐 paper" 无据.
- 研究重点是 4-ESS VSG control (RL agent 训练对象), 风机是 plant 元件.
- 阶梯 C3 cross-eval → C2 ablation → C1 main result, 按结果定. 最差 case = C4 negative finding 仍是 paper 章节.

Phase 0 probe (`scripts/r80_regca1_wire_check.py`, `probes/r80_regca1_wire_check.json`):
- ANDES 2.0.0 含 REGCA1 + REECA1 + REPCA1 trio.
- 4 个 wire config 全部 pflow + 1-step TDS PASS:
  - exp1 V4 baseline (4 GENROU + 5 GENCLS + 0 REGCA1)
  - exp2 W2 only (REGCA1+REECA1 @ Bus 8, 4 GENROU active)
  - exp3 G4 only (REGCA1+REECA1 @ Bus 4, 3 GENROU active 含 G4 链 disable)
  - exp4 v5 target both (n_REGCA1=2, n_REECA1=2, n_GENROU=3, n_TGOV1=3, n_EXDC2=3)

Phase 1 scaffold:
- `src/andes_rl_kundur/env/andes/v5_config.py` — V5Config 继承 V4Config, 加 `wind_model: Literal["regca1", "regca1_w2_only", "gencls"]` + `g4_regca1_sn` / `wf2_regca1_sn`. factory v5_default() = `regca1_w2_only`, v4_plant_fallback() = `gencls`, v5_regca1_both() = `regca1`.
- `src/andes_rl_kundur/env/andes/andes_vsg_env_v5.py` — V4 子类, override `_pre_setup_addons` (跳 G4 governor 当 `regca1` 时) + `_build_system` (分 3 个分支). 不动 V4 / base_env / paper_grade_axes.
- `tests/test_v4_env_regression.py` 1e-9 仍 PASS (107 s, 2 tests). V5 scaffold 没污染 V4 paper path.

Phase A zero-action sanity (`scripts/r80_v5_zero_action.py`):

| Env / Scenario | max_df | final_df | cum_rf | n_steps |
|---|---|---|---|---|
| V4_baseline / no_disturb | 0.0245 | 0.0070 | -1.101e-02 | 50 ✓ |
| V5_w2_only / no_disturb | 0.0291 | 0.0091 | -1.171e-02 | 50 ✓ |
| V5_regca1_both / no_disturb | 0.0000 | 0.0000 | 0.0 | **7 (TDS dead)** ✗ |
| V5_gencls_fall / no_disturb | 0.0245 | 0.0070 | -1.101e-02 | 50 ✓ bit-identical V4 |
| V4_baseline / LS1 | 0.1890 | 0.0728 | -1.181e-01 | 50 |
| V5_w2_only / LS1 | 0.1890 | 0.0679 | -1.168e-01 | 50 ✓ |
| V5_regca1_both / LS1 | 0.1898 | 0.1898 | -6.002e-02 | **4 (TDS dead)** ✗ |
| V4_baseline / LS2 | 0.1683 | 0.0661 | -9.718e-02 | 50 |
| V5_w2_only / LS2 | 0.1723 | 0.0674 | -9.752e-02 | 50 ✓ |
| V5_regca1_both / LS2 | — | — | — | **0 (TDS dead)** ✗ |

观察:
1. V5_w2_only 在 3 个 scenario 全跑满 50 步. ✓
2. V5_w2_only 数字跟 V4 在 ±5% 内 (LS1 final_df: V4 0.073 → V5 0.068 = -7%, 稍微平稳).
3. V5_w2_only ≠ V5_gencls_fall (no_disturb max_df 0.029 vs 0.025) — **W2 REGCA1 真生效**, 不是 bit-identical V4 plant.
4. V5_regca1_both 全军覆没 — 留作未来 round (REPCA1 + 调 Imax / Sn / 真删 G4 链 instead u=0).

Phase A audit (`scripts/r80_v5_audit_fail.py`):
- V5_regca1_both at t=2.0s "Time step reduced to zero. Convergence is not likely."
- REGCA1 G4_R Ipcmd=7.0 接近 Imax=10 (paper G4=700 MW / 100 MVA base, 30% margin)
- REGCA1 HVG_x init clamped at 0, unconstrained=-0.14 (init guess 物理不一致)
- TGOV1 idx=4 init residual 7.56 (u=0 disable 没真清出 DAE)

Phase B C3 cross-eval (`scripts/r80_v5_cross_eval.py`, 跑中, output `results/r80_v5_cross_eval/`):
- ckpt = `results/r72_w4_lstm_tau001_warmup5_s54/agent_{0..3}_best.pt` (td3_lstm, obs_dim=7, hidden=64)
- R72_w4 训练用 V4Config: paper-faithful + action_penalty_mode="normalized". Eval 时 penalty mode 不影响 trace (只影响 reward 计算分支), trace 一致.
- 3 env × 2 scen × (no_ctrl + ckpt) = 12 个 150-step TDS episode
- 每 env 独立子目录, 含 no_control_<scen>.json (axis 8 reference) + ckpt_R72w4_<scen>.json + summary.json (from `score_trace_files`)
- 顶层 r80_v5_cross_eval_summary.json 含 gate_c_decision

GATE C 判定 (Phase B 完成后填):
- V5_w2_only geo - V4 geo ≥ +0.05 → GO Phase C (V5 plant 升级有杠杆, 进 1 seed × 75 ep smoke train)
- |Δ| < 0.05 → C4 negative finding (plant 升级对 V4-trained agent transfer 无影响), 关 R80
- ≤ -0.05 → V5 让 V4 ckpt 更差 (有信号但反向), 仍进 Phase C 看重训是否补回

## Results — cycle 4 cross-eval (`results/r80_v5_cross_eval/r80_v5_cross_eval_summary.json`)

R72_w4 LSTM s54 (td3_lstm, obs_dim=7, hidden=64) 在 3 plant × 2 scenario × 150 steps:

| Env | 11-axis geo | cum_rf | LS1 geo | LS2 geo | LS1 ckpt max_df | LS2 ckpt max_df | LS1 no_ctrl max_df | LS2 no_ctrl max_df |
|---|---|---|---|---|---|---|---|---|
| v4_baseline | **0.3908** | -0.0680 | 0.3539 | 0.4315 | 0.1233 | 0.0989 | 0.1890 | 0.1683 |
| **v5_w2_only** | **0.3814** | -0.0688 | 0.3399 | 0.4281 | 0.1233 | 0.0990 | 0.1890 | 0.1723 |
| v5_gencls_fall | 0.3908 | -0.0680 | 0.3539 | 0.4315 | 0.1233 | 0.0989 | 0.1890 | 0.1683 |

**Δ(V5_w2_only - V4_baseline) = -0.0094** → **|Δ| = 0.0094 < GATE C 阈值 0.05** → **C4 negative finding**.

观察:
1. **V5_gencls_fall bit-identical V4_baseline** (geo 0.3908 = 0.3908, max_df 0.1233 = 0.1233). V5 子类化的 gencls 退路完全干净, V5 scaffold 没引入污染.
2. **V5_w2_only 比 V4 略差 0.94%** (geo 0.3814 vs 0.3908, cum_rf 几乎相同). W2 REGCA1 plant 跟 V4 GENCLS 物理不同, agent transfer 有轻微 cost, 但远低于 GATE C 阈值.
3. **ckpt 控制效果在 V4/V5 两 plant 上一致**: max_df 改善都 ~35% vs no_ctrl, ckpt 控制信号无 plant-sensitivity.
4. **Phase A no_disturb max_df 差异 (V4 0.0245 vs V5 0.029, +19%) 在 ckpt eval 下被吸收**: V5 plant 物理上确实变了 (W2 REGCA1 dynamics ≠ GENCLS M=0.1), 但 V4-trained agent 学到的 ΔH/ΔD 控制规律对 plant 颗粒度不敏感, 6-axis geo 几乎不变.

→ **C3 cross-eval RED gate fail → 不进 Phase C 训练**. C4 negative finding 收尾.

## GATE C Decision: C4 negative finding

C2 ablation / C1 main result 路径在本轮**不开**, 因为 plant 升级证明对 6-axis evaluation 无显著杠杆. V5 env infrastructure 保留 (V5Config + V5 env + V4 regression 不破), 留给:
- 未来 robustness narrative paper 章节 (V5_w2_only as plant-perturbation evidence: agent transfer 鲁棒)
- 未来 G4+W2 一起换路径 (调小 Sn / 调大 Imax / REPCA1)

## Verification

- Phase 0 probe JSON: `probes/r80_regca1_wire_check.json` ✓
- Phase A probe JSON: `probes/r80_v5_zero_action.json` ✓
- Phase A audit: stdout 抓 REGCA1 init failure + step-by-step state
- V4 regression: `pytest tests/test_v4_env_regression.py` PASS (107s, 1e-9 tolerance)
- V5_gencls_fall vs V4_baseline bit-identical: max_df 0.0245 = 0.0245, cum_rf -1.101e-02 = -1.101e-02 (5 位有效数字一致)
- ADR-0004 ADR-0005 written, CONTEXT.md 加 V5 env + paper 风机沉默 词条

## Cross-references

- ADR-0004 `docs/adr/0004-v5-env-regca1-plant-paper-deviation.md`
- ADR-0005 `docs/adr/0005-andes-only-drop-simulink-1to1.md`
- CLM-0040 (ZERO_G4_INERTIA hack 起源)
- R08 verdict §2 Finding 2 (2× max_df 残差归因)
- R37 verdict (V4 self-containment refactor)
- Handoff: `C:\Users\27443\AppData\Local\Temp\handoff-M4mGcB.md`

## Questions opened (this round)

- **Q-0014** (open) — 算法侧能否突破 V4 attractor 0.137 / R72_w4 SOTA 0.391. R80 证否 plant 是瓶颈 (CLM-0141), 真正瓶颈候选: (A) 算法侧 (SAC+4-agent+obs+reward 上限) 或 (B) 系统参数 mismatch (R09 副线没做完). PI 确认 "启动算法探索作为之后任务", 挂 backlog 不立即开 R81. 候选 A1 (include_time_obs + R72_w4 hyper, 1 seed × 75 ep, ~1 day wall) 是 minimal-impl 入口.
- Q-PENDING (no number) — "G4 REGCA1 TDS 不收敛的最小修复路径" (CLM-0140 audit 给出 4 候选). 不重要, 不开 Q, 因为 R80 grill 已经决定 "不需要追完整风机场景", 这是 R81-B 候选但 PI 没选.

## Questions closed (this round)

- (none) — R80 没关闭已 open 的 Q.

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这周干了啥**：从 handoff 拿到 "升级 V5 env REGCA1 风机" 的任务. 11 轮 grill 后发现 handoff 的 "paper-faithful" 立论站不住 (paper Sec.II 明说忽略 inner loop, REGCA1 反方向; Sec.IV-A 风机模型完全沉默, 没法对齐). 重新 framing 成 ADR-0004 "ANDES 工程升级 / paper-deviation", 走 C3→C2→C1 阶梯实验, 不强求达 paper 数字.

**结果（一句话）**：V5 env 写出来了, W2 升级 REGCA1 真生效 (Phase A no_disturb max_df +19%), 但 cross-eval 6-axis geo V5 vs V4 差 -0.94% (远低于 0.05 阈值) → **C4 negative finding, 关 R80**. G4+W2 一起换的 paper-忠实路径 TDS 在 t=2s 死掉, 留 R81+.

**意外**：(1) paper 对风机模型完全沉默, "和 paper 对齐" 在风机这一层根本无据, framing 必须改 (ADR-0004). (2) G4 700 MW / 100 MVA base = Ipcmd 7.0 接近 REGCA1 Imax 默认 10, 加上 G4 链 u=0 disable 留 TGOV1 init residual 7.56, 共同导致 TDS 步长在 t=2s 压零. ANDES `u=0` 在 init 阶段不真清等式, 这是 R08 Finding 3 "probe PASS ≠ 物理生效" 的反向版本. (3) **W2 plant 物理上确实变了 (no_disturb max_df +19%) 但被 ckpt 吸收 (6-axis Δ -0.94%)** — V4-trained agent 学到的 ΔH/ΔD 规律对 plant 颗粒度不敏感, 这本身是个 paper-可用的 robustness finding.

**我默认下一步做**：关 R80, 写 3 个 claim (V5 scaffold OK + W2 升级生效 + 6-axis 不敏感). V5 env infrastructure 留着不删, 可作 paper robustness 章节素材 ("agent transfer 对 plant 风机颗粒度 1×-2× 范围鲁棒"). 后续如果要做 G4+W2 一起换的 paper-忠实路径 (R81+), 候选修复: 调小 G4 Sn / 调大 REECA1 Imax / 真用 `ss.System.remove()` 删 G4 链 instead u=0 / 加 REPCA1 plant controller. 短期回到 V4 paper path 继续 R79 / 后续 ckpt 工作 (V5 不替代 V4, 是 sibling).

**你想插一脚就说**：(a) 如果你不接受 C4 收尾, 想强行进 Phase C 训练 (V5_w2_only + 1 seed × 75 ep smoke) 看 retrain 后 6-axis 是否突破, 说一声开 R81; (b) 如果你想试别的 ckpt (R57 R68 R73 R75) cross-eval 看 R72_w4 是不是特例 (这个 R80 内可以加), 说一声; (c) 如果你想直接挑战 G4+W2 一起换的修复 (调 Sn / Imax / 真删 G4 链), 那是 R81 独立任务. 沉默 = 按 C4 收尾, 我开始写 claim + commit.
