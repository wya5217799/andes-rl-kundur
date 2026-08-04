---
round: R287
state: completed
opened: '2026-07-30'
closed: '2026-07-30'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R287 plan -- Q-0046 弱联络边界扩展

**Status**: ACTIVE
**Opened**: 2026-07-30
**Question**: Q-0046 (programme rank 160, P1_residual_mechanism, 用户本轮授权)
**Driver**: R286/CLM-0645 已证 k<=2.0 存活且双主端点名义增益保留 >=92%。
用户要求按新流程继续一轮, 只做实验, 最多 feed, 禁止 LaTeX。当前唯一预先
提出但未测的防御性边界是 k>2.0。
**Parent**: R286, CLM-0645, Q-0045, sealed R279 bank/controllers.

## TL;DR

零训练边界扩展。冻结 R279 的 q0 + centralized s17/s53/s89, 同一 24 场景
封存库, 同一 Line_4/5/6 r/x 缩放定义, 只把 k 改为 {2.5, 3.0}。双主端点、
统计、动作/储能/注入守卫和 R286 判定树原样复用。先 seal, 后 1 条保留式
smoke, 再 3 shard 全量 192 TDS。停在 sealed results + feed + 必需 ledger,
不写论文。

## 冻结契约

1. **问题**: frozen centralized differential-allocation gain 在声明式走廊
   弱化 k={2.5,3.0} 下是否仍有材料性双端点价值。
2. **场景**: `results/r279_fresh_bank/formal_bank.json`, 24 场景, hash 验证,
   不增删。
3. **臂**: q0 + centralized s17/s53/s89; checkpoint/contract 按 R279
   training matrix 验 hash; 不训练、不选 seed。
4. **plant**:
   `src/andes_rl_kundur/env/andes/andes_vsg_env_v4_weak_tie.py` 原样复用;
   只给 `tie_k` 传 2.5 或 3.0。不改 V4/storage/base env, 不改 corridor。
5. **runner**: 新建 `scripts/run_r287_weak_grid_stress.py` 作为薄适配器,
   复用并 hash 记录冻结的 `scripts/run_r286_weak_grid_td.py` 执行 kernel。
   适配器只覆盖 round/question/phase/k/shard/bootstrap/default paths;
   seal 中 current plan + adapter + parent kernel 都有 hash。禁止改 R286
   历史 runner, 否则其旧 seal 会失真。
6. **smoke**: seal 后运行 bank 第一场景 × q0 × k=3.0, 输出到
   `results/r287_weak_grid_stress/smoke/`, 保留且 hash; 检查 PFlow/TDS、
   tie r/x=3×nominal、300 步完整。
7. **全量**: 24×4×2=192 traces; 3 shards (项目并行上限), resume completed,
   不覆盖, 失败 trace 保留且不重试。
8. **端点/统计**: R286 原样 --
   `normalized_sync_loss_hz2`, `fast_inter_area_iae_hz_s`;
   hierarchical seed-then-scenario ratio bootstrap, 10000 resamples,
   seed 2026073001; nominal reference = sealed R279.
9. **守卫**: matrix complete, zero unaccounted failure, action audit,
   absolute storage/SOC/saturation/constraint, injection consistency,
   50-Hz controller semantics与60-Hz physical endpoints分离。
10. **范围**: corridor scaling 是 declared proxy, 不换算 SCR; location
    read 仅描述; 不写 LaTeX/正文/图/venue 文件; 不自动开训练。

## Outcomes (预注册)

- **SURVIVES**: k=2.5 和 3.0 上双主端点 point<0, point<=-2%, CI95 upper<0,
  且相对 nominal 增益 retention>=0.5。
- **DEGRADED**: 方向仍负但任一端点/级别不满足材料性或 retention<0.5。
- **COLLAPSES**: 任一级别端点反向, 或该级双端点材料性同时消失。
- **INVALID**: matrix/guard/injection/hash 失败, 或失败记录被删改/重跑。

任何分类都写 finding; INVALID 不产生正面 scientific claim。COLLAPSES
最多提出 retraining 问题, 本轮不得启动。

## Methodology

1. `prepare` 在 `traces/` 为空时写 seal, 绑定本 plan、adapter、R286 parent
   kernel、R279 bank/training/formal artifacts、R286 weak-tie env 和 package
   versions。
2. WSL smoke 跑第一封存场景的 q0 @ k=3.0; 完整 300 步、PFlow/TDS 和
   3× corridor injection 都过才启动 matrix。
3. 3 个 WSL worker 分片跑 192 traces; 每条完成即 canonical JSON +
   `.sha256`, 已完成只 resume, 失败保留且停该 worker。
4. analyse 读完整 matrix, 复用 R286/R279 的 endpoint summarizer、
   hierarchical bootstrap、location read 和 guard battery, 写 immutable
   summary/provenance。
5. 对比基准固定为
   `results/r279_formal_evaluation/formal_summary.json` 的 sealed nominal
   centralized-vs-q0 effect; R286 `results/r286_weak_grid_td/` 只作父边界
   解释, 不混进新 bootstrap。

## Cross-references

- Parent boundary: R286 / CLM-0645 / Q-0045.
- Nominal controller comparison: R279 formal, corrected interpretation R280 /
  CLM-0610.
- Formal bank: `results/r279_fresh_bank/formal_bank.json`.
- Project-facing output: `paper/sci_upgrade_survey/reports/R287.md` only;
  no manuscript source is writable.

## 资产保护

- 只读: R279 bank/training/formal artifacts, R286 results/runner/env, all
  checkpoints, paper/latex, LINE/JOURNAL/ARTIFACTS.
- 可新增/修改: Q-0046, 本 plan, R287 adapter + test,
  `results/r287_weak_grid_stress/`, R287 feed/claim/verdict, programme
  priority/archive, deterministic workflow tool/tests if本轮证实真实流程缺口。
- 结果一旦 seal 后, seal 列出的 source 不再改; 流程修复只能在结果分析和
  收尾后做, 且不能改变已封存结果。

## 流程验收观察项

1. 用户显式要求 experiment 时, `session_context.py` 是否仍被 manuscript
   priority 劫持。
2. programme 无 eligible question 时, 新授权能否在结果前形成可审计
   question + priority, 而不是绕开 gate。
3. 第二次弱联络扫描能否复用 kernel 而不复制 600 行 runner、不改历史
   source hash。
4. feed publication gate 是否能在无 LaTeX 时给出闭环结论。

只有观察到可复现摩擦才改流程; 不为本轮写新说明文档。

## 收尾

seal -> smoke -> 3-shard matrix -> analyse -> reserve claim -> feed +
publication gate -> feed_check -> claim -> verdict -> close Q/programme block
-> close round -> validate -> render -> tests -> PI 话原文进对话。严格不进入
manuscript branch。
