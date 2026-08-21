---
round: R451
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-20'
closed: '2026-08-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: 'CANARY-INVALID: the shift-by-two placebo preserved every agent semantic
  neighbour set, model initialization occurred before registered seeding, and information/cost
  contrasts changed reward together with observation access; 0 training manifests
  completed, so execution was terminated and no scientific classification is allowed'
superseded_note: null
---
# R451 plan — M3 actor/critic/reward 消息因子与 shuffled-placebo

**Opened**: 2026-08-20
**Driver**: R410 与 R431 的消息对比符号相反，R438 只能把 SAC 正增量粗分为
联合观测/奖励通道，尚未分离 actor 与 critic 访问，也没有打乱消息对照或
训练代价诊断。
**Parent**: CLM-1215 (R410), CLM-1315 (R431), CLM-1360 (R438),
NOTE-0031。

## TL;DR

(完成后填)

## Snapshot at plan-time (oracle as of 2026-08-20)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] Does the finite-bank information-level margin program (shared action variables per non-anticipative info class, solution section 5.4) certify or refute INFORMATION-LIMITED for the 2% joint target under the exact R352/R353 observation histories?

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375 — Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0004 closed-negative @ R442, by CLM-1370 — AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?

## Methodology

**冻结契约 (prospective, seal 前不再改):**

- 对象与预算逐字复用 R431/R438 adapted-SAC：direct M/D、four VSG、
  matched 8-profile bundle、43,200 interaction steps/run、seeds 401--405、
  0.25/step slew projection、同网络宽度/优化器/回放容量/评估器/守卫。
- 完整 2x2x2 因子：actor neighbour access `a`、critic neighbour access
  `c`、reward neighbour term `r`，八臂 `a{0,1}_c{0,1}_r{0,1}`，每臂
  5 seeds。邻居槽严格为 observation columns 3:7；actor mask 同时用于
  在线 act 与 replay actor update，critic mask 用于 current/target critic
  与 actor-loss critic query。raw replay observation 保留后在 update 内分路，
  禁止“act 遮罩但 replay 未遮罩”。
- 加一臂 `a1_c1_r1_shuffled`：每个时间步把四个 agent 的 3:7 邻居块按
  固定二位循环置换后供 actor/critic 使用，reward 仍用真实 joint row；该
  置换逐步精确保留 pooled marginal，但破坏 agent--neighbour pairing。
- 共 45 个全新 training shards；R431/R438 数值只作漂移锚，不替代新诊断。
  每 shard 保存 per-update critic loss、actor-gradient norm、最终固定 split
  train/validation TD MSE、raw/actor/critic feature covariance rank 与有效条件数。
- 目标逐字：
  `r_i = 100 r_f,i + 50 r_abs,i + 0.0056 r_H + 0.0056 r_D`，其中
  `r_f,i=-(f_i-fbar_i)^2-sum_j eta_ij(f_j-fbar_i)^2`，
  `fbar_i=(f_i+sum_j eta_ij f_j)/(1+sum_j eta_ij)`；`r=1` 时两项
  `eta_ij=1`，`r=0` 时 `eta_ij=0`。其余 reward 无变化。
- 评价逐字复用 R431：每 seed、每 evaluation profile 的完整 records 与
  frozen endpoints/guards。主要不确定性是 seed 配对 bootstrap 90% CI
  (10000 resamples, RNG 451)；energy 越小越好。

## Theory intake

**Mechanism prediction:** true neighbour pairing should carry conditional task
value, while marginally matched but irrelevant shuffled access should expose a
finite estimation/optimization cost.

```
observable: exact nested actor/critic/reward factorial endpoints
  definition: five-seed paired differential and off-diagonal endpoint energies for all eight a/c/r cells
  source: results/research_loop/r451_m3_message_factorial/formal_analysis.json#/factorial
  predicts: true full-message access is non-worse than no-message and access effects localize to actor, critic, reward, or interactions
observable: shuffled-message placebo
  definition: paired true-full versus pooled-marginal-preserving shuffled-neighbour endpoints
  source: results/research_loop/r451_m3_message_factorial/formal_analysis.json#/placebo
  predicts: true neighbours beat both no-message and shuffled messages when conditional information has task value
observable: finite-learning penalty diagnostics
  definition: validation/train TD ratio, actor-gradient-norm variance, and active-feature condition number by arm
  source: results/research_loop/r451_m3_message_factorial/formal_analysis.json#/diagnostics
  predicts: irrelevant shuffled access raises at least two registered costs relative to no-message while failing to improve both endpoints
```

