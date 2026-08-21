---
round: R439
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-19'
closed: '2026-08-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R439 plan — 时变动作 oracle: RQ2 从静态律族扩展到时变族 (环 5)

**Opened**: 2026-08-19
**Driver**: RQ2 目前只对静态律族成立 (R399 9 律 + R416 21 律, oracle 均零
headroom)。审稿人可问"时变增益/动作序列呢?"。本环把 outcome-seeing
oracle 扩展为有界时变动作序列 (分段常数, 有限网格), 若仍零增量则
"确定性已到顶"从静态族升级为有界时变族。
**Parent**: CLM-1140 (R399), CLM-1235 (R416), CLM-1210 (R409)

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

- 对象: R416 同对象 (direct M/D, four VSG, R379 评估银行 4 profiles,
  seed 399, 0.2s x 30 步 (R416 同窗口), 冻结 estimators/guards)。
- 基线参照: R416 21 律中 development 选中律 km3_kd2 (sealed 数值引用)。
- 时变 oracle 构造 (新 seam, `scripts/run_r439_timevarying_oracle.py`):
  - 每个 profile 的 30 步窗口分为 K 段 (K in {2, 3, 5}, 冻结), 每段
    增益取 R416 网格的对角子集 {(0.5,0.5), (1,1), (1.5,1.5), (2,2),
    (3,3)} (5 值; 段内常数)。[2026-08-19 执行前修正: 原文本写 R416
    全网格 5x4=20 值, 与 "K=2: 25 组合; K=3: 125" 矛盾且 K=3 枚举
    会爆炸到 8000; 对角子集使枚举数回到预注册的 25/125/3125, 并保留
    "与 R416 同网格"的字面语义 (对角子集包含于 R416 网格)]。
  - outcome-seeing 选择: 对每 profile 独立穷举 (K=2: 25 组合;
    K=3: 125), K=5 用随机 200 样本 (预注册, 防组合爆炸)。
- 判定: 时变 oracle 在评估 profile 上的 r_d/r_cross 相对静态选中律
  km3_kd2 的改善 >5% (端点任一) 且守卫不劣化 -> TIMEVARYING-HEADROOM
  (RQ2 边界收窄: 静态族无增量但时变族有); 否则
  NO-TIMEVARYING-HEADROOM (RQ2 升级: 有界时变族也无增量)。
- 成本: eval-only, 每候选块 = 该 profile 全部 6 场景 (~35s 实测,
  5.6s/轨迹), 350 块/profile (25+125+200) ≈ 3.5h/profile, 4 profiles
  并行 shard。容量阶梯复用 R416 (同对象同硬件)。

## Gate

- preflight R439 绿。
- rehearsal: 1 条时变候选轨迹 (K=3 随机段) + 1 条静态参照, 身份/
  守卫检查。
- seal: formal_seal.json + hashed results + MANIFEST 登记 (LOCAL-ONLY)。
- 无训练, 无 tuning, 无 bank 重开。

## Outcomes (pre-registered)

- TIMEVARYING-HEADROOM: 时变 oracle 任一评估 profile 相对 km3_kd2
  改善 >5% (r_d 或 r_cross) 且守卫全过 -> RQ2 从"静态族无增量"收窄为
  "静态族无增量、时变族有增量", 论文讨论需按此写。
- NO-TIMEVARYING-HEADROOM: 所有 profile 改善 <=5% 或守卫劣化 ->
  RQ2 升级: "有限静态律族 + 有界时变族均无实测增量" (bounded)。
- CANARY-INVALID: 执行/身份/守卫有效性失败 -> 不判科学结论。
- 无论哪支: km3_kd2 静态数值必须复现 (R416 sealed, 1e-6)。

## 资产保护契约

- 只读: R416/R399 sealed results, src/, scripts/, tests/。
- 新建: `probes/r439_timevarying_oracle.py`, results root, MANIFEST 行。
- 不改: 无 src/scripts 修改; 无训练。

## Cross-references

- CLM-1140 (R399), CLM-1235 (R416), ROUTE.md Phase 1
