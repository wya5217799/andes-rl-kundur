---
round: R424
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-17'
closed: '2026-08-17'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R424 plan — 反馈环：护栏对齐动作约束轮（owner 优化算法指令）

**Opened**: 2026-08-17
**Driver**: 反馈环（creative 条款）+ owner 指令 2026-08-17（按 GPT Pro A1/A2
答复优化算法）。R423（CLM-1270）实测：修估价（critic 梯度裁剪）压发散
5-15x 但未达 3x 停门，动作压力护栏 36/36 在 R419/R420/R422/R423 四轮
纹丝不动；理论层（CLM-1275 + NOTE-0029 A2.3）证明训练约束里根本没有
动作压力统计量——固定 effort 是 regularizer 不是 dual variable。本轮单
因素 = 把动作压力护栏的统计量直接写进训练目标：CD actor 目标加两个
解析项（执行后动作平方能量 = 护栏 RMS 分子统计量；逐步动作变化绝对值
= 护栏 TV 增量统计量），各配一个按回合用对偶上升更新的投影乘子
（μ_RMS、μ_TV），相对残差对冻结的确定性参照阈值归一。奖励 seam 回
R419 逐字（全轮无 action-effort 项，移除 R422 预算混淆）；scalar 臂逐字
R419（字节锚 vs R419 scalar checkpoints）。
**Parent**: CLM-1270 (R423)；CLM-1275 (模态理论层)；NOTE-0029（GPT Pro
A1/A2 答复）；校准日志 2026-08-17 联合选轮条目。
**Concurrency**: 独占轮（other_reserved_processes: 0）。

## TL;DR

Workload: `evidence`。Training。唯一变化因子 = 护栏对齐动作约束机制
（两个解析动作压力项 + 两个按回合投影乘子；冻结超参：μ step 0.05、
μ max 10.0、init 0、相对残差、harm factor 1.10/1.10、ε=1e-9）。奖励
seam = R419 逐字（无 effort 项）；scalar 臂 learner+奖励逐字 R419
（字节锚）；R419 束（9 槽增广、掩码、种子 401/402/403、43,200 步/组、
同超参/估计器/guard/checkpoint）逐字。参照阈值：确定性控制器在 4 个
发展剖面上按护栏公式实测（RMS_ref、每场景 TV 均值），prepare 时冻结为
hashed JSON。预注册判定：任臂全 guard 通过或分类翻转 → 修复确认 → 记录
并按证据更新手稿（creative 条款）；仍 CANARY-FAIL → 报告 + 端点/guard
分布对 R419/R420/R422/R423 四基座对照 + μ 轨迹与残差读数（见 Gate）。
预算：独占阶梯 rungs 1/2/4/8/12/16 后封存；9 shards 共享驱动单波；
串行 evaluate + classify。

## Methodology

### Mission boundary

- Outcome: 9 manifest（μ_RMS/μ_TV 轨迹、残差、critic-loss 趋势、限速
  诊断）+ 240 评估 + 24 确定性 record + 冻结参照阈值 JSON +
  formal_analysis（冻结分类 + 端点/消息增量/限速诊断表 + vs
  R419/R420/R422/R423 四基座中位对照 + μ/残差读数）+ feed/claim/
  verdict/LINE 一致关闭。
- Authority: 反馈环（creative 条款；owner 优化算法指令 2026-08-17）。
- Permitted: 新 learner 模块（guard 子类，独立文件）、runner
  `scripts/run_r424_guard_aligned_constraints.py` + 测试、results 根
  `results/research_loop/r424_guard_aligned_constraints/`（create-only）、
  共享分片驱动、正常收尾。
- Forbidden: 改 cd_matd3.py / cd_matd3_vfix.py 字节（R419/R423 seal
  依赖）；改 R419-R423 runner/契约模块；换算法；训练期访问评估剖面；
  scalar 臂 learner/奖励改动；动 paper-cited 资产。
