# R105 verdict — Reward function audit: project vs paper Eq.14-18 verbatim

**Date**: 2026-05-19
**Status**: DONE — 3 paper-deviation findings, 2 claims (CLM-0191/0192), 1 Q-NEW (Q-0024)
**Type**: audit (zero compute, zero ANDES, zero V4 mutation)
**Wall**: ~25 min (read code + JSON + write claims/verdict)

## TL;DR

R105 (zero-compute audit, ran while R102 magnitude-PI+TGOV1 ablation runs
in WSL background) found **R72_w4 LSTM SOTA was trained with reward weights
substantively divergent from paper Eq.14-18**: `phi_abs=50` extra (NOT in
paper) + `phi_h=phi_d=0.0056` (÷178 vs paper's 1) + `action_penalty_mode=
normalized` (paper Eq.17-18 is literal physical). Effective training
signal is dominated by **frequency restoration** (r_abs term ~50% of r_f)
not paper's pure synchronization. CLM-0191 documents the finding;
CLM-0192 decides to keep R72_w4 as canonical SOTA (eval metric is consistent
across compared controllers, no retraction) but **add paper write-up
disclosure**. Q-0024 opens for future `paper_strict_pure` re-training
to disambiguate whether PHI_ABS=50 is load-bearing.

## Methodology

100% Windows-side file inspection, zero compute, zero ANDES TDS.

1. Read `base_env.py:586-730` (_compute_rewards) verbatim
2. Read `base_env.py:76-84` (PHI_F=100, PHI_H=1, PHI_D=1, PHI_ABS=50 defaults)
3. Read `v4_config.py:42, 197, 212` (phi_abs default=50, paper_strict_pure factory)
4. Read `results/r72_w4_lstm_tau001_warmup5_s54/training_log.json::env_config`
5. Cross-ref `docs/paper/kd_4agent_paper_facts.md` §2.4 (paper Eq.14-18)
6. Cross-ref `scripts/_archive/r20_reward_settled_audit.py` (R20 historical
   PHI_ABS sweep)

## Findings

### F1 (CRITICAL): r_abs term NOT in paper

`base_env.py:684-685, 709-711`:
```python
r_abs = -(float(d_omega[i])) ** 2     # NON-paper term, see line 79-84 comment
rewards[i] = (self.PHI_F * r_f + self.PHI_ABS * r_abs
              + self.PHI_H * r_h + self.PHI_D * r_d)
```

`V4Config.phi_abs default = 50.0`. R72_w4 trained with default → phi_abs=50.
Paper Eq.14: `r_i = φ_f·r^f_i + φ_h·r^h_i + φ_d·r^d_i` — no r_abs term.

Paper §2.4.2 explicitly says r^f=0 when nodes are sync'd, even if all
flat-deviate together. R72_w4's r_abs term forces restoration as well —
diverges from paper.

### F2 (HIGH): φ_h, φ_d ÷178 vs paper

| Component | Paper | R72_w4 SOTA |
|---|---|---|
| φ_h | 1.0 | 0.0056 |
| φ_d | 1.0 | 0.0056 |

R72_w4 trains with action-penalty terms essentially negligible. Paper's
"double-objective: sync + total reserve preservation" (paper §0.5) —
the second objective is NOT effectively enforced in R72_w4.

### F3 (MEDIUM): action_penalty_mode = normalized (paper says physical)

Paper Eq.17 reads as `r^h = -(ΔH_avg)²` with ΔH in physical units (paper
§13 Q-A admits H dimensionality is unclear). R72_w4 uses `normalized` mode
which divides by `max(DM_MAX, |DM_MIN|)=300` first → ΔH_norm ∈ [-1,1] →
r_h ∈ [-1, 0]. Different scale than paper's literal physical reading.

### Aggregate (CLM-0191/0192)

| Component | Weight | Typical Mag | Net Contribution |
|---|---|---|---|
| r_f (sync) | 100 | 0.001 | **-0.10** |
| r_abs (restore) | 50 | 0.005 | **-0.25** ← dominant |
| r_h (norm. ΔH²) | 0.0056 | 0.04 | -0.0002 (negligible) |
| r_d (norm. ΔD²) | 0.0056 | 0.04 | -0.0002 (negligible) |

R72_w4 is a **"restoration-first" agent**, not paper's sync-only DDIC.

## Decision (CLM-0192)

- **NO retraction** of any prior claim (CLM-0094 / CLM-0144 / CLM-0184 / CLM-0186)
- All R85 RL-vs-classical comparisons valid on consistent EVAL metric (`paper_grade_axes`)
- Paper write-up MUST disclose training reward divergence
- Q-0024 opens for `paper_strict_pure` re-training to test if phi_abs=50 is load-bearing

## Verification

- Read source code locations as cited above ✓
- R72_w4 `training_log.json::env_config` parsed ✓
- Numerical estimate of effective contribution magnitudes shown in CLM-0191 table ✓
- V4 / V4Config / base_env / agents/ / ckpt 全部零 mutation ✓
- 零 ANDES TDS, 零 WSL python ✓
- No conflict with R102 (running in WSL) or any other parallel round ✓

## Cross-references

- CLM-0094 (R72_w4 LSTM SOTA, geo=0.391, training_log audited here)
- CLM-0144 (91-round algo plateau, conditional on this reward)
- CLM-0184/0185/0186 (R85 classical baseline, eval-metric apples-to-apples)
- CLM-0149/0153 (R84 actor-critic decoupling — critic learned on this augmented reward)
- CLM-0173 (R89 ANDES Kundur audit, parallel paper-deviation thread)
- `docs/paper/kd_4agent_paper_facts.md` §0.5 + §2.4 + §13 Q-A/B
- `scripts/_archive/r20_reward_settled_audit.py` (R20 PHI_ABS=0 finding)
- ADR-0002 (V4 SSOT + paper-faithful framing) — R105 adds caveat to "paper-faithful"

## Questions opened (this round)

- **Q-0024**: paper_strict_pure (phi_abs=0, phi_h=phi_d=1) retraining —
  match R72_w4 geo 0.391? Disambiguates whether PHI_ABS=50 is load-bearing
  for paper_grade_axes performance.

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这周干了啥**: R102 在 WSL 后台跑 magnitude-PI + TGOV1 ablation (~25 min ETA, 5 min elapsed) 同时, Windows-side 开 R105 = reward function audit. 零 compute / 零 ANDES / 零 V4 mutation, 纯 file inspection. 读 base_env._compute_rewards verbatim + R72_w4 training_log env_config + paper §2.4 + R20 archive.

**结果（一句话）**: **R72_w4 SOTA 训练用的 reward 跟 paper Eq.14-18 substantively divergent** — `phi_abs=50` (paper 没有这项), `phi_h=phi_d=0.0056` (÷178 vs paper 1), `action_penalty_mode=normalized` (paper literal physical). R72_w4 effectively 是 "restoration-first" agent (r_abs 主导 -0.25 vs r_f -0.10), 不是 paper 的 sync-only DDIC.

**意外**: (1) **r_abs term 在 base_env.py:684 写得很明确 "非论文项, PHI_ABS=0 时归零"**, 但 V4Config default = 50, R72_w4 用 default 训练 — 项目早就知道这是 paper-deviation, 但没在 paper write-up 里 disclose. (2) **φ_h=φ_d=0.0056 ≈ 1/178** — R18 历史 (archived) empirically rescale 让 action penalty 量级跟 r_f 平衡, 但 paper 没说这样做. 双 objective (sync + 总 reserve 守恒) 中, 第二个 objective 在 R72_w4 实质 = unenforced. (3) **R72_w4 SOTA 跟 R85 droop 的 1.99× advantage 仍然 valid** — 因为 eval metric (paper_grade_axes) 跨 controller 一致, 不依赖 training reward. 但 paper write-up MUST disclose. (4) **R20 archive 找过 PHI_ABS=0 训练, "anti-paper"** — 历史 evidence 指出去掉 PHI_ABS 会 degrade, 但没量化 multi-seed. Q-0024 登记 paper_strict_pure 重训证伪.

**我默认下一步做**: R105 收尾 done (verdict + 2 claim CLM-0191/0192 + Q-0024). 等 R102 完成 (~20 min ETA) 写 R102 verdict + chat brief. 期间继续 Windows-side 零冲突 audit, 候选 (TBD 按 ROI): (a) 比对 V4 disturbance injection profile (step / ramp / Toggler timing) vs paper Sec.IV-C, (b) 比对 line impedance 跟 Kundur 1994 textbook published values, (c) audit V4 通信延迟 / 邻居 fail 实现 vs paper Sec.IV-D/E.

**你想插一脚就说**: (a) 若你想立即开 Q-0024 paper_strict_pure 重训 (~2h, 单 seed × 75 ep, 跟 R83/R102 抢 WSL slot 风险), 说一声; (b) 若你想直接进 paper 改稿模式 (基于 CLM-0192 disclosure 修 methodology 段落), 是 paper-side 工作不是 research; (c) 若你想从 reward 三 finding (F1+F2+F3) 中挑一个深挖 (例如 audit R72_w4 actor 实际 output 看是否 restoration-biased), 工程量 ~30 min; (d) 沉默 = 等 R102 完成 + 继续 Windows-side audit (默认走 disturbance profile inspection). **我推荐 (d)**.
