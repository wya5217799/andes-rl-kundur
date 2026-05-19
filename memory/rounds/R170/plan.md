---
round: R170
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R170 plan — td3_lstm_hreg λ=0.003 at s54 (retro by R171, NEAR-SOTA)

**Status**: COMPLETED (CLM-0325 documents result — **near R154 SOTA**)
**Type**: research (hreg-λ sweep continuation of R100/CLM-0190)

## Note

Retro plan: parallel session reserved R170 and trained
`td3_lstm_hreg` at s54 with λ=0.003 (smaller than R100's λ=0.01).
**Result: geo=0.4091 — strongest single policy in the project**,
just 0.0028 below R154 4-way ensemble SOTA 0.4119.

Never wrote own claim/verdict; R171 Gap 1 detection rescued this
near-SOTA finding from being silently buried.

See [[CLM-0325]] and `results/r170_w1_hreg_lambda0p003_s54/`.
