---
round: R363
state: completed
manuscript_line: decoupling-marl-model-first
opened: '2026-08-07'
closed: '2026-08-07'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R363 plan — common residual-power channel headroom gate

**Opened**: 2026-08-07
**Driver**: 检验 deep-research 方向 2 的机制缺口:零共同残差契约本身是否
限制物理头空间——在动作基中加入共同残差功率通道后,同一开发库的物理
可行场景数是否超过 R358 的 10/16。
**Parent**: Q-0100; CLM-0940 / R358; CLM-0950 / R360; CLM-0955 / R361;
CLM-0960 / R362; CLM-0925 / R352

## TL;DR

Workload: `evidence`(新 QP 分析,动作基从 3 边零共同扩展为 4 通道
共同+3边)。完全复用 R358 的开发案例库、R341 冻结点模型、物理投影与
2% 端点门;唯一变化 = 动作基加入共同残差功率通道(节点动作基
`[ones(4), incidence]` 的 4 列全启用)。逐场景求解同一物理联合端点 QP,
判定 = 4 通道基下物理可行场景数与 R358 的 10/16 对比。可行数严格增加
→ 零共同契约是结构限制,机制缺口确认;可行数不变 → 机制缺口假说被
削弱。无 holdout 读取、无训练、无仿真、无 EVAL。

## Snapshot at plan-time (oracle as of 2026-08-07)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0100 [opened R363] 共同残差功率通道是否扩大物理头空间
- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0099 closed-negative @ R362, by CLM-0960 — On the exposed development bank, does replacing the one-hop neighbour snapshot messages with frozen R341-model causal prediction trajectories (DMPC-style shared prediction) let a pre-registered tuning-free non-neural map family recover both registered endpoint gates, showing learnable structure that R359, R360, and R361 could not reach from endpoint-only or snapshot-message information?
- Q-0098 closed-negative @ R361, by CLM-0955 — On the exposed development bank, does extending the exact fifteen-field edge-actor information path with one-hop neighbour messages let a pre-registered tuning-free non-neural map family recover both registered endpoint gates, showing learnable structure that R359 and R360 could not reach from endpoint-only information?
- Q-0097 closed-negative @ R360, by CLM-0950 — On the exposed development bank, does a pre-registered flexible non-neural neighbour-residual map family recover both registered endpoint gates from the exact prospective information path, showing learnable structure the R359 fixed affine map could not use?

## Methodology

### 冻结对象(与 R358 逐项相同)

- 16 个 R352 开发场景、25 样本、2 起始零步、R341 冻结点模型(FV0/FV1
  digest 校验)、`0.05` 边流量限、物理投影(节点功率 0.36、斜坡 0.072、
  SOC [0.2,0.8]、能量/电压电流约束)、2% 端点改善目标与共同/差分端点
  定义——全部与 R358 相同。
- R358 的 10/16 物理可行场景是唯一对比基线(信息无约束、3 边零共同基)。

### 变化点:共同残差功率通道(唯一变化)

- 动作基从 3 边零共同(R358 的 `edge_actions` 3 列)扩展为 4 通道
  (共同 + 3 边):节点动作 = `[ones(4), active_power_incidence()] @
  [u_common, u_edge0, u_edge1, u_edge2]`。共同通道 = 全体节点等量净功率
  注入(打破零共同),3 边通道保持零和。
- 响应映射扩展:新建 4 通道因果响应映射(共同+3 边输入 → 4 坐标输出),
  从 R341 模型完整 4 列控制输入构造;不改动 R358 已 seal 的
  `build_control_response_map`。
- 每个开发场景求解同一物理联合端点 QP:最小化差分端点,约束共同端点
  2% 改善 + 物理限制;变量 = 4×25 通道 + 25 松弛。cvxopt QP,求解器
  设置与 R358 相同。
- 判定:可行场景数(accepted)与 R358 的 10/16 对比;并检查原 6 个
  relaxed-infeasible 场景中是否有新可行者(共同通道专门作用于共同端点,
  物理上最可能先解锁这 6 个)。

### 判定树(预注册)

