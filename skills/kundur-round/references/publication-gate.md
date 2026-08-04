# Publication gate

Run this gate after the experiment's machine-readable decision artifacts and
bounded feed conclusions exist, but before claim registration, the round
`verdict.md`, manuscript prose, polished figures, or venue formatting. Here
"decision artifacts" means final guards/summaries produced by the analysis,
not the later ledger `verdict.md`. Use the feed as the pre-draft claim sheet.

Before invoking global auditors, read
`skills/kundur-round/references/research-skill-adapter.md`. It is the only
project-specific adapter; do not rely on copied ANDES rules inside a global
skill.

## Semantic review route

1. **Evidence audit** — apply `audit-manuscript-evidence` to the feed's
   Observations and Conclusions against final machine-readable decisions,
   any already-current parent CLM records, sealed
   summaries, raw result fields, validity guards, exclusions, and
   supersession. A LaTeX draft is not required.
2. **Domain audit** — apply `review-power-systems-manuscript` to the same
   pre-draft claim sheet, model, units, actuator path, endpoints, baselines,
   inference, and scope. Mark presentation-only checks not yet applicable.
3. **External context** — classify:
   - `CURRENT`: a verified landscape or nearest-work source directly covers
     the result axis; cite its path and cutoff.
   - `DEEP-RESEARCH-REQUIRED`: novelty, differentiation, or related-work
     wording depends on an unverified or newly opened axis. Run a bounded
     `deep-research` task before passing the gate.
   - `NOT-APPLICABLE`: the result stays out of the paper or is a pure
     implementation fact with no external scientific claim.
4. Set the claim disposition to `ENTER`, `QUALIFY`, or `STAY-OUT`.

The repository ledger and sealed artifacts remain authoritative. Skill output
is a derivative review view.

## Feed section

Record only the decision summary in the existing feed:

```markdown
## Publication gate

- **Evidence audit**: PASS | QUALIFIED | FAIL — reason + authority pointer.
- **Domain audit**: PASS | QUALIFIED | FAIL — reason + checked boundary.
- **External context**: CURRENT | DEEP-RESEARCH-REQUIRED | NOT-APPLICABLE —
  verified source and cutoff, required question, or stay-out reason.
- **Claim disposition**: ENTER | QUALIFY | STAY-OUT — manuscript action.
- **Allowed claim**: strongest evidence-matched sentence.
- **Stay-out**: stronger claims that remain prohibited.
```

Do not create one durable review report per round. Keep detailed review
discussion in the active conversation or `tmp/`. Persist a finding only when
it becomes one of the existing durable types: a claim correction, open
question, ADR, code issue, updated literature matrix, or registered manuscript
artifact. If a durable consolidated review is required, register it in the
active manuscript line's `ARTIFACTS.json`; individual reviewer passes remain
ephemeral.

## Deterministic close

After the semantic gate passes or qualifies the feed, finalize the same-round
claim card to the gate's Allowed claim, bind the card back to this feed, and
preserve every stronger statement under Stay-out. The earlier reserved claim
stub supplied identity only; it was not a scientific registration.

Run:

```powershell
python memory/tools/feed_check.py <feed-path>
```

`FAIL` in evidence or domain review blocks publication use.
`DEEP-RESEARCH-REQUIRED` blocks readiness until the bounded research task is
closed. `STAY-OUT` may pass because excluding an unsupported result is a valid
publication decision. The checker also resolves the Identity round, claim
records, and repository-relative evidence pointers; requires every numeric
Observation to carry a claim ID; requires every Observation to appear in the
manuscript mapping; and rejects placeholder gate fields. It cannot decide
whether an interpretation is physically correct or whether a fact has been
semantically duplicated across ledgers; those remain the evidence and domain
auditors' responsibility.
