---
round: R428
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-18'
closed: '2026-08-18'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R428 plan — C1-SAC：Yang-2022 TPWRS MADRL-SAC 精确复现（matched bundle，owner 开门）

**Opened**: 2026-08-18
**Driver**: soft-spot program override deck item C1-SAC（trigger: explicit owner
order——owner 2026-08-18 "cpu空余，可以加项目" 选择本项 = 开门）。Why（program
原文）: 手稿定位对照 [1] (Yang et al., TPWRS 2022, MADRL-SAC,
DOI 10.1109/TPWRS.2022.3221439)；精确复现把"engineering baseline"caveat 变成
直接对比。这是定向单实验，不是算法扫荡。接口事实真源 =
`docs/paper/kd_4agent_paper_facts.md`（仓库权威论文事实文档）。
**Parent**: soft_spot_experiment_program.md C1-SAC 项；CLM-0045/0048/0059
(R41/R43/R51 历史 SAC 证据：SAC 在本环境结构性劣势已三证——本轮的精确接口
复现是对照性验证，不是推翻该证据的尝试)；route_owner_decision_soft_spot
_program_2026-08-16.md。
**Concurrency**: 与 R427 收尾并发（R427 正式训练已完成、仅 evaluate/classify/
close-out 在飞）。本 plan 在 R427 关闭前写定；容量阶梯时机按当时在飞状态选
分支：R427 已关闭 → solo 阶梯（other_reserved_processes: 0）；R427 仍在飞 →
concurrent 阶梯 + 声明 R427 sealed 预算（17 进程 / 17×900MB floor，R426 先例）。

## TL;DR

Workload: `evidence`。Training。本轮 = 在 matched bundle（同 profiles/种子
401-403/预算 43,200 步/guard/估计器）上把 [1] 的 SAC 接口**逐字复现**：
每 agent 独立 actor π（高斯+tanh）、单 critic Q（论文 Alg.1 line 4 单数）、
V 目标网络（Eq.21）、auto-α（Eq.23）、4×128 全连接、lr 3e-4、γ 0.99、
batch 256、buffer 10000/agent、无梯度裁剪；奖励 Eq.14-18（φ=[100,1,1]）在
runner 从 **obs 行**逐字重建（§2.4.5 奖励必须与观测一致；无 φ_abs 项）。
三臂：yang_scalar_td3（R419 逐字字节锚）+ sac_no_message（邻居槽真零 + η=0
诚实零约定 → r^f≡0）+ sac_message（全 η=1）。精确公式（语义门要求，逐字）:

```
obs 行 (Eq.11, 7 槽): o=[ΔP_es/2, Δω_rad/3, Δω̇_rad·2π·FN/5, 邻居1..2 Δω_rad/3, 邻居1..2 Δω̇_rad/5]
重建 (Hz):  Δω_i = o[1]·3/(2π);  Δω^c_j = o[3+k]·3/(2π);  η_j = 1(消息臂)/0(无消息臂)
Eq.16: Δω̄_i = (Δω_i + Σ_j η_j·Δω^c_j) / (1 + Σ_j η_j)
Eq.15: r^f_i = −(Δω_i − Δω̄_i)² − Σ_j η_j·(Δω^c_j − Δω̄_i)²
Eq.17: r^h_i = −(mean_{all i} ΔM_i / 2)²        (mechanical-H 解读 + 全局网格运营商均值, 调和 Q-B)
Eq.18: r^d_i = −(mean_{all i} ΔD_i)²
Eq.14: r_i = 100·r^f_i + 1·r^h_i + 1·r^d_i      (KD 值 Sec.IV-B; 无 r_abs 项)
critic (Eq.21):  J_Q = ½·MSE( Q(s,a), r + γ·(1−d)·V̄(s') )         (单 critic, V̄=软更新目标)
actor (Eq.22):   J_π = mean( α·log π(a|s) − Q(s,a) )              (α.detach)
alpha (Eq.23):   J(α) = mean( −α·log π − α·H̄ ),  H̄ = −2 (声明; α∈[0.005,5.0])
V loss (声明调和, 源 [48] Haarnoja 2018):  J_V = ½·MSE( V(s), E_{a~π}[Q(s,a) − log π(a|s)] )
软更新: θ̄ ← (1−τ)·θ̄ + τ·θ, τ = 5e-3 (声明, 源 [48])
```

