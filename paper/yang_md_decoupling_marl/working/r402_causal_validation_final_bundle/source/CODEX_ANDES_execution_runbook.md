# R402 后继因果验证：Codex / ANDES 执行手册

## 1. 目标

本手册用于把当前静态审计中发现的实现问题转化为**最小、可配对、可复现的 ANDES 因果实验**。目标不是做算法 sweep，也不是用更多随机种子掩盖机制不可识别，而是依次回答：

1. 历史 R402 结果能否在只增加日志、不改算法的条件下复现；
2. no-message actor masking、stateful slew learner interface、50→60 Hz observation adapter 三项代码问题分别造成了什么影响；
3. 在代码合同有效之后，componentwise effort、multiplier rule、objective alignment、runtime messages 和 direct-M/D authority 各自贡献多大。

当前历史失败已经可复算；本手册生成的是**prospective evidence**，不得覆盖或改写原 R402 历史目录。

## 2. 必须使用的基线

- 仓库：`andes-rl-kundur`
- 审计包所绑定 commit：`9b64e6e4a4f6eb5367a69a037b84bf0c2a08bee5`
- 模拟器：ANDES 2.0.0
- 拓扑：modified Kundur two-area，固定连接
- 控制周期：0.2 s
- 每轨迹：30 steps / 6 s
- 物理频率基准：60 Hz
- 动作：每台 VSG 两维 normalized M/D action，范围 `[-1,1]`
- decoder：负支路斜率 200，正支路斜率 600；`M>=20`、`D>=10`
- normalized slew：每步每分量不超过 0.25
- 注册 checkpoint：final checkpoint；禁止事后选 best checkpoint
- 确定性参考：`local_neighbour_md_km2_kd2`
- 注册 endpoint/guard evaluator：保持 R402 冻结实现

**不要从审计包复制的部分源码目录直接运行。** 该源码子集缺少至少 `andes_rl_kundur.agents.networks` 与 `andes_rl_kundur.scenarios.contract`。应在完整仓库和上述 commit 上执行。

## 3. 分支与目录隔离

建议创建以下分支/工作树：

```bash
git checkout 9b64e6e4a4f6eb5367a69a037b84bf0c2a08bee5
git switch -c r402-causal-validation-v2
```

所有新结果写入独立根目录，例如：

```text
results/research_loop/r402_causal_validation_v2/
```

禁止：

- 修改 `results/research_loop/r402_cd_matd3_canary/` 中任何历史文件；
- 补造历史 `formal_execution.json`；
- 复用已消费 evaluation bank 做调参；
- 根据 held-out 结果调整 effort 权重、训练预算或选择 checkpoint；
- 把 profile、trajectory、time step 当作独立 seed。

## 4. 实验顺序

执行顺序必须是：

```text
E0 → E1 / E2 / E3 单因素配对 → corrected baseline → E4 / E5 / E6 / E7 → E8
```

不得先做 multiplier 或 effort 实验再修复 no-message masking 与 slew interface，否则结果仍混有实现合同问题。

## 5. E0：只增加日志的历史代码复现

### 5.1 唯一允许变化

只加入日志、校验和 schema validation；不改变：

- actor/critic 结构；
- reward/cost；
- multiplier；
- observation；
- action projector；
- optimizer；
- budget；
- profile schedule；
- checkpoint rule。

### 5.2 随机化

至少使用 6 个 fresh paired seeds：

```text
501, 502, 503, 504, 505, 506
```

同一 seed 的各 intervention 必须共享：

- network initialization RNG stream；
- exploration-noise RNG stream；
- replay-sampling RNG stream；
- profile/scenario order；
- simulator randomness；
- disturbance signs and magnitudes。

不要只设置一个全局 seed 后假设随机流仍然对齐；为每种随机源使用命名 RNG stream，并记录初始状态/hash。

### 5.3 必须日志

#### episode 级

每个 episode 保存：

