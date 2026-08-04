---
id: NOTE-NNNN
source: handoff          # handoff | eng-note | adr-rationale | legacy | session-report
source_path: memory/handoffs/<filename>.md   # repo-relative; must exist on disk
date: YYYY-MM-DD         # ORIGINAL creation date of source (not ingest date)
related_rounds: [R<N>, R<N>]
topics: [<top-level>, <free-sub-tag>, <free-sub-tag>]
                         # Top-level (closed): env, training-infra, evaluation,
                         #                     agents, scenarios, paper,
                         #                     memory-system, pipeline
extracted_claims: []     # CLM-NNNN ids; empty initially, filled lazily when a
                         # round promotes a Key Fact into an atomic claim
status: ingested         # ingested | partially-extracted | fully-extracted
---

## Summary
<3-5 sentences. An AI scanning STATE.md's Archive Index should be able to
decide from this paragraph alone whether to open source_path.>

## Key facts (claim candidates)
- <Bullet 1 — if later promoted to claim, append `→ CLM-NNNN`>
- <Bullet 2>

## Related pointers
- <Pointers only; this section is not task state. Promote unresolved work to
  Q-NNNN or the selected manuscript LINE.md.>
