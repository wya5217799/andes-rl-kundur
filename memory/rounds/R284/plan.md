---
round: R284
state: completed
opened: '2026-07-29'
closed: '2026-07-29'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R284 plan — 左翼加密 (R282 对称补全, q∈[-0.25,-0.1875])

**Status**: ACTIVE
**Opened**: 2026-07-29
**Driver**: R282 确认右翼 U 型上翘为真结构后, R282 verdict 给 PI 留了口
子: 左翼 (q→-0.25) 未加密, ζ-q 图左右不对称会成为审稿人问题. R281 左翼
5 点单调 (0.01880→0.03023), 无异常迹象, 但点距 0.0625 比右翼加密后的
0.0125 粗 5 倍. 用户 2026-07-29 指令 "启动所有剩下的实验" 启动.
**Parent**: CLM-0615, CLM-0625, memory/rounds/R282/verdict.md,
probes/r282_eig_upturn.py

## TL;DR

冻结契约全部沿用 R281/R282 (plant / 映射 / 守卫 / 识别规则), 在
q ∈ {-0.2000, -0.2125, -0.2250, -0.2375} 补 4 个 EIG 点, 加 R281 已有的
-0.1875 / -0.25 两端, 用与 R282 相同的连续性度量 (余弦 ≥0.9 且
|Δf|<0.05 Hz) 验证左翼是否同样平滑连续. 低成本对称保险.

## 冻结契约 (先冻后算)

1. **plant / 映射 / 工作点**: 与 R281/R282 完全相同
   (`AndesMultiVSGEnvV4._build_system()` 原样构建; M_i(q) =
   200+600·(0.25+q·[1,1,-1,-1]); 潮流收敛点线性化). 不改任何 env 代码.
2. **加密网格** (4 点, 先冻): q ∈ {-0.2000, -0.2125, -0.2250, -0.2375},
   落在 R281 已测端点 -0.1875 与 -0.25 之间 (等距 0.0125).
3. **模态识别规则**: 与 R282 相同, 脚本内 (共轭对合并 → max
   |P_a1−P_a2|), 不重调.
4. **连续性度量** (与 R282 同, 先冻): 相邻 q 点 (含 R281 的 -0.1875/-0.25)
   参与向量余弦 ≥ 0.9 且 |Δf| < 0.05 Hz. R281 两点数据从
   results/r281_eig_mechanism/summary.json 只读取出.
5. **守卫** (同 R281): G4 合约 (M=0.1, D=0), 零和 1400, PFlow 收敛.

## Outcomes (预注册判定树)

- **LEFT-FLANK-SMOOTH**: 5 对相邻全连续且 ζ 在 [-0.25,-0.1875] 上平滑
  单调 → 左翼无隐藏结构; 出 finding claim, 手稿 ζ-q 图左右对称加密完毕.
- **LEFT-FLANK-STRUCTURE**: 全连续但 ζ 非平滑单调 (出现局部结构) → 出
  finding claim, 手稿机理段需如实补一句左翼结构.
- **INCONCLUSIVE**: 任一点识别失败或跳支 → 保留现有措辞, 记 open thread.
- 守卫破 → INVALID, 结果不进任何 claim 与手稿.

## 资产保护契约

- 不改 `src/andes_rl_kundur/env/andes/*`, `train.py`, 不改手稿, 不动 V4
  ckpt 命名空间.
- 新增仅限: `probes/r284_eig_left_flank.py`,
  `results/r284_eig_left_flank/*`, `paper/sci_upgrade_survey/reports/R284.md`
  (feed), 本轮 memory 实体.
- R281 summary.json 只读引用 (-0.1875/-0.25 两点), 不重跑.

## Methodology

1. WSL `/home/wya/andes_venv/bin/python`, ANDES 2.0.0.
2. `probes/r284_eig_left_flank.py` (import `probes/eig_alloc_common.py`):
   冻结 plant → 4 点设 GENCLS.M → 守卫 → PFlow → EIG → 共轭对合并 →
   脚本内识别 → 连续性度量 (对 R281 两端点) → summary.json +
   provenance.json.
3. 对照预注册判定树出 verdict; feed 按 experiment-report 技能契约写.