```text
episode_index, interaction_step_start, interaction_step_end,
profile_id, scenario_id, pair_kind, sign,
return_scalar,
C_d_frequency, C_d_power, C_d_total,
C_c_frequency, C_c_rocof, C_c_total,
lambda_pre, lambda_post,
common_iae, worst_peak, worst_rocof,
action_rms, action_tv,
physical_M_lower_clamp_fraction,
physical_D_lower_clamp_fraction,
normalized_boundary_fraction,
tds_failed, terminal_reason
```

#### critic update 级

```text
update_index, episode_index, interaction_step,
q1_mean, q2_mean, target_q_mean,
td_error_q1_mean, td_error_q1_p95,
td_error_q2_mean, td_error_q2_p95,
critic_loss, critic_grad_norm, critic_update_norm,
target_critic_gap,
replay_profile_histogram_hash,
replay_time_index_histogram_hash
```

CD critic必须分别保存 common/differential 两个通道，而不是只保存合并标量。

#### actor update 级

```text
update_index, actor_id, episode_index, interaction_step,
lambda_used,
Q_d_mean, Q_c_mean,
||J_pi^T grad_a Q_d||,
||lambda J_pi^T grad_a Q_c||,
common_to_differential_gradient_ratio,
gradient_cosine,
actor_loss, actor_grad_norm, actor_update_norm,
raw_action_mean/std/p01/p50/p99,
executed_action_mean/std/p01/p50/p99,
pre_slew_post_slew_gap,
message_slot_input_gradient_norm
```

此外，为识别 centralized-critic credit assignment，保存每个 actor 的 one-row replacement Q、joint-action baseline Q、per-agent gradient cosine、其余 actor action 扰动下的 Q sensitivity，以及 sampled joint action 相对 replay support 的距离。没有这些量，不得写“centralized critic solved/caused credit assignment”。

#### transition 级

每一步保存完整时间链：

```text
run_id, episode_index, step_index, profile_id, scenario_id,
raw_observation_7slot,
adapted_observation_7slot,
actor_observation_after_mask,
previous_executed_action,
actor_logits,
raw_tanh_action,
exploration_noise,
pre_slew_target_action,
post_slew_executed_action,
decoder_branch,
delta_M, delta_D,
M_before_clamp, D_before_clamp,
M_after_clamp, D_after_clamp,
physical_clamp_flags,
freq_hz_physical, rocof_hz_per_s, P_es,
step_cost_components,
done, tds_failed
```

数组字段建议保存 Parquet 的 fixed-size list 或 Zarr/HDF5；不要把大数组序列化成不可查询的 Python repr。

#### replay snapshots

至少在 episodes `240, 480, 720, 960, 1200, 1440` 保存：

- 预注册固定数量的均匀 replay sample；
- profile/scenario/time/action 分布；
- observation/action min/max/quantiles；
- evaluation observation 对 replay support 的 kNN/Mahalanobis/OOD 指标；
- sample indices 与 replay insertion IDs。

#### checkpoint evaluation

每个周期 checkpoint 必须在以下对象上 deterministic 评估并分开保存注册 endpoints/guards：历史 development profiles、fresh diagnostic bank、heldout-primary bank、heldout-replication bank。diagnostic/heldout banks 不能用于 checkpoint selection。该四路评估用于区分训练分布上的 fit、development-to-heldout shift 与 checkpoint drift。

### 5.4 E0 通过条件

- 所有 schema 与 hashes 通过；
- final checkpoint rule 未改变；
- held-out 结果方向与历史 R402 一致，即学习臂仍整体落后于确定性参考；同时必须报告 development-profile 结果，不能只验证 held-out 失败；
- 所有 raw→derived 指标可由独立脚本复算；
- 日志本身不改变随机流。需用“logging on/off 同 seed 的前 N 步动作完全相同”测试证明。

## 6. E1：修复 no-message actor masking

应用：

```bash
patch -p1 < reference_fixes/0001_fix_no_message_actor_training_mask.patch
```

### 6.1 唯一变化

no-message arm 的以下 actor forwards 全部将 slots 3–6 清零：

- behavior actor；
- target actor；
- baseline actors；
- 当前更新 actor；
- actor Jacobian/gradient diagnostics。

centralized critic 可以继续接收完整 joint observation。

### 6.2 manipulation checks

必须同时通过：

