# Codex 总任务书：补齐 U1–U9 的真实性、可追溯性与可复算证据

## 任务目标

在现有 `yang-md-decoupling-marl` 仓库中，生成一套**create-only、哈希封存、可由独立脚本复算**的补证数据包，用来核验 `U1–U9` 解答是否真实绑定到项目对象。不要为了得到预期结论而补值、改阈值、重定义对象、读取 evaluation 后重选方案，或把局部/有限库结果外推成普遍结论。

先阅读：

1. `tmp/yang_md_decoupling_marl/gpt_pro_unresolved_math_delta_20260821.md`
2. `tmp/yang_md_decoupling_marl/c1_youlas_sls_certificate.md`
3. 外部解答包中的 `01_complete_solution.md`
4. `memory/rounds/R451/algorithm_audit.json`
5. `memory/rounds/R458/plan.md`
6. 本请求包的其余 Markdown 文件。

## 不可违反的对象边界

- **Object A**：四个独立 agent 直接调节四台 GENCLS VSG proxy 的 `delta_M_i, delta_D_i`；这是乘法参数执行，不是加性功率注入。
- **Object B**：feasibility-native energy-port actuation 与低阶 ring-edge bandpass controller；执行器、reference、estimator、window 和 bank 与 Object A 不同。
- 每个输出文件都必须包含 `object_id`、`actuator_type`、`profile_bank_id`、`reference_id`、`estimator_id`、`horizon_steps`、`sample_period_seconds` 和单位映射。
- 不得把 Object A 与 Object B 的 endpoint ratio、reference denominator 或 action stress 数值相除/合并为因果比较。
- 模型基准 50 Hz 与物理 endpoint 60 Hz 必须分别记录。

## 仓库治理

1. 不改写 R405–R457 的历史文件。
2. R451 保持 `CANARY-INVALID`，不得修补后沿用其 round 身份。
3. R458 只能按现有冻结 runner/plan 执行；若源码或 seal 漂移，输出 `CANARY-INVALID`，不得修复后重跑同一正式 round。
4. U1–U8 新计算使用仓库治理工具分配 successor round；不要自行覆盖既有 round。
5. 所有正式结果 create-only；每个 JSON/NPZ/Parquet/日志均生成 SHA-256 sidecar，并生成根 `SHA256SUMS`。

## 必须先完成的全局证据 WP0

生成：

- `provenance/reproduction_manifest.json`
- `provenance/git_diff.patch`（若 dirty；否则记录空补丁哈希）
- `provenance/environment.txt`
- `provenance/commands.jsonl`
- `provenance/input_inventory.json`
- `provenance/claim_evidence_map.json`

必须记录：

- git commit、branch、dirty 状态、submodule commit；
- Python、ANDES、NumPy、SciPy、PyTorch、CVXPY/solver、BLAS/LAPACK、OS/kernel、CPU/GPU；
- 每次命令、开始/结束 UTC、退出码、stdout/stderr 路径；
- Python/NumPy/Torch/CUDA RNG 初始状态或种子，以及 deterministic flags；
- 所有读取输入和写出结果的内容哈希；
- 每个论文数值到原始文件、字段和生成脚本的依赖链。

如果无法取得 git 元数据，不要猜；写 `unavailable_reason` 并使用全文件内容哈希作为较弱替代。

## WP1：一次性导出共享模型与协议数据

### 1. Object B 完整模型

在 R447 同一 equilibrium 和输入列构造下，导出并封存：

- 原始 DAE snapshot：`time_constants,f_x,f_y,g_x,g_y,x0,y0`；
- control/disturbance input Jacobians：`f_uc,g_uc,f_w,g_w`；
- frequency output Jacobians/映射：`h_x,h_y,h_uc,h_w`；
- zero-time-constant folding indices、dynamic state names、algebraic names；
- continuous reduced `A_c,B_c,B_w,C_c,D_c,D_w`；
- ZOH pre-step 与项目 post-step sampled realization：`A_d,Bc_d,Bw_d,C_pre,D_pre,C_post,D_post`；
- `T_s=0.2 s`、输入/输出 scale matrices、物理单位、50/60-Hz 区分；
- gauge/neutral-mode basis、删除/保留规则、可检测/可稳定 quotient；
- 所有矩阵的 shape、dtype、Frobenius norm、spectral/condition summaries。

