---
round: R440
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-19'
closed: '2026-08-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R440 plan — 能量端口正结果鲁棒性扩展: N-2 开断 + 控制器延迟 (环 6)

**Opened**: 2026-08-19
**Driver**: 正结果 (bandpass K=3.5) 目前只测过 10 个单因子变体 (R413)
与 3 块 unseen 银行 (R415/R417)。manuscript_evidence_map next path #2/#3
登记了 N-2 组合与控制器延迟两轴未执行。本环补这两轴, 把正结果的
鲁棒性包络从"单因子拓扑"扩到"N-2 开断 + 延迟", 全部走 CLM-0665 EIG
硬门。
**Parent**: CLM-1225 (R413), CLM-1230 (R415), CLM-1210 (R409),
CLM-1195 (R408)

## TL;DR

(完成后填)

## Snapshot at plan-time (oracle as of 2026-08-19)

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

**冻结契约 (prospective):**

- 对象: R408/R409 能量端口对象 (四 VSG, feasibility-native map,
  bandpass K=3.5 冻结结构), R409 阈值 (r_d<=0.95, r_cross<=1.10,
  strict 0.95 记录, R379 全套守卫)。
- 两轴 (独立 block):
  - N-2 轴: 组合开断 (corridor 7-8 双回 + corridor 8-9 双回 + 跨走廊
    组合), 冻结 8 个 N-2 变体, 经 `apply_line_outage()`; 每个变体
    EIG 硬门 (CLM-0665: TDS.test_ok, exit_code=0, init residuals,
    finite spectrum, positive-real guard), 不 sound 的变体记录不判。
  - 延迟轴: 控制器输出加冻结延迟 1 步 (0.2s) / 2 步 (0.4s), 冻结
    2 个延迟档, nominal 拓扑。
- 每变体/每档: zero/local/bandpass_k3p5 三臂同条件 (8 paired probes +
  2 disturbances), 同块内 candidate-versus-local 比值。
- 判定: 全部 sound 变体/档位通过 (r_d<=0.95 且 r_cross<=1.10 且守卫
  全过) -> ROBUSTNESS-EXPANDED; 任一失败 -> 记录失败边界 (同 R415
  先例: 有界边界, 不 retune, 不判不可能)。
- 容量: 阶梯或复用 R413 (同对象同硬件)。

## Gate

- preflight R440 绿。
- rehearsal: 1 个 N-2 变体 (EIG 门 + 1 条 bandpass 轨迹) + 1 条延迟
  轨迹, 身份/守卫检查。
- seal: formal_seal.json + hashed results + MANIFEST (LOCAL-ONLY)。
- 无训练, 无 retune, 无 bank 重开。

## Outcomes (pre-registered)

- ROBUSTNESS-EXPANDED: 全部 sound 变体与延迟档通过 -> 正结果包络
  扩展为 "N-2 开断 + 2 档延迟" (bounded 到冻结清单)。
- BOUNDED-FAILURE: 任一 sound 变体/档位端点或守卫失败 -> 该失败
  作为有界边界记录 (与 a4_md_relaxed 同处理), 其余通过项照常报告。
- CANARY-INVALID: EIG 不 sound 或执行有效性失败 -> 不判科学结论。
- 无论哪支: nominal 锚复现 (R408 dev 值, 1e-6)。

## 资产保护契约

- 只读: R413/R415/R408/R409 sealed results, src/, scripts/, tests/。
- 新建: `scripts/run_r440_robustness_expansion.py` (import R413 链 +
  延迟 seam), 定向测试, results root, MANIFEST 行。
- 不改: 无受保护资产; 无训练。

## Cross-references

- CLM-1225 (R413), CLM-1230 (R415), CLM-1210 (R409), CLM-1195 (R408),
  manuscript_evidence_map next path #2/#3
