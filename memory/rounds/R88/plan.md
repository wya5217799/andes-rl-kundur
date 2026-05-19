---
round: R88
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R88 plan — Mechanism reconciliation (synthetic-obs ↔ on-manifold) + transient-phase finding

**Status**: ACTIVE (W1 done, partial-close style)
**Opened**: 2026-05-19
**Driver**: PI "继续研究". R87 (concurrent session) emitted CLM-0160 that
refutes the synthetic-obs affine-Q mechanism story (CLM-0149/0153/0154 and
my R86 extension CLM-0155/0157). R88 reconciles the conflict by mining the
cached on-manifold per-step data the existing windows left on disk.
**Parent**: CLM-0160 (R84-W3-traj on-manifold) + CLM-0155 (R86 cross-ckpt synthetic)

## TL;DR

R86 (synthetic-obs, h_critic=0): 6/6 ckpts monotone-Q, plateau mechanism
candidate = critic representation. CLM-0160 (real ANDES trajectory): the
SAME critic IS concave around a_sota on real obs (advantage +120% of |Q|),
mechanism candidate retracted.

R88-W1 mines the 400-record `per_step.json` cached by R84-W3-traj. **The
on-manifold concavity is bimodal in episode phase**: step 0-2 has 100%
bad-argmax fraction (argmax_dist ≥ 0.5), step 10+ has 2.5%. The critic
is confused in transient phase, confident in steady-state. The 91-round
plateau is consistent with **transient-phase critic data starvation**:
6-axis metric is dominated by early-step max_df / dD_smooth / settling,
but the critic gets only ~6% of training samples from that regime.

Zero ANDES (cached data only). Zero WSL lock conflict.

## Wave 顺序

| Wave | 内容 | Wall |
|---|---|---|
| **W1** | Mine cached `per_step.json`, compute per-step / per-phase aggregate stats, identify bimodal pattern | ~10 min (done) |
| **W2** | Write CLM-0161 (phase-breakdown finding), CLM-0162 (correction of CLM-0157), open Q-0020 (transient-replay-reweighting candidate) | ~30 min (done) |
| **W3** | Verdict + render STATE.md + PI briefing | ~15 min |

Total wall ~55 min, **zero compute**, zero WSL conflict.

## R86 ↔ CLM-0160 ↔ R88 三角

| Probe regime | Source | Verdict on critic | Mechanism implication |
|---|---|---|---|
| Synthetic obs N(0, I), h_critic=0 | R84-W2 (CLM-0149), R86 (CLM-0155) | Monotone in action, argmax on boundary | "Critic representation broken" — WRONG |
| Real ANDES trajectory, **all steps** averaged | R84-W3-traj (CLM-0160) | Concave around a_sota, +120% of |Q| advantage | "Critic competent on-manifold" — TRUE but hides asymmetry |
| Real ANDES trajectory, **per phase** | R88-W1 (CLM-0161, this round) | Bimodal: confident step ≥ 10, confused step 0-2 | "Transient-phase data starvation" — new candidate |

R86 synthetic finding is empirically valid (6/6 ckpts ARE monotone on
prior obs) but **its interpretation** (CLM-0155 universal pathology +
CLM-0157 R87 priority) was overreach. CLM-0162 supersedes CLM-0157.

## 资源冲突 gate

- R83 (obs space training): WSL ANDES locked. R88 zero ANDES. ✅
- R85 (classical PI/Droop baseline): possibly uses WSL for eval. R88 zero ANDES. ✅
- R87 (concurrent session, on-manifold variant): cached `per_step.json` is
  R87's output that R88 reads read-only. Zero conflict. ✅
- R88 输出 namespace: `results/r84_d2b_q_landscape_trajectory/per_step_phase_breakdown.json` (new file in
  R87's dir — extends the existing cache without overwriting). Plus
  `memory/rounds/R88/`, claim writes, question writes.

## 资产保护契约

不动: V4 / V4Config / base_env / paper_grade_axes / agents/ /
scripts/train.py / 任何 R57+ ckpt / R84/R86 scripts / any test.

新建: `results/r84_d2b_q_landscape_trajectory/per_step_phase_breakdown.json`
+ `memory/rounds/R88/{plan.md, verdict.md}` + `memory/claims/{CLM-0161,
CLM-0162}.md` + `memory/questions/Q-0020.md`.

## 测试不变量

- V4 regression `tests/test_v4_env_regression.py` **不需重跑** (零 env 改动)
- R57+ SOTA ckpt 完全未读
- R86/R84 outputs 完全未改

## Cross-references

- CLM-0160 (R84-W3-traj, on-manifold reconciler) — parent + counter-evidence to R86
- CLM-0155/0156/0157 (R86 cross-ckpt synthetic) — R86 finding stands, interpretation revised
- CLM-0157 — superseded by CLM-0162
- Q-0019 (distributional critic) — deprioritised, status stays open with log note
- Q-0014 (algorithm exploration) — narrowed again: not critic rep, not algo class, → transient replay
- R83 plan (obs-space training) — independent path, may also break plateau
