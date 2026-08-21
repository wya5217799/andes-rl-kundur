---
version: 1
status: active
programme_id: tpwrs-vsg-graph-residual
current_phase: P0_converter_vsg_object_authority
north_star: >-
  Preserve R384, R388, and R389's bounded negatives, R385 and R387's invalid
  records, and R386's clean-object pass. The tested REGCV1 and stock-REGF2
  formulations remain stopped. R390 is analysis-invalid by CLM-1095; R391
  closes Q-0108 positive through CLM-1100 and confirms local positive-real
  directions in the exact stock-REGF2 model. No authority, controller,
  learning, causal-loop, or physical-device experiment is authorized.
priority_questions: []
phase_order:
  - P0_converter_vsg_object_authority
  - P1_deterministic_pq_decoupling
  - P2_learning_necessity
  - P3_conditional_residual_marl
  - P4_robustness_fidelity_manuscript
---

# Converter-level VSG P/Q-decoupling research programme

## Current authority

`paper/converter_vsg_pq_decoupling/LINE.md` owns the new experiment route.
`paper/paralleled_vsg_marl/LINE.md` remains active only for bounded manuscript
closure and cannot authorize more simulation or training on the R382
formulation. ADR-0016, ADR-0017, CLM-1070, the route contract, and the
validated successor-route census define the object, successor construction,
invalidity correction, reuse boundary, phase gates, and stopping rule.

R384 closed Q-0104 negative through CLM-1065. The status-disabled `REGCV1`
formulation reached exact object ownership and isolated zero-reference
software writes but failed the native TDS initialization validity test. No
authority, deterministic decoupling, learning-necessity, or training evidence
was opened. R385's immutable classifier later returned a reference-mismatch
STOP, but CLM-1070 found that the runner captured source `p/q` after TDS
replacement rather than at the registered post-power-flow/pre-init point.
R385 is analysis-invalid. R386 corrected only the capture timing and closed
Q-0105 positive through CLM-1075: the structurally clean four-REGCV1 object
passes source, initialization, diagnostics, finite-value, and zero-input drift
guards. R387's signed dynamic authority record is analysis-invalid through
CLM-1080 because trajectory identity/timing and partial-termination taxonomy
were not valid. R388 corrected only those integrity defects and closed Q-0106
negative through CLM-1085: the exact REGCV1/card/port formulation fails the
signed authority gate. No controller or training authority exists, and no
alternative model route was automatically open. The subsequent source audit
and five-family census selected stock REGF2 for one fresh object/initialization
gate. R389 closes Q-0107 negative through CLM-1090: the exact stock four-REGF2
object passes construction and native initialization but fails its registered
no-exogenous-action stationarity gate. Stock REGF2 stops before authority,
controller, or learning work. R390 attempted Q-0108 but is analysis-invalid by
CLM-1095 because of a sparse-matrix adapter defect and a configured-index/
display-name mismatch. R391 corrects only those evidence seams and closes
Q-0108 positive through CLM-1100: two no-time-advance arms reproduce the exact
model's material positive-real directions. The result stops this formulation
before authority or control and opens no causal-loop or physical-device claim.

Historical programme narratives and closed questions remain in
`memory/RESEARCH_PROGRAM_CLOSED.md`, their manuscript lines, claims, and feeds.
They are not evidence or launch authority for the converter-level object.

## Evidence-line disposition

- `paper/paralleled_vsg_marl/` is experiment-side stopped. Its F5 object and
  energy-port methods may inform design, but R382 values and conclusions do not
  transfer.
- `paper/decoupling_marl_model_first/` remains reusable F4 methodology only.
- `paper/icems2026/` and `paper/sci_upgrade_survey/` remain frozen evidence
  lines for their executed objects.

Source code, contracts, probes, and evaluation infrastructure may be adapted
prospectively. No result, checkpoint, claim, threshold, or manuscript wording
moves into the new line.

## Phase gates

### P0 — Converter object, initialization, and authority

- Preserve the Kundur network connectivity and instantiate four stock `REGF2`
  VSM units at the registered controlled locations after the REGCV1 stop.
- First verify exact object identity, structural absence, native
  initialization, zero-input TDS completion, complete diagnostics, and finite
  electrical state. Post-init P/Q action identity and authority require a
  later question.
- Use no controller and no training in this gate.

R384 supplied the valid failure branch for the status-disabled formulation.
R385 is analysis-invalid and cannot be retried. R386 validly passes the clean
construction with the corrected snapshot. R387 attempted Q-0106 but is
analysis-invalid. R388's integrity-only correction validly stops the exact
REGCV1/card/port formulation at signed authority. Another converter model,
card, or physical power port requires a new route decision and repeats P0
qualification. R389 validly stops the installed-default stock-REGF2 object at
the no-exogenous-action stationarity gate, before its Paux/Qaux seam is tested.
R391 validly finds reproducible positive-real directions in the exact object's
ANDES reduced state matrix before time advances. This is a bounded local-model
STOP, not a physical-stability or causal-loop claim. No P1 work is authorized.

### P1 — Deterministic P/Q decoupling

- Freeze self-channel response and P-to-Q/Q-to-P cross-response endpoints.
- Compare one physics-based decoupler against matched zero-action and strong
  conventional baselines under identical information, action, timing, and
  electrical limits.
- Guard solver convergence, voltage, current, active/reactive power, frequency,
  saturation, slew, and control stress.

Exit only with a valid deterministic gain and no-harm result.

### P2 — Learning necessity

- Test one bounded non-learning residual/headroom family after the deterministic
  controller.
- Audit whether permitted local/neighbour information can identify the useful
  residual action.
- Stop without training when joint headroom or information value fails.

### P3 — Conditional residual MARL

- Enter only after P2 passes.
- Freeze one matched residual MARL comparison; do not sweep algorithms.
- Keep one physical converter VSG per runtime actor with independently
  executable P/Q residual actions and audited information permissions.
- Require improvement over the strongest matched non-learning method without
  electrical, frequency, convergence, or control-stress harm.

### P4 — Robustness, fidelity, and manuscript

- Seal operating-point, R/X, rating, delay, heterogeneity, disturbance, and
  communication holdouts before selection.
- Treat topology/VSG-count generalization, EMT, HIL, and deployment as separate
  later evidence tiers.
- Draft only from claims and feeds registered to the new line.

## Launch policy

1. One falsifiable question per round; probe before training.
2. R383 authorized governance only; R384 is the bounded negative opening
   evidence and authorizes no retry.
3. Q-0106 and Q-0107 are closed negative; Q-0108 is closed positive by R391,
   but its positive-real local-model result stops the exact stock-REGF2 route.
   No controller, learning, or successor experiment is authorized.
4. Small development canaries use minimal concurrency; a large formal bank
   uses measured high parallelism with one native thread per WSL process.
5. A negative gate rejects its registered formulation, not every converter
   model or MARL as a class.
