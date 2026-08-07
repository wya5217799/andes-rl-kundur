---
round: R362
state: completed
manuscript_line: decoupling-marl-model-first
opened: '2026-08-07'
closed: '2026-08-07'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R362 plan — shared-prediction (DMPC-style) learnability gate

**Opened**: 2026-08-07
**Driver**: deep-research 方向 1 的第二个变体:把 R361 的一跳邻居快照消息
升级为冻结模型的因果预测轨迹(DMPC 式共享预测);其余与 R361 逐字节相同。
**Parent**: Q-0099; CLM-0955 / R361; CLM-0950 / R360; CLM-0945 / R359;
CLM-0940 / R358; CLM-0925 / R352

## TL;DR

Workload: `evidence`(新分析执行,信息契约从快照消息升级为模型预测消息)。
完全复用 R361 的开发/持有划分、物理投影、起始掩码、R358 目标、端点门与
门槛、23 字段维度预算;唯一变化 = 一跳邻居消息内容从"当前四字段快照"
升级为"冻结 R341 模型对邻居节点未来 4 步频率偏差的因果开环预测轨迹"
(每邻居 4 字段,观察仍为 23 字段)。预测生成器全部冻结:按操作点加载
R341 order-12 模型、R344 冻结输出尺度、扰动尺度 0.05、测量分数 0.01,
因果估计推进 + 零未来残差开环过渡,扰动估计保持;无调参、无扫描、无
训练。映射族 = 4 个(R359 仿射 + R360 三族),OR 语义;全失败 → 信息路径
假说进一步削弱,按注册停止;无 holdout 读取、无训练、无仿真、无 EVAL。

## Snapshot at plan-time (oracle as of 2026-08-07)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0099 [opened R362] 共享预测消息升级后冻结映射族能否通过两个端点门
- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0098 closed-negative @ R361, by CLM-0955 — On the exposed development bank, does extending the exact fifteen-field edge-actor information path with one-hop neighbour messages let a pre-registered tuning-free non-neural map family recover both registered endpoint gates, showing learnable structure that R359 and R360 could not reach from endpoint-only information?
- Q-0097 closed-negative @ R360, by CLM-0950 — On the exposed development bank, does a pre-registered flexible non-neural neighbour-residual map family recover both registered endpoint gates from the exact prospective information path, showing learnable structure the R359 fixed affine map could not use?
- Q-0096 closed-negative @ R359, by CLM-0945 — Can one fixed causal neighbour-local residual controller recover the R358 physical headroom using exactly the future agents' information and three-edge action path?

## Methodology

### 冻结对象(与 R361 逐项相同)

- 16 个 R352 开发场景(zero/selected-local 配对)、16 个 staggered-rise
  持有配对;开发/持有身份、响应映射、物理投影、起始掩码
  `STARTUP_ZERO_STEPS=2`、`SAMPLES_PER_TRACE=25`、`EDGE_FLOW_LIMIT=0.05`
  全部沿用。
- R358 开发目标:10 个接受物理见证做正目标,6 个继承松弛不可行做全零负
  控制;前两个残差动作固定为零。
- 端点与门槛:共同坐标 IAE 与差分坐标能量,名义与失配有界两张响应图,
  配对均值改善 ≥2%、单侧 95% 上界、子组方向、单场景最坏比 ≤1.05;
  端点后果为主判定,动作向量误差仅诊断。
- 禁止项:achieved power、操作点、扰动通道/符号、场景身份、其他边动作
  值、邻居命令、邻居边流量、未来真实值、已实现端点、oracle 值。

### 变化点:共享预测消息(唯一变化)

与 R361 相同:通信环 `{(0,1),(1,2),(2,3),(0,3)}` 冻结,每个 action-edge
actor `(i,j)` 在因果瞬间收到其两个一跳邻居节点(环上与 `i` 相邻的非 `j`
节点、与 `j` 相邻的非 `i` 节点)的四字段消息,顺序 = source-side 邻居先、
target-side 邻居后,邻居表与 R361 相同:

| 边 | source-side 邻居 | target-side 邻居 |
|---|---|---|
| (0,1) | 3 | 2 |
| (1,2) | 0 | 3 |
| (2,3) | 1 | 0 |

消息内容变化:R361 是当前四字段快照(frequency deviation、RoCoF、SOC、
voltage);R362 是**冻结 R341 模型对邻居节点未来四个 0.2-s 样本频率偏差
的因果开环预测轨迹**(四字段 = 未来 4 步预测频率偏差,单位 Hz)。观察
维度仍为 15 + 8 = 23。

预测生成器(全部冻结、无调参、无扫描):

1. 按场景操作点(`FV0`/`FV1`)加载 R341 order-12 separate-input 点模型,
   digest 校验同 R353。
2. 冻结估计器:`synthesize_separate_input_estimator(model, output_scales=
   R344 冻结值[point], disturbance_scale=0.05, measurement_fraction=0.01)`;
   augmented 扰动估计,因果可观测。
3. 因果推进:从场景 trace 的因果 pre-action 观测序列(频率坐标 + 已执行
   命令)沿采样推进估计器,得到 t_k 时刻的状态/扰动估计;只读 t_k 及其
   之前的样本。
