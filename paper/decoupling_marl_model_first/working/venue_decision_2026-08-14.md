# Venue decision record — decoupling-marl-model-first (2026-08-14)

Status: SHORTLISTED (Pass 1). The author/PI owns the final lock (Pass 2).

## Pass 0 constraints

| Item | Recorded value | Owner |
|---|---|---|
| Minimum tier | TPWRS is the stated target direction, not a hard constraint; the final objective is a good paper | author/PI (2026-08-14) |
| Stretch vs acceptance | target TPWRS as aspiration; accept a backup venue when the paper's quality argues for it | author/PI |
| Deadline | none stated | author/PI |
| APC / open access | not stated | author/PI |
| Article type | full journal paper (supervisor recommendation 2026-08-14; pending author confirmation) | author/PI |
| Audience | power-systems dynamics and control; VSG/storage coordination; model-based control with learning-for-grid evidence | fixed by evidence |

Unstated Pass 0 items are not inferred. Pass 2 lock requires the author to
confirm or waive each item above.

## Pass 1 shortlist

Objective: publish the line's terminal evidence as an
implementation-faithful methodology plus bounded deterministic-control paper
with a structural-diagnosis finding; no MARL claim; negative learning-family
results reported as bounded gate outcomes.

### Candidate matrix

| Venue | Model | Role | Transfer cost | Desk-reject risk |
|---|---|---|---|---|
| IEEE Transactions on Power Systems | hybrid OA | primary | — | validation-breadth expectation; must not read as a failed-MARL paper |
| IEEE Transactions on Sustainable Energy | hybrid OA | backup | low (same IEEE format) | storage/VSG integration framing must stay central |
| Electric Power Systems Research | hybrid OA | backup | medium (Elsevier format) | methodology-only novelty |
| IEEE Open Access Journal of Power and Energy | fully OA, APC | stretch | low (IEEE format) | selectivity; APC budget unconfirmed |

### Fit rationale

- TPWRS is the discipline home for power-system dynamics, control, and
  storage coordination and regularly publishes methodology papers with
  bounded case studies. Official resource site:
  <https://cmte.ieee.org/tpwrs/> (accessed 2026-08-14).
- TSTE covers renewable/storage integration and grid-forming/VSG control;
  suitable if the storage-coordination angle is foregrounded.
- EPSR welcomes implementation-oriented and bounded/negative evidence
  papers.
- OAJPE is fully open access with an APC; a good fallback for a
  methodology-heavy paper with negative components. Official PES page:
  <https://ieee-pes.org/publications/open-access-journal-of-power-and-energy/>
  (accessed 2026-08-14).

### Desk-reject risks (primary)

1. Title or abstract promising learning/MARL value - blocked by the
   object-matched title policy.
2. Single modified Kundur topology, two operating points, offline
   finite-bank headroom (LOCAL-ONLY archive), no holdout on R358/R363 - must
   be an explicit Limits item, positioned as bounded evidence for the
   methodology, not plant claims.
3. Centralized QP-on-frozen-linear-predictor controller read as a weak
   control contribution - position it as the deterministic baseline layer of
   the gate framework.
4. "No MARL was trained" read as a failed attempt rather than a gated
   methodology - the argument contract must make the gate sequence the
   contribution.

### Evidence or framing gaps before Pass 2 lock

- Comparative headline claims (deterministic vs zero control; four-channel
  vs three-channel action basis) need the comparator contract of the
  comparison-identifiability gate before claim-bearing drafting.
- The Introduction's related-work pool must be built from verified
  retrieval; `working/hybrid_control_literature_note.md` is an input, not a
  final reference list.
- Exact title wording and length target are fixed at the
  argument-contract stage by the PI.

### Unverified items and owner

| Item | Owner |
|---|---|
| TPWRS page limits, overlength charges, OA policy (official rules at cmte.ieee.org/tpwrs) | supervisor, before Pass 2 |
| TSTE scope statement for methodology papers | supervisor, before Pass 2 |
| EPSR author rules | supervisor, before Pass 2 |
| OAJPE APC amount | supervisor, before Pass 2 |
| Pass 0 constraints (tier / deadline / fees) | author/PI, before Pass 2 |
| Ranking and impact metrics: external estimates only, never gate input | — |

Status: SHORTLISTED

Review triggers:

- before venue-specific framing (manuscript drafting);
- before submission (Pass 3 refresh; official sources re-checked);
- after any material change to title, contribution, evidence, or article
  type.

## Pass 2 preparation note (2026-08-14)

- Official TPWRS anchors located: resource-site FAQ
  (<https://cmte.ieee.org/tpwrs/contact-info-and-faq/>) and common-mistakes
  page (<https://cmte.ieee.org/tpwrs/common-mistakes-omissions/>). The exact
  regular-paper page limit and overlength-charge rules still need to be read
  from the official information-for-authors page at Pass 2; third-party
  guides are external estimates and are not used as authority.
- Official PES authors-kit page located for Pass 2 reading:
  <https://ieee-pes.org/publications/authors-kit/information-for-authors-of-ieee-power-energy-society-transactions-papers/>
  (found 2026-08-14; content not yet read in detail).
- Drafting is venue-neutral for now (the Pass 1 shortlist permits
  format-neutral drafting); venue-specific length/framing decisions wait for
  Pass 2 lock.
