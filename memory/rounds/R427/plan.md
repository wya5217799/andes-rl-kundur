---
round: R427
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-18'
closed: '2026-08-18'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R427 plan — 反馈环：critic 目标归一化轮（DR 菜单 P1，单因素，R425 束上叠加）

**Opened**: 2026-08-18
**Driver**: 反馈环（creative 条款）+ owner 研究目的指令 2026-08-17 晚（校准
日志 loop 行：把 RL 调到能与经典控制器竞争 + 两层轮设计 Tier-1 筛查 →
Tier-2 封存）。R425（CLM-1290）实测：符号修正约束首次移动动作压力护栏
（36→12），但 critic 发散持续（Q4/Q1 4.65–6.29 ≥ 3），约束被 10.0 上限截断
（残差 1.1–10.1x）——价值估计层仍是近因。注册回退（校准日志 R424 选轮行 +
R425 feed follow-up）：下一单因素 = DR 菜单 P1 critic 目标归一化（
`working/r423_value_estimation_repair_deep_research_2026-08-17.md`）。
**Parent**: CLM-1290 (R425)；CLM-1285 (R424 符号缺陷)；CLM-1270 (R423)；
CLM-1255 (R421 读数)；DR 菜单 P1 行。
**Concurrency**: 独占轮（无在飞 round，other_reserved_processes: 0）。

## TL;DR

Workload: `evidence`。Training。唯一变化因子 = CD 臂 critic 的差模通道 TD
目标归一化（PopArt 式运行均值/标准差 + 输出校正），叠加在 R425 束上（前驱 =
R425），其余逐字 R425/R419。语义门：plan 写精确公式（下）+ rehearsal 跑
归一化语义探针 + 定向测试钉方向。两层轮：Tier-1 短预算筛查（开发数据，
20% 步数，seed 401，对照 = R425 存储 trace 精确截断，训练确定性 ⇒ 逐字
成立）+ Tier-2 封存正式 9 shards（43,200 步 + 240 评估 + 24 确定性 record）。

精确公式（语义门要求，逐字；状态 mu_d init 0.0、sigma_d init 1.0，
beta = 1e-3，sigma_min = 1e-4，全部冻结）:

```
bootstrap (no-grad):  a_next = _target_actions(next_obs)        # R425 逐字
  q1', q2' = critic_target(next_obs, a_next)                    # (B,2)
  q'_min = min(q1', q2')
  q'_min[:,0] = sigma_d * q'_min[:,0] + mu_d                    # 差模输出校正
  t = r + gamma*(1 - d) * q'_min                                # 原始目标 (B,2)
统计更新 (no-grad, loss 之前):  batch_mean = mean(t[:,0]);  batch_var = var(t[:,0])  # 有偏
  mu_d    <- (1-beta)*mu_d + beta*batch_mean
  sigma_d <- clip(sqrt((1-beta)*sigma_d^2 + beta*batch_var), sigma_min, inf)
归一化损失 (loss 用更新后统计量):  t_d_norm = (t[:,0] - mu_d)/sigma_d;  t_c = t[:,1]
  L = MSE(q1[:,0], t_d_norm) + MSE(q1[:,1], t_c)
    + MSE(q2[:,0], t_d_norm) + MSE(q2[:,1], t_c)                # 共模列不动
原始尺度重建 (读数字用; 恒等):
  L_orig = sigma_d^2*(MSE(q1[:,0],t_d_norm) + MSE(q2[:,0],t_d_norm))
         + MSE(q1[:,1], t_c) + MSE(q2[:,1], t_c)
         = MSE(sigma_d*q1[:,0]+mu_d, t[:,0]) + MSE(q1[:,1],t_c)
         + MSE(sigma_d*q2[:,0]+mu_d, t[:,0]) + MSE(q2[:,1],t_c)
actor 输出校正 (_actor_objective):  q1_actor[:,0] = sigma_d*q1[:,0] + mu_d
  loss = -mean(q1_actor[:,0] + lambda*q1_actor[:,1])
         + mu_RMS*mean(row^2) + mu_TV*mean(|row - prev|)        # R425 signfix 逐字
```

共模列（critic 第二输出、bootstrap 第二列、lambda Lagrange 机制、奖励 seam
R419 逐字无 effort 项）完全不动——预算语义零改动（DR 菜单 P1 预算保持
要求）。scalar 臂 learner/奖励逐字 R419（字节锚）。机制声明：actor 差模
梯度被 sigma_d 线性放大（输出校正固有），属机制一部分，非隐藏改动。

