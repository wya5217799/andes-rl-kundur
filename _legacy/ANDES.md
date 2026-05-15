# ANDES 主线文件索引

> 当前状态：R37 后主线收尾，写论文/答辩阶段（2026-05-08 冻结）
> 运行环境：**WSL ONLY** — 任何 ANDES 脚本必须走 WSL，禁止 Windows Python

---

## 快速入口（新对话必读顺序）

1. `CONTEXT.md` — ANDES 工程事实（round/branch/env/failure/plan 生态）
2. `RESEARCH_TRAIL.md` — 因果链 R01-R37 + 6 拐点（写论文主源）
3. `scenarios/kundur/NOTES_ANDES.md` — 改代码前必读
4. `quality_reports/handoff/2026-05-07_andes_6axis_recovery_handoff.md` — 5 分钟接续包

---

## 环境实现 (`env/andes/`)

| 文件 | 说明 |
|---|---|
| `env/andes/base_env.py` | 基类：step / reset / obs / reward 共享逻辑 |
| `env/andes/andes_vsg_env.py` | Kundur 主环境 v1 |
| `env/andes/andes_vsg_env_v2.py` | v2 |
| `env/andes/andes_vsg_env_v3.py` | v3 |
| `env/andes/andes_vsg_env_v4.py` | v4（最新，R37 所用） |
| `env/andes/andes_ne_env.py` | NE39 环境 |
| `env/andes/andes_ne_regca1_env.py` | NE39 REGCA1 变体 |

---

## 训练脚本 (`scenarios/kundur/`)

| 文件 | 说明 |
|---|---|
| `scenarios/kundur/train_andes.py` | 主训练脚本 |
| `scenarios/kundur/train_andes_v2.py` | v2 |
| `scenarios/kundur/train_andes_v3.py` | v3 |
| `scenarios/kundur/train_andes_v4.py` | v4 |
| `scenarios/kundur/train_andes_warmstart.py` | **R21 warmstart 最优启动** |
| `scenarios/kundur/_legacy_2026-04/` | 归档旧评估脚本（不要 import） |

### 快速启动命令（详见 memory: project_andes_quick_launch.md）
```bash
# WSL 内，V4 warmstart R21，seed s47/s49/s52 并行（上限 3 个）
wsl -e bash -c "cd /mnt/c/Users/27443/Desktop/Multi-Agent\ \ VSGs && ..."
```

---

## 评估单一入口 (`scripts/research_loop/`)

| 文件 | 说明 |
|---|---|
| `scripts/research_loop/eval_paper_spec_v2.py` | **L4 唯一 eval 入口（L4 lock-in 2026-05-07）** |
| `scripts/research_loop/eval_v4_ensemble.py` | HAWE 异构集成（Asset 5） |
| `scripts/research_loop/eval_v4_all_seeds.py` | 全 seed 评估 |
| `scripts/research_loop/eval_v4_no_control.py` | no_ctrl baseline |
| `scripts/research_loop/eval_v4_ddic.py` | DDIC 评估 |
| `scripts/research_loop/eval_v4_ctde.py` | CTDE 评估 |
| `scripts/research_loop/eval_v4_ensemble_stoch.py` | 随机集成 |
| `scripts/research_loop/eval_v4_ensemble_peraxis.py` | 逐轴集成 |
| `scripts/research_loop/eval_n2_fresh_seed_hawe.py` | 新 seed HAWE |
| `scripts/research_loop/eval_freshseed_hawe_sweep.py` | HAWE 扫参 |
| `scripts/research_loop/eval_swa_baseline.py` | SWA baseline |

### Research Round 探针（R01–R37）

| 文件 | Round | 内容 |
|---|---|---|
| `scripts/research_loop/r01_bc_probe.py` | R01 | behavior cloning 探针 |
| `scripts/research_loop/r02_h0_sweep_v2.py` | R02 | H0 扫参 |
| `scripts/research_loop/r03_governor_wire_probe.py` | R03 | governor 接线探针 |
| `scripts/research_loop/r04_adaptive_baseline_eval.py` | R04 | 自适应 baseline |
| `scripts/research_loop/r08_h_scan.py` | R08 | H scan + governor 物理验证 |
| `scripts/research_loop/r10_governor_wiring_forensic.py` | R10 | governor 接线取证 |
| `scripts/research_loop/r11_pi_ac_residual_probe.py` | R11 | PI AC 残差 |
| `scripts/research_loop/r12_ctde_critic_probe.py` | R12 | CTDE critic 探针 |
| `scripts/research_loop/r13_settling_reward_probe.py` | R13 | settling reward |
| `scripts/research_loop/r14_root3_hscan_v3fixed.py` | R14 | root3 H scan v3 修复 |
| `scripts/research_loop/r15_root3_g4_inertia_probe.py` | R15 | root3 G4 惯量 |
| `scripts/research_loop/r16_root3_line_x_probe.py` | R16 | root3 线路 X |
| `scripts/research_loop/r18_reward_decomp_probe.py` | R18 | reward 分解 |
| `scripts/research_loop/r19_wf2_necessity_probe.py` | R19 | WF2 必要性 |
| `scripts/research_loop/r19_v41_audit_probe.py` | R19 | v4.1 audit |
| `scripts/research_loop/r20_governor_params_probe.py` | R20 | governor 参数 |
| `scripts/research_loop/r20_reward_settled_audit.py` | R20 | reward settled audit |

