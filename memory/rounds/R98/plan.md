# R98 plan — Memory subsystem: Note entity + legacy archive ingest

**Date**: 2026-05-19
**Type**: infrastructure (schema + tooling + data migration, no experiment)
**Status**: complete (close concurrently with this plan)

## Trigger

User flagged that R39's intentional exclusion of `handoffs/` / `docs/adr/` /
`docs/eng-notes/` / `_legacy/` from the memory schema had become a research
liability: AI sessions could not surface prior research without manual file
archaeology. User goal (2026-05-19): "让对话能感知所有过去实验和数据，为了科研".

## Decisions (locked via brainstorming session 2026-05-19)

| ID | Decision |
|----|----------|
| A | New entity kind `Note` (`NOTE-NNNN`) as index layer; does NOT replace original files |
| B | `memory/notes/` directory; original `handoffs/` / `docs/` / `_legacy/` paths unchanged |
| C | Double-layer topics: 8 closed top-level + free sub-tags |
| D | STATE.md `## Archive Index` section: 9-row cap, query-hint footer |
| E | 5 hard rules (N1-N5) + 2 cross-entity warnings (X1, X2) in validate.py |
| F | 4 migration waves: ADR → handoffs → eng-notes → legacy + Wave 4 sweep |
| G | Pre-flight STATE.md hygiene: close R45/R90/R91 if stale |
| H | Lazy claim extraction: notes are index; claims come later when needed |
| I | No back-reference into source files (spec §9-3): lossless preservation |

## Implementation

- Plan: [docs/superpowers/plans/2026-05-19-memory-system-notes-ingest.md](../../../docs/superpowers/plans/2026-05-19-memory-system-notes-ingest.md)
- Spec: [docs/superpowers/specs/2026-05-19-memory-system-notes-ingest-design.md](../../../docs/superpowers/specs/2026-05-19-memory-system-notes-ingest-design.md)
- Branch: `feature/memory-notes-ingest`
- Sub-skill chain: brainstorming → writing-plans → subagent-driven-development

## Out of scope

- Auto-summarization of notes via LLM (Wave 0-4 summaries are human-written for accuracy)
- Note → claim auto-extraction (lazy; do it when a future round needs to cite a Key Fact)
- Indexing GitHub PRs / commit messages (would multiply note count by 10×)
