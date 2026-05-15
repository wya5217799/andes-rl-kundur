# ANDES V4.1 Anti-Paper 根本原因 + Go/No-Go 决策 — Session Handoff

**Date**: 2026-05-07
**Repo**: `C:\Users\27443\Desktop\Multi-Agent  VSGs` (双空格 ANDES focus)
**Status**: env-level 全 paper-faithful (R10-R19), 训练层 anti-paper, **reward formula 结构性退化** 嫌疑最大. 等 R20 probe 决定 go/no-go.
**前置 handoff**: `2026-05-07_v4_session_handoff.md` (R10-R19 详细修法), `session_report_2026-05-07_v4_audit.md` (audit 完整记录)

---

## 🎯 TL;DR (新对话 1 分钟接续)

1. **不是 env bug**. R10-R19 已修光 11 个 env-level bug, V4 baseline (no SAC) 已 paper-magnitude (1.3-1.7×).
2. **是 reward formula 结构性退化**. paper Eq.14 strict (PHI_ABS=0) 在 4-agent 同质 ring 上有 trivial optimum: agents 同步到任意非零 ω + ΔH 互抵 + ΔD 互抵 → r_f=r_h=r_d=0 = 全局最优. SAC 找到 trivial 是数学正确的, 不是 RL 失败.
3. **下一步**: R20 (单 probe, 10 min) = go/no-go gate. 若 trained ckpt @ settled phase `r_f≈0 ∧ r_h≈0 ∧ agents sync 非零 ω` → reward paradox 100% confirmed → V4.2 PHI_ABS=50 短训大概率破局, 值得继续. 否则切回 Simulink-discrete.

---

## 1. 根本原因诊断

### Paper Eq.14 公式 (V4.1 strict 复刻)
- `r_f = -(Δω_i - mean_neighbor_Δω)²`  → **local sync** 惩罚
- `r_h = -(mean(ΔH))²`  → **net ΔH 守恒** 惩罚 (4 agents 互抵 = 0)
- `r_d = -(mean(ΔD))²`  → **net ΔD 守恒** 惩罚 (4 agents 互抵 = 0)
- `PHI_ABS = 0`  → **没有任何项惩罚 |Δω| 本身**

### Trivial Optimum (SAC 找到的最优点)
```
4 agents 同步到任意非零 ω
  + ΔH 分布: 2 个 +X, 2 个 -X (mean=0)
  + ΔD 分布: 2 个 +Y, 2 个 -Y (mean=0)
→ r_f=0, r_h=0, r_d=0 (reward 全局最优)
→ |Δω| 自由 → 比 no_control 还大 ✓ (V4.1 实测 0.20-0.25 vs no_control 0.18)
```

### 证据 (V4.1 训练观察)
- r_d 占 91% reward (mean(ΔD)² 主导, 因 action range 大)
- s43: ΔH 1×负 1×正 (互抵符合预测)
- LS1/LS2 max\|Δf\| 比 no_control 大 11-45%
- action_collapse warnings 多次 (actor std → 0.05, 探索退化)

### Paper 怎么训出来的? (3 种可能)
1. paper 实际 `PHI_ABS > 0`, 文本省略 (Yang 2023 Sec.IV-C 没明确给)
2. paper r_f 实际是 `-(Δω_i)²` (absolute deviation), 不是 local sync, fact doc 公式 (15) 语义模糊
3. paper 用了 reward shaping / curriculum 没记录

**任一情况, strict copy paper Eq.14 不能 reproduce paper Fig.7 = paper formula 实际 incomplete**.

### ANDES 平台 1.3-1.7× residual = 次要
closed-form ODE (ANDES TDS 数值精确) vs Phasor block (paper Simulink) 物理层精度差. 不影响 RL 学习方向, 只影响最终 magnitude. R10-R19 已确认.

---

## 2. Verdict: 修改方向值不值得继续

### 矩阵
| 维度 | 继续 ANDES | 切 Simulink-discrete |
|---|---|---|
| Sunk cost (env-level) | 6 hr 修 11 bug 沉了 | n/a |
| 当前进展 | baseline paper-mag, train anti-paper | discrete 主线 G1-G6 lock |
| Trivial optimum 是否可破 | **PHI_ABS=50 短训 1 次可证** | n/a |
| 平台 residual | 1.3-1.7× (写 appendix B 有学术价值) | 0× (主线) |
| 不可知风险 | reward paradox 解后可能还有退化 | 已知, 控制 |
| 用户主线决策 | RE-OPENED 状态 | closure 主线 (PTDF 失败已撤回) |
| 论文产出 | appendix B 跨平台 negative finding | main results 强 |

