# Memory System: Note Entity + Legacy Ingest — Design Spec

**Date**: 2026-05-19
**Status**: APPROVED 2026-05-19
**Author**: Codex via brainstorming skill
**Supersedes / extends**: R39 memory subsystem (`memory/rounds/R39/plan.md`, `CLAUDE.md` "Memory subsystem" section)
**Scope**: schema extension + tooling + 4-wave legacy ingest. Does **not** change claim / question / round semantics.

---

## 1. Motivation

R39 (2026-05-16) converted `memory/` from passive ledger to active oracle. Three entity kinds (claim / question / round) + auto-rendered `STATE.md`. By design, `memory/handoffs/`, `docs/adr/`, `docs/eng-notes/`, and `_legacy/` were **excluded** from schema — treated as scratchpad or frozen archive.

Six months and 80 rounds later, the cost of that exclusion shows:

- Cross-round learnings sit in 9 handoff files (3,976 lines total) that the oracle never surfaces.
- AI sessions cannot answer "what did the R58→R66 hyperparameter sweep conclude?" without manual file archaeology.
- 5 ADRs have no reverse links from claims — decisions float disconnected from their measurement evidence.
- `_legacy/RESEARCH_TRAIL.md` (520 lines of pre-R39 narrative) is effectively invisible to fresh agents.

**User goal** (2026-05-19): "Let conversations be aware of all past experiments and data for scientific work."

## 2. Non-goals

- Do **not** break R39's "headlines / leaderboard contain only atomic claims" invariant.
- Do **not** retire `memory/handoffs/` — original files preserved as-is for provenance.
- Do **not** retroactively rewrite R01-R38 claims (R39 lazy-backfill principle continues).
- Do **not** auto-extract claims from notes (extraction is human-judged, lazy, triggered by need).

## 3. Architecture

### 3.1 New entity kind: Note

| Property | Value |
|---|---|
| ID format | `NOTE-NNNN` (4-digit zero-padded, monotonic) |
| Location | `memory/notes/NOTE-NNNN.md` |
| Schema | 8 mandatory frontmatter fields + 3 mandatory body sections |
| Role | Index layer over external archives; **not** measurement-of-record |
| Feeds | `STATE.md` `## Archive Index` section (topic-bucketed, count + 3 most recent per bucket) |
| Does not feed | `## Headlines`, `## Leaderboard`, `## In-Flight`, `## Open Questions` |

### 3.2 Note frontmatter (validated)

```yaml
---
id: NOTE-NNNN
source: handoff | eng-note | adr-rationale | legacy | session-report
source_path: <repo-relative path; must exist on disk>
date: YYYY-MM-DD   # original creation date of source, not ingest date
related_rounds: [R55, R58]
topics: [<top-level>, <free-tag>, <free-tag>, ...]
extracted_claims: []   # CLM-NNNN ids; empty initially, filled lazily
status: ingested | partially-extracted | fully-extracted
---
```

### 3.3 Note body (validated structure)

```markdown
## Summary
(3-5 sentences. AI can decide from this paragraph alone whether to open source_path.)

## Key facts (claim candidates)
- Bullet 1 — if later promoted to claim, append `→ CLM-NNNN`
- Bullet 2

## Open threads
(Things the source flagged as TODO/unknown but did not turn into a Q-NNNN. Future rounds can promote these.)
```

### 3.4 Topic taxonomy (double-layer)

**Top-level (closed vocabulary, 8 buckets)** — enforced by validate.py:

1. `env` — V4/V5/AndesBaseEnv/scenarios/disturbance
2. `training-infra` — train.py, replay, dataloader, monitor
3. `evaluation` — paper_grade_axes, eval_*.py, scoring
4. `agents` — SAC/TD3/LSTM/Transformer/CTDE
5. `scenarios` — KUNDUR contract, LS1/LS2, disturbance design
6. `paper` — paper-strict vs paper-faithful, manuscript, ablations
7. `memory-system` — schema/tools/STATE/render
8. `pipeline` — refactor, src layout, package structure

**Sub-tags (open vocabulary)** — recommended for searchability:
- algo names: `lstm`, `td3`, `sac`, `transformer`, `iqn`
- env variants: `v4`, `v5`, `regca1`
- specific concepts: `ctde`, `distributional-critic`, `hyper-sweep`

### 3.5 STATE.md `## Archive Index` section (new)

Inserted between `## Stats` and `## 历史简报`. Auto-rendered:

