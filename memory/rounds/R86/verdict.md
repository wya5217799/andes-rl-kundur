# R86 verdict — Cross-ckpt replication of critic-monotone-Q (CLM-0148/9) ✅ UNIVERSAL

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE (R84 mechanism universalised N=1 → N=6)
**Type**: analysis (multi-ckpt forensics on read-only `.pt`, zero ANDES)
**Wall**: ~25 min plan + ~25 min code + ~5 min compute + ~30 min verdict

## TL;DR

R84-W2 (CLM-0148/0149) 在单 R72_w4 ckpt 上发现 critic 沿 action 轴 monotone
+ argmax 在 boundary ±1. R86 把 N 提到 6 (SAC / TD3-MLP / TD3-LSTM × 多 seed
× R58/R63/R72 三 round). **6/6 ckpts argmax 在 boundary, 5/6 ckpts ≥ 50%
curves monotone, 0/6 healthy critic**. 唯一部分例外是 SAC ckpt 的
monotone_fraction = 0.41 (TD3-MLP/LSTM 全部 ≥ 0.84) — 跟 SAC 在 critic update
里加 entropy bonus 这件事一致. **R84 mechanism finding 从 single-ckpt
observation 升级到 universal pathology**, 给 R57-R82 91-round algo plateau
(CLM-0144) 提供 sufficient mechanism-layer 证据.

零 ANDES, 跟 R83 (obs space training, WSL 锁) + R85 (classical PI/Droop eval)
完全正交.

## Methodology

复用 R84-D2 (`scripts/r84_d2_q_landscape.py`) 的 4 指标 + 加 1 新指标:

1. **Advantage** A(s) = Q(s, a_sota) − mean_a Q(s, a)
2. **argmax_dist** = ||argmax_random_a Q − a_sota||_2 (L2)
3. **Q1/Q2 disagreement** at a_sota
4. **||∂Q/∂a||** at a_sota (autograd)
5. **NEW: monotone_fraction** — 沿 action[d] 51-grid sweep [-1, 1], 数
   discrete derivative sign changes. ≤ 1 sign change = monotone. 报跨
   (obs × action_dim) curves 的 monotone 比例.

Ckpt set (6 个, 全 obs_dim=7):

| Ckpt | Algo | Hidden | Source |
|---|---|---|---|
| r72_w4_lstm_tau001_warmup5_s54 | td3_lstm | 64 | R72 SOTA |
| r58_paper_strict_pure_td3_lstm_s49 | td3_lstm | 64 | R58 |
| r58_paper_strict_pure_td3_lstm_s50 | td3_lstm | 64 | R58 |
| r58_paper_strict_pure_td3_s49 | td3 | 64 | R58 |
| r58_paper_strict_pure_sac_s49 | sac | 64 | R58 |
| r63_w4_td3_combo_s49 | td3 | 64 | R63 |

每 ckpt × 4 agent × 200 prior obs ~ N(0, I) × 100 random action ~ U(-1,1)^2.
Sweep viz 用 8 obs (per ckpt PNG, 4 row × 2 col grid).

Critic API algo-fork via `agent.is_recurrent`:
- SAC / TD3 (non-recurrent): `critic(obs, action) → (q1, q2)`
- TD3-LSTM (recurrent): `critic(obs, action, h0_zeros) → (q1, q2, _h)`

## Results

### Per-ckpt summary

| Ckpt | adv_med | argmax_dist | q1q2 | grad | monotone | healthy |
|---|---|---|---|---|---|---|
| anchor_td3lstm_sota_s54 | +0.006 | 1.116 | 0.041 | 0.045 | **1.00** | ❌ |
| td3lstm_s49 | +0.000 | 1.244 | 0.036 | 0.013 | **1.00** | ❌ |
| td3lstm_s50 | +0.000 | 1.219 | 0.094 | 0.012 | **1.00** | ❌ |
| td3_mlp_s49 | +0.030 | 0.649 | 0.069 | 0.044 | **0.94** | ❌ |
| sac_mlp_s49 | -0.000 | 1.163 | 0.027 | 0.006 | **0.41** | ❌ |
| td3_mlp_r63_s49 | +0.713 | 2.786 | 0.488 | 0.226 | **0.84** | ❌ |

### Cross-ckpt aggregate

