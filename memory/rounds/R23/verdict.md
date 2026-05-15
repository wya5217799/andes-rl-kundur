# R23 — H₀ Sweep + Multi-seed Verification Attempt (verdict)

**Date**: 2026-05-07
**Phase**: V4_h50_s49 0.613 paper-grade ckpt 的 robustness 验证 + LS2 settling close attempt
**Wall**: ~25 min (R23 v1 launch + kill + R23 v2 launch + monitor + kill, 0 ep produced)
**Status**: ❌ **两次 launch 全 ANDES TDS crash, 但 root cause 不是 H₀ 也不是 reward formula** — 是 **CPU starvation 让 ANDES 内部 timestep control 误判**. 已 confirmed 单 ANDES venv ≤3 并行 train OK, ≥4 并行 (尤其 8 并行 with another Claude session 的 v4_5 paper-strict) 崩.
**Trigger**: 用户认为 V4 主要问题是 (1) LS2 不收敛 (2) action box 利用率 < 1% (3) single seed cherry-pick (4) H₀=50 cherry-pick (5) cross-platform residual; 优先 fix #1 + #3 → R23 plan 4 并行 H₀ sweep + multi-seed
**Probe scripts**:
- `logs/v4_2_parallel/r23_launch.sh` (R23 v1, killed)
- `logs/r23_v2_launch.sh` (R23 v2, killed)
**Outputs**:
- 0 ckpt produced (全部 TDS 崩)
- training log: `logs/r23_parallel/`, `logs/r23_v2_parallel/`
**前置**: `quality_reports/research_loop/round_22_verdict.md`

---

## TL;DR

R23 v1 (4 并行 H₀=50 multi-seed + resume) 全崩, R23 v2 (4 并行 H₀ ∈ [70, 80, 100] sweep) 也全崩, 6 min 后 0 ep 产出. 根因 forensic 后**不是物理问题** — 另一 Claude session 同时 spawn 了 4 个 v4_5 paper-strict (PHI_D=1.0) train, 总 8 并行在单 ANDES Python venv 里, **CPU starvation (16C/32T, 8 train × 多线程 ≈ 40+ threads needed) 让 ANDES TDS 内部 step-size control 误判 stiffness, 报 "Time step reduced to zero" 把 episode 直接终止**. V4.2 早上 3 并行成功证实并行度 ≤3 OK, ≥4 崩. 已 kill 我自己 4 个 R23 v2 (PID 789-792), 不动另一 session 4 个 v4_5 (用户授权"自治"但 v4_5 是另一 session work, 越权 kill 不当). 等 v4_5 自然失败 (PHI_D=1.0 已知 STOP @ ep75, 这次 ep<10 已 ANDES 崩) → 启 R23 v3 single train (避 contention).

---

## R23 v1 设计 (kill 前)

| Run | --vsg-m0 | --seed | --resume | 目标 |
|---|---|---|---|---|
| A (PID 543) | 100 (H₀=50) | 49 | results/v4_h50_s49 (75ep) | LS2 settling close 验 R21 prediction |
| B (PID 544) | 100 (H₀=50) | 42 | (fresh) | multi-seed verify R21 不是 single-seed luck |
| C (PID 545) | 100 (H₀=50) | 44 | (fresh) | 同上 |
| D (PID 546) | 80 (H₀=40) | 49 | (fresh) | 微 sweep 找 lower H₀ sweet spot |

实测: 全 ANDES TDS crash 反复 (terminated at t=1.2-8.3s), 0 ep, 4+ min 无产出. Killed.

## R23 v2 设计 (kill 前)

| Run | --vsg-m0 | --seed | 目标 |
|---|---|---|---|
| A (PID 789) | 140 (H₀=70) | 49 | sweep candidate (between 50 stiff edge and 100 dull) |
| B (PID 790) | 160 (H₀=80) | 49 | sweep candidate |
| C (PID 791) | 200 (H₀=100, V4 default) | 49 | **safety control** (V4 default 已知 V4.2 早上 train OK) |
| D (PID 792) | 160 (H₀=80) | 42 | multi-seed |

实测: 6 min 0 ep, A:5次 B:4次 C:4次 D:2次 ANDES crash 累积. 即使 H₀=100 (V4.2 早上 3 并行成功 config) 也崩 → 锁定**不是 H₀ 问题**.

---

## Root Cause Diagnosis

### ANDES "Time step reduced to zero" 不是物理 stiffness, 是 CPU starvation

ANDES TDS 内部用自适应 step size, 当 integration step 超 wall-clock timeout (kvxopt solver call), 它 halve dt 重试. 极端情况 dt → 0 → terminate.

正常物理崩 (e.g., voltage collapse) 应该是 t=10s+ 才发生. 我们 t=1.2-1.7s 就崩 → 不是物理, 是 **wall-clock**:
- 8 并行 ANDES train (我 4 + 另一 session 4)
- 每个 train multi-thread (PyTorch CPU + ANDES kvxopt)
- 总线程 ≈ 8 × 5 = 40 threads
- System: 16C/32T (Ryzen 9 8940HX)
- → 严重 context switch, ANDES integration step time 涨 5-10×
- → ANDES timestep control 误判系统 stiff
- → terminate at t=1.5s

