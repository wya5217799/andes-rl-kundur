# ADR-0014: Keep a project-owned foundation graph outside research authority

- **Status:** Accepted
- **Date:** 2026-08-09

## Context

Understanding this repository requires transferable power-system, control,
simulation, and research-method foundations that are not explained by its
project glossary or file graph. Reusing `.understand-anything/` would make
files and symbols the learning units; reusing `lessons/` would mix canonical
knowledge with generated teaching output; reusing `memory/` or `paper/` would
create a second research authority.

## Decision

Maintain one demand-grown Project Learning Registry under `learning/`.
Foundation Atoms are bilingual transferable concepts connected by acyclic
`requires` edges and linked to project stages by `used-in` plus typed live
anchors. Project-local names, concrete results, claims, full explanations,
teaching-method choices, and inferred learner mastery stay in their existing
homes. The global tutor may update this registry for repository-learning
intent, while ordinary Chat content remains a separate asset scope unless the
user explicitly requests a repository import and the sources are revalidated.

## Consequences

- Repository questions can enrich one shared learning graph without an
  exhaustive initial scan.
- `learning/` is registered as an active non-authoritative teaching delivery;
  it cannot support a paper claim or override source and evidence.
- `lessons/` remains generated teaching output, and Teaching Methods remain
  globally reusable without binding them to project atoms.
