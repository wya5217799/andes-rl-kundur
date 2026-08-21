---
round: R425
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-18'
closed: '2026-08-18'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R425 plan — 符号修正重测：护栏对齐约束惩罚语义（R424 符号缺陷修复）

**Opened**: 2026-08-18
**Driver**: R424 (CLM-1285) 实测密封 learner 把约束项写进 actor 损失负号内
（-mean(Q + λQ_c + μ_RMS·RMS + μ_TV·TV)）→ 梯度下降在最大化动作能量/变化量
（梯度探针内积 −97.6 vs 惩罚方向）→ 约束机制从未按设计被测。本轮单因素 =
把两项移到负号外（惩罚语义），其余逐字 R424/R419，同束重测。owner 订单：
与 R426（B2 五种子）两轮并发，R425 首发（solo 阶梯），R426 声明本轮 17
进程。**语义门**（SKILL.md §2 R424 教训）：plan 写精确公式 + rehearsal 跑
梯度方向探针并留痕 + 定向测试钉方向。
**Parent**: CLM-1285 (R424 符号缺陷)；CLM-1270 (R423)；CLM-1275；NOTE-0029；
校准日志 R424 rehearsal-scope 行。
**Concurrency**: 首发独占封存（other_reserved_processes: 0）；R426 并发加入
时由其 plan 声明本轮的 `wsl_python_processes: 17`，属已声明变更，非静默改动。

## TL;DR

Workload: `evidence`。Training。唯一变化因子 = 约束项符号（从负号内移到
负号外，惩罚语义），损失公式精确如下（语义门要求）：

```
loss = -mean(Q_d + λ·Q_c) + μ_RMS·mean(row²) + μ_TV·mean(|row − prev|)
```

row = project_slew_torch(prev, raw)（执行后 post-slew 动作行，与护栏读取
trace 逐字一致）；μ 机制逐字 R424（step 0.05、max 10、init 0、相对残差）。
奖励 seam = R419 逐字（无 effort 项）；scalar 臂 learner+奖励逐字 R419
（字节锚）；R419 束（9 槽增广、掩码、种子 401/402/403、43,200 步/组、
同超参/估计器/guard/checkpoint）逐字。参照阈值按 R424 同款流程在 prepare
时重测、hashed 冻结。预注册判定（对照 = R424 同束反号）：动作压力失败块
36 → <36 = 符号修正产生护栏级影响；仍 36/36 = 惩罚语义下约束仍未达护栏
层；μ/残差轨迹与 R424（μ 顶满 10、RMS 残差 38.3–90.8）对照；critic Q4/Q1
与 R424 同束基线 5.98–9.61 对照。预算：solo 阶梯 rung 16 封存 17 进程；
9 shards 单波；串行 evaluate + classify。

## Methodology

### Mission boundary

- Outcome: 9 manifest（μ_RMS/μ_TV 轨迹、残差、critic-loss 趋势、限速诊断）
  + 240 评估 + 24 确定性 record + 冻结参照阈值 JSON + formal_analysis
  （冻结分类 + 端点/消息增量/限速诊断 + vs R424/R419/R420/R422/R423 中位
  对照 + μ/残差读数）+ feed/claim/verdict/LINE 一致关闭。
- Authority: 反馈环（creative 条款）+ owner 订单 2026-08-18（修 R424 符号
  缺陷 + 与 R426 并发）。
- Permitted: 新 learner 模块
  `src/andes_rl_kundur/agents/cd_matd3_guard_constraints_vfix.py`（独立
  文件）、runner `scripts/run_r425_guard_constraints_signfix.py` + 测试、
  results 根 `results/research_loop/r425_guard_constraints_signfix/`
  （create-only）、语义门工具 `memory/tools/objective_semantics_lint.py`、
  正常收尾。
- Forbidden: 改 cd_matd3.py / cd_matd3_vfix.py /
  cd_matd3_guard_constraints.py 字节（R419/R423/R424 seal 依赖）；改
  R419-R424 runner/契约模块；换算法；训练期访问评估剖面；scalar 臂
  learner/奖励改动；动 paper-cited 资产。
- Terminal: formal_analysis.json 存在且 9+40 文件齐全 + 参照阈值 JSON。

### 冻结协议 (frozen-first)

- 修复点：`GuardConstrainedSlewAwareCDMATD3Signfix.update`（
  `src/andes_rl_kundur/agents/cd_matd3_guard_constraints_vfix.py`）的 actor
  目标 = 上记精确公式；两项都在执行后（post-slew）动作行上计算：
  RMS 项 = mean(row²)；TV 项 = mean(|row − prev_row|)；权重 = 乘子
  μ_RMS、μ_TV（负号外 = 惩罚）。
