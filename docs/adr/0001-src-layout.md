# ADR-0001: Adopt `src/andes_rl_kundur/` standard src-layout

- **Status:** Accepted
- **Date:** 2026-05-16
- **Deciders:** repository owner (during `/grill-with-docs` session)

---

## Context

Through R36 (2026-05-08), this repository accumulated code as a flat
collection of top-level directories at the repo root:

```
andes-rl-kundur/
├── agents/         ← active code
├── env/            ← active code
├── evaluation/     ← active code (paper-cited)
├── probes/         ← active code (research infra)
├── scripts/        ← active code (eval entry points + 36 archived round drivers)
├── scenarios/      ← active code (entry points + contract.py constants)
├── utils/          ← active code (with broken imports)
├── config.py       ← active code (partially superseded V1 dead params)
├── paper/          ← frozen IEEE manuscript (36 MB)
├── dissertation/   ← frozen UNNC FYP
├── memory/         ← claim ledger infrastructure
├── results/        ← gitignored except whitelist/
├── docs/           ← spec + handoff documents
└── _legacy/        ← frozen 2026-05-08 snapshot
```

The paper is finished. The decision under review here arises while
preparing the codebase for the next research phase ("研究出更好的
agent" — escape the 0.137 multi-seed attractor, exceed HAWE's 0.439
ceiling). Three structural facts force a decision:

1. **The repo currently has no package boundary.** Internal modules
   import each other via `sys.path.insert(0, ROOT)` plus bare names
   (`from agents.sac import SACAgent`). There is no `pyproject.toml`,
   no installable package, no version pinning. Adding `pip install -e .`
   workflow requires choosing a layout now.

2. **Top-level mixes six semantic classes.** Active code, frozen
   artifacts, infrastructure, data, documentation, and legacy snapshots
   all sit as sibling directories. A new contributor cannot tell, by
   looking, which directories are alive.

3. **Continued research will add algorithms.** AD-07 introduces a
   `BaseAgent` abstraction to allow TD3/PPO experiments without
   rewriting the train loop. Without a clear package home, those
   new files will land in another flat top-level directory, repeating
   the structural problem.

## Considered options

### Option A — Leave structure flat, document with README table

Annotate the top level with a "what each directory is" table. No file
moves. No import changes.

- **Pros:** zero migration risk; preserves `git blame` perfectly;
  no external link breakage; smallest diff.
- **Cons:** structural problem persists in code, only papered over in
  README; not pip-installable; adds nothing for future extensibility.

### Option B — `src/` as a flat namespace, no package wrapper

```
src/
├── agents/
├── env/
├── evaluation/
├── probes/
├── scenarios/
├── scripts/
└── utils/
```

Imports stay `from agents.sac import ...`; require
`sys.path.insert(0, "src")` or `[tool.setuptools.packages.find]
where = ["src"]` in `pyproject.toml`.

- **Pros:** moderate migration; visually cleaner top level;
  intermediate step toward standard layout.
- **Cons:** still not a proper namespace — `agents`, `env`, `utils`
  are generic enough to collide with other packages in the same
  Python environment; not pip-installable as a single package
  with a clean name.

### Option C — Standard src-layout with named package

```
src/
└── andes_rl_kundur/
    ├── __init__.py
    ├── agents/
    ├── env/
    ├── evaluation/
    ├── probes/
    ├── scenarios/
    └── utils/
scripts/                  ← top-level entry points
├── train.py
├── eval_no_control.py
├── eval_ddic.py
├── eval_all_seeds.py
└── eval_ensemble.py
artifacts/                ← top-level frozen products
├── paper/
└── dissertation/
```

Imports become `from andes_rl_kundur.agents.sac import SACAgent`.

- **Pros:**
  - Standard Python packaging — works with `pip install -e .`,
    publishable to a private index, importable from sibling repos
    (e.g. a follow-on `andes-rl-smib`).
  - Namespace prefix prevents collisions in shared venvs.
  - Top-level `scripts/` makes entry points discoverable —
    a new user immediately sees what is runnable.
  - `artifacts/` cleanly separates frozen outputs from active code.
