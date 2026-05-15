# andes-rl-kundur — Research Workbench + Claim Ledger Memory System

**Date**: 2026-05-15
**Status**: APPROVED (brainstorming)
**Type**: New repo migration + novel memory subsystem design
**Decision authority**: User
**Spec target audience**: planner agent (next step: writing-plans skill)

---

## §0 Purpose & Scope

Create a new GitHub repository `andes-rl-kundur` (private) that:

1. **Inherits** all ANDES-related assets from current project `Multi-Agent  VSGs` plus useful files from `毕业论文/`.
2. **Continues as a research workbench** (not a frozen archive) — new rounds, ablations, post-review revisions, journal resubmissions will happen here.
3. **Replaces** the current scattered memory (CONTEXT.md / RESEARCH_TRAIL.md / MEMORY.md / round_NN_verdict.md × 30 / handoff_vNN.md) with a **Claim Ledger** memory system that:
   - Maintains a single trustworthy research timeline
   - Solves number-drift across documents (4 versions of headline: 0.613 → 0.607 → 0.554 → 0.444)
   - Drops new-conversation onboarding cost from ~2000 lines to ~50 + 1 handoff
   - Provides traceable provenance from data → claim → paper sentence

**Out of scope**: Refactoring ANDES code during migration. Refactoring scripts. Cleaning dead code. Removing old version files. These wait until the new repo settles and a new round explicitly takes them on.

**Non-goal**: Build a full knowledge graph database. The system is markdown-first, git-friendly, AI-writeable. Minimize tooling.

---

## §1 Architecture — Three Layers

```
┌──────────────────────────────────────────────────────────────────┐
│  Layer 3  Derived Views   (auto-regenerated, read-only)          │
│  memory/STATE.md  (~50 lines, AI onboarding entry)               │
│         ▲                                                         │
│         │  rendered by `memory/tools/render.py` from Layer 1+2   │
├─────────┴─────────────────────────────────────────────────────────┤
│  Layer 2  Round Events    (one folder per round, free-form md)   │
│  memory/rounds/RNN/  ├ plan.md  └ verdict.md                     │
│         ▲                                                         │
│         │  each round produces / supersedes claims               │
├─────────┴─────────────────────────────────────────────────────────┤
│  Layer 1  Claim Ledger    (atomic, citable, append-only)         │
│  memory/claims/CLM-NNNN.md   (YAML frontmatter + optional body)  │
└──────────────────────────────────────────────────────────────────┘
```

### Three invariants

1. **Claim files are append-only for substantive fields** — never delete or edit `statement`, `provenance`, `supersedes`. To negate or update, create a new claim with `supersedes: [...]` or `type: correction`. Tool may write `status` and `superseded_by` on the predecessor (book-keeping fields only).
2. **Round is the bundling event** — claims belong to rounds; round folders never modify each other (no schema-level round-to-round edges, no editing of earlier verdicts). Prose may freely cross-reference earlier rounds. New rounds append; never modify earlier round folders.
3. **Views are pure derivations** — anything in Layer 3 is regenerated. Editing Layer 3 manually is forbidden.

---

## §2 Claim Schema

### File location
```
memory/claims/CLM-NNNN.md       # flat, never nested by round
```

### Frontmatter

```yaml
---
# Required 5 ----------------------------------------
id: CLM-0042
type: finding                 # finding | decision | correction
trust: V                      # V verified | S speculative | T todo-verify
status: current               # current | superseded | refuted
statement: |
  R21 V4 h50_s49 6-axis = 0.444 (4.04× no_ctrl 0.104)

# Optional 4 ----------------------------------------
round: R30                    # which round produced this
supersedes: [CLM-0017]        # required when type=correction
provenance:                   # required when trust=V (warning only otherwise)
  - scripts/research_loop/eval_paper_spec_v2.py @ 2d9708e
  - results/andes_paper_alignment_6axis_2026-05-07.json
tags: [headline, numerical, 6-axis, §V-A]

# Tool-managed (humans do not write) -----------------
superseded_by: []
---

# Optional body: derivation, full table, figure refs, context prose
```

### Field semantics

