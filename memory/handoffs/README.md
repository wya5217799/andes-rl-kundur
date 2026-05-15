# memory/handoffs/ — informal session-end notes

**This directory is NOT part of the schema-managed memory subsystem.**

## What lives here

Free-form markdown notes written at the end of a Claude Code session
(or before `/clear`), capturing whatever the author thinks is useful
for picking up later. Filename, structure, and content are unrestricted.

These are the analogue of `git stash`: ephemeral, personal, allowed
to overlap with other notes, allowed to go stale.

## What does NOT live here

Anything that the next round or the oracle should automatically see.
Use one of the schema-managed entities instead:

- A research **finding / decision / correction** → write a `CLM-NNNN`
  claim in `memory/claims/`.
- An **open research question** that future rounds should address →
  write a `Q-NNNN` file in `memory/questions/`.
- A **round-bounded summary** of what was done and what's left →
  write `memory/rounds/RNN/verdict.md` (5-section template at
  `memory/rounds/_TEMPLATE_VERDICT.md`).

## What the tooling does (and does not do)

- `python memory/tools/validate.py` **does not read** this directory.
  Handoff files can use any format without breaking validation.
- `python memory/tools/render.py` **does not surface** handoffs in
  `memory/STATE.md`. The oracle reads claims + questions + rounds only.
- `git` tracks everything in this directory normally. Old handoffs
  are kept for historical context; you may prune anything older than
  ~30 days or marked STALE at your discretion.

## Why this exists at all

Session boundaries and round boundaries are orthogonal axes. A session
can span 0, 1, or many rounds; a round can span 0, 1, or many sessions.
This directory is the scratchpad for the session axis. The schema is
for the round axis.

See `memory/rounds/R39/plan.md` decision G for the rationale.