- **n_ckpts**: 6
- **n_healthy_critics**: **0 / 6**
- **n_monotone_heavy_ckpts (frac ≥ 0.5)**: **5 / 6** (SAC is partial exception)
- **n_argmax_boundary_ckpts (dist ≥ 0.5)**: **6 / 6**
- median monotone_fraction = **0.969**
- median argmax_dist = **1.191**

Interpretation (from script `_interpret`): **UNIVERSAL pathology** —
≥ N-1 ckpts in both monotone-heavy and boundary-argmax categories.

### Sweep visualisations

6 个 PNG 文件 (`results/r86_qlandscape_multickpt/per_ckpt_*_sweep.png`).
每张 4 row (agent) × 2 col (action_dim), 每 subplot 叠 8 条 prior-obs Q curves.
TD3-LSTM ckpts (3 个) 曲线**几乎全线性**; TD3-MLP s49 (R58) 接近线性但有
轻微 curvature; SAC s49 是唯一 visible non-monotone 曲线占主导的 ckpt
(matches monotone_fraction = 0.41). r63_w4 magnitudes 是 outlier (Q 量级 ~ 10×
其余 5 ckpt — 不同训练 reward scale 导致), 但 monotone pattern 仍 0.84.

### SAC 例外解读 (CLM-0156)

SAC critic update 用 `Q(s, a) − α log π(a|s)` 作 Bellman target — α log π 项
作为 action-dependent reward shaping, 推 critic 给不同 action 不同 value.
TD3 / TD3-LSTM critic 直接 regress noisy TD target → tanh-squashed target
action smoothing → critic 平均化所有 action → monotone collapse.

SAC monotone=0.41 vs TD3 0.84–1.00 是 **0.4 量级差异**, 不是 "SAC 不 monotone".
SAC 的 critic 也不健康 (advantage=−0.0001 ≈ 0, argmax_dist=1.163 仍 boundary).
只能说 "entropy regularisation 让 critic 表示稍好一点, 但不够 break plateau".
SAC baseline geo ≤ 0.391 (CLM-0144) 验证这件事.

## Decision (CLM-0157)

R87+ priority **switched** from "algo class sweep" to "critic representation
perturbation". Q-0014 reinterpreted. R87 候选 priority order:

1. **Action feature engineering** (cheapest, MVD): critic input 从 `[obs, a]`
   改成 `[obs, a, a^2, |a|, sign(a)]`. 让 bilinear MLP 能表达 concave.
2. **Distributional critic** (theoretical strongest): IQN/QR head, 32 quantile
   output + quantile Huber loss. Actor 不动.
3. **Spectral norm + larger h**: h=128 with spectral norm 每层 (R62 plain h=128
   already monotone in CLM-0155, 加 spectral norm 是结构 fix).

执行 gate: R83 (obs space refactor) 结果. R83 obs aug 如果突破 0.391 plateau,
R87 不需要; 否则 R87 走 (1) → (2) sequential.

## Infrastructure changes

不动 V4 / V4Config / base_env / paper_grade_axes / agents/ / R57+ ckpt /
R84 outputs / any test.

新建:
- `scripts/r86_qlandscape_multickpt.py` — multi-ckpt forensics + monotone stat
- `results/r86_qlandscape_multickpt/{summary.json, per_agent.json,
  per_ckpt_<6>_sweep.png}` — outputs
- `memory/rounds/R86/{plan.md, verdict.md}`
- `memory/claims/{CLM-0155, CLM-0156, CLM-0157}.md`
- `memory/questions/Q-0019.md`

测试不变量: V4 regression 不需重跑. R57+ SOTA ckpt read-only loaded.

## Cross-references

- R84 verdict CLM-0148/0149 — R86 universalises mechanism layer evidence
- CLM-0144 (R57-R82 91-round algo plateau) — R86 给出 sufficient mechanism layer 证据
- Q-0014 — R86 + CLM-0157 重新定义 priority: 不再 sweep algo, 改 critic rep
- Q-0018 (R84) — ANDES-trajectory variant 仍未做 (Q-0018 仍 open, blocked on R83 lock)
- Q-0019 (this round) — distributional critic 测试候选
- R83 plan — orthogonal, R83 verdict 出来后再决定 R87 是否需要
- R85 plan — orthogonal classical baseline path

## Questions opened (this round)

- **Q-0019** — Does distributional critic (IQN/QR head) break the monotone-Q
  pathology in CLM-0155? Cheap MVD candidate + paper-narrative cleanest fix.

