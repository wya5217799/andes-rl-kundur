---
round: R279
state: completed
opened: '2026-07-27'
closed: '2026-07-27'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R279 plan — reviewer-driven MARL identifiability study

**Status**: ACTIVE
**Opened**: 2026-07-27
**Driver**: Q-0041 after the adversarial ICEMS review blocked method identifiability.
**Parents**: CLM-0580, CLM-0585, CLM-0595, CLM-0600
**Reserved claim**: CLM-0605

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: plan
- Origin Date: 2026-07-27
- Verification Status: UNVERIFIED
- Version Label: code_plan_v1

## TL;DR

R279 不是续跑 R278，也不是“再找一个好种子”。它只回答审稿人最致命的可识别性问题：

1. 简单的因果区域间反馈能不能解释 seed 49 的收益？
2. 同样信息、同样动作、几乎同样参数量的集中式单 actor，能不能解释所谓多智能体收益？
3. 参数共享结构能不能在三个预先固定的新种子和一套全新封存场景上稳定胜出？
4. 零和惯量到底只是动作预算守恒，还是动态上真的接近解耦？

论文文件全程只读。任何负结果都保留；不换奖励、不换算法、不加 HAWE、不补幸运种子。

## Snapshot at plan-time

- R278 已关闭为 `PILOT-NO-GO`，不得重开或覆盖。
- 当前无其他 active round，也无 ANDES 进程。
- R274/R275 慢速有功和公共惯量层继续作为不可变物理基线。
- R278 seed 49 只作历史诊断，不进入新三种子正式汇总。
- 当前工作树中的 ICEMS LaTeX、图片和 PDF 是用户已有修改；R279 不触碰这些路径。

## Research question and hypotheses

### Primary question

在相同 plant、观测、标量动作、奖励、训练步数和物理约束下，参数共享 actor 是否具有超出因果反馈与集中式单 actor 的可重复增量价值？

### Falsifiable hypotheses

- H1 (causal explanation): 一个冻结的区域间频差/RoCoF 反馈即可吃掉 R278 的主要收益。
- H2 (centralized explanation): 直接由 joint observation 输出 `q` 的 size-matched actor 至少匹配参数共享 actor。
- H3 (MARL-specific value): 参数共享 actor 在新三种子和 fresh bank 上同时胜过 `q=0`、因果反馈和集中式 actor。
- H4 (dynamic leakage): `sum(delta M)=0` 不等于共同/差分动态严格解耦；共同频率对 `+q/-q` 仍可能有可测响应。

## Frozen plant, action and information contract

保持 R274–R278 不变：

- `AndesMultiVSGEnvV4Storage`，物理 60 Hz 报告，0.2 s 控制步长；
- R274 equal-sharing droop+PI BESS；
- R275 3 s 公共惯量脉冲；
- 仅允许 `q*[+1,+1,-1,-1]` 的 3 s 秩一区域间惯量重分配；
- `|q|<=0.25`，`|q_t-q_(t-1)|<=0.25`，D residual 恒为 0；
- M 基线 200，对应 `M=2H`、`H=100 s`；D 基线 100；正向归一化动作由 `delta M=600*a_M` 解码；
- 同一七维 local observation、同一 joint observation、同一 team reward；
- 60 s formal horizon、原有 fast/differential/common/storage/action/completion/tail guards。

代数上只登记两项保证：fleet-mean inertia budget preservation 和 rank-one inter-area input direction。任何动态“解耦”只从轨迹测量，不从零和公式推导。

## Methodology

主基线是 measured run `r275_fast_md_authority` 中的 `slow_droop_pi_plus_common_m_pos`；正式比较不使用估算 baseline。R279 依次执行机制审计、causal development、matched training、fresh-bank screen 和 formal evaluation。每一 stage 的输入 hash、预算、停止条件和输出目录在前一 stage 看见结果前冻结。
## Stage A — no-new-trajectory mechanism audit

复用不可变的 R275 `q=0`、R277 `h1_pos/h1_neg` 和 R278 seed-49 traces，生成只读诊断：

1. seed 49 的 step-0 `q` 是否跨 24 场景相同；
2. `q` 与可用区域间频差/RoCoF 的相关和饱和比例；
3. `h1_pos`、`h1_neg` 相对 `q=0` 的差分收益与共同频率泄漏；
4. odd response `0.5*(y(+q)-y(-q))`；
5. even nonlinear shift `0.5*(y(+q)+y(-q))-y(0)`；
6. M/D 的单位、基准、动作解码和模拟器字段映射。

输出只用于冻结后续比较，不重新裁决 R278。

## Stage B — causal classical comparator

