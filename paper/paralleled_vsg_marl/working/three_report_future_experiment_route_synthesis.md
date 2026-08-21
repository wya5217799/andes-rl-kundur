# Future Experiment Route Synthesized from Three Deep Research Reports

## Status and authority

- **Date:** 2026-08-14
- **Purpose:** extract the distinct, decision-relevant content of three external Deep Research reports and convert it into a bounded future-experiment route.
- **Authority:** non-authoritative research synthesis. It does not register evidence, support a manuscript claim, change the active route, or authorize simulation or training.
- **Current-line boundary:** the `paralleled-vsg-marl` experiment route remains stopped at R382 because the tested finite controller family did not establish joint probe-cross improvement headroom. The present manuscript therefore remains in manuscript-only repair/closure mode.
- **Future-work boundary:** any execution derived from this document requires a separately authorized research line, a prospectively frozen objective, and the repository's normal evidence-round gates.

## Source passport

The three source files are preserved here by content hash rather than copied verbatim. Their overlapping prose, temporary search markers, and unverified bibliographic details are intentionally excluded.

| Source snapshot | SHA-256 | Distinct contribution retained |
|---|---|---|
| `C:\Users\27443\Downloads\deep-research-report (1).md` | `FFE986A3CF3D7D6742873E0EEFDA53AB74FA8EE6B34F1DC7382F1E92DAB0A411` | Multi-timescale architecture; explicit cross-coupling metrics; staged two-, four-, and many-VSG experiments; averaged-model to EMT/HIL progression. |
| `C:\Users\27443\Downloads\deep-research-report (2).md` | `BCD83A207BF2FAD0155937E99F35E6E70D39181FF8025C0C34CFE108B7C5CF42` | Strong model-based comparison set; separation of multi-agent consensus from MARL; residual, graph, and shielded learning alternatives; safety/stability priority. |
| `C:\Users\27443\Downloads\deep-research-report (3).md` | `073FFB84C2353D3B84946DD9A4581395D39F533D90F44DAF51AE0CED4D72A972` | Benchmark tiers; graph-local CTDE; topology and agent-count generalization; out-of-distribution physics randomization; explicit safety stack and ablation structure. |

The reports contain opaque retrieval markers and literature summaries that have not been independently verified against primary sources. No citation from them is manuscript-ready until its title, authorship, venue, year, DOI, and claimed result are checked independently.

## Consolidated scientific conclusions

1. **The control problem contains at least three different couplings.** These are the local active/reactive-power channel coupling, the differential dynamics among parallel VSG units, and the network/information coupling that determines whether coordination can be decentralized. A single reward value or frequency-nadir metric cannot diagnose all three.

2. **Physical authority and deterministic structure must precede learning.** A credible plant must expose controllable per-VSG power/voltage channels and their limits. A credible baseline must already use known structures such as virtual or complex impedance, feedforward decoupling, mutual damping, consensus/diffusion, or constrained predictive control where applicable.

3. **MARL is defensible only as a bounded residual or slow supervisory layer.** It should adapt references, gains, damping, impedance, or coordination weights at a slower timescale. It should not replace inner current/voltage loops or directly generate converter switching commands.

4. **Learning needs matched-permission evidence.** Every learned controller must be compared with deterministic controllers that receive the same observations, communication graph, action channels, update rate, saturation limits, and safety projection. Otherwise an apparent learning gain may only be an information or actuator-permission advantage.

5. **Safety is a constraint interface, not merely a reward term.** The reports converge on bounded actions, rate limits, state/action projection, current/energy/voltage constraints, deterministic fallback, and explicit infeasibility handling. Penalty-only safety is inadequate for paper-facing execution.

6. **Scalability and HIL are downstream questions.** Topology transfer, agent-count transfer, communication loss, EMT, and HIL are valuable only after a small converter-level system establishes physical authority and non-learning joint improvement headroom.

## What each report adds beyond the common core

| Report | Useful addition | How it changes the experiment plan |
|---|---|---|
| Report 1 | Orthogonal active/reactive-power probes and explicit cross-channel metrics, plus a staged system-size and fidelity ladder. | Makes decoupling a measured property rather than a coordinate label; starts with a two-VSG diagnostic cell before scaling. |
| Report 2 | Strong recent families of deterministic coordination, including centre-of-inertia/consensus, diffusion-like coordination, constrained predictive control, and energy/stability-oriented formulations. | Raises the baseline bar and prevents MARL from being credited for a capability already supplied by model-based coordination. |
| Report 3 | Graph-local policy design, parameter sharing, out-of-distribution physics randomization, and a layered safety shield. | Converts scalability from a larger training run into a test of locality, transfer, and constraint preservation. |

## One falsifiable objective for a future research line

> On a converter-level model of paralleled VSGs with explicit voltage/current control, active/reactive-power ports, virtual/output impedance, DC-side energy or power limits, and current limits, determine whether a bounded per-VSG residual action family retains **joint improvement headroom** beyond the strongest matched-permission deterministic controller on both (i) bidirectional active/reactive-power cross-coupling and (ii) inter-VSG differential dynamics, without degrading power sharing, voltage/frequency regulation, current/energy feasibility, control stress, or safety.

This objective is deliberately upstream of algorithm choice. Failure to establish joint headroom ends the learning route; it is not a reason to try a larger learner.

## Recommended evidence gates

