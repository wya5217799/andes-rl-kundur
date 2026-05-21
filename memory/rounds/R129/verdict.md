# R129 verdict — td3_qr_lstm s49 collapse (CLOSED-NEGATIVE, geo=0.0413)

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE — QR prototype catastrophic collapse at 75 ep s49
**Type**: experiment (single-seed training, 75 ep)
**Wall**: ~35 min train + post-hoc eval

## TL;DR

Single-seed s49 training of `td3_qr_lstm` (CLM-0157(a) prototype, CLM-0189).
Training healthy 75/75 episodes; auto-eval crashed because checkpoint_loader
missed `td3_qr_lstm` dispatch (fixed this session). Post-hoc eval yields
**geo=0.0413 (LS1=0.0, LS2=0.1702)** ≪ no_control 0.104 ≪ R72_w4 SOTA 0.391.
QR alone (no AFE) yields 4× better than AFE-containing R124/R127 but still
60% below no_control. CLM-0255 documents the cross-round headline.

## Results

| Metric | Value | vs no_control 0.104 |
|---|---|---|
| 11-axis geo (best.pt) | **0.0413** | -0.063 |
| LS1 geo | 0.0 | -0.117 |
| LS2 geo | **0.1702** | +0.083 |
| paper-§IV-C cum_rf | -0.2094 | — |

Notable: LS2 partially survives (0.17) while LS1 crashes (0.0). Suggests QR
critic is sensitive to disturbance direction; LS1 (Bus 14 load drop, freq
rises) triggers more aggressive bang-bang than LS2 (Bus 15 load increase,
freq drops). The asymmetry is itself a paper-publishable mechanism datum.

See `results/r129_w1_qr51_s49/final_eval_summary.json` + `final_eval/` traces.

## Cross-references

- CLM-0255 (R124+R127+R129 falsification headline)
- CLM-0189 (QR prototype now marked CODE-PROTOTYPE-ONLY)
- CLM-0157 (R86 R87+ priority, (a) downgrade context)
- R127 verdict (full PI briefing, cross-round)
- R124 verdict (peer collapse)

## Questions opened (this round)

- **Q-NEW** (informal, captured under R127 Q-NEW): LS1 vs LS2 disturbance-
  direction asymmetry of QR critic — does it persist at multi-seed and
  500 ep? (Paper-Sec.V data point if confirmed.)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- **Q-0014** (algorithm exploration backlog): R129 contributes the QR-only
  data point; LS2=0.17 hint suggests QR is *not* useless, just disturbance-
  asymmetric. Q-0014 should weight QR > AFE in future priority.

## 给 PI 的话

详见 R127 verdict 的 `给 PI 的话` —— R129 是其中一个数据点 (td3_qr_lstm s49
geo=0.0413, LS1=0 / LS2=0.17), QR alone 4× 比 AFE-containing 跑好但仍 60%
below no_control. CLM-0255 头条总结. 不再重复完整 PI brief.