- Terminal: formal_analysis.json 存在且 9+40 文件齐全 + 参照阈值 JSON。

### 冻结协议 (frozen-first)

- 修复点：CD actor 目标（`GuardConstrainedSlewAwareCDMATD3.update`，
  `src/andes_rl_kundur/agents/cd_matd3_guard_constraints.py`）在
  `loss = -mean(Q_d + λ·Q_c)` 上追加两项，都在执行后（post-slew）动作
  行上计算（与护栏读取的 trace 完全一致）：
  - RMS 项 = mean(row²)（护栏 action-RMS 分子的逐步统计量）；
  - TV 项 = mean(|row − prev_row|)（护栏每场景 TV 的逐步增量）；
  权重 = 乘子 μ_RMS、μ_TV。
- 对偶：每回合 runner 按护栏公式累积 episode 统计量，相对残差 =
  mean_t mean_{i,d} a² / max((1.10·RMS_ref)², ε) − 1 与
  Σ_t mean_{i,d}|Δa| / max(1.10·TV_ref_sm, ε) − 1；μ ← clip(μ +
  0.05·residual, 0, 10)。
- 参照阈值：`reference_action_stats.json` 在 prepare 时由确定性控制器
  在 4 个发展剖面实测（护栏同款公式），hashed 冻结进 seal。
- 奖励 seam = R419 逐字（physical_costs，无 effort 项）；λ 机制逐字
  R419（budget 3.0、step 0.05、max 10、init 1.0）。
- 锚：scalar 臂 3 组 checkpoint sha256 == R419 同臂同种子（机检，
  不匹配 = invalid_reason）；确定性参照评估逐字不变。
- 读数：critic-loss 趋势（R423 同款 Q4/Q1 规则）+ μ_RMS/μ_TV 轨迹与
  残差（manifest 最后 20 回合）+ 限速诊断。
- 其余 = R419 逐字（增广、投影语义、掩码、超参、种子、调度、诊断）。

## Gate

- 分类树 = 冻结 classify_canary（同 R419-R423）。
- Outcomes (pre-registered, decision tree): CANARY-PASS 或任臂全 guard
  通过 = 修复确认 → 记录、按证据更新手稿、继续；仍 CANARY-FAIL = 报告
  + 端点/guard 分布与 R419/R420/R422/R423 对照 + μ/残差读数（预注册
  判据：动作压力护栏失败块数 36 → <36 = 约束机制产生护栏级影响；36 不
  动 = 约束未达护栏层）+ critic-loss Q4/Q1；CANARY-INVALID = 调查。
- 锚：scalar 臂 checkpoint == R419（任何不匹配 = DRIFT）。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r424_guard_aligned_constraints.py --shards tmp/andes/r424_train_shards.json --workers <ladder> --round R424` (9 train shards) + `... run_r424_guard_aligned_constraints.py evaluate` + `... classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r424_guard_aligned_constraints.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + snapshot + 每臂 1 步真实增广 rollout + replay store（填满 batch）+ learner update 演练（CD 臂 guard 项 actor 目标 + μ 更新 seam）+ save/load roundtrip（μ 保留）+ R419 奖励路径。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R424/capacity_evidence.json
- host_process_budget: 17
- wsl_python_processes: 17
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- R419-R423 资产只读（对照与锚只读引用）；cd_matd3.py / cd_matd3_vfix.py
  字节不动（guard 子类在独立模块）；paper-cited 资产只读；dirty
  worktree 保留。
- 新文件仅: guard learner 模块 + tests、run_r424 runner + tests、R424
  results 根（create-only）、ledger/feed/手稿收尾文件。

## Cross-references

- CLM-1270 (R423)；CLM-1275（模态理论层）；NOTE-0029。
- `working/gpt_pro_md_decoupling_a1_a2_answer_2026-08-17.md`（A2.3）。
- `tmp/yang_md_decoupling_marl/r424_candidate_protocol_draft.md`。
- `working/gate_calibration_log.md`（2026-08-17 联合选轮条目）。
