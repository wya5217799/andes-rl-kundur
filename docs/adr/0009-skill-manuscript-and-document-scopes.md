# ADR-0009: Separate skill, project, manuscript, and document scopes

- **Status:** Accepted
- **Date:** 2026-07-30
- **Deciders:** repository owner and Codex workflow review
- **Supersedes:** none
- **Related:** ADR-0007, ADR-0008, `docs/repo-hygiene/research-skills.scope.json`

## Context

The research workflow combines general-purpose navigation, two external
academic-skill families, project-specific experiment governance, and
paper-specific drafting. Without explicit boundaries, global skills can absorb
ANDES-only rules, one manuscript can write into another manuscript's context,
and each deep-research or review pass can create another apparently current
report. Those failure modes increase cold-start context and allow derivative
analysis to drift away from sealed experimental facts.

Journal choice has a similar lifecycle problem. A shortlist is useful before
drafting because it changes story depth and package constraints, but rankings,
fees, scope, and author instructions can change. A one-time AI recommendation
must not silently become a permanent venue fact.

## Decision

Use four nested scopes with one-way authority:

1. **Global skill scope** — `ask-matt`, `ask-research-supervisor`, ARS,
   Supervisor Skills, and specialist auditors remain project-neutral. They
   advise or execute their own workflow but own no project writes.
2. **Project scope** — `skills/kundur-round/` owns the ANDES lifecycle, ledger,
   feed contract, physical audit requirements, and the adapter that global
   research skills must obey in this repository.
3. **Manuscript-line scope** — every active paper has one delivery root, one
   `LINE.md`, one exclusive write scope, declared shared read roots, and one
   `ARTIFACTS.json`. Several ongoing papers may be active at once: lifecycle
   status answers whether a line remains writable, while
   `session_context.py --line <id>` selects the bounded context for one
   session. `priority` is only a fallback when the request does not identify a
   line; it is not a repository-wide lock. An explicit line selection may
   outrank an unreserved research goal, while an already-active experiment
   round still has precedence. The line stores navigation and current intent,
   not copies of experiment or Deep Research facts.
4. **Document scope** — generated research, decision, review, and drafting
   artifacts are ephemeral by default. A durable artifact declares purpose,
   inputs, producer, authority, status, supersession, and review date. Only one
   active canonical artifact may exist per purpose.

Venue selection uses a staged gate: constraints, shortlist, lock, and
pre-submission refresh. Official journal sources govern scope and submission
rules; institutional ranking requirements remain author/PI decisions and must
be verified through the institution's accepted source.

Venue metadata distinguishes journals, conferences, and other delivery types.
A journal line retains its transfer-backup requirement; a locked conference
line may omit a transfer venue because revising an accepted conference paper is
not a journal-shortlisting decision.

The experiment feed remains the paper-facing fact layer. Claims, verdicts, and
raw results retain their existing authority. Literature reports, consolidated
reviews, venue decisions, and manuscript prose are derivative and may be
marked stale by expiry or input-hash drift.

## Consequences

- General skills remain reusable across repositories; updating this project
  does not mutate their domain knowledge.
- New papers can coexist without sharing a writable context or copying the
  entire research programme into each paper.
- Switching papers is a read-only routing action. It does not edit priorities,
  freeze another line, or move evidence; a frozen line must be deliberately
  reactivated before it becomes selectable.
- `session_context.py --list-lines` exposes line id, lifecycle status, routing
  metadata readiness, and selectability without loading programme or evidence
  history.
- Deep Research and reviewer passes no longer create unbounded permanent
  reports; most output stays in `tmp/<line>/`, while the one promoted artifact
  is registered and superseded deliberately.
- A new session reads the active line and its manifest rather than scanning
  historical documents. The manifest is injected into `required_reading`
  automatically and freshness alerts are part of the returned context.
- Durable decisions are reached through `decision_refs`; experimental facts are
  reached through claim-to-feed `evidence_refs`. Feeds stay out of the eager
  reading set, and repository health constrains both navigation and cold-start
  size.
- Repository health checks detect write-scope escape, duplicate canonical
  documents, unregistered manuscript files, missing inputs, expired review
  dates, input drift, external-skill authority leakage, and missing scope
  metadata. Expiry and input drift block current use.
- The extra metadata is justified only for durable cross-session artifacts;
  transient analysis remains frictionless and disposable.
