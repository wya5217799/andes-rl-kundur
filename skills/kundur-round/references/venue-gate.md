# Venue Gate

Choose a journal in stages. A journal suggestion is a dated decision aid, not a
scientific verdict and not a permanent fact.

## Pass 0: constraints

Record the author's actual objective before searching:

- minimum acceptable tier under the author's institution's named system;
- stretch versus probability-of-acceptance preference;
- deadline and maximum tolerable review duration;
- APC and open-access constraints;
- article type, conference-extension status, and transfer preferences;
- audience and disciplinary center of gravity.

Do not infer an institutional ranking rule. If the author names a regional or
institutional list, ask for or verify the exact edition used by that
institution.

## Pass 1: shortlist

Run after the research question and likely contribution are concrete. Build a
main/backup/stretch shortlist from:

1. current official aims and scope;
2. accepted article types and conference-extension policy;
3. recent papers close to the contribution;
4. evidence and theory expectations visible in those papers;
5. official publication model and fees;
6. dated ranking or metric evidence required by the author's constraints;
7. transfer cost between candidates.

Use primary or official journal sources for scope, article type, author rules,
fees, and policies. Label ranking lists, crowd-sourced review times, acceptance
rates, and forum reports as external estimates with source and access date.

Return:

```text
Objective and hard constraints:
Candidate matrix:
Primary / backup / stretch:
Fit rationale:
Desk-reject risks:
Evidence or framing gaps:
Unverified items and owner:
Status: SHORTLISTED | BLOCKED
Review triggers:
```

`SHORTLISTED` is enough for format-neutral drafting. It is not permission to
make venue-specific compliance claims.

## Pass 2: lock

Run when the contribution, evidence boundary, and article type are stable.
Compare the full story—not merely keywords—to the current scope and a bounded
sample of recent close papers. Confirm extension policy, length, data/code
expectations, fees, and author constraints.

Return `LOCKED` only when:

- one primary and at least one transfer-compatible backup are named;
- every hard author constraint is verified or assigned to a human owner;
- the paper's contribution and evidence match the primary venue's audience;
- the manuscript or project record points to the dated decision record;
- no unresolved official-policy conflict remains.

The author or PI owns the final lock.

## Pass 3: refresh

Run before submission and after any material change to title, contribution,
article type, evidence, deadline, fees, ranking requirements, or journal
policy. A stale decision becomes `REVALIDATE`; it never silently remains
`LOCKED`.

After the refresh, load `submission-audit.md` for package compliance. The
venue gate chooses the destination; the submission auditor verifies the actual
package.
