---
round: R441
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-20'
closed: '2026-08-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R441 plan — R439 时变 headroom 守卫补全 (no-harm guard completion)

**Opened**: 2026-08-20
**Driver**: R439 判 TIMEVARYING-HEADROOM 时 `_classify_profile` 只查
`valid` (有限/映射/界内/无 slew 违例) + 改善 >5%, 漏查 no-harm 守卫
(common-mode no-harm +3%、action-stress no-harm +10%); 且 R439 只存
r_d/r_cross 摘要, 原始频率轨迹被丢弃, 无法离线补查。本环重跑 R439 4 个
获胜时变候选 + 静态参照, 补完整 summary + no-harm 守卫, 分类
GUARD-CLEAN vs GUARD-VIOLATED。
**Parent**: CLM-1355 (R439), CLM-1235 (R416), CLM-1140 (R399)

## TL;DR

(完成后填)

## Snapshot at plan-time (oracle as of 2026-08-20)

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

**冻结契约 (prospective, seal 前不再改):**

- 对象: R416/R439 同对象 (direct M/D, four VSG, 评估 bank 4 profiles
  eval_a..d, seed 399, 0.2s x 30 步, 冻结 estimators/guards/阈值)。
- 静态参照: R416 development 选中律 `local_neighbour_md_km3_kd2`
  (km3_kd2, sealed 数值引用)。
- 时变候选: R439 sealed 获胜候选 (只读, runner 从
  `results/research_loop/r439_timevarying_oracle/profiles/eval_*.json`
  读 `best_timevarying.candidate` + `best_timevarying.k`, 经 .sha256
  校验; 此处仅文档化):
  - eval_a: `[[3.0,3.0],[3.0,3.0],[3.0,3.0]]` k=3
  - eval_b: `[[3.0,3.0],[3.0,3.0]]` k=2
  - eval_c: `[[3.0,3.0],[3.0,3.0],[3.0,3.0]]` k=3
  - eval_d: `[[3.0,3.0],[3.0,3.0],[3.0,3.0]]` k=3
- 每 profile: 静态参照 + winner 各跑全部 6 个 signed scenarios,
  `summarise_profile` 得完整 summary (含 common_frequency_iae_hz_s、
  worst_unit_peak_hz、worst_rocof_hz_s、action_rms、action_total_variation)。
- no-harm 守卫 (winner vs static):
  - common-mode no-harm (+3%): common_frequency_iae_hz_s <= 1.03x,
    worst_unit_peak_hz <= 1.03x, worst_rocof_hz_s <= 1.03x。
  - action-stress no-harm (+10%): action_rms <= 1.10x,
    action_total_variation <= 1.10x。
  - winner `valid` (mapping/bound/slew) 为真, 且 r_d 改善 >5% 仍成立。
- 阈值来源: R399 `md_decoupling_headroom.py::build_contract()` thresholds
  (maximum_common_harm=0.03, maximum_action_stress_harm=0.10)。
- 分类: GUARD-CLEAN (全部 no-harm 守卫过 + 改善 >5% 成立) 否则
  GUARD-VIOLATED (记录具体违反守卫 + 违反 profile)。
- 执行 seam: `scripts/run_r441_timevarying_guard.py` (importlib 加载 R439
  runner, 复用 `_run_trajectory`/`_profiles`/`_evaluation_scenarios`/
  `build_contract`/STATIC_SELECTED + `summarise_profile`)。子命令
  capacity/rehearse/prepare/shard <profile_id>/aggregate/classify。
- 成本: eval-only, 每 profile 12 轨迹 (6 静态 + 6 winner, ~5.6s/轨迹
  ≈ 67s), 4 shards 并行。容量复用 R439 阶梯或重测 (同对象同硬件)。

## Gate

- preflight R441 绿 (BLOCK=0)。
- rehearsal: formal entry 同 pre-attempt path; 1 条静态参照 + 1 条 winner
  轨迹 (eval_a), 身份/守卫检查, output absence。
- capacity: 复用 R439 capacity_evidence.json (同对象同硬件) 或重测
  rungs 1/2/4/8/12/16; assemble_capacity.py --cap-workers 4
  --other-reserved 0; host_process_budget 5, native threads 1。
- seal: formal_seal.json (contract sha, launch budget, sources) + hashed
  results + MANIFEST 登记 (LOCAL-ONLY)。
- 无训练, 无 tuning, 无 bank 重开。

## Outcomes (pre-registered)

- GUARD-CLEAN: 全部 4 profile 的 no-harm 守卫 (common-mode +3%,
  action-stress +10%) 全过, winner valid, r_d 改善 >5% 成立 ->
  R439 时变 headroom 守卫干净, 解耦兼容性 (common-mode 无害 +
  降交叉/差分) 成立。
- GUARD-VIOLATED: 任一 profile 任一 no-harm 守卫违反 -> 记录具体违反项;
  CLM-1355 的 "cross-response not degraded" 需收窄为 correction。
  - 若违反涉及 common-mode 无害 (不是只 action-stress), 动摇论文
    "时变族有余量" 的解耦兼容性, feed 写清边界。
- CANARY-INVALID: 执行/身份/守卫有效性失败 -> 不判科学结论。
- 无论哪支: km3_kd2 静态数值必须复现 (R416 sealed, 1e-6)。

## 资产保护契约

- 只读: R439/R416 sealed results (只读不改), src/, scripts/ 既有,
  tests/ 全部。
- 新建: `scripts/run_r441_timevarying_guard.py`, results root
  `results/research_loop/r441_timevarying_guard/`, MANIFEST 行。
- 不改: 无 src/scripts 既有文件修改; 无训练。

## Cross-references

- CLM-1355 (R439), CLM-1235 (R416), CLM-1140 (R399), RQ2 boundary
  refinement (R439 feed)