- 完整性失败(源/父/库存/数值/求解器/制品任一不过)→ `ANALYSIS-INVALID`
- 4 通道基下可行场景数 > 10(或 6 个原不可行场景中出现新可行)→
  `COMMON-CHANNEL-HEADROOM-EXPANDED`:零共同残差契约是结构限制,机制
  缺口确认;只开放一个单独注册的机制变更后继问题;training 仍 false。
- 4 通道基下可行场景数 == 10 且 6 个原不可行场景仍全部不可行 →
  `COMMON-CHANNEL-HEADROOM-UNCHANGED`:零共同契约不是绑定限制,机制
  缺口假说被削弱;不授权继续修补。
- 不可行数减少但总数仍为 10 的不可能情形按完整性失败处理(计数矛盾)。

### 主要泄漏防护

- 只读 R358 已暴露的开发案例库;无 holdout 读取。
- QP 是信息无约束的物理可行性分析(与 R358 同构),不拟合任何映射、
  不读 oracle 标签、不涉及训练。
- 4 通道响应映射从同一冻结模型构造,不改任何已 seal 源文件。
- 判定先于任何机制变更讨论;失败即停,不授权换契约/换基/扩库。

## Formal launch contract

- formal_entry: `python scripts/run_r363_common_channel_qp.py analyse --expected-seal-sha256 <sha256>`.
- rehearsal_command: `python scripts/run_r363_common_channel_qp.py rehearsal`.
- rehearsal_scope: 同 R358 — 走与正式入口相同的前置路径,覆盖 plan/question
  身份、R352/R341/R358 父哈希、开发库身份、4 通道响应映射形状与因果性、
  节点动作基秩与列符号、共同通道物理语义(等量净功率)、物理投影、
  分类器合成正/负/无效用例、cvxopt 版本、依赖安装与输出不存在;不读
  holdout 标签、不建 attempt/result。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- worker_processes: 1
- native_threads_per_process: 1
- wsl_python_processes: 0(全程离线串行 create-only)
- capacity_evidence: `memory/rounds/R363/capacity_evidence.json`
- host_process_budget: 1
- other_reserved_processes: 0
  16 场景 4 通道 QP 为确定性数值运算,单进程单线程分钟级完成;正式运行前
  用开发数据干跑实测并写入 capacity_evidence。
- Formal completion: 一个不可变 `analysis.json` + manifest + sidecar,或
  一个不可变 `failure.json` + sidecar;禁止重试。

## Gate

Design passes only when: 4 通道响应映射形状 (4·25, 4·25) 且因果;节点动作
基列符号与 R344 相同;共同通道 = 等量净功率注入且 3 边通道零和;物理
投影与 R358 逐项相同;QP 变量/约束/求解器设置可审计;分类器
(EXPANDED / UNCHANGED / INVALID)可测;来源闭合与定向测试全过。任何
缺失返回 `BLOCK`。

## 资产保护契约

R341-R362 的 plan、question、claim、源码、rehearsal、seal、attempt、
结果、feed、verdict、门槛与本线证据全部字节不变。新增:Q-0100、R363
plan、一个 4 通道响应映射实现 seam(新文件,不改任何已 seal 文件)、一个
R363 probe、一个稳定 adapter、定向测试,以及后续单独授权的 R363 制品。
不改其他手稿线、不启动学习或物理仿真、不改工作标题、不公开推送。

## Cross-references

- Q-0100
- CLM-0940 / R358 PHYSICAL-HEADROOM-FOUND (10/16 baseline)
- CLM-0960 / R362 NO-NEIGHBOUR-LEARNABLE-STRUCTURE (shared prediction)
- CLM-0955 / R361 NO-NEIGHBOUR-LEARNABLE-STRUCTURE (snapshot message)
- CLM-0950 / R360 NO-NEIGHBOUR-LEARNABLE-STRUCTURE
- CLM-0925 / R352 matched neighbour-local deterministic controller
- R353 exact causal split and gate grammar
- R341 separate-input point models (4 control columns)
- R344 control-coordinate basis [ones(4), incidence]
