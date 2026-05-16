# Handoff — R52 memory-hygiene dogfood round (planned)

**Date written**: 2026-05-17
**Author session**: Claude Code (R50 batch optimizer)
**Reader**: next Claude session opening this repo cold
**Goal**: execute the R52 round in one focused 30–40 min sitting
**Status when written**: planned but NOT started

---

## Why this round exists

R50 (the most recent optimization batch, 12 commits `1fd945b..6276909`)
added 6 features to the memory + research system that **none of the
existing claims/rounds use yet**:

| R50 item | Where it lives | Used? |
|---|---|---|
| G  reserve_round.py     | `memory/tools/reserve_round.py`     | 0 callers |
| H  STATE.md leaderboard | `memory/tools/render.py` (5b section) | empty section |
| I  CLM `metric:` field  | `memory/tools/validate.py` Rule 5   | 0/59 claims have it |
| J  `status: obsoleted`  | `memory/tools/validate.py` Rule 6   | 0/59 claims have it |
| L  query.py --best      | `memory/tools/query.py`             | 0 callers |
| E  score_run.py         | `scripts/score_run.py`              | 0 callers (E waits R53+) |

The opt-batch was discussed in the session that produced it as a
**two-stage experiment**: stage 1 (build the tools) is done; stage 2
(prove adoption) is this R52 round. If after R52 + 2 follow-up rounds
the tools are still 0-caller, revert per the M1/M2 criteria below.

