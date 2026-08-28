# Academic Research Suite review and revision response — 2026-08-28

## Manuscript information

- **Title:** *Decoupling-Oriented Coordination of Paralleled  VSGs With Multi-Agent Reinforcement Learning*
- **Target:** ICEMS 2026, IEEE A4 conference format.
- **Review mode:** `reviewer_full`, contract `reviewer/reviewer_full/v2`.
- **Criteria status:** `criteria_binding_unavailable`; all scores and the decision are `NOT_CALIBRATED` and are not a formal ICEMS acceptance prediction.
- **Initial reviewed TeX:** `A19922C9B3E330FEC5ABE682A9737A108B5ABA2782563898C7453589B2EE9277`.
- **Revised TeX:** `33FE35DFEA68ACD12C729388FBA5A8F2A02E3A641875C43E31C66415D01834BD`.
- **Revised PDF:** `609C2D607DEEE395EBBCA54DB5B7EDCA82BE87B70A4128774F24DB0EB99B66D1`.
- **Execution boundary:** no ANDES run, training, evaluation, tuning, or new claim-bearing statistical analysis was performed in this writing/review task.

## Panel provenance and initial decision

Five paper-blind Phase-1 cards were produced before five paper-visible Phase-2 cards. Each Phase-2 seat remained blind to peer output. All ten cards passed the suite's phase-conformance checker. The panel synthesis and provenance validators also passed.

- Runtime contract SHA-256: `F5E59E127ABB1E5ED24C7DAB067F3422D5E083656FBFDF30317BBA7EDFE79AED`.
- Panel provenance SHA-256: `B5EC3452AD349FE5421F6EAF05395F72AB5A4BBDBAB768317CBA74DC1332D0BC`.
- Editorial synthesis SHA-256: `512128A65E38F4FCDBB96C9E97F7B5E7B7A35199BDEACF483D62DDB86F848006`.
- Initial mechanical decision: **`major_revision`**, selected by failure condition F2 because mandatory D6 was `block (repairable)`.

The five seats used separate invocation contexts and roles, but all used the OpenAI provider and GPT-5 model family. Role separation is not statistical or institutional independence, and same-family correlated-error risk remains.

## Summary of manuscript changes

The revision:

1. replaced the imprecise `open-loop` label with `zero-adaptive-action`;
2. added a closest-work paragraph that identifies the inherited adaptive-$M/D$/MARL elements and frames the novelty as an evaluation design;
3. states that the 103%/110% limits were prospectively registered, imported without retuning, and are empirical comparator-relative tolerances rather than safety or hardware limits;
4. explicitly limits the `0/208` result to those exact thresholds because action-ratio margins and neighbouring-threshold sensitivity are not in the sealed audit;
5. defines $\Delta_{\rm geo}$ and distinguishes its descriptive mean-log scale from the signed-rank inferential target;
6. adds an internal provenance and availability statement, including the missing public identifier and environment-lock limitations; and
7. connects communication-imperfection, EMT, and HIL work to the observations, mapping, and guards each future stage would challenge.

The paper remains six pages. No new data, simulation, checkpoint, or inferential result was added.

## Source finding trace

Every emitted weakness is mapped below; no reviewer comment is omitted.

| Source finding | Consolidated item | Revision status |
|---|---|---|
| EIC W1 — title obscures the evaluation identity | S1 | declined by owner constraint |
| EIC W2 — undefined $\Delta_{\rm geo}$ | S2 | closed |
| EIC W3 — closest-work comparison missing | R1 | partially closed |
| EIC W4 — decisive thresholds lack significance argument | R2 | partially closed |
| Methodology W1 — estimand and inference not aligned | R3 | partially closed |
| Methodology W2 — threshold rationale and margins missing | R2 | partially closed |
| Methodology W3 — paper-facing replay provenance missing | R4 | partially closed |
| Domain W1 — nearest-work positioning too coarse | R1 | partially closed |
| Domain W2 — `open-loop` is physically imprecise | S3 | closed |
| Perspective W1 — action-limit meaning and sensitivity missing | R2 | partially closed |
| Perspective W2 — deployment exclusions lack an evidence ladder | S4 | closed |
| DA M1 — threshold/comparator dependence is the strongest counterargument | R2 | unresolved evidence component |

