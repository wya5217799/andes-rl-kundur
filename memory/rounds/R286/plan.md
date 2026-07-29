---
round: R286
state: completed
opened: '2026-07-29'
closed: '2026-07-29'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R286 plan — Q-0045 弱联络走廊时域存活 + 扰动位置依赖

**Status**: ACTIVE
**Opened**: 2026-07-29
**Question**: Q-0045 (programme rank 150, P1_residual_mechanism, 已授权)
**Driver**: SCI 扩展 C2 弱网段目前只有线性化证据 (R283 CLM-0630 强度
梯度, R285 CLM-0640 可测区边界). 时域控制增益 (CLM-0610: centralized
vs q0 双主端点 −24.35% / −17.04%) 只在标称联络强度 k=1 测过. 弱走廊
下增益是否存活未知; 封存库横跨 4 个扰动位置, 增益是否位置artifact
也未读. 用户 2026-07-29 指令启动全部剩余实验.
**Parent**: CLM-0610, memory/rounds/R279/verdict.md,
scripts/run_r279_formal.py, probes/eig_alloc_common.py,
results/r279_fresh_bank/formal_bank.json

## TL;DR

零训练迁移评估: 冻结的 R279 臂 (q0 + centralized s17/s53/s89, 共 4 臂)
在同一封存 24 场景库上重跑, 唯一变化是 7↔8 三回联络走廊 (Line_4/5/6)
r/x 乘 k ∈ {1.5, 2.0}. 每 k 级对 centralized vs q0 做配对双主端点对比,
过预注册判定树. 另把名义 traces (R279 既有, 只读) 与新 traces 按
location 分组读效应量 (纯描述). 共 24×4×2 = 192 条 TDS, 先冒烟后全量.

## 冻结契约 (先冻后跑)

1. **场景库**: `results/r279_fresh_bank/formal_bank.json` 只读, 加载时
   `load_scenario_bank` 验 SHA256 (与 R279 同 hash). 不改库, 不加场景.
2. **臂** (4, 先冻): `q0` (ZeroResidualController) + `centralized_s17` /
   `centralized_s53` / `centralized_s89` (ckpt 来自
   `results/r279_matched_training/centralized_s{seed}/final.pt`, 加载验
   hash 同 R279). 不加 shared 臂, 不加 causal 臂 (causal 是守卫对照臂,
   本轮问题是 centralized 增益存活).
3. **弱网注入**: 新文件
   `src/andes_rl_kundur/env/andes/andes_vsg_env_v4_weak_tie.py` 定义
   `AndesMultiVSGEnvV4WeakTie(AndesMultiVSGEnvV4Storage)`, 类属性
   `TIE_K`, 覆写 `_build_system()`: 调 super() 后 (setup 已完成,
   PFlow 尚未跑 — PFlow 在 base_env.reset 里 _build_system 返回后才
   执行) 把 TIE_IDX = ("Line_4","Line_5","Line_6") 的 r 和 x 各乘
   TIE_K. 与 probes/eig_alloc_common.py 的参数时机完全一致. 不改
   andes_vsg_env_v4.py / andes_vsg_storage_env.py / r279_controllers.py.
4. **k 级** (2, 先冻): k ∈ {1.5, 2.0}. 名义 k=1 数据 = R279 既有
   traces, 只读复用, 不重跑.
5. **runner**: `scripts/run_r286_weak_grid_td.py`, 复制
   `run_r279_controller_scenario` 的执行纪律 (seed=ENV_SEED=42,
   steps=300, delta_u 来自场景, trace schema 同 R279, 每记录写
   location/sign/severity/tie_k), 仅把 env 构造换成 WeakTie 子类.
   seal-before-trace: 先写 seal manifest (场景 hash + ckpt hash + k 级
   + 臂名单), traces 数必须为 0 时才开跑; 产物 `_write_new` 拒覆盖,
   逐文件 .sha256.
