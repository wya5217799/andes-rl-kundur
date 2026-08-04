---
round: R281
state: completed
opened: '2026-07-29'
closed: '2026-07-30'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R281 plan — 差动惯量分配 → 区间模态阻尼机理门 (Q-0042)

**Status**: ACTIVE
**Opened**: 2026-07-29
**Driver**: SCI 扩展版的机理段需要一个被验证实验撑住的"为什么"; 本轮用冻结模型的特征值分析回答差动分配 q 是否实质改变区间模态阻尼比, 动笔前先过门
**Parent**: CLM-0610, Q-0042, paper/sci_upgrade_survey/REPORT.md (2026-07-29 调研 + idea-evaluator 判定)

## TL;DR

在 R279/R280 冻结的 V4 改造 Kundur 系统上做 ANDES EIG 线性化, 沿冻结动作模态
[1,1,-1,-1] 静态扫 q ∈ [-0.25, +0.25], 提取区间模态阻尼比 ζ(q) 与频率 f(q).
过门标准: |ζ(+0.25) − ζ(−0.25)| / |ζ(0)| ≥ 5% 且方向与学习控制器实际利用的
有益方向一致. 不训练, 不跑新时域库, 不改手稿.

## Snapshot at plan-time (oracle as of 2026-07-29)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0041 closed-positive @ R280, by CLM-0610 — Do matched causal and centralized baselines explain the R278 shared-policy signal?
- Q-0038 closed-negative @ R278, by CLM-0600 — Does one learned zero-sum inertia allocator outperform the frozen reference on unseen disturbances?
- Q-0040 closed-positive @ R277, by CLM-0595 — Is there an attainable disturbance-adaptive differential-inertia margin above the sealed classical reference?

## 冻结契约 (先冻后算)

1. **plant**: 与 R279/R280 完全相同的 V4 构建 (kundur_full.xlsx + Bus12/14/15/16
   + 4×GENCLS VSG + 风机代理 M=0.1 + IEEEG1 + EXST1 DAE-active +
   ZERO_G4_INERTIA=True). 经 `AndesMultiVSGEnvV4._build_system()` 原样构建,
   不改任何 env 代码.
2. **动作→惯量映射** (来自 R278 冻结合约 + base_env 写入逻辑, 已读源码核实):
   M_i(q) = 200 + 600·(0.25 + q·pattern_i), pattern=[1,1,-1,-1] 对应
   VSG buses [12,16] (area1, 正号) 与 [14,15] (area2, 负号). D 冻结 100.
   q=0 → 全部 350; q=+0.25 → area1=500, area2=200; 总和恒 1400 (零和).
3. **q 网格** (9 点, 先冻): {-0.25, -0.1875, -0.125, -0.0625, 0, +0.0625,
   +0.125, +0.1875, +0.25}. 工作点: 潮流收敛点 (pulse 前稳态).
4. **区间模态识别规则** (先冻): 在频率 ∈ [0.2, 1.5] Hz 的机电模态中, 用
   参与因子 (omega 状态) 计算 area1 (GENROU 1,2 + GENCLS@12,16) 与
   area2 (GENROU 3,4 + GENCLS@14,15) 参与量之差 |P_a1 − P_a2|,
   取差值最大的模态为区间模态; 若该模态在 9 个网格点上识别不一致,
   记识别失败 flag 并保留全部模态表.
5. **有益方向 b** (先冻, 测量不拟合): b = sign(R280 正式库 192 条封存轨迹中
   active 窗口内执行 q 的均值), 从 results/ 封存产物读出后记入本轮 seal.
6. **开发级异质轴** (只作 probe, 不进正式结论): VSG baseline M0 ∈
   {100, 200, 300} × q ∈ {0, ±0.25}, 探测分配敏感度随聚合惯量的变化,
   用于防御 F2 (与已知异质性结论的重叠度).

## Methodology

1. WSL `/home/wya/andes_venv/bin/python`, ANDES 2.0.0. 冒烟已过: base case
   EIG 52 特征值可用 (probes/r281_eig_smoke.py).
2. 脚本 `probes/r281_eig_sweep.py`: 经 env 构建冻结 plant → 按契约 2 设
   GENCLS.M → PFlow → EIG → 记录全部模态 (f, ζ) + 参与因子 + 识别结果.
3. 9 点主扫描 → ζ(q), f(q) 曲线 + 单调性/跨度统计 → 方向 b 对照.
4. 开发级异质 probe (契约 6).
5. 全部数值 + 契约哈希写 `results/r281_eig_mechanism/` (summary.json +
   provenance.json + seal).

## Outcomes (预注册量级判定)

主端点: 区间模态阻尼比 ζ(q) 在 9 点网格上的跨度
S = |ζ(+0.25) − ζ(−0.25)| / |ζ(0)|.

- **S ≥ 5% 且单调且方向=b** → MECHANISM-CONFIRMED: 手稿机理段按 (b) 半解析写,
  ζ(q) 映射图 + 方向一致性入正文.
- **1% ≤ S < 5%, 或单调破** → MECHANISM-PARTIAL: 机理段降级为有界经验陈述,
  不声称分配调控阻尼.
- **S < 1%** → MECHANISM-ABSENT: SCI 方案降级 (a) 纯经验轨道, 调研报告 §7-C1
  失去机理支柱, 需回 idea-evaluator 重议.
- 模态识别在网格上不一致 / 零和破 / G4 零化破 / 哈希错 → INVALID, 结果不进
  任何手稿与 claim.

对照证据 (只读): R280 正式库 192 条轨迹封存产物 (results/ 下 R279/R280
sealed summary), 仅用于读出有益方向 b 与增益符号, 不用于拟合任何参数.

## Gate (预注册判定)

- **MECHANISM-CONFIRMED**: 主端点跨度 |ζ(+0.25)−ζ(−0.25)|/|ζ(0)| ≥ 5%,
  ζ(q) 在网格上单调, 且 ζ 随 b·q 增大而增大 (方向与 R280 增益符号一致).
- **MECHANISM-PARTIAL**: 映射真实但弱 (跨度 < 5%) 或非单调; 手稿机理段降级
  为有界经验陈述.
- **MECHANISM-ABSENT**: ζ 对 q 不敏感; SCI 方案降级 (a) 纯经验轨道,
  inertia-placement 框架失去机理支柱.
- **INVALID**: 线性化/工作点/模态识别/provenance 契约失败 (含 G4 零化,
  零和, 哈希核对任一不过).

## 资产保护契约

- 不改 `src/andes_rl_kundur/env/andes/*`, `train.py`, `paper_grade_axes.py`,
  不改 manuscript, 不动 V4 ckpt 命名空间.
- 新增仅限: `probes/r281_eig_*.py`, `results/r281_eig_mechanism/*`,
  本轮 memory 实体.
- env 侧 R274 慢 droop+PI 不在 ANDES DAE 内 (作用于慢共模回路), 本轮线性化
  不含它 — 记为 scope limit, 不声称覆盖共模恢复回路.

## Cross-references

- CLM-0610 (CENTRALIZED-EXPLANATION-SUFFICIENT) — 增益测量来源
- CLM-0595/0600 (R277/R278) — 差动 oracle 与 pilot 边界
- Q-0042 — 本轮关闭对象
