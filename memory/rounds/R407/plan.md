---
round: R407
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-15'
closed: '2026-08-15'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R407 plan — candidate-B 0.4 Hz ring-edge bandpass gate on the energy ports

**Opened**: 2026-08-15
**Driver**: owner 批准的候选 B(route_decision_bandpass_b_2026-08-16.md):
二阶正实带通阻尼在老线 feasibility-native 能量端口上检验; 新线候选 A 已停
(CLM-1180), legacy M/D 路径保持零(R369/R375 停止规则不变)。
**Parent**: CLM-1185 (R406 一阶族关闭), CLM-1040 (R379), CLM-1035 (R378),
route_decision_bandpass_b_2026-08-16.md。

## TL;DR

冻结结构 F(s) = K*2*zeta*wm*s/(s^2 + 2*zeta*wm*s + wm^2), wm = 2*pi*0.4,
zeta = 0.35, 双线性离散 + 0.4 Hz 增益校正, 环边差分输入(对公共频率严格
透明); 只搜 K ∈ {0.10, 0.25, 0.50, 1.00, 2.00}。同一 60 轨迹开发数据组、
同一估计器与阈值(差模 <=0.95, 探测交叉 <=1.10, 全守卫)。任一 K 双过 →
BAND-PASS(后继单独 held-out 门); 全不过 → BAND-FAIL(带通阶段停)。

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

### 冻结对象与结构

- 对象: R376-R379 同一四 VSG 能量端口对象(buses 12/16/14/15),
  feasibility-native 动作映射, 60 轨迹开发数据组, seed 42, 0.2s x 50 步。
- 带通: F(s) = K*2*zeta*wm*s/(s^2 + 2*zeta*wm*s + wm^2), wm = 2*pi*0.4 rad/s,
  zeta = 0.35 冻结; 双线性离散 + 0.4 Hz 增益校正(ring_bandpass_damping.py,
  已实现 + 6 测试绿); 环边差分 v = -B_r F(z) B_r^T omega, 1^T v = 0。
- 归一化动作 = clip(v, +/-0.70)(= R379 controller_action_clip), 经
  feasibility-native map 进入能量端口。
- K 网格冻结: {0.10, 0.25, 0.50, 1.00, 2.00}。只搜 K, 不改 zeta/结构/阶数。
- 臂: zero_feedback / local_feasibility_native / bandpass_k<k>(每 K 一臂)。

### 判定树(预注册)

- 任一 K 双端点过(差模 <=0.95 且交叉 <=1.10)+ 全守卫过 -> BAND-PASS
  (记录该 K; 后继单独 held-out 门)。
- 全 K 至少一端点或一守卫不过 -> BAND-FAIL(带通阶段停, 不重试)。
- 执行不完整/无效 -> INVALID。

### 实现与复用

- scripts/run_r407_bandpass_gate.py: 复用 R379 的 job/汇总/分类路径,
  臂构造用 BandpassArmController 适配器; 纯判定函数 bandpass_decision
  (已实现 + 5 测试绿)。不修改任何 sealed 资产。
- 结果根 results/research_loop/r407_bandpass_gate/, create-only + .sha256。

## Gate

Pre-registered decision tree: BAND-PASS / BAND-FAIL / INVALID (outcomes 见
Methodology)。claim 收尾前 reserve_claim.py --round R407。

## 资产保护契约

- 只读: R376-R379 sealed 产物、gate_b3_deterministic.py、
  feasibility_native_deterministic.py、energy-port 环境。不改任何
  paper-cited 资产。
- 新增: scripts/run_r407_bandpass_gate.py、
  src/andes_rl_kundur/control/ring_bandpass_damping.py +
  tests/test_r407_bandpass_gate.py + tests/test_ring_bandpass_damping.py
  (经本 round 授权)。
- 不碰 R378/R379 held-out 库; 不训练; 不重开 M/D 路径或任何停止族。

## Cross-references

- paper/paralleled_vsg_marl/working/route_decision_bandpass_b_2026-08-16.md
- tmp/paralleled_vsg_marl/b_round_plan_draft.md (冻结设计来源)
- CLM-1185, CLM-1040, CLM-1035 (父证据)

## Formal launch contract

- formal_entry: scripts/run_r407_bandpass_gate.py (execute 子命令; 前置验证:
  source/parent hash、installed ANDES package/case、output absence; create-only
  结果 + .sha256 侧车)
- rehearsal_command: scripts/andes_scratch.py 启动同一 formal_entry 的
  --rehearse 路径(WSL), 走 same pre-attempt verification path, 不创建正式
  attempt。
- rehearsal_scope: same-pre-attempt-path; K=0.10 单臂 + 1 条 50 步开发轨迹;
  不创建任何正式产物。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case,
  output_absence, 初始化残差, 折叠矩阵有限。
- wsl_python_processes: 9 (1 launcher + 8 workers; A-2 并行执行)
- native_threads_per_process: 1
- capacity_evidence: memory/rounds/R407/capacity_evidence.json
  (本 round 自测 ladder rungs 1/2/4/8: rung 8 全绿 0.6453 jobs/s; 预算 9 锚定于 rung 8)
- host_process_budget: 9
- other_reserved_processes: 0
- 预算一经 seal 不得按结果改动; attempt 创建前失败 → aborted, 修复走后继 round。

## Execution amendments (registered before use, R402 precedent)

- A-1 (bandpass arm registration): 首次 execute 在首个 K 点失败——R379 的
  _run_job 只认识 R379 臂, bandpass_k* 臂不被 controller_spec 识别。修补:
  本地分叉 _run_job 与 _make_controller(带 bandpass 分支, zero/local 走
  R379 spec), 附回归测试 test_controller_factory_recognizes_bandpass_arms。
  预修补 attempt 保留于 results/research_loop/r407_bandpass_gate_pre_repair/。
  修补不改 K 网格/阈值/判定树/数据组。

- A-2 (parallel execution, owner directive 充分利用 CPU): 5 个 K 点独立, execute
  改为 8 工作进程并行(每进程单原生线程, 模块导入时已 pin); 容量 ladder 实测
  rung 8 全绿(0.6453 jobs/s, 单作业 ~10-12 s), 预算从 3 修订为 9
  (1 launcher + 8 workers), 容量证据已更新为 rung 8 锚定。预并行 attempt 保留于
  results/research_loop/r407_bandpass_gate_pre_repair_2/。修补不改 K 网格/
  阈值/判定树/数据组。

- A-3 (row-field completeness repair): 并行 attempt 的守卫全部报
  lower_power_system_pu 缺失——本地分叉的作业循环漏写 R379 行字段(上下界/
  锚点/可行功率/余量/越界), 估计器守卫因字段缺失而误报, BAND-FAIL 判定无效。
  修补: _enrich_row 纯函数补齐全部 10 个必需行字段, 附回归测试
  test_enrich_row_produces_all_estimator_required_keys。预修补 attempt 保留于
  results/research_loop/r407_bandpass_gate_pre_repair_3/。修补不改 K 网格/
  阈值/判定树/数据组。