预注册判定（对照 = R425 同束）: 原始尺度 critic Q4/Q1 < 3 = 发散被压制（
读数必须用 L_orig 重建——归一化尺度读数会平凡满足 <3，口径已声明）；仍 ≥3
= 发散持续；任臂全 guard 通过或分类翻转 = 修复确认 → 停 claim gate 问
owner（B1 约定）；动作压力失败块 12 → <12 = P1 叠加后护栏级增益；12 不动
= 约束层独立于价值尺度修复。预算：solo 阶梯（rungs 1/2/4/8/12/16）后封存
（预期 rung 16 / 17 进程，实测为准）；9 shards 单波；串行 evaluate +
classify。

## Snapshot at plan-time (oracle as of 2026-08-18)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Methodology

### Mission boundary

- Outcome: 9 manifest（critic_loss_trace 归一化尺度 + critic_loss_original_trace
  + critic_stats_trace (mu_d/sigma_d) + actor_grad_norm_trace（CD 臂，
  log-only，不耗 RNG）+ mu_RMS/mu_TV/残差/lagrange/slew 诊断）+ 240 评估 +
  24 确定性 record + 冻结参照阈值 JSON + formal_analysis（冻结分类 +
  端点/消息增量/限速诊断 + vs R425/R424/R419 中位对照 + 原始尺度 Q4/Q1
  判决读数 + 归一化尺度辅助读数 + mu_d/sigma_d/actor-grad 轨迹）+ 正常收尾。
- Authority: 反馈环（creative 条款）+ owner 研究目的指令（校准日志 loop
  行）。
- Permitted: 新 learner 模块
  `src/andes_rl_kundur/agents/cd_matd3_critic_norm.py`（独立文件）、runner
  `scripts/run_r427_critic_target_normalization.py` + 测试、results 根
  `results/research_loop/r427_critic_target_normalization/`（create-only）、
  Tier-1 输出 `tmp/andes/r427_tier1/`（开发筛查，非密封）、
  objective_semantics_lint.py 归一化探针扩展（additive，R425 penalty 形态
  不动）、正常收尾。
- Forbidden: 改 cd_matd3.py / cd_matd3_vfix.py / cd_matd3_guard_constraints.py
  / cd_matd3_guard_constraints_vfix.py 字节（R419-R425 seal 依赖）；改
  R419-R426 runner/契约模块；换算法；训练期访问评估剖面；scalar 臂
  learner/奖励改动；动 paper-cited 资产；动 R425 约束参数（step 0.05 /
  max 10 / init 0 / harm factor 1.10）。
- Terminal: formal_analysis.json 存在且 9+40 文件齐全 + 参照阈值 JSON。

### 冻结协议 (frozen-first)

- 修复点：`PopArtDifferentialCriticSlewAwareCDMATD3Signfix`（
  `src/andes_rl_kundur/agents/cd_matd3_critic_norm.py`）——继承
  `GuardConstrainedSlewAwareCDMATD3Signfix`（R425 束约束机制逐字），只覆盖
  `_critic_update`（上记 bootstrap/统计更新/归一化损失/原始尺度重建）、
  `_actor_objective`（上记输出校正）、`update()`（复制 signfix 逐字 +
  诊断 dict 追加 critic_loss_original / mu_d / sigma_d /
  actor_grad_norm_log10，log-only 不耗 RNG）、save/load（payload 追加
  mu_d/sigma_d 键，schema 2 不变，load 默认值向后兼容）。
- 统计更新顺序冻结：bootstrap → 统计更新 → 归一化损失（loss 用更新后
  统计量；重建恒等逐字成立）。
- 归一化只落差模列；共模列 MSE/bootstrap/lambda/奖励 seam/Lagrange 预算
  机制全部 R425 逐字；scalar 臂 learner 逐字（字节锚）。
- 锚：scalar 臂 3 组 checkpoint sha256 == R419 同臂同种子（
  SCALAR-BIT-IDENTICAL；不匹配 = invalid_reason）；CD 臂无字节锚（单因素
  隔离经 scalar 锚 + 同束对照 + 环境同一性）。确定性参照评估逐字不变。
- 参照阈值：`reference_action_stats.json` 在 prepare 时实测（R425 同款
  流程）、hashed 冻结。
- 读数：原始尺度 Q4/Q1（判决用，冻结公式 = R425 同款 quartile 规则）+ 归一化
  尺度 Q4/Q1（辅助机制读数）+ mu_d/sigma_d 轨迹 + actor log-grad-norm（每
  policy update，log10(4 actor L2 梯度范数均值)，CD 臂）+ mu_RMS/mu_TV/
  残差 + slew 诊断。
