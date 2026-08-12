---
round: R364
state: completed
manuscript_line: null
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R364 plan — 固定标题的研究线重置与资产复用处置

**Opened**: 2026-08-12
**Driver**: 现有两条实验线均不能让“解耦、并联 VSG 多主体协调、MARL”在同一实验对象中同时成立，必须在任何新执行前重置标题目标线与默认导航。
**Parent**: CLM-0905, CLM-0945, CLM-0965

## TL;DR

冻结三条不再承载固定标题的旧手稿线，建立一条以真实 per-VSG 对象为第一门的新标题线；旧资产只允许作为实现或设计输入，经新线前瞻验证后使用，既有结果、checkpoint 和 claim 不迁移。本轮只做治理与方向处置，不运行 ANDES、不训练、不生成性能证据。

## Snapshot at plan-time (oracle as of 2026-08-12)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0100 closed-positive @ R363, by CLM-0965 — On the exposed development bank, does adding a common residual-power channel to the three-edge zero-common action basis enlarge the per-case physical action-space headroom, showing that the zero-common residual contract itself (rather than information) limits the R358 feasibility?
- Q-0099 closed-negative @ R362, by CLM-0960 — On the exposed development bank, does replacing the one-hop neighbour snapshot messages with frozen R341-model causal prediction trajectories (DMPC-style shared prediction) let a pre-registered tuning-free non-neural map family recover both registered endpoint gates, showing learnable structure that R359, R360, and R361 could not reach from endpoint-only or snapshot-message information?
- Q-0098 closed-negative @ R361, by CLM-0955 — On the exposed development bank, does extending the exact fifteen-field edge-actor information path with one-hop neighbour messages let a pre-registered tuning-free non-neural map family recover both registered endpoint gates, showing learnable structure that R359 and R360 could not reach from endpoint-only information?

## Methodology

1. 以外部 Deep Research 报告、Yang 等 TPWRS 论文的已核实复现事实基底、现有三条手稿线的导航卡和最新绑定 claim/feed 为输入。
2. 用标题逐词审计对象一致性：`Paralleled VSGs` 要求每台 VSG 同时是物理单元与运行时 agent；`Coordination` 要求独立 per-VSG 动作和可审计的信息交互；`MARL` 要求真实多智能体训练与 matched ablation；`Decoupling-Oriented` 要求独立物理耦合指标和强确定性解耦基线。
3. 资产按 `implementation reuse`、`design reference`、`non-transferable evidence` 三类登记。V4/配置、独立 SAC/CTDE、确定性控制与封存评估框架可候选复用；旧数值、旧 checkpoint、旧 claim、scalar/edge actor 的对象语义禁止迁移。
4. 新线按最短可证伪顺序导航：对象与复现门 → 确定性解耦/协调门 → 有界 per-VSG residual MARL 门 → 才考虑 OOD、安全和实时验证。
5. 用 ADR 记录不可逆方向决策，用 `CONTEXT.md` 固定领域术语，用 `LINE.md`/`ARTIFACTS.json`/delivery contract 重设唯一 active 线，并清除研究 programme 中已关闭问题的过时优先级。

## Gate

- PASS：旧线全部不可被 session bootstrap 选中；新线成为唯一 active 标题线；导航不复制旧数值；复用边界和第一个停止门明确；所有治理、memory 和定向测试通过。
- FAIL：任何旧线仍为 active、任何旧证据被描述为新线标题证据、或者新线允许在 per-VSG 对象门通过前启动训练。
- 本轮不判定方法性能，不授权后续仿真或训练。

## 资产保护契约

- 不改任何 plant、controller、agent、evaluation 代码，不改旧 feed、claim、result、checkpoint 或手稿正文。
- 保留工作区既有未提交改动，特别是 `paper/decoupling_marl_model_first/ARTIFACTS.json` 新登记项与相邻工作文档；只做与 line-state 处置直接相关的最小修改。
- 新增 `paper/paralleled_vsg_marl/` 导航资产、ADR 和本轮治理 feed；冻结旧线但不删除其资产。
- 外部报告 SHA256 `d2dd21c5fec731f6886393f6af106dc677b496494ae468c1c79182d6217c2e76`；Yang 事实基底 SHA256 `8284cd4b07d2c19fdc1c41088ae3f378b2f04df8be181e77d46f5e809dc7737f`。两者是方向输入，不是仓库实验 evidence。

## Cross-references

- CLM-0905：ICEMS 真实分布式比较的有界负处置。
- CLM-0945：model-first 邻居因果余量门的有界负处置。
- CLM-0965：共同通道只有离线物理可行性，不含控制或学习增益。
- DOI: 10.1109/TPWRS.2022.3221439。
- ADR: `docs/adr/0015-reset-fixed-title-to-object-matched-line.md`（本轮新增）。
