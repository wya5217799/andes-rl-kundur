---
round: R314
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R314 plan — local/simplex predictor repair on a new holdout

**Opened**: 2026-08-03
**Driver**: 用一个新增 development 工况修复 R313 的 operating-point interpolation NO-GO。
**Parent**: CLM-0770; CLM-0775; Q-0070

## TL;DR

R312 OP0--OP2 保持原训练真源；把已看过的 R313 HP1 仅作为第四个 development
点，不再当验证。用两个固定 local simplex 预测两个全新工况，执行与 R313 同构
的 34 条 bank。阈值、cross 消融和 EVAL 不变；到 PASS、NO-GO 或 INVALID 即停，
不写控制器、分布式智能体或 MARL。

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0070 [opened R313] Can one local/simplex predictor using R313 HP1 only as an added development operating point meet the unchanged response bounds on a newly sealed untouched operating-condition bank?

## Recently Closed (last 3)

- Q-0069 closed-negative @ R313, by CLM-0775 — Can a coupling-retaining predictor fitted only on the valid R312 bank predict separately sealed unseen pulse amplitudes and operating conditions within prospective common/differential error bounds?
- Q-0068 closed-positive @ R312, by CLM-0770 — Can a separately sealed fresh 27-trace Stage-1 bank using the R309 two-phase solver and R311 record-guard seam pass the full authority, linearity, coupling, and EVAL integrity contract?
- Q-0067 closed-positive @ R311, by CLM-0765 — Can one explicit Stage-1-to-EVAL record-guard synthesis pass a small source-bound adapter canary without changing source records, scientific thresholds, or the R310 verdict?

## Methodology

### Development 输入和 local predictor

- R312 27 条记录保留；额外只读 R313 HP1 的 17 条记录（zero + 四坐标、
  双符号、0.025/0.065 双幅值）。R313 HP0 永不进拟合。
- HP1 每个坐标先按幅值归一到 0.05 system p.u.，分别做正负中心差，再对两
  幅值的单位响应取等权平均。仍是线性幅值缩放，不加 quadratic term。
- augmented model 共 44 条 development 记录。验证 zero trace 仍只做真实增量
  参考，不进入拟合或 simplex 选择。
- local full arm 保留全部 common/differential 输出；local block arm 只清零
  common↔differential cross 输出，其余数据、权重、预算、指标一致。

### 两个全新 local-simplex holdout

- HQ0 simplex=`OP0,OP1,HP1`，权重 `0.20,0.30,0.50`：device M/D=
  175/87.5，tie scale=1.10，SOC=0.40。
- HQ1 simplex=`OP0,OP2,HP1`，权重 `0.20,0.30,0.50`：device M/D=
  205/102.5，tie scale=1.40，SOC=0.52。
- 每点一条 zero；common、edge-0/1/2 各跑 ±0.025 和 ±0.065 system p.u.；
  5 active + 20 recovery，共 34 条全新物理轨迹。
- 幅值已在 R313 development 出现，因此本轮只声称新工况验证，不声称新幅值
  泛化。plant、solver、拓扑、动作与物理 guard 完全沿用 R313。

### 冻结门和 EVAL

- total NRMSE <=0.15；peak-magnitude relative error <=0.10；peak timing
  error <=0.2 s；逐条最坏值判定。
- full 相对 matched block 的 aggregate cross squared-error reduction >=20%，
  cross-record win fraction >=75%，cross signal 可观测。
- 34 条源记录和 sidecar 全部验证后才运行 24 条 edge view 的 EVAL；profile
  `vector_power`，1-s window，10000 bootstrap，seed=2026080314；仍是
  `EXTERNAL_AUTHORITY_REQUIRED`。
- outcome 后不改 development 集、simplex、holdout、阈值或 EVAL metadata。

### Comparison identifiability gate

- local full versus local block：`ALLOW`。唯一差异是是否保留 cross 输出；
  identified estimand 仍是本实现的 held-out cross-output prediction error。
- R313 global versus R314 local：`QUALIFY`。R314 同时增加 HP1 development 数据
  并改变为 local simplex，只能称“组合修复”，不得归因给 local rule 或数据量
  单独一项。
- allowed claim 和 stay-out 与 R313 相同：固定拓扑、有限时域、小脉冲、具体
  predictor；禁止 predictor 类、controller、agent、MARL、泛化或部署结论。

### 小步试错规则

- INVALID：只开同一失败原因的 execution/EVAL canary；科学门不动。
- VALID NO-GO 且只有 0.065 幅值层失败：允许一个新 development amplitude
  的单因子 nonlinearity diagnosis，再用新 holdout。
- VALID NO-GO 且两幅值同向、只在一个 simplex 失败：停止继续密集加点，转向
  显式 descriptor/LTV 动态 reduction；不得做 interpolation sweep。
- cross 无增量或多原因混合：停止该 template 路线，回到结构模型诊断。
- PASS：关闭 Q-0070，但 controller/MARL 仍不授权；下一门是动态/模态 reduction
  与 mismatch-set coverage。

## Gate

- `INVALID-LOCAL-PREDICTOR-VALIDATION`：seal/source/model provenance、34 条执行
  或 24 条 EVAL 完整性任一失败；不解释 predictor 指标。
- `LOCAL-PREDICTOR-NO-GO`：执行有效，但任一 NRMSE/peak/timing/cross-value 门失败。
- `LOCAL-PREDICTOR-PASS`：所有执行门、逐条响应界和 cross-value 门全过。

## 资产保护契约

- 不变：R312/R313 artifacts、physical plant、拓扑、solver、动作坐标、34-trace
  bank 结构、误差阈值、matched cross ablation、EVAL 权威与 no-training ceiling。
- 新增：HP1 development adapter、local/simplex predictor 测试、R314 create-only
  adapter、seal、模型、34 条新记录、EVAL、analysis、provenance、feed、claim。
- 禁止：改写 R312/R313；使用 R313 HP0 或任何 R314 holdout 拟合；阈值放宽；
  结果选择 rerun；controller、distributed runtime、agent、reward 或训练。

## Cross-references

- Stage-1 prerequisite: CLM-0770.
- Global predictor NO-GO and repair branch: CLM-0775.
- Question: Q-0070.
