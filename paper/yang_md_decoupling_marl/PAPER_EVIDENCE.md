# Paper evidence card — `yang-md-decoupling-marl`

This is the compact fact sheet for the fresh R485 manuscript. It is a writing
aid, not scientific authority. Resolve every paper claim to the named claim,
feed, and hash-valid result before publication.

## Paper identity and one-sentence result

- Fixed title: **Decoupling-Oriented Coordination of Paralleled VSGs With
  Multi-Agent Reinforcement Learning**.
- Paper type: bounded, guard-first evaluation of a corrected M/D-MARL object;
  not a successful-MARL paper and not a universal MARL verdict.
- Main result: 121/208 all-fresh policies meet both aggregate 5% decoupling
  endpoints, but 0/208 satisfy the registered endpoint-plus-command-activity
  contract on all four profiles.

## Results that may carry the paper

| Result | Exact finding | Where it belongs |
|---|---|---|
| Endpoint qualification | 121/208 policies meet both aggregate endpoints. | Abstract, Results, Conclusion |
| Complete-contract qualification | 0/208 policies pass the full profile-complete contract. | Abstract, Results, Conclusion |
| Guard counts | All 832 policy-profile blocks fail both normalized command-RMS and command-TV limits; 397 also fail RoCoF and 37 fail worst-frequency peak. | Main Results table/figure |
| Non-action Pareto subset | 5/208 policies meet both endpoints and every non-action guard; all five still fail command activity. | Results interpretation |
| Distance from action threshold | Action-only break-even multiplier: 97.6575 / 131.9193 / 140.2508 (min/median/max), versus the registered 1.10 limit. | Results robustness |
| Channel activity | Median comparator-relative ratios across 832 blocks: M RMS 31.2256, D RMS 5.6923, M TV 87.9674, D TV 83.4118. | Main or supplemental Results |
| Source factorial | No registered 6-second or separate 30-second source contrast establishes a positive material effect after Holm control. | Results; keep horizons separate |
| Deterministic comparator | Direct M/D passes the separate 30-second fresh-bank gate on 4/4 profiles. | Results; do not pool with learned policies |
| Training disclosure | All 208 final manifests are valid and record `alpha_at_floor=true`; this is not evidence of convergence or non-convergence. | Limitations |

Primary authority: `CLM-1525`, `paper/yang_md_decoupling_marl/reports/R485.md`,
and `results/research_loop/r485_60hz_source_factorial/r485-formal-20260829-a/formal_analysis.json`
(SHA-256 `2dad35d8e7f559bbcfa124dbae3628aa0d9ceae3ccfbe77996330c891927409b`).

## Post-hoc results that enrich, but cannot replace, the headline

Use these only with the labels **post-hoc**, **recorded-path**, or
**checkpoint diagnostic**, as applicable.

| Question | Bounded observation | Safe interpretation |
|---|---|---|
| Did projection create TV? | The exact common-reset componentwise projector satisfies `TV(projected) + terminal tracking residual <= TV(raw)` per channel. On the first frozen policy and four profiles, projected/raw channel-TV ratios are 0.3607--0.4442; exact projector replay error is zero. | TV non-increase is structural for this recursion; the observed gaps quantify attenuation rather than identify a plant mechanism. |
| Does the actor use previous executed action? | On 24 policies (8 arms x 3 seeds) and one frozen profile, replacing the two previous-action input slots by their full-record means leaves 0.0710--0.2046 of raw TV; median 0.1438, 48/48 channel ratios <=0.50. | The actor output is strongly sensitive to this input replacement on the tested frozen paths. The full-record mean is an acausal post-hoc anchor, so this is not feedback amplification, a deployable intervention, or a plant counterfactual. |
| Is RMS quasi-static? | On 24 policies x four profiles, the constant-anchor/actual raw-RMS ratio has median 0.9588; 141/192 ratios are >=0.90 (D 87/96; M 54/96) and none are <=0.50. For the one included checkpoint, temporal variation still contributes 37.45%--51.23% of raw RMS-squared energy. | Comparable aggregate norm is frequent, especially for D, but it does not mean that the output is temporally static or that a quasi-static source is dominant. |
| Does the reward distinguish temporal order? | Reordering the same action row multiset changes combined TV by 13.22--18.46x while the registered action cost is identical. | The tested action-cost term is TV-blind; this does not prove that the missing TV term caused training outcomes. |
| Is fixed previous-action input sufficient? | Recursive projection on recorded observations reduces total TV to 0.2499--0.3186 of actual, but leaves it 18.63--31.68x the direct comparator; joint RMS remains 6.53--8.40x the comparator and M RMS rises on all four profiles. | The single intervention is insufficient and did not justify an ANDES run. |