不得只导出频带能量或 spectral radius 标量。

### 2. Controller 与 headroom

分别导出：

- frozen ring bandpass controller 的完整 realization；
- frozen local feasibility-native PI 的完整 realization；
- feedback sign、loop break、采样/更新时序；
- normalized command 到 system-pu power 的 headroom gain、offset、lower/upper limits；
- active mode ID、clamp branch、SOC/voltage/headroom 状态；
- equilibrium 邻域内 mode-invariance 检查。

### 3. Object A 数据

在 R446 同一 equilibrium 导出：

- `f_u,g_u` 的八个 M/D 输入列及其标签/单位；
- reduced `A_r,B_w,C_r,D_w`；
- `M0,D0`、动作到实际 `M,D` 的映射、amplitude/slew limits；
- 所有会影响执行的隐藏状态：previous executed action、headroom/clamp/hysteresis、通信缓存、保护/valid 状态。

### 4. Profile、scenario、window 与 reference 协议

为每个参与计算的 profile 导出：

- profile 参数、topology、grid strength、equilibrium hash；
- signed common/differential/localized probes 的完整时序；
- initial state、disturbance records、scenario IDs；
- horizon、window、quadrature weights、pre-step initial frequency；
- endpoint projector、common/differential basis；
- reference trajectory与正 denominator；
- guard thresholds、聚合公式、boundary-aware TV/RoCoF 定义。

Object B 必须重新计算 Object B 自身的 reference 和 guard denominator；只能复用 R452 的**公式与阈值定义**，不得复用 Object A 的 numerical denominator。

## WP2：U1 certificate-bearing 数据

1. 冻结 class contract：
   - `Q(z)=sum_{h=1}^{10} Q_h z^{-h}`；
   - `Q_h=T_d^T Qhat_h T_d`，`Qhat_h in R^{3×3}`；
   - 共 90 个实变量；
   - `sum_h ||Qhat_h||_F^2 <= 1`；
   - normalization 与 `T_d` 明文封存；
   - `locality_claim=false`，除非另有 LFT locality 验证。
2. 先验证 baseline internal stability 和 gauge 处理，再构造 DCF；若 DCF 不能通过系数级 block Bézout 检查，停止并输出失败证据，不得伪造。只有在预先授权时才转 full output-feedback SLS。
3. 对 90 个基向量生成每个 profile/scenario/window 的 lifted response columns：差模、cross、common IAE/peak/RoCoF、action RMS/TV、headroom。
4. 选定 saturation 路径并封存：
   - 保守全程不饱和 `L∞`；或
   - 固定 active mode；或
   - exhaustive mode SOCP；或
   - MISOCP。
   不得把 `saturation fraction <=5%` 直接写成 SOCP。
5. 解 phase-I，导出**未缩放** primal/dual arrays、cone data、scaling map、solver log、版本与容差。
6. 用独立 checker 重算 Bézout、lift、primal feasibility、dual feasibility、stationarity、gap 和 lower bound。
7. 若得到 witness，只在 witness 及预注册对称系数扰动上运行 nonlinear DAE，保存 active-mode trace 和 linear–nonlinear discrepancy。

合法输出只有：

- `FEASIBLE-WITNESS-IN-QY10`；
- `INFEASIBLE-QY10-WITH-VERIFIED-DUAL-BOUND`；
- `CERTIFICATE-INVALID`；
- `CERTIFICATE-NOT-IDENTIFIABLE`。

## WP3：U3/U4 execution semantics 与 exact guard

### U3