- **Cons:**
  - Largest migration: every internal import gains
    `andes_rl_kundur.` prefix.
  - `memory/claims/CLM-*.md` provenance entries that point to the
    old paths (e.g. `agents/sac.py @ <commit>`) remain accurate
    against historical commits but require new prefix for any
    newly-written claim.
  - External references (paper appendix URLs, dissertation supplementary
    links) need verification — though the user has explicitly accepted
    this risk and noted the old git history is preserved on `main`.

## Decision

**Adopt Option C.** Package name: `andes_rl_kundur` (matches repo name).
Entry-point scripts live at the top-level `scripts/` directory and are
not part of the installable package. Frozen products (`paper/`,
`dissertation/`) move under `artifacts/`.

## Rationale

The decisive consideration is the stated future direction: continued
research targeting "更好的 agent." That work will:

- Introduce new algorithms (TD3, PPO, others) — needs a clear home
  inside the package, alongside SAC.
- Potentially fork into a sibling repo (`andes-rl-smib`,
  `andes-rl-ne39`) — namespace prefix prevents Python-side conflicts
  when both packages are installed in the same venv.
- Be referenced from external write-ups (follow-on papers, blog posts,
  conference talks) — `pip install andes-rl-kundur` is a stable
  reference; `cd repo && PYTHONPATH=src python ...` is not.

Option A defers the structural problem without solving it. Option B is
strictly worse than C — same migration cost (because internal paths
still move under `src/`), but no namespace protection. Once we are
paying the migration cost, paying it once for the standard layout is
correct.

The migration cost itself is mitigated by:

- AD-12 phasing — Phase 1 keeps structure flat while cleaning logic,
  so Phase 2 is a pure rename operation.
- AD-11 verification — `paper_grade_axes.py` JSON outputs must be
  bit-identical before and after Phase 2, providing a sharp acceptance
  test for the rename.
- AD-14 R37 round — paper-cited file relocations are documented in
  the claim ledger.

## Consequences

### Required follow-ups

- Create `pyproject.toml` with `[tool.setuptools.packages.find] where = ["src"]`
  and project metadata.
- Update `CLAUDE.md` to reflect new paths (in Phase 2's documentation pass).
- Update `scenarios/kundur/NOTES_ANDES.md` paths.
- Update root `README.md` to point to `pip install -e .` workflow.
- Issue claim `CLM-00XX` in R37 verdict recording the relocation +
  JSON-equivalence proof.

### Reversible / irreversible

- **Reversible at low cost:** any sub-decision within the package
  (renaming a submodule, adding a new submodule, moving a file
  between submodules) — `git mv` + import update.
- **Reversible at moderate cost:** flipping back to Option B (drop
  the `andes_rl_kundur` namespace, leave `src/<submodules>/` flat) —
  one global find-and-replace on imports.
- **Effectively irreversible:** going back to Option A (everything
  flat at root) — would discard all the namespace cleanup work and
  re-import-rewrite everything. Don't.

### What this ADR does not commit to

- The exact internal structure of `src/andes_rl_kundur/agents/` —
  whether `BaseAgent` lives there or in `src/andes_rl_kundur/core/`
  is a sub-decision (AD-07).
- Whether `scenarios/contract.py` moves under `src/.../scenarios/contract.py`
  (planned: yes) or merges into a shared `constants.py` — open.
- Whether to publish to a private index — not committed; the layout
  supports it but does not require it.

## References

- `_legacy/CONTEXT_AD01-AD14.md` § AD-09 — short form of this decision.
- `_legacy/CONTEXT_AD01-AD14.md` § AD-10 — `artifacts/` reorganization (companion decision).
- `_legacy/CONTEXT_AD01-AD14.md` § AD-12 — two-phase execution plan that makes this
  migration safe.
- `_legacy/CONTEXT_AD01-AD14.md` § AD-14 — R37 documenting round for paper-cited file moves.
- Python Packaging User Guide, *src layout vs flat layout*:
  https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/