Post-hoc authority: `CLM-1530`,
`paper/yang_md_decoupling_marl/reports/R486.md`, and
`results/research_loop/r486_r485_posthoc_intake/analysis.json`
(SHA-256 `75c911f83a9f50c9f208e94c18c039a3b170d09d2575f7396958dcf16b1b257c`).
The expanded RMS grid is at
`paper/yang_md_decoupling_marl/working/r485_quasistatic_rms_grid_20260831/result.json`
(SHA-256 `3547418b3802ef821df3a5ff52f444d97d2820ea2b7c8347a2fb1ce334c4fd13`).

## Recommended paper compression

The strongest compact Results object is a qualification funnel:

```text
208 valid final policies
  -> 121 meet both aggregate endpoints
  ->   5 also meet every non-action guard
  ->   0 meet the complete command-activity contract
```

Pair it with one command-activity distribution figure or table. Put source
factorial estimates in a compact table or supplement. Keep the mechanism
diagnostics in Discussion or an exploratory supplement; they are not a fourth
main contribution.

## Mechanism language that is safe now

Use language close to:

> For the exact common-reset componentwise limiter, executed command TV is no
> greater than raw command TV. On frozen observation paths, replacing the
> time-varying previous-executed-action actor input by its within-record mean
> reduced raw TV in all 48 tested channel-policy cases, with ratios no greater
> than 0.205. Constant-anchor raw RMS was at least 0.90 times actual raw RMS in
> 141/192 cases (M: 54/96; D: 87/96). These are finite-grid actor-path
> statements, not additive causal shares or closed-loop counterfactuals.

Do not say that the analysis proves a unique root cause, a closed-loop
counterfactual, a stability mechanism, or a physically safe intervention.

## Claim ceiling

- Command RMS and TV are comparator-relative normalized command-activity
  summaries, not actuator energy, wear, fatigue, thermal load, hardware harm,
  or deployment safety.
- Failure to establish a source effect is not zero effect or equivalence.
- The finite one-topology benchmark does not establish topology
  generalisation, universal MARL inadequacy, stability, convergence, or
  optimality.
- The quasi-static and previous-action interventions are not additive causal
  decompositions. The anchors use full-record means and therefore must remain
  explicitly post-hoc, frozen-path, and non-deployable diagnostics.

## Mathematical question status

- `Q-0112` remains a successor-line information-margin question. The current
  archive does not identify an endogenous action-dependent information tree or
  the owner/observation map of the fleet-common `B_+` coordinate. Do not send
  the old question unchanged and do not make it a submission gate for this
  paper.
- Two independent returns for the current-paper finite-record TV/RMS audit
  were compared adversarially. The undated second verifier passes repo-side on
  the original ZIP and is preferred over the first verifier, whose own
  comparison tolerance rejected eight non-load-bearing float values. The
  shared TV theorem and finite-grid counts are accepted under project verdict
  `ADVERSARIAL QUALIFIED PASS`; see
  `working/gpt_pro_r485_mechanism_math_20260901/COMPARATIVE_ADVERSARIAL_REVIEW.md`.
  Neither return establishes a unique mechanism, causal plant intervention,
  training benefit, or full-policy sensitivity distribution.

## Writing order

1. Draft the Abstract and Introduction from the formal R485 funnel.
2. Build Results from R485, then use R486 only for magnitude and precision.
3. Add at most the single projector inequality and the bounded mechanism
   paragraph approved in `COMPARATIVE_ADVERSARIAL_REVIEW.md`; keep them in
   Discussion or a compact analysis paragraph, not as a new headline or fourth
   contribution.
4. Recheck every cited number against its source locator and preserve the
   endpoint/contract, 6-second/30-second, and formal/post-hoc separations.
