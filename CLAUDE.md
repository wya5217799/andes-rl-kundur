# andes-rl-kundur — AI navigation

## Read first

- `CONTEXT.md` — glossary + 14 architecture decisions (AD-01 … AD-14)
- `docs/adr/0001-src-layout.md` — long-form rationale for the src layout
- `memory/STATE.md` — auto-rendered current research state
- Latest `memory/handoffs/*.md` — what was in progress at last handoff

## Repository layout (post 2026-05-16 refactor)

```
andes-rl-kundur/
├── src/andes_rl_kundur/      Python package (library code)
│   ├── agents/               SAC + SAC_CTDE + BaseAgent Protocol
│   ├── env/andes/            V4 self-contained env + base_env
│   ├── evaluation/           paper_grade_axes (Asset 4, paper-cited)
│   ├── probes/               andes_common reuse layer
│   ├── scenarios/contract.py KUNDUR domain constants
│   ├── utils/monitor.py      TrainingMonitor diagnostics
│   └── config.py             SAC hyperparameters
├── scripts/                  Runnable entry points
│   ├── train.py
│   ├── eval_no_control.py
│   ├── eval_ddic.py
│   ├── eval_ensemble.py
│   ├── eval_all_seeds.py
│   └── _archive/             Frozen round drivers (R01..R36)
├── tests/                    pytest regression tests
├── artifacts/                Frozen outputs (paper/, dissertation/)
├── memory/                   Claim ledger + rounds + handoffs
├── docs/                     ADRs, engineering notes, design specs
├── results/                  Gitignored except whitelist/
├── _legacy/                  Frozen ancestors of refactored modules
└── pyproject.toml            Package metadata + tool config
```

## Memory subsystem (novel infrastructure)

Three layers, four file kinds, two tools. Full design:
`artifacts/dissertation/docs/superpowers/specs/2026-05-15-andes-research-workbench-design.md`
(if not present locally, see `docs/superpowers/specs/`).

### When to write a new claim

After producing any of:
- A new numerical result you might cite (`type: finding, tags: [numerical]`)
- A correction or replacement of a prior number (`type: correction, supersedes: [...]`)
- A research-direction pivot (`type: decision`)

### When NOT to write a claim

- Throwaway debug output
- Intermediate values from a sweep (only the final selected value gets a claim)
- "Working hypotheses" you have not verified — use `trust: S` or `trust: T`,
  do not write `trust: V` without provenance

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
- `python memory/tools/render.py` — regenerate `memory/STATE.md`

Run `validate.py` before every commit. Run `render.py` after adding or
superseding claims.

## Code conventions

### ANDES = WSL only

See `docs/eng-notes/NOTES_ANDES.md`. Windows-side ANDES installs are
historical mis-installs; do not use them.

### Modifying the env

Read `docs/eng-notes/NOTES_ANDES.md` before changing any
`src/andes_rl_kundur/env/andes/*` or `scripts/train.py`. The
`AndesMultiVSGEnvV4` class is paper-faithful and silent-inheritance
bug fixed (R37 / CLM-0040: `ZERO_G4_INERTIA = True` is now explicit).

### Modifying paper_grade_axes.py

Asset 4 is paper-cited. Any change requires a new round + new claim
documenting the ranker version. Even a path-only relocation is logged
(R37 recorded the 2026-05-16 move to `src/andes_rl_kundur/evaluation/`).

## Active research rules

- Caveman Chinese for verdict/plan files (per user preference, see
  `_legacy/CONTEXT.md` style)
- Single ANDES session at a time on Windows (16C/32T workstation), max
  3 parallel WSL python processes
- Default model env: `andes_vsg_env_v4` (paper-faithful H₀=100,
  ZERO_G4_INERTIA=True for reproducibility of paper numbers)
- Regression: `tests/test_v4_env_regression.py` must stay green at
  1e-9 tolerance against the PRE_REFACTOR baseline JSONs
