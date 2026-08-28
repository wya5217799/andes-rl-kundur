criteria_binding_unavailable
calibration_status: NOT_CALIBRATED
contract_role: domain
## Dimension Scores

### D1: methodology_rigor
score: not_assessed

### D2: domain_accuracy
score: warn
trigger: "incomplete positioning"

### D3: argumentative_coherence
score: not_assessed

### D4: cross_disciplinary_relevance
score: not_assessed

### D5: writing_and_structure
score: not_assessed

### D6: venue_fit_and_contribution
score: not_assessed

## Review Body

The physical object, terminology boundaries, and headline result statements are largely accurate against the supplied parameter card and sealed R478--R484 evidence. In particular, the paper distinguishes device- and system-base quantities, arithmetic common/differential coordinates from identified modes, finite-window response energies from Lyapunov or stored-energy objects, deterministic-fresh evidence from learned-canary evidence, and tested-bank failure from a universal MARL claim. The remaining D2 concern is limited to how the nearest prior work is positioned, plus one minor control-theory terminology issue.

### S1: The corrected physical and action object is explicit and internally consistent
The manuscript states the per-unit frequency convention, the project-specific M/D base conversion, the M=2H convention, the amplitude-and-slew projection, and the asymmetric decoder in a traceable sequence. It also correctly states that learned actions modulate parameters rather than directly injecting active power.
**Evidence Anchor**: equation: Eqs. (1)--(4) — swing convention, exactly-once base conversion, normalized-action projection, and device-base M/D decoder

### S2: The decoupling quantities are interpreted within their mathematical limits
The three rows of the registered differential transform span arithmetic directions orthogonal to the fleet-common vector, and the manuscript explicitly avoids calling them identified modes. It likewise describes the two endpoints as discrete response energies rather than joules, storage functions, or Lyapunov functions.
**Evidence Anchor**: equation: Eqs. (5)--(7) — registered common/differential coordinates and signed finite-window endpoint definitions

### S3: The empirical claim boundary is unusually disciplined
The learned-policy result is reported as a finite-bank separation between aggregate endpoint qualification and the complete per-profile guard, while the deterministic fresh result, learned canary result, and two horizons remain non-pooled. The paper also disclaims stability, safety, hardware, topology, cross-H, and universal-algorithm conclusions.
**Evidence Anchor**: figure: Fig. 3(a)--(b) — 126 of 208 endpoint-qualified policies, zero complete-contract passes, and exact learned block-level guard counts

### S4: The source-intervention interpretation avoids a semantic-information overclaim
The paper accurately identifies N versus P as a same-time total source intervention that can combine authenticity, optimization, contemporaneous dependence, and distribution shift. It does not relabel the source-factor estimates as pure neighbour-information effects or interpret non-rejection as equivalence.
**Evidence Anchor**: table: Table II — separate 6 s and 30 s source estimates with Holm-adjusted decisions

### W1: Nearest-work positioning remains too coarse
**Problem**: The Introduction enumerates relevant adaptive-VSG and MARL studies, and the Discussion says their plants, learners, rewards, and validation objectives differ, but the manuscript never states the decisive similarities and differences paper by paper. This leaves the relationship between the inherited M/D-adaptive learner family, Yang et al. (2023), and the present evaluation contribution less auditable than the physical contract itself.
**Evidence Anchor**: absence: Sections I, III-B, and V — expected an explicit nearest-work comparison separating inherited controller elements from this paper's evaluation contribution; checked Introduction paragraphs 1--3, the learner description, Discussion paragraph 2, and the bibliography
**Why it matters**: The paper's novelty is deliberately an evaluation design rather than a new learning algorithm, so accurate incremental-contribution positioning depends on showing exactly what is inherited, changed, and newly tested.
**Suggestion**: Add one compact paragraph or table using the already cited Yang (2023), Lu (2024), Zhang (2024), and Kang (2025) papers. For each, verify from the original source the plant, adaptive variables, agent/critic structure, information access, validation endpoint, and claim scope; then state which elements the present study inherits and which evaluation safeguards are new.
**Severity**: Minor
**Confidence**: 4 — core expertise in VSG coordination; original external articles were not independently re-opened in this seat
**Norm status**: [FIELD-NORM UNVERIFIED]

### W2: “Open-loop” is imprecise for the zero-action sensitivity bank
**Problem**: Setting the adaptive M/D action to zero does not open the internal VSG, governor, network, or plant feedback loops. The later phrase “zero-action screen” is physically clearer than “open-loop sensitivity bank.”
**Evidence Anchor**: text: Section I, paragraph 4 "A separate open-loop sensitivity bank also showed that a \SI{6}{s} window can miss the tail at high inertia."
**Why it matters**: The present wording can be read as a loop-breaking experiment, whereas the evidence is a baseline closed-system response with zero adaptive action.
**Suggestion**: Replace “open-loop sensitivity bank” with “zero-adaptive-action sensitivity bank” or “uncontrolled-parameter-modulation sensitivity bank,” and use that term consistently.
**Severity**: Minor
**Confidence**: 5 — core expertise in power-system dynamic-control terminology

No additional missing reference is asserted. The bibliography already contains foundational VSG sources, the closest named adaptive-VSG/MARL sources, SAC, safe power-system RL, and the statistical reference needed for the manuscript's bounded interpretation; W1 asks for stronger integration and verified comparison of those existing sources, not citation-count expansion.
