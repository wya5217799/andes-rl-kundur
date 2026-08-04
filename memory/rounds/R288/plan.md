---
round: R288
state: completed
opened: '2026-07-30'
closed: '2026-07-30'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R288 plan — sealed small-signal topology-information value gate

**Status**: ACTIVE
**Opened**: 2026-07-30
**Driver**: 在训练图策略前，先判定真实线路状态变化是否使“知道拓扑”具有
可测决策价值。
**Parent**: CLM-0595, CLM-0615, CLM-0630, CLM-0650; Q-0047

## TL;DR

不训练。先只用结构、线路参数、连通性和 q0 PFlow 选出 3 个合法线路开断，
写 seal 后才跑 EIG。名义图 + 3 个变体，各跑 q0 + R277 六个 Hadamard
零和惯量分配，共 28 个点；比较每拓扑谱 oracle 与最佳 topology-blind
鲁棒固定分配。结果只回答小信号信息价值，不进入时域、GNN 或论文正文。

## Snapshot at plan-time (oracle as of 2026-07-30)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0047 [opened R287] Does genuine network-configuration variation create material small-signal value for topology-conditioned differential-inertia allocation?

## Recently Closed (last 3)

- Q-0046 closed-positive @ R287, by CLM-0650 — Does the frozen differential-allocation gain retain material value when the declared inter-area corridor weakening is extended from k=2.0 to k=2.5 and k=3.0?
- Q-0045 closed-positive @ R286, by CLM-0645 — Does the differential-allocation gain survive a weakened inter-area tie corridor in time domain, and does it depend on disturbance location?
- Q-0044 closed-positive @ R285, by CLM-0640 — What is the structure of the inter-area / VSG-local mode hybridization zone at low aggregate inertia (M0 in [100,200), q = +/-0.25)?

## Methodology

### A. 冻结对象

- Plant: `AndesMultiVSGEnvV4._build_system()`，不改 env 默认值。
- VSG 顺序: Bus `[12,16,14,15]`; D、G4、PFlow/EIG 与
  `probes/eig_alloc_common.py` 保持。
- q0: `[350,350,350,350]`，fleet total M=1400。
- 六分配: R277 三个 Hadamard 零和方向及其符号；每个向量两台 M=500、
  两台 M=200，total M=1400。固定顺序:
  `h1_pos,h1_neg,h2_pos,h2_neg,h3_pos,h3_neg`。
- 不读 R288 EIG/时域 endpoint 选 topology；不运行时域。

### B. Stage A — topology selection，EIG 前

只读 base plant 的 Bus/Line 状态、端点、area、r/x/b；不调用 EIG。

排除:

1. `Line_4/5/6`（已测走廊代理，不重复）；
2. `Line_8`（默认 Toggler 语义，避免重复事件）；
3. 任一端点为 VSG Bus 12/14/15/16 的 stub；
4. 同端点 parallel group 大小 >1（删一条不改变 simple graph）；
5. 删边后 active-bus simple graph 不连通；
6. 非有限/非正 x，或 q0 PFlow 不收敛。

结构排序先于 PFlow/EIG:

- 对每个合格 unique edge，计算删边后最短路径变长的无序 bus-pair 数
  `distance_impact`；
- 按 `distance_impact` 降序、`abs(x)` 降序、line idx 升序；
- 从 q0 PFlow 通过者中先贪心取端点互不重合的前 3 条；不足 3 时按原排序
  补齐。

选定 3 条后写 `topology_inventory.json` 与
`memory/rounds/R288/topology_information_seal.json`；seal 含完整 inventory、
选择/排除理由、allocation library、阈值、输入/代码 hash。seal 存在后禁止
重选。

### C. Stage B — 28-point EIG matrix

Topologies: `nominal` + 3 个 sealed 单线路静态开断。每个 topology 新建 plant，
只令目标 `Line.u=0`，保持 bus/VSG 数和其余线路状态不变，重新 PFlow。

每 topology 跑 7 个冻结 M 向量。沿用 R281/R283:

- EIG 后合并共轭对；
- 0.2–1.5 Hz 中按最大
  `|P_area1-P_area2|` 识别 GENROU inter-area 候选；
- within-topology candidate 相对该 topology q0:
  participation cosine >=0.90 且 |df| <0.05 Hz；
- variant q0 相对 nominal q0:
  cosine >=0.80 且 |df| <0.10 Hz；
- 记录 PFlow、G4、total-M、opened-line、bus/VSG-count 和
  positive-real-eigenvalue guards。

名义 topology 的 q0/h1_pos/h1_neg 必须复现 R281 q=0/+0.25/-0.25 三锚点，
`|dzeta| <1e-6`；否则 INVALID。

