---
round: R265
state: completed
opened: '2026-07-24'
closed: '2026-07-24'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R265 plan — Q-0028 sealed disturbance replication

**Status**: COMPLETED
**Opened**: 2026-07-24
**Driver**: R264 的 cap-0.25 门控只在发现集 LS1/LS2 上有小信号；
Q-0028 要求冻结门控后做前瞻 held-out 复现。
**Parent**: Q-0028, R264, CLM-0520

## TL;DR

先用固定生成器生成 20 条无 LS1/LS2 anchor 的随机负荷扰动，
把实际 JSON bytes 和 SHA-256 封存，再让 R201、droop k=10、
static alpha=0.25、R264 gate cap=0.25 跑完全相同的场景。
主比较只看 gate 对 static；物理 common-mode IAE 和归一化
differential loss 是共主终点。`geo` 不在随机场景上算。

## Snapshot at plan-time (oracle as of 2026-07-24)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0028 [opened R264] Will prospectively unseen load cases reproduce the candidate effect?

## Recently Closed (last 3)

- Q-0027 closed-partial @ R264, by CLM-0520 — Can a state-dependent droop residual policy advance both dual metrics?
- Q-0008 closed-negative @ R252, by CLM-0415 — Verify paper-metric ranking persists at 500-ep paper convergence horizon
- Q-0021 closed-positive @ R252, by CLM-0231 — V4 env TGOV1 governors u=1.0 in ANDES JSON but R08 Finding 3 says "completely ineffective" — which is true post-R37 refactor?

## Methodology

### 冻结对象

- Scenario generator:
  `generate_test_scenarios(n=20, seed=20260724, include_anchors=False)`.
- Bank size: `n=20`. 这是算力约束的 exploratory replication，
  不是 publication-level power claim。
- Bank serialization: UTF-8 canonical JSON，`sort_keys=True`，
  compact separators，末尾一个 LF。
- Bank manifest 必须写生成器 fully-qualified name、参数、当前 git HEAD、
  生成器源码 SHA-256、serialization rule、20 条实际 scenario。
- 运行任何 controller 前把 bytes 写到
  `memory/rounds/R265/scenario_bank.json`，把 SHA-256 写到 sidecar，
  再把 hash 回填本 plan。Evaluator 每次启动先重新 hash；不匹配就拒跑。
- 生成器、bank、scenario 顺序、样本量、seed、controller 参数、
  endpoint、bootstrap seed、判定 gate 看过第一条 trajectory 后都不能改。

### Controller 和运行合同

- Frozen checkpoint: `results/r201_w1_hreg_tau005_s54`, suffix `best`.
  四个 actor 文件逐个 SHA-256 入 provenance；R201 仍是 legacy evidence。
- Controllers exactly:
  1. deterministic R201;
  2. droop `k=10`;
  3. static blend `alpha=0.25`;
  4. R264 mode-ratio gate
     `ratio_full_scale=0.05`, `alpha_cap=0.25`.
- V4 `paper_faithful`, env seed 42, 150 steps, real ANDES in WSL。
- 每条 scenario 内四 controller 连跑；run order 按 scenario index
  cyclic rotation，平衡机器时间顺序。
- Trace 必须带 bank hash、scenario index、run order、controller spec、
  checkpoint hashes、50-Hz legacy / 60-Hz physical provenance。
- 支持只读 resume：已有 trace 只有在 metadata、bank hash、controller
  spec 和 completeness contract 全匹配时才复用；默认拒绝 overwrite。
- 任何 runner exception 单列为 evaluation error，不冒充 plant failure。
  `tds_failed` / incomplete 是控制结果，必须保留，不能从统计中静默删掉。

### 预注册 endpoints

所有 lower-is-better。主比较是 gate minus static alpha=0.25；
负 effect = gate 改善。

共主终点：

1. `vsg_mean_iae_hz_s`：60-Hz physical common-mode restoration；
2. `normalized_sync_loss_hz2`：
   `mean_t mean_i (delta_f_i - mean_i(delta_f))^2`，不随 horizon 或
   agent 数线性放大。

