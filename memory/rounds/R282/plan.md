---
round: R282
state: completed
opened: '2026-07-29'
closed: '2026-07-29'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R282 plan — U 型上翘真伪确认 (R281 后续, q∈[+0.1875,+0.25] 加密)

**Status**: ACTIVE
**Opened**: 2026-07-29
**Driver**: R281 verdict 留了口子: q=+0.25 端 U 型上翘破了全局单调,
判定只给 MECHANISM-PARTIAL. 上翘若是模态 hybridize 的识别 artifact,
CLM-0615 的"非全局单调"措辞就要修; 若是真物理, 措辞原样保留.
手稿机理段的诚实边界取决于此. 用户 2026-07-29 指令启动.
**Parent**: CLM-0615, memory/rounds/R281/verdict.md, probes/r281_eig_sweep.py

## TL;DR

冻结 plant / 守卫 / 识别规则全部沿用 R281 合约 (hash 11a4800123f48a33),
只在 q ∈ {0.2000, 0.2125, 0.2250, 0.2375} 补 4 个 EIG 点, 加上 R281 已有
的 0.1875 / 0.25 两端, 看上翘区间是平滑连续 (真) 还是识别跳支 (假).
流程改进: 模态识别这次进脚本 (R281 是离线临时做的, 不可复现).

## 冻结契约 (先冻后算)

1. **plant / 映射 / 工作点**: 与 R281 完全相同 (经
   `AndesMultiVSGEnvV4._build_system()` 原样构建; M_i(q) =
   200+600·(0.25+q·[1,1,-1,-1]); 潮流收敛点线性化). 不改任何 env 代码.
2. **加密网格** (4 点, 先冻): q ∈ {0.2000, 0.2125, 0.2250, 0.2375},
   落在 R281 已测端点 0.1875 与 0.25 之间 (等距 0.0125).
3. **模态识别规则** (与 R281 amendment 相同, 但这次写进脚本): 频率 ∈
   [0.2,1.5] Hz 机电模态, 先合并共轭对 (|Δf|<1e-9 且 |Δreal|<1e-9),
   再按 omega 状态参与因子算 |P_a1−P_a2| (area1=GENROU1,2+GENCLS@12,16;
   area2=GENROU3,4+GENCLS@14,15), 取最大者为区间模态.
4. **连续性度量** (先冻): 相邻 q 点 (含 R281 的 0.1875/0.25) 识别模态的
   参与向量余弦相似度 ≥ 0.9 且 |Δf| < 0.05 Hz → 连续; 否则记跳支 flag.
   R281 两点数据从 results/r281_eig_mechanism/summary.json 只读取出.
5. **守卫** (同 R281): G4 合约 (M=0.1, D=0), 零和 1400, PFlow 收敛,
   每点必过, 不过则该点记 INVALID.

## Outcomes (预注册判定树)

- **UPTURN-REAL**: 4 点全部连续 (无跳支) 且 ζ 在 [0.1875..0.25] 上平滑
  单调不减 → U 型是真实 plant 物理; CLM-0615 措辞原样保留, 本轮出
  finding claim 补强 (单调区间 [−0.25,+0.125] + 右端真实上翘).
- **UPTURN-ARTIFACT**: 区间内出现跳支 (余弦 < 0.9 或频率跳) 且跳支解释
  上翘 (原支 ζ 延续平缓走势, 新支被误识别) → 出 correction claim 修
  CLM-0615: "非全局单调"降级为"识别 artifact, 可识别分支内单调",
  手稿机理段措辞相应放宽.
- **INCONCLUSIVE**: 任一新点识别失败 (无清晰区间模态) 或守卫破 → 保留
  R281 有界措辞, 记 open thread, 不出新结论 claim.
- 守卫破 (G4/零和/PFlow) → INVALID, 结果不进任何 claim 与手稿.

## 资产保护契约

- 不改 `src/andes_rl_kundur/env/andes/*`, `train.py`, `paper_grade_axes.py`,
  不改手稿, 不动 V4 ckpt 命名空间.
- 新增仅限: `probes/r282_eig_upturn.py`, `results/r282_eig_upturn/*`,
  `paper/sci_upgrade_survey/reports/R282.md` (feed), 本轮 memory 实体.
- R281 summary.json 只读引用 (0.1875/0.25 两点 + 参与向量), 不重跑.

## Methodology

1. WSL `/home/wya/andes_venv/bin/python`, ANDES 2.0.0.
2. `probes/r282_eig_upturn.py`: 冻结 plant → 4 点设 GENCLS.M → 守卫 →
   PFlow → EIG → calc_pfactor → 共轭对合并 → 脚本内识别区间模态 →
   连续性度量 (对 R281 两端点) → summary.json + provenance.json.
3. 对照预注册判定树出 verdict; feed 报告按 experiment-report 技能契约写.
