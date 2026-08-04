# ADR-0008: Bound session context and review experiments before drafting

- **Status:** Accepted
- **Date:** 2026-07-30
- **Deciders:** repository owner and Codex workflow review
- **Supersedes:** none
- **Related:** ADR-0003, ADR-0007, `skills/kundur-round/SKILL.md`

## Context

The schema-managed memory and repository contract can grow safely, but cold
sessions still loaded several long status and policy documents. Experiment
feeds made results easy to cite, yet evidence, domain, and external-literature
review could still be deferred until after LaTeX prose and figures existed.
That delay made claim repair expensive. Writing a separate review report after
every round would solve the timing problem by creating a document-sprawl
problem.

## Decision

Cold sessions use `memory/tools/session_context.py` as a bounded adapter over
the programme selector and active manuscript registry. It returns one mode,
one objective, explicit gates, and at most eight required files. The durable
ledger remains unbounded; the working context does not. Historical lookup is
query-driven rather than loaded by default.

After final machine-readable guards and analysis decisions exist, every future
paper-facing experiment feed closes a publication gate before claim
registration, the round `verdict.md`, or drafting. Evidence audit, power-system
domain audit, and external-context status are summarized in the existing feed.
Deep research runs only when novelty or differentiation depends on an
uncovered axis. Detailed review discussion remains ephemeral unless it becomes
an existing durable entity.

The feed remains the paper-facing fact layer; claims/questions/rounds remain
the ledger; raw measurements remain under results; manuscript prose remains
under its registered delivery line. No second memory or review ledger is
created.

The active manuscript `line-state` snapshots its authoritative experiment-feed
directory through `ARTIFACTS.json`. A new or edited feed invalidates that
snapshot and routes the next cold start to `manuscript-refresh`. A refresh must
reconcile the line objective, bounded reading set, claim bindings, and affected
registered derivatives before accepting the new directory hash. This is a
navigation acknowledgement, not a copy of experimental facts.

`LINE.md` is therefore an index, not a digest. It keeps the current action and
scope, `decision_refs` into durable Deep Research/venue decisions, and
`evidence_refs` that bind claim cards to feeds. Authoritative feeds must not be
listed in `required_reading`; they are opened lazily only for the claim being
used. Repository health enforces a line-size budget, a total cold-start byte
budget, at least one durable decision reference, and acknowledgement of the
latest feed. Updating only the feed-directory hash cannot satisfy the gate.

## Consequences

- A new conversation can recover the current task without reading project
  history or relying on chat memory.
- The number of historical rounds and claims no longer determines context
  size.
- Unsupported or externally stale claims are caught before prose and figures
  make them expensive to repair.
- One experiment still creates only the planned round skeleton, one feed, one
  claim card, and machine artifacts; semantic review does not add a new report
  family. `repo_health.py` enforces the round-directory Markdown budget from
  R287 onward while grandfathering historical evidence.
- Manuscript-line frontmatter becomes the machine-readable cold-start contract
  and must be updated when its next action changes.
- A paper-facing round cannot become invisible to the next manuscript session:
  feed-directory drift remains a hard navigation alert until explicitly
  acknowledged.
- Deep Research, feed conclusions, and result values remain detailed at their
  authoritative locations without being copied into the navigation layer.
