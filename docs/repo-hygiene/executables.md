# Executable lifecycle

The machine-readable source is `docs/repo-hygiene/contract.json`. This document
explains the roles that its executable classifiers enforce.

## Analysis seam

- Reusable analysis implementation lives behind package interfaces under
  `src/andes_rl_kundur/`.
- A conclusion-affecting, question-specific investigation lives in `probes/`
  and records its round/results/feed provenance.
- `scripts/` contains stable execution adapters for training, evaluation,
  maintenance, and round orchestration. An adapter may call analysis
  implementation; it does not hide scientific selection or validity logic.
- Manuscript figure builders are presentation adapters. They consume declared
  sealed evidence and do not choose cases or repair validity post hoc.

## States

| State | Meaning | Transition |
|---|---|---|
| `active` | Supported entrypoint with a current caller | Remains tested and documented |
| `frozen` | Preserved executable from completed work | Becomes `archived` after provenance-safe relocation |
| `archived` | Historical implementation retained only for audit | Immutable except path/index repair |
| `generated` | Recreated from another declared source | Kept out of source-control entrypoint checks |
| `exempt` | Tool-owned executable outside project policy | Requires an explicit contract entry |

Closing a round freezes its round-specific executable. Relocation happens only
after every live caller and provenance pointer is accounted for; a migration
map records any path change. When the same implementation pattern is needed a
second time, it is promoted behind a package interface and the entrypoints stay
thin.

## Enforcement

`python scripts/repo_health.py check` discovers maintained scripts, research
probes, round-local runners, and registered figure builders. Each must match a
lifecycle classifier. A newly added, unclassified entrypoint is an error. An
`active` entrypoint owned by a completed round is reported as an archive
candidate. Figure adapters also declare evidence paths; the validator checks
that the evidence exists and that the builder source references it. A frozen
figure whose source data is not already a structured result consumes a reviewed
evidence manifest containing the selected values, claim mapping, and source
hashes; the builder rejects source drift before rendering.

Maintained ANDES entrypoints are launched through
`python scripts/andes_scratch.py <entrypoint> ...`. The adapter changes the
child working directory, preserving ANDES scratch files under `tmp/andes/`.
Known input/output path flags are anchored to the repository before launch, so
relative checkpoint and result paths retain their direct-entrypoint semantics.
