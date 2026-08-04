---
round: R292
state: completed
opened: '2026-07-31'
closed: '2026-08-01'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R292 plan — true distributed vector comparison

**Driver**：旧 shared 分支四次局部 actor 后集中压成同一标量 q。用户明确授权改成真正分布式执行，并要求稳定后无人值守、最大安全并行。

**Parent**：Q-0049；CLM-0610 只作 scalar 证据边界，不改 R279/R280/R291。

## TL;DR

固定一条 4 节点 path 通信图，三条有向边对应三维零和动作。集中式和分布式都控制相同 edge-flow 坐标；区别只在 joint actor 对比 neighbour-only shared edge actor。先 TDD 和真实 ANDES smoke；工程稳定后，3 个 WSL worker 并行跑三种子，不看性能调参。

## Falsifiable question

在同一 modified Kundur plant、慢 droop--PI 储能层、3 s 公共惯量脉冲、三维零和动作、team reward、训练预算和 fresh bank 下：neighbour-only distributed edge TD3 是否相对 q0 在两个差模主端点都有可重复价值；它相对 matched centralized vector TD3 是胜、统计不可分、还是明显更差？

## Methodology

### Frozen causal objects

- 节点顺序：VSG 0/1/2/3；通信图 edges = [(0,1),(1,2),(2,3)]，方向按小编号到大编号。
- local obs 5 维：本机 60-Hz delta-f、本机 RoCoF、上一时刻本机 residual、本机相对 reset 的 P、静态 area sign。无 common mean、无远端状态。
- distributed actor：同一 10->64->64->1 actor 逐 edge 调用，只看两端 obs；centralized twin critic 只训练时使用 20 维 joint local obs 和 3 维 executed edge action。
- centralized actor：20->hidden->3，参数量在实现预检时一次性匹配 distributed actor，随后冻结；同一 critic、reward、replay、optimizer、exploration 和训练步数。
- edge flow absolute max 0.125；edge slew max 0.125；node residual = incidence @ edge flow。故 sum residual = 0，node magnitude <=0.25，node slew <=0.25，无中央 action projection。
- physical action：固定 common + node residual 只改 M；D residual = 0；15 steps 后 edge/node residual 全零。
- seeds = [101,137,173]；每 architecture 每 seed 300 episodes x 15 steps；warmup 512；不选种子。
- fresh-bank generator seed = 2026073101；environment seed = 42；24 signed multi-location cases；checkpoints 全冻结后才生成和 screen。
- formal arms = q0 + central_vector_s101/s137/s173 + distributed_edge_s101/s137/s173；24 x 7 = 168 条 60-s trajectories。
- co-primary：normalized synchronization loss；first-3-s inter-area IAE。20,000 次 hierarchical seed/scenario bootstrap，seed 2026073102，lower better，materiality -2%。

## TDD seams

1. vector contract 公共接口：edge action -> bounded/slew-limited edge flow + exact-zero-sum node residual + physical M/D action。
2. environment reset/step：四个 5 维 local observations；逐设备执行；60-Hz telemetry；旧 scalar env 不变。
3. distributed policy inference：一条 edge 的输出不受非端点 observation 改动；无 joint actor / central action aggregator。
4. matched centralized policy：同一 3 维 edge action合同、参数预算、checkpoint reload。
5. training/formal adapters：seal-before-trace、no overwrite、failure retention、3-worker ceiling、action/storage/completion/provenance audits。

## Engineering stability gate

以下全部通过才允许并行训练：Windows focused/full tests；WSL import；一个 q0 与两个 worked edge-action 的短真实 ANDES smoke；两 architecture 各一次 finite update；checkpoint round-trip bit-identical；locality、zero-sum、magnitude、slew、active-window、D-zero、60-Hz schema guards 全绿。此门不看控制性能，不据结果换图、奖励、宽度或 seed。

## Formal decision tree

1. 任一 seal/hash、训练预算、fresh-bank 顺序、168 条 completion、action/storage/physical/tail、bootstrap 或 provenance 合同失败 -> `INVALID`。
2. distributed 对 q0 两个主端点均 <=-2%，95% upper <0，且至少 2/3 seeds 双端点方向改善；再看 distributed 对 central：
   - 两端点也通过同一改善门 -> `DISTRIBUTED-SUPERIOR`；
   - central contrast 任一端点 95% interval 跨 0 且无 material worsening -> `DISTRIBUTED-EFFECTIVE-NOT-SEPARATED`；
   - 否则 -> `DISTRIBUTED-EFFECTIVE-INFERIOR`。
3. distributed 未过 q0 双门，但 central 过 -> `CENTRAL-VECTOR-ONLY`。
4. 两 learned arms 都未过 q0 双门 -> `NO-REPRODUCIBLE-VECTOR-VALUE`。

所有 positive class 还要求 common/fast/slow/storage mean 与 CVaR guards、每设备 M/D 范围、零和、动作 TV、失败和 tail guards 全绿。次要端点不得救主门失败。

## Execution and no-polling contract

- ANDES 仅 WSL `/home/wya/andes_venv/bin/python`，入口统一 `scripts/andes_scratch.py`。
- 稳定后用一个隐藏的 persistent `wsl.exe` 跑 unattended shell；shell 用 `wait` 管三 worker，不靠 Codex 高频轮询。
- 同时最多 3 个 WSL Python；每个 seed worker 顺序跑 central/distributed，三 seed 并行。
- worker 原子写独立目录，resume 只接受 hash 匹配的 completed artifact；失败保留、不覆盖、不自动重试。
- training 全完成并验证后，coordinator 自动 seal fresh bank、3-way screen、seal formal、3-way formal evaluation、一次 analysis；任一硬门失败立即停止后续阶段。

## 资产保护契约

- 不改 `paper/`、`andes_vsg_env_v4.py`、`base_env.py`、`paper_grade_axes.py`、R279/R280/R291、旧 checkpoints/results。
- 新 reusable logic 只进 `src/andes_rl_kundur/`；稳定执行 adapter 进 `scripts/`；结论逻辑进 `probes/`；本轮 artifacts 只进 `results/r292_*` 和 `memory/rounds/R292/`。
- 不作 topology generalization、通信延迟/丢包 robustness、stability certificate、统一 GFM-BESS、EMT/HIL 或 deployment claim。

## Stop

工程门失败即关闭 exact contract；工程门过则只跑这一套冻结矩阵。不得新增 seed、网络、reward、图、动作维度或 post-hoc tolerance。正式结果完成前不解释 progress logs。

## Cross-references

- Q-0049：本轮唯一 in-flight 问题。
- CLM-0610 / R280：只提供 scalar learned-allocation 已存在和 broad MARL claim 禁止外推的父边界。
- R274 + R275：fresh q0 arm 复现其冻结 slow droop--PI storage + 3 s common-inertia layers；不把旧 trace 当本轮 baseline 数字。
- R279：训练预算和 physical endpoint/audit 结构的只读来源；不复用其 formal bank、判定或 scalar action contract。