| Gate | Question | Minimum output | Stop condition |
|---|---|---|---|
| **F0 — Plant validity** | Does each VSG have a physically meaningful and independently addressable control port? | Converter-level model contract, units, limits, timescales, and actuator identity tests. | Stop if the action is repaired away, maps to the wrong device, lacks authority, or omits constraints essential to the claimed phenomenon. |
| **F1 — Deterministic baseline** | What can the strongest model-based controller achieve with the allowed information and actuator set? | Tuned fixed/enhanced VSG plus at least one explicit decoupling/coordination baseline under identical permissions. | Stop algorithm work if the baseline is not stable, not constraint-compliant, or not permission-matched. |
| **F2 — Orthogonal benchmark** | Are the two cross channels and the differential modes observable and measurable? | Prospectively frozen active-power and reactive-power probe bank with cross-channel, sharing, oscillation, and constraint metrics. | Stop if the benchmark cannot distinguish coupling mechanisms or if measurement noise/aggregation hides per-unit dynamics. |
| **F3 — Non-learning joint headroom** | Does any bounded, admissible residual action improve both required coupling dimensions beyond F1? | Identity, deterministic residual, and finite action-family comparison under the same shield. | Stop the learning route if improvement is one-sided, comes from extra permissions, or violates any no-harm endpoint. |
| **F4 — Information value** | Is deployable local or neighbourhood information sufficient to select the useful residual action? | Full-state oracle comparator, local-only controller, and progressively enlarged neighbourhood controllers. | Stop MARL if a matched deterministic local/neighbour controller closes the residual gap, or if only undeployable global information works. |
| **F5 — Learning value** | Does learning outperform all matched non-learning alternatives reproducibly? | Seed-aware, uncertainty-aware comparison and reward/communication/shield ablations. | Stop on non-reproducible gains, constraint violations, baseline under-tuning, or sensitivity that dominates the reported benefit. |
| **F6 — Generalization and fidelity** | Does the mechanism persist outside the training distribution and at higher fidelity? | Parameter, operating-point, grid-strength, topology, delay/loss, agent-count, EMT, and eventually HIL evaluations. | Bound the claim to the last passed fidelity/generalization tier; do not infer hardware readiness from simulation. |

## Minimum viable experiment design

### Plant and staging

- Start with a **two-VSG converter-level diagnostic cell**, then move to four units only after F0–F3 pass.
- Represent voltage and current loops, active/reactive-power control, virtual or output impedance, network impedance, current saturation, and a DC-side energy or power constraint appropriate to the action port.
- Keep the present positive-sequence active-power proxy separate from this future object. It cannot by itself support claims about converter-level active/reactive decoupling, current-limited behavior, or hardware safety.

### Co-primary endpoints

- Active-power command/disturbance to reactive-power response.
- Reactive-power or voltage command/disturbance to active-power response.
- Inter-VSG differential oscillation energy, damping, or settling.

These must be paired with no-harm endpoints: active/reactive sharing, circulating current, voltage/frequency excursion, current and energy limits, saturation/recovery, action rate, control variation, and failed-run rate. Aggregate reward is diagnostic only, not a primary physical endpoint.

### Matched deterministic comparison set

At minimum, compare:

1. fixed or enhanced VSG control;
2. virtual/complex impedance or feedforward decoupling;
3. mutual-damping, consensus, or diffusion-style coordination;
4. a constrained predictive or energy/stability-oriented coordinator when computationally feasible;
5. identity residual and bounded deterministic residual families.

All arms must share the same observation support, communication edges, control period, action bounds, rate limits, and safety projection.

### Probe bank and out-of-distribution scope

- Freeze orthogonal active- and reactive-channel steps or pulses before controller selection.
- Vary operating point, VSG ratings, filter/output impedance, line resistance-to-reactance ratio, grid strength, and load composition.
- Add topology switches, communication delay/loss, larger agent counts, and unseen graph families only after the small-system mechanism passes.

## Learning experiment, only if F0–F4 pass

The minimum comparison should contain the strongest deterministic controller, identity residual, bounded random residual, independent learning, a centralized information-rich comparator, local no-message MARL, graph/message-enabled MARL, decoupling-objective ablation, and shield ablation where ethically and physically safe. Parameter sharing and graph-local observations are preferred for agent-count transfer.

The reports mention several possible MARL algorithms, but no algorithm or hyperparameter grid should be frozen before the physical and information gates. Algorithm search cannot repair missing actuator authority, absent headroom, or an invalid benchmark.

## Priority order

1. **Highest priority:** specify and qualify a converter-level two-VSG plant, then test F0–F3. This is the shortest experiment that can falsify the proposed learning route.
2. **Second priority:** define the safety projection and deterministic fallback as part of the action interface, then evaluate information value at F4.
3. **Third priority:** train a residual learner only if the first two priorities leave a reproducible residual gap.
4. **Later work:** graph/topology scaling, EMT, real-time execution, and HIL.

The following are not recommended next steps: reopening the stopped current power-port route, sweeping virtual inertia/damping as a substitute for plant validity, resuming algorithm-only searches on fixed Kundur topology, direct PWM/current-loop MARL, or importing unverified numerical settings from the three reports.

## Decision for this project

- Retain this document as the single project-local extraction of the three external reports.
- Keep the current `paralleled-vsg-marl` line in manuscript-only closure/repair; this synthesis does not reopen it.
- If the future objective is selected, create a separate research line and begin with the plant/object specification and F0 thresholds, not with training.
- Treat every bibliographic or platform-specific statement in the source reports as verification debt until checked against primary sources.

## Internal boundary references

- `paper/paralleled_vsg_marl/ROUTE.md`
- `paper/paralleled_vsg_marl/reports/R382.md`
- `paper/paralleled_vsg_marl/working/Decoupling-Oriented_Coordination_of_Paralleled_VSGs_with_MARL_deep-research.md`
- `paper/paralleled_vsg_marl/working/when-learning-is-unnecessary-learning-readiness-deep-research.md`

