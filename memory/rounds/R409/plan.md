---
round: R409
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-16'
closed: '2026-08-16'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R409 plan — held-out gate for the R408 Q-ENTRY candidate (bandpass K=3.5)

**Opened**: 2026-08-16
**Driver**: R408 (CLM-1195) found the frozen 0.4 Hz ring-edge bandpass
entering Q = {r_d <= 0.95, r_cross <= 1.10} at K=3.5 on the disclosed
development bank; the R408 plan's pre-registered decision tree required a
separately registered held-out gate for the found arm before any
title-supporting use.
**Parent**: CLM-1195 (R408 Q-ENTRY), CLM-1190 (R407 BAND-FAIL), CLM-1185
(R406 alpha sweep).

## TL;DR

Run the frozen single-family bandpass at K=3.5 on the R379 evaluation
(held-out) bank — the unseen probe/disturbance scenarios (PQ_0 / bus15,
seed 42, 0.2 s x 50 steps) — with arms zero / local / bandpass_k3p5, the
same frozen estimators, thresholds (r_d <= 0.95, r_cross <= 1.10), and all
guards.  Both endpoints passing with every guard -> HELDOUT-PASS (the
candidate is eligible for title-supporting use); otherwise HELDOUT-FAIL
(bounded; the R408 result remains a development-bank result only).

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

### 冻结对象与结构（与 R408 完全一致的对象与实现）

- 对象: R376-R379 四 VSG feasibility-native 能量端口, seed 42,
  0.2s x 50 步; 估计器与守卫同 R408/R407。
- 候选臂: bandpass_k3p5 = RingBandpassDamping(K=3.5, zeta=0.35,
  f0=0.4 Hz, 双线性 + 0.4 Hz 增益校正), 环边差分, clip +/-0.70,
  经 feasibility-native map。
- 评估库 (held-out, 从未执行): R379 evaluation 阶段场景 ——
  probe_condition eval3_probe_pq0_minus_0p40 (delta_u PQ_0 -0.40),
  disturbance eval3_disturbance_pq0_plus_0p60 与
  eval3_disturbance_bus15_plus_0p55; 8 配对探测 + 2 扰动/臂,
  3 臂 (zero_feedback / local_feasibility_native / bandpass_k3p5),
  共 30 条轨迹。
- 阈值: 差模比 <= 0.95, 交叉比 <= 1.10, 全部守卫; 严格交叉门 <= 0.95
  作为附加记录。

### 判定树（预注册）

- bandpass_k3p5 双端点过 + 全守卫 -> HELDOUT-PASS（候选进入可引用状态;
  该 arm 可用于论文正文, 但仍遵守线路 title 政策）。
- 任一端点不过或任一守卫不过 -> HELDOUT-FAIL（R408 结果保持为
  开发库结果; 不重试、不调参、不换结构）。
- 执行不完整/无效 -> INVALID。

## Gate

Pre-registered decision tree: HELDOUT-PASS / HELDOUT-FAIL / INVALID。
claim 收尾前 reserve_claim.py --round R409。

## 资产保护契约

- 只读: R376-R379/R406/R407/R408 sealed 产物、gate_b3_deterministic.py、
  feasibility_native_deterministic.py、energy-port 环境、
  ring_bandpass_damping.py、blend_damping.py。
- 新增（经本 round 授权）: scripts/run_r409_heldout_gate.py +
  tests/test_r409_heldout_gate.py。
- 不训练; 不重开 M/D 路径; R404 数值不进 title-supporting results;
  held-out 库只用这一次。

## Cross-references

- memory/rounds/R408/plan.md (判定树: 后继 held-out 门)
- paper/yang_md_decoupling_marl/reports/R408.md
- CLM-1195 (R408 Q-ENTRY), CLM-1190 (R407), CLM-1185 (R406)

## Formal launch contract

- formal_entry: scripts/run_r409_heldout_gate.py (--execute; 前置验证:
  source hash、installed ANDES package/case、output absence; create-only
  结果 + .sha256 侧车)。
- rehearsal_command: scripts/andes_scratch.py 启动同一 formal_entry 的
  --rehearse (WSL), same pre-attempt verification path, 不创建正式产物。
- wsl_python_processes: 9 (1 launcher + 8 workers)
- native_threads_per_process: 1
- capacity_evidence: memory/rounds/R409/capacity_evidence.json
  (本 round 自测 ladder rungs 1/2/4/8; 预算 9 锚定于 rung 8)
- host_process_budget: 9
- other_reserved_processes: 0
- 预算一经 seal 不得按结果改动; attempt 创建前失败 -> aborted。
