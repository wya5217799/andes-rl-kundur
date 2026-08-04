# ADR-0011: Two-Layer Plain-Language Research Reporting

**Date**: 2026-08-03
**Status**: Accepted
**Supersedes**: ADR-0003 briefing format for R317 onward
**Related**: ADR-0008, `memory/rounds/_TEMPLATE_VERDICT.md`,
`memory/tools/validate.py`

## Context

The repository already separates measured evidence into results, feeds,
claims, and verdicts, but the chat-closing PI briefing still copied technical
names, acronyms, round IDs, filenames, and metric labels. Glossary annotation
explained those terms without fixing the underlying audience mismatch. The
user's explicit requirement is stricter: a report that still requires the PI
to decode repository language has failed, regardless of scientific accuracy.

## Decision

Research delivery has two layers with different jobs.

### 1. Reader-facing report

From R317 onward, `## 给 PI 的话` contains exactly three labelled parts:

1. `发生了什么`
2. `这说明什么`
3. `下一步做什么`

The body is complete natural Chinese. It contains no English, abbreviation,
repository identifier, filename, code name, or obvious specialist term. A
number may remain only when its sentence directly communicates improvement,
deterioration, or pass/fail. Counts, sample sizes, run IDs, and process numbers
stay out.

The agent pastes only this body verbatim as the default chat-closing report.
No technical recap is placed before or after it unless the user explicitly
asks for technical detail.

### 2. Technical evidence

The feed, result artifacts, claim card, and technical verdict skeleton retain
exact professional terminology, metrics, identifiers, hashes, and values.
Nothing is deleted or weakened for readability. These artifacts remain the
auditable source for manuscript writing and evidence review.

## Enforcement

`validate_verdict_structure()` is the public enforcement seam. For R317+ it
requires the three labels and rejects Latin text/code formatting, a bounded
list of common project-jargon terms, and number-bearing sentences without a
result-meaning cue. The vocabulary list is a guard against obvious leakage,
not a claim that plain-language quality can be fully automated; authors must
still perform the semantic rewrite first.

`render.py` accepts both the ADR-0003 legacy headline label and the ADR-0011
meaning label. Historical verdicts are immutable. Glossary annotation remains
available for legacy briefings but is no longer the forward solution.

## Consequences

- The PI receives the research story without decoding the repository.
- Technical evidence remains complete and auditable in its existing layer.
- Verdict authors must genuinely translate the result instead of replacing
  English jargon with Chinese jargon.
- The validator may need a small vocabulary update when a recurring specialist
  term leaks through; such updates are forward safeguards, not historical
  rewrites.