### Fixed law

定义物理可解释的有界两区域反馈：

`e_f = Delta f_AB / 0.05 Hz`

`e_r = Delta RoCoF_AB / 0.5 Hz/s`

`q_target = 0.25 * tanh(-(K_f*e_f + K_r*e_r))`

随后应用与学习策略相同的标量幅值、slew、3 s active window 和零和投影。控制器只使用当前/历史观测，不看 disturbance label、未来轨迹或 oracle 选择。

### Frozen development budget

在已查看的 R274 bank 上只允许九组非零候选：

`(K_f,K_r) in {(0.25,0),(0.5,0),(1,0),(0,0.25),(0,0.5),(0,1),(0.25,0.25),(0.5,0.25),(0.5,0.5)}`。

- 每组仅跑 24 个 15-step/3-s development trajectories；严格预算 216 条。
- R275 `q=0` 的前 15 steps 按 hash 复用，不重跑。
- 每组必须 24/24 完成、动作合同通过、fast guards 不差于 +5%。
- 选择分数为两个 differential endpoint 相对 `q=0` 比值的等权平均。
- 为避免按位置过拟合，先最小化四个 disturbance-location 分层中的最坏分数，再以全库分数、较小 `K_f^2+K_r^2`、固定候选顺序破同分。
- 若没有候选同时改善两个 endpoint，仍按同一 minimax 顺序冻结最佳有效非零 law；不得把 causal comparator 偷换回 `q=0`。
- 冻结后跑一次 24-case、60-s development guard audit；只允许因实现/安全无效而按预先排序回退，不按性能重新选 gain。

该 law 是“causal inter-area frequency/RoCoF feedback”，不冒充对文献 mutual-damping 公式的逐式复现。

## Stage C — matched centralized and shared TD3

### Shared architecture

复用 R278 `SharedAreaTD3` 的方法合同：四次同一个 7→64→64→1 actor 调用，经集中聚合得到一个 `q`。actor 参数量 4,737。

### Centralized ablation

新增一个 direct scalar actor：joint observation 28→55→55→1，输出同一个 bounded/slew-limited `q`。actor 参数量 4,731；与 shared actor 相差 6 个参数。critic、target network、reward、replay、optimizer、warm-up、exploration、训练 episodes 和总 environment steps 全部相同。

### Frozen seeds and budget

- 新种子固定为 `[17,53,89]`；不含历史 seed 49。
- 两种 architecture 对每个 seed 各训练一次：总计 6 个 checkpoint。
- 每个 checkpoint 固定 300 episodes、15 steps/episode、4,500 real-ANDES steps。
- 保存全部 final checkpoint；不做 best checkpoint、early stopping、checkpoint soup 或 seed selection。
- development bank 只用于训练；训练后不根据 viewed-bank 性能删 seed 或改合同。

## Stage D — fresh-bank formal evaluation

所有 causal gains、六个 checkpoints、source hashes 和分析代码冻结后，才允许生成 formal bank。

### Bank

- generator seed: `2026072704`；
- 24 cases = 4 locations × 2 signs × 3 severities；
- magnitude ranges 与 R274 一致，但禁止复制 R274 的精确 `delta_u`；
- 先跑 identical-storage-DAE zero-support completion screen；
- 保留全部排除和失败；不 redraw；
- 至少 20/24 feasible、每个 location/sign 至少 2、edge 至少 6，否则 `INVALID`。

### Formal arms

在 included fresh cases 上比较八个 arms：

1. `q=0` frozen R274+R275 reference；
2. frozen causal feedback；
3. centralized TD3 seeds 17/53/89；
4. shared TD3 seeds 17/53/89。

每条 formal trajectory 为 300 steps/60 s。最大 3 个 WSL ANDES 进程，分片互斥、可 resume、禁止覆盖。

## Statistical analysis

### Endpoints

Co-primary：

- normalized synchronization loss；
- first-3-s inter-area IAE。

Fast/common guards：RoCoF、worst-bus peak、first-3-s common IAE、full-horizon VSG-mean IAE、final-10-s common error。

同时报告 completion、per-seed effects、场景改善比例、CVaR90、action L1/TV/saturation、M/D range、physical zero-sum ULP audit、BESS power/SOC/energy/ramp/capability 和全部失败。

### Uncertainty

- deterministic controllers vs `q=0`: shared-index paired bootstrap over formal scenarios，10,000 resamples，seed `2026072705`；
- learned architecture contrasts: two-level hierarchical bootstrap，先重采样 3 seeds、再用共享索引重采样 scenarios，20,000 resamples，seed `2026072706`；
- 每个 seed 单独列出，不只给 pooled mean；
- lower is better；materiality = ratio-of-means <= -2% 且 95% upper bound < 0；
- MARL-specific contrast同时要求至少 2/3 shared seeds 对 central 和 causal 在两个 endpoint 上方向一致改善。