| Field | Required | Notes |
|---|---|---|
| `id` | yes | `CLM-NNNN` monotonic, never reused |
| `type` | yes | `finding` (new fact) / `decision` (pivot) / `correction` (overrides prior) |
| `trust` | yes | `V` verified / `S` speculative / `T` todo-verify. No `C` (corrected) — that's encoded structurally via `type: correction` + `supersedes` |
| `status` | yes | `current` / `superseded` / `refuted`. Tool flips to `superseded` when a later claim names this in its `supersedes` |
| `statement` | yes | Single-line citable claim. The form paper would cite |
| `round` | optional | Empty when claim is a standalone paper fact not derived from a round |
| `supersedes` | optional | Required when `type: correction` |
| `provenance` | optional | Required for `trust: V` (warning-level otherwise). Format: `<path> @ <commit>` or `<path>` |
| `tags` | optional | Free list. `§X-Y` tags double as paper anchors (no separate `paper_anchor` field) |
| `superseded_by` | tool-managed | Humans never write. Tool auto-fills back edge |

### Three type uses

**finding** — new fact (numerical, causal, observation, audit, incident — all distinguished by `tags`):
```yaml
type: finding
tags: [numerical, headline, 6-axis, §V-A]
```

**decision** — route change (6 拐点 emerge naturally from this type):
```yaml
type: decision
statement: ANDES path RE-OPENED → COMPLETED (V4 reached paper-grade alignment)
tags: [pivot]
```

**correction** — supersedes or refutes a prior claim (absorbs old refutation + numerical supersede roles):
```yaml
type: correction
supersedes: [CLM-0017]
statement: R21 6-axis = 0.444 (post r30 ranker N1c geo-mean fix; was 0.613)
```

### Validator rules (3 only)

1. `id` is unique
2. `supersedes: [X]` appears → X must exist; tool auto-writes `superseded_by += [current_id], status = superseded` on X
3. `status: current` ⇔ `superseded_by` is empty (mutex: a current claim has not been superseded)

Plus 1 warning-level check: forward/back edge symmetry (CLM-X.supersedes ⊃ {Y} ⇒ CLM-Y.superseded_by ⊃ {X}). Plus 1 warning-level check: `trust: V` should have non-empty `provenance`.

---

## §3 File Layout

```
andes-rl-kundur/
├── README.md                          # public-facing (private repo, but README still matters)
├── CLAUDE.md                          # project nav, points AI to memory/STATE.md as entry
├── MEMORY.md                          # index for memory/ subsystem (lean, ~80 lines)
├── .gitignore                         # results/ ignored except whitelist
├── LICENSE                            # TBD (private repo, can defer)
│
├── memory/                            # the novel memory subsystem
│   ├── STATE.md                       # auto-rendered, ~50 lines, single onboarding entry
│   ├── claims/
│   │   ├── CLM-0001.md
│   │   ├── CLM-0002.md
│   │   └── …                          # flat ledger, ~30-50 at migration end, grows over time
│   ├── rounds/
│   │   ├── R01/
│   │   │   ├── plan.md                # free-form
│   │   │   └── verdict.md             # free-form, references CLM-IDs
│   │   ├── R02/ … R37/
│   ├── handoffs/
│   │   ├── 2026-05-08-andes-path-closure.md
│   │   ├── 2026-05-08-handoff-v17.md
│   │   └── …
│   └── tools/
│       ├── validate.py                # ~80 LOC, runs 3 validator rules + 2 warnings
│       └── render.py                  # ~150 LOC, regenerates STATE.md
│
├── env/andes/                         # 8 files (v1-v4 + NE39 + base)
├── scenarios/kundur/                  # train_andes*.py × 5
├── scenarios/new_england/             # train_andes.py (NE39 future work)
├── probes/andes_common/               # 4 reusable utility modules
├── scripts/research_loop/             # r01-r36 probes + eval_*.py (selectively kept)
│   └── _archive/                      # one-shot scripts no longer in active use
├── evaluation/paper_grade_axes.py     # Asset 4 (six-axis ranker)
├── agents/                            # SAC / MA manager / networks (ANDES train dep)
├── utils/monitor.py                   # training monitor
├── config.py                          # ANDES section only; Simulink/ODE sections dropped
│
├── paper/
│   ├── main.tex
│   ├── figure_scripts/                # 21 scripts
│   └── figures/                       # ~36MB, kept in git (figures are paper-ready)
│
├── dissertation/                      # from 毕业论文/dissertation/
│   ├── main.tex
│   ├── figures/
│   ├── refs.bib
│   ├── CONTEXT.md                     # from 毕业论文/CONTEXT.md
│   └── WRITING_STANDARD.md
│
├── docs/
│   └── paper/
│       ├── kd_4agent_paper_facts.md
│       └── andes_replication_status_2026-05-07_6axis.md
│
├── results/                           # GITIGNORED except whitelist (see §4.2)
│   ├── MANIFEST.md                    # tracks what exists locally; committed
│   ├── whitelist/                     # key ckpts + eval JSON, committed
│   └── …                              # everything else local-only
│
└── _legacy/                           # source-of-truth originals retained for audit
    ├── RESEARCH_TRAIL.md              # from current repo, frozen
    ├── CONTEXT.md
    └── ANDES.md
```

