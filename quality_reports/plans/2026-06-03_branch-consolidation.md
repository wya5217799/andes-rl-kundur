# Branch consolidation — merge important branches into main

**Status**: COMPLETED (pushed to origin/main @ 4e3d450)
**Date**: 2026-06-03
**Approved**: user chose "全做 + 合并后推送"

## Landscape (at start)

| Branch | vs main | Content | Action |
|---|---|---|---|
| `codex/codebase-review-cleanup` | +1 / -0 (FF) | import-contract + memory-validation cleanup, on origin | **FF merge** ✅ done |
| `claude/gallant-einstein-3ac554` | +0 / -14 (tip is main ancestor) | old notes-ingest spec/plan, fully in main | **delete branch + worktree** |
| `feature/memory-notes-ingest` | +18 / -14 | Note entity system (NOTE-0001..0023) + tools + tests, ~1763 LOC | **re-number IDs, merge** |

## Problem: ID collision (feature branch)

main and feature both used R109 / CLM-0182 / Q-0023 for DIFFERENT content.
Re-number feature side to free IDs before merge:

- `R109` → `R260` (main max = R259)
- `CLM-0182` → `CLM-0490` (main max = CLM-0485)
- `Q-0023` → `Q-0026` (main max = Q-0025)

Internal refs to fix (feature side): CLM-0490.md, Q-0026.md, R260/plan.md,
R260/verdict.md, render.py comments (R98→R260). NOTE-*.md carry no R109/CLM/Q refs.

## Steps

1. [done] FF main → codex/codebase-review-cleanup; validate.py green (262 claims, 0 err).
2. [ ] Phase A: in feature worktree, git mv R109→R260, CLM-0182→CLM-0490,
   Q-0023→Q-0026; fix internal refs; commit on feature branch.
3. [ ] Phase B: `git merge feature/memory-notes-ingest` into main. Resolve
   conflicts: validate.py, render.py, test_validate.py, test_render.py (code merges),
   STATE.md (re-render). add/add ledger conflicts eliminated by Phase A renumber.
4. [ ] Phase C: pytest memory/tools/tests + validate.py + render.py. Iterate to green.
   Commit merge.
5. [ ] Delete stale gallant-einstein worktree + branch.
6. [ ] Push main → origin.

## Safety net

- All in git; `git merge --abort` recoverable.
- validate.py = ledger-invariant gate; only commit merge if it exits 0 and
  memory/tools/tests pass.
