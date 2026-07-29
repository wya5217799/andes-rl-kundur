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

`python scripts/repo_health.py check` discovers top-level script entrypoints and
requires each to match a lifecycle classifier. A newly added, unclassified
entrypoint is an error. An `active` entrypoint owned by a completed round is
reported as an archive candidate.
