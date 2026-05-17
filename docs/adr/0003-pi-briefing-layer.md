# ADR-0003: PI Briefing Layer in verdict.md + STATE.md

**Date**: 2026-05-17
**Status**: Accepted
**Related**: ADR-0001 (src layout), R39 (memory system origin), R59 (impl)

## Context

The memory system (R39) has four entity kinds — claim / question / round /
STATE.md — plus a non-schema scratchpad (handoffs). `verdict.md` is the
canonical write-target after a round closes; `STATE.md` is the daily-read
oracle auto-rendered from claims + questions + rounds.

These artifacts were designed for the **next agent**, not for the **PI**
(user). Verdicts carry jargon (`HAWE`, `lr-warmup`, `6-axis`, `s50 ckpt`),
cross-reference internal codes (`CLM-0065`, `Q-0007`, `R56-α`), and bury
forward-looking decisions in the last lines after 200+ lines of technical
content. The R57 verdict (240 lines) is representative.

A 2026-05-17 `/grill-with-docs` session surfaced the user's actual
complaint: not "jargon I don't recognise" (they understand LSTM / HAWE /
SAC) but **loss of the research story** — the user has stopped feeling
like a participant. Direct quote:

> 我很多时候懒得决策，关键是我要理解，研究时我要有参与感，ai很多时候比我
> 更懂技术。

Translation of the operational ask:

- AI keeps autonomous decision-making on technical choices
- PI gets a narrative they can engage with
- PI exercises **participation, not approval** — silence = AI proceeds
- One reading channel, not "汇报很多" fragmented across files

## Alternatives considered

**(A) Separate file `memory/BRIEFING.md`** — Rejected. User has "汇报很
多" fatigue. A parallel file invites silent abandonment ("I'll read it
later") and defeats the single-reading-channel goal.

**(B) Push briefing via Feishu / email per round** — Rejected.
Push-mode has its own silence dynamic; user explicitly asked for "对话
框里给我讲就行" — narrative inline in the active chat.

**(C) Reformat verdict.md to PI register** — Rejected. Verdicts have a
working purpose for the next agent: precise jargon, cross-refs,
hypothesis adjudication tables. Two audiences need two registers; do not
sacrifice agent-utility for PI-readability.

**(D) Q-NNNN schema fields like `recommended_action` / `urgency`** —
Rejected. Decisions about GPU budget, paper readiness, and risk flags do
not fit cleanly into Q-NNNN (which is a forward-uncertainty entity).
Round-author judgment per round is more honest than mechanical schema
derivation. And not all PI-relevant items map to an open Q.

## Decision

### 1. Fourth mandatory verdict section

`memory/rounds/RNN/verdict.md` (for N ≥ 59) **must** contain
`## 给 PI 的话` with five fixed sub-segments:

| Sub-segment | Purpose |
|---|---|
| **这周干了啥** | 1–2 sentences of context |
| **结果（一句话）** | Headline number / outcome |
| **意外** | Surprising finding / risk / pivot — the *participation hook* |
| **我默认下一步做** | Agent's intended default action |
| **你想插一脚就说** | Explicit invitation; silence = default proceeds |

Soft cap **≤ 30 lines** total. Validator warns on exceedance; does not
block.

### 2. Glossary auto-annotation

`memory/glossary.yml` maps project terms to one-line definitions
(< 30 chars). `render.py` walks the briefing text and annotates each
term on **first occurrence per briefing** as `term(definition)`.
Subsequent occurrences in the same briefing render bare. Goal: PI
never hits an unexplained acronym.

Matching uses ASCII-word lookarounds so Chinese characters do not
break term boundaries (e.g. `用LSTM时` matches `LSTM`).

### 3. STATE.md aggregation

`render.py` lifts the newest R59+ verdict's `## 给 PI 的话` body to a
new top section `## 给 PI 的简报（最新一轮）`, with glossary
annotation applied. A `## 历史简报` section below lists one-line
headlines (the "结果（一句话）" segment) from previous R59+ rounds.

Old sections (Headline Numbers, In-Flight, Open Questions, Recently
Closed, Latest Round, Leaderboard, Stats) remain unchanged below.

### 4. Agent chat-delivery contract

When an agent closes a round (writes `verdict.md`), it **MUST** output
the `## 给 PI 的话` body verbatim as its chat-closing turn. Saying "see
verdict.md" or pointing at STATE.md is not compliant. This is the
**primary** delivery channel; the file is archival backup.

This contract is enforced by CLAUDE.md text, not by tooling (no plausible
runtime check exists).

### 5. Backward compatibility

The cutoff is **R59 onward**. R01..R58 verdicts are not retrofit. The
`## 历史简报` section will be empty until R59 closes; then it grows
one entry per future round.

## Consequences

**Positive**

- PI re-enters research story without context-switching to a file
- AI retains technical autonomy (default action proceeds on silence)
- Glossary forces explicit "what does this jargon mean" rather than
  assuming reader knows
- One reading channel for PI (chat + STATE.md top), one write-channel
  for agents (verdict.md, two registers)
- Old verdicts unchanged (no retrofit burden)
- Test cutoff (R≥59) keeps validation incremental, not big-bang

**Negative**

- Verdict authors must context-switch between two registers per round
  (jargon body + PI-narrative briefing)
- Glossary is a maintained artifact; out-of-date entries actively
  mislead
- chat-delivery contract relies on agent compliance; no enforcement
  mechanism in tooling

**Neutral**

- STATE.md grows by ~30 lines + a historical headlines section. Still
  under 100 lines total; fits comfortably in a chat read.

## Implementation

R59 (this round). Files touched:

- `memory/rounds/_TEMPLATE_VERDICT.md` — add 4th mandatory section
- `memory/tools/validate.py` — enforce for R≥59; soft-warn on length
- `memory/tools/render.py` — extract + annotate + aggregate
- `memory/glossary.yml` — new file, seed terms
- `memory/tools/tests/test_validate.py` — new test cases
- `memory/tools/tests/test_render.py` — new test cases
- `memory/tools/tests/fixtures/rounds/R02/verdict.md` — add briefing
  segment (test only — fixture round R02 doesn't have to follow R≥59
  cutoff, but adding it lets render.py tests exercise the extraction)
- `CLAUDE.md` — agent chat-delivery contract
- `CONTEXT.md` — three new glossary entries
- `memory/rounds/R59/verdict.md` — dogfood (own 给 PI 的话 section)

## Future work (not in R59)

- Promote `PI_BRIEFING_LINE_CAP` from soft warn to hard error if the
  discipline holds for 5+ rounds
- Add `python memory/tools/query.py --briefing R<N>` lookup
- Optionally: weekly digest aggregator if per-round cadence proves too
  frequent
