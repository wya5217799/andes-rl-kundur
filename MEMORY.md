# MEMORY index

This file is the index for the `memory/` subsystem. See the design spec:
`docs/superpowers/specs/2026-05-15-andes-research-workbench-design.md`.

## Layout

```
memory/
├── STATE.md              # auto-rendered, read first
├── claims/CLM-NNNN.md    # atomic facts (append-only)
├── rounds/RNN/           # plan.md + verdict.md (append-only)
├── handoffs/             # cross-session handoffs (append-only)
└── tools/                # validate.py + render.py (+ tests)
```

## Schema (claim frontmatter)

Required: `id`, `type` (finding|decision|correction), `trust` (V|S|T),
`status` (current|superseded|refuted), `statement`.

Optional: `round`, `supersedes`, `provenance`, `tags`.

Tool-managed (never write): `superseded_by`.

## Validator rules (hard, fail commit)

1. `id` unique across all claims
2. `supersedes: [X]` => X exists; tool auto-writes back edge
3. `status: current` => `superseded_by` is empty

Warnings (do not fail):
- forward/back edge symmetry
- `trust: V` requires non-empty `provenance`

## Workflow

```
# Start a new round
mkdir memory/rounds/R38
$EDITOR memory/rounds/R38/plan.md

# After running experiments, write verdict + claims
$EDITOR memory/rounds/R38/verdict.md
$EDITOR memory/claims/CLM-0040.md        # new finding
$EDITOR memory/claims/CLM-0041.md        # correction supersedes CLM-0005

# Validate (fix back edges) + render STATE
python memory/tools/validate.py --fix
python memory/tools/render.py

# Commit
git add memory/
git commit -m "round: R38 — <topic>"
```

## Append-only discipline

Substantive fields (`statement`, `provenance`, `supersedes`) NEVER edited.
To correct a claim, author a new claim with `type: correction` and
`supersedes: [old_id]`. Tool flips old claim to `status: superseded`.

## Stats (regenerate after migration)

See `memory/STATE.md` for current counts.