A parallel issue: K (provenance soft-check) lit up immediately with
**30 dangling-path WARN**s on the live ledger. Most are pre-R37 paths
(env/* / evaluation/* / probes/* / config.py → src/andes_rl_kundur/...)
and Codex's R45 archive moves (scripts/_r4*_score_*.py →
scripts/_archive/round_scripts/...). These need a one-time rewrite.

R52 dogfoods G–L on the way to cleaning K's debt, killing two birds.

---

## Pre-flight (do these first, ~2 min)

```bash
# 1. Confirm clean baseline
git log --oneline -3
# Expect tip at or after 6276909 (R50 E commit). If newer commits from a
# parallel Codex session exist, that's fine — just note the hash.

git status --short
# Expect mostly clean. Codex parallel work may show as staged src/* or
# tests/*; ignore those for R52 (use `git commit -- <paths>` pattern).

# 2. Tests green
wsl bash -c "cd /mnt/c/Users/27443/Desktop/andes-rl-kundur && \
  /home/wya/andes_venv/bin/python -m pytest tests/ -q 2>&1 | tail -3"
# Expect: 77 passed (or higher if Codex added more)

wsl bash -c "cd /mnt/c/Users/27443/Desktop/andes-rl-kundur && \
  /home/wya/andes_venv/bin/python -m pytest memory/tools/tests/ -q 2>&1 | tail -3"
# Expect: 69 passed (R50 G+I+J+K+L+H tests included)

# 3. Validate clean
wsl bash -c "cd /mnt/c/Users/27443/Desktop/andes-rl-kundur && \
  /home/wya/andes_venv/bin/python memory/tools/validate.py 2>&1 | tail -3"
# Expect: OK: 59+ claims, 4+ questions, ~39 warnings (most from K — 30 stale paths)

# 4. Codex CLI not interfering?
ls -la ~/.codex/logs_2.sqlite-wal 2>&1 | awk '{print $6, $7}'
# OpenAI Codex CLI last activity. If mtime > 1 day ago, no interference risk.
```

If anything fails, STOP and diagnose before continuing — the R52 plan
assumes a clean baseline.

---

## R52 step-by-step playbook

### Step 1 — Reserve the round number (validates G)

```bash
wsl bash -c "cd /mnt/c/Users/27443/Desktop/andes-rl-kundur && \
  /home/wya/andes_venv/bin/python memory/tools/reserve_round.py"
# Expect: prints `52` (or higher if Codex grabbed 52 first).
# This creates memory/rounds/R<N>/ as an atomic side effect.
```

Let `<N>` = the number it printed. Use throughout. **Do NOT manually
pick 52**; that's the whole point of validating G.

### Step 2 — Create `memory/claims/_TEMPLATE.md` (Patch A1)

This template doesn't exist yet (`memory/questions/_TEMPLATE.md` does
but claims/ does not). Create with the metric block as an opt-in
commented placeholder so future authors see it:

```yaml
---
id: CLM-NNNN
type: finding          # finding | decision | correction
trust: V               # V (verified) | S (stated) | T (theoretical)
                       # Note: decision MUST be S; correction MUST be V
status: current        # current | superseded | obsoleted
statement: |
  <one paragraph; cite specific numbers, configs, claim IDs>
round: R<N>
provenance:
  - <path/to/result.json>  # K will WARN if missing on disk
  - <path/to/script.py>
  - memory/rounds/R<N>/verdict.md
tags: [<key>, <words>, <for-query>]
# Optional structured metric block — fill in if statement cites a
# benchmark number. Enables STATE.md ## Leaderboard (R50 H) and
# `query.py --best <metric_name>` lookups (R50 L).
# metric:
#   name: 6_axis      # or settling_s, max_df_Hz, etc.
#   value: 0.334      # numeric, NOT bool
# Optional supersede chain (if this claim replaces an older one).
# supersedes: [CLM-XXXX]
# Optional obsoletion (if external change rendered the claim stale
# WITHOUT a successor — e.g. ranker drift).
# obsoleted_round: R<N>
# obsoleted_reason: <one sentence>
---
```

Save and `git add memory/claims/_TEMPLATE.md`.

### Step 3 — Backfill metric on 8 headline claims (Patch B1)

For each claim below, add a `metric:` block to the YAML frontmatter
just before the closing `---`. The values are extracted from each
claim's existing `statement` field — verify by re-reading the claim
before editing.

| CLM | metric.name | metric.value | source line in statement |
|---|---|---|---|
| CLM-0005 | 6_axis | 0.444 | "R21 V4 h50_s49 6-axis = 0.444" |
| CLM-0006 | 6_axis | 0.415 | "HAWE w8515 ... 6-axis = 0.415" |
| CLM-0007 | 6_axis | 0.439 | "HAWE w9802 ... 6-axis = 0.439" |
| CLM-0049 | 6_axis | 0.310 | "HAWE TD3 norm 6-axis = 0.310" |
| CLM-0050 | 6_axis | 0.347 | "best ensemble 6-axis = 0.347" |
| CLM-0052 | 6_axis | 0.342 | "median (consensus-picking) ... 0.3423" — round to 0.342 |
| CLM-0054 | 6_axis | 0.334 | "hidden=64 : 0.3346 range..." — round to 0.334 |
| CLM-0056 | 6_axis | 0.351 | "median aggregation reaches 6-axis = 0.3509" — round to 0.351 |

**Care**: `CLM-0008` is intentionally NOT in this list — it gets the
**obsoleted** treatment in Step 4 instead.

After edits, run validate immediately:

```bash
wsl bash -c "cd /mnt/c/Users/27443/Desktop/andes-rl-kundur && \
  /home/wya/andes_venv/bin/python memory/tools/validate.py 2>&1 | grep -E 'ERROR|^OK'"
# Expect: 0 ERROR, OK line. If Rule 5 errors, the metric block is
# malformed (likely missing name or value key).
```

### Step 4 — Mark CLM-0008 obsoleted (Patch B2, validates J)

CLM-0008 cites `no_control baseline 6-axis = 0.104 (post r30 ranker fix)`.
Under the current post-R36 ranker, no_control scores **0.094** (verified
in R44 verdict). The claim is true-as-of-R30 but stale-now.

Edit `memory/claims/CLM-0008.md` frontmatter:

```yaml
---
id: CLM-0008
# ...existing fields...
status: obsoleted          # was: current
obsoleted_round: R<N>      # the R-number reserve_round gave you
obsoleted_reason: |
  Post-R30 ranker tuning (R35 / R36) shifted the no_control baseline
  from 0.104 to 0.094 under the current paper_grade_axes. The R30-era
  0.104 anchor is preserved here for historical context but is no
  longer the live measurement. See R44 verdict for the side observation.
# ...rest unchanged...
---
```

The claim has no successor (it's the same configuration, the ranker
changed under it) so **do not set `supersedes` or `superseded_by`**.
That's exactly what `obsoleted` means (vs `superseded`).

Validate again — Rule 6 (R50 J) should accept this; Rule 3
(current ↔ superseded_by empty) is irrelevant because status is now
obsoleted not current.

### Step 5 — Fix 30 stale provenance paths (Patch C1, K cleanup)

Known mappings (from pre-R37 src-layout migration + R45 archive):

```
env/andes/*.py                  → src/andes_rl_kundur/env/andes/*.py
evaluation/paper_grade_axes.py  → src/andes_rl_kundur/evaluation/paper_grade_axes.py
probes/andes_common/*.py        → src/andes_rl_kundur/probes/andes_common/*.py
config.py                       → src/andes_rl_kundur/config.py
paper/main.tex                  → artifacts/paper/main.tex
paper/figures/*                 → artifacts/paper/figures/*
dissertation/main.tex           → artifacts/dissertation/main.tex
scripts/_r38_score_td3_sweep.py        → scripts/_archive/round_scripts/_r38_score_td3_sweep.py
scripts/_r40_score_phi_zero_sweep.py   → scripts/_archive/round_scripts/_r40_score_phi_zero_sweep.py
scripts/_r41_score_A_sac_phi0.py       → scripts/_archive/round_scripts/_r41_score_A_sac_phi0.py
scripts/_r41_score_B_normalized.py     → scripts/_archive/round_scripts/_r41_score_B_normalized.py
scripts/_r41_score_C_td3_200ep.py      → scripts/_archive/round_scripts/_r41_score_C_td3_200ep.py
scripts/_r42_score_alpha_sac_norm.py   → scripts/_archive/round_scripts/_r42_score_alpha_sac_norm.py
scripts/research_loop/eval_v4_ensemble.py  → scripts/eval_ensemble.py
```

Apply the rewrite. Suggested approach — write
`memory/tools/_oneoff_fix_provenance_paths.py`:

```python
"""One-off: rewrite stale provenance paths in CLM frontmatter.

Maps known path migrations from pre-R37 src-layout and Codex R45
archive moves. Idempotent: a second run produces no diff. Delete
after R52 lands.
"""
import re
from pathlib import Path

MAPPING = {
    # pre-R37 src-layout
    "env/andes/": "src/andes_rl_kundur/env/andes/",
    "evaluation/paper_grade_axes.py": "src/andes_rl_kundur/evaluation/paper_grade_axes.py",
    "probes/andes_common/": "src/andes_rl_kundur/probes/andes_common/",
    "config.py": "src/andes_rl_kundur/config.py",
    # paper / dissertation moves to artifacts/
    "paper/main.tex": "artifacts/paper/main.tex",
    "paper/figures/": "artifacts/paper/figures/",
    "dissertation/main.tex": "artifacts/dissertation/main.tex",
    # Codex R45 archive
    "scripts/_r38_score_td3_sweep.py": "scripts/_archive/round_scripts/_r38_score_td3_sweep.py",
    "scripts/_r40_score_phi_zero_sweep.py": "scripts/_archive/round_scripts/_r40_score_phi_zero_sweep.py",
    "scripts/_r41_score_A_sac_phi0.py": "scripts/_archive/round_scripts/_r41_score_A_sac_phi0.py",
    "scripts/_r41_score_B_normalized.py": "scripts/_archive/round_scripts/_r41_score_B_normalized.py",
    "scripts/_r41_score_C_td3_200ep.py": "scripts/_archive/round_scripts/_r41_score_C_td3_200ep.py",
    "scripts/_r42_score_alpha_sac_norm.py": "scripts/_archive/round_scripts/_r42_score_alpha_sac_norm.py",
    "scripts/research_loop/eval_v4_ensemble.py": "scripts/eval_ensemble.py",
}

ROOT = Path(__file__).resolve().parents[2]
total = 0
for f in sorted((ROOT / "memory" / "claims").glob("CLM-*.md")):
    text = f.read_text(encoding="utf-8")
    new = text
    for old_p, new_p in MAPPING.items():
        # Match path-as-list-item (leading "- " or "- " with whitespace)
        new = re.sub(rf"(- ){re.escape(old_p)}", rf"\1{new_p}", new)
    if new != text:
        f.write_text(new, encoding="utf-8")
        total += 1
        print(f"rewrote {f.name}")
print(f"\ntotal: {total} files rewritten")
```

Run it and re-validate:

```bash
wsl bash -c "cd /mnt/c/Users/27443/Desktop/andes-rl-kundur && \
  /home/wya/andes_venv/bin/python memory/tools/_oneoff_fix_provenance_paths.py"
wsl bash -c "cd /mnt/c/Users/27443/Desktop/andes-rl-kundur && \
  /home/wya/andes_venv/bin/python memory/tools/validate.py 2>&1 | \
  grep -c 'provenance path missing'"
# Expect ≤ 5 (down from 30). Remaining ones are genuinely missing
# files (e.g. dataset paths gone, deleted artefacts) — list them in
# the R<N> verdict's "known dangling provenance" section.
```

**Delete the one-off script** at the end (`git rm` after the commit
lands or skip adding it altogether and use a python -c heredoc).

### Step 6 — Archive stale handoffs (Patch C2)

`memory/handoffs/` currently has 14 files; 9 are from 2026-05-07 to
2026-05-08 (≥ 10 days old, superseded by `2026-05-17_post-R41.md` and
`2026-05-17_post-refactor.md`).

```bash
cd /mnt/c/Users/27443/Desktop/andes-rl-kundur
mkdir -p memory/handoffs/_archive
git mv memory/handoffs/2026-05-07_MASTER_INDEX.md memory/handoffs/_archive/
git mv memory/handoffs/2026-05-07_andes_6axis_recovery_handoff.md memory/handoffs/_archive/
git mv memory/handoffs/2026-05-07_andes_breakthrough_FINAL.md memory/handoffs/_archive/
git mv memory/handoffs/2026-05-07_andes_breakthrough_update.md memory/handoffs/_archive/
git mv memory/handoffs/2026-05-07_andes_path_closure.md memory/handoffs/_archive/
git mv memory/handoffs/2026-05-07_andes_v41_reward_paradox_handoff.md memory/handoffs/_archive/
git mv memory/handoffs/2026-05-07_handoff_v12.md memory/handoffs/_archive/
git mv memory/handoffs/2026-05-07_handoff_v13.md memory/handoffs/_archive/
git mv memory/handoffs/2026-05-07_handoff_v14.md memory/handoffs/_archive/
git mv memory/handoffs/2026-05-08_handoff_v17.md memory/handoffs/_archive/
```

Update `memory/handoffs/README.md`: add one paragraph explaining the
archive convention ("handoffs > 10 days old or referenced by no
in-flight question/round live in _archive/; the top-level handoffs
directory is for the most recent session-pickup material").

### Step 7 — Patch A2: validate.py soft warn for findings missing metric

Add to `memory/tools/validate.py` `validate_rules()`:

```python
# Soft-warn: finding / correction claims whose statement cites a
# benchmark-like decimal number but carry no metric block.
# Pushes adoption of R50 opt I without blocking authorship.
_DECIMAL_RE = re.compile(r"\b\d+\.\d{2,4}\b")
for claim in claims.values():
    ctype = claim.get("type")
    if ctype not in ("finding", "correction"):
        continue
    if claim.get("metric"):
        continue
    stmt = claim.get("statement") or ""
    if _DECIMAL_RE.search(stmt):
        warnings.append(
            f"{claim['id']}: statement cites decimal(s) but has no "
            f"metric block — consider adding one for H/L (soft hint)"
        )
```

Don't forget `import re` at top of validate.py if not already there.
Add 2 tests in `memory/tools/tests/test_validate.py`:

- finding with statement "result is 0.334" but no metric → 1 WARN
- finding with the same statement + metric block → 0 WARN
- decision claim with decimal → 0 WARN (rule only fires for finding/correction)

Be aware: after this rule lands, every backfilled-metric claim in
B1 won't trigger this warn (because they have metric blocks). But
the 25+ existing claims without metric AND with decimal numbers in
their statements WILL trigger the warn. That's the point. Expect
the WARN count to JUMP from ~5 (post-C1) to ~30 (post-A2), then go
back down to <10 as future claims start filling metric.

### Step 8 — Update CLAUDE.md memory section (Patch A3)

Add this paragraph to the memory subsection of project-level CLAUDE.md
(or whichever doc the project uses to onboard new sessions —
`CONTEXT.md` is a candidate):

```markdown
### Creating a new round / claim

1. Reserve the round number atomically:
   `python memory/tools/reserve_round.py`
   This creates `memory/rounds/R<N>/` as a side effect. Never pick
   a round number by hand — parallel sessions will race.

2. Copy `memory/claims/_TEMPLATE.md` for each new claim. If the
   claim's statement cites a benchmark number (6-axis, settling, etc.),
   fill in the `metric:` block — that's what powers the STATE.md
   `## Leaderboard` and `query.py --best`.

3. If the round produces a number whose paper-grade scoring you want
   to reuse, drive it through `python scripts/score_run.py ...`
   instead of inline-coding the eval loop. Same surface every round.
```

### Step 9 — Write R<N> plan.md + verdict.md

Use `memory/rounds/_TEMPLATE_VERDICT.md` as the verdict skeleton.
R<N> is a hygiene round (no experiments), so:

- Date: 2026-05-17
- Type: infrastructure (memory housekeeping)
- TL;DR: one sentence summarising what got cleaned up + which R50
  opts went from 0 → 1 caller.
- Body sections: list each step 2–8 with its outcome metric.

R<N>/plan.md is short — just "execute this handoff document". Reference
this handoff file in the plan's body.

Mandatory Q-sections at the bottom:
- Questions opened (this round): (none)
- Questions closed (this round): (none — Q-0004 is Codex's, untouched)
- Questions advanced (this round, status unchanged): (none)

### Step 10 — Render + validate + verify leaderboard appears

```bash
wsl bash -c "cd /mnt/c/Users/27443/Desktop/andes-rl-kundur && \
  /home/wya/andes_venv/bin/python memory/tools/render.py && \
  head -50 memory/STATE.md"
# Expect: a NEW `## Leaderboard (top-10 by metric)` section between
# "## Latest Round" and "## Stats", listing the 8 backfilled claims
# sorted by metric.value descending.

wsl bash -c "cd /mnt/c/Users/27443/Desktop/andes-rl-kundur && \
  /home/wya/andes_venv/bin/python memory/tools/query.py --best 6_axis --top 5"
# Expect 5 rows, top one being CLM-0005 [R30] 6_axis = 0.4440
```

If leaderboard is empty / query returns 0 rows: a metric block is
malformed somewhere. Re-run validate.py to find which claim.

### Step 11 — Full pytest + memory tests pass

```bash
wsl bash -c "cd /mnt/c/Users/27443/Desktop/andes-rl-kundur && \
  /home/wya/andes_venv/bin/python -m pytest tests/ memory/tools/tests/ -q 2>&1 | tail -3"
# Expect: ~79 + 71 = ~150 tests passed (was 77 + 69 = 146 — A2 adds 2 tests).
```

### Step 12 — Commit as single round commit

```bash
git add memory/claims/_TEMPLATE.md \
        memory/claims/CLM-0005.md memory/claims/CLM-0006.md \
        memory/claims/CLM-0007.md memory/claims/CLM-0008.md \
        memory/claims/CLM-0049.md memory/claims/CLM-0050.md \
        memory/claims/CLM-0052.md memory/claims/CLM-0054.md \
        memory/claims/CLM-0056.md \
        memory/handoffs/_archive/ \
        memory/handoffs/README.md \
        memory/rounds/R<N>/plan.md memory/rounds/R<N>/verdict.md \
        memory/tools/validate.py \
        memory/tools/tests/test_validate.py \
        memory/STATE.md \
        CLAUDE.md  # or CONTEXT.md depending on which has the memory section

git commit -m "round: R<N> — memory hygiene dogfood (R50 G/H/I/J/L → in use)" \
  -- <list those paths again to scope-lock against any Codex parallel work>
```

**Use `git commit -- <paths>` explicitly** — there's been a documented
history of Codex's parallel session quietly staging files that ride
along into other commits if you `git commit` without path scoping.

---

## Validation criteria — how to know R<N> succeeded

| Check | Expected after R<N> |
|---|---|
| `validate.py` ERRORS | 0 |
| `validate.py` provenance WARN count | ≤ 5 (was 30) |
| `validate.py` "missing metric" WARN count | ≤ 30 (the rule is on, untouched claims emit) |
| pytest tests/ | ≥ 79 passed |
| pytest memory/tools/tests/ | ≥ 71 passed |
| Claims with `metric:` block | ≥ 8 |
| Claims with `status: obsoleted` | ≥ 1 (CLM-0008) |
| STATE.md `## Leaderboard` section | present with 8 rows |
| `query.py --best 6_axis --top 5` | 5 rows, R21 0.444 at top |
| handoffs/ top-level file count | 5 (was 14) |
| handoffs/_archive/ file count | 9 |
| R<N> verdict.md exists | Yes, with 3 mandatory Q-sections |
| `reserve_round.py` callers | 1 (this round) |

---

## Rollback plan

If R<N> goes sideways:

```bash
# Reset to before R52 commit, keep working tree
git reset --soft HEAD^

# Or fully discard
git reset --hard HEAD^
```

Per-step rollback is cheap because each patch is additive:
- B1 (metric backfill): re-edit each CLM, drop the metric block
- B2 (CLM-0008 obsoleted): revert status to `current`, drop obsoleted_* fields
- C1 (provenance fix): re-run the one-off script with MAPPING inverted, or `git checkout HEAD~ memory/claims/`
- C2 (handoffs archive): `git mv` files back
- A2 (validate soft warn): revert validate.py + test_validate.py edits

---

## Out of scope (do NOT do in R<N>)

- **Adding metric blocks to ALL 35 finding-type claims** — start with
  the 8 most-cited. Future rounds organically fill the rest when
  they touch their own claims.
- **Removing V4Config fields** (include_own_action_obs, phi_max,
  phi_settle) — they're tested + reproducibility anchors. Keep.
- **Touching scripts/score_run.py adoption** — that needs a real
  research round to use it (R53+ with actual experiments). R<N> is
  hygiene only.
- **Anything in the actual research pipeline** (training, eval scripts,
  ANDES code) — R<N> stays inside `memory/` + a few config touches.

---

## Adoption checkpoints (decide kill/keep at R55)

If after **R<N> + 2 follow-up research rounds**:

- `reserve_round.py` still has only 1 external caller (R<N> itself)
- Future rounds keep manually picking R-numbers
- No new claims add `metric:` blocks
- `query.py --best` is still not invoked by anyone

→ **Apply the M-criteria**:
- M1: 3 consecutive rounds without adoption → flag candidate for revert
- M2: a clean `git revert` of R50 G/I/J/L/E (keep K + H since K is
  immediately useful and H is 0-cost passive) leaves pytest + validate
  green → revert is safe

If adoption is real after R55, the R50 batch graduates from "stage 2
trial" to permanent infrastructure and this checkpoint is no longer
needed.

---

## Key file pointers

| Need | Path |
|---|---|
| The R50 batch (12 commits) | `git log --grep="R50\|opt [A-L]"` or `git log 109050f..6276909 --oneline` |
| Last research round | `memory/rounds/R51/verdict.md` (Codex's SAC h=64 negative) |
| Open question | `memory/questions/Q-0004.md` (Codex's AndesBaseEnv absorb, R<N> ignores) |
| Headline numbers (R30-era) | CLM-0005..0008 |
| Current production setting | CLM-0055 (TD3 norm 75ep h=64, supersedes CLM-0047) |
| Current best single seed | s51 h=64 = 0.365 (CLM-0054 cites) |
| Current best ensemble | HAWE-h64 median = 0.351 (CLM-0056) |
| Memory validate runner | `python memory/tools/validate.py` |
| Memory render runner | `python memory/tools/render.py` |
| WSL Python | `/home/wya/andes_venv/bin/python` |
| WSL repo path | `/mnt/c/Users/27443/Desktop/andes-rl-kundur` |

---

## TL;DR for the reader

**Goal**: prove R50 stage 2 (adoption) by doing one hygiene round that
exercises G/H/I/J/L on the way to clearing K's 30-WARN debt + archiving
old handoffs.

**Effort**: 30–40 min if you follow the playbook linearly. Each step
has an explicit "expect X" check, so you'll know within seconds if
you've gone wrong.

**Output**: one commit `round: R<N> — memory hygiene dogfood`, no
research, no V4 env changes, fully reversible.

**Start command**:

```bash
# Open this file
cat memory/handoffs/2026-05-17_R52_memory_hygiene_plan.md | head -40
# Pre-flight (Section "Pre-flight")
# Then Step 1
```
