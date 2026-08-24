# Paper Writing Protocol

Use this protocol whenever the route includes manuscript story design,
drafting, material revision, or whole-paper review. It combines focused prose
generation with explicit scientific control without creating another project
state machine.

## Division of responsibility

| Responsibility | Owner |
|---|---|
| Scientific facts, scope, authorization, and canonical evidence | Repository or user-provided evidence authority |
| Technical-paper logic chain | `tech-paper-template`, or the paper-type-specific equivalent |
| Methods, Results, Discussion, Related Work, Conclusion, and Abstract prose | `paper-writer` |
| Technical Introduction prose | `intro-drafter`, after the story and evidence are stable |
| Faithful sentence-level language repair | `paper-polish` |
| Argument architecture when the logic remains unresolved | ARS academic-paper plan or outline branch |
| Controlled material revision, rebuttal traceability, and multi-role re-review | ARS academic-paper or reviewer workflow |
| Claim truth, domain correctness, and journal compliance | Specialist audit skills |

The rule is: focused Supervisor skills produce the paper; ARS supplies the
control mechanisms that the focused skills do not own; specialist audits
decide whether the science and package are supportable. No skill may promote
its own draft or review opinion into scientific authority.

## Pre-result use

This protocol is not restricted to a finished manuscript. Before or during an
experiment, use only the parts whose inputs already exist:

- use W1-W2 as an evidence-demand analysis to expose missing comparisons,
  observations, or figures before design freeze;
- during a frozen active run, draft stable Methods or system descriptions from
  the frozen contract and define figure structure from predeclared metrics;
- keep Results, headline contributions, Abstract, and title provisional until
  the Result and Claim gates return accepted inputs.

Planning support never changes an active experiment. An outcome-dependent
metric, figure, or story change belongs to an authorized amendment or successor
attempt.

## Entry contract

Before producing manuscript prose, settle:

1. the active paper or deliverable scope and its writable files;
2. paper type and target reader;
3. current venue state and any live constraints that affect length or form;
4. approved claims, explicit exclusions, and evidence locators;
5. whether the task is story design, new prose, language-only editing,
   bounded material revision, or structural rewrite;
6. the exact artifact to deliver and the gate that will accept it;
7. for comparative headline claims, a completed comparator contract that names
   what differs and what conclusion that difference can identify.

Missing evidence blocks claim-bearing prose. Missing venue lock does not block
venue-neutral drafting, but it blocks venue-specific framing and formatting.

## W0: freeze the truth boundary

Inventory headline claims, negative or null results, limitations, measured
conditions, and prohibited extensions. In a governed repository, reuse its
claim and evidence records. An external Evidence Map or Claim Registry is only
a temporary view over those records, never a competing ledger.

Every material claim needs:

```text
claim identifier or stable label
source locator
allowed strength
tested scope
required qualification
target section or figure
```

Run the repository's pre-draft publication or evidence gate when one exists.
Do not continue to W1 on a failed hard gate.

For every headline claim that compares methods, architectures, policies,
baselines, control strategies, or ablations, read
[comparison-identifiability-gate.md](comparison-identifiability-gate.md) and
complete its comparator contract before W1. A measured difference between two
arms does not by itself identify the architecture or method named in the prose.
`BLOCK` stops claim-bearing drafting; `QUALIFY` sets the wording ceiling for all
sections.

## W1: establish one argument contract

Use `tech-paper-template` for a technical paper and its paper-type equivalent
for other genres. The contract must make these links explicit:

```text
problem and stakes
  -> limitations of existing work
  -> research objective or key idea
  -> real challenges
  -> method components
  -> contribution claims
  -> experiments, figures, and evidence
```

Run ARS plan or outline only if this chain remains ambiguous, a contribution
has no evidence-bearing section, or sections make incompatible commitments.
Do not run ARS merely to restate a stable chain in another template.

For cross-session work, promote at most one canonical argument contract under
the active project's artifact policy. Otherwise keep the planning view
ephemeral.

## W2: create section and paragraph contracts

