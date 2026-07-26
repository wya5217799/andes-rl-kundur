---
round: R263
state: completed
type: infra
opened: '2026-07-24'
closed: '2026-07-24'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R263 plan — TPWRS research autopilot: durable programme + one-command next goal

**Status**: COMPLETED
**Opened**: 2026-07-24
**Driver**: New sessions can recover facts from STATE.md, but there is no
machine-readable north star that ranks open questions by their contribution
to the accepted TPWRS research thesis.
**Parent**: CLM-0510, Q-0027

## TL;DR

Add one authoritative long-horizon research programme and one deep
`select_next_goal()` module.  The selector must refuse duplicate work when a
round is active, choose only programme-ranked open questions, and emit a
complete `/goal` contract with evidence and stopping conditions.

## Snapshot at plan-time (oracle as of 2026-07-24)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0027 [opened R262] Can a state-dependent droop residual policy advance both dual metrics?

## Recently Closed (last 3)

- Q-0008 closed-negative @ R252, by CLM-0415 — Verify paper-metric ranking persists at 500-ep paper convergence horizon
- Q-0021 closed-positive @ R252, by CLM-0231 — V4 env TGOV1 governors u=1.0 in ANDES JSON but R08 Finding 3 says "completely ineffective" — which is true post-R37 refactor?
- Q-0005 closed-partial @ R186, by CLM-0350 — Why does TD3+LSTM seed 50 collapse while seeds 49/51 converge?

## Methodology

1. Add `memory/RESEARCH_PROGRAM.md` as the single source for the accepted
   thesis, phase gates, ranked question backlog, evidence requirements, and
   kill/pivot rules.
2. Add root `AGENTS.md` as the Codex new-session bootstrap: read the programme,
   STATE, and process rules; run the selector; resume active work before
   starting anything new.
3. Add `memory/tools/research_goal.py` with one external interface,
   `select_next_goal(repo_root)`.  It hides programme parsing, question-state
   lookup, active-round detection, priority ordering, and `/goal` rendering.
4. Test ready selection, closed-question skipping, active-round blocking,
   stale-active handling, and malformed programme rejection through that
   interface.
5. Update CLAUDE.md and README.md in the same change so future agents discover
   the module without relying on chat memory.
6. Run the focused tests, memory validator/render, and relevant broader tests.

## Gate

- **PASS** only if a clean checkout-like fixture selects Q-0027 and emits a
  goal containing one objective, required reading, verification commands,
  scope limits, and a verifiable stopping condition.
- **PASS** only if any genuinely active round changes selection to BLOCKED,
  while a stale `state: active` plan with an existing verdict does not.
- **PASS** only if repository memory validation succeeds and STATE renders.
- Otherwise keep R263 active; do not launch a research experiment.

## Pre-registered outcomes

- **READY**: all selector behavior tests pass, the live repository blocks
  while R263 is active, and after R263 closes the selector returns Q-0027 with
  a complete goal contract. Close R263 positive and launch that contract.
- **PARTIAL**: the durable programme and bootstrap validate, but one-command
  selection cannot distinguish active from stale rounds or cannot render all
  required goal fields. Keep the programme, close R263 partial, and open a
  narrowly scoped infrastructure repair before any scientific round.
- **INVALID**: memory validation fails, required reading cannot be resolved,
  or selection can bypass an active round. Keep R263 active until corrected;
  no research result may be interpreted under this automation layer.

## 资产保护契约

- No environment, agent, checkpoint, paper metric, or result is modified.
- `memory/STATE.md` remains generated output, not a policy store.
- Existing question and round schemas remain backward-compatible.
- No new round is auto-reserved by the selector; selection is read-only.

## Cross-references

- CLM-0510 / R262: fixed R201-droop blending is Pareto-only.
- Q-0027: state-dependent residual/gating is the next low-cost scientific
  question.
- `研究计划/proposal/PROPOSAL_SPEC.md`: topology-general GNN control is already
  the accepted forward thrust.
- `docs/research/2026-07-24_rl_vsg_publication_landscape.md`: publication and
  evaluation audit supporting the physics/safety/topology programme.