1. no-message actor forward 的 slots 3–6 恒为 0；
2. 对 no-message actor 输出求 slots 3–6 的输入梯度，范数严格为 0；
3. message arm 相同梯度不被结构性强制为 0；
4. replay 中 full state 与 actor-masked view 分字段保存，避免语义混淆；
5. E1 与 E0 除 mask 外的配置 hash 完全相同。

E1 完成前，不得把 message-minus-no-message 写成通信因果效应。

## 7. E2：修复 stateful slew learner interface

参考实现：`reference_fixes/slew_aware_td3_interface.py`。

### 7.1 唯一变化

- actor state 增加本机上一时刻 post-slew executed M/D action，两维；
- actor 继续输出与历史实现相同的 normalized **target action**，不在 E2 中改成增量命令；
- executable action 使用冻结 projector 的 target-to-executed map：

\[
u_t=\tanh(\ell_t),\qquad
a_t^{exec}=\operatorname{clip}\!\left[
a_{t-1}^{exec}+\operatorname{clip}\left(u_t-a_{t-1}^{exec},-0.25,0.25\right),-1,1
\right];
\]

- behavior、target actor、online actor objective、critic action semantic 与 replay 全部使用同一 map；
- next state 的 previous-action field 等于当前 transition 的 executed action；
- 增量命令参数化只能另设 E2b，不得与最小 E2 合并，否则无法把效果归因于 hidden-slew repair。

### 7.2 manipulation checks

- 所有 behavior/target/online actor action 均满足 bounds 与 slew；
- sampled transition 可由 `previous_executed_action` 与 `normalized_target_action` 通过同一 projector 精确重构 executed action；
- target action 不再查询一步不可达 action；
- actor observation 的 previous-action 字段与 projector state 完全一致；
- `pre_slew_post_slew_gap` 的定义和单位固定；
- E2 与 E0 除 action interface 外配置 hash 相同。

### 7.3 注意

不要简单移除 external projector。那会改变注册物理合同，不是对原问题的单因素修复。

### 7.4 更广义信息状态的后置判别

历史七槽 actor row 还不包含当前/基线 M/D、profile identity 或显式 phase。不要立刻做 observation sweep。先用 E0 的 development-versus-heldout checkpoint evaluation 和 E2 的 previous-action repair判断：

- 若 E2 同时改善 Q calibration、action stress 和 endpoints，则先停止扩展 observation；
- 若 E2 manipulation checks 完全通过但 development profiles 仍失败，可预注册一个单一 state-sufficiency intervention；
- 若 development 通过而 heldout 失败，优先诊断 distribution shift，而不是把问题归咎于优化；
- 强确定性 local-neighbour controller 已经反驳“七槽局部信息使目标物理上不可能”的说法。

单一 state intervention 应一次加入预先选定的最小充分字段，例如 `previous executed action + current M/D`，不得对 time/profile/history 组合做 outcome-driven sweep。

## 8. E3：统一 frequency adapter

应用：

```bash
patch -p1 < reference_fixes/0002_apply_frequency_adapter_consistently.patch
```

### 8.1 唯一变化

所有 learned actor 与 deterministic controller 在消费 observation 前，按冻结 contract 对 frequency/RoCoF slots 做一次且仅一次 50→60 转换。

### 8.2 manipulation checks

- 保存 raw 和 converted slots；
- 对 slots 1–6 验证 converted/raw=`60/50`，其余槽不变；
- 每个 actor path 标记 adapter application count，必须等于 1；
- 禁止 train/eval 路径出现不同 conversion count。

## 9. corrected baseline

分别完成 E1、E2、E3 相对 E0 的单因素配对后，再建立 `E1+E2+E3` corrected baseline。不得直接用三项合并结果反推任一单项效应。

corrected baseline 是 E4–E7 的唯一训练基线。

## 10. E4：componentwise effort 单因素干预

参考实现：`reference_fixes/componentwise_effort_cost.py`。

### 10.1 cost 对象

只使用 post-slew executed normalized action：

\[
J_{effort}=w_m\,\mathbb E\|a_t^{exec}\|_2^2
+w_{tv}\,\mathbb E\|a_t^{exec}-a_{t-1}^{exec}\|_1.
\]

