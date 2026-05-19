---
round: R171
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: meta
note: Dual-identity round — plan filed as meta (gap-fix), but parallel session also wrote CLM-0325 with round=R171 (research hreg dose-response). See verdict.md for the merged story.
---
# R171 plan — Ledger system gap fixes + orphan cleanup (R166 follow-up)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: meta / infrastructure
**Driver**: While answering "which experiments are unfinished" (user query
post-R166), discovered 4 ledger gaps that masked R156 (already-executed
collapse) and Q-0023 (already-answered mag-PI). R166 fixed the
open/close asymmetry but missed results↔ledger detection.
**Parent**: CLM-0316 (R166 decision anchor); discovered during user
audit of unfinished experiments.

## Gaps to fix

### Gap 1 — results filesystem ⟂ ledger (HIGHEST IMPACT)
R156's `results/r156_w1_td3_mlp_s54/final_eval_summary.json` (geo=0.0117
COLLAPSE) sat on disk with no CLM, no verdict. validate.py had no signal.
**Fix**: rule `R-results-orphan` — scan `results/r<NNN>_*` dirs; if
final_eval_summary.json exists but no CLM references the path or round
number, warn.

### Gap 2 — Open Q with implicit answer (designed in R166 but skipped)
Q-0023 (mag-PI) answered by CLM-0256 since R133 but Q never flipped.
R166 plan section 2 declared a `Q-superseded-by-claim` heuristic but
implementation skipped it. **Fix**: implement keyword-overlap heuristic
(Q.title ↔ CLM.statement+tags); warn when an open Q has ≥3 keyword
matches in a `current` claim emitted after Q was opened.

### Gap 3 — Question enum too narrow (closed-partial missing)
Q-0014 answered conditionally by CLM-0295 (single-algo no, ensemble yes).
True status is `closed-partial`. Existing enum forced `closed-positive`
with caveat in closed_note. **Fix**: add `closed-partial` to enum; flip
Q-0014.

### Gap 4 — Latest Round pointer misleading
After R166, STATE.md `## Latest Round` = R166 (meta/infra), but the
latest *research* round is R165. **Fix**: render.py picks the latest
round with `type != meta/infra`; falls back to latest-any if no research
round exists.

## Execution order (TDD where applicable)

A1. Gap 3 (easiest first): extend QUESTION_STATUS_ENUM in validate.py;
    1 test (existing closed-partial in fixture should pass)
A2. Gap 4: add `type` field to plan.md schema; render.py
    `_round_type()` helper; latest_research_round logic + test
A3. Gap 1: validate.py `warn_results_orphan(rounds_dir, claims, repo_root)`
    function + main() wiring + tests
A4. Gap 2: validate.py `warn_question_supersession(questions, claims)`
    using keyword-overlap; soft cap on match count (top 1 suggestion);
    tests
A5. Run all tests; run validate.py end-to-end

B1. Close R168/R169/R170 reserved-empty (parallel-session race)
B2. Flip Q-0014 status: closed-positive → closed-partial
B3. Write R156 minimal verdict + CLM-NNN (td3 MLP collapse, geo=0.0117)
B4. Close Q-0023 closed-positive by CLM-0256 (mag-PI matches droop)
B5. Write CLM for R171 decision (gap fixes + cleanup summary)
B6. Write R171 verdict (3 Q-sections + PI briefing)
B7. Re-render STATE.md; validate green

## Out of scope

- Gap 5-9 (commit-time validate hook, sweep CLI tool, soft-warn
  cleanup, parallel-session timeout, stale threshold tuning) — defer
- Renaming legacy claims / restructuring schema — leave alone
- Actually executing Q-0020 / Q-0008 training — that's R172+

## Cross-references

- CLM-0316 (R166 decision)
- R166/plan.md (parent design)
- R166/verdict.md (parent verdict)
