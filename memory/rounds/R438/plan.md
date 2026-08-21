---
round: R438
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-19'
closed: '2026-08-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R438 plan — SAC 家族消息对比方向翻转机制隔离 (环 3)

**Opened**: 2026-08-19
**Driver**: RQ4 同一消息问题两家族方向相反: CD-MATD3 家族消息对比为负
(R410/CLM-1215: −78.43%/−26.74%), adapted-SAC 家族消息对比为正
(R431/CLM-1315: +25.0%/+34.1%; R434 全 10 变体仍正)。方向翻转无机制
解释, 手稿讨论无法定位"消息价值"边界。本环做 2x2 单因子分解:
观测消息通道 (邻居频率槽) x 奖励消息通道 (eta 权重)。
**Parent**: CLM-1215 (R410), CLM-1315 (R431), CLM-1330 (R434),
CLM-1310 (R430)

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

**冻结契约 (prospective, seal 前不再改):**

- 对象: R431 同对象 (direct M/D, four VSG, matched bundle, 8 profiles,
  43,200 steps/run, seeds 401-405, SACAgent byte-unchanged, slew 投影
  0.25/step, R431 reward 逐字 r_i = 100 r_f + 50 r_abs + 0.0056 r_H +
  0.0056 r_D, 冻结 classifier/estimators/guards)。
- 2x2 分解 (R431 已有 (obs=1, rew=1) message 臂与 (obs=0, rew=0)
  no-message 臂; 本环补对角两臂):
  - `sac_obs_only`: 观测含邻居频率槽 (3:5 满值), 奖励 eta=0
    (r_f 只用自身偏差)。
  - `sac_rew_only`: 观测邻居槽归零, 奖励 eta=1 (r_f 含邻居项)。
- 与 R431 对照: message (1,1), no-message (0,0)。四臂同 bundle 同 seeds
  同预算。R431 训练 5 seeds x 2 臂 = 10 runs; 本环新增 2 臂 x 5 seeds
  = 10 runs。
- 评估: R431 协议 (nominal bank, frozen classifier, 守卫, 端点表)。
  R431 的 message/no-message 已 sealed 数值直接引用; 本环只评估新增
  两臂 + 复算对照 (nominal anchor 1e-6)。
- 判定树 (预注册):
  - obs_only ≈ message 且 rew_only ≈ no-message -> OBS-CHANNEL-DRIVES:
    正消息增量来自观测信息通道, 与奖励结构无关。
  - rew_only ≈ message 且 obs_only ≈ no-message -> REW-CHANNEL-DRIVES:
    增量来自奖励的邻居项。
  - obs_only 与 rew_only 均 ≈ no-message -> JOINT-REQUIRED: 两通道
    缺一不可 (交互效应)。
  - obs_only 与 rew_only 均 ≈ message -> REDUNDANT: 任一通道足够。
  - 任一臂守卫失效/方向混乱 -> 记边界, 不判机制 (bounded)。
  - "≈" 判据: 端点 (r_d/r_cross 5-seed 中位) 相对差 <=10% 视为同侧;
    message 对比增量 (vs no-message) 符号为主要判据。
- 无新算法/无 tuning/无 bank 重开。单因子纪律: 每臂与 R431 对应臂
  只差声明的 obs/rew 通道。

## Gate

- preflight R438 绿 (BLOCK=0)。
- rehearsal: 走 formal entry 同 pre-attempt path; 2 条短轨迹
  (obs_only/rew_only 各 1 条, 3 episodes); objective-semantics 探针
  (eta=0 时 r_f 不含邻居项, eta=1 时含 — 梯度/数值方向检查)。
- seal: formal_seal.json (contract sha, launch budget, sources)。
- 容量: 阶梯 rungs 1/2/4/8/12/16 或复用 R433 容量 (同学习器同硬件,
  无负载重测); native threads 1; host_process_budget 与
  other_reserved_processes 在 seal 冻结 (R436 若在飞, 互声明 reserved)。
- 正式: 10 训练 shards + eval + classify。

## Outcomes (pre-registered)

判据: 新增臂 5-seed 中位端点 vs R431 no-message 5-seed 中位端点。
"≈ 同侧" = 相对差 <=10%; "≈ 异侧" = 相对差 >10%。消息对比符号 = 相对
R431 no-message 改善为正 / 恶化为负。

- OBS-CHANNEL-DRIVES: obs_only ≈ message (正对比) 且 rew_only ≈
  no-message (无对比) -> 正消息增量来自观测通道 (邻居频率信息)。
- REW-CHANNEL-DRIVES: rew_only ≈ message 且 obs_only ≈ no-message
  -> 增量来自奖励的邻居项 (协调目标信号)。
- JOINT-REQUIRED: obs_only 与 rew_only 均 ≈ no-message -> 两通道
  缺一不可, 交互效应。
- REDUNDANT: obs_only 与 rew_only 均 ≈ message -> 任一通道足够。
- BOUNDED-UNCLASSIFIED: 任一新臂守卫失败 / 端点非有限 / 方向混乱
  -> 只记边界, 不判机制; 本轮不以残缺数据下机制结论。
- 无论哪支: nominal 锚必须复现 (1e-6), R431 对照数值 sealed 引用。

## 资产保护契约

- 只读: R431/R430/R428 sealed results, src/ 既有文件, scripts/ 既有
  runner, tests/ 全部。
- 新建: `scripts/run_r438_sac_message_channels.py` (import R431 链,
  单 seam: obs/rew 通道选择), 定向测试, results root, MANIFEST 登记。
- 不改: sac.py, cd_matd3.py, andes_vsg_env_v4.py, 既有 runner。
- 语言: feed 英文; plan/verdict 紧凑中文。

## Cross-references

- CLM-1215 (R410 消息修复, CD 负增量), CLM-1315 (R431 SAC 正对比),
  CLM-1330 (R434 拓扑), CLM-1310 (R430), R428 (C1-SAC 复现)
