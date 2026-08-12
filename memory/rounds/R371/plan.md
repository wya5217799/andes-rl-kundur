---
round: R371
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R371 plan — 逐台能量功率入口的设计与实现契约

**Opened**: 2026-08-12
**Driver**: R370 只选择了条件式方向；必须先把功率命令、无调速器时的转矩入口、逐台映射和能量结算分开，才能判断该对象是否值得进入真实仿真门。
**Parent**: CLM-0565, CLM-0580, CLM-0990, CLM-0995

## TL;DR

本轮完成一个静态设计门和最小可复用实现，不运行 ANDES、不训练。公开 seam 固定为纯函数式 `dispatch` 与 `settle`：前者把四路功率请求投影为受约束的功率命令和逐台绝对 `pref` 写值，后者只用实际读回的入口转矩与转速结算能量。ANDES 适配器只允许通过 `SynGen.set_pref/get_pref` 作用于四个 VSG 索引，并强制旧 M/D 动作为零。若把 `tm0` 直接当成恒功率、使用独立 ESD1、忽略速度换算或不能保持一一映射，则设计停止。

## Snapshot at plan-time (oracle as of 2026-08-12)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0103 closed-negative @ R369, by CLM-0990 — Does one globally fixed local-neighbour per-VSG M/D controller clear the deterministic efficacy and no-harm gate on the balanced development bank, while a bounded non-learning outcome oracle shows at least five percent additional headroom with nonconstant direct actions?
- Q-0102 closed-positive @ R366, by CLM-0980 — Can the fixed-title line freeze a 60-Hz, permission-matched per-VSG inertia/damping comparison contract and a deterministic baseline family that leaves a falsifiable learning gate without importing the old action-object mismatch or claiming storage feasibility?
- Q-0101 closed-positive @ R365, by CLM-0975 — Does the existing ANDES V4 candidate provide four separately addressable VSG agents with independent bounded inertia and damping actions, causal local-neighbour observations, measurable differential dynamics, and nonzero network-transmitted action authority?

## Methodology

1. 静态核对已安装 ANDES 2.0.0：`SynGen.set_pref/get_pref` 无调速器时回落到 `GENCLS.tm0`，值为系统基准标幺；摆动方程使用 `tm`，且 `tm0-tm=0`。记录源码路径与哈希，不运行时域仿真。
2. 固定物理语义：控制器动作是系统基准上的增量有功请求；投影后命令为 `p_cmd`；无调速器的采样保持入口写值为 `tm0_base + p_cmd/omega_sample`；保持期间实际增量功率为 `(tm_actual-tm0_base)*omega_actual`。因此命令功率、写入转矩和实际功率必须分别记录。
3. 复用 `EnergyFeasibleBESSContract` 的逐台功率、爬坡、电流能力、SOC 和能量投影；能量结算只接受实际入口功率，不接受请求值或命令值。
4. TDD seam 已由 R370 路线与本次继续授权确认：`VSGEnergyPortContract.dispatch`、`VSGEnergyPortContract.settle`、`AndesVSGEnergyPortEnv.reset/step`。每个 red-green slice 只写一个公开行为测试，ANDES 作为外部系统用最小 fake adapter，不 mock 自有模块。
5. 新环境采用 wrapper，保持 V4、`base_env.py`、现有 ESD1 环境和旧 checkpoint bit-identical。wrapper 的 `step` 只接收四路功率请求，内部向 V4 传精确零 M/D 动作；返回请求、命令、`pref` 读回、实际入口功率、SOC/能量和约束遥测。
6. 静态 design probe 汇总接口检查、源语义、对象排除项和下一物理门；输出 create-only JSON 与 SHA-256。该输出只判设计是否可进入物理对象测试。

## Gate

- `ENERGY-PORT-DESIGN-PASS`：四路一一映射、功率/转矩/实际功率分离、系统基准单位、正速度换算、零 M/D、实际功率结算、对象排除和 create-only 分析全部通过。
- `STOP-TORQUE-POWER-CONFLATION`：把 `tm0` 写值直接当恒功率或不按实际转速结算。
- `STOP-OBJECT-MISMATCH`：动作进入独立 ESD1、中心标量或非逐台入口。
- `STOP-ENERGY-CONTRACT`：SOC/能量按请求或命令而不是实际功率更新，或逐台约束不可追溯。
- `ANALYSIS-INVALID`：ANDES 版本/源码/哈希、实现测试或输出完整性不通过。
- PASS 只授权后继物理对象门；不授权 ANDES 轨迹、训练、控制增益或论文结果。

## 资产保护契约

- 不改 `base_env.py`、`andes_vsg_env_v4.py`、`andes_vsg_storage_env.py`、训练入口、旧结果、旧 feed、旧 claim 或 checkpoint。
- 允许新增 `control/vsg_energy_port.py`、`env/andes/vsg_energy_port_env.py`、对应定向测试、R371 静态 probe/result/feed/claim/verdict，以及当前线导航同步。
- 不复用 ESD1 的物理对象；只复用其来源已冻结的能量可行投影逻辑。
- 结果目录为 `results/research_loop/r371_vsg_energy_port_design/`，本轮只含静态设计 JSON 与 sidecar，登记 `LOCAL-ONLY`。

## Cross-references

- `CLM-0565`：当前 V4 的 `tm0` 固定且没有独立功率/能量状态，要求模型与执行器修复。
- `CLM-0580`：现有能量投影与慢功率权限只属于独立 GFL ESD1 混合代理。
- `CLM-0990`：直接逐台 M/D 方案保持停止。
- `CLM-0995`：唯一后继方向是 VSG-owned energy-constrained active-power-reference port，先过对象修复门。
