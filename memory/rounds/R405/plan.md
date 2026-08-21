---
round: R405
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-15'
closed: '2026-08-15'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R405 plan — 线性化 + 候选A静态同质化 已披露开发门

**Opened**: 2026-08-15
**Driver**: owner 批准外部数学方案方向(2026-08-16): 静态 M/D 同质化是唯一未测的
一阶交叉自由度; 先线性化归档, 再物理门验候选 A。
**Parent**: CLM-1140 (R399 有限族无余量), CLM-1155 (R402 canary-fail),
CLM-1175 (R404 终局), route_successor_design_homogenization.md#decision,
tmp census PROCEED (2026-08-16)。

## TL;DR

两目的合一轮: (1) 在 8 个 canary 剖面工作点数值线性化 ANDES, 导出真实 4x4
网络矩阵 L, 验证 [Pc,L] 交换子, 归档为分析工具; (2) 候选 A(静态同质化偏置,
slew 爬坡后保持)在全部 48 个已披露场景上跑冻结估计器与阈值, 对比 sealed
km2_kd2 参考值, 判定交叉通道是否被同质化压低。不训练、不开未见库、无题目正
宣称。

## Snapshot at plan-time (oracle as of 2026-08-15)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?
- Q-0110 closed-positive @ R396, by CLM-1125 — Does the projected-passive dual-droop VSM (PPVSM1) two-unit diagnostic cell pass clean native initialization, a 0.2-second zero-input stationarity gate, and a spectrum guard with no positive-real mode and no neutral degeneracy beyond the network common-angle reference, thereby opening only a separately registered signed P/Q authority gate?
- Q-0109 closed-positive @ R392, by CLM-1105 — Which installed REGF2 feedback path or parameter carries the two reproducible positive-real local modes of the exact R391 four-REGF2 equilibrium, under prospectively frozen one-variable-at-a-time parameter-perturbation EIG arms?

## Methodology

### 冻结对象与参考(不变)

- 对象: ANDES 2.0.0 modified Kundur 四 VSG 代理, 60 Hz 物理端点, 0.2 s x 30
  步, 8 个 canary 剖面(profile 定义 = R401 seal /contract/profiles:
  baseline_m0/d0, steady_loads, 6 scenarios/剖面, 4 dev + 4 eval)。
- 参考臂: local_neighbour_md_km2_kd2。sealed 值 = R402 确定性参考记录
  (24 eval 场景)。本轮在-round 重跑该律于全部 48 场景, 24 eval 场景结果必须
  与 sealed 值在浮点容差内一致(不匹配 = INVALID, 不判科学结论)。
- 阈值不变: r_cross <= 0.95 且 r_d <= 0.95; 公共 IAE/最坏峰值/最坏 RoCoF
  <= 1.03; 动作 RMS/总变差 <= 1.10; 饱和分数 0; 全部完成、零失败。
- 动作盒/解码/斜率不变: [−1,1]^2, 分段解码 Δ = u·600 (u>=0) / u·200 (u<0)
  (ΔM,ΔD ∈ [−200,+600], 与 seal decoder 一致), 钳位 M>=20, D>=10,
  slew 0.25/0.2s。差模变换 = R401 seal 矩阵。
- 估计器: 复用 R399/R402 的 sealed 估计器模块(有符号奇响应、交叉能量、
  扰动差模能量、公共 IAE/峰值/RoCoF、动作 RMS/TV/饱和/完成)。不改估计器。

### 目的 1: 剖面线性化(分析工具)

- 每剖面: 经 ANDES Set 应用该剖面 baseline_m0/d0 于四台 GENCLS VSG 代理,
  应用 steady_loads, 原生初始化后构造 DAE Jacobian (f_x, f_y, g_x, g_y),
  折叠 A = f_x − f_y g_y^{-1} g_x; 输出 = 4 行频率映射, 输入 = 4 列 PQ 负荷
  功率 (PQ_0, PQ_1, PQ_Bus14, PQ_Bus15)。
- 每点检查: 初始化残差 <= 1e-4, 折叠全有限; 有效描述符 = 零时间常数管线折叠
  (R380 机制, 排除 Tf=0 快状态), 其 positive-real 计数 = 0; 原始 Schur 折叠的
  正实部对如实报告为 g_y 病态下的折叠伪影。
- 约减 4x4 L: 排练确认 PFlow.B 不可用且 gy 功率平衡行无法可靠识别 → 本轮
  报告 not-extracted 及原因, 折叠模型能量分析承担分析工具角色; 同质化前后矩
  (Var(1/M), Var(D/M^2), |Pd M^{-1} Pc|_F) 复算并归档(离线 probe 已实现)。
- 实现: probes/homogenization_linearization.py (判定逻辑) 复用
  vsg_energy_port_source_model.py 的源模型构造基础设施(适配 M/D 对象);
  scripts/run_r405_homogenization_gate.py 为 execution adapter。
- 线性化失败不阻候选 A 物理评估(两目的独立); 失败点如实报告。

### 目的 2: 候选 A 物理门

- 每剖面目标: m* = clip(调和均值 1/m* = mean 1/M0i, common_M 区间),
  d* = clip(m*^2 mean D0i/M0i^2, common_D 区间); 归一化目标 u* 由分段解码
  逆函数给出 (Δ>=0 → Δ/600, Δ<0 → Δ/200); 候选 A 用离线爬坡调度
  (probe homogenized_action_schedule, 与 LocalMDActionProjector 行为等价:
  盒内、每步 ≤0.25、到目标后保持), 无动态反馈。
