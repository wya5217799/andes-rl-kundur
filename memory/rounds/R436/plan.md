---
round: R436
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-19'
closed: '2026-08-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R436 plan — 能量端口锚定残差 MARL canary (环 1)

**Opened**: 2026-08-19
**Driver**: owner 授权补充实验环 1: 在已验证的能量端口对象 (bandpass K=3.5,
R408/R409 通过 dev+heldout) 上, 第一次测学习器——基线锚定残差 SAC,
零残差 = 精确确定性基线 (天然 hard no-harm 兜底)。两向皆值钱:
残差学习改善 K=3.5 -> 论文叙事可翻转; 无增量 -> "学习无价值"结论
扩展到成功接口。
**Parent**: CLM-1210 (R409 HELDOUT-PASS), CLM-1195 (R408 Q-ENTRY),
CLM-1315 (R431 SAC+slew), CLM-1325 (R433 SAC 惩罚), CLM-1330 (R434 拓扑迁移)

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

- 对象: 四 VSG 可行性原生能量端口 (buses 12/16/14/15, R408/R409 对象,
  `AndesVSGEnergyPortEnv` + `FeasibilityNativeVSGActionMap`)。训练与评估
  均经 `scripts/andes_scratch.py` (WSL), ANDES 2.0.0, kundur_full.xlsx。
- 确定性基线: 冻结 bandpass K=3.5 (R409 字节相同结构, zeta 0.35,
  bilinear 0.4Hz 增益校正, ring-edge 频率差, clip ±0.70), 作为残差锚。
- 学习臂 (新): per-agent SAC (`SACAgent`, R430/R431 配置: 4x128,
  twin-Q, auto-alpha [0.005,5.0], lr 3e-4, gamma 0.99, tau 0.005,
  batch 256, buffer 10k, grad cap 1.0, one update/env step), 每 agent
  输出 1 维归一化残差标量。
- 残差映射 (复用 `map_residual_action`, 已有测试): 残差 x ∈ [-1,1] 经
  runner 缩放 0.70 (与基线 clip 同量纲), 映射到 基线±headroom;
  零残差 -> 精确 bandpass 输出; 外层投影恒等 (identity guard)。
- 两臂: `residual_sac_no_message` (邻居 obs 槽归零) /
  `residual_sac_message` (满邻居槽)。参照臂: bandpass_k3p5 (R409 sealed
  数值可引用, 同对象同条件) + zero_feedback。
- 观测 (每 agent, 冻结): 7 槽行 = [本地频率偏差, 本地 RoCoF, 本地 P_es,
  2 邻居频率偏差 (消息臂满值/无消息臂 0), 上次残差]。频率偏差 =
  (f - 60)/60 Hz 归一化, RoCoF = Δf/0.2s 归一化, P_es 用 contract
  归一化分母。无 area-mean 增强 (与历史 ckpt 不兼容, 且本对象无旧 ckpt
  复用——纯新对象, 新契约)。
- 奖励 (冻结公式, objective-semantics 门: rehearsal 梯度方向探针 +
  定向测试钉方向):
  r_i = 100*r_f,i + 50*r_abs,i + 0.0056*r_H + 0.0056*r_D 同 R431
  公式逐字 (freq 恢复 + 动作幅度 + 差分/公共能量), 但动作项基于
  **残差标量**而非 M/D 向量: r_abs,i = -(残差_i)^2 均值; r_f/r_H/r_D
  从 freq_hz_physical + 差分坐标构造 (与 R431 同语义)。精确公式
  `memory/rounds/R436/formulas.md` 在 seal 前冻结并 hash。
- 训练: 8 profiles (R408 dev bank 条件子集, 冻结), seeds 401-405
  (R431 统计规模), 43,200 steps/run, 10 runs (2 臂 x 5 seeds),
  R428 训练循环逐字复用 + 单 seam: 动作路径换成残差映射。
- 评估: R413 的 10 个 EIG-sound 变体 (学习臂从未见过; bandpass 参照
  与 local 参照重跑同变体, R434 先例) + nominal 锚 (R408 dev 数值
  1e-6 相对复现)。守卫: R409 全套 (r_d <= 0.95, r_cross <= 1.10,
  all R379 guards)。无训练期 holdout 访问。
