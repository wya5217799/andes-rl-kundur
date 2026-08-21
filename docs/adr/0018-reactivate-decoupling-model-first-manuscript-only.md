# ADR-0018: Reactivate decoupling-marl-model-first for manuscript-only closure

- **Status:** Accepted
- **Date:** 2026-08-14
- **Deciders:** repository owner (author/PI)
- **Related:** ADR-0015, ADR-0008, ADR-0010

## Context

ADR-0015 froze `decoupling-marl-model-first` as a navigation-frozen evidence
line after its bounded deterministic-control investigation ended without a
qualifying learned-controller increment, and moved the fixed MARL title to
`paralleled-vsg-marl`. Freezing changed navigation and execution authority
only and did not weaken the line's bounded claims.

The owner now directs that this line's terminal evidence (R306-R363,
CLM-0740-CLM-0965) be written up as a paper following the manuscript-line
process, while the experiment side stays frozen: no new rounds, claims,
questions, simulator execution, or training on this line.

## Decision

Reactivate `decoupling-marl-model-first` as an active, selectable manuscript
line in `manuscript-closure` stage, with priority below the two executing
experiment lines.

- The experiment side remains frozen: stop conditions forbid any new
  evidence round, claim, question, simulator execution, or training on this
  line. Manuscript work only.
- The write scope remains the line's own paper root; the shared ledger,
  `results/`, and other manuscript lines stay read-only.
- The fixed MARL title is not supported by this evidence and is not reused
  here. The paper adopts an object-matched working title (methodology plus
  bounded deterministic-control framing); exact wording is fixed by the PI at
  the argument-contract stage, and no title term may exceed the registered
  claim ceiling.
- Venue state restarts at unassessed and must pass the venue gate (Pass 1
  shortlist before venue-specific drafting, Pass 3 refresh before
  submission).
- All existing claims, feeds, results, and hashes remain unchanged.

## Consequences

- `session_context.py --line decoupling-marl-model-first` selects this line
  again.
- Cold-start fallback priority keeps the two experiment lines first.
- The paper's evidence boundary is exactly the 45 bound feeds and their
  claims; reviewer requests that need new data or execution are future work,
  not this line's repair.
- ADR-0015's freeze rationale (title-goal failure) is preserved in the line
  history; this decision changes only manuscript-writing authority.
