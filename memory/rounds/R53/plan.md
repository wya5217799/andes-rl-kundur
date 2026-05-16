# R53 plan — memory hygiene dogfood

**Date**: 2026-05-17
**Type**: infrastructure (memory housekeeping)
**Status**: planned

## Goal

Execute the R52 hygiene playbook at
`memory/handoffs/2026-05-17_R52_memory_hygiene_plan.md` to prove stage-2
adoption of the R50 opt batch (G/H/I/J/L) and clear K's 30-WARN dangling-
provenance debt. The round number `R53` (not `R52`) is what
`reserve_round.py` gave us — R52 was atomically grabbed by Codex's
parallel research session (commit `45c4987`, time-in-obs attack). This
race is exactly what G was built to handle; using R53 validates that.

## Body

Steps 2..10 of the handoff:

- Step 2 — create `memory/claims/_TEMPLATE.md` (was missing; Q template
  already existed)
- Step 3 — backfill structured `metric:` blocks on 8 headline claims
  (CLM-0005/0006/0007/0049/0050/0052/0054/0056). Powers R50 H
  (leaderboard) + R50 L (`query.py --best`).
- Step 4 — mark CLM-0008 `status: obsoleted` (no_control baseline 0.104
  → 0.094 under post-R36 ranker, no successor claim). Validates R50 J.
- Step 5 — one-off script rewrites stale provenance paths (pre-R37
  src-layout + Codex R45 archive). 21 claims rewritten; dangling
  warnings 30 → 5.
- Step 6 — archive 10 handoffs ≥ 10 days old to `_archive/`; document
  the convention in `memory/handoffs/README.md`.
- Step 7 — add Warning C to validate.py: finding/correction citing a
  decimal but no metric block → soft hint. 3 new tests; 41/41 pass.
- Step 8 — add "Creating a new round / claim" subsection to
  `CLAUDE.md` so future sessions land on reserve_round / template /
  score_run conventions automatically.
- Steps 9–10 — write this plan + verdict, regenerate STATE.md, confirm
  the new Leaderboard section appears, sanity-check `query.py --best
  6_axis --top 5`.

No research, no env changes, no V4 touches. Fully reversible per the
handoff's rollback section.

## Out of scope

- Backfilling metric blocks on the remaining ~25 finding claims —
  organic adoption when future rounds touch their own claims.
- `score_run.py` adoption (E) — that needs an actual research round
  (R54+).
- Anything in the research pipeline (training, eval, ANDES code).
