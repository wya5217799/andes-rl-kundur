---
round: R401
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-15'
closed: '2026-08-15'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R401 plan — Gate A 三种子开发 canary 契约冻结

**Opened**: 2026-08-15
**Driver**: R400 修订后唯一允许的下一证据动作：前瞻冻结三种子开发 canary 的
完整契约（bank、单位、解码器、时序、奖励、预算、收敛/缺跑规则、容量、
估计器），preflight 通过后封印，零训练零评估。
**Parent**: CLM-1145 (R400)；CLM-1140 (R399)；
`paper/yang_md_decoupling_marl/working/route_amendment_r400.md`

## TL;DR

Workload: `evidence`。本轮只冻结并封印 Gate A canary 契约 + 实测 WSL 容量
证据，不实现学习器、不训练、不评估。契约以新纯模块
`src/andes_rl_kundur/evaluation/cd_matd3_canary.py` 机器可读固化，判决策树
同文件预注册；WSL 侧只跑 rehearsal 与代表性容量梯（容量 trace 排除在
evidence 之外）。封印后仅授权后继轮训练三臂×三种子，不得换算法。

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

- Outcome: 封印一份机器可读 + 计划可读的 Gate A canary 契约；实测容量证据
  RUN-READY；preflight 绿；feed/claim/verdict/LINE 一致关闭；零训练。
- Current authority: R400 修订把唯一下一步锁为三种子开发 canary 的单独
  evidence round；本 round 领号于 yang-md-decoupling-marl，无其他 active round。
- Permitted: 新纯契约模块 + 定向测试 + 契约 runner（rehearse /
  measure-capacity / prepare 三 seam），WSL 代表性容量梯（trace 非 claim
  bearing），seal，正常 ledger/feed/导航收尾。
- Forbidden: 学习器网络/训练循环实现与执行、checkpoint 选择、learning 臂的
  ANDES 评估、算法替换、旧 checkpoint/数值/prose 复用、其他手稿线写入。
- Terminal: R401 关闭且 seal 存在；canary 执行是后继轮，本轮不启动。

### Frozen Gate A canary contract（全部前瞻冻结，值不进结果回填）

#### 1. 科学对象、动作与解码器（继承 R399，逐字不变）

- ANDES 2.0.0 修改 Kundur，60 Hz 物理，四 VSG 代理，一 agent 独立执行一行
  `delta_M_i, delta_D_i`。
- 动作归一化 `[-1, 1]`，slew `0.25`，解码器非对称
  `delta_M: -200/+600`, `delta_D: -200/+600`，物理钳位 `M>=20, D>=10`，
  mapping atol `3.0517578125e-05`。
- 时序：`dt=0.2 s`，扰动后 `6 s = 30` 步窗口；toggler、随机扰动、通信
  故障/延迟全部关闭。
- 50/60-Hz 语义：物理端点在 60 Hz；V4 控制器槽位保留 50 Hz 遗产刻度，
  经 `adapt_v4_observations_to_physical`（slot 1..6 乘 60/50）一次转换。

#### 2. 全新 heterogeneous bank（与 R399 六 profile 全部不相交）

| profile | split | baseline M0 | baseline D0 | (Bus14, Bus15) load | probe | localized (loc, mag) |
|---|---|---|---|---|---|---|
| canary_dev_a | development | (150,250,170,230) | (60,140,80,120) | (2.24, 0.42) | 0.85 | PQ_1, 0.95 |
| canary_dev_b | development | (230,150,250,170) | (120,60,140,80) | (2.02, 0.66) | 1.05 | PQ_Bus15, 1.15 |
| canary_dev_c | development | (210,190,160,240) | (130,70,110,90) | (2.42, 0.14) | 0.75 | PQ_0, 0.85 |
| canary_dev_d | development | (240,160,190,210) | (90,110,70,130) | (2.12, 0.54) | 0.95 | PQ_Bus14, 1.05 |
| canary_eval_a | evaluation | (140,260,200,220) | (50,150,90,130) | (2.56, 0.34) | 0.90 | PQ_0, 1.00 |
| canary_eval_b | evaluation | (260,140,220,200) | (150,50,130,90) | (2.06, 0.26) | 0.80 | PQ_Bus14, 0.90 |
| canary_eval_c | evaluation | (180,240,150,210) | (70,130,60,110) | (1.96, 0.64) | 1.00 | PQ_Bus15, 1.10 |
| canary_eval_d | evaluation | (220,200,260,140) | (110,90,150,50) | (2.32, 0.46) | 1.10 | PQ_1, 1.20 |

- 每 profile 六 signed 场景（common/differential/localized × 正/负），构造
  公式与 R399 相同（common 四分到四负荷；differential 对 PQ_0/PQ_1 加、对
  PQ_Bus14/PQ_Bus15 减；localized 全量到注册位置）。bank_seed=401。
