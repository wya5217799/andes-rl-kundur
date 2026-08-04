---
round: R291
state: completed
opened: '2026-07-30'
closed: '2026-07-30'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R291 plan — 状态感知平滑交接 Gate A

**Driver**: 检验固定 3 s 的缺口究竟是交接机制，还是仅需更长支撑。
**Parent**: CLM-0590、CLM-0610、Q-0048

## TL;DR

不训练。慢层、V4、储能、快速幅值冻结。新 24 场景 bank。五臂含 slow、
fixed 3/5 s、common/full handoff。状态门若不能以性能或等效性能/更低动作
量击败 fixed 5 s，就没有 timing value。

## Snapshot at plan-time (oracle as of 2026-07-30)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0048 [opened R291] Does deterministic state-aware smooth handoff provide timing-specific value beyond fixed 3 s and fixed 5 s fast-support schedules?

## Recently Closed (last 3)

- Q-0047 closed-partial @ R290, by CLM-0665 — Does genuine network-configuration variation create material small-signal value for topology-conditioned differential-inertia allocation?
- Q-0046 closed-positive @ R287, by CLM-0650 — Does the frozen differential-allocation gain retain material value when the declared inter-area corridor weakening is extended from k=2.0 to k=2.5 and k=3.0?
- Q-0045 closed-positive @ R286, by CLM-0645 — Does the differential-allocation gain survive a weakened inter-area tie corridor in time domain, and does it depend on disturbance location?

## Methodology

### 冻结对象

- plant：V4 + 独立 ESD1 储能；不改 env。
- slow：R274 droop--PI，四设备等分；不改增益。
- fast：四机公共 `M` 动作；幅值 `+0.25`；`D=0`；`q=0`。
- dt `0.2 s`；300 步 / 60 s；物理 60-Hz 指标。
- bank：R274 分层生成器，seed `2026073001`；24 场景；4 位置 x 2 符号 x
  3 强度；与 R274/R279 `delta_u` 零重合。
- 全纳入；不筛选、不 redraw；任一臂未完成即 `INVALID`。
- paired bootstrap：10,000 次；seed `2026073002`。

### 五臂

| arm | slow BESS | fast common M |
|---|---|---|
| `slow_only` | on | off |
| `fixed_3s` | on | `0.25` 前 15 步，后为 0 |
| `fixed_5s` | on | `0.25` 前 25 步，后为 0 |
| `common_handoff` | on | 公共频差/频差率状态门 |
| `full_handoff` | on | 公共状态 + 区域差模 + slow gap |

状态门只用上一步已测物理量决定下一步动作。已有 15-step actor 不外推。

### 冻结交接契约

- `e = 60 Hz - mean(f_i)`；频差率用最近 3 个间隔的因果差分。
- 频率分辨率 `epsilon_f_res = 0.005 Hz`。
- 频差率分辨率 `epsilon_r = 0.025 Hz/s = epsilon_f_res / dt`。
- 恢复相：`e * de/dt <= -0.000125 Hz^2/s`；或
  `|e| <= 0.05 Hz` 且 `|de/dt| <= 0.025 Hz/s`。
- 最短 on-time `1.0 s`，来自 BESS full-scale ramp；确认与最短 off-time
  均 `0.6 s` / 3 步。
- 退出/重入迟滞倍数 `2.0`。
- `full_handoff` 另需 `|Delta f_AB| <= 0.05 Hz`，且每设备
  `|Pslow_req-Pslow_actual| <= 0.072 pu`。后者等于冻结
  `0.36 pu/s` ramp 的一个 0.2-s 步长。
- taper `1.0 s` / 5 步：内部动作每步最多 `0.05`；禁止从 0.25 阶跃到 0。
- 最迟 t=4.0 s 开始安全 taper，t=5.0 s 必为 0。若当时未 ready，记录
  `forced_release=true`，不能冒充成功交接。
- 每设备 action-L1 最大 `1.25 action-s`；fixed 3 s 为 `0.75`。初始
  0→0.25 允许；其后 slew 最大 0.05。记录 gate/switch/release/forced/TV/
  remaining budget。

### 注册指标

共同主指标，均越低越好：

1. 控制相对 `3--10 s` 的 worst-bus frequency IAE；
2. 同窗 common-frequency secondary peak。

守卫：

- full-horizon `vsg_mean_iae_hz_s`；
- `final_window_common_abs_mean_hz`；
- `max_abs_rocof_hz_s`、`worst_bus_peak_abs_hz`；
- `normalized_sync_loss_hz2`、前三秒 `fast_inter_area_iae_hz_s`；
- completion/TDS、上 10% tail、SOC、功率、能量、ramp/capability、
  constraint、动作幅值/slew/L1/TV；