### Doc category discipline (prevent classification bloat)

Only **4 doc kinds** in `memory/`:

| Doc | Schema? | Mutability |
|---|---|---|
| `claims/CLM-NNNN.md` | yes (frontmatter) | append-only (substantive fields) |
| `rounds/RNN/plan.md` | no | append-only after round closes |
| `rounds/RNN/verdict.md` | no | append-only after round closes |
| `handoffs/YYYY-MM-DD-*.md` | no | append-only |

No separate folders for audits, incidents, pivots, anti-patterns, decisions. These are encoded as tags on claims:
- audit → `type: finding, tags: [audit]`
- incident → `type: finding, tags: [incident]`
- pivot → `type: decision`
- anti-pattern → `type: correction` with `supersedes: [old_wrong_claim]`

---

## §4 Migration Strategy

### §4.1 Asset migration (sources → new repo)

Sources: current project at `C:\Users\27443\Desktop\Multi-Agent  VSGs\` and `C:\Users\27443\Desktop\毕业论文\`.

| Source | Destination in `andes-rl-kundur` | Action |
|---|---|---|
| `env/andes/*` (8 files) | `env/andes/` | direct copy |
| `scenarios/kundur/train_andes*.py` (5) | `scenarios/kundur/` | direct copy |
| `probes/andes_common/*` (4 modules) | `probes/andes_common/` | direct copy |
| `scripts/research_loop/*` | `scripts/research_loop/` | **triage**: active r01-r36 + eval_v4_*.py kept; one-shot scripts → `scripts/research_loop/_archive/` |
| `evaluation/paper_grade_axes.py` | `evaluation/` | direct copy |
| `agents/sac*.py`, `ma_manager.py`, `networks.py` | `agents/` | direct copy |
| `config.py` | `config.py` | **trim**: drop ODE/Simulink sections, keep ANDES only |
| `utils/monitor.py` | `utils/` | direct copy |
| `paper/main.tex`, `paper/figure_scripts/*` (21), `paper/figures/*` (36MB) | `paper/` | direct copy |
| `毕业论文/dissertation/*` | `dissertation/` | direct copy (main.tex + figures + bbl + refs.bib) |
| `毕业论文/CONTEXT.md`, `WRITING_STANDARD.md` | `dissertation/CONTEXT.md`, `dissertation/WRITING_STANDARD.md` | direct copy |
| `docs/paper/kd_4agent_paper_facts.md` | `docs/paper/` | direct copy |
| `docs/paper/andes_replication_status_2026-05-07_6axis.md` | `docs/paper/` | direct copy |
| `quality_reports/research_loop/round_NN_*.md` (~37 rounds) | `memory/rounds/RNN/` | direct copy, rename `round_NN_plan.md` → `RNN/plan.md` |
| `quality_reports/research_loop/audits/*`, `incidents/*` | `memory/rounds/RNN/` (inline into hosting round) or referenced via tags | merge into hosting round folder |
| `quality_reports/handoff/*andes*` | `memory/handoffs/YYYY-MM-DD-*.md` | direct copy + rename |
| `毕业论文/plan/2026-05-08*v17*` and master index | `memory/handoffs/` | direct copy |
| `RESEARCH_TRAIL.md`, `CONTEXT.md`, `ANDES.md` | `_legacy/` | preserve frozen as audit trail |

**Explicitly not migrated**: ODE backend (`env/ode/`), Simulink backend (`env/simulink/`, `scenarios/*/train_simulink.py`, `engine/`, `slx_helpers/`), Simulink-specific docs.

### §4.2 results/ strategy (whitelist mode)

`.gitignore` excludes all of `results/` except an explicit whitelist:

- `results/MANIFEST.md` — committed, indexes every dir/file with: round source, artifact hash, local path, size
- `results/whitelist/` — committed, contains:
  - R21 best.pt (lucky single 0.444)
  - R30 HAWE recipe (w8515 / w9802 ensemble configs)
  - `andes_paper_alignment_6axis_2026-05-07.json` (post-fix headline ranking)
  - no_control baseline eval JSON
  - 2-3 additional ckpts cited in paper §V/§VI

Everything else (per-step trajectory dumps, per-seed full results, intermediate eval JSON) is local-only. MANIFEST.md is the discovery surface; users with the raw data attach it via a sibling local dir.

Fallback: if whitelist grows past ~500MB, switch to git-LFS for `results/whitelist/`.

### §4.3 Knowledge sedimentation (lite, 30-50 claims)

Targeted claim extraction from existing artifacts. Coverage:

1. **Headlines** (~8 claims):
   - Pre-fix headlines: CLM for 0.613, 0.607, 0.554 (all `status: superseded`)
   - Post-fix headlines: 0.444 (R21), 0.439 (HAWE w9802), 0.104 (no_control), 4.04× ratio — all `type: correction, status: current`
   - Multi-seed attractor 0.137±0.005 across H₀×seed×ckpts
   - These form the **headline drift chain** demonstrating the system's core value

2. **6 拐点 decisions** (6 claims, type=decision):
   - R06 axes.py Bug-A discovery → ranker fix
   - R10-R17 V4 env creation
   - R21 V4_h50_s49 lucky single 0.613 (later superseded → 0.444)
   - R24 multi-seed reproduction reveals R21 outlier
   - R30 HAWE ensemble breakthrough (5 bespoke Asset 5)
   - r30 ranker N1c fix → final headline lock-in

3. **5 bespoke assets** (5 claims, type=finding, tags=[asset]):
   - MCP Simulink toolkit
   - Simulink-as-RL bridge
   - TDD probe layer (probes/andes_common)
   - Six-axis ranker (evaluation/paper_grade_axes.py)
   - HAWE Heterogeneous Actor Weighted Ensemble

4. **Anti-patterns / corrections** (~10 claims, type=correction):
   - From `CONTEXT.md §2` table: V3 governor wiring claimed working but DAE_INACTIVE; V4 H₀=10 vs actual H₀=100; settling=∞ truncation bug; etc.
   - Each refutes a prior implicit-belief claim (which we seed with `trust: S` to represent "what we used to think")

5. **Paper-cited facts** (~10 claims, type=finding, tags=[§X-Y]):
   - Disclosed deviations (3 items: action range 33×, φ 2000×, calibrated Pm_step)
   - Per-agent dominance pattern (§ssec:dominance)
   - LS1 vs LS2 asymmetry
   - Cross-platform 1.42× residual hypothesis

Workload estimate: ~5 hours total. Each claim takes 5-15 min (read source, extract statement, fill provenance, tag).

### §4.4 GitHub repo creation

- **Name**: `andes-rl-kundur`
- **Visibility**: private
- **Initial branch**: `main`
- **First commit policy**: large initial commit acceptable (this is migration, not feature work)
- **LICENSE**: deferred (private repo; decide at publication time)
- **README.md**: brief — what the repo is, where to start (CLAUDE.md → memory/STATE.md), how to onboard a new contributor or new AI session

### §4.5 Migration execution order

```
Step  Task                                                  Est
─────────────────────────────────────────────────────────────────
1     Scaffold new repo skeleton (dirs + empty files)       0.5 h
2     Write memory/tools/validate.py (3 rules + 2 warns)    1.0 h
3     Write memory/tools/render.py (STATE.md generator)     1.5 h
4     Test tools with 3 fixture claims                      0.5 h
5     Asset copy: env, scenarios, probes, agents, utils     0.5 h
6     Asset copy: paper, dissertation, docs/paper           0.5 h
7     Trim config.py (drop ODE/Simulink sections)           0.5 h
8     .gitignore + results/MANIFEST.md template +
      results/whitelist/ population                          1.0 h
