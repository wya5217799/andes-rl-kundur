---
round: R169
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R169 plan — td3_lstm_hreg λ=0.005 at s54 (retro by R171)

**Status**: COMPLETED (CLM-0325 documents result)
**Type**: research (hreg-λ sweep continuation of R100/CLM-0190)

## Note

Retro plan: parallel session reserved R169 and trained
`td3_lstm_hreg` at s54 with λ=0.005 (between R100's λ=0.01 and
R157's λ=0.03 extreme). Never wrote own claim/verdict; R171 Gap 1
detection surfaced the result.

Result: geo=0.3988 (LS1=0.334, LS2=0.477) — near R72_w4 baseline
0.3908.

See [[CLM-0325]] and `results/r169_w1_hreg_lambda0p005_s54/`.
