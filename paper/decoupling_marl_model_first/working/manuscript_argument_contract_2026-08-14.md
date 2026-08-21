# Manuscript argument contract — decoupling-marl-model-first

Created 2026-08-14 by the research supervisor (tech-paper-template W1) from
the line's terminal evidence. This is the canonical manuscript argument
contract for the paper. It holds no measurement values: every number is
reached through the bound feeds and claims listed below. It is working
control for drafting, not manuscript prose, and not evidence that any
controller works.

## 1. Paper-type positioning

- Type: New Problem/Setting paper with Technique components.
- Rationale: the contribution is the problem formulation and decision
  procedure itself — an implementation-faithful, gate-sequenced protocol
  that decides, before training, whether a learned residual has physical
  headroom on a storage-coordinated VSG plant — demonstrated end to end on
  one bounded setting, including its mechanism-level diagnosis. The
  deterministic controller is an established-technique module, not the
  contribution, which defuses "your controller is simple" objections.

## 2. Thinking template

| Stage | Content |
|---|---|
| Research background | Paralleled VSGs with energy storage need coordinated active-power control for common-mode frequency and differential synchronization; MARL is increasingly proposed, but sim-only evidence carries fidelity risk and rarely pre-checks whether a learned layer can add value. |
| Limitation 1 | Learning-for-grid studies rarely publish an executable plant contract; simulator fidelity defects (frequency base, unit-base conversions, internal limiters) can silently invalidate measured gains. |
| Limitation 2 | "A residual learned layer improves over a strong deterministic baseline" is usually assumed, not gated: no standardized headroom check quantifies the residual gap before training compute is spent. |
| Limitation 3 | When a learning route fails, the failure mechanism is rarely isolated; an action-basis design choice (e.g., zero-common edge bases) can structurally cap what any learned layer can reach. |
| Key Idea / Our Goal | Demonstrate an implementation-faithful, gate-sequenced methodology — exact plant contract, coordinate decomposition, deterministic baseline, residual-headroom gate — that establishes a bounded deterministic storage-power-control gain and diagnoses, at mechanism level, why the tested residual families add no qualifying increment on this plant. |
| Challenge 1 | The simulator's executable device laws differ from the intended model; the contract must be reconciled against source before any endpoint is trusted. |
| Challenge 2 | The plant is not hard-decoupled (measured common/differential cross gains are nonzero), so control authority needs an exact coordinate decomposition and a frozen action basis. |
| Challenge 3 | A negative learning verdict must be attributable: no-headroom vs wrong-information vs structurally-capped action basis requires a staged diagnostic design. |
| Methodology topic sentence | The proposed gate sequence makes every experiment stage a pre-registered, sealed, fail-closed gate over one unchanged plant, so each verdict is bounded and attributable. |
| Module A (Challenge 1) | Implementation-faithful plant contract: equation-to-source reconciliation, three power layers (request/command/achieved), Stage-0/1 canaries. Evidence: R306-R341 feeds. |
| Module B (Challenge 2) | Exact inertia-weighted common/differential coordinates, frozen action bases, deterministic baseline with exact physical projection and guards. Evidence: CLM-0910 (R344), CLM-0920 (R351), CLM-0925 (R352), CLM-0930/0935/0940 (R356-R358). |
| Module C (Challenge 3) | Staged diagnostic gates: outcome-seeing oracle upper bound (CLM-0915, R350), information-path families (CLM-0945-CLM-0960, R359-R362), action-basis ablation (CLM-0965, R363). |
| Contribution 1 | An implementation-faithful, gate-sequenced pre-training protocol for storage-coordinated VSGs, with its executable plant contract and canary gates (Section III-IV). |
| Contribution 2 | A bounded, sealed deterministic storage-power-control gain plus a quantified nominal residual-headroom upper bound (Section V). |
| Contribution 3 | A mechanism-level diagnosis: zero-common residual bases structurally limit common-coordinate headroom and a common channel restores it, while the tested information families add no qualifying increment (Section VI). |

## 3. Self-consistency checks

- Check 1 Limitations -> Key Idea: pass (each limitation is answered by one
  gate stage).
- Check 2 Key Idea -> Challenges: pass (challenges are the three stages'
  implementation blockers, not invented modules).
- Check 3 Challenges -> Methodology: pass (one module per challenge).
- Check 4 Methodology -> Contributions: pass (contributions cover modules
  A/B/C and their evidence sections).

## 4. Truth boundary (W0)

Headline spine (every material statement binds to one of these; other
feeds are methodology provenance, summarized without numbers):

| Claim | Role in paper | Allowed strength | Required qualification | Target section |
|---|---|---|---|---|
| CLM-0740 (R306) | canary validity | implementation-validity on one nominal zero-input canary | no authority/controller claims | III-B |
| CLM-0900 (R341) | model gate | finite fresh-bank predictor qualification | no interpolation/general-model claim | IV-A |
| CLM-0910 (R344) | deterministic gain | sealed finite paired bank, vs zero control | centralized; two locally constructed points; no stability/safety claims | V-A |
| CLM-0915 (R350) | oracle upper bound | nominal outcome-seeing oracle below 2% floor; neighbour-local proxy negative | does not bound neural methods | V-B |
| CLM-0945-CLM-0960 (R359-R362) | information families | tested affine/RBF/k-NN/quadratic families under frozen contracts add no qualifying increment | no unlearnability claim; neural residual untested | VI-A |
| CLM-0965 (R363) | mechanism diagnosis | four-channel basis feasible 16/16 vs 10/16 on exposed bank; zero-common contract is the structural limiter | information-unconstrained; no holdout; no controller/learning conclusion | VI-B |

