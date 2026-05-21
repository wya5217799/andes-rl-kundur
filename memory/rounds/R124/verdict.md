# R124 verdict — td3_afe_lstm s49 collapse (CLOSED-NEGATIVE, geo=0.0100)

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE — AFE prototype catastrophic collapse at 75 ep s49
**Type**: experiment (single-seed training, 75 ep)
**Wall**: ~25 min train + post-hoc eval

## TL;DR

Single-seed s49 training of `td3_afe_lstm` (CLM-0157(b) prototype, CLM-0190).
Training healthy 75/75 episodes; auto-eval crashed because checkpoint_loader
missed `td3_afe_lstm` dispatch (fixed this session). Post-hoc eval yields
**geo=0.0100 (LS1=0, LS2=0)** ≪ no_control 0.104 ≪ R72_w4 SOTA 0.391. AFE
alone catastrophic at this training horizon. Headline + cross-round
implications in **CLM-0255**; the stacked QR+AFE round (R127) and
seed-49 QR-alone round (R129) reach the same collapse pattern.

## Results

| Metric | Value | vs no_control 0.104 |
|---|---|---|
| 11-axis geo (best.pt) | **0.0100** | -0.094 |
| LS1 geo | 0.0 | -0.117 |
| LS2 geo | 0.0 | -0.087 |
| paper-§IV-C cum_rf | -0.2119 | — |

See `results/r124_w1_afe_s49/final_eval_summary.json` + `final_eval/` traces.

## Cross-references

- CLM-0255 (R124+R127+R129 falsification headline)
- CLM-0190 (AFE prototype now marked CODE-PROTOTYPE-ONLY)
- CLM-0157 (R86 R87+ priority, (b) demoted in light of R124)
- R127 verdict (full PI briefing, cross-round)
- R129 verdict (peer collapse)

## Questions opened (this round)

- (none — covered by R127's "longer horizon" Q-NEW)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- **Q-0014** (algorithm exploration backlog): R124 contributes one of the
  three falsifying data points; together with R127+R129 CLM-0255 advances
  Q-0014's interpretation but does not close it.

## 给 PI 的话

详见 R127 verdict 的 `给 PI 的话` —— R124 是其中一个数据点 (td3_afe_lstm s49
geo=0.0100), 跟 R127 / R129 同 closed-NEGATIVE 结论 + CLM-0255 头条总结. 不再
重复完整 PI brief.