- 臂: (a) 零动作 sanity; (b) km2_kd2 in-round 匹配重跑; (c) 候选 A。
  全部 48 场景 (24 dev + 24 eval), 同信息权限、同执行路径。
- 判定树(预注册):
  - PASS-A: r_cross<=0.95 且 r_d<=0.95 且全守卫过 → 授权 A+B 轮。
  - PARTIAL-A: r_cross<=0.95, r_d>0.95, 无害全过 → 按批准计划进 A+B 轮;
    无题目宣称。
  - NO-CROSS-EFFECT: r_cross>0.95 → 网络不对称主导; 后续物理工作需 owner
    再决定。
  - GUARD-FAIL: 任一完成/饱和/无害/应力守卫失败 → 候选 A 停, 本轮不修不重试。

### 明确不做

- 不训练、不调参、不换学习器、不开新未见库、不改阈值、不动 sealed 判定逻辑。
- 老线一阶族 α 线搜 = 单独 owner 授权(parallelled 线), 不属于本轮。

## Gate

Pre-registered decision tree 见 Methodology 目的 2 (outcomes: PASS-A /
PARTIAL-A / NO-CROSS-EFFECT / GUARD-FAIL / INVALID)。任何 FAIL/INVALID 按
对应分支走; INVALID 不产生科学结论。claim 收尾前
reserve_claim.py --round R405。

## 资产保护契约

- 只读: R401/R402/R404 sealed 产物、km2_kd2 实现 (per_vsg_md.py 只经现有
  投影器调用, 不改代码)、R399/R402 估计器模块。
- 不改: andes_vsg_env_v4.py / base_env.py / train.py / 任何 paper-cited 资产。
- 新增: probes/homogenization_linearization.py + scripts/run_r405_*.py +
  tests/test_* (经本 round 授权); 结果根 results/research_loop/r405_* 全部
  .sha256, 登记 results/MANIFEST.md; 线性化矩阵归档为分析工具, 不进 feed 数字。

## Cross-references

- route_successor_design_homogenization.md#decision (owner 授权)
- tmp/yang_md_decoupling_marl/technical-route-census.json (PROCEED)
- tmp/yang_md_decoupling_marl/external_solution_assessment.md (离线验证)
- CLM-1140, CLM-1155, CLM-1160, CLM-1175 (父证据)

## Formal launch contract

- formal_entry: scripts/run_r405_homogenization_gate.py (execute 子命令,
  前置验证: source/parent hash、installed ANDES package/case、output absence、
  合同 closed 后放行 attempt; 创建 results/research_loop/r405_* 与
  formal_attempt/execution/analysis/manifest, 逐文件 .sha256)
- rehearsal_command: scripts/andes_scratch.py 启动同一 formal_entry 的
  --rehearse 路径(WSL), 走 same pre-attempt verification path, 不创建正式
  attempt; 覆盖 source/parent hash、installed package、installed case、
  output absence、合同字段完整性。
- rehearsal_scope: same-pre-attempt-path; 1 个代表性剖面线性化 + 1 条 30 步
  候选 A 轨迹(开发数据); 不创建任何正式产物。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case,
  output_absence, 初始化残差, 折叠矩阵有限; rehearsal 输出与源码 hash 进 seal。
- wsl_python_processes: 3 (1 launcher + 2 workers; 线性化与评估均串行执行,
  预算为容量上限而非强制并行; 容量证据显示串行耗时在预算内)
- native_threads_per_process: 1
- capacity_evidence: memory/rounds/R405/capacity_evidence.json
  (已执行 ladder rungs 1/2/4: rung 4 全绿, throughput 0.2254 jobs/s,
  内存 ~204 MB; R339+ 规则)。
- host_process_budget: 3
- other_reserved_processes: 0
- 预算一经 seal 不得按结果改动; 若 rehearsal 后在 attempt 创建前失败, 本轮
  aborted, 修复走后继 round, 不原地补丁重试。

## Execution amendments (registered before use, R402 precedent)

- A-1 (shape repair): 首次 execute 在 linearization 阶段失败——
  load_input_columns 把 ANDES 的 1 维残差向量直接传给
  fold_input_columns(要求 2 维)。修补: fold_input_columns 接受 1 维输入并
  reshape 为单列, 附回归测试 test_fold_input_columns_accepts_flat_residual_vectors。
  预修补 attempt 保留于 results/research_loop/r405_homogenization_gate_pre_repair/。
  修补不改 arms/seeds/bank/阈值/判定树。
- A-2 (column-shape repair): 第二次 execute 再次在 load_input_columns 失败——
  fold_input_columns 错误要求 f_u/g_u 行数相同; 真实描述符状态残差(102)与
  代数残差(284)行数不同, 只需列数相同。修补: 只校验列数一致, 附回归测试
  test_fold_input_columns_allows_mismatched_row_counts; 同时 rehears 增加
  load_input_columns 单列覆盖, 堵住同族执行期缺陷。预修补 attempt 保留于
  results/research_loop/r405_homogenization_gate_pre_repair_2/。
