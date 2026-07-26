---
round: R266
state: completed
opened: '2026-07-25'
closed: '2026-07-25'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R266 plan — 先拆 gate 抖动，再只选一个平滑机制

**Status**: COMPLETED
**Opened**: 2026-07-25
**Driver**: R265 物理均值赢，但 action-TV 爆；先用旧轨迹拆清来源，再查文献选唯一机制。
**Parent**: CLM-0525, Q-0029

## TL;DR

不跑新 ANDES，不训练，不扫 R265。只做两件事：

1. 重构 R265 每步 alpha 和 gate 轨迹里的两个基动作；
2. 用已核验文献比较 low-pass、hysteresis/dwell、slew/rate limiting，
   冻结最多一个 Q-0029 候选。

## Snapshot at plan-time (oracle as of 2026-07-25)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0029 [opened R265] Can temporal regularisation make the state selector deployable?

## Recently Closed (last 3)

- Q-0028 closed-negative @ R265, by CLM-0525 — Will prospectively unseen load cases reproduce the candidate effect?
- Q-0027 closed-partial @ R264, by CLM-0520 — Can a state-dependent droop residual policy advance both dual metrics?
- Q-0008 closed-negative @ R252, by CLM-0415 — Verify paper-metric ranking persists at 500-ep paper convergence horizon

## Methodology

### 研究问题

- **RQ1**：R265 action-TV 主要来自基控制器变化，还是
  `delta alpha * controller disagreement`？
- **RQ2**：low-pass、hysteresis/dwell、slew/rate limiting 哪个最对症，
  且代价最可审计？
- **RQ3**：下一轮怎样预注册，才不在 R265 上调平滑常数？

### 轨迹分解

对 20 条 `mode_gate_c0p25` 原始轨迹：

1. `t>=1` 用前一步频率按冻结公式重构 `rho_t`、`alpha_t`；
2. 用 droop 公式重构 `s_t`；
3. 由 `u_t=(1-alpha_t)p_t+alpha_t s_t` 解出 `p_t`；
4. 校验重构 action 与原 trace，校验 alpha 均值/饱和比例与 telemetry；
5. 用
   `delta u_t=(1-alpha_t)delta p_t+alpha_t delta s_t
   +delta alpha_t(s_{t-1}-p_{t-1})`
   报 base、switch、不可加交互项。沿用项目 action-TV：先 agent 内 L1，
   再 agent 均值、时间求和。

这是 R265 development bank 上的 retrospective diagnosis，不是确认试验。
第一版零 ANDES 重构已在 plan 落盘前运行；因此本轮数值只用于定位和选机制，
不能写成预注册效果。基控制器是
`results/r201_w1_hreg_tau005_s54` best checkpoint 与 droop k10。

### 文献调研

三个独立视角：经典切换/增益调度控制、VSG/逆变器动态控制、
RL residual/safe action。每项先验真题名/作者，再核摘要或正文；
无法核验不进正文。至少覆盖三个机制分支，每支尽量三篇。

## Outcomes

- **机制定位通过**：action 重构误差接近数值精度；telemetry 对上；
  base/switch 分解覆盖 20/20。
- **解释区间**：
  - switch triangle share `>=0.60` 且逐场景 `corr(total,switch)>=0.90`：
    switch-dominant，可选直接约束 `delta alpha` 的机制；
  - share `0.40-0.60` 或 correlation `0.50-0.90`：mixed，只能在文献有
    稳定/硬界支持时选；
  - share `<0.40` 或 correlation `<0.50`：不选 alpha smoother，回到
    base-controller variation。
- **文献通过**：关键引用逐条 VERIFIED 或明确 PAYWALL 降级；三个分支有覆盖；
  正反证据同列。
- **选择通过**：只在项目分解和文献同时指向同一机制时冻结一个候选；
  优先可给 `delta alpha` 硬界、相位/延迟代价透明、单参数可按物理时间尺度预注册。
- 若证据不够，结论是“不选”，不凭直觉补参数。
- 本轮只 advance Q-0029；不声称 smooth gate 已通过新 bank。

## Gate

PASS = 机制定位通过 + 文献通过 + 选择通过。否则 PARTIAL：
保留分解，Q-0029 不冻结机制。

## 资产保护契约

- 不改 R265 bank、manifest、trace、summary。
- 不改 V4、checkpoint、`ratio_full_scale=0.05`、`alpha_cap=0.25`。
- 不跑 ANDES，不训练，不生成新 sealed bank。
- 只新增 R266 plan/verdict、CLM-0530 和一份 `docs/research/` 中文报告。

## Cross-references

- CLM-0475：R201 比 droop k10 平滑；旧 smoothness reward 不是本轮路线。
- CLM-0525：R265 物理均值改善，但 action-TV guard 负结论。
- Q-0029：先拆 action-TV，再冻结一个动态 gate。
