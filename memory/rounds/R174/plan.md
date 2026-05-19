---
round: R174
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
note: R176 GC hotfix un-flipped this. Earlier GC wrongly swept R174 as reserved-empty (plan.md missing) but results/r174_*/final_eval_summary.json existed from parallel-session training. R174 = NEW SINGLE-POLICY SOTA geo=0.4139.
---
# R174 plan — td3_lstm_hreg λ=0.002 at s54 (retro by R176 hotfix, NEW SINGLE-POLICY SOTA)

**Status**: COMPLETED — **NEW SINGLE-POLICY SOTA**
**Type**: research (hreg-λ sweep continuation of R170 sweet-spot finding)

## Result

geo=**0.4139** (LS1=0.367, LS2=0.467, cum_rf=-0.069)

This **beats R170 (0.4091, λ=0.003)** by +1.2% and beats R154 4-way
ensemble (0.4119) by +0.5% — first single policy to land *at* the
ensemble ceiling.

Hreg λ=0.002 is the new dose-response sweet spot, tighter than
R170's λ=0.003. The dose-response curve continues to climb at lower
λ; even finer-grain ({0.001, 0.0015, 0.0025}) may find a peak.

## Note on GC mishap (R176 hotfix)

Parallel session reserved R174 + ran training + eval, producing
`results/r174_w1_hreg_lambda0p002_s54/final_eval_summary.json` but
never wrote `memory/rounds/R174/plan.md`. My initial R176 GC
(`reserve_round.py --gc --gc-minutes 0`) wrongly swept this as
reserved-empty. The hotfix to `gc_empty_rounds()` now also checks
for matching `results/rNNN_*/final_eval_summary.json` before
sweeping. R174 un-flipped to completed.

See `results/r174_w1_hreg_lambda0p002_s54/`. Parallel session is
running R177 ensemble eval that includes R174 — formal CLM with
full dose-response refinement may land in their narrative.