4. 开环预测:从估计状态做 4 步过渡 `A z + B_u u`,未来残差控制为零、
   未来扰动 = 估计扰动保持;输出 = 模型输出矩阵对邻居节点的 4 步频率
   偏差预测(坐标 → 频率的冻结逆变换,用 `weighted_common_differential_
   transform.inverse` 与 60 Hz 基)。
5. 消息 = 该邻居节点未来 4 步预测频率偏差;消息本身不是 oracle、不是
   已实现端点、不是未来真实值,而是冻结模型在因果信息上的开环外推。

预测质量不是调参对象:模型/估计器/尺度全部冻结,预测误差是信息路径的
一部分被测,不是可修参数。

### 映射族与判定树(预注册)

四个冻结族(全部无调参、无扫描、无种子、无奖励、无神经/强化学习):

1. 固定仿射(R359 同款,standardized affine)
2. RBF 核岭(核宽 = 训练配对距离中位数,正则 `1e-3`)
3. k-NN(`k=5`,标准化欧氏距离)
4. 二次多项式基(23 字段 → 299 列一阶+交互,标准化,无正则)

leave-one-scenario-out 开发投影,逐边拟合。

- 完整性失败(源/父/库存/信息/预测因果/泄漏/数值/过程/制品任一不过)→
  `ANALYSIS-INVALID`:保留 attempt,禁止就地重试。
- 完整性全过、至少一族同时通过名义与失配有界两个端点门 →
  `NEIGHBOUR-LEARNABLE-STRUCTURE-FOUND`:只开放一个单独注册的后继问题;
  training/simulation/holdout/EVAL 保持 false。
- 完整性全过、所有族均至少一个端点门失败 →
  `NO-NEIGHBOUR-LEARNABLE-STRUCTURE`:信息路径假说被进一步削弱,按
  deep-research 注册停止;不允许同契约下的就地修补、换种子、换阈值、
  扩库、换预测视界或其他信息变体。

### 主要泄漏防护

- 每个场景的目标行在其被预测时全部排除(leave-one-scenario-out)。
- 预测只读 t_k 及其之前的样本;未来真实值、已实现端点、oracle 值、
  其他场景值一律不进入预测器或映射族。
- 无 holdout 残差标签、反事实端点或 oracle 动作进入拟合/选择/门槛/修复。
- 开发门失败即停,不读任何 holdout。
- 四族只共享同一开发集;判定为"任一通过"是预注册 OR 语义,不是事后挑族。

## Formal launch contract

- formal_entry: `python scripts/run_r362_shared_prediction_residual.py analyse --expected-seal-sha256 <sha256>`.
- rehearsal_command: `python scripts/run_r362_shared_prediction_residual.py rehearsal`.
- rehearsal_scope: 同 R361 — 走与正式入口相同的前置路径,覆盖 plan/question
  身份、R352/R358/R359/R360/R361 父哈希、开发/持有身份、23 字段信息
  所有权(15 自身 + 8 共享预测消息)、邻居表冻结、预测生成器冻结
  (R341 模型 digest、R344 尺度、估计器参数、4 步视界)、起始掩码、四族
  冻结、泄漏屏障、分类器合成正/负/无效用例、依赖安装与输出不存在;
  不读 holdout 标签、不建 attempt/result。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- worker_processes: 1
- native_threads_per_process: 1
- wsl_python_processes: 0(全程离线串行 create-only)
- capacity_evidence: `memory/rounds/R362/capacity_evidence.json`
- host_process_budget: 1
- other_reserved_processes: 0
  预测生成 + 四族 × 16 场景 leave-one-out 拟合为确定性数值运算,单进程
  单线程分钟级完成;正式运行前用开发数据干跑实测并写入 capacity_evidence。
- Formal completion: 一个不可变 `analysis.json` + manifest + sidecar,或
  一个不可变 `failure.json` + sidecar;禁止重试。

## Gate

Design passes only when: 23 字段信息契约逐字段可解释(15 自身字段与 R360
相同 + 8 共享预测消息按冻结邻居表与冻结预测生成器);预测只读因果样本;
R341 模型与 R344 尺度按 digest 绑定;四族实现为冻结常量且无任何扫描
路径;leave-one-scenario-out 泄漏屏障可测;开发/持有分离与 R361 完全
一致;两个端点门复用 R353 语法;三分类器(FOUND / NO / INVALID)纯 OR
语义;来源闭合与定向测试全过。任何缺失返回 `BLOCK`。

## 资产保护契约

R341-R361 的 plan、question、claim、源码、rehearsal、seal、attempt、
结果、feed、verdict、门槛与本线证据全部字节不变。新增:Q-0099、R362
plan、一个共享预测实现 seam(新文件,不改任何已 seal 文件)、一个 R362
probe、一个稳定 adapter、定向测试,以及后续单独授权的 R362 制品。
不改其他手稿线、不启动学习或物理仿真、不改工作标题、不公开推送。

## Cross-references

- Q-0099
- CLM-0955 / R361 NO-NEIGHBOUR-LEARNABLE-STRUCTURE (snapshot message)
- CLM-0950 / R360 NO-NEIGHBOUR-LEARNABLE-STRUCTURE
- CLM-0945 / R359 NO-NEIGHBOUR-CAUSAL-HEADROOM
- CLM-0940 / R358 PHYSICAL-HEADROOM-FOUND
- CLM-0925 / R352 matched neighbour-local deterministic controller
- R353 exact causal split and gate grammar
- R344 frozen output scales and deterministic bridge seam
- R341 separate-input point models
