---
round: R421
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-17'
closed: '2026-08-17'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R421 plan — B3 诊断插桩重跑（R410 束，log-only）

**Opened**: 2026-08-17
**Driver**: 反馈环 + program B3：完整训练曲线是复现规范（Henderson 等，
*Deep RL that Matters*, AAAI 2018），当前只保留末 20 幕成本/乘子，无法
定位失败机制；R420 目标修复负结果（CLM-1250）证明"缺动作惩罚"假设不
成立，在下一轮目标修复前必须先拿到逐 update 诊断曲线。本轮回跑
repaired no-message / message 两臂 × 种子 401/402/403（6 组），带只读
诊断插桩，产出机制假设（假设非归因）。
**Parent**: CLM-1215 (R410 基线/锚)；CLM-1245 (R419)；CLM-1250
(R420 负结果)；program B3 + feedback research P3。

## TL;DR

Workload: `evidence`。Training（log-only）。唯一变化因子 = 记录：诊断
learner 子类（DiagnosticCDMATD3）逐位复现 R410 冻结计算路径 + 只读插桩
（critic/actor 损失、Bellman 残差统计、分模块对数梯度范数、TD-error 分布
与采样状态方差等回放覆盖代理）；记录绝不消耗 RNG 流。**位一致预注册锚**：
每 run 的 final.pt 必须与 R410 密封 checkpoint 字节相同（sha256 相等）——
记录不扰动训练的机器证明。协议其余逐字 R410（掩码修复、种子 401/402/403、
43,200 步/组、同超参/奖励/调度）。完成判据 = 6 组逐 update CSV + hashed
汇总 JSON（含 P3 预注册读数-失败类映射）。预算：训练阶梯 rungs 1/2/4/8
后封存。

## Methodology

### Mission boundary

- Outcome: 6 run manifest（含 CSV sha256）+ diagnostics.csv × 6 +
  formal_analysis（汇总 + R410 字节锚判定）+ feed（含机制假设注）/
  claim/verdict/LINE 一致关闭。
- Authority: 反馈环 + program B3（creative 条款）。
- Permitted: 诊断 learner 子类（已实现、位一致测试绿）+ runner
  `scripts/run_r421_diagnostics.py` + 测试、results 根
  `results/research_loop/r421_diagnostics/`（create-only）、共享分片驱动
  编排 6 训练分片、正常收尾。
- Forbidden: 改冻结 learner 路径/契约/奖励；训练期访问评估剖面；对
  R410 密封资产任何写入。
- Terminal: formal_analysis.json 存在且 6 组 CSV+manifest 齐全。

### 冻结协议 (frozen-first)

- 诊断字段 DIAGNOSTIC_FIELDS（16 字段，seal 校验）：update_count、
  critic_loss、actor_loss_mean、lagrange、残差 mean/abs_max/std/q25/
  q50/q75、critic/actor 对数梯度范数 mean/max、td_error_std、
  sampled_state_variance_mean。
- P3 预注册读数规则（进 seal）：reward 曲线升而 guard 仍失败 →
  目标-判决不匹配；训练中发散 → 优化失败；残差上升 + 回报平台 →
  价值估计失败；actor 梯度消失 → 策略停滞；TD-error 分布塌缩/状态
  方差停滞 → 探索/覆盖失败。
- 位一致锚：final.pt sha256 == R410 同臂同种子 final.pt sha256；
  任一不匹配 → DRIFT 记录并调查。

## Gate

- 无冻结分类器消费；判定 = 锚判定 + 诊断汇总 + 机制假设注（假设级，
  不写成归因）。预注册失败 flag：run invalid / TDS 失败 → 如实记录。
- 预注册分支：锚判定 R410-BIT-IDENTICAL = 记录不扰动训练，诊断曲线
  可信，按 P3 读数规则写机制假设；DRIFT = 记录每臂漂移并调查（报告，
  不隐藏）。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r421_diagnostics.py --shards tmp/andes/r421_train_shards.json --workers <ladder> --round R421` (6 train shards) + `... run_r421_diagnostics.py summarize`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r421_diagnostics.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + snapshot + 两臂各 1 步真实 rollout + replay store + update（含诊断字段产出）+ save/load roundtrip；不创建 formal artifact。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R421/capacity_evidence.json
- host_process_budget: 9
- wsl_python_processes: 9
- native_threads_per_process: 1
- other_reserved_processes: 0

## 执行修正（只增派生视图，不改科学契约，R419 probe 先例）

- 封存 runner 的 summarize 只做 R410 字节锚判定 + 汇总；P3 预注册读数
  规则（机制假设）的确定性实现不在 runner 内。
- 修正：新增只读分析探针 `probes/r421_diagnostics_readout.py`——对 6 个
  封存 diagnostics.csv 施加预注册读数-失败类映射（数值阈值在看最终曲线
  之前冻结：优化失败 = critic_loss Q4 > 3×Q1；价值估计失败 =
  bellman_residual_mean Q4 > 1.25×Q1；策略停滞 = actor_grad_norm_mean
  Q4 < 0.5×Q1；探索塌缩 = td_error_std 或采样状态方差 Q4 < 0.5×Q1；
  Q1/Q4 = 前/后 25% 有效 update 的中位），写入
  `results/research_loop/r421_diagnostics/diagnostic_readout.json`
  （create-only, hashed）。输出为机制假设（假设非归因）；训练/评估
  路径、锚判定、分类器全部不变。

## 资产保护契约

- R410 资产只读（anchor 只读引用）；冻结 learner 字节不动（诊断子类在
  独立模块 `cd_matd3_diagnostics.py`）；paper-cited 资产只读；dirty
  worktree 保留。
- 新文件仅: run_r421 runner + tests、R421 results 根（create-only）、
  ledger/feed/手稿收尾文件。

## Cross-references

- CLM-1215 (R410)；CLM-1245 (R419)；CLM-1250 (R420)；
  program B3；`working/feedback_loop_deep_research_2026-08-17.md` P3；
  tests/test_cd_matd3_diagnostics.py（位一致证明）。
