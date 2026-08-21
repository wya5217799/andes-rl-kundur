---
round: R398
state: completed
manuscript_line: null
opened: '2026-08-15'
closed: '2026-08-15'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R398 plan — Yang 兼容公共—差模 MARL 新线登记

**Opened**: 2026-08-15
**Driver**: 用户明确要求另开固定标题论文线，保留 Yang 式逐 VSG 惯量/阻尼 MARL，并用最小改动让 `Decoupling-Oriented`、`Coordination` 与 `MARL` 可被同一比较识别。
**Parent**: CLM-0445；CLM-0480；CLM-0495；CLM-0550；CLM-0990；CLM-1055；`tmp/paralleled-vsg-marl/technical-route-census.json`

## TL;DR

建立独立 `yang-md-decoupling-marl` 手稿线。对象保留 Yang 式四 VSG、四 actor、逐机 `delta_M/delta_D`、本地加许可邻居信息；算法候选固定为无记忆 TD3 加公共—差模向量 critic 与公共模态 no-harm 约束。当前轮只登记方向、对象、比较与停门，不运行 ANDES、不训练。

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

1. 旧 `paralleled-vsg-marl` 保持 R382 后实验终止；新线只继承代码、接口、测试和失败边界，旧 checkpoint、数值、阈值、claim、标题措辞不转移。
2. 固定标题：`Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning`。
3. `Paralleled VSGs`：四个明确 VSG 对象；每台一个独立 actor；动作仍为本机有界 `delta_M_i, delta_D_i`，不聚合为标量或边动作。
4. `Decoupling-Oriented`：公共坐标 `z_c=(1/4)1^T delta_f` 与三个算术差分坐标 `z_d=T_d delta_f`；要求新 paired common/differential probe 上 off-diagonal cross-response 与扰动差分能量改善，并守住公共频率、最坏机频差、RoCoF、失败、饱和和动作应力。坐标变换或 reward 改善本身不算解耦。
5. `Coordination`：message-enabled 逐机执行必须超过 matched no-message/local-only arm；集中 critic 或共享参数不当作 runtime coordination。
6. `MARL`：未来只比较 Yang 对象上的 fresh scalar-reward memoryless TD3、同容量 no-message mode-aware TD3、message-enabled mode-aware TD3 与 cross-coordinate-objective ablation；四 actor 联合训练、独立执行；不声称精确复现 Yang 的 SAC。
7. 奖励/critic 保留 absolute/common-mode anchor，避免 CLM-0480 的 all-agents-drift reward hack；循环策略不进入首轮，避免 CLM-0495 旧 recurrent-target 缺陷。
8. 新 benchmark 只实质改变 operating point、VSG inertia/droop mismatch、disturbance location/sign/magnitude/distribution；第一篇保持 Kundur connectivity，不宣称 topology/VSG-count generalization。
9. 下一 evidence gate 不是训练：先在 matched strong deterministic baseline 后做 outcome-blind development screen 与 bounded non-learning joint-headroom gate。未同时出现 decoupling 改善、common no-harm 与非恒定逐机动作，立即停止。
10. 最终 MARL 比较在以后单独 round 冻结容量、训练/调参、seed/checkpoint 与 sealed evaluation 预算；本轮不预填这些预算。

## Mission contract

- Outcome: 新线、ADR、路线合同、manifest 与注册表可被项目工具读取；Direction、Design 与 comparison-identifiability 有明确返回。
- Current authority: 无 active round；旧固定标题线为 experiment-side stopped；用户授权新 successor line。
- Permitted: 新线治理、术语/ADR、前瞻比较合同、本轮 decision feed/claim/verdict 与仓库验证。
- Writable: `paper/yang_md_decoupling_marl/`、`docs/adr/0019-*`、`CONTEXT.md`、`docs/repo-hygiene/contract.json`、R398 正常 ledger/feed 资产。
- Budget: 零 ANDES、零训练、零新物理轨迹；仅本地文档与验证。
- Terminal: 新线可由 `session_context.py --line yang-md-decoupling-marl` 选择；比较门给出唯一下一 gate；R398 完整关闭。
- Pause: 只有写入与用户未提交资产不可安全合并、注册校验无法修复、或需要新实验权限时暂停。
- Progress: quiet。

## Gate

- PASS：新线选择与作用域校验通过；标题四项各有同对象证据门；新 benchmark 相对旧固定拓扑 sweep 有实质变化；下一步唯一为 non-learning joint-headroom gate；future MARL 比较至少可被明确限定并列出未冻结项。
- FAIL：复开 R382/旧 direct-M/D stop；把旧 checkpoint/结果当新证据；只换 TD3/SAC/网络；用 reward 或坐标标签代替 input-output decoupling；无 strong deterministic/no-message/objective ablation；或允许本轮仿真/训练。
- Comparison decision：下一 non-learning gate 目标为 `ALLOW`；未来 MARL gate 在 capacity/training/selection budget 冻结前保持 `QUALIFY`，不得提前启动。

## 资产保护契约

- 保留全部现有 dirty-worktree 资产，不清理、不重置、不覆盖其他论文线。
- 不改旧 feed、claim、results、checkpoint、plan/verdict、V4 paper-cited assets 与当前 programme 结论。
- 只新增新线、ADR、术语和 R398 账本；`contract.json` 仅追加一个 delivery line。
- 现有二十路线 census 为 scratch 导航输入；R398 不复制其结果到新 evidence。

## Cross-references

- CLM-0445：旧 RL 与 strong droop 的公共/差分目标取舍。
- CLM-0480：sync-only reward 的 collective-drift collapse。
- CLM-0495：旧 recurrent target 纠正边界。
- CLM-0550：exact droop-residual TD3 合同 NO-GO，禁止把 residual 当默认稳妥路线。
- CLM-0990：旧 direct M/D fixed-bank 余量 stop，只限其 formulation。
- CLM-1055：旧 power-port 路线无 joint headroom；旧线禁止 learner。
