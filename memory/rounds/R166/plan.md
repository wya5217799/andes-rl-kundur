---
round: R166
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R166 plan — Research workflow asymmetry fix (housekeeping + tooling)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: meta / infrastructure
**Driver**: 16 zombie rounds + 3 stale Qs detected mid-session via STATE.md
audit. Root cause = asymmetric open/close cost: `reserve_round.py` is one
atomic call; closing requires full `verdict.md` (3 Q-sections + PI briefing).
Rounds that get superseded, aborted, or queued-but-never-fired accumulate
because the close ceremony doesn't fit their actual exit path.

**Parent**: STATE.md @ 09:56 (showed 11 in-flight), refreshed render @ ~10:00
detected 6 more empty reserved dirs (R155 R157 R159 R161 R162 R164) created
by a parallel session while this design was being written.

## Goal

Make the round/question ledger reflect reality, and prevent the asymmetry
from re-accumulating. Two outputs:
1. **Schema + tooling**: `state` field on plan.md; validate.py recognises
   3 close paths (completed / superseded / aborted); render.py separates
   active / queued / stale; both tools warn on staleness signals.
2. **One-time sweep**: classify and close all 16 zombie rounds + 3 stale Qs
   under R166.

## Design (4 sections, all user-approved 2026-05-19)

### Section 1 — Round lifecycle data model

New `state` field on `RNNN/plan.md` frontmatter:

```yaml
---
round: R<NNN>
state: active        # active | queued | completed | superseded | aborted
opened: <YYYY-MM-DD>
closed: null         # date when state becomes terminal
supersedes_rounds: []
superseded_by_round: null    # required if state=superseded
abort_reason: null            # required if state=aborted
superseded_note: null         # 1-line context if state=superseded
---
```

State semantics:

| state | meaning | verdict.md req. | terminal? |
|-------|---------|------------------|-----------|
| `active` | Truly in progress | — | no |
| `queued` | Reserved, waiting for slot | — | no |
| `completed` | Work done, conclusion drawn | **yes** (3 Q-sections + PI briefing, ADR-0003) | yes |
| `superseded` | Obsoleted by later round | no (only `superseded_by_round` + `superseded_note`) | yes |
| `aborted` | Planned but won't execute | no (only `abort_reason`) | yes |

Invariants:
- `state` field is the canonical source of truth (not dir/file presence).
- Terminal states are sticky (cannot revert to active).
- `superseded_by_round` must point to an existing round dir.
- `closed` date required for all terminal states.

### Section 2 — validate.py extension

5 new rules (3 hard, 2 soft):

| Rule id | Type | Check |
|---------|------|-------|
| `R-state-required` | hard | every `RNNN/plan.md` has `state` field |
| `R-state-enum` | hard | `state ∈ {active, queued, completed, superseded, aborted}` |
| `R-terminal-fields` | hard | `completed` → verdict.md exists (existing rule); `superseded` → `superseded_by_round` non-null + target dir exists; `aborted` → `abort_reason` non-null |
| `R-stale-active` | soft | `state=active` AND `opened` ≥ 14 days ago AND no verdict.md → "Round R<NNN> may be zombie" |
| `R-stale-queued` | soft | `state=queued` AND `opened` ≥ 7 days ago → "Round R<NNN> queued for a week" |

Plus 1 question rule:

| `Q-superseded-by-claim` | soft | open Q whose subject keywords appear in a recent claim's provenance → "Q-<NNNN> may be closed-by CLM-<MMMM>" |

Implementation: extend `_iter_round_dirs` path in `validate.py` to also
load `plan.md` frontmatter and run state-aware checks. Add functions:
- `validate_round_state(plan_path) -> list[str]` (hard rules)
- `warn_stale_round(plan_path, *, today) -> list[str]` (soft warns)
- `warn_question_supersession(questions, claims) -> list[str]`

### Section 3 — render.py + STATE.md re-layout

Replace `## In-Flight` with 3 explicit sections grouped by state:

```markdown
## 在跑 (state=active)
- R<NNN> — <plan path> [opened YYYY-MM-DD]

## 排队 (state=queued)
- (空 if none)

## ⚠️ 疑似 stale (validate warnings)
- R<NNN> — <reason> → suggestion

## Open Questions
- Q-<NNNN> [opened R<NN>] <subject>
- ⚠️ Q-<NNNN> — possibly closed by CLM-<MMMM>
```

`_round_is_in_flight()` becomes `_round_state()` returning the enum.
Stale-detection helper extracted so validate.py + render.py share it.
Empty reserved dirs (no plan.md) ignored by both tools (they're not
rounds yet; addressed by housekeeping sweep, not flagged ongoing).

### Section 4 — R166 sweep classification

**16 zombie rounds + R156 (left active)**:

