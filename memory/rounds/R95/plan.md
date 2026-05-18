# R95 plan — Actor LSTM warm-up time-resolved quantification (complements CLM-0170)

**Status**: ACTIVE → CLOSED-POSITIVE
**Opened**: 2026-05-19
**Driver**: PI "继续研究". CLM-0170 (R92) qualitatively described actor
"smoothly slides toward boundary over first ~15 steps"; R95 quantifies the
time-resolved magnitude curve and identifies LSTM warm-up lag as plateau
mechanism #2 (action-space ceiling = #1, already in R94).
**Parent**: CLM-0170 (R92), CLM-0161 (R88), CLM-0160 (R84-W3-traj)

## TL;DR

Mine the same cached `r84_d2b_q_landscape_trajectory/per_step.json` that
R92 (CLM-0170) and R88 (CLM-0161) used, but extract `sota_action` per step
(not just summary stats) to get the **time-resolved ||a|| ramp-up curve**.
Find:

- Step 0 actor ||a||_2 = 0.149 (10% of max √2).
- Reaches 90% of saturation by step 10.
- corr(||a||, advantage) = +0.932 overall.
- Mechanism refinement: plateau composition = action-space ceiling (R92 #1) + LSTM warm-up lag (R95 #2).

Theoretical claim (CLM-0175): R94 widen-bound experiment will improve
steady-state axes (settling) but not transient axes (max_df) if LSTM warm-up
remains the binding constraint in step 0-5.

Zero ANDES, zero WSL, zero conflict.

## Wave 顺序

| Wave | 内容 | Wall |
|---|---|---|
| **W1** | Mine cached per_step.json for sota_action time series + correlation analysis (done) | ~10 min |
| **W2** | Write CLM-0174 (temporal ramp quantification) + CLM-0175 (theoretical prediction for R94) + Q-0022 (warm-h_0 candidate) | ~25 min (done) |
| **W3** | Verdict + render STATE.md + PI briefing | ~15 min |

Total wall ~50 min, zero compute beyond W1.

## 资源冲突 gate

- R83 (obs space training): WSL ANDES locked. R95 zero ANDES. ✅
- R85 (classical baseline): WSL eval. R95 zero. ✅
- R87 (closed): R95 uses its cached output read-only. ✅
- R89 (R09 sideline): zero overlap. ✅
- R91 (D3 obs sufficiency): uses same cached file but for different
  variables (obs sufficiency, not sota_action ramp). Zero data write
  conflict. ✅
- R92 (action coordination, CLM-0170): closed. R95 uses its conclusions.
- R94 (widen-bound training, in flight): R95 produces a falsifiable
  prediction (CLM-0175) for R94's result. R94 is the test bed; R95 is the
  hypothesis. ✅
- R95 output namespace: `memory/rounds/R95/`, `memory/claims/{CLM-0174,
  CLM-0175}.md`, `memory/questions/Q-0022.md`. No file writes outside
  these.

## 资产保护契约

不动: V4 / V4Config / base_env / paper_grade_axes / agents/ /
scripts/train.py / R57+ ckpt / R84/R86/R92/R94 scripts / R94 in-flight
training data / any test.

新建: `memory/rounds/R95/{plan.md, verdict.md}` +
`memory/claims/{CLM-0174, CLM-0175}.md` + `memory/questions/Q-0022.md`.

## 测试不变量

- V4 regression `tests/test_v4_env_regression.py` 不需重跑
- 所有现存 cached data read-only

## Cross-references

- CLM-0170 (R92 action-saturation finding) — parent. R95 quantifies its
  qualitative "smoothly slides" claim
- CLM-0161 (R88 phase bimodality) — sibling. R88 measured critic
  confidence per phase; R95 measures actor magnitude per step
- CLM-0162 (supersedes CLM-0157) — R95 inherits the "actor saturates,
  no representation pathology" framing
- CLM-0174 (this round, finding)
- CLM-0175 (this round, theoretical prediction for R94)
- Q-0022 (this round, LSTM warm-h_0 candidate)
- R94 plan (widen-bound training, in flight) — R95 produces the
  predicted-outcome matrix for R94 result
