---
round: R361
state: completed
manuscript_line: decoupling-marl-model-first
opened: '2026-08-07'
closed: '2026-08-07'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R361 plan — one-hop neighbour-message learnability gate

**Opened**: 2026-08-07
**Driver**: deep-research 判定瓶颈在信息路径而非映射容量;唯一机制变化 =
每个边 actor 的信息路径从 15 字段扩展到 29 字段(加两个一跳邻居节点消息),
其余与 R360 逐字节相同,重测两个端点门。
**Parent**: Q-0098; CLM-0950 / R360; CLM-0945 / R359; CLM-0940 / R358;
CLM-0925 / R352

## TL;DR

Workload: `evidence`(新分析执行,信息契约改变,可能影响学习路线结论)。
完全复用 R360 的开发/持有划分、物理投影、起始掩码、R358 目标、端点门与
门槛;唯一变化 = 冻结通信环 `{(0,1),(1,2),(2,3),(0,3)}` 上每个 action-edge
actor 增加其两个一跳邻居节点的七字段端点观察(按 source-side 先、
target-side 后冻结顺序),观察维度 15→29。映射族 = R359 固定仿射 + R360
三个灵活族,共 4 族,全部冻结无调参,leave-one-scenario-out 开发投影,
OR 语义:任一通过 → 正类;全失败 → 信息路径假说被进一步削弱,按注册
停止;无 holdout 读取、无训练、无仿真、无 EVAL。

## Snapshot at plan-time (oracle as of 2026-08-07)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0098 [opened R361] 一跳邻居消息扩展后冻结映射族能否通过两个端点门
- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0097 closed-negative @ R360, by CLM-0950 — On the exposed development bank, does a pre-registered flexible non-neural neighbour-residual map family recover both registered endpoint gates from the exact prospective information path, showing learnable structure the R359 fixed affine map could not use?
- Q-0096 closed-negative @ R359, by CLM-0945 — Can one fixed causal neighbour-local residual controller recover the R358 physical headroom using exactly the future agents' information and three-edge action path?
- Q-0095 closed-positive @ R358, by CLM-0940 — Do any exposed R356 candidates retain the unchanged joint target under the exact three-edge physical limits?

## Methodology

### 冻结对象(与 R360 逐项相同)

- 16 个 R352 开发场景(zero/selected-local 配对)、16 个 staggered-rise
  持有配对;开发/持有身份、响应映射、物理投影、起始掩码
  `STARTUP_ZERO_STEPS=2`、`SAMPLES_PER_TRACE=25`、`EDGE_FLOW_LIMIT=0.05`
  全部沿用。
- R358 开发目标:10 个接受物理见证做正目标,6 个继承松弛不可行做全零负
  控制;前两个残差动作固定为零。
- 端点与门槛:共同坐标 IAE 与差分坐标能量,名义与失配有界两张响应图,
  配对均值改善 ≥2%、单侧 95% 上界、子组方向、单场景最坏比 ≤1.05;
  端点后果为主判定,动作向量误差仅诊断。
- 禁止项:achieved power、操作点、扰动通道/符号、场景身份、**其他边
  动作值**、未来样本、已实现端点、oracle 值。

### 变化点:一跳邻居消息(唯一变化)

通信环 `{(0,1),(1,2),(2,3),(0,3)}` 冻结。每个 action-edge actor `(i,j)`
在因果瞬间额外收到其两个一跳邻居节点(环上与 `i` 相邻的非 `j` 节点、与
`j` 相邻的非 `i` 节点)的四字段消息:frequency deviation、RoCoF、SOC、
voltage;顺序 = source-side 邻居先、target-side 邻居后:

| 边 | source-side 邻居 | target-side 邻居 |
|---|---|---|
| (0,1) | 3 | 2 |
| (1,2) | 0 | 3 |
| (2,3) | 1 | 0 |

消息共 8 字段,观察维度 15 → 23(23 字段二次基 299 列 < 345 行训练折,
四族全部可拟合)。消息取与自身观察完全相同的因果 pre-action 样本;消息
内容永远不是邻居动作、边流量、命令、场景身份、扰动身份、未来值、已实现
端点或 oracle 值。

### 映射族与判定树(预注册)

四个冻结族(全部无调参、无扫描、无种子、无奖励、无神经/强化学习):