| Round | New state | Justification |
|-------|-----------|---------------|
| R115 | superseded | by R103 (CLM-0203 closed paper_strict_pure) |
| R118 | superseded | by R113 (CLM-0215 closed Toggler ablation) |
| R119 | aborted | wider action bound replaced by R132 α-sweep (CLM-0218) |
| R120 | aborted | depended on R118; moot |
| R122 | superseded | by R142 (CLM-0275 QR-LSTM training completed) |
| R123 | superseded | by R144 (AFE absorbed into stacked path) |
| R131 | aborted | triple-stack queue never fired; R154 changed direction |
| R143 | completed | results in CLM-0275 (R142/R143 jointly recorded); write minimal verdict |
| R144 | aborted | stacked QR+AFE replaced by R127 path |
| R149 | completed | plan self-declares closed-negative; write minimal verdict |
| R155 | aborted | reserved-empty; reason: number reclaim |
| R157 | aborted | reserved-empty; reason: number reclaim |
| R159 | aborted | reserved-empty (parallel-session race) |
| R161 | aborted | reserved-empty (parallel-session race) |
| R162 | aborted | reserved-empty (parallel-session race) |
| R164 | aborted | reserved-empty (parallel-session race) |
| R156 | active | confirmed active per parallel session — leave alone |

**3 stale Qs**:

| Question | New status | By |
|----------|------------|-----|
| Q-0014 (algorithm-side breakthrough) | closed-partial | CLM-0295 (R154 ensemble gives conditional answer) |
| Q-0017 (Transformer fix) | abandoned | no follow-up since R82; deprioritised |
| Q-0019 (distributional breaks monotone Q) | closed-negative | CLM-0275 (R142 QR-LSTM matches baseline, no break) |

## Execution order

### Phase A — Tooling (TDD)
A1. Read existing `validate.py` round-handling + `_iter_verdicts`
A2. Write tests for `R-state-required`, `R-state-enum`, `R-terminal-fields`
    in `tests/test_validate.py` (RED)
A3. Implement `validate_round_state()` in `validate.py` (GREEN)
A4. Write tests for `R-stale-active`, `R-stale-queued` with fixed `today=`
    fixture (RED)
A5. Implement `warn_stale_round()` (GREEN)
A6. Write tests for `Q-superseded-by-claim` heuristic (RED → GREEN)
A7. Update `reserve_round.py` to write `state: active` + `opened: <today>`
    into the new plan.md it generates
A8. Backfill: for every existing `RNNN/plan.md`, inject `state: active`
    + `opened: <git-log-derived>` if missing. Script: one-shot Python in
    `memory/tools/_backfill_round_state.py`, kept in repo as audit artifact
    with `# one-shot, ran R166 sweep` header.
A9. Run `validate.py` — expect ~17 stale-active warnings as signal that
    Phase B is needed
A10. Write tests for render.py 3-section split + ⚠️ markers (RED → GREEN)
A11. Implement render.py changes
A12. Run `render.py` — verify STATE.md shows active=1 (R156), queued=0,
     stale=many

### Phase B — Sweep (R166 housekeeping)
B1. Flip 13 plan.md states per table (write `state`, `closed`,
    `superseded_by_round` or `abort_reason`, `superseded_note`)
B2. Write minimal verdict.md for R143 (completed; reference CLM-0275)
B3. Write minimal verdict.md for R149 (completed; reference plan's own
    closed-negative note + reproduce in proper format)
B4. Update 3 Q files: Q-0014 → closed-partial, Q-0017 → abandoned,
    Q-0019 → closed-negative. Each needs `closed_round: R166` and
    `closed_by: <claim>` per existing question schema.
B5. Write CLM-0296 documenting the housekeeping sweep (so closed
    questions have a `closed_by` target; type=decision, trust=S)
B6. Write R166 verdict.md (3 Q-sections + PI briefing) — this is the
    only round that needs a real verdict in this sweep
B7. Run `validate.py` — expect all-green (no warnings)
B8. Run `render.py` — STATE.md regenerated cleanly

### Phase C — Commit
C1. Stage: validate.py, render.py, reserve_round.py, tests/, all
    flipped plan.md files, new verdict files, Q files, CLM-0296,
    R166 verdict.md, STATE.md, this plan
C2. Commit message: `infra: round lifecycle states + R166 housekeeping
    (close 16 zombies, 3 stale Qs)`
C3. Keep `_backfill_round_state.py` in repo as audit artifact (header
    marks it `# one-shot`)

## Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| Parallel session still running, may reserve R167+ mid-sweep | Detect via dir listing; absorb new reserved-empties into B1 if they appear |
| Backfill date inference wrong (git log can lie about mv-renamed files) | Use file mtime as fallback; warn if `opened` ends up later than any claim's round |
| New state-required rule breaks `_legacy/` or `R10-17` bundled verdicts | scope check to `ROUND_DIR_RE` only — already excludes those |
| validate.py soft warns flood after backfill before sweep | expected signal; Phase A9 explicitly anticipates this |

## Out of scope (explicit)

- Renaming or restructuring claim provenance fields — leave alone
- Touching `handoffs/` (out of schema by design)
- Adding new ADRs — this is operational hygiene, not architectural
- Cleaning `_archive/` or `_legacy/` — those are intentionally frozen
- Re-rendering historical STATE.md snapshots — only current state matters