- Tier-1 筛查（开发数据，pre-seal，不 gate Tier-2）: 3 runs（3 臂 × seed
  401 × 8,640 步 = 288 episodes = 20% 预算），输出 tmp/andes/r427_tier1/；
  对照 = R425 存储 critic_loss_trace.json 截断到 Tier-1 trace 同长度（训练
  确定性 ⇒ 逐字精确），同公式算原始尺度 Q4/Q1。判决用途：机制检查（轨迹
  有限、统计量有限、checkpoint 可载）+ 早期警示读数；正式判决以 43,200 步
  Tier-2 为准。机械缺陷（NaN/崩溃）pre-seal 修复后重跑；seal 后失败只能
  abort（规则）。Tier-1 dev 预算 = 4 进程（3 workers + driver），容量依据
  = R425/R426 同机阶梯证据（rung 16 安全）；正式阶梯在 Tier-1 后重测，只
  封存正式预算。
- 语义门：rehearsal_checks 含 `normalization_semantics_probe`；rehearsal 在
  真实 learner 上跑归一化语义探针并把数值写进 rehearsal JSON；定向测试钉
  同一方向；收尾前跑 objective_semantics_lint.py R427。探针四项：
  output_correction_identity（|L_orig − 重建恒等式| < 1e-9 相对）、
  common_target_untouched（共模目标列与基座逐字一致）、
  differential_gradient_positive_rescale（P1 loss 与基座 loss 在相同 batch/
  相同权重下的 critic 梯度内积 > 0——无符号翻转，R424 教训泛化）、
  stats_convergence（合成常量 batch 下 EMA 收敛到该常量 std，相对误差
  < 1%）。
- 其余 = R425 逐字（9 槽增广、掩码、种子 401/402/403、43,200 步/组、同
  超参/估计器/guard/checkpoint 流程、约束机制参数）。

## Gate

- 分类树 = 冻结 classify_canary（同 R419-R425）。
- Outcomes (pre-registered): 任臂全 guard 通过或分类翻转 = 修复确认 → 停
  claim gate 问 owner（B1 约定）；仍 CANARY-FAIL = 报告 + 端点/guard 分布
  对 R425 及 R419 对照 + 原始尺度 critic Q4/Q1 读数（预注册判据：<3 = 发散
  压制；≥3 = 持续，对照 R425 同束 4.65–6.29）+ mu_d/sigma_d/actor-grad
  轨迹解读 + 动作压力失败块读数（12 → <12 = 护栏级增益；12 不动 = 约束层
  独立）；CANARY-INVALID = 调查。
- 锚：scalar 臂 3 组 checkpoint sha256 == R419 同臂同种子（任何不匹配 =
  DRIFT）；确定性参照评估逐字不变。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r427_critic_target_normalization.py --shards tmp/andes/r427_train_shards.json --workers <ladder> --round R427` (9 train shards) + `... run_r427_critic_target_normalization.py evaluate` + `... classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r427_critic_target_normalization.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + snapshot + 每臂 1 步真实增广 rollout + replay store（填满 batch）+ learner update 演练（CD 臂归一化 critic 路径 + 输出校正 actor 路径 + guard 乘子 seam）+ save/load roundtrip（mu_d/sigma_d + mu_RMS/mu_TV 保留）+ **归一化语义探针（语义门，留痕进 rehearsal JSON）** + R419 奖励路径。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence, normalization_semantics_probe
- capacity_evidence: memory/rounds/R427/capacity_evidence.json
- host_process_budget: 17
- wsl_python_processes: 17
- native_threads_per_process: 1
- other_reserved_processes: 0

（预算数字为预期，以 solo 阶梯实测为准；seal 前把实测回填 plan。）

## 资产保护契约

- R419-R426 资产只读（对照与锚只读引用）；cd_matd3.py / cd_matd3_vfix.py /
  cd_matd3_guard_constraints.py / cd_matd3_guard_constraints_vfix.py 字节
  不动（P1 子类在独立模块）；paper-cited 资产只读；dirty worktree 保留。
- 新文件仅: P1 learner 模块 + tests、run_r427 runner + tests、R427 results
  根（create-only）、Tier-1 tmp 输出、lint 工具 additive 扩展、
  ledger/feed/手稿收尾文件。

## Cross-references

- CLM-1290 (R425)；CLM-1285 (R424 符号缺陷)；CLM-1270 (R423)；CLM-1255
  (R421 读数)。
- `working/r423_value_estimation_repair_deep_research_2026-08-17.md`（P1 行 +
  验证引文 PopArt Hessel 2019 / RBS Schaul 2021 / TD7 Fujimoto 2023）。
- `working/soft_spot_experiment_program.md`（mission 契约 + 两层轮设计 +
  saturate-or-skip）。
- `working/gate_calibration_log.md`（R424 选轮行 + owner 两层指令/研究目的
  行）。
- `skills/kundur-round/SKILL.md` §2 语义门。
