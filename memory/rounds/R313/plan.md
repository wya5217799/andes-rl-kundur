---
round: R313
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R313 plan — sealed coupling-retaining predictor holdout

**Opened**: 2026-08-03
**Driver**: 用全新幅值和工况检验 R312 拟合的 common/differential 脉冲响应 predictor。
**Parent**: CLM-0770; Q-0069

## TL;DR

只用 R312 的 27 条有效轨迹拟合 25-step 凸插值响应模板；随后在两个未见
工况、两个未见幅值上跑 34 条新物理轨迹。完整模型和 block-diagonal
消融只差 measured cross block。到 PASS、NO-GO 或 INVALID 即停；不写控制器，
不建分布式智能体，不训练 MARL。

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0069 [opened R312] Can a coupling-retaining predictor fitted only on the valid R312 bank predict separately sealed unseen pulse amplitudes and operating conditions within prospective common/differential error bounds?

## Recently Closed (last 3)

- Q-0068 closed-positive @ R312, by CLM-0770 — Can a separately sealed fresh 27-trace Stage-1 bank using the R309 two-phase solver and R311 record-guard seam pass the full authority, linearity, coupling, and EVAL integrity contract?
- Q-0067 closed-positive @ R311, by CLM-0765 — Can one explicit Stage-1-to-EVAL record-guard synthesis pass a small source-bound adapter canary without changing source records, scientific thresholds, or the R310 verdict?
- Q-0066 closed-negative @ R310, by CLM-0760 — Can a fresh two-phase-solver Stage-1 bank execute all signed common and edge active-power probes across OP0--OP2 with valid authority, local linearity, and measured common-differential coupling?

## Methodology

### 训练输入和 predictor

- 训练真源只准 `results/r312_model_first_stage1/run_manifest.json` 的 27 条
  hash-verified 记录；同时要求 R312 `analysis.classification=STAGE1-PASS`。
- 每个 OP、每个 common/edge 坐标取正负中心差，形成 0.05 system-p.u.
  的 25-step common/differential 响应模板。预测按幅值线性缩放。
- 工况预测只用预注册 barycentric 权重插值训练模板。验证 zero trace 只用于
  计算真实增量，不进入拟合、权重或模型选择。
- full arm 保留四个输出坐标；block-diagonal arm 对 common 输入清零
  differential 输出，对 edge 输入清零 common 输出；其余字节级相同。

### 全新 holdout bank

- HP0 = `0.50 OP0 + 0.25 OP1 + 0.25 OP2`：device M/D=200/100，
  tie scale=1.25，SOC=0.50。
- HP1 = `0.20 OP0 + 0.60 OP1 + 0.20 OP2`：device M/D=180/90，
  tie scale=1.20，SOC=0.42。
- 每点一条 zero；common、edge-0/1/2 各跑 ±0.025 和 ±0.065 system p.u.；
  5 个 active sample + 20 个 recovery sample，共 34 条新轨迹。
- 物理 plant、60-Hz base、two-phase solver、拓扑、ESD1 路径、25-step
  horizon 和 Stage-1 execution guards 不变。R312 trace 不得进入验证 bank。

### 冻结指标和 EVAL

- 每条 forced-response total NRMSE <= 0.15；peak-magnitude relative error
  <= 0.10；peak timing error <= 0.2 s。
- cross-block 估计量按每条 cross output L2 error 聚合。full 相对 block 的
  aggregate squared-error reduction >= 20%，且至少 75% 记录严格更好；
  cross signal 必须可观测。该门只识别 retained cross block 的信息价值。
- 全 34 条源记录和 sidecar 验证后才运行 EVAL；只转换 24 条 edge 记录。
  EVAL-v2 profile=`vector_power`，1-s active window，10000 bootstrap，
  seed=2026080313；状态必须保持 `EXTERNAL_AUTHORITY_REQUIRED`。
- 不用 EVAL 调参。EVAL 不拥有 feed、claim 或 verdict 权威。

### Comparison identifiability gate

- **Decision**: ALLOW。
- **Executed comparison**: 同一 R312 训练 bank、同一 HP0/HP1 验证 bank、
  同一输入输出坐标、插值权重、幅值缩放、预算和指标；只开/关 cross block。
- **Identified estimand**: 这一具体 25-step 凸插值模板中，retained cross
  block 对 held-out cross-output prediction error 的增量价值。
- **Allowed claim**: 若过门，只能说该实现于这一 modified-Kundur、固定拓扑、
  小脉冲凸包内 bank 上满足冻结误差界且 retained cross block 有增量价值。
- **Stay-out**: predictor 类普适优越性、控制器效果、稳定性保证、分布式执行、
  多智能体/MARL 价值、拓扑或部署泛化。

### 小步试错规则

- INVALID：只开同一失败原因的最小 execution/EVAL canary；不改科学阈值。
- VALID NO-GO 且只有 0.065 幅值层系统失败：允许新 round 加一个独立
  development amplitude，单因子测试 quadratic amplitude term，再用新 holdout。
- VALID NO-GO 且只有一个工况层系统失败：允许新 round 加一个独立
  development operating point，单因子测试 local/simplex interpolation，再用新 holdout。
- cross arm 无增量价值、多个原因混合或无法唯一归因：停止 predictor 优化，
  回到模型结构诊断；禁止算法 sweep。
- PASS：Q-0069 关闭，但仍不授权 controller/MARL；下一轮先补动态/模态 reduction
  和 mismatch-set 门。

## Gate

- `INVALID-PREDICTOR-VALIDATION`：seal/source/model provenance、34 条执行、
  24 条 EVAL 完整性任一失败；不解释 predictor 指标。
- `PREDICTOR-NO-GO`：执行有效，但任一 total NRMSE/peak/timing/cross-value
  科学门失败。
- `PREDICTOR-PASS`：所有执行门、逐条响应界和 cross-value 门全过。
- 结果后不改工况、幅值、模型阶次、阈值、EVAL metadata 或判定树。

## 资产保护契约

- 不变：R312 记录/分析、plant、拓扑、solver、动作坐标、物理 guard、
  EVAL 权威边界、no-controller/no-training ceiling。
- 新增：纯 predictor 公共模块及测试、R313 create-only adapter、seal、冻结模型、
  34 条物理记录、24 条 guarded EVAL views、analysis、provenance、feed 和 claim。
- 禁止：改写 R312；用 holdout 拟合/选模型；结果驱动 rerun；controller、reward、
  distributed runtime、agent 或 neural training。

## Cross-references

- Stage-1 prerequisite: CLM-0770.
- Question: Q-0069.
- Manuscript gate: `paper/decoupling_marl_model_first/LINE.md`.