Comparator contract (comparison-identifiability): each comparative
statement is paired and frozen on the same bank/projection; (i) R344
deterministic vs matched zero control identifies the controller effect
only; (ii) R363 vs R358 identifies the action-basis effect only; (iii)
R359-R362 identify information-family effects under the fixed basis; (iv)
R350 identifies the information-pattern gap (oracle vs neighbour-local).
No statement may attribute a difference to architecture or learning
classes beyond these contrasts.

Comparison-identifiability gate result (run 2026-08-14, post-draft
verification): Decision ALLOW for all four executed comparisons at the
executed ceiling.
- C1 (R344 controller vs paired zero control): same plant, bank,
  disturbance, timing, action coordinates, limits, projection; only the
  controller differs. Allowed claim: frozen centralized controller effect
  vs zero control on the sealed bank. Stay-out: distributed execution,
  learning, stability, safety, generalization.
- C2 (R363 four-channel vs R358 three-edge): same bank, projection,
  endpoints, solver; only the action basis differs (action-space
  difference). Allowed claim: basis effect on physical feasibility of the
  joint 2% target, information-unconstrained. Stay-out: causal channel
  selection, controller conclusions.
- C3 (R359-R362 families/information variants): same bank, basis,
  projection, limits; family or information pattern is the single
  differing factor per contrast. Allowed claim: the tested families under
  the tested patterns add no qualifying increment. Stay-out: neural
  methods, untested nonlinear families, general information
  insufficiency.
- C4 (R350 oracle vs neighbour-local): same traces, basis, projection;
  information pattern differs. Allowed claim: information-pattern gap
  between an outcome-seeing upper bound and an endpoint-local linear
  proxy. Stay-out: nonlinear estimators, richer patterns.
Negative-result rule applied: every failure is phrased as bounded
non-demonstration for the executed formulation, never as class-level
"learning has no value".

## 5. Wording ceiling (hard)

- Forbidden: "proves residual learning is useless/unlearnable"; "MARL
  cannot work"; "decoupling achieved" (cross gains are nonzero and
  retained); topology-generalization, stability, safety, hardware, or
  deployment language; holdout claims for the headroom results; "trained
  agents" language (none was trained).
- Required qualifiers: finite bank / exposed development bank; one
  modified Kundur topology; two operating points; offline feasibility;
  LOCAL-ONLY archive; centralized controller; phasor-domain only.
- The mechanism finding (CLM-0965) is the positive spine; the negative
  family results are reported as gate outcomes of the protocol, never as
  a verdict on learning in general.

## 6. Section skeleton (W2)

| Section | Job | Inputs | Exit sentence |
|---|---|---|---|
| I Introduction | compress the chain; no promise beyond ceiling | this contract + differentiation memo | contributions list |
| II Related work | RL-for-grid, GFM/storage coordination, simulation-fidelity/benchmarking | differentiation memo (verified citations) | gap: no pre-training gate protocol with mechanism diagnosis |
| III Plant and implementation contract | exact plant, four graphs, three power layers, fidelity repairs | model_contract.md, R306-R324 | contract frozen and validated |
| IV Gate methodology | gate sequence, coordinate decomposition, canaries, seals | R306-R341, implemented_control_and_topology.md | each gate is fail-closed and pre-registered |
| V Deterministic baseline and headroom | deterministic gain + oracle upper bound + information families | CLM-0910, CLM-0915, CLM-0920-0940, CLM-0945-0960 | bounded gain; no qualifying learned increment under frozen contracts |
| VI Mechanism diagnosis | action-basis ablation, structural limiter | CLM-0965, R363 | zero-common contract is the structural limiter |
| VII Discussion and limits | what transfers conceptually, what does not | line LIMITS sections | all generalization statements refused |
| VIII Conclusion | one bounded claim per contribution | — | closes at the ceiling |

Figure plan (data sources only; rendering is a later stage): plant/graph/
action-basis diagram (annotate one caught fidelity defect, e.g. the 60/50
Hz repair); gate-sequence flowchart; R312 signed-probe cross gains (0-4%
axis, diverging scale); R344 paired endpoints with a per-scenario oracle
panel (R350 data); R363 feasibility expansion. The R359-R362 family
results live as Table II in the text (no separate figure; duplication
avoided per review 5.1). All figure data comes from the registered
results JSONs through the feeds; no re-computation.

## 7. Follow-up pointers

- Differentiation memo (deep-research, bounded) -> working file, purpose
  `differentiation`, due before drafting Section II.
- Title wording is fixed by the PI at or before Abstract time; current
  provisional wording: "An Implementation-Faithful Model-First
  Methodology for Storage-Coordinated Paralleled VSGs: Bounded
  Deterministic-Control Gain and Residual-Headroom Limits".
