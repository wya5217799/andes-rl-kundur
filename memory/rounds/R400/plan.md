---
round: R400
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-15'
closed: '2026-08-15'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R400 plan — 同线智能体训练路线前瞻修订

**Opened**: 2026-08-15
**Driver**: 用户明确要求继续既定 fixed-title 论文线，保留 Yang 式逐 VSG
智能体和 CD-MATD3，不再让 R399 的非学习筛查替代真实智能体比较。
**Parent**: CLM-1135；CLM-1140；
`paper/yang_md_decoupling_marl/working/route_contract.md`

## TL;DR

工作量：`evidence`，因为本轮前瞻修改正式路线与标题支持逻辑。保持 R399
分类和全部数值不变；在同一手稿线登记一份 successor decision，把其强确定性
控制器改为正式对手而非训练否决门，并把唯一下一步冻结为三种子开发 canary
的单独 evidence round。本轮零 ANDES、零训练、零新轨迹。

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

### Mission boundary

- Outcome: 新路线修订、LINE/ARTIFACTS 导航、decision feed/claim/verdict
  一致；下一动作唯一且不在 R400 执行。
- Permitted: 当前线内前瞻路线治理、逻辑骨架、比较与阳性门冻结、正常
  ledger/feed 收尾。
- Forbidden: 改写 R399、复用旧 checkpoint/训练曲线为新证据、学习器实现、
  ANDES、训练、调参、held-out 读取、算法替换、其他手稿线写入。
- Terminal: R400 关闭后，下一轮只可冻结并执行三种子 development canary；
  不自动进入五种子或正式评价。

### Paper skeleton

- Type: technique paper.
- Limitation 1: Yang-compatible scalar synchronization learning does not
  directly identify common-to-differential or differential-to-common response.
- Limitation 2: reward improvement does not attribute runtime neighbour-message
  coordination.
- Limitation 3: weak/no-control comparisons cannot support the fixed title
  against the strongest matched deterministic M/D law.
- Key idea: retain the Yang four-VSG/four-actor direct M/D object and introduce
  one common--differential mode-aware multi-agent TD3 bundle with explicit
  common no-harm and matched message/objective attribution.
- Challenge/module A: separate common and differential costs without
  collective drift -> vector critic plus common constraint.
- Challenge/module B: isolate coordination -> matched message/no-message arms.
- Challenge/module C: establish physical increment -> strong deterministic,
  fresh Yang-compatible learner, multi-seed held-out and physical guards.
- Contributions: one bounded learner (Methods), one physical decoupling
  definition/benchmark (Problem/Evaluation), one attribution comparison
  (Experiments). No algorithm-class, topology, safety or deployment claim.

### Prospective route amendment

1. R399 remains a valid `STOP-NO-JOINT-HEADROOM` result for its six-profile,
   nine-law finite selector. It is not reclassified and is not evidence about
   trained TD3/MATD3 performance.
2. R399's selected strong deterministic implementation becomes a disclosed
   comparator. The outcome-aware decision to train anyway is registered here;
   R399 evaluation profiles cannot be reused as unseen learning evaluation.
3. The selected method stays `CD-MATD3`; no SAC/PPO/GNN/other algorithm search.
   The inherited object stays four VSGs, four independently executed bounded
   `delta_M_i,delta_D_i` rows, and local plus permitted neighbour observations.
4. Next canary has exactly three learning arms: fresh Yang-compatible
   scalar-reward memoryless TD3, capacity-matched CD-MATD3 without runtime
   neighbour messages, and message-enabled CD-MATD3. Three fresh training
   seeds use development conditions only.
5. Canary continuation requires valid independent per-VSG execution, completed
   training/evaluation, no physical/action guard failure, no reward-only win,
   and a consistent favorable direction for the full method versus both
   learning comparators on the two registered decoupling endpoints. It does not
   support the title or open formal evaluation automatically.
6. Only a separately sealed successor may run at least five fresh seeds on a
   new held-out bank. It includes the strongest deterministic law, the fresh
   Yang-compatible TD3, full/no-message CD-MATD3, and the cross-coordinate
   objective ablation with matched budgets.
7. Formal title-positive classification requires at least 10% improvement over
   the strong deterministic comparator on both off-diagonal cross-response and
   disturbance differential energy; common-frequency integral, worst-unit
   peak and RoCoF each no worse than 103%; message-enabled consistently better
   than no-message; objective ablation removes a material increment; all
   completion, action identity, bounds, slew, saturation and stress guards
   pass. Exact estimators, uncertainty and budgets must be frozen before that
   execution.
8. A canary failure ends this selected learner without algorithm replacement.
   A formal failure ends the title-positive experiment route. Thresholds cannot
   be relaxed after outcomes.

## Gate

- PASS: one registered same-line amendment preserves R399, fixes CD-MATD3 as
  the only proposed learner, freezes the three-arm canary and five-seed
  positive logic, and authorizes no execution inside R400.
- FAIL: silently reinterpret R399; reopen its bank; switch the selected
  algorithm; omit the strong deterministic/Yang-compatible/no-message/
  objective comparison; weaken the two physical endpoints; or launch training.
- Self-consistency: limitations -> key idea -> three challenges -> three
  modules -> three contributions must all pass.

## 资产保护契约

- 保留 dirty worktree；不 reset/clean，不覆盖其他人或其他论文线资产。
- R398/R399 plan、feed、claim、verdict、results、hash 与分类只读。
- 只新增 R400 正常 ledger/feed 与当前线 route amendment；LINE/ARTIFACTS
  只做导航和生命周期更新。
- V4、环境、agent、训练脚本、checkpoint 与 results 本轮不改。

## Cross-references

- CLM-1135：原始 Yang-compatible CD-MATD3 前瞻选择。
- CLM-1140：R399 finite-law 无联合余量，只限其非学习 formulation。
- `paper/yang_md_decoupling_marl/working/route_contract.md`：被本轮前瞻
  amendment 取代的旧 gate order；保留为历史决策输入。