Before drafting a section, define its job, inputs, allowed claims, exclusions,
figures or tables, and exit sentence. For each load-bearing paragraph, settle:

```text
paragraph job
claim or observation
evidence locator
permitted inference
required qualifier
relationship to the next paragraph
```

These bindings are working controls. Keep them in temporary storage unless
another session must depend on them; if persistence is necessary, consolidate
them into the single argument contract rather than creating one file per
section or reviewer.

## W3: generate prose in dependency order

For a full empirical paper, default to:

1. Methods or system description;
2. Results;
3. Discussion and limitations;
4. Related Work and differentiation;
5. Introduction;
6. Conclusion;
7. Abstract and title.

This order keeps the Introduction and Abstract from promising a paper that the
evidence-bearing sections do not deliver. A bounded section request may enter
directly at that section once W0-W2 are satisfied.

Use `paper-writer` for the body and `intro-drafter` only for the technical
Introduction. Design figures once the corresponding claim and data definition
are stable. Do not ask multiple writing skills to generate competing versions
of the same section unless the user explicitly requests alternatives.

## W4: run write-time consistency gates

Before a section is accepted:

1. bind every factual, quantitative, causal, mechanism, robustness, and
   generalization statement to the approved truth boundary;
2. distinguish observation from interpretation and hypothesis;
3. check terminology, notation, units, population, conditions, and metric
   definitions against the rest of the paper;
4. verify that contribution strength has not increased during prose
   generation;
5. verify citations independently when the selected writing skill requires it;
6. re-run the comparison-identifiability gate whenever a comparator, title,
   contribution, or causal attribution changes;
7. keep placeholders and unsupported conveniences out of final prose.

For a full draft, also check Abstract, Introduction, Results, Discussion, and
Conclusion for the same headline claims, bounds, and numerical values.

## W5: review in consequence order

Review only after the draft has enough evidence binding to make review useful:

1. claim-to-artifact or publication gate;
2. domain specialist review;
3. bounded literature or novelty check when an external-context gap remains;
4. for an immature draft or isolated concern, one focused review;
5. for a complete claim-bearing manuscript approaching submission, the
   comprehensive [Final manuscript review bundle](review-bundles.md).

Consolidate overlapping findings by scientific consequence. Reviewer count is
not review quality, and broad presentation review cannot close a failed
scientific gate. Token cost alone is not a reason to omit a complementary
pre-submission pass once the bundle entry contract is satisfied.

## W6: revise according to change class

Classify each requested change before editing:

- **Language-only:** use `paper-polish`. Preserve scientific meaning and report
  any meaning-risk edit.
- **Bounded material change:** use a block- or issue-bound revision plan. ARS
  patch revision is preferred when untouched text must be protected. Re-run
  the affected evidence, domain, citation, and cross-section checks.
- **Structural rewrite:** explicitly reopen W1-W3. ARS plan or outline may
  control the rewrite; full re-emission is an acknowledged escalation, never a
  silent fallback. Re-run whole-draft consistency and all affected hard gates.

Every reviewer promise must correspond to an actual manuscript change,
evidence action, or reasoned disagreement. After revision, use ARS re-review
when the original finding set was multi-role or when claim-strength drift is a
material risk.

## W7: finish the exact package

After scientific and structural gates pass:

1. apply bounded language polish;
2. compile and inspect the exact LaTeX/PDF artifact;
3. refresh venue facts from current official sources;
4. run the journal-specific submission audit;
5. record only the final consolidated review or decision artifact needed by a
   future session.

## Cost and stop rules

- Do not run the ARS full academic pipeline by default inside a governed
  repository. Its Material Passport, progress state, and claim records must map
  to existing project state if the user explicitly chooses that pipeline.
- Do not keep separate Supervisor Evidence Maps, ARS Claim Registries, reviewer
  reports, and project claim ledgers as coequal permanent records.
- Do not polish unsupported science.
- Do not use a fresh Deep Research report as experimental evidence.
- Stop when the immediate deliverable passes its owning gate; do not
  automatically continue to the next expensive stage.