物理/控制 dashboard：

- worst-bus peak、VSG-mean peak、dispersion RMS/ISE、max sampled RoCoF、
  terminal worst-bus error、0.05-Hz settling；
- normalized sync loss；
- action L1、total variation、saturation fraction；
- failure count/rate 和 95% exact binomial interval。

每个 continuous endpoint 报 controller mean/median、worst-1、worst-2、
upper-tail empirical CVaR90。`n=20` 时 CVaR90 只有 worst 2，
只作描述性 tail guard，不给它强推断含义。

### Paired uncertainty

- `10,000` 次 paired percentile bootstrap，seed `2026072401`。
- 每次重采样 scenario index；同一个 index matrix 同时保留四 controller，
  禁止 controller 各自重采样。
- 对预先写死的 contrasts 报 mean difference、ratio-of-means percent
  effect、95% interval、bootstrap probability of improvement：
  gate-static（primary）、gate-R201、gate-droop、static-R201、
  static-droop。
- 若 contrast 任一 controller 有 failure/incomplete，则不丢 scenario；
  continuous bootstrap 标为 unavailable，并由 failure outcome 决策。

## Gate

先检查 invalid：

- bank/hash/source contract 破坏、checkpoint hash 漂移、controller 参数漂移、
  runner exception、trace provenance 缺失，或 verification fail：
  **INVALID**，修基础设施后用同一 bank 重跑，不改科学 gate。

有效结果按 gate 对 static alpha=0.25 判：

- **POSITIVE replication**：
  20/20 paired traces 都 complete；两个共主终点的 paired 95% CI upper
  都 `<0`；gate failure 不高于 static；worst-bus peak 和 max RoCoF 的
  CVaR90 不劣于 static `>5%`，worst-1 不劣于 `>10%`；
  settling success 不低；action-TV CVaR90 不劣于 `>25%`。
- **PARTIAL replication**：
  上述 safety/failure/action guards 全过；恰好一个共主终点 CI upper
  `<0`，另一个 point effect `<0`。这是 mixed/underpowered signal，
  不能叫复现成功。
- **NEGATIVE replication**：
  其他所有有效结果，包括两个 CI 都含 0、任一共主 point effect
  `>=0`、gate failure 增加、或 tail/action guard 失败。

Positive 才进入 corrected multi-seed residual training。
Partial/negative 关闭这个手工 threshold/cap gate；不许在 sealed bank
上调 threshold、capacity、checkpoint 或 decision gate。

## Sealed bank provenance

- Bank path: `memory/rounds/R265/scenario_bank.json`
- SHA-256:
  `68816647eca8c0ccabe847ec883eaf59676c7afc915c09081a7851bf1e2dfae0`
- Sidecar: `memory/rounds/R265/scenario_bank.json.sha256`
- Seal audit before first controller trajectory:
  20/20 unique random scenarios, 0 LS1/LS2 anchors, 0 exact overlap with
  the R58 seed-2026 random subset, four PQ buses represented, 10 positive /
  10 negative steps. Windows `Get-FileHash` matched the sidecar exactly.

## 资产保护契约

- 不改 V4 dynamics、`V4Config.paper_faithful`、`paper_grade_axes.py`、
  R201 checkpoint、R262/R264 artifacts。
- `geo` 只留作 LS1/LS2 历史 diagnostic；本 bank 不生成 post-hoc composite。
- 新结果只写 `results/r265_sealed_gate_replication`。
- 新统计/封存逻辑放 reusable evaluation module；不用 round-only one-off
  housekeeping script。

## Cross-references

- R261 / ADR-0006：50/60-Hz 双频率 provenance。
- R262 / CLM-0510：R201、droop、static alpha=0.25 measured components。
- R264 / CLM-0520：cap-0.25 discovery-set mechanism signal。
- Q-0028：本轮 prospectively sealed replication contract。
