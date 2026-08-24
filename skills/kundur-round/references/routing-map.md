# Decision Routing Map

Route by the decision that must be made, not by the calendar stage. The run
state limits what may change; the decision question selects the owner.

## State constraints

| Research object | Permitted effect |
|---|---|
| Idea or unplanned study | Advice and prospective design changes |
| Tunable pilot | Project-authorized changes for a future evaluation; pilot outputs remain exploratory |
| Frozen active run | Read-only research and monitoring; changes require an authorized amendment or successor |
| Terminal result | Preserve executed data and validity status; analyze under the governing contract |
| Claim or draft | Bind wording to accepted evidence and the identified estimand |
| Submission package | Change only declared package elements and re-run affected checks |

`frozen-change` is a stop signal, not a route to a more creative skill.

## Decision map

Names below are capability examples when installed. A project-local adapter may
replace them with a repository-native owner that returns the same kind of
artifact.

| Decision need | Primary capability | Add only when |
|---|---|---|
| One bounded external fact or focused evidence gap | `research` | Escalate only when a landscape is needed |
| Literature landscape, nearest-work map, or competing method families | `deep-research` | Use a systematic or Socratic ARS mode only when that machinery is itself required |
| Whether one candidate direction deserves future investment | Supervisor inline Direction review or the current project research owner | Add external research for a factual gap; add `idea-evaluator` only when a separate adversarial artifact can change the decision; evaluate successor directions rather than re-grading a completed result |
| Vague research question or method mismatch | Academic Research Suite, bounded `deep-research` Socratic or research-architecture mode | Return one RQ brief or methodology blueprint; do not start the full suite |
| Whether a comparison identifies the named factor | [Comparison-identifiability gate](comparison-identifiability-gate.md) | Run before comparator freeze and again after a material comparator or headline change |
| Prospective experiment or statistical design | Project-native study planner | Add bounded ARS `experiment-agent plan` for generic variables, confounds, sampling, or analysis support |
| Formal experiment vulnerability or pre-freeze red-team | [Experiment vulnerability bundle](review-bundles.md) | Use for high-consequence studies or an explicit loophole search; keep small pilots compact |
| Non-quick launch, resource freeze, resize, utilization, ETA, or monitoring question | [Execution-readiness module](execution-readiness.md) | Return one checked efficiency card to the authorized runner |
| Offline implementation, unit tests, or development-data prototype | Smallest directly applicable engineering capability | Escalate before physical execution, protected evidence, or claim consequence |
| Statistical interpretation or reproducibility of completed outputs | Project-native analysis owner | Add bounded ARS `experiment-agent validate` only for a distinct statistical or reproducibility report |
| Formal result validity and traceability | Project-native evidence gate | Add the project-declared domain audit after evidence bindings exist |
| Strongest permitted conclusion | Evidence and domain gates, then claim owner | Add external research or a bounded adversarial review only for unresolved context or alternative explanations |
| Evidence-demand skeleton, figure plan, or stable Methods description | Paper-writing protocol | Before results, use it as planning only; preserve frozen metrics and claim boundaries |
| Claim-bearing prose or material revision | Paper-writing protocol | Use focused writing or revision capabilities after evidence inputs exist |
| Methodology-focused manuscript review | Focused reviewer | Use Academic Research Suite `methodology-focus` when an actual Methods/Results artifact exists |
| Multi-perspective manuscript or re-review | Broad reviewer or bounded ARS `full` / `re-review` mode | Use only when independent perspectives or revision traceability can change the decision |
| Complete claim-bearing manuscript approaching submission | [Final manuscript review bundle](review-bundles.md) | Run broad complementary review by default when its entry contract is satisfied |
| Venue choice or revalidation | Venue gate | Use current official sources and dated external evidence |
| Submission-package compliance | [Submission-audit module](submission-audit.md) | Target venue, article type, and package must already exist |

## Selection rules

1. Choose one primary owner for the decision-bearing artifact.
2. Add at most one supporting audit per gate unless project governance requires
   a fixed audit set.
3. Combine checks inside one owner when they use the same input, authority, and
   return artifact. Split only when evidence source, tool, authority, or failure
   consequence differs.
4. Let project-local governance replace global defaults. Domain-specific
   auditors and execution skills are discovered from the active project and are
   never required global dependencies.
5. Preserve one project record. External reports, Material Passports, evidence
   maps, and reviewer notes are temporary adapters unless a project owner
   explicitly adopts them.
6. Treat an external router as a bounded owner of one named workflow and mode.
   It does not inherit authority to re-route the project or start later stages.
7. Passing code or automation checks returns an implementation artifact;
   passing an external review returns advice. Neither strengthens evidence.
8. Capability availability and invocation are separate. Use
   `explicit-handoff` for an explicit-only owner that the user has not invoked.
9. Named skills are examples, not requirements. If one is unavailable, select
   an owner with the same question, input, return, and authority contract, or
   give bounded Advice. Never imply that an unavailable capability ran.
10. For projectless Advice, the Supervisor may own a simple gate and return it
    inline. Require a durable artifact only when a declared downstream owner
    needs one.

## Overlap resolution

- `research` answers one bounded question; `deep-research` maps a landscape.
- `deep-research` describes external knowledge; `idea-evaluator` advises whether
  a candidate direction merits future investment.
- Project evidence and domain gates determine what the executed study proves;
  ARS experiment validation adds statistics or reproducibility checks.
- The experiment-efficiency gate decides readiness and monitoring, not study
  design or scientific validity.
- Project evidence audit traces claims to authoritative artifacts; ARS
  integrity or claim-reference checks examine a manuscript's citations and
  wording after such an artifact exists.
- Focused review handles one declared concern; a multi-role panel is reserved
  for decisions that genuinely benefit from independent perspectives.
- Venue selection chooses the destination; submission audit checks the actual
  package.
