<!-- Filename convention: prefer `verdict.md` (canonical). validate.py uses
     canonical-preempt semantics: if `RNN/verdict.md` exists, it is the only
     file validated for that round; any sibling `*verdict*.md` (e.g.
     `round_28_to_34_final_verdict.md`) is treated as a supplementary note
     and not enforced to the Q-section schema. -->

# R## verdict — <one-line title>

**Date**: YYYY-MM-DD
**Status**: in-progress
**Type**: experiment | infrastructure | analysis
**Wall**: ~Xh

## TL;DR

<≤3 sentences. The first sentence is auto-extracted by `render.py` into
STATE.md's "Latest Round" line, so make it self-contained.>

<!-- R291+: keep the entire verdict at <=80 nonblank lines. Method, results,
     guards, and interpretation live in the Feed or machine JSON; verdict.md
     only carries lifecycle state, question transitions, PI briefing, and the
     final Feed pointer. -->

<!-- ============================================================
     The 3 Q-sections below are MANDATORY. validate.py enforces
     they exist, even if every line is "none".
     ============================================================ -->

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `<paper/<line>/reports/RNN.md or results/<run>/FEED.md>`

<!-- ============================================================
     `## 给 PI 的话` is mandatory from R59 onward (ADR-0003).
     ADR-0011 tightens the forward contract from R317 onward:

     1. Answer only three reader questions: 发生了什么、这说明什么、
        下一步做什么. Each label appears exactly once.
     2. Write complete natural Chinese first. No English, abbreviations,
        repository IDs, filenames, code names, or obvious specialist terms.
     3. Keep a number only when it directly tells the reader how much better,
        how much worse, or whether the result passed. Counts and identifiers
        stay in the Feed/results evidence layer.
     4. The Feed, claim, result JSON, and technical verdict skeleton retain
        professional names, metrics, IDs, and exact data for audit.

     Paste only the body below verbatim as the user-facing closing report.
     Do not prepend or append a technical recap unless the user asks for it.
     ============================================================ -->

## 给 PI 的话

**发生了什么**：<用完整人话交代这次遇到的问题、做了什么改变>

**这说明什么**：<说明有没有达到事先要求、能说明什么、还不能说明什么>

**下一步做什么**：<说明默认继续做什么，以及什么情况下立即停止>
