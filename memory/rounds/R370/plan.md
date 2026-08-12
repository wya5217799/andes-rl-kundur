---
round: R370
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R370 plan — 固定标题的后继机制方向门

**Opened**: 2026-08-12
**Driver**: 直接逐台调节惯量和阻尼的有限候选余量门未通过；在任何新实现或训练前，必须选择一个既改变执行机制、又不破坏逐台虚拟同步发电对象的后继方向。
**Parent**: CLM-0970, CLM-0975, CLM-0980, CLM-0990; design input CLM-0580, CLM-0965

## TL;DR

本轮只完成方向选择：比较继续调参、独立旁挂储能、仅换学习或通信结构、以及“每台虚拟同步发电单元拥有受能量约束的内部有功功率入口”四类路线。只有最后一类可同时保留既定题目对象、改变已停止的执行机制并复用现有储能约束资产；它必须先通过对象修复门，现有独立并网储能不能直接改名复用。本轮不改控制代码、不运行仿真、不训练。

## Snapshot at plan-time (oracle as of 2026-08-12)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0103 closed-negative @ R369, by CLM-0990 — Does one globally fixed local-neighbour per-VSG M/D controller clear the deterministic efficacy and no-harm gate on the balanced development bank, while a bounded non-learning outcome oracle shows at least five percent additional headroom with nonconstant direct actions?
- Q-0102 closed-positive @ R366, by CLM-0980 — Can the fixed-title line freeze a 60-Hz, permission-matched per-VSG inertia/damping comparison contract and a deterministic baseline family that leaves a falsifiable learning gate without importing the old action-object mismatch or claiming storage feasibility?
- Q-0101 closed-positive @ R365, by CLM-0975 — Does the existing ANDES V4 candidate provide four separately addressable VSG agents with independent bounded inertia and damping actions, causal local-neighbour observations, measurable differential dynamics, and nonzero network-transmitted action authority?

## Methodology

1. 以固定题目四词契约审查候选：每台物理单元与运行时执行者一一对应；动作逐台独立；解耦端点仍是设备间差分振荡；协同必须由有无邻居信息的运行时消融识别。
2. 以 `CLM-0990` 为停止边界：任何仍以逐台惯量、阻尼为主动作的学习器、奖励、网络或通信变体均不构成新机制。
3. 审查现有储能实现的对象语义。`andes_vsg_storage_env.py` 明示四个独立并网储能与四个虚拟同步代理仅同母线并存；因此它的功率动作不能直接称为虚拟同步发电单元动作。
4. 审查可复用机制资产：逐台能量、荷电状态、功率、爬坡和电流投影；四节点共同/差分功率坐标；确定性功率控制器；封存评估与故障保留。旧结果只作方向输入，不迁移为本线证据。
5. 候选方向定义为每台虚拟同步发电单元内部拥有一个显式有功功率参考入口及能量状态。运行时动作是四个逐台有界功率参考，而不是独立旁挂装置功率；共同/差分坐标只用于分析和同权限控制设计，不把四个执行者压成一个中心动作。
6. 下一门只验证对象和入口：一一映射、单位/符号/时延、零动作一致性、单端干预因果性、按实际交换功率计量的能量守恒，以及逐台独立约束。未通过即停止该方向；通过后另行设计确定性基线和非学习余量门。

## Gate

- `DIRECTION-SELECTED-WITH-OBJECT-REPAIR`：仅当一个候选既 materially 改变逐台执行机制、又能在定义层面保持每台虚拟同步发电单元为物理对象与执行者，并有明确的先行对象修复门。
- `DIRECTION-REJECTED-OBJECT-MISMATCH`：若候选动作属于独立并网储能、中心标量或边执行者，却被重命名为逐台虚拟同步发电协同。
- `DIRECTION-REJECTED-SAME-MECHANISM`：若只换学习器、奖励、消息、种子或网络，主动作仍是已停止的逐台惯量、阻尼。
- `NO-DIRECTION`：若没有候选同时满足题目对象、机制差异和可执行的先行验证。
- 本轮返回方向决策，不授权实现、仿真、训练、性能或论文主张。

## 资产保护契约

- 不修改 `src/`、`scripts/`、`probes/`、`tests/`、旧 feed、旧 claim、旧 result 或 checkpoint。
- 只写本轮 plan/feed/decision claim/verdict，以及当前线 `LINE.md`、`ROUTE.md`、`ARTIFACTS.json` 的导航同步。
- model-first 实现清单哈希：`099a4c3acae425ff23276dc8ea8a92535c27b2bb472047cae4e210048813772d`。
- 独立储能环境哈希：`52cced7b9b6958de991e73192a83b78d9794bf2959e42c78f76a6375f6f2d4f4`；能量投影实现哈希：`9a8f113b7da792aa5a32e5fdccfc031beb7cbb3cab7bf8f2a9deda850d5de991`。
- 共同通道 feed 哈希：`9f019f8bb3fb9a7a79efb8341b90011bf74bf489ebfde72e09f0b83307c9c541`；外部调研与 Yang 事实基底沿用 R364 登记哈希。

## Cross-references

- `CLM-0990`：逐台惯量、阻尼有限候选余量不足，停止该注册方案但不否定其他协同机制。
- `CLM-0580`：独立并网储能具有受约束的共同频率调节权限，但对象只限混合代理。
- `CLM-0965`：共同功率通道在离线有限样本上扩大物理余量，但没有因果控制器或学习结论。
- `paper/decoupling_marl_model_first/working/implemented_control_and_topology.md`：虚拟同步代理与储能模型分离的实现事实，以及可复用功率/能量约束资产。