### 决策原则
**Phase 1 R20 (≤10 min) 必做**, 是 cheap go/no-go gate.

| R20 verdict | 后续 | budget |
|---|---|---|
| reward paradox **confirmed** (我赌 ≥80%) | 跑 V4.2 = V4.1 + PHI_ABS=50, 50 ep × 1 seed | 15 min |
| V4.2 win (max_df < 0.183) | 扩 200 ep × 3 seed, paper Fig.7/9 verdict | ~1.5 hr |
| V4.2 不 win | PHI_F sweep + Eq.17 改 abs(ΔH), 再 50 ep | 30 min |
| **总上限** | go path 全做完 | **≤ 4 hr** |
| reward paradox **NOT confirmed** | 写 appendix B + 切 Simulink | 2 hr 撤离 |

### 绝对不做的事
- ❌ 不分析直接再扫 PHI 超参 (浪费 ≥3 hr)
- ❌ 不验 hypothesis 直接 200 ep × 3 seed sweep
- ❌ 不做 R20 直接动 reward formula

---

## 3. R20 Probe 设计 (单 probe, ≤10 min)

### 目标
量化 V4.1 trained ckpt 在 settled phase 的 reward decomposition + actor 状态.

### 输入
- ckpt: `results/v4_1_paper_s44/checkpoints/best.pt` (V4.1 200 ep, anti-paper 代表)
- env: `env/andes/andes_vsg_env_v4.py` V4.1 strict (PHI_ABS=0)
- scenario: LS1 + LS2 (paper Fig.6/8 disturbance)

### 测什么 (单 trace 即可, episode_length=150 取 30s 看 settled)
1. **reward 分量**: 每 step 记 r_f, r_h, r_d 数值. 看 last 30 step (settled phase) 是否全 ≈ 0.
2. **agents 频率分布**: 4 agents 各自 Δω. 看是否 sync 到非零稳态 (e.g., 4 agents 全在 +0.05 Hz).
3. **ΔH/ΔD 分布**: 4 agents 各自 ΔH, ΔD. 看 mean 是否 ≈ 0 (互抵).
4. **actor μ/σ**: 看 std 是否 < 0.1 (collapse 程度).

### 写哪
- 脚本: `scripts/research_loop/r20_reward_paradox_audit.py`
- verdict: `quality_reports/research_loop/round_20_verdict.md` (ladder format)

### Verdict 判据
- **PARADOX_CONFIRMED**: last 30 step `r_f<0.01 ∧ r_h<0.01 ∧ r_d<0.01 ∧ |mean Δω|>0.01 ∧ |mean ΔH|<10 ∧ |mean ΔD|<10`
- **PARADOX_PARTIAL**: 其中 ≥2 满足
- **PARADOX_REJECTED**: ≤1 满足 → 另寻 hypothesis (B/C/D), ROI 急降

### 实施
用 `probes/andes_common/tracers.py::run_zero_action_trace` 改成 `run_ckpt_trace(ckpt_path, scenario)`. 单 ckpt × 2 scenario × 1 seed = 2 traces. 写 verdict 即可.

---

## 4. Phase 路线图 (R20 confirmed 后)

### Phase 2: V4.2 短训 (15 min)
```bash
python scenarios/kundur/train_andes_v4.py \
  --seed 42 --episodes 50 \
  --phi-abs 50 \
  --save-interval 5 \
  --run-name v4_2_phiabs50_s42
```
**SUCCESS gate**: ckpt @ ep 50 LS1 max\|Δf\| < 0.183 (no_control)

### Phase 3: 200 ep × 3 seed (~1.5 hr)
若 Phase 2 win, 用同配置扩 (s42, s43, s44 并行启动 3 个 ANDES TDS, ANDES 不卡 MATLAB 资源).