- 开发 4 profile 只供训练；评估 4 profile 训练期不可见。

#### 3. 三学习臂 + 强确定性参照

- `yang_scalar_td3`：fresh Yang-compatible 标量奖励 TD3；4 个独立 7 槽 actor，
  集中式联合 critic（36 输入→1 输出，training-only），非 Yang SAC 精确复现。
- `cd_matd3_no_message`：CD-MATD3，运行时 actor 输入为同一 7 槽网络但邻居槽
  3..6 每步由 env adapter 置零；critic 范围与 message 臂逐字相同。
- `cd_matd3_message`：CD-MATD3，运行时 actor 读全 7 槽。
- 确定性参照 `local_neighbour_md_km2_kd2`（R399 开发选择的那条固定律），
  零训练预算，只在全新评估 profile 上执行作参照；其 R399 轨迹/数值不复用。

#### 4. 奖励契约（前瞻数字，全臂同参数）

- scalar TD3：V4 默认标量奖励（`phi_f=100, phi_abs=50, phi_h=0.0056,
  `phi_d=0.0056`，50-Hz 控制器刻度），步奖励为四 agent 之和；TDS 失败步
  奖励 `-200`，episode 终止。
- CD-MATD3 双分量代价（60-Hz 物理刻度）：
  `c_d(t) = sum_k (z_d,k/0.15)^2/3 + sum_k (p_d,k/0.25)^2/3`，
  `z_d = T_d(f-60)`, `p_d = T_d P_es`；
  `c_c(t) = mean_i((f_i-60)/0.15)^2 + mean_i(RoCoF_i/1.0)^2`；
  `r_d = -c_d`, `r_c = -c_c`；TDS 失败步 `c_d = c_c = 50`，episode 终止。
- 拉格朗日乘子：`lambda_0=1.0`，每 episode 后
  `lambda = clip(lambda + 0.05*(sum_t c_c(t) - 3.0), 0, 10)`；actor 最小化
  `-(Q_differential + lambda*Q_common)`。common 预算 `B_c=3.0` 前瞻绝对值。
- 奖励/坐标分永不作 gate 输入：`reward_used_for_gate=False`。

#### 5. 训练、收敛与 checkpoint 契约

- 网络容量：actor MLP `[256,256]` tanh（7→2）；critic MLP `[256,256]` twin
  （36→2，scalar 臂 36→1）；三臂同一 hidden 结构。
- TD3 超参：`lr=3e-4, gamma=0.99, tau=0.005, buffer=200000, batch=256,
  `policy_noise=0.2, noise_clip=0.5, explore_noise=0.1, policy_delay=2`。
- 交互预算：每 seed `1440 episodes × 30 steps = 43200` steps；开发场景顺序
  24 个（4 profile × 3 pair × 2 sign）确定性循环 60 遍，全臂全 seed 相同。
- 收敛规则：固定预算、无 early stop；诊断（episode return、critic loss、
  lambda）只记录不参与选择。非有限 critic loss / 非有限动作 → 该 run invalid
  → 消耗该 seed。
- checkpoint 规则：评估只用 final 权重；每 240 episode 存 snapshot 仅供
  provenance；无 best-of 选择。
- 评估访问：训练期禁止执行评估 profile；九个训练全部完成后才评估。

#### 6. 缺跑规则（先注册，出事后不得改）

- 每 (arm, seed) 重启配额 `1`；仅 host 侧崩溃签名（进程被杀/内存耗尽/WSL
  停机）可重启，重启同 seed 从头训。
- 配额后仍缺 seed → `CANARY-INVALID`（无科学结论，需后继轮）。
- 评估永不重试；缺失/损坏评估 record → `CANARY-INVALID`。

#### 7. 物理/无伤害估计器（与 R399 同公式）

- `z_c = mean(f-60)`；`T_d` 三行 `[1/2,1/2,-1/2,-1/2]`、
  `[1/sqrt2,-1/sqrt2,0,0]`、`[0,0,1/sqrt2,-1/sqrt2]`；奇数响应
  `z_odd=(z_pos-z_neg)/2`。
- off-diagonal 交叉响应能量：common 对下 30×0.2s 的 `mean(z_d,odd^2)` 加
  differential 对下 `z_c,odd^2`，除以注册探测幅值平方；
  disturbance differential 能量：三对 `mean(z_d,odd^2)` 各自归一化求和。
- common 守卫：common 频率绝对积分、worst-unit 峰值、worst RoCoF（含
  初始频率差分）各不差于确定性参照 `103%`；动作 RMS 与总变差不差于 `110%`；
  饱和 `<=5%`；非恒定动作与逐 VSG 独立动作下限 `1e-6`。

#### 8. Canary 判决策树（预注册，不可回看后改）

