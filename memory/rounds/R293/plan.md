---
round: R293
state: aborted
opened: '2026-08-02'
closed: '2026-08-02'
supersedes_rounds: []
superseded_by_round: null
abort_reason: User redirected programme to model-first control synthesis before further
  neural architecture claims.
superseded_note: null
---
# R293 plan — strong-classical-prior distributed comparison

**Driver**：修 ICEMS 一眼硬伤。R280 只比同一标量，R292 虽是真分布式但把性能/无伤害失败混成 `INVALID`，且没强经典分布式基线。

**Parent**：Q-0050。R292/CLM-0675 只作开发证据，不改阈值、不补 trace、不救结论。

## TL;DR

先冻一个 neighbour-only 经典 edge 惯量重分配器，再让 central/distributed TD3 都只学同一经典先验上的有界 magnitude residual。q0、经典、集中式、分布式同三维 edge action、同物理层、同 formal bank。证据完整性与性能/安全分轨；跑得差是有效负结果，不是 `INVALID`。

## Falsifiable question

强 common-mode 经典控制已固定时，neighbour-only distributed edge residual TD3 是否在 fresh bank 上同时超过 tuned causal edge controller，并对 joint-observation centralized vector residual TD3 达到双主端点优越或 5% 非劣？

## Methodology

### Causal objects

- q0：R274 droop--PI storage + R275 3 s common-M pulse；edge residual 恒零。
- classical-edge：path edges `[(0,1),(1,2),(2,3)]`。节点 severity 只用本机当前 normalized `|delta-f|, |RoCoF|, |delta-P|`；edge raw=`tanh(k*(severity_target-severity_source))`，正 flow 把惯量移向 target。
- distributed residual：同一 shared 10->64->64->1 actor 逐 edge 调用，只看两端 obs；critic 可 joint，但只在训练用；三条 edge 输出分别执行，无中央 action aggregation。
- centralized residual：joint 20->59->59->3 actor；同一 classical prior、edge 坐标和执行器；actor 参数量差 <1%。
- 两 learned actor 只改 magnitude：`m=clip(|classical_raw|+0.5*actor,0,1)`；方向固定为 severity gradient；`severity_target=severity_source` 时 edge=0。此投影只保证局部方向一致，不称 stability/safety certificate。

## Classical development contract

- feature families 固定三组：`rocof=(0,1,0)`、`freq_rocof=(0.5,0.5,0)`、`full=(1/3,1/3,1/3)`。
- gain 固定 `[0.25,0.5,1.0]`；共 9 个，不增补。
- development bank：R274 24 cases，只作 viewed development；9 x 24，15 steps。
- 排序：先过 action/finite/zero-sum；再最小化两主端点 equal-weight mean candidate/q0 ratio；并列取较低 edge TV，再按冻结顺序。
- guard bank：R292 v3 的 24-case bank 仅作 viewed guard；复用 hash-verified q0，选中经典臂另跑 24 条 60 s。
- credible gate：全部执行/物理/存储完整；edge action 非平凡；两主端点、RoCoF、worst-bus peak 的 mean 与 CVaR 均不得相对 q0 恶化超过 5%。不要求经典差分臂必须赢 q0；q0 本身是强经典 common baseline。若全 9 个无安全可用候选，`CLASSICAL-FAMILY-NO-GO` 后停。

## Learned contract

- seeds=`[211,257,293,331,379]`，全部报告；不复用 R292 seed，不选 seed。
- 每 architecture/seed 300 episodes x 15 steps；warmup 512；同 TD3 critic、replay、optimizer、exploration、batch 和 update schedule。
- reward 固定 R292 sync + area + edge-TV，再加 `0.25*max_i((RoCoF_i/0.5)^2)`；因为 R292 的已知阻塞是 RoCoF tail。本轮不 sweep weight。
- checkpoints 全冻后才生成 fresh bank。训练 failure 原样保留；不自动换 seed/宽度/reward。

## Formal matrix and statistics

- fresh-bank generator seed `2026080203`；environment seed 42；24 signed multi-location cases；生成/screen 先于任何 controller formal trace。
- arms：q0 + selected classical-edge + central residual 5 seeds + distributed residual 5 seeds；24 x 12 = 288 条 60 s。
- co-primary：normalized synchronization loss；first-3-s inter-area IAE。20,000 次 hierarchical seed/scenario bootstrap，seed `2026080204`；lower better；learned-vs-classical materiality -2%。
- distributed-vs-central non-inferiority：每主端点 `(distributed-central)/central*100` 的 one-sided 95% bootstrap upper < +5%；至少 3/5 paired seeds 双端点不差于 +5%。
- positive claim 另需 common/fast/slow/storage mean 与 CVaR、每设备 M/D、zero-sum、action TV、failure/no-convergence 全部过冻结门。

## Decision tree

1. seal/hash、代码/预算、fresh-bank 顺序、trace 归属、action 执行或 bootstrap 实现失败 -> `INTEGRITY-INVALID`。
2. 仿真 non-convergence、controller failure、主端点失败或 no-harm 失败保留为 outcome；不得触发 integrity invalid。
3. distributed 对 classical 双主端点均 <=-2%、95% upper <0、至少 3/5 seed 双端点方向改善，且 positive guards 过：
   - 对 central 同样 material superiority -> `DISTRIBUTED-SUPERIOR`；
   - 否则两端点均过 5% 非劣 -> `DISTRIBUTED-NONINFERIOR-LOCAL`；
   - 否则 -> `DISTRIBUTED-EFFECTIVE-CENTRALIZED-SUPERIOR`。
4. central 对 classical 过双门、distributed 不过 -> `CENTRALIZED-SUPERIOR`。
5. 两 learned 臂均不过 classical 双门 -> `NO-NEURAL-INCREMENT`。
6. efficacy 方向过但 positive guards 失败 -> 对应 `*-GUARD-FAIL` 有效负类；不得写性能/架构正结论。

## Engineering gate

- unit：severity orientation/sign symmetry、strict endpoint locality、prior/residual projection、edge/node limits、slew、zero-sum、inactive zero、central/distributed capacity与 checkpoint round-trip。
- Windows tests 全绿；WSL import；真实 ANDES q0/classical/两 learned 各一次 finite short smoke。
- 工程门绿后最多 3 个 WSL Python 并行；同阶段共享 seal，worker 独立原子写；coordinator `wait`，不高频轮询。

## Assets and boundaries

- reusable controller/actor logic 进 `src/andes_rl_kundur/`；判定进 `probes/`；execution adapter 进 `scripts/`；artifacts 只进 `results/r293_*`、`memory/rounds/R293/`、`paper/icems2026/reports/R293.md`。
- 不改 R279/R280/R292 artifacts；正式 feed publication gate 前不改 ICEMS LaTeX。
- 只可称 4-VSG path 上 neighbour-only parameter-sharing CTDE edge policy；不称 generic MARL、四独立 device agents、topology generalization、通信 robustness、stability、deployment 或 MARL 必然优于 centralized。

## Stop

经典 family credible gate 失败即停；否则只跑上述 5-seed/12-arm matrix。任何 formal endpoint 可见后不改 gain、feature、reward、seed、action、阈值或 bank。

## Cross-references

- q0 measured sources：`results/r274_prospective_active_power_authority`、`results/r275_fast_md_authority`；本轮 formal 仍 fresh 重跑，不复制旧数字。
- scalar boundary：CLM-0610 / R280；true-distributed invalid boundary：CLM-0675 / R292。
- 本轮唯一 in-flight question：Q-0050。