1. 固定仿射(R359 同款,standardized affine)
2. RBF 核岭(核宽 = 训练配对距离中位数,正则 `1e-3`)
3. k-NN(`k=5`,标准化欧氏距离)
4. 二次多项式基(23 字段 → 299 列一阶+交互,标准化,无正则)

leave-one-scenario-out 开发投影,逐边拟合。

- 完整性失败(源/父/库存/信息/因果/泄漏/数值/过程/制品任一不过)→
  `ANALYSIS-INVALID`:保留 attempt,禁止就地重试。
- 完整性全过、至少一族同时通过名义与失配有界两个端点门 →
  `NEIGHBOUR-LEARNABLE-STRUCTURE-FOUND`:只开放一个单独注册的后继问题;
  training/simulation/holdout/EVAL 保持 false。
- 完整性全过、所有族均至少一个端点门失败 →
  `NO-NEIGHBOUR-LEARNABLE-STRUCTURE`:信息路径假说被进一步削弱,按
  deep-research 注册停止;不允许同契约下的就地修补、换种子、换阈值、
  扩库或其他信息变体。

### 主要泄漏防护

- 每个场景的目标行在其被预测时全部排除(leave-one-scenario-out)。
- 邻居消息只取同一因果 pre-action 样本,不跨场景、不跨扰动、不取未来。
- 无 holdout 残差标签、反事实端点或 oracle 动作进入拟合/选择/门槛/修复。
- 开发门失败即停,不读任何 holdout。
- 四族只共享同一开发集;判定为"任一通过"是预注册 OR 语义,不是事后挑族。

## Formal launch contract

- formal_entry: `python scripts/run_r361_neighbour_message_residual.py analyse --expected-seal-sha256 <sha256>`.
- rehearsal_command: `python scripts/run_r361_neighbour_message_residual.py rehearsal`.
- rehearsal_scope: 同 R360 — 走与正式入口相同的前置路径,覆盖 plan/question
  身份、R352/R358/R359/R360 父哈希、开发/持有身份、23 字段信息所有权
  (15 自身 + 8 一跳邻居消息)、邻居表冻结、起始掩码、四族冻结、
  泄漏屏障、分类器合成正/负/无效用例、依赖安装与输出不存在;不读
  holdout 标签、不建 attempt/result。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- worker_processes: 1
- native_threads_per_process: 1
- wsl_python_processes: 0(全程离线串行 create-only)
- capacity_evidence: `memory/rounds/R361/capacity_evidence.json`
- host_process_budget: 1
- other_reserved_processes: 0
  四族 × 16 场景 leave-one-out 拟合为确定性数值运算,单进程单线程分钟级
  完成;正式运行前用开发数据干跑实测并写入 capacity_evidence。
- Formal completion: 一个不可变 `analysis.json` + manifest + sidecar,或
  一个不可变 `failure.json` + sidecar;禁止重试。

## Gate

Design passes only when: 23 字段信息契约逐字段可解释(15 自身字段与 R360
相同 + 8 一跳邻居消息按冻结邻居表);邻居表与通信环一致且顺序冻结;
四族实现为冻结常量且无任何扫描路径;leave-one-scenario-out 泄漏屏障可测;
开发/持有分离与 R360 完全一致;两个端点门复用 R353 语法;三分类器
(FOUND / NO / INVALID)纯 OR 语义;来源闭合与定向测试全过。任何缺失
返回 `BLOCK`。

## 资产保护契约

R341/R350/R351/R352/R353/R354/R355/R356/R357/R358/R359/R360 的 plan、
question、claim、源码、rehearsal、seal、attempt、结果、feed、verdict、
门槛与本线证据全部字节不变。新增:Q-0098、R361 plan、一个一跳邻居消息
实现 seam、一个 R361 probe、一个稳定 adapter、定向测试,以及后续单独
授权的 R361 制品。不改其他手稿线、不启动学习或物理仿真、不改工作标题、
不公开推送。

## Cross-references

- Q-0098
- CLM-0950 / R360 NO-NEIGHBOUR-LEARNABLE-STRUCTURE
- CLM-0945 / R359 NO-NEIGHBOUR-CAUSAL-HEADROOM
- CLM-0940 / R358 PHYSICAL-HEADROOM-FOUND
- CLM-0925 / R352 matched neighbour-local deterministic controller
- R353 exact causal split and gate grammar