### D. Registered estimands

对 topology `t` 与 eligible allocation `a`:

`zeta_ratio(t,a) = zeta(t,a) / zeta(t,q0)`。

- Per-topology oracle: 该 topology 最大 zeta；平局先 q0，再按冻结顺序。
- Topology-blind robust fixed: 对全部 4 topology 都 eligible 的同一 allocation，
  最大化 `min_t zeta_ratio(t,a)`；同样平局规则。
- Headroom:
  `100*(zeta_oracle(t)-zeta_fixed(t))/abs(zeta_fixed(t))`。
- 报告 oracle action 数、各 topology headroom、mean/max headroom、固定动作的
  worst-case ratio、全部 branch/physical guards。

5% headroom 延续 R281 modal materiality；2% mean headroom 延续当前物理
endpoint materiality。阈值在 seal 后不改。

## Gate

1. **INVALID**: seal/hash 漂移；选择规则不符；不是 4x7 完整矩阵；名义三锚
   失败；PFlow/line/VSG/total-M/G4/稳定性 guard 失败；非有限结果。
2. **PARTIAL-IDENTIFICATION**: integrity 通过，但任一 variant q0 跨 topology
   branch check 失败，或任一 topology 不是 7/7 candidate 都通过 within-branch
   check。只报描述，不做信息价值结论。
3. **STATIC-TOPOLOGY-VALUE**: 全部 guard/branch 通过；per-topology oracle 至少
   选 2 种不同动作；max headroom >=5%，且 4-topology mean headroom >=2%。
   这只允许提出下一轮经典 topology-conditioned 时域问题，不允许 GNN。
4. **NO-MATERIAL-TOPOLOGY-VALUE**: 有效完整矩阵但不满足 3。停止近期
   topology-conditioned learner/GNN 路线。

严禁在结果可见后换 topology、候选、识别阈值、headroom 阈值或固定动作定义。

## Outcomes

- `STATIC-TOPOLOGY-VALUE`: 7/7 branch/guards 全过，oracle 动作数 >=2，
  max headroom >=5%，mean headroom >=2%。
- `NO-MATERIAL-TOPOLOGY-VALUE`: 有效完整矩阵，但上述动作切换或 headroom
  联合门不通过。
- `PARTIAL-IDENTIFICATION`: integrity 通过但跨 topology q0 或任一 candidate
  branch gate 不全；不解释 headroom。
- `INVALID`: seal/anchor/matrix/PFlow/line/VSG/total-M/G4/稳定性/finite 任一
  integrity guard 失败。

名义 baseline 与三锚来自
`results/r281_eig_mechanism/summary.json`；R288 不从其他 run 外推 baseline。

## Execution

1. TDD pure selection/allocation/oracle/gate logic。
2. `prepare` 通过 WSL scratch launcher 跑 topology inventory + q0 PFlow，
   写 seal；检查结果目录此前无 R288 EIG。
3. `run` 在同一 seal 下串行跑 28 EIG，写一个不可覆盖 matrix + `.sha256`。
4. `analyse` 只读 sealed matrix，写 analysis/provenance + sidecars。
5. reserve claim 后写 `results/r288_topology_information/FEED.md`，执行
   publication gate、feed_check、claim/verdict/question/programme 收尾。

Planned files:

- `src/andes_rl_kundur/evaluation/topology_information.py`
- `probes/r288_topology_information.py`
- `scripts/run_r288_topology_information.py`
- `tests/test_topology_information.py`
- `memory/rounds/R288/topology_information_seal.json`
- `results/r288_topology_information/`
- `memory/rounds/R288/verdict.md`

## 资产保护契约

- 不改 `andes_vsg_env_v4.py`、train/reward/controller/checkpoint、R277/R281-R287
  产物、scenario bank、论文/LaTeX/图/venue。
- 保留所有现有 tracked/untracked 用户改动；不 stage/commit/push/clean。
- ANDES 只用 WSL `/home/wya/andes_venv/bin/python`，入口经
  `scripts/andes_scratch.py`；不在 repo root 留 ANDES scratch。
- 不覆盖任何 R288 formal artifact；失败保留，修复只能走 execution amendment。

## Cross-references

- `docs/research/2026-07-30_topology_information_value_gate.md#decision`
- `memory/questions/Q-0047.md`
- CLM-0595 / R277 complete zero-sum spatial basis
- CLM-0615 / R281 nominal modal anchors
- CLM-0630 / R283 branch checks and declared impedance-proxy boundary
- CLM-0650 / R287 one-topology time-domain boundary