---

## Probe 复用工具层 (`probes/andes_common/`)

> 写新 ANDES probe 前必读 `probes/andes_common/README.md` 决策树

| 文件 | 说明 |
|---|---|
| `probes/andes_common/paper_constants.py` | LS1/LS2 + Fig.6/8 + Eq.12 常量 |
| `probes/andes_common/tracers.py` | run_zero_action_trace / run_h_scan / variant_ablation |
| `probes/andes_common/verdict.py` | ladder resolver |
| `probes/andes_common/utils.py` | introspect_model 等 |
| `probes/andes_common/README.md` | **决策树，必读** |

---

## 6-axis 量化评估 (`evaluation/`)

| 文件 | 说明 |
|---|---|
| `evaluation/paper_grade_axes.py` | **6-axis 评分函数（post-fix patched，论文用）** |
| `evaluation/paper_eval.py` | 评估指标 |
| `evaluation/metrics.py` | 基础指标 |
| `evaluation/runner_helpers.py` | runner 辅助 |

---

## 关键数字（post-fix，2026-05-07 修正，论文用）

| 指标 | 旧值（已推翻） | **正确值** |
|---|---|---|
| R21 single best | 0.613 | **0.444**（4.04× no_ctrl） |
| HAWE w9802 | 0.607 | **0.439**（= 99.3% R21） |
| no_ctrl baseline | 0.110 | **0.104** |

---

## 训练日志 (`logs/`)

| 目录/文件 | 说明 |
|---|---|
| `logs/v4_ws_r21_2000ep_s47.log` | R21 warmstart seed 47，2000 轮 |
| `logs/v4_ws_r21_2000ep_s49.log` | R21 warmstart seed 49，2000 轮 |
| `logs/v4_ws_r21_2000ep_s52.log` | R21 warmstart seed 52，2000 轮 |
| `logs/r37_*/` | R37 并行训练日志 / pid / launch 脚本 |
| `logs/v4_1_phi_rescale/` ~ `logs/v4_9_warmstart/` | v4 各并行 run |

---

## 文档 / Handoff / Audit

| 文件 | 说明 |
|---|---|
| `scenarios/kundur/NOTES_ANDES.md` | **改代码前必读（6-axis 修正 + L4 重构）** |
| `docs/paper/andes_replication_status_2026-05-07_6axis.md` | **当前复现状态权威文档** |
| `quality_reports/handoff/2026-05-07_andes_6axis_recovery_handoff.md` | 最新 handoff（5 分钟接续） |
| `quality_reports/handoff/2026-05-07_andes_path_closure.md` | 路径关闭记录 |
| `quality_reports/handoff/2026-05-07_andes_v41_reward_paradox_handoff.md` | reward paradox 分析 |
| `quality_reports/audits/2026-05-07_andes_6axis_failure_analysis.md` | 6-axis 失败分析 |
| `quality_reports/audits/2026-05-07_andes_paper_alignment_root_cause.md` | paper 对齐根因 |

---

## 辅助脚本 (`scripts/research_loop/`)

| 文件 | 说明 |
|---|---|
| `scripts/research_loop/dump_eval_v4_ranking.py` | 输出 eval ranking |
| `scripts/research_loop/dump_per_axis_breakdown.py` | 逐轴分解 |
| `scripts/research_loop/dump_principal_gini_table.py` | Gini 表 |
| `scripts/research_loop/dump_n2_freshseed_scores.py` | 新 seed 评分 |
| `scripts/research_loop/dump_freshseed_sweep.py` | HAWE 扫参输出 |
| `scripts/research_loop/analyze_per_agent_contribution.py` | 每智能体贡献分析 |
| `scripts/research_loop/experiment_r36_ranker_tuning.py` | R36 ranker 调参 |
| `scripts/research_loop/check_state.py` | 状态检查 |
| `scripts/research_loop/state_io.py` | 状态 I/O |
| `scripts/research_loop/k_max_calc.py` | k_max 计算 |

---

## 结果文件

| 路径 | 说明 |
|---|---|
| `results/andes_paper_alignment_6axis_2026-05-07.json` | 21 ckpt 完整 6-axis ranking |
| `logs/n2_fresh_seed/` | 新 seed 训练结果 |
| `paper/figures/v4_ddic_*/` | 各 variant 论文图 |
