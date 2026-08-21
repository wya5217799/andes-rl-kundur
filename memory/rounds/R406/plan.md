---
round: R406
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-15'
closed: '2026-08-15'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R406 plan — external-solution alpha line-sweep on the frozen first-order family

**Opened**: 2026-08-15
**Driver**: owner 单独授权的 α 线搜(route_decision_alpha_sweep_2026-08-16.md):
外部方案 P2 判定两个端点(R378 α=0.60: r_d 0.962/交叉 0.79; R379 α=0.90:
r_d 0.914/交叉 1.15-1.29)不足以证明一阶族必然无解, 两频率选择性上界 4.76,
线性插值预测 α≈0.675 附近可能可行。
**Parent**: CLM-1040 (R379 stop), CLM-1035 (R378 stop), CLM-1030 (R377),
CLM-1025 (R376), external_solution_assessment.md P2。

## TL;DR

冻结 α 网格 {0.675, 0.625, 0.65, 0.70, 0.725, 0.75, 0.80, 0.85}(首测 0.675),
在 R376-R379 同一对象、同一 60 轨迹开发数据组、同一估计器与阈值
(差模能量 <=0.95, 探测交叉 <=1.10, 全无害守卫)上逐一评估一阶高通互阻尼族。
任一点双过 → SWEEP-FOUND-CANDIDATE(后继单独 held-out 门); 全不过 →
SWEEP-NO-CANDIDATE(网格内关闭一阶族)。不改增益/阶数/网格, 不碰 held-out,
不训练。

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

### 冻结对象与估计器(与 R376-R379 完全一致)

- 对象: R379 同一四 VSG 能量端口对象(buses 12/16/14/15), 同一
  feasibility-native 动作映射、同一开发数据组 60 轨迹、seed 42、0.2s x 50 步。
- 族: R378/R379 的 distributed low-corner high-pass mutual damping 律,
  结构/增益(ks1 kc0p5)/归一化全部复用 R379 实现; 只变 highpass_alpha。
- 估计器与阈值: 复用 gate_b3_deterministic 分类器(差模能量比 <=0.95,
  探测交叉比 <=1.10, 无害守卫 = R379 冻结值)。
- 臂: zero_feedback / local_feasibility_native / 每 α 一个 damping 臂
  (共 8 个网格点)。

### 冻结 α 网格与判定树(预注册)

- 网格(顺序执行): 0.675, 0.625, 0.65, 0.70, 0.725, 0.75, 0.80, 0.85。
- 判定: 任一点双端点过 + 全守卫过 → SWEEP-FOUND-CANDIDATE(记录该点,
  后继单独 held-out 门, 本 round 不碰 held-out); 全部点至少一端点或一守卫
  不过 → SWEEP-NO-CANDIDATE; 执行不完整/无效 → INVALID。
- 网格外增益/阶数/角频率修改 = 违规, 本 round 不做; 不训练; 无题目正宣称。

### 实现与复用

- 新 runner scripts/run_r406_alpha_sweep.py: 循环网格构建 per-α 合同并调用
  R379 同款执行/分类器路径; 复用 feasibility_native_deterministic.py、
  gate_b3_deterministic.py、R379 环境构造(不改这些 sealed 资产)。
- 结果根 results/research_loop/r406_alpha_sweep/, create-only + .sha256。

## Gate

Pre-registered decision tree: SWEEP-FOUND-CANDIDATE / SWEEP-NO-CANDIDATE /
INVALID (outcomes 见 Methodology)。claim 收尾前 reserve_claim.py --round R406。

## 资产保护契约

- 只读: R376-R379 sealed 产物、feasibility_native_deterministic.py、
  gate_b3_deterministic.py、energy-port 环境。不改任何 paper-cited 资产。
- 新增: scripts/run_r406_alpha_sweep.py + tests/test_r406_alpha_sweep.py
  (经本 round 授权); results/research_loop/r406_alpha_sweep/ 全 .sha256。
- 不碰 R378 held-out 库; 不训练; 不重开 R375/R380-R382 任何停止规则。

## Cross-references

- paper/paralleled_vsg_marl/working/route_decision_alpha_sweep_2026-08-16.md
- tmp/yang_md_decoupling_marl/external_solution_assessment.md (P2)
- tmp/yang_md_decoupling_marl/external_solution_v2_root_cause.md
- CLM-1025, CLM-1030, CLM-1035, CLM-1040 (父证据)

## Formal launch contract

- formal_entry: scripts/run_r406_alpha_sweep.py (execute 子命令; 前置验证:
  source/parent hash、installed ANDES package/case、output absence、合同
  closed; create-only 结果 + .sha256 侧车)
- rehearsal_command: scripts/andes_scratch.py 启动同一 formal_entry 的
  --rehearse 路径(WSL), 走 same pre-attempt verification path, 不创建正式
  attempt。
- rehearsal_scope: same-pre-attempt-path; α=0.675 单臂 + 1 条 50 步开发轨迹;
  不创建任何正式产物。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case,
  output_absence, 初始化残差, 折叠矩阵有限。
- wsl_python_processes: 3 (1 launcher + 2 workers)
- native_threads_per_process: 1
- capacity_evidence: memory/rounds/R406/capacity_evidence.json
  (同日同机 ladder: rung 4 全绿 0.2254 jobs/s; 预算 3 锚定于 rung 4)
- host_process_budget: 3
- other_reserved_processes: 0
- 启动前置条件: R405 已 terminal(memory/rounds/R405/verdict.md 存在)后
  才可创建 formal attempt; 声明值仅在该时序下有效。预算一经 seal 不得按
  结果改动; attempt 创建前失败 → aborted, 修复走后继 round。

## Execution amendments (registered before use, R402 precedent)

- A-1 (alpha propagation repair): 首次 execute 对 8 个网格点全部产生了相同数字——
  controller_spec 从 distributed_candidates 读取 highpass_alpha, 而 sweep_contract
  只覆盖了无消费者使用的顶层字段, 8 个点实际重跑了同一个 alpha=0.90 控制器。
  修补: sweep_contract 把网格点写入每个候选; alpha_check 增加运行时守卫;
  回归测试 test_sweep_contract_propagates_alpha_into_candidates 锁定传播。
  预修补 attempt 保留于 results/research_loop/r406_alpha_sweep_pre_repair/。
  修补不改网格/阈值/判定树/数据组。
