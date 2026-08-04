---
round: R302
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R302 plan — 向量 EVAL 与训练放行门

**Opened**: 2026-08-03
**Driver**: R300 的真正向量分布式记录被旧 R278 标量字段误判；先修评估，再判断是否训练。
**Parent**: Q-0059; CLM-0710; CLM-0715.

## TL;DR

不训练。先让 EVAL-v2 显式区分旧标量投影与向量零和执行。只读重放 R300，审计 R294--R301 是否已有 2Kv 解决不了且必须学习的机制；没有就明确 BLOCK。

## 冻结问题

能否在不削弱旧标量契约、不改变 R300 权威结果的前提下，让 EVAL-v2 正确审计真正的四智能体向量执行；当前证据是否已足够冻结一个有必要训练的分布式残差任务？

## Methodology

1. TDD 只测两个公共缝隙：`evaluate_trace_directory` 与 CLI。
2. 默认 profile 保持旧标量投影行为；新增显式向量 profile，复用物理端点、完整配对、60 Hz、来源哈希和储能守卫。
3. 向量 profile 检查四台 ESD1 的 requested/commanded/actual 有功向量、功率/爬坡/SOC/约束和非标量执行；同时要求 M/D `action_norm` 保持零。仅对声明的本地差分控制器，用 `mechanism_trace` 审计附加 residual 的严格零和；公共 DAPI 总有功不要求零和。旧 R278 raw vote/projection 指标标 N/A，不伪造。
4. 对 R300 records 只读重放。场景元数据只能由已存在的 `job.scenario` 规范化进入临时副本或受支持读取路径，禁止改正式记录。
5. 对 R294--R301 当前 claim、formal summary 与 feed 做训练需求审计；EVAL 输出始终是诊断，不取代 formal guard、feed、claim、verdict。

### Outcomes — 预注册判定树

- 默认旧 profile 行为或 fixture 变化 -> `LEGACY-REGRESSION`，停止。
- 向量 profile 需跳过配对、60 Hz、hash、完成、储能或零和守卫才能通过 -> `VECTOR-EVAL-INVALID`，停止。
- 向量 profile 通过 R300，负例失败，但没有已证的 2Kv 剩余机制或学习必要性 -> `EVAL-READY-TRAINING-BLOCKED`。
- 只有同时存在一个 2Kv 可复现失败轴、局部信息必要性、匹配经典基线、冻结动作权限和小探针 kill gate -> `ONE-TRAINING-SMOKE-AUTHORIZED`；训练另开 round，R302 不训练。

## Verification

- `python -m pytest tests/test_eval_v2.py -q`
- 旧默认 profile scorecard 的 schema、contract、validity 与 CLI 回归不变。
- 新向量 profile 对 R300 36/36 完成 records 只读诊断；缺 sidecar、差分 residual 非零和、功率/爬坡/SOC 越界和 M/D 非零负例必须失败。
- `python memory/tools/feed_check.py results/r302_vector_eval_training_gate/FEED.md`
- 全仓 tests、memory tools tests、validate、render、repo health 全绿。

## 资产保护契约

- R294--R301 seals、records、summaries、feeds、claims 只读。
- 不改手稿、环境、训练器、控制器或 paper-cited ranker；不运行 ANDES，不训练网络。
- 只允许修改 EVAL-v2、薄 CLI、聚焦测试、Q-0059/R302 治理和一个 R302 诊断结果根。
- 不把 EVAL 自评升级为论文证据；不作纯架构、MARL、硬解耦、稳定性、拓扑或部署结论。
