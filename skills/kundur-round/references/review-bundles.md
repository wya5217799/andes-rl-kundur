# Review Bundles

A review bundle is one bounded owner that runs several complementary review
passes over the same frozen input and returns one consolidated decision. Use a
bundle when missing one class of defect is costlier than the additional model
tokens. Keep the five scientific gates unchanged.

Review breadth is not authority. Each pass keeps its own evidence source and
completion rule; synthesis deduplicates findings without erasing disagreements.
Disclose when all reviewer roles used the same model family.

## Experiment vulnerability bundle

Use this bundle for a formal or high-consequence study, a requested red-team,
or a result whose interpretation may change a claim. A small reversible pilot
normally needs one compact pre-check and post-check instead.

### Design red-team

Run before prospective freeze. The project-native study planner remains the
primary scientific owner. Cover, in one coordinated return:

- whether the hypothesis and estimand answer the stated question;
- comparator identifiability, confounds, leakage, information advantage, and
  outcome-dependent choices;
- missing controls, baselines, ablations, negative controls, or stress cases;
- sampling, analysis unit, uncertainty, multiplicity, exclusions, and missing
  data handling;
- feasibility, resource, safety, ethics, provenance, and reproducibility risks;
- the strongest alternative explanation and the observation that would
  distinguish it;
- pass, qualify, fail, and invalid criteria plus a kill-or-pivot rule.

Use bounded `deep-research` for a genuine external-knowledge gap and
`idea-evaluator` for the value of a successor direction. Academic Research
Suite `experiment-agent plan` may add a methodology blueprint. Project and
domain owners adopt any change prospectively.

**Return:** a ranked vulnerability ledger. Every blocking item names the
failure consequence, required prospective repair, authority, and verification.

### Frozen-run anomaly review

During a frozen active run, inspect monitoring integrity, provenance, protocol
deviation, safety, and whether the anomaly creates a successor question. Keep
the current run monitor-only. External research and adversarial interpretation
remain advisory and cannot change metrics, comparators, thresholds, exclusions,
or the registered story.

**Return:** continue-monitoring, authorized-amendment-required, or
successor-required, with the anomaly and affected future decision recorded.

### Result challenge

After terminal analysis, start from project-native validity records. Add only
passes that contribute a distinct artifact:

- evidence and provenance trace;
- project-declared domain audit;
- statistical or reproducibility validation, including bounded ARS
  `experiment-agent validate` when useful;
- alternative-explanation and sensitivity challenge;
- bounded external-context check for novelty or interpretation.

Inputs with missing provenance or internal contradiction remain quarantined.
The bundle returns to the Result gate; only an accepted Result may enter the
Claim gate.

## Final manuscript review bundle

Use by default for a complete, claim-bearing manuscript approaching submission
when the required capabilities are available. Use a focused review for an
immature draft or one isolated concern.

### Entry

Freeze one manuscript snapshot and provide:

- target venue or explicit venue-neutral status;
- allowed claims, qualifications, stay-out claims, and evidence locators;
- exact figures, tables, references, supplements, and build target;
- project-required evidence, domain, or compliance owners;
- reviewer comments and response material when this is a revision.

A missing truth boundary blocks the bundle. Missing venue lock permits
venue-neutral review but not a submission-ready decision.

### Coverage

Run complementary passes against that same snapshot:

1. **Truth:** the `evidence-audit.md` and `power-systems-audit.md` modules
   check claims, numbers, units, comparisons, and source artifacts.
2. **External context:** bounded `deep-research`, citation verification, or ARS
   claim-reference checks examine closest work, missing citations, and factual
   support without becoming project evidence.
3. **Peer review:** ARS academic-paper-reviewer `full` mode supplies editorial,
   methodology, domain, perspective, devil's-advocate, and synthesis views.
4. **Presentation:** `pre-submission-reviewer` checks macro logic, prose,
   grammar, LaTeX, figures, and visible submission defects.
5. **Package:** exact build inspection, current venue facts, and the
   `submission-audit.md` module check the actual submission package.

Do not repeat a narrower mode already contained in a broader pass on the same
snapshot. Use ARS `methodology-focus` earlier when only Methods/Results exist;
use `full` for the complete manuscript, then `re-review` after material fixes.
Use `quick`, `guided`, or `calibration` only when that specific return is the
decision need.

### Synthesis and revision

Preserve every independent report before synthesis. Consolidate findings by
scientific consequence rather than reviewer count:

1. evidence, validity, ethics, or compliance blockers;
2. claim strength and comparison attribution;
3. methodology, statistics, and reproducibility;
4. novelty, related work, and venue fit;
5. argument, figure, format, and language defects.

Return each disagreement instead of averaging it away. A general reviewer
cannot close a project evidence or domain finding. After revision, run ARS
`re-review` when a multi-role finding set exists, re-run affected truth and
package checks, and verify that claim strength did not drift.

### Completion

Return one review packet:

```text
Reviewed snapshot:
Required passes and invocation status:
Completed passes and artifacts:
Blocking findings:
Deduplicated revision ledger:
Material disagreements:
Claim-strength drift:
Exact package status:
Decision: NOT-READY | QUALIFIED | READY
Next authorized action:
```

`READY` requires every required owner to return a permitting result, every
blocking finding to be resolved or formally accepted by its authority, the
exact package to pass its mechanical checks, and no unsupported claim-strength
increase. Capability unavailability is reported; it is never simulated.
