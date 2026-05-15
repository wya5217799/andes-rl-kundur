# R39 verdict — Memory system rewired to active oracle

**Date**: 2026-05-16
**Status**: **COMPLETE**.
**Type**: infrastructure (schema + tooling, no experiment)
**Wall**: ~3 h (grilling + execution)

## TL;DR

`memory/` is now an active oracle. Claude (or any cold-start reader)
opens `STATE.md` and sees 6 sections — headlines, in-flight, open
Questions with candidate experiments, recently closed Qs, latest round
TL;DR, stats — without reading 26 round verdicts or 12 handoff files.
29 tests green; `validate.py` enforces 4 claim rules + 3 Q rules + 3
verdict-structure rules; `Q-0001` opens the only forward-fill question
(ZERO_G4_INERTIA paper-faithful rerun, deferred from R37/CLM-0040).

## What changed

Per the `/grill-me` design (A–J locked, then executed as 4 commits):

| Commit | Hash | Scope |
|--------|------|-------|
| 1 | absorbed by `c66ce24` | Schema cleanup: `_SKIPPED.md` for R09/R12-R19/R31/R32, CLM-0042 statement→1-line + body Notes, 8 decision claims trust V→S, `validate.py` +R4 trust-consistency rule, +4 pytest cases (RED-first). |
| 2 | `183e7a4` | New entities: `memory/questions/_TEMPLATE.md` + `Q-0001.md` (G4 inertia rerun), `memory/rounds/_TEMPLATE_VERDICT.md`. `validate.py` +`load_questions`, +`validate_question_rules` (3 Q rules), +`validate_verdict_structure` + `warn_verdict_recommended`. 29 historical verdicts retrofit with placeholder 3 Q-sections. +9 pytest cases. |
| 3 | (this round) | `render.py` rewrite for 6-section `STATE.md`. Removed legacy "Open Decisions" + "Most Recent Handoff". Added Open Questions / Recently Closed / In-Flight / TL;DR extraction / Q-aware Stats. `memory/handoffs/README.md` declares scratchpad role. +9 pytest cases. |
| 4 | (this commit) | Docs: `CLAUDE.md` memory subsystem section rewritten for active-oracle model; `CONTEXT.md` glossary +Q entity, handoffs declared out-of-schema. This `verdict.md` is the first dogfood of the new 5-section template. |

## Verification

```text
$ python memory/tools/validate.py
OK: 43 claims, 1 questions, 9 warnings
$ python memory/tools/render.py
Rendered memory/STATE.md
$ cd memory/tools && python -m pytest tests/ -v
======================== 29 passed, 1 warning in 0.16s ========================
```

The 9 warnings are all soft: 8 historical verdicts lack `## TL;DR` +
1 lacks `**Status**:` header. Forward template includes both.

## Notes on the parallel session collision

While the grilling was in progress, a separate Codex session committed
`5b18ab1` (TD3Agent) and `c66ce24` (R38 TD3 sweep verdict). That second
commit also independently performed most of commit 1's schema cleanup
(trust V→S on the 8 decision claims, CLM-0042 statement→1-line,
`_SKIPPED.md`, `validate.py` +R4, +4 pytest cases). The R39 plan
adjusted: commit 1 is now absorbed by `c66ce24`; commits 2–4 stack
cleanly on top. R38 round number is preserved for the TD3 experiment,
R39 numbering chosen for this infrastructure round.

## Cross-references

- `memory/rounds/R39/plan.md` — original plan with A–J decision matrix
- `CLAUDE.md` — refreshed memory subsystem section
- `CONTEXT.md` — glossary +Q entity
- `memory/handoffs/README.md` — handoffs declared scratchpad
- `memory/questions/Q-0001.md` — G4 inertia open question

## Questions opened (this round)

- Q-0001: ZERO_G4_INERTIA=False headline rerun → `memory/questions/Q-0001.md`

## Questions closed (this round)

- none

## Questions advanced (this round, status unchanged)

- none
