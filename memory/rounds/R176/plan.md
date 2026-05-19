---
round: R176
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: meta
---
# R176 plan — Gap 5-10 fixes (full ledger system hardening)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: meta / infrastructure
**Driver**: User said "全部 gap 一次性修". R166 + R171 fixed Gap 1-4;
this round closes the remaining 6 gaps surfaced during those rounds.
**Parent**: CLM-0316 (R166), CLM-0330 (R171). Concurrent with R172
training (Q-0020).

## Gaps to fix

| Id | Gap | Approach | Est |
|----|-----|----------|-----|
| **G5** | Pre-commit hook only runs render, not validate → broken commits possible | Add `scripts/git_hooks/pre-commit` script invoking validate.py with exit-on-error; install instructions in README | 15 min |
| **G6** | sweep scripts (`_r166_sweep.py`, `_r171_sweep.py`) are one-shot; no reusable round-close CLI | Build `memory/tools/close_round.py` with subcommands `superseded`/`aborted`/`completed`, atomic frontmatter edit | 30 min |
| **G7** | 78 soft warns persist (TL;DR missing on R01-R38, PI briefing line caps, stale provenance) | TLDR_CUTOFF=59 parallel to PI_BRIEFING_CUTOFF; raise PI_BRIEFING_LINE_CAP 30→40; provenance survey | 20 min |
| **G8** | `reserve_round.py` atomic but empty dirs from crashed/abandoned sessions stick around | Add `--gc` flag scanning `RNNN/` dirs older than 1 hour with no plan.md, convert to aborted | 25 min |
| **G9** | `R-stale-active` 14-day threshold useless for 30-rounds/day project velocity | Tighten to 3 days; `R-stale-queued` 7→2 days | 5 min |
| **G10** | Parallel session wrote CLM-0325 with round=R171 even though R171 was meta — silent contract violation | New `R-claim-into-meta-round` warning: claim.round → round with type=meta is suspicious | 20 min |

Sweep R173/R174/R175 to aborted (3 more parallel-race empty dirs).

## Execution order (low-risk → high-risk)

1. **G9** (5 min) — one-line constant change + test
2. **G6** (30 min) — close_round CLI + tests (no schema change)
3. **G7** (20 min) — cutoff constant + tests; survey provenance
4. **G10** (20 min) — new validate warning + test
5. **G8** (25 min) — reserve_round --gc + test
6. **G5** (15 min) — git hook script (no Python code change)
7. R173/R174/R175 aborted via new close_round CLI (dogfood G6)
8. R176 verdict + CLM
9. Final test + validate green + commit

## Out of scope

- Wholesale TL;DR retrofit on R01-R38 (cutoff exempts them instead)
- Removing 78 warnings entirely — some are accurate (e.g. CLM-0145
  references `CLM-0057/0058/0059` as a path which is wrong; that's
  a real data error, not noise)
- Refactoring frontmatter schema (e.g. `round_state.py` module split)
- R172 training results — those land in R172 verdict separately

## Cross-references

- CLM-0316 (R166 decision)
- CLM-0330 (R171 decision)
- R166/plan.md (parent design)
- R171/plan.md (more recent parent)