声明调和（论文内部矛盾/未指定，逐一列出）: 12.A buffer clear 矛盾 → 不 clear，
标准 replay；每 episode 梯度步数未给 → 每 env 步 1 次梯度步（每 agent）；
τ 未给 → 5e-3（[48]）；α 范围未给 → [0.005,5.0]；Ḧ 未给 → −2；V loss 未给 →
[48] 形式；Q-B ΔH_avg 范围未给 → 全局（网格运营商）；动作无 slew 投影（论文
无此物；CD 臂的 B1 slew 投影不进本接口）；TDS 失败无合成 50 惩罚（论文无此
项）→ 终止 episode 并记 any_tds_failure。预算/护栏/评估 = matched bundle
逐字（43,200 步/组、240 评估 + 24 确定性 record、冻结分类器、8 profile
契约）。

预注册判定（pause branch = B1 同款）: 任臂全 guard 通过或分类翻转 = 复现
确认 → 停 claim gate 问 owner；仍 CANARY-FAIL = 报告 + 端点/guard 分布对
scalar 对照与 R410/R425 CD 家族对照 + SAC 训练诊断（per-agent critic loss
轨迹、alpha 轨迹、log π 熵轨迹、log-only）+ 消息增量；CANARY-INVALID =
调查。R18 风险预注册：paper-strict-pure 奖励（φ=[100,1,1] 无 abs）历史上在
V4 发散（ADR-0002/R18）——若 SAC 臂发散/全无效，如实报告为"精确接口在本
物理环境复现失败"，不作调参修复（修复 = 新轮）。

## Methodology

### Mission boundary

- Outcome: 9 manifest（SAC 臂: per-agent critic/actor/alpha loss 轨迹、
  alpha 轨迹、熵 log π 轨迹、buffer 覆盖诊断，log-only）+ 240 评估 + 24
  确定性 record + formal_analysis（冻结分类 + 端点/消息增量 + vs scalar/
  R410/R425 中位对照 + SAC 诊断读数）+ 正常收尾。
- Authority: owner order 2026-08-18（C1-SAC 开门）+ soft-spot program
  C1-SAC 项 + creative 条款。
- Permitted: 新 learner 模块
  `src/andes_rl_kundur/agents/yang_sac_exact.py`（独立文件，论文接口逐字）、
  runner `scripts/run_r428_c1_sac.py` + 测试、results 根
  `results/research_loop/r428_c1_sac/`（create-only）、Tier-1 输出
  `tmp/andes/r428_tier1/`、正常收尾。
- Forbidden: 改 sac.py/sac_base.py/sac_ctde.py 字节（历史 R41-51 依赖）；
  改 cd_matd3.py 家族字节；改 paper-cited 资产（base_env/v4_config/
  andes_vsg_env_v4）；改契约/估计器；训练期访问评估剖面；SAC 臂做任何非
  论文调参（lr/网络/裁剪/双 critic/9 槽增广/B1 投影一律禁止）。
- Terminal: formal_analysis.json 存在且 9+40 文件齐全。

### 冻结协议 (frozen-first)

- 臂: `sac_message`（obs 邻居槽真实值，η=1，r^f 完整）+
  `sac_no_message`（obs 槽 3-6 真零，η=0，r^f≡0，Eq.14 只剩 r^h/r^d）+
  `yang_scalar_td3`（R419 逐字，字节锚 SCALAR-BIT-IDENTICAL）。
- learner: `YangExactSACAgent`（每 agent 一个实例，4 个独立实例组成臂）:
  actor Gaussian(tanh) 4×128、单 critic Q 4×128 (obs 7 + act 2 → 1)、V 网络
  4×128 (obs 7 → 1) + V 目标网络；优化器 Adam lr 3e-4 ×3（actor/critic/α）；
  无梯度裁剪；replay 每 agent 独立 capacity 10000；上记精确损失逐字。
