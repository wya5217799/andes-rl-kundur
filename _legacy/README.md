# _legacy/

Frozen source-of-truth documents from the predecessor repository
`Multi-Agent  VSGs`. These files are **NOT the current state** — the current
state is in `memory/claims/`, `memory/rounds/`, and `memory/STATE.md`.

These files are retained for:
1. **Audit trail** — verifying that the migrated claim ledger faithfully
   represents the original research record.
2. **Reflection writing** — paper/dissertation §VI reflection can mine these
   for context that the lite migration did not extract.
3. **Forensic** — if any claim's provenance is questioned, the original
   document is here.

**Do not edit these files.** If a fact in `_legacy/` contradicts a current
claim, the current claim is authoritative (and ideally cites the legacy
provenance). File a `type: correction` claim if reconciliation is needed.

## Files

| File | Original purpose |
|------|------------------|
| `RESEARCH_TRAIL.md` | R01-R37 causal trail with 6 拐点 (caveman style) |
| `CONTEXT.md` | ANDES track engineering context + anti-patterns |
| `ANDES.md` | Original entry-point doc |
| `audits/` | Cross-round audit reports that did not map cleanly to a single round |
