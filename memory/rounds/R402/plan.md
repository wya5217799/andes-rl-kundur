---
round: R402
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-15'
closed: '2026-08-15'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R402 plan — Gate A 三种子开发 canary 执行

**Opened**: 2026-08-15
**Driver**: R401 已封印完整 Gate A canary 契约并授权后继轮执行；本轮严格按
契约训练三学习臂×三种子，评估后经预注册判决策树分类。
**Parent**: CLM-1150 (R401 契约封印)；CLM-1145 (R400 修订)；
`memory/rounds/R401/formal_seal.json`

## TL;DR

Workload: `evidence`。按 R401 seal 执行：9 个 (arm, seed) 训练（43200 交互步
/ seed，4 并行 worker + launcher = 5 进程），确定性参照 + 9 策略共 240 条评估
record，分类器给出 `CANARY-PASS` / `CANARY-FAIL` / `CANARY-INVALID`。不改契约、
不换算法、不用 R399 轨迹。投影约五小时（rollout 锚定，不含更新开销）。

## Snapshot at plan-time (oracle as of 2026-08-15)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?
- Q-0110 closed-positive @ R396, by CLM-1125 — Does the projected-passive dual-droop VSM (PPVSM1) two-unit diagnostic cell pass clean native initialization, a 0.2-second zero-input stationarity gate, and a spectrum guard with no positive-real mode and no neutral degeneracy beyond the network common-angle reference, thereby opening only a separately registered signed P/Q authority gate?
- Q-0109 closed-positive @ R392, by CLM-1105 — Which installed REGF2 feedback path or parameter carries the two reproducible positive-real local modes of the exact R391 four-REGF2 equilibrium, under prospectively frozen one-variable-at-a-time parameter-perturbation EIG arms?

## Methodology

### Mission boundary

- Outcome: 9 个训练 manifest + 240 条评估 record + 24 条确定性参照 record +
  formal_analysis 分类 + feed/claim/verdict/LINE 一致关闭。
- Authority: R401 seal（contract sha256 与 launch 预算已封印）；本轮只消费、
  不修改该契约。
- Permitted: 新 learners 模块 + 测试、执行 runner + 测试、results 根
  `results/research_loop/r402_cd_matd3_canary/`、正常 ledger/feed 收尾。
- Forbidden: 算法替换/清扫、契约数值改动、R399 profile/轨迹/checkpoint 复用、
  budget 超出 seal 的 5 进程、评估 bank 训练期读取。
- Terminal: formal_analysis.json 存在且分类为三者之一；分类后关闭本轮。

### 实现（本轮新增，全部 fresh code）

- `src/andes_rl_kundur/agents/cd_matd3.py`：CDMATD3（4 独立 actor 7→[256,256]→2
  tanh；twin 联合 critic 36→[256,256]→2；actor 最小化 -(Q_d + λ Q_c)；λ 每
  episode 对偶更新）与 YangScalarTD3（同 actor；critic 36→[256,256]→1；标量
  奖励）；成本函数、RoCoF、邻居槽置零掩码；save/load。9 定向测试绿。
- `scripts/run_r402_cd_matd3_canary.py`：rehearse / train / evaluate / classify
  四 seam；load_seal 校验 R401 seal 逐字段；create-only + sha256 sidecar；
  每进程原生线程固定 1。6 定向测试绿。
- 训练循环细节：episode 按契约 24 场景确定性循环；scalar 臂步奖励 = V4 四
  agent 奖励之和（TDS 失败步 −200）；CD 臂按物理 60-Hz trace 计算 c_d/c_c
  （TDS 失败步 50/50）；buffer 满 batch 后每步 critic 更新、每 policy_delay
  步 actor/目标更新；探索噪声 0.1；训练期不接触评估 profile。
- 步数计数规则（契约消费解释）：TDS 失败提前终止的 episode 计入其已执行步，
  运行继续到累计执行 43200 交互步为止（场景循环不间断）；manifest 记录
  执行步、attempted episode 数与 TDS 失败 episode 数。评估侧 TDS 失败仍按
  契约直接判 record 无效（评估永不重试）。
