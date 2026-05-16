# R53 verdict — memory hygiene dogfood (R50 G/H/I/J/L → 1+ caller)

**Date**: 2026-05-17
**Status**: **COMPLETE**
**Type**: infrastructure (memory housekeeping)
**Wall**: ~45 min

## TL;DR

Executed the R52 hygiene playbook end-to-end: created the missing
`memory/claims/_TEMPLATE.md`, backfilled `metric:` blocks on 8 headline
claims, marked CLM-0008 obsoleted (J validated), rewrote 21 claims'
stale provenance (dangling WARN 30→5), archived 10 stale handoffs,
added Warning C to validate.py (finding/correction citing decimal but
missing metric — 27 hints, +3 tests, 41/41 pass), and added a
"Creating a new round / claim" section to CLAUDE.md so future sessions
adopt reserve_round / template / score_run by default. R50 opts
G/H/I/J/L go from 0 callers each to 1+; K's debt is cleared modulo
5 genuinely-deleted historical paths.

## Methodology

Linear walk of the 12-step playbook in
`memory/handoffs/2026-05-17_R52_memory_hygiene_plan.md`, validate-after-
each-step to fail fast. Round number reserved via
`reserve_round.py` (R52 already taken by Codex's parallel research
commit `45c4987`, so we got R53 — exact race condition G was built for).

## Results

| Validation criterion | Target | Achieved |
|---|---|---|
| `validate.py` ERROR count | 0 | 0 |
| Provenance "missing on disk" WARN | ≤ 5 (was 30) | 5 |
| Missing-metric soft WARN | ≤ 30 | 27 |
| `pytest tests/` | ≥ 77 | 77 |
| `pytest memory/tools/tests/` | ≥ 71 | 72 (was 69; +3 A2 tests) |
| Claims with `metric:` block | ≥ 8 | 8 |
| Claims with `status: obsoleted` | ≥ 1 | 1 (CLM-0008) |
| STATE.md `## Leaderboard` populated | yes | yes, 8 rows |
| `query.py --best 6_axis --top 5` | 5 rows | 5 rows |
| handoffs/ top-level count | 5 | 5 (incl. README, R52 plan) |
| handoffs/_archive/ count | 9 | 10 |
| `reserve_round.py` external callers | 1 (this round) | 1 |

R50 batch adoption status post-R53:

| Opt | Status before R53 | Status after R53 |
|---|---|---|
| G (reserve_round.py) | 0 callers | 1 caller (R53 itself) |
| H (STATE.md ## Leaderboard) | empty section | 8 rows populated |
| I (CLM `metric` field) | 0/59 claims | 8/60 claims |
| J (status: obsoleted) | 0/59 claims | 1/60 (CLM-0008) |
| K (provenance soft-check) | 30 WARN | 5 WARN |
| L (query.py --best) | 0 callers | 1 caller (this verdict) |

E (score_run.py) intentionally untouched — needs an actual research
round to use; not a hygiene concern.

## Verification

- `validate.py` ends with `OK: 60 claims, 4 questions, 42 warnings`
  (0 errors).
- 27 of those warnings are the new Warning C "missing metric"
  soft-hints, distributed across older finding claims that cite
  decimal numbers. Expected; this is the design (push organic
  adoption without blocking authorship).
- Remaining 5 dangling provenance paths are genuinely-deleted
  historical eval scripts under `scripts/research_loop/` plus 2
  weird `_legacy/CONTEXT.md "5 Bespoke Asset"` parser glitches.
  Leaving these as-is for future rounds.
- `query.py --best 6_axis --top 5` confirmed top result is
  CLM-0005 [R30] 6_axis = 0.4440.

## Known dangling provenance

After C1, 5 entries remain WARN:

- CLM-0001: `scripts/research_loop/eval_v4_ddic.py` (R45 archive
  retired the directory; eval is now `scripts/eval_ddic.py`)
- CLM-0004: `scripts/research_loop/eval_v4_no_control.py`
  (now `scripts/eval_no_control.py`)
- CLM-0005: `scripts/research_loop/eval_paper_spec_v2.py`
  (deleted; superseded by `scripts/eval_ensemble.py` + `scripts/score_run.py`)
- CLM-0015 / CLM-0016: `_legacy/CONTEXT.md "5 Bespoke Asset"` —
  the path has a quoted section reference; the validator's
  separator-strip helper doesn't catch the quote case. Path itself
  exists (`_legacy/CONTEXT.md` is on disk); only the appended
  section reference confuses it.

Not fixing in R53 — would require either editing 3 historical-archive
claims (CLM-0001/0004/0005) to point at the new script names (risk:
breaking historical attribution) or extending the
`_extract_provenance_path` helper (out of hygiene-round scope). Both
are candidates for a future round.

## Cross-references

- Playbook: `memory/handoffs/2026-05-17_R52_memory_hygiene_plan.md`
- R50 opts list: same handoff, "Why this round exists" table
- One-off script: `memory/tools/_oneoff_fix_provenance_paths.py`
  (committed alongside this round for audit; delete after R54)
- Race-condition example: Codex's parallel R52 research commit
  `45c4987` "time-in-obs FAILS" — both sessions wanted the next
  available R-number simultaneously, reserve_round.py resolved it.

## What changed (files)

- `memory/claims/_TEMPLATE.md` — created (was missing, Q template
  existed)
- `memory/claims/CLM-0005/0006/0007/0049/0050/0052/0054/0056.md` —
  +metric block
- `memory/claims/CLM-0008.md` — status: current → obsoleted, +reason
- 21 claims rewritten by `_oneoff_fix_provenance_paths.py` (mostly
  pre-R37 `env/*` / `evaluation/*` → `src/andes_rl_kundur/...`
  rewrites plus R45 archive rewrites)
- `memory/handoffs/_archive/*` — 10 files moved via `git mv`
- `memory/handoffs/README.md` — +"_archive/ convention" subsection
- `memory/tools/validate.py` — +Warning C block + `_DECIMAL_RE` constant
- `memory/tools/tests/test_validate.py` — +3 tests for Warning C
- `memory/tools/tests/fixtures/claims/CLM-0002.md` /
  `CLM-0003.md` — +metric block (preserves clean-fixtures invariant
  against Warning C)
- `CLAUDE.md` — +"Creating a new round / claim" subsection
- `memory/STATE.md` — regenerated; Leaderboard now populated

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none — Q-0004 is Codex's R51 question, untouched by R53)

## Questions advanced (this round, status unchanged)
- (none)
