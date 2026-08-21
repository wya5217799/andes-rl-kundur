---
round: R435
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-19'
closed: '2026-08-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R435 plan — 预算机制因果验证轮（R432 假设的乘子地板单因子测试, owner 批准）

**Opened**: 2026-08-19
**Driver**: owner 批准 2026-08-19（"尽量提高硬件利用率" + 审稿风险分析第 4 项;
任务替补指令: 任务结束立即启动新任务）: R432 (CLM-1320) 的 B3 遥测显示
lagrange 乘子从 ~0.97 衰减到 ~0.0（4/6 组）而逐回合公共成本持平（0.7-3.8,
1440 回合中 81-480 回合超 3.0 预算）, 其有界假设 "预算机制过早停止施压,
故无信号驱动公共频率成本下降" 登记为 future single-factor round — 本轮即该
因果测试。**无人值守启动**: owner 预授权（2026-08-19 铁律: 09:00 后 agent
停止, 仿真自动跑满硬件）; R433 gate（pause branch / CANARY-INVALID）由
自动化强制, 任一触发即停、请示 owner。
**Parent**: R432/CLM-1320 (B3 遥测 + 假设), R410 (冻结束),
R433 (训练波次结束后的硬件窗口)。

## TL;DR

Workload: `evidence`; frozen training round. Single factor vs R432: the
frozen dual update's lower clip moves from 0.0 to the pre-registered floor
1.0 (the multiplier's starting level), so the budget mechanism keeps
pressing at the initial pressure for the whole run; everything else
R432-verbatim (same bundle, seeds 401-403, B3 telemetry).  Paired R432
runs are the no-floor control; the classify applies the pre-registered
judgement (supported / refuted / invalid).

## Methodology

- Runner `scripts/run_r435_multiplier_floor.py` = 导入冻结 R432 runner
  （只读）, 仅补丁其模块全局 `_agent_for` → `_floored_agent_for`（R410
  `_agent_for` 逐字复制 + `R435-SEAM` 类交换: CD 臂用
  `FlooredCDMATD3`）。训练循环与 B3 遥测 = R432-verbatim（零复制, 无漂移
  面）; 冻结 `cd_matd3.py` 字节不变。
- **精确公式（语义门, verbatim）**: `lambda' = clip(lambda + step*(cost - budget), floor, maximum)`,
  其中 `floor = 1.0`（冻结初值）, `step = 0.05`, `maximum = 10.0`（R410
  冻结值不变）; 与冻结更新唯一的差异是下界 0.0 → 1.0。actor loss
  `-mean(q1[:,0] + lambda*q1[:,1])` 不变。新模块
  `src/andes_rl_kundur/agents/cd_matd3_multiplier_floor.py`
  （`LagrangeFloorMixin` + `FlooredCDMATD3`, 子类化冻结 learner, R419 教训）。
- 束: R410 修复束（cd_matd3_no_message + cd_matd3_message, seeds 401-403,
  每组 43,200 步, 6 shards）; 同种子 = 同 RNG 流 → R432 配对运行是
  no-floor 对照。
- **预注册判定（classify 内执行, 禁止离线手算）**:
  1. 机械: 全部 6 组 `lagrange_final >= 1.0`（地板保持）→ 否则
     CANARY-INVALID。
  2. 因果主判据（配对 vs R432, 同臂同种子）: R435 终 360 回合
     （episodes 1081-1440）公共成本均值 < 0.8 × R432 同窗口均值,
     ≥ 4/6 对 → **SUPPORTED**（活乘子驱动公共成本下降）。
  3. 因果次判据: 组内终四分之一 < 0.8 × 初四分之一（≥ 4/6 组）;
     critic Q4/Q1 vs R432（6.2-30.5）; 超 3.0 预算回合数 vs R432。
  4. 主判据不成立但乘子保持活跃 → **REFUTED**（机制保持施压也不驱动
     成本下降 — 因果主张被证伪, 瓶颈在别处, 如 critic 发散）。
- 容量: reuse R433 capacity evidence（R431 rung-16 链, RUN-READY）after
  fresh no-other-process snapshot; 冻结 15 workers（wsl 16, budget 16,
  reserved 0）。

## Frozen scientific contract

1. 单因子: 乘子地板 1.0（冻结双更新的下界 0.0 → 1.0, 其余逐字）。
2. 束/种子/预算/遥测: R432-verbatim（2 臂 × 3 种子 × 43,200 步）。
3. 对照: R432 配对诊断（同臂同种子, no-floor）。
4. 无 eval / 无分类器 / 无调参 / 无新 bank / 无其它因子。

## Pre-registered decision tree

1. 任一组缺行/非有限/训练未收敛 → CANARY-INVALID, 保留产物, 不重试。
2. 机械检查失败（任一组成终乘子 < 1.0）→ CANARY-INVALID（地板未保持,
   机制未按设计运行）。
3. 主判据 ≥ 4/6 → SUPPORTED: 活乘子驱动公共成本下降（R432 假设因果
   验证成立）; 报告配对表 + 次判据。
4. 主判据 < 4/6 但机械通过 → REFUTED: 机制保持施压不驱动成本下降;
   feed 写回 `refuted` 裁决（external-theory-intake 格式）, 瓶颈定位
   到 critic 发散等次判据。
5. 不授权: 任何调参 / 其它因子 / 重跑 / 改变地板值。

## Capacity and execution card

- 先例证据: R433 capacity evidence（R431 rung-16 链, RUN-READY,
  selected_workers 15）; R435 reuse after fresh no-other-process snapshot。
- Frozen budget: `host_process_budget: 16`, `wsl_python_processes: 16`
  （15 workers + 1 driver）, `native_threads_per_process: 1`,
  `other_reserved_processes: 0`（R434 波次结束后才 seal/launch）。总
  16 <= 32 logical CPUs; 内存: 16 × 0.944 GiB + 3 GiB OS ≈ 18 GiB
  <= 27 GiB WSL MemTotal。
- Ready jobs: 6 train shards 一波 workers=15（~3.2h, R432 单组 ~191 min）,
  然后串行 classify。

Execution readiness 按 capacity/rehearse/prepare 顺序; rehearsal 含
floor_semantics_probe 后 RUN-READY。Sealed concurrency immutable。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r435_multiplier_floor.py reuse-capacity` → `rehearse` → `prepare` → `shards` → `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r435_multiplier_floor.py --shards tmp/andes/r435_train_shards.json --workers 15 --round R435` → `classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r435_multiplier_floor.py rehearse`
- rehearsal_scope: same-pre-attempt-path; source/parent/runtime/output guards + `floor_semantics_probe`（真实 learner 短窗口: 乘子永不 < 地板; 冻结更新在地板上方时两者逐位一致; actor 加权不变）; 无 formal artifact
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence, floor_semantics_probe
- capacity_evidence: memory/rounds/R435/capacity_evidence.json
- host_process_budget: 16
- wsl_python_processes: 16
- native_threads_per_process: 1
- other_reserved_processes: 0

## Theory intake

机制预测（R432 feed 登记的有界假设: "预算机制过早停止施压, 故无信号驱动
公共频率成本下降"）的可观测清单 — 全部进入本轮的 sealed 协议, 由
`classify` 读取, rehearsal 的 floor_semantics_probe 验证可读性:

```
observable: lagrange_final
  definition: 训练结束时的 lagrange 乘子值, 每组一个
  source: diagnostics_summary.json#/lagrange_final
  predicts: >= 1.0（地板保持）in 全部 6 组 → 机械检查通过; 否则 CANARY-INVALID
observable: final_quarter_mean_common_cost
  definition: 逐回合公共成本（episode_rows 第 2 列）末 360 回合均值, 每组一个
  source: diagnostics_summary.json#/episode_rows
  predicts: R435 < 0.8 × R432 同窗口（同臂同种子配对）≥ 4/6 对 → SUPPORTED;
            < 4/6 但机械通过 → REFUTED
observable: within_run_quarter_ratio
  definition: 末 360 回合均值 / 初 360 回合均值, 每组一个
  source: diagnostics_summary.json#/episode_rows
  predicts: < 0.8 在 ≥ 4/6 组 → 次级支持信号
observable: critic_q4_q1
  definition: 逐步 critic loss 的 Q4/Q1 四分位比, 每组一个
  source: diagnostics_summary.json#/critic_loss_q4 / #/critic_loss_q1
  predicts: 报告 vs R432（6.2-30.5）; 持续发散 → 发散为存留机制线索
observable: episodes_above_budget
  definition: 公共成本 > 3.0 的回合数, 每组一个
  source: diagnostics_summary.json#/episode_rows
  predicts: 报告 vs R432（81-480）
```

裁决写回: feed Conclusions/Follow-up 显式给出 `refuted`（主判据不成立）或
`supported` / `undecidable`。

## 资产保护契约

- Byte-unchanged/read-only: R432/R410 sources, seals, results, claims,
  feeds; `cd_matd3.py`, V4 env, classifier, estimators, R410 runner,
  R432 runner 与 B3 诊断数据。
- New only: `cd_matd3_multiplier_floor.py`（子类化新模块）, R435
  runner/tests, R435 lifecycle artifacts, create-only R435 results 与收尾
  ledger/feed/claim。
- Dirty worktree preserved; no reset/clean/stage/commit; no manuscript
  prose。

## Gate calibration target

- 记录: 地板语义门（objective_semantics_lint）、判定门（主/次判据）、
  引用门（R432 对照）是否太硬/太软/刚好。无门在 attempt 内放松。

## Cross-references

- R432/CLM-1320（B3 遥测 + 假设 + follow-up 登记）, R410（冻结束）,
  R433/R434（同一硬件窗口的兄弟轮）, R425/R424（objective-semantics
  门先例）。
- Workflow authority: `paper/yang_md_decoupling_marl/LINE.md`, owner order
  2026-08-19, `CLAUDE.md`, `skills/kundur-round/SKILL.md`。