6. **端点与统计**: 与 R279 完全相同 —
   `summarise_icems_policy_trace(record, final_window_steps=50,
   fast_window_steps=15)`; 双主端点 normalized_sync_loss_hz2 +
   fast_inter_area_iae_hz_s; centralized 三种子合并对 q0 配对
   (24 场景 × 3 种子 = 72 对/k 级), 报 ratio-of-means + 配对 bootstrap
   CI (复用 R279 分析工具). 守卫: tds_failed 率, PFlow 收敛, G4 合约,
   BESS 物理合约 — 同 R279 相对/绝对纪律.
7. **扰动位置读**: 按 bank `location` 字段 (PQ_0 / PQ_1 / PQ_Bus14 /
   PQ_Bus15, 各 6 场景) 分组, 每位置每 k 级报双主端点配对效应量
   (ratio-of-means, 种子合并). 纯描述, 不拟合, 不做显著性声称
   (每组仅 6 场景).
8. **裁剪顺序** (预注册, 仅墙钟压力触发): 先砍 k=1.5 整级, 再砍到
   centralized_s17 单种子; 永不砍 q0 与端点集. 触发与执行记进
   verdict.
9. **范围**: 不训练, 不改控制器, 不改库, 不改 paper-cited env 本体;
   重训问题仅由判定树开启为后续问题.

## Outcomes (预注册判定树)

- **SURVIVES**: 两个 k 级 (若只跑一级则该级) 上 centralized vs q0 双主
  端点均保持改善且方向不变 (ratio < 1), 且改善幅度相对名义的材料性
  保留 ≥50% (名义 −24.35% → 至少约 −12%) → finding claim,
  Q-0045 closed-positive; 重训问题不必开.
- **DEGRADED**: 双主端点方向保持但改善幅度材料性下降 (<50% 保留) 或
  仅一个端点保持 → finding claim 但有界, Q-0045 closed-partial;
  是否开重训问题写进 PI 话由 PI 定.
- **COLLAPSES**: 任一 k 级双主端点增益消失或反向 (ratio ≥ 1) →
  finding claim (负面结果同等价值), Q-0045 closed-negative, 并开
  "弱网重训" 后续问题卡 (不自动启动实验).
- **INVALID**: PFlow/TDS 失败率超 R279 基线纪律, 或守卫破, 或注入被
  证明未生效 (冒烟时 tie_lines 记录值 ≠ k×名义) → 结果不进任何 claim.

## 资产保护契约

- 不改 `src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py`,
  `andes_vsg_storage_env.py`, `base_env.py`,
  `src/andes_rl_kundur/evaluation/r279_controllers.py`,
  `results/r279_fresh_bank/*`, `results/r279_formal_evaluation/*`,
  `results/r279_matched_training/*`, `train.py`, 手稿, V4 ckpt 命名空间.
- 新增仅限: `src/andes_rl_kundur/env/andes/andes_vsg_env_v4_weak_tie.py`,
  `scripts/run_r286_weak_grid_td.py`, `scripts/analyse_r286_weak_grid.py`,
  `results/r286_weak_grid_td/*`, `reports/R286.md` (feed), 本轮 memory
  实体 (rounds/R286/*, claims/CLM-0645.md).

## Methodology

1. WSL `/home/wya/andes_venv/bin/python`, ANDES 2.0.0. 冒烟先行:
   1 场景 × q0 × k=2.0 单条, 确认 (a) tie_lines 记录值 = k×名义,
   (b) PFlow 收敛, (c) 单条墙钟 → 决定全量编排 (顺序 or 分 shard).
2. 全量: 24 场景 × 4 臂 × 2 k 级 = 192 条. 若冒烟单条 >~45s 则按 k 级
   分 2 shard 串行跑; 超 300s 工具上限用 nohup 断线保护 + 轮询
   (R279 同法).
3. `scripts/analyse_r286_weak_grid.py`: 读 traces → 端点汇总 → 每 k 级
   配对对比 → 判定树分类 → location 分组表 → analysis.json.
4. 收尾固定序列: feed reports/R286.md → verdict → CLM-0645 填卡 →
   Q-0045 closed-* → programme 归档 + 列表回 [] → close_round →
   validate / render → pytest → PI 话原文贴对话 → LINE.md 同步.
