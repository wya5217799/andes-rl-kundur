# andes-rl-kundur — AI Navigation

## Read this first
- `memory/STATE.md` — current state (auto-rendered)
- Latest `memory/handoffs/*.md` — ongoing work

## Memory subsystem (the novel part of this repo)

Three layers, four file kinds, two tools. Full design:
`docs/superpowers/specs/2026-05-15-andes-research-workbench-design.md`.

### When to write a new claim
After producing any of:
- A new numerical result you might cite (`type: finding, tags: [numerical]`)
- A correction or replacement of a prior number (`type: correction, supersedes: [...]`)
- A research-direction pivot (`type: decision`)

### When NOT to write a claim
- Throwaway debug output
- Intermediate values from a sweep (only the final selected value gets a claim)
- "Working hypotheses" you have not verified — use trust: S or trust: T,
  do not write trust: V without provenance

### Claim authoring template
```yaml
---
id: CLM-NNNN
type: finding | decision | correction
trust: V | S | T
status: current
statement: |
  <one-line citable claim>
round: RNN
provenance:
  - <path> @ <commit>
tags: [...]
---
```

### Tools
- `python memory/tools/validate.py` — check 3 rules + 2 warnings
- `python memory/tools/validate.py --fix` — auto-write back edges
- `python memory/tools/render.py` — regenerate STATE.md

Run `validate.py` before every commit. Run `render.py` after adding or
superseding claims.

## Code conventions

### ANDES = WSL only
See `scenarios/kundur/NOTES_ANDES.md`. Windows-side ANDES installs are
historical mis-installs; do not use them.

### Modifying env/andes
Read `scenarios/kundur/NOTES_ANDES.md` before changing any
`env/andes/*` or `scenarios/kundur/train_andes*.py`.

### Modifying paper_grade_axes.py
Asset 4 is paper-cited. Any change requires a new round + new claim
documenting the ranker version.

## Active research rules

- Caveman Chinese for verdict/plan files (per user preference, see
  `_legacy/CONTEXT.md` style)
- Single ANDES session at a time on Windows (16C/32T workstation), max 3
  parallel WSL python processes
- Default model env: `andes_vsg_env_v4` (paper-faithful H₀=100)