### 10.2 约束

- normalization reference 和权重只在 calibration bank 上冻结；
- 不允许看 held-out endpoint 后调权重；
- multiplier、observation、网络、预算、objective 其余部分不变；
- 保存 magnitude 与 increment 两部分各自的 actor gradient。

### 10.3 因果判定

只有当 manipulation check 显示 effort 梯度实际进入 actor update，并且 paired held-out endpoints/guards 在 primary 与 replication bank 一致改善，才能写“componentwise effort contributed”。只降低 RMS/TV 而 endpoints 不改善，只能说明它解释 action stress，不能解释 endpoint failure。

## 11. E5：multiplier 单因素干预

建议预注册三个规则：

1. 历史 projected `lambda∈[0,10]`；
2. fixed common weight `lambda=1`；
3. projected `lambda∈[1,10]`。

其他所有对象保持 corrected baseline 不变。

必须保存逐 actor update：

\[
r_\theta=
\frac{\|\lambda J_\pi^\top\nabla_aQ_c\|_2}
{\|J_\pi^\top\nabla_aQ_d\|_2+10^{-12}}.
\]

小 lambda 本身不是 common contribution 可忽略的充分证据；必须同时报告 gradient ratio。

## 12. E6：objective alignment 单因素干预

目标是识别 per-trajectory surrogate 与 signed-pair physical endpoint 的错配，而不是直接把不可微 evaluator 塞进 TD3。

最低要求：

- 保存完整 `P_es`；
- 明确 absolute `T_d P_es` 是否惩罚基线异质性；
- 增加 baseline-subtracted power diagnostic；
- 预注册 signed-pair-compatible surrogate 或 paired batch construction；
- 保存 surrogate 与注册 endpoint 在 diagnostic bank 上的 rank correlation/gradient alignment；
- effort、multiplier、slew、message 合同保持 corrected baseline 不变。

## 13. E7：runtime message value

E7 包含两个互补层次：

1. corrected message-on/off paired training；
2. 对 corrected message checkpoints 的 frozen-policy M0–M7 closed-loop interventions。

建议 M0–M7：

```text
M0 true messages
M1 all neighbour slots zero
M2 one-step delay
M3 two-step delay
M4 neighbour identity permutation
M5 within-pair slot swap
M6 matched-variance independent noise
M7 conditional replacement / local-state-matched message resampling
```

每个 intervention 使用相同 disturbance realization。保存 actor-only action contrast 与 closed-loop physical contrast。M0–M7 只能描述已训练 policy 的 value/sensitivity；它不能替代 corrected paired training。

## 14. E8：R402-specific DAE/LTV authority

这是非训练 prospective calculation。对每个 development/evaluation/fresh profile 的相关 operating point 导出：

\[
f_x,f_y,g_x,g_y,f_u,g_u,f_w,g_w,
\]

并计算：

\[
A_r=f_x-f_yg_y^{-1}g_x,
\qquad
B_{u,r}=f_u-f_yg_y^{-1}g_u.
\]

同时输出：

- `cond(g_y)` 与求解残差；
- direct-M、direct-D 的 one-sided decoder Jacobian；
- active slew/clamp set；
- 30-step LTV lifted map；
- common/differential projected singular values；
- authority/controllability Gramian；
- constrained reachable set；
- 从确定性 reference 邻域出发的 local headroom；
- finite-difference checks。

R405 matrices 不得替代 R402-specific export。

## 15. 新 bank 规则

至少建立：

- calibration bank：只做 normalization/penalty scale；
- training bank：fresh；
- diagnostic bank：fresh，不用于选 checkpoint；
- heldout-primary bank：fresh、one-use；
- heldout-replication bank：fresh、one-use。

每个 bank 保存 profile generator seed、完整 profile parameters、disturbance manifest 和 SHA-256。任何已消费 bank 不得转回 tuning。

## 16. 输出目录合同