对至少一个完整评估 bank 和一个短 deterministic toy bank，逐步记录：

- `obs_t`；
- `previous_executed_action`；
- `raw_policy_action`；
- amplitude-clipped raw action；
- slew-projected executed action；
- physical M/D 或 power command；
- reward各分量；
- `next_obs`；
- `done/valid/tds_failed`；
- 所有 actuator hidden states 与 active-mode ID；
- replay 实际存储字段；
- target actor raw action、projected target action、critic input、TD target。

若历史 R431 replay buffer 仍存在，按 formal manifest 的哈希读出并量化历史 target mismatch。若不存在，明确写 `historical_bias_not_reconstructible`；可用历史 checkpoint 在新冻结 state bank 上做 retrospective one-step diagnostic，但不得称为精确历史训练偏差。

### U4

从原始轨迹独立重算：

- common-frequency IAE；
- worst-unit peak；
- RoCoF；
- differential/cross energies；
- action RMS；
- boundary-aware action TV；
- saturation fraction；
- completion/valid/TDS failure。

同时导出训练约束的原始 episode cost、discount、normalization、budget、multiplier 和更新轨迹。对一个命名类执行 exact finite-bank max-violation phase-I：优先选择 350 schedule family 或 U1 的凸类。神经策略局部优化失败不得解释为类不可行。

## WP4：U5–U8 数值补证

### U5：total sensitivity

对 `rho in {logM,logD}` 和预注册 `h,h/2,h/4`：

- 每个 `rho±h` 重新解 equilibrium；
- 导出 equilibrium derivative、DAE total derivatives、continuous/sampled `A/B/C/D` derivatives；
- 用 `expm_frechet` 或等价 block exponential 得到 ZOH derivatives；
- 导出 controller/headroom/reference derivative；
- 计算全 Nyquist `G,G_rho` 与 finite-band/finite-window energy derivative；
- 用 centered difference + Richardson 交叉核验；
- 保存 `cond(zI-A)`、`cond(I+PcK)`、equilibrium residual、mode hash。

### U6：fractional delay

- 使用 continuous plant + digital controller + exact ZOH split 构造 `tau=mTs+delta` 的 augmented closed-loop matrix；
- 扫描预注册 delay range，跟踪全部非 gauge eigenvalue branches；
- 导出每个 branch 的 eigenvalue、左右向量、residual、condition、匹配 ID；
- 若有 simple unit-circle crossing，用 bracket + Brent/bisection 定位；
- 另在 nonlinear bank 运行 `tau=0.1 s`，随后只按预注册二分规则增加点；
- 每个点报告 endpoint、guards 和 active-mode hash。

没有结构化 uncertainty set 时只允许报告 nominal local delay margin，禁止写 robust margin。

### U7：mixed tensors 与 amplitude scaling

在 R446 equilibrium：

- 导出 `N_j,E_j,R_j,S_j` 或至少对注册 state/disturbance directions 的可复算 JVP/HVP；
- 使用三组以上同时减半的 `(h,eta)`，每个角点解 algebraic equations并记录 residual/mode；
- 构造 30-step bilinear lift；
- 对 `epsilon,epsilon/2,epsilon/4`（推荐再加 `epsilon/8`）运行 zero-action、zero-bias M/D feedback 和 additive energy-port 小信号 command；
- 保存 `||Delta y_MD||/epsilon`、`/epsilon^2` 和 additive `/epsilon`；
- 导出 additive port lifted map和声明子空间的 singular values。

若 M/D policy 有 equilibrium bias、mode switch 或 DAE singularity，不得使用 `O(epsilon^2)` 结论。

### U8：approximate separation

- 优先直接构造 finite-window input-output cross Toeplitz lift；
- 导出 `P_u,Q_y`，并仅在能由设备名称/对称表示验证时导出 full-state `P_x`；
- 检查 projector idempotence、rank、basis labels；
- 计算 `epsilon_A,epsilon_B,epsilon_C,epsilon_D`；
- 计算 `||H_dc||_2`、实际 cross energy、0–Nyquist resolvent condition；
- 对 swing reduced model导出 `Z_dd,S_c,z_dc,b_c` 与 heterogeneity numerator；
- 比较实际 cross transfer 和上界；
- 做 homogeneous projection + 小 perturbation scaling。