## Gate

- preflight BLOCK=0；fresh host load + R438/R431 capacity ladder 复核后选合法 rung；
  training 属 >20 min，必须 background shard driver，native threads=1。
- rehearsal 走同一 formal pre-attempt path，检查：source/parent/case/output
  absence；3:7 actor/critic mask；四行邻居块置换的 pooled marginal 不变且
  pairing 改变；真实 SAC learner 上 `r=1` 的更负协调奖励使同初值、终止样本的
  critic Q 更新方向低于 `r=0`；full/full 与原 SACAgent 一步参数更新一致。
  第一次排练把“一次更新后另一状态的 Q”误当方向门，受网络泛化干扰而失败；
  该 `rehearsal_failed_v1.json` 保留。`rehearsal_v2.json` 改为同一终止样本上的
  `-dL/dQ` 直接门并通过；随后按 R419 的门禁经验补齐真实 ANDES transition
  的 store/update 覆盖并在最终 canonical `rehearsal.json` 加入完整 SAC
  语义门；seal 只引用 canonical 文件。
- 正式完整性：45/45 training manifests 有效、全 43,200 steps、无非有限
  loss/checkpoint；45 臂评估 records 完整；全新输出 create-only + sidecar。
- `INFORMATION-VALUE-SUPPORTED`：true `111` 相对 `000` 与 shuffled 在两端点
  的 paired 90% CI 下界均 >0；任一对比未满足则 `NOT-SUPPORTED`。
- `FINITE-COST-SUPPORTED`：shuffled 相对 `000` 未在两端点同时改善，且
  validation/train TD ratio、actor-gradient-norm variance、active-feature
  condition number 三项中至少两项的 5-seed median 更高；否则
  `NOT-SUPPORTED`。
- 总判定为两项的四象限：`VALUE-AND-FINITE-COST`、`VALUE-ONLY`、
  `FINITE-COST-ONLY`、`M3-REFUTED`。任一完整性/锚/有限性失败为
  `CANARY-INVALID`，不重试。

## Outcomes (pre-registered)

- 不论分支，R410 与 R431 跨家族符号不作为因果配对；本轮只识别 adapted-SAC
  内部通道与有限训练代价。
- 新 `000/111/110/001` 四角的 5-seed endpoint median 必须在对应 R431/R438
  sealed median 的 10% 内；超出即漂移锚失败并 `CANARY-INVALID`。

## Formal launch contract

- `formal_entry`: WSL scratch launcher + `soft_spot_shard_driver.py`，runner
  `scripts/run_r451_m3_message_factorial.py`，45 train shards，随后九臂 eval
  与 classify。
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r451_m3_message_factorial.py rehearse`。
- `rehearsal_scope`: synthetic real-learner mask/update probes + one short ANDES
  trajectory per representative arm；不创建 formal training/result。
- `rehearsal_checks`: parent hashes、installed package/case、output absence、
  `sac_semantics_probe`（含更负协调 reward 把 Q 更新向下）、nested mask、
  shuffle marginal、full-update parity。
- `capacity_evidence`: fresh no-load check and identical-learner R438 ladder;
  rungs 1/2/4/8/12/16，按实测最大合法 rung。
- `host_process_budget`: seal 后填；`other_reserved_processes`: 0；
  `wsl_python_processes`: seal 后填；`native_threads_per_process`: 1。

## 资产保护契约

- 只读：R410/R431/R438 sealed artifacts，全部 `src/`、既有 runners/tests。
- 新建：R451 runner、定向测试、capacity/rehearsal（含保留的失败 v1）/seal、
  `results/research_loop/r451_m3_message_factorial/`。
- 不改 learner/environment/parent runner；seal 后失败则 aborted，不原轮补丁重跑。

## Cross-references

- CLM-1215, CLM-1315, CLM-1360; advisory `problems/M3_message_contrast_sign.md`;
  `verification/m_observable_matrix.md`；owner decision advisory unresolved。