## Decision gate

### MARL-IDENTIFIABLE-POSITIVE

Shared architecture 在两个 co-primary endpoint 上：

- 相对 `q=0`、causal 和 centralized 均达到 -2% materiality；
- hierarchical 95% upper bound 全部小于 0；
- 至少 2/3 seeds 对两个 simpler comparators 同方向改善；
- 所有 common、fast、tail、action、storage、completion、provenance guards 通过。

### CAUSAL-EXPLANATION-SUFFICIENT

Frozen causal law 对 `q=0` 有 guarded differential value，而 shared architecture 未通过对 causal 的上述增量门槛。

### CENTRALIZED-EXPLANATION-SUFFICIENT

Centralized actor 匹配或优于 shared，或 shared 未通过对 centralized 的上述增量门槛，但 centralized 自身对 `q=0` 有可重复价值。

### NO-REPRODUCIBLE-LEARNED-VALUE

两种 learned architectures 都未在新三种子/fresh bank 上清除两个 co-primary gates，且实验有效。

### INVALID

任一 seal/hash、匹配预算、seed、bank screen、trajectory completion、action/physical/storage、bootstrap 或 provenance 合同失败。

优先级：`INVALID` 最高；否则若 shared 通过全部独特价值门槛则 positive；否则依次报告 causal、centralized、no-reproducible 的实测解释。不得用次要 endpoint 覆盖 co-primary 失败。

### LEARNED-VALUE-NOT-MARL-IDENTIFIABLE

If at least one learned architecture clears the two `q=0` co-primary gates, but
none of the registered causal, centralized, or MARL-specific branches is
satisfied, report this non-positive residual class.  It means learned value may
exist, but the experiment cannot identify parameter sharing as its cause.  This
branch is registered before any R279 real-ANDES trajectory and prevents the
original decision tree from forcing such a result into an inaccurate
`NO-REPRODUCIBLE-LEARNED-VALUE` label.

## Monitoring and compute budget

- Windows unit/full tests 和 WSL smoke 在第一条 formal trajectory 前通过。
- 每个批次监控 process-alive、stderr、completed task count 和 60-min shard hard timeout；不自动重试 crash。
- 预计新增：216 条短 causal development + 24 条 causal full guard + 6×4,500 training steps + 24 条 screen + 最多 192 条 formal trajectories。
- 这是数小时 CPU/DAE 工作；按 stage 产物 resume，不让论文编辑与实验并发。

## Planned implementation seams

- `src/andes_rl_kundur/control/causal_area_feedback.py`
- `src/andes_rl_kundur/agents/central_scalar_td3.py`
- `src/andes_rl_kundur/evaluation/reviewer_identifiability.py`
- `scripts/run_reviewer_identifiability.py`
- `tests/test_causal_area_feedback.py`
- `tests/test_central_scalar_td3.py`
- `tests/test_reviewer_identifiability.py`
- `memory/rounds/R279/causal_development_seal.json`
- `memory/rounds/R279/training_seal.json`
- `memory/rounds/R279/formal_seal.json`
- `results/r279_reviewer_identifiability/`

## Verification

- `python memory/tools/round_preflight.py R279`
- `python memory/tools/dual_metric_lint.py`
- `python -m pytest tests -q`
- WSL `/home/wya/andes_venv/bin/python` for every real ANDES run
- targeted WSL real-ANDES smoke
- Ruff on all R279 sources/tests
- `python memory/tools/validate.py`
- `python memory/tools/render.py`

## 资产保护契约

- 不修改 `paper/icems2026/**` 或 `output/pdf/icems2026_full_paper.pdf`。
- 不修改、覆盖或重新分类 R274–R278 的 seal、trace、summary、checkpoint、claim、question 或 verdict。
- 不改 V4/storage/default controller；新增逻辑走独立 R279 seams。
- 不 stage、commit、push 或清理用户已有改动，除非用户另行明确要求。
- 不使用 HAWE、LSTM、GNN、算法/奖励/隐藏层 sweep、EMT、HIL 或部署结论。

## Cross-references

- CLM-0580: slow active-power authority positive.
- CLM-0585: common fast-inertia layer positive.
- CLM-0595: outcome-seeing differential margin exists.
- CLM-0600: R278 seed-49 pilot no-go.
- Q-0041: reviewer-driven identifiability question.
- `quality_reports/ars_icems2026_review/00_synthesis.md`.