## Questions closed (this round)

- (none) — R86 does not close Q-0014 (still open, but its candidate space
  is narrowed by CLM-0157 decision). Q-0018 still open (ANDES-trajectory
  variant pending R83 lock release).

## Questions advanced (this round, status unchanged)

- **Q-0014** (algorithm exploration backlog) — R86 CLM-0157 narrows
  candidate space: stop sweeping actor architecture; perturb critic
  representation instead. Status stays "open" because Q-0014's exact
  unresolved question ("can we ever break 0.391?") is not yet answered;
  R87+ (Q-0019 / action feature eng / spectral norm) will close it.
- **Q-0018** (ANDES-trajectory variant of R84-D2) — R86 prior-obs result
  makes Q-0018 lower priority (6 ckpts on prior obs already give
  universal evidence; trajectory replay would be confirmatory, not
  primary). Still open, blocked on R83 lock.

## 给 PI 的话

**这周干了啥**：你说"想想有什么更有意义的研究, 别问我, 自动研究". 看 STATE — R83 obs space training + R85 classical PI/Droop baseline 已在另两个 session 跑, R84 单 ckpt mechanism finding (CLM-0148/0149) 还是 N=1 标本. 我开 R86 = **R84 mechanism cross-ckpt 复制**, 测同 critic 病理在 SAC / TD3-MLP / TD3-LSTM × 多 seed × R58/R63/R72 三 round 上是否复现. **零 ANDES, 0 WSL 进程**, 不抢任何 lock.

**结果（一句话）**：R84 完全复现, 而且更强 — 6 个 ckpt **6/6 argmax 在 action boundary, 5/6 ≥50% Q 曲线沿 action 轴 monotone, 0/6 critic 是 healthy 的**. 唯一部分例外是 SAC ckpt 的 monotone_fraction=0.41 (vs TD3/LSTM 全部 ≥ 0.84), 跟 SAC critic update 加 entropy bonus 这件事方向一致, 但 SAC critic 也不健康 (advantage≈0, argmax 仍在 boundary). cross-ckpt median monotone_fraction = **0.969**.

**意外**：r63_w4_td3_combo_s49 Q magnitudes 大 10× 其他 ckpt (advantage=+0.71, q1q2 disagree=0.49, grad_norm=0.23), 但 monotone pattern 还是 0.84 — 说明 Q magnitude 跟 monotone 现象**独立**, 不是 "Q 数值小所以看不出形状" 的 numerical artifact. 这是 R84 → R86 升级的关键证据: monotone collapse 不是 R72_w4 specific basin, 也不是 small-Q numerical issue, 是 TD-based critic + tanh actor 在 7-dim paper-faithful obs 下 **universal pathology**.

**我默认下一步做**：(1) R86 partial-close, CLM-0155/0156/0157 + Q-0019 写入 (已完成). (2) **不开 R87** — 等 R83 (obs space) 出 verdict. 如果 R83 obs aug 突破 0.391 → R87 不需要; 如果 R83 仍 RED → 立刻开 R87 W1 = action feature engineering (`critic([obs, a, a^2, |a|, sign(a)])`, MVD, 1 文件改 networks.py 就够), W2 = IQN distributional critic head. (3) 同步: R83/R85 verdict 出来后 render STATE.md, 把 CLM-0157 决策传播到 Q-0014. 沉默就这么做.

**你想插一脚就说**：(a) 想立刻 prototype R87 distributional critic 不等 R83 — 我可以, IQN head 改 networks.py + td3_lstm.py 大约 200 行 diff, 但跟 R83 narrative 会重叠你需要 ack; (b) 想测 SAC class advantage 更扎实 (CLM-0156 N=1 不够) — 我可以扩 R86 到 5 个 SAC seed 看 monotone 是否稳定在 0.41 左右, 1 个 ckpt × 4 agent × 5 分钟 compute; (c) 觉得 prior-obs caveat 还是不够 — Q-0018 ANDES trajectory variant 等 R83 锁释放后接, 但 R86 N=6 prior 已经是 sufficient mechanism evidence, 我不推荐拖延; (d) 想我直接把 R86 + R84 mechanism finding 写成 paper section draft — 可以, paper Section IV-D "Why the plateau" 现在有 quantitative evidence (monotone_fraction=0.969 + 0/6 healthy). 我推荐 (默认) **(1)+(2): 写完结案等 R83**.
