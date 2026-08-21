---
round: R383
state: completed
manuscript_line: null
opened: '2026-08-14'
closed: '2026-08-14'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R383 plan — converter-level VSG P/Q 解耦新线治理登记

**Opened**: 2026-08-14
**Driver**: 当前固定标题线已被五家族盘点判定为只收稿；用户明确授权按三份研究报告提出的物理解耦路线继续实验，因此必须在任何新 ANDES 执行前分离论文权限、研究对象与证据账本。
**Parent**: CLM-1055；`tmp/paralleled-vsg-marl/technical-route-census.json`；`paper/paralleled_vsg_marl/working/three_report_future_experiment_route_synthesis.md`

## TL;DR

建立独立 `converter-vsg-pq-decoupling` 手稿线，保留 Kundur 两区域网络与 ANDES 2.0.0，不复开 R382。新线先验证 converter-level VSG 的初始化、逐机 P/Q 控制权和物理交叉响应；确定性解耦与非学习余量通过前禁止 MARL。

## Snapshot at plan-time (oracle as of 2026-08-14)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0103 closed-negative @ R369, by CLM-0990 — Does one globally fixed local-neighbour per-VSG M/D controller clear the deterministic efficacy and no-harm gate on the balanced development bank, while a bounded non-learning outcome oracle shows at least five percent additional headroom with nonconstant direct actions?
- Q-0102 closed-positive @ R366, by CLM-0980 — Can the fixed-title line freeze a 60-Hz, permission-matched per-VSG inertia/damping comparison contract and a deterministic baseline family that leaves a falsifiable learning gate without importing the old action-object mismatch or claiming storage feasibility?
- Q-0101 closed-positive @ R365, by CLM-0975 — Does the existing ANDES V4 candidate provide four separately addressable VSG agents with independent bounded inertia and damping actions, causal local-neighbour observations, measurable differential dynamics, and nonzero network-transmitted action authority?

## Methodology

1. 把现有二十条路线盘点作为导航输入，只继承 F4/F5 的方法、代码 seam 与停止门；旧数值、checkpoint、claim 和标题措辞不迁移。
2. 建立独立手稿线、英文路线契约与导航 manifest；原 `paralleled-vsg-marl` 保持实验终止、仅收稿，不改其证据或优先级。
3. 新线固定 ANDES 2.0.0 与 Kundur 两区域网络连接关系；允许改变发电装置对象，将 `PV+GENCLS` 代理替换为已登记的 converter-level VSG 模型。
4. 首个科学问题只问四台装置能否初始化并分别表现出带符号的 `Pref/Qref` 控制权、正确动作身份与有限 P/Q 交叉响应；不问控制性能，不训练。
5. 后续顺序固定为：对象/初始化/控制权门 → 强确定性 P/Q 解耦门 → 非学习余量与信息门 → 条件式 residual MARL → held-out 与高保真验证。
6. 小型开发 canary 用单进程或最小并发；大规模正式 bank 只在实测容量阶梯后冻结尽可能高的安全并发，每个 WSL Python 进程的原生数值线程固定为一。

## Gate

- PASS：新线可由 `session_context.py --line converter-vsg-pq-decoupling` 唯一选择；标题不预设 MARL 正结论；对象、拓扑、平台、证据隔离、首门和停门均明确；programme 不再把旧线当实验授权；治理验证全绿。
- FAIL：新线复用旧结果为证据、修改 Kundur 连接拓扑、允许在物理/确定性/余量门前训练，或旧 R382 被重新授权。
- 本轮只做治理与前瞻设计，不运行 ANDES、不产生性能证据、不训练。

## 资产保护契约

- 不改旧 feed、claim、result、checkpoint、旧 plan/verdict 与 paper-cited V4 资产。
- 保留当前工作区中三份研究报告综合文档及其 manifest 登记，不覆盖用户改动。
- 新增 `paper/converter_vsg_pq_decoupling/`、一份 ADR、programme 导航更新及本轮正常 ledger 资产。
- 三份研究报告只作为 advisory direction input；其陈述不是本线实验 evidence。

## Cross-references

- CLM-1055：R382 终止旧功率端口路线，禁止在该 formulation 上继续余量或训练。
- ADR-0015：旧线的 decoupling 明确排除 electromagnetic P/Q decoupling；新对象必须另线登记。
- 五家族盘点：当前线终局为 `MANUSCRIPT-ONLY`；新路线仍属 F5，不是算法家族扩张。