若不存在可信 full-state projector，不要硬算 `[A,P_x]`；保留为 input-output lift 和 swing-reduction 结果。

## WP5：U2 新的 3×3×2 factorial

新建 successor round，不复用 R451 结果。设计：

- actor source `A in {0,P,N}`；
- critic source `C in {0,P,N}`；
- reward `R in {base,base+neighbor_term}`；
- 共 18 cells；所有 cell 输入维数、网络宽度、优化器、update 数、replay 容量、projector、environment bank 相同。

必须：

1. 在创建任何网络前设置所有 RNG；同一 training seed 从同一 `base_state_dict` 克隆 18 个 arms；
2. donor bank 使用独立 seed，训练前冻结；
3. placebo：recipient `i` 的两个槽使用独立 episode `pi(e)` 中的 `i` 与 `i+2` donor，确保两个真实邻居槽均改变；
4. 对每个槽、feature、time 检查 pooled empirical multiset hash与 authentic donor bank相同；
5. 在固定 reward 下比较 access，在固定 access 下比较 reward；
6. 采用 U3 已验证的 executed-action replay semantics；
7. training seed 是顶层独立单位，scenario/trajectory 只在 seed 内聚合；
8. 预注册 primary endpoint、materiality、contrast、CI 和 multiplicity rule；
9. 运行预算 sweep 或至少保存完整 learning curve，用于判断 optimization-unresolved；
10. 训练失败/无效 seed 不得静默替换或删除。

seed 数不得凭经验随意定。先输出 `power_analysis.json`：给定预注册 materiality 和 paired seed variance 假设计算所需样本量；若达不到，只能标为 exploratory。

## WP6：R458 与可选 distributional successor

### 冻结 R458

若 seal/source hashes 全部匹配，严格按已有命令链执行：`capacity -> rehearse -> prepare -> dev shards -> select -> eval shards -> aggregate`。选择完成后先封存 `selection.json` 哈希，再允许 eval phase 读取。最好用文件权限或独立进程目录证明 `select` 无法读取 eval shards。

必须交付：

- capacity/rehearsal/formal seal；
- 全部 dev shard及哈希；
- `selection.json` 和 selection input inventory；
- eval 静态与唯一 winner shards；
- per-profile exact guard；
- `formal_analysis.json`、classification、stdout/stderr、SHA256SUMS。

### 若要 transfer probability

另开 successor，预先声明 profile generator `D`、参数联合分布、topology strata、active-mode admissibility、`m_dev/m_test`、目标概率 `p0`、置信度和样本量。test bank 独立生成、永久冻结、只运行一次。不得把 R458 的固定 4 profiles 改写为随机样本。

## 独立核验要求

至少两套逻辑独立的 checker：

1. 生成脚本之外的纯 NumPy/SciPy checker；
2. 对 U1 的 cone/dual 和关键矩阵可使用高精度或 interval arithmetic 复核。

checker 不得直接调用生成脚本的汇总函数来“验证自己”。原始轨迹到 endpoint 的复算也要使用独立实现。

## 最终交付

生成一个压缩包，根目录至少包含：

- `README.md`
- `provenance/`
- `contracts/`
- `model_exports/`
- `u1_certificate/`
- `u2_factorial/`
- `u3_u4_traces/`
- `u5_u8_math/`
- `r458/`
- `independent_checks/`
- `claim_evidence_map.json`
- `SHA256SUMS`

最终报告按 U1–U9 分别给：状态、使用文件/字段、独立核验结果、支持/反驳分支、允许写入论文的最强句子、仍缺数据。任何未运行或失败项明确标记，不生成看似完整的占位数值。
