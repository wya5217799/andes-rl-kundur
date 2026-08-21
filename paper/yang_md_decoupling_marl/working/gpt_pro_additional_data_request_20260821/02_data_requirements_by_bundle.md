# 按共享工作包整理的数据需求

## WP0 — Provenance 与可复现根证据

### 必须数据

| 文件 | 必须字段 | 用途 |
|---|---|---|
| `reproduction_manifest.json` | commit、dirty、submodules、host、package versions、BLAS、RNG、determinism | 证明结果来自哪套代码和运行时 |
| `input_inventory.json` | path、sha256、size、role、producer round | 证明没有偷换输入 |
| `commands.jsonl` | command、cwd、env diff、start/end UTC、exit code、stdout/stderr | 完整执行链 |
| `git_diff.patch` | dirty patch 或空补丁 | 允许第三方恢复实际源码 |
| `claim_evidence_map.json` | claim ID → derived field → raw artifact → script | 每个数值的字段级来源 |
| `SHA256SUMS` | 全部正式文件 | 内容完整性 |

### 真实性门槛

- 只记录 seed 数字不够；还应记录 seeding 发生在网络/环境构造前还是后。
- 只保存 summary 不够；至少关键命题应保留 raw matrix/trajectory。
- 结果文件与 sidecar 的时间戳不能作为唯一证据，内容哈希和输入依赖才是核心。
- 任何重跑必须生成新的 run ID；不得覆盖旧结果后继续沿用旧哈希。

---

## WP1 — 模型、单位、对象与协议主数据

### A. Object B 模型核心

| 数据 | 最小版本 | 完整版本 |
|---|---|---|
| DAE Jacobians | `f_x,f_y,g_x,g_y` + equilibrium | 加 `f_uc,g_uc,f_w,g_w`、输出 Jacobians、state/algebraic names |
| 连续 reduced model | `A_c,B_c,B_w,C,D` | 加 reduction residual、rcond、gauge basis、descriptor blocks |
| sampled model | `A_d,Bc_d,Bw_d,C_post,D_post,T_s` | 同时导出 pre-step output 与 ZOH block exponential核验 |
| units/scales | control/output scale matrices | 每个 channel label、system pu base、Hz base、normalization transform |
| controller | `K(z)` 可复现 realization | 两种 controller 全部 state-space、update timing、feedback sign |
| headroom | equilibrium gain/limits | 每 profile active mode、tube invariance、one-sided derivatives |

### B. Object A 模型核心

- 八个 `delta_M/delta_D` 的 input labels、单位与 runtime 映射；
- equilibrium、DAE Jacobians、扰动列与输出映射；
- amplitude、slew、clamp、previous executed action；
- M/D action 是否零偏置；
- hidden execution state 与 mode transitions。

### C. Profile/protocol

每个 profile 必须绑定：

```text
object_id
profile_id
profile_bank_id
topology_hash
equilibrium_hash
scenario_ids
probe/distance waveform hashes
initial-condition hash
sample_period_seconds
horizon_steps
metric_window
quadrature
reference_id
reference trajectory hash
guard thresholds and units
```

### 共同使用关系

- U1：plant、controller、headroom、profiles、reference、lift；
- U5：所有参数依赖与 derivative；
- U6：continuous/ZOH split 与完整 closed loop；
- U7：Object A tensors 与 additive port map；
- U8：reduced A/B/C/D、I/O projectors、conditioning。

---

## WP2 — U1 证书数据

### 必须数据对象

1. `class_contract.json`
   - `H=10`；strictly causal；90 variables；differential basis；coefficient norm；normalization；是否 locality。
2. `dcf_factors.npz` 或 full output-feedback SLS arrays
   - 所有左右 coprime factors；state-space/polynomial convention；feedback sign。
3. `bezout_check.json`
   - 每个 coefficient residual、relative norm、conditioning。
4. `lift_index.json` + `lift_arrays.npz`
   - 每个 row 对应 profile/scenario/sample/output/guard；每个 column 对应 `(tap,row,col)`。
5. `phase1_conic_problem.npz`
   - affine equalities、linear inequalities、SOC blocks、scaling、variable ordering。
6. `primal_solution.npz`、`dual_solution.npz`
   - 原始尺度变量；solver-scaled 变量另存。
7. `certificate_check.json`
   - primal/dual residual、stationarity、gap、lower bound、安全折扣、高精度结果。
8. `nonlinear_transfer_validation/`
   - witness执行轨迹、active modes、linear/nonlinear endpoint、perturbations。

### saturation 必须单独声明