- 对偶：每回合 runner 按护栏公式累积 episode 统计量，相对残差 =
  mean_t mean_{i,d} row² / max((1.10·RMS_ref)², ε) − 1 与
  Σ_t mean_{i,d}|Δrow| / max(1.10·TV_ref_sm, ε) − 1；μ ← clip(μ +
  0.05·residual, 0, 10)。**口径声明（审稿疑点 1）**：RMS 用时间平均能量、
  TV 用逐步变化总和——聚合口径不同是有意的，与护栏定义逐字一致；各自
  参照（RMS_ref = 确定性参照能量时间平均的平方根；TV_ref_sm = 参照每
  场景 TV 的均值）用同口径实测，残差无量纲。
- 参照阈值：`reference_action_stats.json` 在 prepare 时由确定性控制器在 4
  个发展剖面实测（护栏同款公式），hashed 冻结进 seal。
- 奖励 seam = R419 逐字（physical_costs，无 effort 项）；λ 机制逐字 R419
  （budget 3.0、step 0.05、max 10、init 1.0）。
- 锚：scalar 臂 3 组 checkpoint sha256 == R419 同臂同种子（机检，不匹配 =
  invalid_reason）；确定性参照评估逐字不变。
- 读数：critic-loss 趋势（R423 同款 Q4/Q1 规则）+ μ_RMS/μ_TV 轨迹与残差
  （manifest 最后 20 回合）+ 限速诊断。**critic 基线声明（审稿疑点 2）**：
  R424 实测 R419 基座无裁剪 Q4/Q1 = 5.98–9.61（同束基线）；R423 feed 的
  "未裁剪 24.4–126.4x" 是 R410 族旧基座读数（CLM-1255，跨束 indicative），
  不用于本轮同束对照。
- 语义门（SKILL.md §2）：rehearsal_checks 含 `penalty_direction_probe`；
  rehearsal 在真实 learner 上跑梯度方向探针并把数值写进 rehearsal JSON；
  定向测试钉同一方向；收尾前跑 `objective_semantics_lint.py R425`。
- 其余 = R419 逐字（增广、投影语义、掩码、超参、种子、调度、诊断）。

## Gate

- 分类树 = 冻结 classify_canary（同 R419-R424）。
- Outcomes (pre-registered): CANARY-PASS 或任臂全 guard 通过 = 修复确认 →
  停 claim gate 问 owner（B1 约定）；仍 CANARY-FAIL = 报告 + 端点/guard
  分布与 R424（同束反号）及 R419/R420/R422/R423 对照 + μ/残差读数。预注册
  判据：动作压力失败块数 36 → <36 = 符号修正产生护栏级影响；36 不动 =
  惩罚语义下约束仍未达护栏层；μ/残差对 R424 的"顶满 10 + 残差 38.3–90.8"
  解读（惩罚语义下预期：μ 上升伴残差下降 = 约束绑定；μ≈0 = 训练统计量已
  满足）；critic-loss Q4/Q1 vs R424 同束 5.98–9.61；CANARY-INVALID = 调查。
- 锚：scalar 臂 checkpoint == R419（任何不匹配 = DRIFT）。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r425_guard_constraints_signfix.py --shards tmp/andes/r425_train_shards.json --workers 16 --round R425` (9 train shards) + `... run_r425_guard_constraints_signfix.py evaluate` + `... classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r425_guard_constraints_signfix.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + snapshot + 每臂 1 步真实增广 rollout + replay store（填满 batch）+ learner update 演练（CD 臂 signfix actor 目标 + μ 更新 seam）+ **梯度方向探针（语义门，留痕进 rehearsal JSON）** + save/load roundtrip（μ 保留）+ R419 奖励路径。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence, penalty_direction_probe
- capacity_evidence: memory/rounds/R425/capacity_evidence.json
- host_process_budget: 17
- wsl_python_processes: 17
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- R419-R424 资产只读（对照与锚只读引用）；cd_matd3.py / cd_matd3_vfix.py /
  cd_matd3_guard_constraints.py 字节不动（signfix 子类在独立模块）；
  paper-cited 资产只读；dirty worktree 保留。
- 新文件仅: signfix learner 模块 + tests、run_r425 runner + tests、R425
  results 根（create-only）、语义门工具、ledger/feed/手稿收尾文件。

## Cross-references

- CLM-1285 (R424 符号缺陷)；CLM-1270 (R423)；CLM-1275（模态理论层）；
  NOTE-0029。
- `working/gpt_pro_md_decoupling_a1_a2_answer_2026-08-17.md`（A2.3）。
- `working/gate_calibration_log.md`（R424 rehearsal-scope 行 + owner 并发/
  短预算/研究目的指令）。
- `skills/kundur-round/SKILL.md` §2 目标语义门。