1. 全 bank 完整有效：3 臂 × 3 seed × 24 评估 record + 24 确定性 record，
   manifest 全部 `interaction_steps=43200`、诊断有效、不缺跑 → 否则 INVALID。
2. 每 (arm, seed) 对确定性参照的 common/动作/饱和/非恒定/独立守卫全过 →
   否则 `CANARY-FAIL`。
3. 全方法（message 臂）对每个学习对照（scalar TD3、no-message CD-MATD3）：
   seed 中位数在两个注册物理端点都严格改善（>0）；
4. 至少 2/3 seed 对每个对照在两端点都改善；
5. 全方法 seed 中位点估计在两端点都优于确定性参照（无 10% 下限要求）；
6. 奖励或坐标分单独不能判 PASS（结构上排除）。
- 全过 → `CANARY-PASS`：仅授权另行封印的 Gate B 五种子 held-out 比较，
  不是 title 证据。全 bank 完整但判据失败 → `CANARY-FAIL`：所选学习器路线
  终止，不得换算法补救。

### Design red-team return

- 泄漏：评估 profile 训练期禁止执行；final-only 评估；开发/评估身份计划内
  冻结。
- 消息归因：no-message 臂与 message 臂网络逐参数同构，仅运行时邻居槽置零；
  两臂 critic 训练范围逐字相同，只差运行时消息。
- 容量匹配：三臂 hidden `[256,256]`、同 optimizer/batch/更新节拍；
  full-vs-scalar 为 bundle 对比，不隔离单一算法因子（身份按 R400 注册）。
- 奖励黑客：分类只读物理 trace 汇总，`reward_used_for_gate=False`。
- 伪重复：seed 是独立学习单元；3-seed 中位数 + seed 级表是描述性有限 bank
  灵敏度，无总体推断。
- 脆弱性决定：无阻塞项；正式执行前仍须 Result/Claim 挑战 canonical feed。

## Gate

- PASS: 契约模块封印（`build_contract` 覆盖 R400 Gate A 要求的全部输入），
  容量证据 `RUN-READY` 且 plan 预算与实测一致，preflight 绿，feed/claim/
  verdict/LINE/ARTIFACTS 一致；只授权后继轮按契约训练三臂×三种子。
- FAIL: 任一 R400 要求输入未冻结、容量 HOLD、plan/证据预算不符、算法替换、
  旧证据复用、本轮训练。
- Self-consistency: R400 Gate A 清单（bank、50/60-Hz、单位、解码器、时序、
  奖励缩放、交互/调参/checkpoint 预算、收敛与缺跑规则、容量、估计器）
  → 本契约 §1-§8 与 machine contract 字段一一映射。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r401_cd_matd3_canary_contract.py measure-capacity`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r401_cd_matd3_canary_contract.py rehearse`
- rehearsal_scope: same-pre-attempt-path；无轨迹、无 formal 输出；source/parent
  哈希、installed package/case、active plan/line、契约闭合、输出缺失。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R401/capacity_evidence.json
- host_process_budget: 5
- wsl_python_processes: 5
- native_threads_per_process: 1
- other_reserved_processes: 0

> 容量梯已实测（rungs 1/2/4，代表性 30 步零动作开发场景任务）：
> 4 worker 全有效、RSS 安全、吞吐增益达标，选择 4 worker →
> host_process_budget=5、wsl_python_processes=5（含 launcher），与候选一致；
> 投影 canary 全工作量约 4.96 小时（仅按 rollout 步成本锚定，不含学习器
> 更新开销）。capacity trace 非 claim-bearing，排除在 evidence 外。

## 资产保护契约

- 保留 dirty worktree；不 reset/clean/stage/commit，不覆盖其他人或其他
  论文线资产。
- 不动 paper-cited 资产（`base_env.py`、`andes_vsg_env_v4.py`、`train.py`、
  `paper_grade_axes.py`）；V4 仅作执行入口被 runner 只读使用。
- R398/R399/R400 全部 plan/feed/claim/verdict/results/hash/分类只读；R399
  六 profile 与轨迹不得作为本轮新证据。
- 只新增：纯契约模块 + 测试、契约 runner + 测试、R401 的 rehearsal/
  capacity/seal 资产、本轮 feed/claim/verdict、LINE/ARTIFACTS 导航更新。

## Cross-references

- CLM-1145 (R400)：同线修订，唯一下一步=三种子 canary 契约轮。
- CLM-1140 (R399)：finite-law 无联合余量；强确定性参照与风险信号来源。
- CLM-1135 (R398)：线注册与标题语义。
- `paper/yang_md_decoupling_marl/working/route_amendment_r400.md`：Gate A/B
  门与停留边界。
- `docs/adr/0019-separate-yang-md-decoupling-marl-successor.md`：线分离决策。