- 训练 seam: 每 env 步——4 agent 各 store (o_i, a_i, r_i, o'_i)；buffer ≥
  256 后每 agent 1 次梯度步（顺序声明：critic→actor→α→V→软更新）。
  探索 = 训练时从 π 采样（reparameterized）；评估 = 均值 tanh(μ)
  （deterministic）。
- 奖励: runner 从 obs 行 + info delta_M/delta_D 按上记公式重建，不读 env 的
  PHI 奖励（env 只供 obs/转移）；r_i ≤ 0 恒成立（语义探针钉）。
- 锚: scalar 臂 3 组 checkpoint sha256 == R419 同臂同种子（不匹配 = DRIFT）；
  确定性参照评估逐字不变。
- 诊断 (log-only 不耗 RNG): 每 agent 每 update 的 critic_loss/actor_loss/
  alpha_loss/alpha/log π 均值 → `sac_diagnostics_trace.json`；SAC 臂 manifest
  记录 per-agent 最终 alpha + 轨迹 hash。
- Tier-1 筛查（开发数据, pre-seal, 不 gate Tier-2）: 3 臂 × seed 401 ×
  8,640 步，输出 tmp/andes/r428_tier1/；机制检查（轨迹有限、alpha 有限、
  checkpoint 可载、r_i ≤ 0）+ 早期读数（SAC critic loss 尺度 vs CD 家族）。
  机械缺陷 pre-seal 修复重跑；seal 后失败 abort。
- 语义门: plan 写精确公式（上）+ rehearsal 跑 `sac_semantics_probe` 留痕 +
  定向测试钉方向；收尾前 objective_semantics_lint.py R428（lint 工具需
  再 additive 扩展 SAC 探针形态）。探针四项: critic_target_identity
  （y == r + γ(1−d)V̄(s′)，与 Eq.21 逐字）、actor_loss_form（J_π = α log π − Q
  的梯度 = ∇Q − α∇log π，符号钉）、alpha_loss_form（Eq.23 逐字）、
  reward_nonpositive_and_obs_consistent（Eq.14-18 重建值 ≤ 0 且与 obs 行
  一致）。
- 其余 = matched bundle 逐字（8 profile、种子 401-403、43,200 步、同估计
  器/guard/checkpoint 流程、冻结分类器）。

## Gate

- 分类树 = 冻结 classify_canary（同 R419-R427）。claim 的对比指标 =
  canary 端点（off_diagonal_response_energy / disturbance_differential_energy）
  + guard 分布 + 消息增量，非 R41 时代 paper-grade 轴（geo/cum_rf ranker）。
  CLM-0430 双指标政策适用于 paper-grade ranker 的奖励消融轮；本轮是
  matched-bundle 的 SAC 接口对照，不 claim 该 ranker 下的 geo/cum_rf 消融，
  故 claim 只挂 canary 端点（preflight 的 reward-ablation WARN 已据此审阅）。

- 分类树 = 冻结 classify_canary（同 R419-R427）。
- Outcomes (pre-registered): 任臂全 guard 通过或分类翻转 = 复现确认 → 停
  claim gate 问 owner（B1 约定）；仍 CANARY-FAIL = 报告 + 端点/guard 分布对
  scalar 对照与 R410/R425 CD 家族 + SAC 诊断读数（预注册判据：SAC 臂 critic
  loss 是否收敛/Q4-Q1 趋势、alpha 是否漂到上限、消息增量符号）+ 如实记录
  "exact interface on our physics"结果；R18 发散预注册：纸奖励发散/全无效
  → 如实报告，不调参。CANARY-INVALID = 调查。
- 锚: scalar 臂 3 组 checkpoint sha256 == R419（任何不匹配 = DRIFT）。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r428_c1_sac.py --shards tmp/andes/r428_train_shards.json --workers <ladder> --round R428` (9 train shards) + `... run_r428_c1_sac.py evaluate` + `... classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r428_c1_sac.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + snapshot + 每臂 1 步真实 rollout + 每 agent replay store（填满 batch）+ SAC learner update 演练（critic/actor/α/V/软更新 seam）+ save/load roundtrip + **sac_semantics_probe（语义门，留痕进 rehearsal JSON）** + 纸奖励重建路径。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence, sac_semantics_probe
- capacity_evidence: memory/rounds/R428/capacity_evidence.json
- host_process_budget: 17
- wsl_python_processes: 17
- native_threads_per_process: 1
- other_reserved_processes: 0

（R427 关闭后 solo 阶梯；若 R427 仍在飞则按 concurrent 分支声明 R427
sealed 17 并改写本段——seal 前冻结实测值回填。）

## 资产保护契约

- R419-R427 资产只读（对照与锚只读引用）；sac.py/sac_base.py/sac_ctde.py
  字节不动；cd_matd3 家族字节不动；paper-cited 资产只读；dirty worktree
  保留。
- 新文件仅: SAC learner 模块 + tests、run_r428 runner + tests、R428 results
  根（create-only）、Tier-1 tmp 输出、lint 工具 additive 扩展、
  ledger/feed/手稿收尾文件。

## Cross-references

- `docs/paper/kd_4agent_paper_facts.md`（接口真源：Eq.11-23、Alg.1、Table I、
  §12/§13 调和点）。
- `working/soft_spot_experiment_program.md` C1-SAC 项。
- CLM-0045/0048/0059（R41/R43/R51 历史 SAC）；ADR-0002（paper-strict-pure
  与 R18 发散）。
- `skills/kundur-round/SKILL.md` §2 语义门。