- 缺跑/重启：每 (arm, seed) 配额 1，仅 host 侧崩溃（进程被杀/内存耗尽/WSL
  停机）；崩溃现场目录改名保留为 quarantine 后同 seed 从头重训；配额后仍
  缺 → `CANARY-INVALID`。

### 并行与容量（含用户授权的预密封容量修正）

- 初始冻结预算：host_process_budget=5、wsl_python_processes=5（4 worker+
  launcher）、native_threads_per_process=1、other_reserved_processes=0
  （R401 seal 校验）。四个首发训练在此预算下启动。
- 实测训练 worker 常驻 4 个开发 profile 的 V4 实例，RSS 约 900 MB。
- 用户授权容量扩容后，本轮执行一次预密封容量修正（R399 同款流程）：新增
  memory/rounds/R402/capacity_evidence_v2.json，梯 rungs 1/2/4/8、每 rung
  16 个代表性开发零动作任务；边际吞吐 5% 规则不变；内存规则按修正注册为
  并发训练 worker 投影 RSS 不得超过 WSL 总内存一半。实测：rung8 吞吐
  1.159 jobs/s（较 rung4 增加 67%）、8×900MB=7.03GB 不超过 23.5GB/2，
  选择 8 worker，新预算 host_process_budget=9、wsl_python_processes=9
  （8 worker+launcher）。修正只改并发数；臂/种子/步数/奖励/判据契约逐字
  不变。

## Gate

- 判决策树（预注册，出自 R401 契约，不得回看后改）：
  1. bank 完整有效（9 manifest + 240 + 24 record 全部 present/valid）否则
     `CANARY-INVALID`；
  2. 每 (arm, seed) 对确定性参照的 common/动作/饱和/非恒定/独立守卫全过，
     否则 `CANARY-FAIL`；
  3. message 臂对每个学习对照在两端点 seed 中位数严格改善（>0）；
  4. 至少 2/3 seed 对每个对照两端点都改善；
  5. 中位点估计两端点优于确定性参照；
  6. 奖励/坐标分不能单独判 PASS。
- `CANARY-PASS`: 只授权另行封印的 Gate B 五种子 held-out 比较，不是 title
  证据。`CANARY-FAIL`: 所选学习器路线终止，不换算法。`CANARY-INVALID`:
  无科学结论，需后继治理轮。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r402_cd_matd3_canary.py train --arm <arm> --seed <seed>` (9 次, 4 并发) + `... evaluate` + `... classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r402_cd_matd3_canary.py rehearse`
- rehearsal_scope: same-pre-attempt-path；seal/contract/source/installed runtime/
  authority 校验 + 每臂一次真实 1 步 env rollout（actor/store/save/load 全路径），
  不创建任何 formal artifact。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R402/capacity_evidence_v2.json
- host_process_budget: 9
- wsl_python_processes: 9
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- 保留 dirty worktree；不 reset/clean/stage/commit，不覆盖其他人或其他论文线
  资产。
- 不动 paper-cited 资产（`base_env.py`、`andes_vsg_env_v4.py`、`train.py`、
  `paper_grade_axes.py`）；V4 仅被 runner 只读实例化。
- R398/R399/R400/R401 全部资产只读；R399 六 profile/轨迹/数值不得成为本轮
  证据。
- 只新增：learners 模块与测试、执行 runner 与测试、R402 results 根、本轮
  feed/claim/verdict、LINE/ARTIFACTS 导航更新。
- 正式输出 create-only：崩溃 quarantine 保留，评估不重试，分类只读输入。

## Cross-references

- CLM-1150 (R401)：封印契约与容量预算；本轮唯一执行依据。
- CLM-1145 (R400)：同线修订，canary 通过/失败/无效的后继语义。
- CLM-1140 (R399)：强确定性参照来源（`local_neighbour_md_km2_kd2`）。
- `memory/rounds/R401/formal_seal.json`：contract/launch/capacity 封印。

