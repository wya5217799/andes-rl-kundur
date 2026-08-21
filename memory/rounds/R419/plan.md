---
round: R419
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-17'
closed: '2026-08-17'
supersedes_rounds:
- R418
superseded_by_round: null
abort_reason: null
superseded_note: 'R418 (same B1 protocol) aborted on a sealed-runner train-loop defect:
  the previous executed action was stored unflattened, crashing all nine shards at
  the first replay store. This round re-runs the identical frozen protocol with the
  flattened store and a rehearsal that exercises the replay store and learner update
  seams.'
---
# R419 plan — B1 限速状态感知修复包（R418 后继，同协议）

**Opened**: 2026-08-17
**Driver**: 反馈环 + program B1 后继轮。R418 以 aborted 终止（封存 runner
训练循环把 prev-executed 动作未展平存入 replay，九分片首步全崩；教训：
rehearsal 必须覆盖 replay store 与 learner update 路径，已 codify）。本
轮回跑同一冻结协议，带展平修复与覆盖 store/update 的 rehearsal。
**Parent**: CLM-1215 (R410)、CLM-1220 (R411)；R418 abort 记录（校准日志
2026-08-17）；program B1 + feedback research P1。

## TL;DR

Workload: `evidence`。Training。协议与 R418 逐字相同（见其 plan，本文件
只声明增量）：唯一变化因子 = 限速状态契约（演员观测增补上一拍执行后动
作 7→9 槽、掩码保留；目标/在线演员路径经同一可微限速投影后进 critic）；
三臂 × 种子 401/402/403、43,200 步/组、R402 超参/奖励/估计器/guard/
checkpoint 逐字；每 run manifest 记限速诊断（饱和率、执行-目标偏差）。
**两处修复增量**：(1) 训练循环 store 时 prev-executed 展平为 (8,)
（与 R410 的 action 展平一致）；(2) rehearsal 每臂在真实一步 rollout 后
执行一次 replay store + learner update（buffer 未满时 update 返回 None
也算路径演练），杜绝同类缺陷再次穿透封存。预算阶梯后冻结。

## Methodology

### Mission boundary

- 与 R418 相同：9 训练 manifest + 240 评估 + 24 确定性 record +
  formal_analysis（冻结分类 + B1 决策表 + 限速诊断）+ 正常收尾。
- Authority: 反馈环 + program B1（creative 条款：翻转不暂停、按证据
  更新手稿）。
- Permitted/Forbidden 与 R418 相同；读取 R418 放弃产物不作为证据
  （全新执行，新结果根 `results/research_loop/r419_slew_state_bundle/`）。

### 冻结协议 (frozen-first)

- 与 R418 逐字相同（增广、目标语义、超参、限速诊断、分片 resume）。

## Gate

- 与 R418 相同（冻结分类树 + B1 决策规则 + 确定性参照环境锚）。
- Outcomes (pre-registered, decision tree): CANARY-PASS 或任臂全物理
  guard 通过 = 包效应翻转 → 记录决策、按证据更新手稿、继续；仍
  CANARY-FAIL = 报告（限速状态假设被弱化）+ 限速诊断表；分类
  CANARY-INVALID = 如实记录并调查；环境锚（确定性参照 vs R410）超差 =
  DRIFT 记录。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r419_slew_state_bundle.py --shards tmp/andes/r419_train_shards.json --workers <ladder> --round R419` (9 train shards, driver = launcher, budget 内) + `... run_r419_slew_state_bundle.py evaluate` (单进程) + `... classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r419_slew_state_bundle.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + source/parent/runtime snapshot + 每臂 1 步真实增广 rollout + replay store + learner update 演练 + save/load roundtrip；不创建 formal artifact。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R419/capacity_evidence.json
- host_process_budget: 9
- wsl_python_processes: 9
- native_threads_per_process: 1
- other_reserved_processes: 0

## 执行修正（只增派生视图，不改科学契约，R411/R416 probe 先例）

- P1 文献第 3 条要求记录"策略是否真的使用新增特征"；R419 封存 runner
  只记限速饱和率与执行偏差，不含特征使用消融。
- 修正：新增只读分析探针 `probes/r419_prev_action_ablation.py`——对 9 个
  R419 checkpoint 做 zero-out 特征消融评估（演员输入的 prev-action 槽
  置零，投影器状态与执行路径不变），用同估计器复算端点，与封存 evaluate
  的全特征记录对比，写入
  `results/research_loop/r419_slew_state_bundle/prev_action_ablation.json`
  （create-only, hashed）。预注册解释：消融端点相对全特征端点变差 =
  策略使用了该特征（gap>0）；几乎无差 = 特征未被使用（同样重要）。
  分类器、阈值、guard、训练与评估路径全部不变。

## 执行修正（训练分片重启，只处理启动失败不改科学契约，R410 崩溃隔离先例）

- `cd_matd3_message|403` 分片（第二波）在密封源码校验处被拒：会话期间
  为 B3 预实现的诊断子类被临时追加进 learner 文件，导致 learner 哈希
  偏离 R419 seal；该分片零训练步、零 manifest（仅有 started.json）。
- 修正：learner 文件已恢复至密封字节（sha256 与 seal 记录一致，验证
  通过）；诊断子类改住独立新模块（B3 轮内落地）。实际核查：该分片在
  创建任何产物之前即被拒（无 run_dir、无 started.json），故无需隔离，
  直接以同种子从零重跑一次（等价于冻结契约的 restart 配额 1）。科学
  契约、臂、种子、步数、奖励、判定全部不变；第 8 组已完成 run 不受
  影响。附加记录：恢复过程中一次 Windows 文本写入把 LF 换成 CRLF 导致
  磁盘字节仍漂移，已以精确字节（newline=""）重写并逐字节验证。

## 资产保护契约

- 与 R418 相同。R418 结果根（aborted）与 seal 保留为审计记录。

## Cross-references

- CLM-1215 (R410)、CLM-1220 (R411)；R418 plan（协议真源）+ abort
  reason；program B1 + `working/feedback_loop_deep_research_2026-08-17.md`
  P1；R402 容量锚。
