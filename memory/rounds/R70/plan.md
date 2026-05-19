---
round: R70
state: active
opened: '2026-05-18'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R70 plan — thorough cross-metric evaluation + best agent paper figures

**Date**: 2026-05-18
**Type**: evaluation matrix + paper figure verification
**Wall budget**: ~45 min (eval generation + matrix + plots)

## Trigger

R68 + R69 收尾后用户问"最好 agent 是哪个"，我答 R69 W3 LSTM (tau+warmup=20).
用户问"还需要训练吗？如果不，对候选人做彻底大评估"。

NO new training needed. All 9 hyper axes empirically swept.

Need: cross-metric matrix (paper-metric × 6-axis v3 × per-agent) for all top candidates,
then plot best agent paper figures for visual verification.

## Candidates (no new training, only inference + eval)

| Mode | Family | Seeds | Status |
|---|---|---|---|
| paper-metric SOTA | R67 TD3 tau=0.001 | s49/s50/s51 | s50 trace ✓; s49/s51 launching |
| paper-faithful SOTA | R68 SAC tau=0.001 | s49/s50/s51 | All 3 launching |
| v3 6-axis SOTA | R69 W3 LSTM tau+warmup=20 | s49/s50/s51/s52 | All 4 ✓ |
| LSTM tau-only | R68 W2 + R69 W2/W4 | s50/s51/s52 | All ✓ |
| R57 historical | R57-α LSTM warmup=5 | s49/s50/s51 | s51 ✓; s49/s50 launching |
| LSTM warmup-only | R68 W3a/W4l | s50/s51 | Both ✓ |

## Waves

**W1-W3 (in flight, started ~2 min ago)**:
- R67 TD3 s49: `r70_eval_td3_paper_s49`
- R67 TD3 s51: `r70_eval_td3_paper_s51`
- R68 SAC s50: `r70_eval_sac_paper_s50`

**W4-W7 (queue, launch when W1-3 free slot)**:
- R68 SAC s49 + s51
- R57-α s49 + s50

**W8 (matrix + plot, after all evals)**:
- Run `_r70_eval_matrix.py` → markdown table of all candidates
- Run `_r70_plot_best_agent.py r69_w3_lstm_tau001_warmup20_s50_6axis_s50` → paper Fig 6/7/8

## Decision tree

After matrix:
- If R69 W3 confirmed v3 SOTA across 3-seed mean → plot it as canonical best
- If a 4-agent collaborative candidate beats R69 W3 in v3 → re-evaluate
- For paper writing: cite TD3 R67 in Sec.IV-C scalar table + plot R69 W3 in figures (multi-controller report)

## Schema plan

- **CLM-0109+** (decision/S) — paper_grade_axes v3.0 (11-axis) ranker locked in
- **CLM-0110+** (finding/V) — R70 evaluation matrix: who is true SOTA per mode
- **CLM-0111+** (finding/V) — Best agent paper-figure verification

## Out of scope

- New training (sweep complete)
- LSTM architecture refactor (Q-0013 / R66, deferred)
- Code drift bisect (CLM-0104, deferred)
- Paper writing itself (separate session)