| 路径 | 允许结论 | 代价/限制 |
|---|---|---|
| `||u||∞ < limit` | 0 saturation 的保守证书 | 可能过于保守 |
| fixed active mode | 该 mode 内 SOCP | 必须证明整个候选 tube 不切 mode |
| exhaustive modes | piecewise-affine 全覆盖 | mode 数可能大 |
| MISOCP | 精确编码最多 5% 样本饱和 | 需要整数证书/全局 gap |

---

## WP3 — U3/U4 原始轨迹与训练/守卫数据

### 逐步轨迹最小字段

```text
run_id, object_id, profile_id, scenario_id, seed, step, time_s
obs_t
prev_executed_action
raw_action
amplitude_clipped_action
executed_action
physical_command
reward_total + reward_components
next_obs
actuator_hidden_state_before/after
active_mode_id
completed, valid, tds_failed, done
```

### Bellman audit额外字段

```text
replay_obs, replay_prev_action, replay_action, replay_reward, replay_next_obs, replay_done
target_raw_action, target_executed_action
critic_current_input, critic_target_input
td_target, q_current, bellman_residual
```

### U4 guard raw evidence

- 物理频率全轨迹与 pre-step initial frequency；
- 每台设备动作全轨迹；
- static/reference 对应轨迹；
- 每个 metric 的逐样本 contribution；
- 最终 profile aggregate 与 exact boolean guard；
- invalid/failed trajectory 清单，不得只保留成功样本。

### 训练约束 raw evidence

- reward/cost公式和版本哈希；
- episode common cost、discount、normalization denominator；
- budget、dual multiplier、projection、每次 multiplier update；
- batch IDs、checkpoint IDs；
- 若复核 R456：保存 objective/constraint gradient vectors、parameter ordering、cosine、step 后真实 guard change。

---

## WP4 — U5–U8 数学数值数据

### U5

- `rho_grid.json`：`rho0,±h,±h/2,±h/4`；
- 每点 equilibrium、residual、mode hash；
- continuous and sampled matrices；
- total derivative arrays；
- controller/headroom/reference derivatives；
- full-frequency `Pc,Pw,K,L,S,G,G_rho`；
- energy integrands、quadrature、ratio derivative；
- Richardson table、condition numbers、direct-FD discrepancy。

### U6

- continuous plant/controller realization；
- delay augmentation specification；
- `B0(delta),B1(delta)` arrays；
- per-delay augmented matrix hash；
- full pole branches、eigenvectors、residuals、condition numbers；
- crossing brackets；
- nonlinear fractional-delay trajectories和active mode。

### U7

- `N_j,E_j,R_j,S_j` 或完整方向导数索引；
- 每个 finite-difference corner 的 DAE residual；
- step convergence/Richardson；
- 30-step bilinear lifted operator；
- amplitude sweep raw trajectories；
- log-log slope与normalized ratios；
- additive port lift与 singular values；
- actuation normalization contract。

### U8

- I/O common/differential bases；
- full-state projector（若可验证）；
- `epsilon_A/B/C/D`；
- exact finite-window cross Toeplitz lift；
- actual cross gain/energy；
- resolvent/Schur conditioning；
- `Z_dd,S_c,z_dc,b_c`；
- homogeneous/perturbation scaling data；
- bound slack `bound - actual`。

---

## WP5 — U2 因果 factorial 数据

### 设计与冻结

- 18 cell 的 canonical config 和 hash；
- base initialization state dict hash per seed；
- donor bank hash；
- placebo permutation/hash audit；
- reward hash per `R` level；
- environment/eval bank hash；
- update budget和checkpoint schedule。

### 原始训练数据

- 每 seed/cell 的完整 learning curve；
- replay semantics audit；
- loss、entropy/alpha、dual、action stats；
- checkpoint和 optimizer state；
- failure/NaN/early stop；
- held-out bank的 profile-level endpoints和guards。

### 推断数据

- seed 内聚合 cell outcome；
- paired contrasts；
- seed-cluster/bootstrap或exact sign-flip结果；
- primary/secondary endpoint；
- materiality threshold；
- multiplicity处理；
- budget sweep；
- `optimization_status ∈ {converged-enough, budget-sensitive, unresolved}`。

### 不可由该实验产生的数据

- 神经 policy class 的 exact global optimum；
- 任意 architecture/topology 的消息价值；
- deployment distribution 上的价值。

---

## WP6 — R458 / distributional transfer

### R458 必须保留

- frozen candidate sequence hash；
- dev static + 350 candidate rows per dev profile；
- selection input inventory；
- `selection.json`；
- selection完成时间和hash；
- eval static + same winner only；
- per-profile raw/summary/guard；
- transfer count与branch；
- no-reselection audit。

### 量化概率的额外数据

- profile generator code与distribution spec；
- independent dev/test RNG states；
- strata；
- sample size calculation；
- all generated profile manifests，包括失败 profile；
- one-shot test results；
- exact binomial/stratified interval。
