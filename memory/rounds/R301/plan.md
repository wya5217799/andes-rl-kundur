---
round: R301
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R301 plan — 相对 RoCoF 增益的模型门

**Opened**: 2026-08-03
**Driver**: 2Kv 已通过独立 eval，但其增益来源不是稳定性推导；先算清楚，再决定是否做一次更高增益探针。
**Parent**: Q-0058; CLM-0710.

## TL;DR

不扫 3Kv/4Kv。先把四本地 DAPI、规则环图、离散 RoCoF 滤波器、ESD1 有功通道写成可审计的小信号模型。模型若不能唯一授权一个候选，保留 2Kv 并停；若能，下一轮只测该候选，随后才允许独立封存 eval。

## 冻结问题

实现的残差是否同时满足：图公共模态严格为零、差分通道在目标频带耗散、固定锚点闭环无新增不稳定模态；以及这些结果能否给出 2Kv 之后唯一、前瞻的增益候选或充分性停止点？

## Methodology

1. 写纯计算模块，精确计算规则无向图拉普拉斯的公共核与差分特征值。
2. 从实现式 `r[k]=alpha r[k-1]+(1-alpha)(f[k]-f[k-1])/T` 推导并数值审计单位圆频响；同时给出理想连续摆动模态的 Routh 条件。
3. 用 R294 固定锚点 122 维矩阵、四个 ESD1 `Ipout_y` 输入状态、四个 DAPI 积分状态和四个滤波状态构造 0.2 s 采样闭环。该项只作局部小信号诊断，不升级为稳定性证书。
4. 对已完成 R300 records 跑 EVAL-v2；其输出只住 `tmp/R301/`，不得覆盖 formal summary、claim 或 feed 权威。

### Outcomes — 预注册判定树

- 图公共核或严格零和失败 -> `INVALID-CONTROLLER-SEPARATION`，禁止新仿真。
- 实现的数字滤波器在注册目标频带出现负实部，或 2Kv 固定锚点诊断新增单位圆外极点 -> `MODEL-NO-GO`，禁止增益升级。
- 理想模型只证明非负增益耗散、却不给有限最优/上界，且 2Kv 已使锚点动态差分支路不弱于静态同步支路 -> `2KV-SUFFICIENT-NO-BLIND-ESCALATION`。
- 只有模型产生一个离散、唯一、且高于 2Kv 的候选，同时保持差分目标频带正实与固定锚点稳定，才 -> `ONE-NONLINEAR-PROBE-AUTHORIZED`。候选不能由 R300 端点挑选。
- R301 内不运行该候选的 ANDES 性能轨迹；若授权，另开选择 round，且通过后再开 disjoint formal eval。

## 数值与范围

- 固定 `T=0.2 s`, `tau=0.2 s`, `Kp=2`, `Ki=0.2`, `Ksync=1`, `Kconsensus=1/s`，通信图为四节点规则环。
- 目标频带 `0.2--1.5 Hz`，锚点模态 `1.1352719219 Hz`；只报告该固定 modified Kundur 平衡点附近的小信号量。
- 2Kv 指总增益 `0.4884814249924001 system-pu s/Hz`。不从 R300 结果反推阈值。
- EVAL-v2 为诊断层；正式性能只由 R300 formal summary 与 guard 权威承担。

## Cross-references

- 权威性能基线：`results/r300_fixed_2kv_formal/formal_summary.json`。
- 固定锚点模型：`results/r294_model_validation/stage_a/records/16__fixed_lti_anchor.json`。
- 当前最强已注册基线：CLM-0710。

## 资产保护契约

- R294--R300 seals、records、summaries、feeds、claims 全部只读。
- 新增只允许 Q-0058/R301 状态、一个可复用纯计算模块、一个结论判定 probe、聚焦测试、一个 R301 结果 JSON 及 sidecar、feed/claim/verdict。
- 不改任何手稿，不训练网络，不运行多拓扑，不制造 MARL 或硬解耦结论。