```markdown
## Archive Index

> Query: `python memory/tools/note_query.py --topic <top> [--tag <sub>] [--round <RNN>] [--grep <pattern>]`

- [training-infra] 6 notes — NOTE-0008 LSTM rollout zero-padding; NOTE-0005 hyper sweep R58→R66; NOTE-0003 paper-strict eval
- [evaluation]     4 notes — NOTE-0019 paper-grade ranker v2; NOTE-0017 settling-axis tolerance; NOTE-0013 6-axis re-weighting
- [memory-system]  3 notes — NOTE-0001 R39 grilling outcomes; NOTE-0002 R52 hygiene plan; NOTE-0009 R52 cleanup retrospective
- [paper]          2 notes — NOTE-0020 paper-strict vs paper-faithful decision; NOTE-0021 优化方向 (legacy)
- [env]            3 notes — NOTE-0011 NOTES_ANDES; NOTE-0012 V4 audit report; ...
- [pipeline]       2 notes — NOTE-0010 src-layout ADR; NOTE-0023 post-refactor handoff
- ...
```

Bucket rules:
- Show only buckets with ≥ 1 note.
- Within bucket: 3 most recent notes by date (descending), 1-line summary truncated to 60 chars.
- Total section cap: 1 query hint row + up to 8 bucket rows = **9 lines max** (one row per top-level topic; collapses to count-only if all 8 active and section would exceed 10 lines).

## 4. Tooling diff

### 4.1 New tools

| File | Purpose |
|---|---|
| `memory/tools/new_note.py` | Reserve next NOTE-NNNN id, scaffold a stub with frontmatter prefilled |
| `memory/tools/note_query.py` | Filter notes by topic / sub-tag / round / source / grep; print id + summary + path |

### 4.2 validate.py extensions

Existing: 4 claim rules + 3 question rules + 3 verdict rules.

Add **5 note rules** (all blocking):

- **N1**: filename `NOTE-NNNN.md` matches frontmatter `id`
- **N2**: `source` ∈ {handoff, eng-note, adr-rationale, legacy, session-report}
- **N3**: `source_path` resolves to an existing file under repo root
- **N4**: every id in `extracted_claims` exists in `memory/claims/`
- **N5**: `topics[0]` (top-level) ∈ {env, training-infra, evaluation, agents, scenarios, paper, memory-system, pipeline}

Add **2 cross-entity rules** (warnings only, not blocking):

- **X1**: every ADR in `docs/adr/` has at least one note with `source: adr-rationale, source_path: docs/adr/<file>`
- **X2**: every `memory/handoffs/*.md` (excluding `README.md` and `_archive/`) has at least one note pointing to it

### 4.3 render.py extensions

- New section emitter for `## Archive Index` (bucketed, 3-per-bucket, query hint footer)
- Existing 6 sections unchanged
- No change to leaderboard logic — claim metrics still drive it

### 4.4 CLAUDE.md update

Add to "Read first" list:

> - When the task touches work from rounds older than ~20 rounds back, run `python memory/tools/note_query.py --topic <relevant> --grep <keyword>` before assuming prior context is lost.

Add to "Memory subsystem" table:

> | **Note** (`NOTE-NNNN`) | `memory/notes/` | Indexed archive of handoffs / ADRs / legacy docs; not measurement-of-record | `validate.py` enforces 5 rules; `note_query.py` searches; `render.py` surfaces as Archive Index |

## 5. Migration plan (4 waves + pre-flight)

### Pre-flight: STATE.md hygiene

Status: blocks Wave 0.

- Audit `R45/plan.md` and `R91/plan.md`: real in-flight or stale?
  - If stale → write `verdict.md` with status `abandoned` + `## Questions opened/closed/advanced` all empty + a one-line reason.
  - If real → leave as-is.
- `R90/`: missing TL;DR and PI briefing. Either close it (write verdict.md with mandatory sections) or annotate why it's pending.
- `R88`, `R89`: their PI briefings should appear in `## 历史简报`. Verify `render.py` is including R88+ entries or fix the renderer.

Verification: `python memory/tools/render.py && python memory/tools/validate.py` both green.

### Wave 0 — ADR ingest (5 notes)

For each of `docs/adr/0001..0005`:
- New note with `source: adr-rationale`, `source_path: docs/adr/000N-*.md`
- Summary = ADR's "Decision" + "Rationale" sections, compressed
- topics drawn from ADR title (e.g., 0001 → `[pipeline, src-layout]`)
- `related_rounds` = rounds that cite the ADR (grep)
- After Wave 0: each ADR file gets a `## Related Notes` footer listing back-pointer note ids

Verification: 5 new notes; validate.py + render.py green; STATE.md shows `[pipeline]` bucket with NOTE-0001/0002 visible.

### Wave 1 — handoffs (9 notes, possibly 11 after splits)

Source files (9):
- `2026-05-15-migration-complete.md` (58 lines)
- `2026-05-17_R52_memory_hygiene_plan.md` (549 lines — **may split into 2** by topic)
- `2026-05-17_R56_lstm-actor-implementation.md` (470 lines — **may split into 2**)
- `2026-05-17_R58_paper_strict_handoff.md` (229)
- `2026-05-17_R58_to_R66_hyper_sweep_handoff.md` (289)
- `2026-05-17_post-R41.md` (192)
- `2026-05-17_post-R55_arc-summary.md` (331)
- `2026-05-17_post-refactor.md` (88)
- `2026-05-18_R67_to_R75_evaluator_evolution_handoff.md` (302)