- 交接强制释放数、switch count、最小 inter-switch time。

连续比较只用五臂均完成对；失败保留并阻断正向判定。

### 归因比较

历史实测 `r274_prospective_active_power_authority` 与
`r275_fast_md_authority` 只提供 actuator/慢层可用性的动机，不提供 R291
效果基线或阈值。R291 所有五臂在新
`r291_state_aware_handoff` bank 上重新成对测量。

1. `common_handoff - fixed_3s`：实用增益。
2. `common_handoff - fixed_5s`：timing value；排除更长时域。
3. `full_handoff - common_handoff`：额外差模/slow-gap 状态价值。
4. `fixed_5s - fixed_3s`：纯 duration value。
5. `slow_only`：快速层权威背景，不参与 timing 成功门。

material：点值 `<= -2%`、paired 95% 上界 `<0`；non-inferior：两主指标
上界 `<=+2%`；effort：L1 点值 `<=-10%`、上界 `<0`；no-harm：守卫点值
与上 10% tail 均不高于 `+5%`。

### Ask Matt 工程工单

- academic goal / acceptance：隔离 timing 与 duration；服从本 plan 五臂、
  阈值、统计、gate。
- blocker / deliverable：新增 stateful supervisor、telemetry、可 hash/resume/
  不覆盖的 prepare/run/analyse seam。
- authority：只新增 R291 code/tests/round/results/feed；不改 env/train/历史。
- verification：red-green；focused/full pytest、Ruff、WSL smoke、preflight。
- return gate：代码绿、seal 前 trace=0 后归还科研 gate；不得改科学契约。

## Gate

先判有效性。source/seal/bank/hash 漂移、任一缺臂/失败、非有限指标、物理
违规、动作预算超限均为 `INVALID`。

`common_handoff` 只有同时满足下列条件才有 timing value：

1. 相对 fixed 3 s 两主指标都 material；
2. 相对 fixed 3 s 全守卫 no-harm；
3. 相对 fixed 5 s 二选一：
   - 至少一主指标 material，另一主指标 no-harm；或
   - 两主指标 non-inferior，且 action-L1 effort benefit；
4. `forced_release_count=0`，动作与物理守卫全过。

若通过，分类 `HANDOFF-POSITIVE-COMMON`。`full_handoff` 自身先通过同一
timing gate；再相对 common 至少一主指标 material、另一主指标 no-harm，
才升为 `HANDOFF-POSITIVE-FULL`。否则删额外状态。

若 fixed 5 s 优于 fixed 3 s，但两个状态门均无 timing value，分类
`FIXED-DURATION-ONLY`。若连 duration 也无有效增益，分类
`NO-HANDOFF-VALUE`。部分主指标有信号但未过联合门，分类
`HANDOFF-PARTIAL`。

Kill：非正向即停止 learned gate/MPC；不调阈值、不换 bank、不补 seed。
full 不胜 common 就删除 diff/slow-gap 触发。

## Outcomes

- `HANDOFF-POSITIVE-FULL`：full 先过 timing gate，再显著胜 common。
- `HANDOFF-POSITIVE-COMMON`：common 过 timing gate；full 无额外价值。
- `HANDOFF-PARTIAL`：存在注册主指标信号，但联合门或守卫未全过。
- `FIXED-DURATION-ONLY`：fixed 5 s 有效；状态门不能证明 timing value。
- `NO-HANDOFF-VALUE`：固定延长与状态交接均不清除联合物理门。
- `INVALID`：seal、hash、完成、有限性、预算或物理契约任一失效。

## 资产保护契约

- 不改 `base_env.py`、`andes_vsg_env_v4.py`、storage env、`train.py`、
  R274--R290、历史 claim/trace/seal/checkpoint。
- 新增：
  `src/andes_rl_kundur/evaluation/state_aware_handoff.py`、
  `scripts/run_r291_state_aware_handoff.py`、
  `tests/test_state_aware_handoff.py`、
  `results/r291_state_aware_handoff/`、
  `paper/icems2026/reports/R291.md`。
- real ANDES 只用 WSL `/home/wya/andes_venv/bin/python`，最多 3 进程，经
  `scripts/andes_scratch.py`。
- 不 stage、commit、push、PR。保留所有已有脏工作树内容。

## Cross-references

- Q-0048
- CLM-0590 / R276 additive-only
- CLM-0610 / R280 scalar centralized-vs-shared boundary
- `docs/research/2026-07-30_state_aware_multitimescale_handoff_deep_research.md`
