# ADR-0007: Enforce repository governance through one contract

- **Status:** Accepted
- **Date:** 2026-07-29
- **Deciders:** repository owner and repository-hygiene review
- **Supersedes:** none
- **Related:** ADR-0001, `docs/repo-hygiene/2026-07-29_problem_statement.md`

## Context

The research ledger has a schema and validator, but repository-wide rules for
delivery lines, canonical and derived artifacts, root cleanliness, executable
lifecycle, navigation freshness, and third-party skills are distributed across
prose documents. The result is a clean ledger inside a repository whose
downstream artifacts can still fork or drift.

Expanding the ledger validator would mix research-record validity with
repository structure. Encoding the same policy in an agent skill would make a
stochastic prompt the enforcement authority. Continuing with prose alone would
leave pre-commit, CI, humans, and agents applying different rules.

## Decision

Repository-wide hygiene is governed by one machine-readable contract and one
repository-governance validator. The validator is a separate module from the
research-ledger validator and exposes one command-line seam shared by local
checks, pre-commit, CI, and agent workflows.

Policy packs cover repository roots, delivery lines, canonical and derived
artifacts, executable lifecycle, navigation documents, and vendored or
tool-owned subtrees. Existing debt enters through a checked-in baseline:
baseline findings remain visible, while newly introduced violations fail.
Debt is removed by shrinking the baseline until the corresponding rule can be
enforced without exceptions.

Skills are adapters at this seam. A repository skill may audit, explain,
prepare a migration manifest, and run verification, but the contract and
validator remain the source of truth. The repository-local `kundur-round`
skill remains canonical for the research-round process. External research
skills provide explicitly invoked writing or review perspectives and do not
reserve rounds or claims, change programme gates, or create another ledger.

## Consequences

- Repository policy changes have one locality and one test surface.
- Historical debt can be ratcheted down without making initial adoption
  unusable.
- Pre-commit and CI run the same implementation instead of copying rules.
- A future hygiene skill stays thin and can be replaced without changing
  enforcement.
- The governance contract becomes a maintained repository asset and must
  evolve with directory and delivery-line changes.