Split rule: if source > 400 lines AND covers ≥ 2 top-level topics → split into one note per top-level topic, all pointing to the same `source_path`.

Verification: `## Archive Index` shows growth; `validate.py` rule X2 (handoff coverage warning) no longer fires for any file in `memory/handoffs/`.

### Wave 2 — eng-notes + session-report (2 notes)

- `docs/eng-notes/NOTES_ANDES.md` (231 lines) — single note, `source: eng-note`, topics `[env, training-infra]`
- `_legacy/session_report_2026-05-07_v4_audit.md` — `source: session-report`, topics `[env, evaluation]`

### Wave 3 — _legacy (5-8 notes after splits)

- `_legacy/CONTEXT.md` (575 lines) — likely splits into 3 notes (env / agents / pipeline)
- `_legacy/RESEARCH_TRAIL.md` (520 lines) — likely splits into 3-4 notes by phase (pre-V4, V4-bringup, paper-grade evaluator)
- `_legacy/优化方向.md` (89) — single note, `source: legacy`, topic `[paper]`

### Wave 4 — sweep for missed sources

After Waves 0-3, grep for:
- `scripts/_archive/r*.py` — if a frozen driver has substantial docstring with experimental rationale not captured in any claim, create a note
- `results/whitelist/*.md` — if any
- `quality_reports/` if it exists with content
- GitHub issues at this repo — if there are closed issues with decisions not in claims

Result: ≤ 5 additional notes expected.

### Total expected note count

Wave 0: 5 + Wave 1: 9-11 + Wave 2: 2 + Wave 3: 5-8 + Wave 4: 0-5 = **21-31 notes**.

## 6. Risk and rollback

| Risk | Mitigation |
|---|---|
| Note signal degrades over time (becomes write-only like pre-R39 handoffs) | `note_query.py` is the gateway — if it's not used, archive index also won't be used, and we'll notice |
| `## Archive Index` becomes long enough to push STATE.md > 200 lines | 9-line cap (3.5); if exceeded, top-level buckets compress to count-only |
| Topic taxonomy rots (real topics drift from 8 buckets) | Sub-tags are open; if a 9th top-level bucket genuinely needed, add via schema-cleanup round following R39 precedent |
| Ingestion is lossy (note summary misses something later needed) | `source_path` always points to the verbatim original; note is index, not replacement |
| Validate.py blocking rules slow down note creation | Stub generator `new_note.py` prefills schema so manual error is minimized |

**Rollback path**: if the system regresses, delete `memory/notes/`, revert `validate.py` / `render.py` / `CLAUDE.md`. No claim / question / round data is mutated — original files in `handoffs/`, `docs/`, `_legacy/` are read-only sources.

## 7. Success criteria

- [ ] `python memory/tools/validate.py` green after each wave
- [ ] `STATE.md` regenerates with `## Archive Index` section showing ≥ 6 of 8 top-level buckets populated by end of Wave 3
- [ ] `note_query.py --topic training-infra` returns a hit for the LSTM rollout zero-padding handoff content
- [ ] `note_query.py --grep "paper-strict"` returns the corresponding ADR-rationale note + handoff notes
- [ ] On a fresh session, prompt "What did R58→R66 hyperparameter sweep conclude?" causes the agent to find NOTE-XXXX via Archive Index (manual test)
- [ ] At least 1 claim gets `extracted_from: NOTE-NNNN` within 30 days (signals the lazy-extraction loop is working)

## 8. Out of scope (deferred to future rounds)

- Auto-summarization of notes via LLM during ingest (Wave 0-4 summaries are human-written for accuracy)
- Note → claim auto-extraction (R39 lazy principle applies; do it when a round needs to cite)
- Versioning of notes (a note is immutable once ingested; if source changes substantially, supersede via new note with `supersedes: NOTE-...`)
- Indexing GitHub PRs / commit messages (would multiply note count by 10×; revisit if value emerges)

## 9. Decisions on initially-open questions (resolved 2026-05-19)

1. **Archive Index exposes claim-extraction count per bucket** — format: `[training-infra] 6 notes · 2 claims extracted`. Rationale: surfaces whether the lazy claim-extraction loop is actually happening; near-zero render cost.
2. **Note IDs are global monotonic** — `NOTE-0001 .. NOTE-NNNN`. Rationale: simpler reserve logic, matches CLM-/Q- conventions; sub-tag and `source` field already make grep equally easy.
3. **No back-reference written into source files** — original handoffs / ADRs / legacy docs stay byte-identical. Rationale: preserves "lossless preservation" of source; `note_query.py --source-path <path>` provides the reverse lookup.