```text
r402_causal_validation_v2/
├── contract/
│   ├── frozen_config.yaml
│   ├── intervention_manifest.yaml
│   ├── bank_manifest.json
│   └── seed_manifest.json
├── environment/
│   ├── git_commit.txt
│   ├── git_status.txt
│   ├── andes_version.json
│   ├── pip_freeze.txt
│   └── system_info.json
├── runs/<experiment>/<arm>/seed<seed>/
│   ├── started.json
│   ├── manifest.json
│   ├── episode_log.parquet
│   ├── actor_update_log.parquet
│   ├── critic_update_log.parquet
│   ├── transition_log.zarr/
│   ├── replay_snapshots/
│   ├── checkpoint_eval.parquet
│   ├── q_calibration.parquet
│   ├── checkpoints/
│   └── final.pt
├── evaluations/<bank>/<experiment>/<arm>/seed<seed>/
│   ├── raw_trajectories.zarr/
│   ├── registered_metrics.json
│   └── diagnostics.parquet
├── dae_authority/
├── qa/
├── formal_analysis.json
├── formal_execution.json
├── manifest.json
└── SHA256SUMS
```

## 17. QA 与自动失败条件

任一条件触发即将 run 标为 invalid，不得悄悄重启后覆盖：

- nonfinite observation/action/Q/loss/gradient；
- missing trajectory or wrong 30-step length；
- decoder identity、bounds、slew、adapter-count 不通过；
- actor mask manipulation check 不通过；
- replay action semantic 与 critic/target semantic 不一致；
- RNG stream hash 在 paired conditions 中意外漂移；
- held-out bank 在训练完成前被读取；
- final checkpoint hash 与 evaluation manifest 不匹配；
- 输出文件未进入 manifest/SHA256SUMS。

失败 run 必须隔离为不可变 crash directory，并保留 stdout/stderr、exception、最后 RNG states。

## 18. 因果报告规则

以 paired training seed 为统计单位。至少报告：

- 每 seed 的 paired difference；
- paired median；
- exact sign test；
- paired bootstrap interval；
- primary 与 replication bank 分开；
- manipulation checks；
- guard pass/fail，不允许 reward 覆盖 physical failure。

一个机制只有同时满足以下条件才能写成 verified contribution：

1. 机制 manipulation check 通过；
2. paired physical effect 方向稳定；
3. heldout-primary 与 heldout-replication 一致；
4. 严重替代解释不能同样解释结果；
5. 没有 outcome-dependent tuning。

## 19. 交付给本审计的最小文件

完成 E0–E3 后，先发送一个阶段包，不必等待 E4–E8：

```text
contract/
environment/
E0-E3 run manifests
full episode/update/transition logs
checkpoint evaluations
raw heldout trajectories
registered metrics
QA reports
source diff/patches
manifest.json
SHA256SUMS
```

压缩前运行：

```bash
find r402_causal_validation_v2 -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
python -m pytest -q
python tools/validate_r402_causal_package.py r402_causal_validation_v2
```

阶段包命名建议：

```text
r402_causal_validation_v2_E0_E3.zip
```

完成 E4–E8 后另建不可变最终包，禁止覆盖阶段包。

## 20. Codex 最终任务指令

> 在完整 `andes-rl-kundur` 仓库 commit `9b64e6e4a4f6eb5367a69a037b84bf0c2a08bee5` 上执行 R402 causal-validation v2。严格按 E0→E1/E2/E3→corrected baseline→E4/E5/E6/E7→E8 顺序；先以 logging-only E0 建立可复现 baseline，再做单因素配对干预。不得修改历史 R402 目录，不得复用 consumed evaluation bank 调参，不得算法 sweep，不得 best-checkpoint substitution。采用至少 6 个 fresh paired seeds、命名 RNG streams、fresh calibration/training/diagnostic/heldout-primary/heldout-replication banks。保存本文规定的 episode、actor-update、critic-update、transition、replay、checkpoint-evaluation、Q-calibration、完整 P_es、raw/adapted observation、pre/post-slew action 和 DAE/LTV authority 数据。每个实验必须通过 mask、slew、frequency adapter、hash、schema、leakage 和 checkpoint identity manipulation checks。先交付不可变 E0–E3 阶段包，再执行机制实验。所有结论以 paired seed 为统计单位，physical endpoints/guards 优先于 reward。
