# Affected claims inventory — R478 M/D base-convention invalidation (2026-08-24)

## What happened

`GENCLS.M/D` are base-converted power parameters in ANDES. The pre-R478 V4
environment wrote device-base numbers directly into system-base runtime
arrays: runtime inertia/damping were halved, the reset anchor drifted (a zero
first action changed runtime M/D), and every commanded action had half its
declared physical effect. All time-domain and derived evidence produced on
that object is invalid as evidence until corrected revalidation replaces it.
This is an evidence-object invalidation, NOT a verdict that each conclusion
is false — relative conclusions may survive; absolute numbers will not.

## Criterion (machine-readable)

A current claim is **suspect** if its evidence (evidence_refs / provenance /
scripts / result roots) traces to the pre-R478 V4 object:

- old `paralleled-vsg-marl` line runs (R1-R369, V4 plant, direct M/D actions);
- `yang-md-decoupling-marl` line runs (R398-R477: deterministic headroom
  gates, SAC/factorial training, energy-port banks, topology variants);
- storage/energy-port line runs (R371-R396, wrapper executes the affected
  zero-M/D base step);
- EIG/static anchors and LTI model validation on the V4 plant (D was
  overwritten to the wrong base at setup, so even static results are affected).

**Excluded** (correct or unrelated evidence object):

- `decoupling-marl-model-first` line (R306-R364 family; separate env with the
  correct conversion, verified zero-action no-jump, CLM-0740);
- PPVSM1 diagnostic-cell rounds (R387-R397; separate minimal cell);
- pure methodology / infra / decision claims (ranker audits, tools, Q
  closures, paper strategy) — these carry no V4-object numbers.

## Tiers

| Tier | Count | Action |
|---|---|---|
| TIER-1 suspect (flagged) | 285 | `suspect: true` + `suspect_round: R478` + reason on the card; listed in STATE.md |
| TIER-2 review (not flagged) | 37 | evidence mixes affected and non-affected roots, or claim is metric/tooling/code-fix content; needs per-claim review before citation |
| EXCLUDED (model-first / PPVSM1 / methodology) | 58 + 49 | not flagged |

Regeneration: the classification JSON below is the authoritative id list.
Re-run the classifier (criterion above) if the claim set changes.

## Files

- `suspect_claims_20260824.json` (+ `.sha256`) — tier-1/tier-2/excluded id lists.
- STATE.md section "Suspect Claims (evidence object invalid)".
- Note NOTE-NNNN (md-base-convention-suspect) — discovery + scope summary.

## Lifecycle

Suspect markers are non-terminal: status stays `current` until replacement
evidence exists. When corrected revalidation evidence closes, each affected
claim is flipped via the normal `correction`/`superseded`/`obsoleted`
mechanism; the suspect fields are then removed by
`memory/tools/flag_suspect_claims.py clear --ids ...`.

Tooling: `python memory/tools/flag_suspect_claims.py list|flag|clear`.