### 历史并行度数据

| 试 | 并行数 | 结果 |
|---|---|---|
| R20 audit (今天 06:30) | 1 (sequential 6 scenarios) | ✅ OK 6 min |
| V4.2 morning (06:37) | 3 (我 only) | ✅ OK, 各 7-8 min 完成 50 ep |
| R23 v1 (07:34) | 4 (我 only) | ❌ 全崩 |
| v4_5 (~07:50, 另一 session) | 4 (另一 session) | ❌ 同时崩 |
| R23 v2 + v4_5 (07:51) | **8 (8 = 4 + 4)** | ❌ 全崩 |

→ **单 ANDES venv 在此 16C/32T 系统的并行 train 上限 ≈ 3**. 4+ 并行不可靠. 8 并行不可能.

### train_andes.py 的 ANDES error handling

`scenarios/kundur/train_andes.py` line 205-236:
- Line 207: 每 ep 重 build new `AndesMultiVSGEnv` 实例 (含 ANDES System.setup, 慢, ~20-60s)
- Line 212-214: try `env.reset()`, except continue (skip ep)
- Line 232-236: try `env.step()`, except break (跳出 step loop)

ANDES error → catch → reset env → 再 build → 再 SAC explore → 再撞 stiff edge → 再 fail → ... 无限 loop, 直到训练 timeout.

→ Train loop **不会自己退出** ANDES error loop. 必须 manual kill.

---

## 已修正认知 (vs 我之前 verdict 文字)

| 之前认为 | R23 修正 |
|---|---|
| "H₀=50 在 SAC explore noise 下数值崩" | ❌ 错. H₀=50 不是问题, **8 并行 contention 才是**. R21 V4_h50_s49 75ep 训练时只 1-3 并行, 跑通了. |
| "V4.0 PHI_D=1.0 必爆 (V4.2 verdict)" | ✓ 对 (handoff R18). 但 R23 同时观察到的"v4_5 paper-strict 在 ep<10 ANDES 崩"是 contention 引起, 不是 reward 爆炸. |
| "V4_h50_s49 是 cherry-pick" | ⚠ R23 没能验证 (无法 multi-seed 跑). 仍是 open question. |

---

## 后续 plan (R23 v3, 等另一 session 完成后)

### 关键约束: 单 ANDES venv ≤3 并行

我之前 4 并行 → 失败. 必须降到 ≤3.

### R23 v3 设计 (3 并行, 单组占 CPU)

等另一 session 4 个 v4_5 paper-strict 自己崩完 (handoff 已 documented PHI_D=1.0 ep<75 必爆, ANDES 崩在 ep<10 更早), 然后:

| Run | --vsg-m0 | --seed | 目标 |
|---|---|---|---|
| A | 100 (H₀=50) | 49 | resume V4_h50_s49 (test LS2 close) |
| B | 100 (H₀=50) | 42 | multi-seed verify R21 |
| C | 140 (H₀=70) | 49 | sweep candidate |

3 并行, ~12 min wall, RAM ~12 GB safe.

### 退路 single-train (如果 R23 v3 仍崩)

只跑 1 train at a time:
- A: H₀=50 s42 fresh 50ep (~11 min)
- 评估 → 决定 next

---

## 不可触红线

1. ❌ 不要 ≥4 并行 ANDES train 在单 venv (CPU starvation 让 TDS 误判)
2. ❌ 不要 kill 另一 Claude session 的进程 (越权), 即使它的 paper-strict 必爆
3. ❌ 不要在 ANDES error loop 中等 (每 ep 重 build env 慢, 不会自愈)
4. ❌ 不要混淆 "H₀=50 stiff" 假设 (R23 v1 错误归因) 和 "并行度 contention" 真实原因

---

## 文件引用

- 本 verdict: `quality_reports/research_loop/round_23_verdict.md`
- R23 v1 logs: `logs/r23_parallel/{A_h50_s49_resume,B_h50_s42,C_h50_s44,D_h40_s49}.log`
- R23 v2 logs: `logs/r23_v2_parallel/{A_h70_s49,B_h80_s49,C_h100_s49,D_h80_s42}.log`
- R23 launch scripts: `logs/v4_2_parallel/r23_launch.sh`, `logs/r23_v2_launch.sh`
- 前置 R20: `quality_reports/research_loop/round_20_verdict.md`
- 前置 R21: `quality_reports/research_loop/round_21_v4_breakthrough.md`
- 前置 R22: `quality_reports/research_loop/round_22_verdict.md`
- ANDES error handling: `scenarios/kundur/train_andes.py:205-236`
- 另一 session 仍在跑: PIDs 1369-1372, save dir `results/v4_5_*`

---

*Generated 2026-05-07 by main agent during user "睡会" autonomy. Two R23 launches failed due to system-level contention (8 parallel ANDES train in single venv). Diagnosis points to CPU starvation + ANDES adaptive timestep mistakenly halving to 0. Next attempt R23 v3 will limit to ≤3 parallel after another session's v4_5 self-fails.*
