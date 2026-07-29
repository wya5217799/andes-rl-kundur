---
round: R285
state: completed
opened: '2026-07-29'
closed: '2026-07-29'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R285 plan — Q-0044 hybridization 区绘图 (低惯量模态混杂区)

**Status**: ACTIVE
**Opened**: 2026-07-29
**Question**: Q-0044 (programme rank 140, P1_residual_mechanism, 已授权)
**Driver**: R283 惯量轴在 M0=100/q=−0.25 与 M0=150/q=±0.25 触发分支串线
识别 flag (CLM-0630): 低聚合惯量区里 max-contrast 规则抓不到干净区间
模态. C2 段需要知道梯度到底在哪里可测量. 用户 2026-07-29 指令启动.
**Parent**: CLM-0630, memory/rounds/R283/execution_amendment_20260729.md,
probes/eig_alloc_common.py, probes/r283_branch_analysis.py

## TL;DR

冻结 plant 上铺 20 格地图: M0 ∈ {100,125,150,175} × q ∈
{-0.25,-0.125,0,+0.125,+0.25}. 14 格新算, 6 格 (M0∈{100,150} 端点行)
从 R283 只读复用, 3 个 R283 flag 格为归因重算 (须 1e-6 复现 R283 识别值).
每格过分支有效性筛 (与 R283 同), 画 valid/flag 边界, 并对每个 flag 格
归因: 规则抓到了什么 (模态族), 最近的类区间模态在哪.

## 冻结契约 (先冻后算)

1. **plant / 映射 / 工作点**: 与 R281/R282/R283 完全相同. 不改 env 代码.
2. **网格** (20 格, 先冻): M0 ∈ {100,125,150,175} × q ∈
   {-0.25,-0.125,0,+0.125,+0.25}. 新算 14 格; R283 只读复用 6 格
   (M0∈{100,150} × q∈{-0.25,0,+0.25}); 归因重算 3 格 (M0=100/q=−0.25,
   M0=150/q=±0.25, 记录完整合并模态列表, 识别值须 |Δζ|<1e-6 复现
   R283, 否则 INVALID).
3. **识别与有效性筛**: 与 R282/R283 完全相同 (共轭对合并 → max
   |P_a1−P_a2|; 级内 q=0 锚定, 端点判余弦 ≥0.9 且 |Δf|<0.05 Hz; 跨级
   q=0 链只判余弦 ≥0.9). 本轮不引入新识别规则 (mode-tracking 延续规则
   是后续修正案事项).
4. **归因分类器** (先冻): 对 flag 格记录 (a) 规则所抓模态的频率/阻尼/
   对比度/前二参与机; (b) 频带内对比度前三的模态同样信息; (c) 归类:
   前二参与机含 VSG → "VSG-local-leaning"; 对比度 < 0.3 →
   "non-area-contrasted"; 其余 → "GENROU-area-leaning". 归因只描述
   测量结果, 不做机理声称.
5. **守卫** (同 R283): G4 合约, 零和 = 1400·(M0/200), PFlow 收敛, 每点
   必过, 不过记该点 INVALID-point. 锚点守卫: 3 个归因重算格 1e-6 复现
   R283.
6. **范围**: 不训练, 不跑时域, 不改拓扑, 不动手稿; 无泛化声称.

## Outcomes (预注册判定树)

- **ZONE-CHARTED**: 20 格全部完成有效性分类, valid/flag 边界成形,
  每个 flag 格归因记录完整 → 出 finding claim, Q-0044 closed-positive.
- **ZONE-PARTIAL**: 边界可辨但 (i) 某些 flag 格频带内完全无类区间模态
  可供归因, 或 (ii) ≤25% 格 INVALID-point → 出 finding claim 但有界,
  Q-0044 closed-partial.
- **INVALID**: 归因重算格未 1e-6 复现 R283 (合约漂移), 或 >25% 格
  INVALID-point → 结果不进任何 claim 与手稿.

## 资产保护契约

- 不改 `src/andes_rl_kundur/env/andes/*`, `train.py`, 不改手稿, 不动 V4
  ckpt 命名空间.
- `probes/eig_alloc_common.py` 允许一处后向兼容扩展: `run_eig_at(...,
  keep_modes=False)` 可选返回合并模态列表 (既有调用方行为不变; R283/
  R284 已封盘结果不受影响).
- 新增仅限: `probes/r285_hybridization_map.py`,
  `probes/r285_zone_analysis.py`, `results/r285_hybridization_map/*`,
  `paper/sci_upgrade_survey/reports/R285.md` (feed), 本轮 memory 实体.

## Methodology

1. WSL `/home/wya/andes_venv/bin/python`, ANDES 2.0.0.
2. `probes/r285_hybridization_map.py`: 17 点 EIG (14 新 + 3 归因重算,
   keep_modes=True 记录合并模态) + 6 格 R283 只读 → summary.json +
   provenance.json.
3. `probes/r285_zone_analysis.py` (分析进脚本): 读 summary → 逐格有效性
   筛 → 边界图 → flag 格归因 (分类器) → 判定分类 → zone_analysis.json.
4. 对照判定树出 verdict; feed 按 experiment-report 技能契约写; Q-0044
   按结果置 closed-*; programme 块归档, 列表回 [].
