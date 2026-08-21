# Domain docs

Single-context repo: domain language lives in `CONTEXT.md`; architecture
decisions live in `docs/adr/`.

- Use `CONTEXT.md` vocabulary for every domain term in output (issue title,
  refactor proposal, hypothesis, test name). Don't drift to synonyms the
  glossary explicitly avoids.
- Concept missing from the glossary is a signal: invented language
  (reconsider) or a real gap (open a `Q-NNNN` or flag it on the issue).
- If output contradicts an existing ADR, surface it explicitly:
  "Contradicts ADR-0001 (src layout) — worth reopening because …".