## Response to required revisions

### R1 — substantiate the evaluation-design contribution

> Compare the nearest VSG/MARL and safe-control work, separating inherited controller elements from the claimed evaluation safeguards.

**Author response:** We agree with the positioning problem. The revision now names the nearest distributed inertia--droop MARL, single-VSG SAC, MADDPG, decentralized multi-VSG MARL, and constraint-aware power-system RL precedents. It states that the broad adaptive-$M/D$ and learning objects are inherited and that the bounded contribution is the post-correction, frozen-family, bank-separated, horizon-separated, guard-first audit.

**Changes made:** revised p. 1, Introduction; reinforced on revised p. 5, Discussion.

**Status:** `partially_closed`. The paragraph is a source-based direct comparison, but it is not a full dimension-by-dimension table covering every plant, observation, critic, comparator, bank, horizon, and guard. The closure review therefore retains publication-positioning risk rather than claiming a complete originality census.

### R2 — establish the meaning and robustness of empirical guard limits

> Explain the 103%/110% limits, report action-stress margins, test threshold sensitivity, and address comparator dependence.

**Author response:** We agree with the core criticism. The revision identifies prospective registration and hash import, explains the decision purpose of the 3% frequency and 10% command-stress allowances, and says explicitly that they are not industry-, hardware-, stability-, or safety-calibrated. It also narrows the headline conclusion to the exact registered thresholds.

**Changes made:** revised p. 2, Section II-C; revised p. 5, Discussion and Limitations.

**Status:** `partially_closed`. The R484 sealed analysis stores the two action-guard decisions as Booleans but not the action-RMS/total-variation ratios, margins, quantiles, neighbouring-threshold roster, or alternative-comparator sensitivity. Those quantities cannot be reconstructed as manuscript prose. Closing this item requires a new, explicitly labelled claim-bearing secondary analysis of the existing 5,088 trajectories and a new seal. It does not require retraining or new simulation trajectories, but it was outside the authority of this writing/audit task.

### R3 — align source-effect estimates and inference

> Name one estimand and pair it with compatible estimation, testing, and interval reporting.

**Author response:** We agree. The revision defines $\Delta_{\rm geo}=100\{\exp(\langle d_s\rangle_s)-1\}\%$ as a descriptive mean-log transformation and states that the exact Wilcoxon signed-rank route targets a rank-based seed-level location shift instead. It no longer implies that the adjusted $p$ value is an interval for $\Delta_{\rm geo}$.

**Changes made:** revised p. 4, Section III-B and Table II; limitation repeated on revised p. 5.

**Status:** `partially_closed`. The distinction is now correct, but the sealed analysis contains no estimate/interval compatible with the signed-rank target. A test inversion or another predeclared aligned inferential route would be new claim-bearing analysis. The present paper can defend only the registered raw/Holm decision and descriptive mean-log summary, not a precision claim.

### R4 — supply paper-facing replay provenance

> Provide a versioned archive/access pointer, software environment, case and parameter artifacts, checkpoints, manifests, and regeneration entry points.

**Author response:** We agree and added everything that can be supported without inventing a public deposit. The paper now records that the internal archive binds reviewed commits and SHA-256 identities, 208 checkpoints, parameter/profile cards, 16 shards and 5,088 trajectories, regeneration scripts, Python 3.12.3, and ANDES 2.0.0. It states that no public identifier, complete dependency lock, or container is available.

**Changes made:** revised p. 5, Discussion and Limitations. The internal evidence map now says `internally traceable`, not `reproducible`.

**Status:** `partially_closed`. Internal traceability is documented; unrestricted independent replay remains unavailable. A public or access-controlled archival deposit plus an environment lock is still required before claiming external reproducibility.

## Response to suggested revisions

