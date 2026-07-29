---
round: R283
state: completed
opened: '2026-07-29'
closed: '2026-07-29'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R283 plan — Q-0043 电网强度扫描 (惯量轴 + 联络线电抗轴)

**Status**: ACTIVE
**Opened**: 2026-07-29
**Question**: Q-0043 (programme rank 130, P1_residual_mechanism, 已授权)
**Driver**: R281 开发级 probe 见 "总惯量减半 → 分配敏感度翻倍 (+53%@+0.25)",
但仅 M0∈{100,300} 两点、且 M0=100/q=−0.25 识别断点; C2 弱电网段需要
一条实测的强度-敏感度梯度. SCI 手稿线 C1 主轴的验证段取决于此.
**Parent**: CLM-0615, CLM-0625, memory/rounds/R281/verdict.md,
memory/rounds/R282/verdict.md, probes/r282_eig_upturn.py

## TL;DR

冻结 plant 与 R281/R282 完全相同, 扫两条预注册的强度轴: A 惯量轴
M0∈{100,150,200,250,300} × q∈{0,±0.25} (15 点); B 电气轴 (SCR 代理)
联络走廊电抗 k∈{1.0,1.5,2.0} × q∈{0,±0.25} (9 点). 每级算敏感度
S = |ζ(+0.25)−ζ(−0.25)|/|ζ(0)| (R281 span 定义), 定性比较跨级梯度,
不拟合参数. 识别规则用 R282 脚本内版本, 不重调.

## 冻结契约 (先冻后算)

1. **plant / 映射 / 工作点**: 与 R281 完全相同 (经
   `AndesMultiVSGEnvV4._build_system()` 原样构建; M_i(q) =
   200+600·(0.25+q·[1,1,-1,-1]); 潮流收敛点线性化). 不改任何 env 代码.
2. **A 轴 (惯量强度)**: 执行惯量向量整体乘 s=M0/200,
   M0 ∈ {100, 150, 200, 250, 300}, q ∈ {0, −0.25, +0.25}. 15 点.
   M0=200 行是 R281 复现锚点.
3. **B 轴 (电气强度, SCR 代理 — 声明式定义)**: 联络走廊 = 7↔8 三回
   长线路 Line_4/Line_5/Line_6 (kundur_full.xlsx, r≈0.022, x≈0.22,
   等值 x≈0.0733, 占区间走廊电抗绝对主导; 8↔9 两回 x≈0.02 不动).
   k ∈ {1.0, 1.5, 2.0} 同比例缩放这三回的 r 与 x (r/x 不变), 充电 b
   不动 (对机电模态影响可忽略, 声明性简化). k 越大 = 电网越弱
   (SCR 越低). 每个 k 在新潮流工作点线性化 (先冻声明). k=1.0 行是
   R281 复现锚点.
4. **模态识别规则** (与 R282 相同, 脚本内, 不重调): 频率 ∈ [0.2,1.5] Hz
   机电模态, 先合并共轭对 (|Δf|<1e-9 且 |Δreal|<1e-9), 再按 omega 状态
   参与因子算 |P_a1−P_a2| (area1=GENROU1,2+GENCLS@12,16;
   area2=GENROU3,4+GENCLS@14,15), 取最大者为区间模态. 识别失败记 flag,
   该点排除出梯度判定.
5. **敏感度指标** (先冻): 每强度级 S = |ζ(+0.25)−ζ(−0.25)| / |ζ(0)|,
   与 R281 span 同定义. 跨级比较只定性 (scope limit: 不拟合参数逼梯度).
6. **守卫**: G4 合约 (M=0.1, D=0) 每点必过; 零和守卫按级重声明 —
   A 轴每级零和总额 = 1400·(M0/200) (同一零和分配原则在缩放后的聚合
   水平上; 非放松, 是随轴定义), B 轴 = 1400; PFlow 每点必收敛
   (B 轴每个 k 重新潮流). 锚点守卫: M0=200 行与 k=1.0 行的 ζ 必须
   复现 R281 锚值 (ζ(0)=0.01947, ζ(−0.25)=0.03023, ζ(+0.25)=0.02132,
   |Δζ|<1e-6), 否则合约漂移 → INVALID.
7. **范围**: 不训练, 不跑新时域库, 不改拓扑, 不动手稿; 不做拓扑/稳定
   证书/跨仿真/HIL 声称. env 侧 R274 慢 droop+PI 不在 DAE 内 (同 R281).

## Outcomes (预注册判定树)

- **STRENGTH-GRADIENT-CONFIRMED**: ≥1 条轴全部点识别成功, 该轴跨级
  S_max/S_min ≥ 1.5 且趋势方向一致 → 出 finding claim, C2 弱电网段按
  实测梯度写.
- **STRENGTH-GRADIENT-PARTIAL**: (i) 较强轴 S 比 ∈ [1.2,1.5); 或
  (ii) S 比 ≥1.5 但该轴有非锚点识别失败 (剩余级仍可判定); 或 (iii) 一轴
  不可判定而另一轴 CONFIRMED → 出 finding claim 但有界措辞, C2 段收窄.
- **STRENGTH-GRADIENT-ABSENT**: 两轴 S 比 < 1.2 且全部点识别成功 →
  出 finding claim, C2 段收窄回 R281 开发级 probe 表述 (授权块
  stop_when 第 3 条).
- **INVALID**: 任一守卫破 (G4/零和/PFlow/锚点失配) 或两轴 S 均不可测量
  → 结果不进任何 claim 与手稿.

## 资产保护契约

- 不改 `src/andes_rl_kundur/env/andes/*`, `train.py`, `paper_grade_axes.py`,
  不改手稿, 不动 V4 ckpt 命名空间.
- 新增仅限: `probes/eig_alloc_common.py` (R281/R282 第三次复用的共用函数
  抽取: build_frozen_plant / executed_m / machine_state_indices /
  merge_conjugate_pairs / identify_interarea / cosine / sha256_file /
  run_eig_at 泛化), `probes/r283_strength_sweep.py`,
  `results/r283_strength_sweep/*`, `paper/sci_upgrade_survey/reports/R283.md`
  (feed), 本轮 memory 实体. 既有 r281/r282 脚本不回填改动.
- R281 summary.json 只读引用 (锚点比对), 不重跑.

## Methodology

1. WSL `/home/wya/andes_venv/bin/python`, ANDES 2.0.0.
2. `probes/r283_strength_sweep.py`: 冻结 plant → A 轴 15 点 (设 GENCLS.M
   ×s) → B 轴 9 点 (设 Line_4/5/6 r,x ×k → 重新 PFlow) → 每点守卫 →
   EIG → calc_pfactor → 共轭对合并 → 脚本内识别 → 每级 S → 锚点比对 →
   summary.json + provenance.json.
3. 对照预注册判定树出 verdict; feed 报告按 experiment-report 技能契约写;
   Q-0043 按结果置 closed-*; programme 块归档 RESEARCH_PROGRAM_CLOSED.md
   且列表回 [] (砍 1 后的新维护规则首次执行).
