---
round: R418
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-17'
closed: '2026-08-17'
supersedes_rounds: []
superseded_by_round: null
abort_reason: 'sealed runner train-loop defect: the previous executed action was stored
  unflattened ((4,2) into the (8,) replay slot), crashing all nine shards at the first
  store; the rehearsal gap (no store/update path) is codified and the runner fixed;
  successor round re-runs the identical protocol'
superseded_note: null
---
# R418 plan — B1 限速状态感知修复包 (slew-state-aware bundle)

**Opened**: 2026-08-17
**Driver**: 反馈环（owner 指示不间断机制）+ 程序清单 B1（最高单项价值）。
审计的首要假设：执行的是状态化限速投影，而演员状态缺上一执行动作、
目标优化的是未限速输出。文献（
`working/feedback_loop_deep_research_2026-08-17.md` P1）确认该修复为规范
做法且目标-动作语义对齐是承重改动。
**Parent**: CLM-1215 (R410 CANARY-FAIL)、CLM-1220 (R411 幅度稳健)；
program B1 + feedback research doc。

## TL;DR

Workload: `evidence`。Training。唯一变化因子 = 限速状态契约：每个臂的
演员观测增补上一拍**执行后**（限速投影后）动作（7→9 槽；no-message 臂
的邻居掩码保留、prev-action 不受掩码影响）；目标与在线演员路径经同一
可微限速投影后送入 critic（目标-动作语义对齐）。其余逐字 R402/R410 契
约：三臂 × 种子 401/402/403 共 9 组训练（43,200 交互步/组）、同 8-
profile 分区、同超参/奖励/估计器/guard/checkpoint 规则。新 learner 类
（SlewAwareCDMATD3 / SlewAwareYangScalarTD3，checkpoint schema v2，与
历史 v1 互不误载）+ 新 runner + seal。每 run manifest 增记限速诊断
（饱和率、执行-目标偏差均值，P1 要求）。容量：训练代表性任务阶梯
rungs 1/2/4/8、≥32 任务/rung、R402 实测 RSS 锚半内存规则；封存预算后
以共享驱动分片训练（9 shards = arm|seed），训练完成后单进程 evaluate +
classify。

## Methodology

### Mission boundary

- Outcome: 9 训练 manifest（含限速诊断）+ 240 评估 record + 24
  确定性参照 record + formal_analysis（冻结分类 + B1 决策表：端点 vs
  确定性参照、vs R410、消息增量）+ feed/claim/verdict/LINE 一致关闭。
- Authority: 反馈环 + program B1（creative mode：任何臂通过物理 guard
  或分类翻转 → 记录决策、按证据更新手稿、继续，不暂停）。
- Permitted: learner 追加类 + 测试（冻结类字节不动）、R418 runner +
  测试、results 根 `results/research_loop/r418_slew_state_bundle/`
  （create-only）、共享分片驱动编排训练分片、正常收尾。
- Forbidden: 改冻结 CDMATD3/YangScalarTD3 路径、契约模块、估计器、
  guard、reward；换算法；动 R410/R411 资产；训练期访问评估剖面。
- Terminal: formal_analysis.json 存在且 9+40 文件齐全。

### 冻结协议 (frozen-first)

- 增广：obs_actor = [7 槽行（no-message 臂邻居槽置零）, prev_executed
  (2)]，prev_executed 初始为零、每步 = 上一步 projector 输出；评估与
  训练同增广路径。
- 目标语义：replay 存 (obs, prev, executed, r, next_obs, done)；目标
  演员输出加 TD3 噪声后经 `project_slew_torch(prev=本步 executed)` 再
  进目标 critic；在线演员目标同投影后再进 critic。投影 = clamp 限速
  数学（与运行时投影器一致，除其 float32 保守 1-ULP 记账）。
- 超参/奖励/种子/预算/checkpoint 规则 = R402 契约逐字；actor 输入 9、
  critic 输入不变（4×7+4×2）。
- 限速诊断（P1 预注册）：每 run 记录 slew_saturation_rate（|Δ执行| 达
  限速界的步占比）与 execution_mismatch_mean（|执行−目标| 均值）。
- 分片：训练 9 shards（id = `<arm>|<seed>`）；evaluate 单进程；resume
  规则同 R411（缺失文件补写）。

## Gate

- 分类树 = 冻结 `classify_canary`（阈值逐字 R401 契约）。
- **主预注册测量**: 三臂端点 vs 确定性参照、vs R410 三臂中位（
  R410 endpoint_table.json 只读引用）、修复包下消息增量（R410
  median-then-ratio 公式）。
- **B1 决策规则（预注册）**: 任臂全部物理 guard 通过或分类翻转
  （CANARY-PASS）→ 记录为包效应翻转、按证据更新手稿、继续（creative
  条款）；仍 CANARY-FAIL → 报告（对论文加一句话：修复包未翻转判负，
  限速状态假设被弱化）+ 限速诊断表。
- 环境锚：确定性参照记录应与 R410 逐位一致（env 未变）；学习臂无漂移
  锚（单因素改变训练路径）。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r418_slew_state_bundle.py --shards tmp/andes/r418_train_shards.json --workers <ladder> --round R418` (9 train shards, driver = launcher, budget 内) + `... run_r418_slew_state_bundle.py evaluate` (单进程) + `... classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r418_slew_state_bundle.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + source/parent/runtime snapshot + 每臂 1 步真实增广 rollout（掩码与投影路径 exercised）+ save/load roundtrip；不创建 formal artifact。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R418/capacity_evidence.json
- host_process_budget: 9
- wsl_python_processes: 9
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- 保留 dirty worktree；不 reset/clean/stage/commit。
- 冻结 learner 类/契约/估计器/guard 字节不动；R410/R411 资产只读。
- paper-cited 资产（base_env / andes_vsg_env_v4 / train.py /
  paper_grade_axes.py）只读。
- 新文件仅: learner 追加类 + tests、run_r418 runner + tests、R418
  results 根（create-only）、ledger/feed/手稿收尾文件。
- 训练分片日志与容量痕迹非 claim-bearing（tmp/andes +
  memory/rounds/R418）。

## Cross-references

- CLM-1215 (R410)：被修复基线与其端点表。
- CLM-1220 (R411)：判负的幅度稳健性。
- program B1 + `working/feedback_loop_deep_research_2026-08-17.md` P1。
- R402 容量锚 `memory/rounds/R402/capacity_evidence_v2.json`。