| Item | Status | Response and location |
|---|---|---|
| S1 — revise title/subtitle | `declined_by_owner_constraint` | The owner fixed the exact title. The evaluation identity is instead made explicit on p. 1. The residual title-framing risk is accepted, not hidden. |
| S2 — define $\Delta_{\rm geo}$ | `closed` | Algebraic definition and direction added on p. 4. |
| S3 — replace `open-loop` | `closed` | Replaced with `zero-adaptive-action` on p. 1 and in the evidence map. |
| S4 — add deployment evidence ladder | `closed` | Delay/loss/quantization, EMT, and HIL are connected to the relevant observations, dynamics/mapping, and implementation effects on p. 5. |

## Page-by-page change log

| First-family freeze | Revised freeze | Change |
|---|---|---|
| p. 1 | p. 1 | closest-work positioning and corrected zero-adaptive-action terminology |
| p. 2 | p. 2 | threshold provenance, purpose, calibration boundary, and exact-cutoff limitation |
| p. 4 | p. 4 | $\Delta_{\rm geo}$ definition and estimand/inference distinction |
| p. 5 | p. 5 | closest-work boundary, deployment evidence ladder, archive/access limitations, and missing compatible interval |
| p. 6 | p. 6 | references pruned to the works cited by the revised manuscript |

## Closure review

The revised freeze received three additional read-only checks:

- **Scientific/evidence correctness:** no CRITICAL finding, no arithmetic mismatch, no bank pooling, and no pre-R478 directional evidence reuse. Four MAJOR publication-evidence gaps remain: R1 positioning depth, R2 threshold/comparator robustness, R3 compatible interval, and R4 external replay access.
- **ARS obligation closure:** R1--R4 remain `partially_closed`; S2--S4 are closed; S1 is declined under the fixed-title constraint. The contract-relative decision remains **`major_revision (repairable)`**.
- **PDF/layout:** PASS after the post-audit float-order correction documented below. Six A4 IEEE pages; 0 LaTeX errors, 0 overfull boxes, 0 undefined citations/references, all fonts embedded/subsetted, no Type 3 fonts, and no visible clipping, overlap, or blank anomaly. Seven underfull boxes remain non-blocking.

This closure is not a second institutionally independent panel. The original five-seat panel shared one model family/provider, and the closure reviewers are additional role-separated model checks.

## Post-audit float-order correction

The original format closure omitted a semantic float-order gate. It checked page count, fonts, clipping, overlap, legibility, and LaTeX diagnostics, but did not require every claim-bearing result figure to appear before the Conclusion. Consequently, the two-column `figure*` for the learned-policy result floated to page 6 after the Conclusion even though its source declaration was in Results. A user annotation exposed this audit omission.

The result figures and their first callouts were reordered while preserving figure-number order. Results and the first Fig. 2/Fig. 3 callouts now appear on page 4, followed by Fig. 2 on page 4 and Fig. 3 on page 5; Discussion starts on page 5, while Conclusion and References are on page 6. Thus each figure is cited before it appears and every body figure precedes the Conclusion. The six-file source package was rebuilt and clean-compiled from extraction after this correction. No scientific claim, number, data object, or experiment changed.

## Final experiment and evidence decision

The bug-corrected R478--R484 record is sufficient for the manuscript's exact bounded thesis:

> on the fixed comparator, exact prospectively registered 103%/110% contract, four-profile canary bank, and tested 208-policy family, endpoint qualification and complete-contract qualification differ.

No additional training or simulation experiment is required to state that conclusion. Compared with the earlier bug-tainted positive manuscript, the rewritten argument is narrower but materially more defensible because it excludes the invalid positive evidence and separates fresh/canary, deterministic/learned, and 6 s/30 s evidence objects.

However, full closure of the second-suite publication-risk audit requires a new formal secondary analysis of already stored trajectories:

1. action-RMS and total-variation ratios, margins, and distributions;
2. a declared neighbouring-threshold and comparator sensitivity analysis; and
3. an estimate and confidence interval aligned to the selected source-effect inferential target.

Those are new evidence analyses, not new experiments, and must be prospectively scoped and sealed rather than added informally during manuscript editing.

## Closing statement

The manuscript rewrite and both requested review families are complete. The deliverable is scientifically usable as a transparent finite-contract paper, but it should not be represented as having cleared the richer suite's publication gate. The remaining `major_revision` decision is driven by missing robustness and replay evidence, not by an undisclosed numerical error or an invalid use of the corrected experimental record.