- 判定树 (预注册):
  - 任一残差 SAC 臂在 >=1 变体上 r_d <= 0.95 且 r_cross <= 1.10 且全
    守卫过, 且该变体 bandpass 参照未达 -> LEARNED-BEYOND-DETERMINISTIC
    (翻转性结果, 停 claim gate 问 owner)。
  - 消息臂 5-seed 中位 r_d 或 r_cross 显著优于无消息臂 (相对差 >10%)
    且不劣化守卫 -> MESSAGE-INCREMENT (bounded)。
  - 两臂均无变体达标且消息对比无增量 -> NO-LEARNING-INCREMENT
    (有界负结果: 能量端口对象上锚定残差学习无增量)。
  - 训练/评估有效性失败 (bank invalid) -> CANARY-INVALID, 记执行失败
    不判科学结论。

## Gate

- 训练前: scratch 小预算 (1200 steps) 验证残差映射 identity + SAC
  学习器能存储/更新 + reward 有限。
- preflight R436 绿 (BLOCK=0)。
- rehearsal: 走 formal entry 同 pre-attempt path (source hashes,
  installed runtime, output absence), 1 条 bandpass 参照轨迹 +
  1 条残差 SAC 轨迹 (3 episodes), objective-semantics 梯度方向探针
  (`gradient_probe` / `gradient_probe_message`, 残差项梯度方向 =
  惩罚下降/奖励上升, r_abs_alignment +28.0 通过) 写 rehearsal JSON。
- seal: formal_seal.json (contract sha, launch budget, sources)。
- 正式: 10 训练 shards (worker 阶梯选 rung, native threads 1) + eval
  shards + classify。
- 容量: 阶梯 rungs 1/2/4/8/12/16, ≥32 tasks/rung, 5%±2pp 边际规则 +
  内存记账 (900MB RSS/worker 底 + 4GiB OS headroom, owner 2026-08-17
  规则)。host_process_budget 与 other_reserved_processes 在 seal 冻结
  (并行轮 R437 已 close, 无在飞 reserved)。

## Outcomes (pre-registered)

- LEARNED-BEYOND-DETERMINISTIC: 任一残差 SAC 臂在某变体 r_d<=0.95 且
  r_cross<=1.10 且全守卫过, 而 bandpass 参照同变体未达 (含 nominal)。
  -> 翻转性结果; 停 claim gate, owner 重评 title/叙事。
- MESSAGE-INCREMENT: 消息臂 5-seed 中位 r_d 或 r_cross 相对无消息臂
  改善 >10%, 且守卫不劣化。-> bounded 正增量, 按协调价值写。
- NO-LEARNING-INCREMENT: 两臂均无变体达标 (bandpass 已达的除外) 且无
  消息增量。-> 有界负结果: 能量端口对象上锚定残差学习无增量。
- CANARY-INVALID: bank 有效性失败 (TDS 失败率/非有限/身份漂移/锚点
  复现失败)。-> 记执行失败, 不判科学结论。
- 无论哪支: nominal 锚 (bandpass r_d=0.938947, r_cross=0.539791) 必须
  1e-6 相对复现; 守卫= R409 全套 (r_d<=0.95, r_cross<=1.10, R379
  guards)。

## 资产保护契约

- 只读: R408/R409/R413/R415 sealed results, src/ 全部既有文件,
  scripts/ 全部既有 runner, tests/ 全部。
- 新建: `scripts/run_r436_energy_residual_sac.py` (新 runner),
  `src/andes_rl_kundur/agents/residual_sac.py` 或 runner 内 adapter
  (若复用 SACAgent 不加文件), `tests/test_run_r436_*.py` 定向测试,
  `memory/rounds/R436/formulas.md`, results root, MANIFEST 登记。
- 不改: `feasibility_native_vsg_action.py` (residual seam 已存在,
  不改), `sac.py`, `andes_vsg_env_v4.py`, `vsg_energy_port_env.py`,
  `gate_b3_deterministic.py`。
- title 治理: 本轮若 LEARNED-BEYOND-DETERMINISTIC, 结果进手稿需
  owner 重评 title/叙述; 否则按有界负结果写。

## Cross-references

- CLM-1210 (R409 HELDOUT-PASS), CLM-1195/1200/1205 (R408), CLM-1310
  (R430), CLM-1315 (R431), CLM-1325 (R433), CLM-1330 (R434),
  manuscript_evidence_map next-evidence-path #4 (官方登记方向),
  ROUTE.md Phase 1-2 对照
