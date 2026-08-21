---
round: R408
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-16'
closed: '2026-08-16'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R408 plan — V2 non-learning solving gate (K->0 audit, gain extension, B1/E1 blends)

**Opened**: 2026-08-16
**Driver**: Owner manuscript-route decision (2026-08-15,
working/route_owner_decision_v2_solving_2026-08-15.md): resume this line for
the V2 non-learning joint-headroom gate only, and complete the physical
re-verification experiments demanded by
tmp/yang_md_decoupling_marl/gpt_pro_math_abstraction_v2.md (P5/P6/P7/P0'/P8).
**Parent**: CLM-1180 (R405 homogenization gate), CLM-1185 (R406 alpha family
closed), R407 bandpass gate (BAND-FAIL within K in {0.10..2.00}); external
advisory candidates registered as ARTIFACTS.json v2-external-candidates.

## TL;DR

On the same registered feasibility-native energy-port object as R379/R406/R407
(buses 12/16/14/15, dev bank, seed 42, 0.2 s x 50 steps, frozen thresholds
r_d <= 0.95, r_cross <= 1.10, all guards), run four pre-registered stages:
A) K->0 anchor audit + small-gain grid of the frozen 0.4 Hz ring-edge bandpass
with per-step zero-sum telemetry (P6 discrimination); B) bandpass gain
extension K in {2.25, 2.50, 2.75, 3.00, 3.25, 3.50, 4.00} (P0'/P8 candidate,
advisory prediction r_d(3.5) ~ 0.944 / r_cross(3.5) ~ 0.569); C) fixed parallel
blend B1 (highpass alpha=0.85 + 0.70 * bandpass K=2, pre-clip mixing,
advisory prediction (0.946, 1.088)); D) time-varying A/B blend E1 (cosine
cross-fade 3.6-4.0 s, advisory prediction (0.940, 1.080)). Decision: first
candidate arm passing both thresholds and all guards -> Q-ENTRY (constructive
candidate for P0'); otherwise bounded negative for the searched finite
families (NOT a universal impossibility claim).

## Snapshot at plan-time (oracle as of 2026-08-16)

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

### 冻结对象与结构（全部复用，不修改任何 sealed 资产）

- 对象: R376-R379 同一四 VSG 能量端口对象（buses 12/16/14/15），
  feasibility-native 动作映射（FeasibilityNativeVSGActionMap +
  r272_frozen_bess_contract），开发数据组, seed 42, 0.2s x 50 步, 臂结构
  3 臂/组（zero_feedback / local_feasibility_native / 候选臂），
  phase_jobs("development") 每臂 8 探测 + 2 扰动 = 10 轨迹。
- 估计器与阈值: gate_b3_deterministic 冻结估计器; r_d <= 0.95,
  r_cross <= 1.10, 全部守卫（TDS、零和、饱和 0、SOC、动作秩、应力）;
  对比对象 = local_feasibility_native（确定性基线）。
- 主判据: 交叉阈值 1.10（与 R406/R407 执行一致）; 0.95 作为找到候选的
  附加严格门记录, 不参与主判定。

### Stage A — K->0 锚点审计与小平增益网格（P6 判别, 最高优先）

- 臂: bandpass_k0, bandpass_k1e3, bandpass_k3e3, bandpass_k1e2,
  bandpass_k3e2, bandpass_k5e2, bandpass_k7p5e2, bandpass_k0p1
  （k 与 R407 同构: k 前缀 p 表示小数点, e 表示科学计数; 例如
  bandpass_k3e3 = K=3e-3, bandpass_k7p5e2 = K=0.075）。
- 每个臂新增逐步遥测: sigma_v(t) = 1^T * normalized_action(t),
  sigma_p(t) = 1^T * (feasible_power - zero_anchor_power)(t),
  sigma_mapped(t) = 1^T * (commanded_power - requested_power)(t)（失真）。
- 预注册判定（P6 判别树, 任一支命中即记录）:
  1. r_d(K=0) 与 zero 臂能量比: 若 r_d(0) ≈ E_d(zero)/E_d(local)
     （预言 ≈ 2.79, 来自基线差模 −64.13% vs 零动作）→ 零锚点 = 零动作
     语义, 小增益异常是极限对象定义问题; 若 r_d(0) ≈ 1 → 执行层在 K=0
     退化为基线, 异常需要非线性端口解释; 其他值 → 记录并按
     ||sigma_p||_2/K 斜率继续判别。
  2. 若 sigma_v ≡ 0 且 ||sigma_p||_2/K -> c > 0: 异构端口映射破坏零和
     是一阶主因（P6 机制 a/b）;
  3. 若 sigma_p ≈ 0 且异常仍在: 协议/伪影（机制 c）。
- 本 stage 不进入 Q 判定（K<=0.1 全部已知在 Q 外）; 输出 = P6 机制判定。

### Stage B — 带通增益扩展（P0'/P8 主候选）

- 臂: bandpass_k2p25, bandpass_k2p5, bandpass_k2p75, bandpass_k3p0,
  bandpass_k3p25, bandpass_k3p5, bandpass_k4p0（K 网格冻结,
  结构/zeta/f0/离散化与 R407 完全一致）。
- 判定: 首个 r_d <= 0.95 且 r_cross <= 1.10 且守卫全过的 K ->
  Q-ENTRY(k); 全部不过 -> 记录单调性与裁剪/守卫行为, 进入 Stage C。
- 预言（advisory, 非结果）: 二次拟合 r_d(3.5) ≈ 0.944, r_cross(3.5) ≈ 0.569。

### Stage C — 固定并行混合 B1（P8 候选 1）

- 臂: blend_b1 = highpass(alpha=0.85, ks=1, kc=1, R406 结构) 与
  bandpass(K=2, R407 结构) 并行, 在公共归一化命令接口、裁剪与能量映射
  之前合成 q = q_A + 0.70 * q_B; 归一化 = clip(q, +/-0.70)。
- 判定: 双端点过 + 全守卫 -> Q-ENTRY(blend_b1); 否则记录并进入 Stage D。
- 预言（advisory）: r_d ≈ 0.946, r_cross ≈ 1.088。

### Stage D — 时变 A/B 混合 E1（P8 候选 2）

- 臂: blend_e1 = g(t) * q_A(t) + (1 - g(t)) * q_B(t), A/B 全程并行不重置,
  g(t) = 1 (t <= 3.6), cos 窗 (3.6, 4.0), 0 (t >= 4.0); A 有效时长 3.8 s。
- 判定: 双端点过 + 全守卫 -> Q-ENTRY(blend_e1); 否则 bounded negative。
- 预言（advisory）: r_d ≈ 0.940, r_cross ≈ 1.080。

### Stage F —（仅当需要）P7 幅值扫描

- 若 Stage A-D 全部未进入 Q 且时间预算允许: 对 local 与 bandpass_k2p0
  两臂做探测幅值扫描 probe_component_action in {0.05, 0.1, 0.25, 0.5},
  拟合 J(a) = J1 + c2 a^2 + c4 a^4, 判别 P7 分歧来源（高阶项 vs 协议）。
- 该 stage 的合约变更是冻结注册的一部分, 不在执行后调整。

### 判定树（预注册汇总）

- 任一候选臂（Stage B/C/D）双端点过 + 全守卫 -> Q-ENTRY（P0' 构造反例,
  记录候选; 附加记录其 r_cross <= 0.95 严格门是否也过）。
- Stage A 给出 P6 机制判定（锚点语义 + 泄漏斜率 + 协议伪影三选一/组合）。
- 全部候选失败 -> SEARCHED-FAMILIES-NEGATIVE（有限族有界负结论,
  不是"任意有限阶 LTI 不可行"定理; 与外部 P5 判定一致, 无新定理）。
- 执行不完整/无效 -> INVALID。

## Gate

Pre-registered decision tree above (Q-ENTRY / SEARCHED-FAMILIES-NEGATIVE /
INVALID)。claim 收尾前 reserve_claim.py --round R408。

## 资产保护契约

- 只读: R376-R379/R406/R407 sealed 产物、gate_b3_deterministic.py、
  feasibility_native_deterministic.py、energy-port 环境、ring_bandpass_damping.py。
  不改任何 paper-cited 资产。
- 新增（经本 round 授权）: scripts/run_r408_v2_solving_gate.py +
  src/andes_rl_kundur/control/blend_damping.py（如需要独立模块）+
  tests/test_r408_v2_solving_gate.py + tests/test_blend_damping.py。
- 不训练; 不碰 held-out; 不重开 M/D 路径; R404 数值不进 title-supporting
  results。

## Formal launch contract

- formal_entry: scripts/run_r408_v2_solving_gate.py (execute 子命令; 前置验证:
  source/parent hash、installed ANDES package/case、output absence; create-only
  结果 + .sha256 侧车)。
- rehearsal_command: scripts/andes_scratch.py 启动同一 formal_entry 的
  --rehearse 路径(WSL), 走 same pre-attempt verification path, 不创建正式
  attempt。
- rehearsal_scope: same-pre-attempt-path; bandpass_k0p1 单臂 + 1 条 50 步开发
  轨迹; 不创建任何正式产物。
- rehearsal_checks: source_hash, installed_package, installed_case,
  output_absence, 初始化残差, 遥测字段在位。2026-08-15 排练通过:
  rows=50, tds_failed=false, identity_ok=true, telemetry_present=true。
- wsl_python_processes: 9 (1 launcher + 8 workers; owner 授权并行执行,
  每个 worker 一个 native numerical thread)
- native_threads_per_process: 1
- capacity_evidence: memory/rounds/R408/capacity_evidence.json
  (本 round 自测 ladder rungs 1/2/4/8; 预算 9 锚定于 rung 8)
- host_process_budget: 9
- other_reserved_processes: 0 (2026-08-15 检查无其他研究 python 进程;
  32 核 23 GB, 空闲充足)
- 预算一经 seal 不得按结果改动; attempt 创建前失败 → aborted, 修复走后继 round。

## Execution amendments (registered before use, R402/R407 precedent)

- A-1 (blend arm registration): 本 round 的 _make_controller 分叉自 R407,
  支持 zero/local/bandpass_k*/blend_b1/blend_e1; 若执行中发现臂注册遗漏,
  按本节点先登记再修补。

## Cross-references

- paper/yang_md_decoupling_marl/working/route_owner_decision_v2_solving_2026-08-15.md
- tmp/yang_md_decoupling_marl/gpt_pro_math_abstraction_v2.md (问题集)
- tmp/yang_md_decoupling_marl/external_solution_v2_candidates_assessment.md
- tmp/yang_md_decoupling_marl/vsg_v2_* (advisory 候选)
- CLM-1180 (R405), CLM-1185 (R406), R407 feed (带通族关闭)