9     memory/rounds/ population (37 round dirs + copy)      0.5 h
10    memory/handoffs/ population                           0.5 h
11    _legacy/ population (RESEARCH_TRAIL etc.)              0.2 h
12    Knowledge sedimentation: 30-50 lite claims             5.0 h
13    Run validate.py, fix issues                           0.5 h
14    Run render.py → STATE.md                              0.1 h
15    Sanity-check STATE.md numbers vs handoff_v17          0.5 h
16    Write README.md, CLAUDE.md, MEMORY.md                 1.5 h
17    git init, gh repo create --private, first push         0.5 h
─────────────────────────────────────────────────────────────────
                                                       ≈ 14.8 h
```

---

## §5 Non-functional considerations

### Maintainability (primary constraint per user)

- Every claim costs 5-15 min to write; ~30 sec to read
- Tool surface is 2 scripts (~250 LOC total); no CLI command sprawl
- Schema: 5 required + 4 optional + 1 tool-managed = 10 fields max
- Validator: 3 hard rules + 2 warnings
- View layer: 1 file (STATE.md); no fan-out into multiple derived dirs
- Doc kinds in memory/: 4 (claim, plan, verdict, handoff); no audits/incidents/pivots/anti-patterns subdirs

### AI session ergonomics

New conversation flow:
1. Read `memory/STATE.md` (~50 lines, auto-generated, current headlines + open decisions + latest round + latest handoff pointer)
2. Read latest `memory/handoffs/YYYY-MM-DD-*.md` (~150 lines, ongoing work)
3. Done. Ready to work.

Compared to current: 4-5 large docs × 200-500 lines each ≈ 2000+ lines. **~10× reduction.**

### Paper writing ergonomics

To write paper §V-A:
1. `grep "§V-A" memory/claims/*.md | grep "status: current"` → list of relevant claims
2. For each, read frontmatter `statement` and `provenance` → paragraph + footnote
3. Cite `CLM-NNNN` inline (paper conversion: `CLM-NNNN` → references list entry mapping)

No more manual cross-referencing of CONTEXT.md / RESEARCH_TRAIL.md / handoff for the current number.

### Number-drift defense (the original pain)

Walked through end-to-end in §2. The `supersedes` / `superseded_by` mutual edge + `status` flip + `STATE.md` filter = drift cannot reappear silently. The old number is preserved (for §VI reflection) but never appears as current.

### Append-only discipline trade-off

Pro: lineage is auditable; reflection writing has rich material; no destructive edits.

Con: writers must think about claim shape before writing. Validator catches structural errors but cannot prevent semantic errors (a wrong claim with `trust: V` is still wrong).

Mitigation: `trust: T` (todo-verify) is the default for any new claim until cross-checked. `trust: V` requires explicit promotion + provenance.

---

## §6 What this design does NOT include

- No knowledge graph / RDF / SPARQL — markdown + grep only
- No web UI / dashboard — STATE.md is the only rendered surface
- No automatic claim extraction from verdict prose — claims are written deliberately, not scraped
- No multi-user collaboration logic (assumes single primary author + AI sessions)
- No CI/CD beyond a pre-commit hook running validate.py
- No replay of full R01-R37 history (lite migration only; 120-200 claim full replay is a possible future round but not a migration step)
- No paper-pack auto-generator — query via grep, format manually for LaTeX
- No cross-repo links (the current `Multi-Agent  VSGs` repo remains independent; this is a fresh start, not a fork)

---

## §7 Open items deferred to implementation plan

1. Whether validate.py runs as a pre-commit hook or only manually (default: manual; revisit if violations occur)
2. Exact extraction template/checklist for the 30-50 lite claims (will be a step-by-step worksheet in the plan)
3. Whether `_legacy/` originals are added in a separate commit (recommended for clean diff) or in the initial commit
4. Whether to keep `_legacy/` in git long-term or move to a separate archive branch after one year
5. Whether to write a one-page `memory/README.md` explaining the schema + tools to a fresh contributor

---

## §8 Success criteria (after migration completes)

- `python memory/tools/validate.py` passes with zero hard errors
- `memory/STATE.md` exists, lists post-fix headlines (0.444, 0.439, 0.104), the latest round (R36 or R37), and the latest handoff
- A fresh Claude session reading only `CLAUDE.md` + `memory/STATE.md` + the latest handoff can correctly answer:
  - "What is the current paper headline number?" → 0.444 (not 0.613)
  - "What is HAWE?" → Asset 5, 5-bespoke ensemble, achieved 0.439 / 99.3% R21
  - "Is the ANDES path closed?" → Re-opened R21, currently COMPLETED
- 30-50 claims exist, with 8 headlines + 6 decisions + 5 assets + 10 anti-patterns + ~10 paper-cited facts
- The drift chain (0.613 → 0.554 → 0.444) is reconstructible via `superseded_by` traversal
- GitHub private repo `andes-rl-kundur` exists with the first push complete
- Migration completed within ~15 hours of focused work

---

**Approvers**: User (brainstorming dialogue, 2026-05-15)
**Next step**: invoke `superpowers:writing-plans` skill to produce the step-by-step implementation plan
