---
round: R360
state: completed
manuscript_line: decoupling-marl-model-first
opened: '2026-08-07'
closed: '2026-08-07'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R360 plan - flexible non-neural neighbour-residual learnability gate

**Opened**: 2026-08-07
**Driver**: 检验 R359 负结果到底是"相邻信息路径无可学结构"还是"仿射函数类
太窄"：用预注册的三个无调参非神经映射族成员在同一信息契约上重测两个端点门。
**Parent**: Q-0097; CLM-0945 / R359; CLM-0940 / R358; CLM-0925 / R352

## TL;DR

Workload: `evidence`. 完全复用 R359 的开发/持有划分、15 字段精确信息契约、
三边独立动作路径、物理投影、起始掩码与 R358 开发目标；只把"固定仿射每边
映射"换成预注册的三成员灵活映射族（RBF 核岭、k-NN、二次多项式基），全部
无调参、无训练、无扫描。开发门失败即按预注册停止学习路线；任一成员通过
只开放一个单独注册的后继问题。无 holdout 读取、无训练、无仿真、无 EVAL。

## Snapshot at plan-time (oracle as of 2026-08-07)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0097 [opened R360] 灵活非神经邻居残差映射族能否在精确信息路径上越过两个注册端点门

## Recently Closed (last 3)

- Q-0096 closed-negative @ R359, by CLM-0945 — fixed affine neighbour residual fails the development gate
- Q-0095 closed-positive @ R358, by CLM-0940 — physical action-space headroom in ten exposed cases
- Q-0094 closed-negative @ R356, by CLM-0930 — matched neighbour-local baseline leaves no joint headroom

## Methodology

### 冻结对象（与 R359 逐项相同）

- 16 个 R352 开发场景（zero/selected-local 配对）、16 个 staggered-rise
  持有配对；开发/持有身份、响应映射、物理投影、起始掩码
  `STARTUP_ZERO_STEPS=2`、`SAMPLES_PER_TRACE=25`、`EDGE_FLOW_LIMIT=0.05`
  全部沿用。
- 信息契约：每个边 actor 一个 15 字段 `LocalEdgeObservation`（两端频率偏差、
  RoCoF、上一边执行流、两端先前命令/SOC/电压/上下残差功率界），禁止项同
  R359（achieved power、操作点、扰动通道/符号、场景身份、其他边值、联合
  坐标、未来样本、已实现端点、oracle 值）。
- R358 开发目标：10 个接受物理见证做正目标，6 个继承松弛不可行做全零负
  控制；前两个残差动作固定为零。
- 端点与门槛：共同坐标 IAE 与差分坐标能量，名义与失配有界两张响应图，
  配对均值改善 ≥2%、单侧 95% 上界、子组方向、单场景最坏比 ≤1.05；
  端点后果为主判定，动作向量误差仅诊断。

### 变化点：三成员灵活映射族（唯一变化）

1. **RBF 核岭**：核宽 = 训练配对距离中位数启发式（固定），正则化固定
   `1e-3`，闭式解，逐边拟合。
2. **k-NN**：`k=5`，标准化欧氏距离，无参数。
3. **二次多项式基**：15 字段 → 全一阶+二次交互基，标准化，无正则化，
   Moore-Penrose 最小二乘。

三个成员全部预注册、冻结；无核宽/正则化/k/次数扫描，无种子，无奖励，
无神经/强化学习。每个成员独立走 leave-one-scenario-out 开发投影。

### 判定树（预注册）

## Outcomes

- 完整性失败（源/父/库存/信息/因果/泄漏/数值/过程/制品任一不过）→
  `ANALYSIS-INVALID`：保留 attempt，禁止就地重试。
- 完整性全过、至少一个成员同时通过名义与失配有界两个端点门 →
  `NEIGHBOUR-LEARNABLE-STRUCTURE-FOUND`：只开放一个单独注册的后继问题；
  training/simulation/holdout/EVAL 保持 false。
- 完整性全过、所有成员均至少一个端点门失败 →
  `NO-NEIGHBOUR-LEARNABLE-STRUCTURE`：按 R359 PI 话预注册停止，学习路线
  终止，Q-0097 关闭为负，不授权 holdout 修复、训练或仿真。

### 主要泄漏防护

- 每个场景的目标行在其被预测时全部排除（leave-one-scenario-out）。
- 无 holdout 残差标签、反事实端点或 oracle 动作进入拟合/选择/门槛/修复。
- 开发门失败即停，不读任何 holdout。
- 三成员只共享同一开发集，互不选择（无"选最好的成员"之外的 meta 选择；
  判定为"任一通过"是预注册 OR 语义，不是事后挑成员）。

## Formal launch contract

- formal_entry: `python scripts/run_r360_flexible_neighbour_residual.py analyse --expected-seal-sha256 <sha256>`.
- rehearsal_command: `python scripts/run_r360_flexible_neighbour_residual.py rehearsal`.
- rehearsal_scope: 同 R359 — 走与正式入口相同的前置路径，覆盖 plan/question
  身份、R352/R358 父哈希、开发/持有身份、15 字段信息所有权、起始掩码、
  三成员冻结（核宽/k/次数常量）、泄漏屏障、分类器合成正/负/无效用例、
  依赖安装与输出不存在；不读 holdout 标签、不建 attempt/result。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- worker_processes: 1
- native_threads_per_process: 1
- wsl_python_processes: 0（全程离线串行 create-only）
- capacity_evidence: `memory/rounds/R360/capacity_evidence.json`
- host_process_budget: 1
- other_reserved_processes: 0
  三成员 × 16 场景 leave-one-out 拟合为确定性数值运算，单进程单线程即可
  在分钟级完成；正式运行前用开发数据干跑实测并写入 capacity_evidence。
- Formal completion: 一个不可变 `analysis.json` + manifest + sidecar，或
  一个不可变 `failure.json` + sidecar；禁止重试。

## Gate

Design passes only when: 15 字段信息契约逐字段与 R359 相同；三成员实现为
冻结常量且无任何扫描路径；leave-one-scenario-out 泄漏屏障可测；开发/持有
分离与 R359 完全一致；两个端点门复用 R353 语法；三分类器（FOUND / NO /
INVALID）纯 OR 语义；来源闭合与定向测试全过。任何缺失返回 `BLOCK`。

## 资产保护契约

R341/R350/R351/R352/R353/R354/R355/R356/R357/R358/R359 的 plan、question、
claim、源码、rehearsal、seal、attempt、结果、feed、verdict、门槛与本线
证据全部字节不变。新增：Q-0097、R360 plan、一个灵活映射实现 seam、一个
R360 probe、一个稳定 adapter、定向测试，以及后续单独授权的 R360 制品。
不改其他手稿线、不启动学习或物理仿真、不改工作标题、不公开推送。

## Cross-references

- Q-0097
- CLM-0945 / R359 NO-NEIGHBOUR-CAUSAL-HEADROOM
- CLM-0940 / R358 PHYSICAL-HEADROOM-FOUND
- CLM-0925 / R352 matched neighbour-local deterministic controller
- R353 exact causal split and gate grammar