### Phase 4: 6-axis verdict + Fig.7/9 plot
```bash
python scripts/research_loop/eval_v4_all_seeds.py
python evaluation/paper_grade_axes.py results/research_loop/eval_v4_2_phiabs50/
python paper/figure_scripts/v4_1_fig7_9_ddic.py  # 复用, 切 ckpt 路径
```

### Phase 5: 论文写作
- main: ANDES V4.2 paper-aligned results (若 Phase 4 axis avg ≥ 0.5)
- appendix B: cross-platform residual + PI-AC methodology error + reward formula completeness 讨论

---

## 5. Repo 当前状态 (代码全 commit)

### 关键文件 (新对话直接读)
- `env/andes/andes_vsg_env_v4.py` — V4 paper-faithful 环境
- `env/andes/base_env.py` — DT-bug fix + M/D physical clamp
- `scenarios/kundur/train_andes_v4.py` — V4 trainer + CLI (--phi-abs / --phi-h / --phi-d / --vsg-m0 / --vsg-d0)
- `probes/andes_common/` — probe framework (utils + tracers + verdict + paper_constants)
- `scripts/research_loop/r1{0..9}_*.py` — R10-R19 forensic
- `scripts/research_loop/eval_v4_{no_control,ddic,all_seeds}.py` — V4 eval drivers
- `evaluation/paper_grade_axes.py` — 6-axis scorer
- `paper/figure_scripts/v4_{baseline_fig6_8,1_fig7_9_ddic}.py` — paper plot

### 已有 ckpts (anti-paper, 用作 R20 输入)
- `results/v4_1_paper_s{42,43,44}/` — V4.1 200 ep 完整, 全 anti-paper
- 推荐 R20 用 `s44/checkpoints/best.pt` (best @ ep 94, max\|Δf\| 0.223)

### Eval 数据 (paper Fig.7/9 antipaper plot 已生成)
- `paper/figures/v4_1_baseline/v4_1_ddic_vs_nc_load_step_{1,2}.png` — 视觉证据 ΔH/ΔD 多负
- `results/research_loop/eval_v4_baseline/` — DDIC + no_control trace JSON

---

## 6. 不可触红线 (避免重复犯错)

1. **不要再扫 PHI 超参盲跑** (V4.0 PHI_D=1 已 STOP @ ep75, V4.1 PHI_D=0.0056 200 ep anti-paper, 第 3 次扫法不会换答案)
2. **不要在 anti-paper baseline 上加 CTDE / settling reward / PI-AC** (浪费, fix reward 才有意义)
3. **不要不写 verdict 就动代码** (R20 必须先有 ladder verdict 文档)
4. **不要混 -discrete repo** (PTDF 失败已撤回, 那是 Simulink 主线; 此 handoff 是 ANDES 双空格 repo)
5. **不要重训 V4.0 / V4.1** (200 ep × 3 seed 已花 ~3 hr, 数据全在 results/)

---

## 7. 给新对话的 5 分钟 Checklist

```
[ ] 读本 handoff (2 min)
[ ] 读 docs/paper/kd_4agent_paper_facts.md Eq.14-18 (2 min)
[ ] 看 paper/figures/v4_1_baseline/*.png (1 min, 视觉 anti-paper)
[ ] 决定: 立刻跑 R20 还是先讨论
```

---

## 8. 风险声明

- R20 confirmed 后 V4.2 PHI_ABS=50 仍不 win 的概率 ~20% (其他 hypothesis B/C 可能并存)
- 即便 V4.2 win, ANDES 1.3-1.7× residual 不会消失, paper Fig.7/9 视觉 100% match 不可能 (平台层物理差)
- 切 Simulink-discrete 路径在 PTDF 失败后, single-point 主线已 G1-G6 lock, **是 fallback 不是失败**

---

## 9. 文件引用

- 本 handoff: `quality_reports/handoff/2026-05-07_andes_v41_reward_paradox_handoff.md`
- 前置: `quality_reports/handoff/2026-05-07_v4_session_handoff.md`
- audit: `quality_reports/research_loop/session_report_2026-05-07_v4_audit.md`
- R10-R17 verdict: `quality_reports/research_loop/round_10_to_17_unified_verdict.md`
- paper 事实: `docs/paper/kd_4agent_paper_facts.md`

---

*Generated 2026-05-07 by main agent. Reward paradox hypothesis ready for R20 falsification probe.*
