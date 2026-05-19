---
round: R39
state: active
opened: '2026-05-16'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R39 plan — Memory system → active oracle

**Date**: 2026-05-16
**Type**: infrastructure (schema + tooling, no experiment)
**Status**: in-progress

## Trigger

`/grill-me` session (this conversation) interviewed 10 design branches
A–J on the research memory subsystem. Goal: convert `memory/` from a
passive ledger (write-only) into an active oracle that surfaces
"what to do next" without manual archaeology.

## Decisions (locked via grilling A–J)

| ID | Decision |
|----|----------|
| A | Focus = memory system (not pipeline; R37 already closed pipeline debt) |
| B | Role = active oracle, not passive ledger |
| C | New atomic forward-action unit = Question (`Q-NNNN`) |
| D | Questions open/close at round-verdict close (3 mandatory verdict sections) |
| E | Q schema = 6 frontmatter fields + `## Candidates` + `## Log` (soft body) |
| F | STATE.md = 6 sections (Headlines / In-Flight / Open Q / Recently Closed / Latest Round / Stats) |
| G | `memory/handoffs/` stripped from schema — free scratchpad, not oracle-feeding |
| H | Round verdict template = 5 mandatory sections (Header + TL;DR + 3 Q-section) |
| I | Backfill = minimum (G4 inertia → Q-0001 only; lazy elsewhere) |
| J | Schema cleanup batch: round-gap doc, CLM-0042 one-line, trust V→S on decisions |

## Execution (4 commits, vertical TDD slices)

| Commit | Scope | Verification |
|--------|-------|--------------|
| 1 | J: `_SKIPPED.md`, CLM-0042 statement→1-line, 8 decisions trust V→S, validate.py +R4 trust-consistency rule (TDD: failing test first) | `pytest memory/tools/tests/ -v` green; `validate.py` green on real claims |
| 2 | E + H + I: Q template, `Q-0001.md` G4-inertia backfill, verdict template, validate.py +3 rules (Q schema / Q closure / verdict structure). Retrofit 26 historical verdicts with 3 placeholder Q-sections | `pytest` green; `validate.py` green |
| 3 | F + G: `render.py` rewrite for 6-section STATE.md (Open Q + Recently Closed + In-Flight detection). `handoffs/README.md` marks dir as non-schema | `pytest` green; manual inspect STATE.md (Open Q = Q-0001 only) |
| 4 | Docs (`CLAUDE.md` memory section, `CONTEXT.md` glossary +Q) + R39/verdict.md dogfood (first use of new 5-section template) | `validate.py` green; R39 verdict passes new structure rule |

## Verification gates

After each commit:
1. `cd memory/tools && python -m pytest tests/ -v` → all green
2. `python memory/tools/validate.py` → all green
3. `python memory/tools/render.py` → STATE.md regenerates

## Out of scope

- T1/T2 training-script automation (`new_claim.py`, eval-to-claim auto-stub)
  — manual is fine, defer until friction observable.
- Non-G4 historical Q backfill — lazy; only when new Q wants to cite.
- R40 first real loop iteration (e.g. address Q-0001 via ZERO_G4=False
  rerun) — separate decision after R39 lands.
- R38 (TD3 vs 0.137 attractor) — pre-existing plan, untouched.

## Addresses Questions

(none — this is the infrastructure round that creates the Question
entity; Q-0001 G4-inertia is *opened* not *addressed* here)

## Risks

- Retrofitting 26 historical verdicts with placeholder Q-sections may
  cause merge friction if any historical verdict is concurrently
  edited. Mitigation: single batch sed, no manual edits.
- `render.py` rewrite is the largest single change (~200 lines).
  Mitigation: test-driven, fixtures already cover headline+decision
  rendering; new fixtures for Q rendering.
