# Manuscript argument contract — paralleled-vsg-marl line

Canonical argument contract for manuscript closure of the fixed-title line.
Authority: `paper/paralleled_vsg_marl/ROUTE.md#current-gate` (next eligible
action = finish the manuscript around the accumulated bounded negative
evidence), `LINE.md` stop rules, ADR-0015. Venue: unassessed; draft is
venue-neutral. Title is fixed as an unsupported target; no
MARL/coordination/positive-decoupling claim may be written.

## W0 — truth boundary

### Allowed claims (each binds to claim + feed)

| # | Claim (allowed wording ceiling) | Source | Allowed strength | Target section |
|---|---|---|---|---|
| A1 | A four-VSG modified-Kundur ANDES object supports four runtime actors, one per VSG unit, with independent bounded intervention. | CLM-0975/R365 | prerequisite result, one plant/condition/horizon | Method/System, Results Tab.1 |
| A2 | The same-step local/ring-neighbour observation contract reconstructs exactly; physical 60-Hz endpoints are reported after explicit 50-Hz normalization repair. | CLM-0975/R365, CLM-0980/R366 | prerequisite | Method/System |
| A3 | A per-VSG energy-constrained active-power-reference port is a valid VSG-owned actuator: units, sign, timing, zero-action equivalence, independent intervention, achieved-power energy accounting. | CLM-1000/R371, CLM-1005/R372 | bounded finite object evidence | Method/Actuator, Results Tab.1 |
| A4 | The four ports have bounded, energy-consistent, signed authority on common + three differential coordinates; nonzero cross-coordinate responses remain (transform alone is not decoupling). | CLM-1010/R373 | bounded bank, descriptive | Results Tab.1, Discussion |
| A5 | A frozen deterministic local-neighbour per-VSG M/D controller showed development-bank efficacy (69.92% differential-energy reduction vs zero action) but the non-deployable conditional oracle added only ~1.05%, below the frozen 5% headroom gate; direct M/D formulation stopped. | CLM-0990/R369 | development gate, not held-out | Results 4.1 |
| A6 | The deterministic power-reference formulation selected on immutable development data reduced registered endpoints descriptively on its held-out bank, but every selected-controller trajectory triggered the energy-port ramp-projection guard; formulation stopped STOP-UNSAFE-CONTROL. | CLM-1020/R375 | guarded stop; directional ratios are guard-failed diagnostics only | Results 4.2, Limitations |
| A7 | First-order frequency-selective damping channels cannot jointly pass the 0.4-Hz differential oscillation and reject the sustained action-domain probe within frozen 0.95/1.10 thresholds (R376-R379 family evidence; R378 held-out 0.962x differential energy, probe cross 0.79x; R379 no candidate). | CLM-1025/R376, CLM-1030/R377, CLM-1035/R378, CLM-1040/R379 | bounded negative family result | Results 4.3, Discussion |
| A8 | A separately constructed full-order source model passed source guards at two points but all 16 single-control records failed frozen trajectory fidelity (max NRMSE 1.139 vs 0.15); model-based route stopped before controller design. | CLM-1045/R380 | bounded negative stop | Results 4.4 |
| A9 | A fixed two-stage washout neighbour controller reduced development differential energy to 0.917x local but tied settling and violated both probe-cross ceilings (1.289, 1.301 vs 1.10); stopped STOP-DEVELOPMENT-NO-CANDIDATE without touching the evaluation bank. | CLM-1050/R381 | bounded negative stop | Results 4.5 |
| A10 | A bounded outcome-seeing finite residual family reduced disturbance differential energy to 0.818x local without endpoint harm, but every probe-coordinate selection fell back to the local baseline (probe-cross 1.0 vs 0.95); STOP-NO-DETECTED-JOINT-HEADROOM; disturbance-only authority, not joint decoupling headroom. | CLM-1055/R382 | bounded negative; explicitly not an impossibility result | Results 4.6, Discussion |
| A11 | Because the joint non-learning headroom prerequisite never passed, the direct per-VSG MARL comparison is terminally blocked on this route; the fixed title terms remain unsupported targets. | ROUTE.md, LINE.md stop rules | route stop, not MARL-class verdict | Discussion, Limitations, Conclusion |
| A12 | Bounded negative evidence accumulates through preregistered gates with guard-first validity; failed/invalid analyses (R368, R374) were corrected without retry or outcome-driven rule change. | CLM-0985/R368, CLM-1015/R374, CLM-0990/R369 | methodology narrative | Method/Protocol, Limitations |

### Explicit stay-out (never written as positive claims)

- MARL value, learned coordination, message value, neural increment.
- Decoupling improvement, coordination value, controller superiority.
- Stability, safety, robustness, topology generalization, deployment, hardware.
- Title support: every title term stays prospective/rejected.
- Old-line results as evidence (icems2026, model-first, survey) — design inputs only.

## W1 — argument chain

1. Problem: paralleled VSGs dynamically couple; heterogeneous inertia/droop and
   localized disturbances create differential-frequency oscillation; decoupling
   oriented coordination is a claimed remedy in the literature.
2. Limitations of existing work: learned VSG coordination is usually compared
   against fixed droop/no-control baselines, without matched action permission,
   energy feasibility, and pre-training headroom gates; positive results may be
   comparison-contract artifacts.
3. Research objective: on one object, test whether direct per-VSG control
   coordination adds value without physical, energy, or control-stress harm,
   with matched deterministic baselines and a falsifiable learning question.
4. Real challenges: actuator must be VSG-owned and energy-constrained; matched
   permission comparison; joint decoupling endpoint must improve without
   no-harm degradation; headroom must exist before training is even eligible.
5. Method components: (i) four-VSG object with per-VSG energy port; (ii)
   matched zero/local/neighbour deterministic arms on one feasibility-native
   action map; (iii) probe + disturbance banks with guard-first physical
   validity; (iv) outcome-blind non-learning headroom oracle before any
   training gate.
6. Contribution claims: bounded-object validation (A1-A4); matched negative
   evidence across four registered mechanism families (A5-A10); methodological
   result that a headroom-gated, permission-matched protocol stops the MARL
   route before training (A11-A12). No positive title claim.
7. Experiments/figures: Table 1 (object/actuator passes), Table 2 (gate
   sequence outcomes), Fig. 1 (system + port), Fig. 2 (differential energy
   waterfall across arms), Discussion synthesis.

## W2 — section contracts

### S1 Abstract (write last)
- Job: state bounded negative contribution in ~200 words.
- Allowed: A1-A12 compressed; explicit "title terms remain unsupported".
- Exit: reader knows no MARL was authorized and why.

### S2 Introduction
- Job: motivation, gap, contribution, roadmap.
- Claims: none beyond A1/A12 framing; no positive literature claims.
- Exit: contribution list with bounded negative emphasis.

### S3 System model and per-VSG energy port (Methods)
- Job: object identity (four GENCLS VSG proxies, buses 12/16/14/15), 60-Hz
  physical endpoints, observation contract, actuator contract (pref/tm port,
  power-to-torque, achieved-power energy accounting), feasibility-native map.
- Claims: A1-A4.
- Exit: reader can reproduce the intervention.

### S4 Protocol: matched comparison and gates
- Job: arms table (zero/local/neighbour/random/oracle), bank design (probe +
  disturbance), coordinates (common + three differential), endpoints, frozen
  thresholds (0.95 primary, 1.10/1.05 no-harm, 5% headroom), guard-first
  validity, no-retry rule.
- Claims: A12.
- Exit: reader understands why each stop is a registered rule, not a retry.

### S5 Results
- 5.1 Object and actuator validation: A1-A4 (Table 1).
- 5.2 Direct M/D formulation: A5.
- 5.3 Deterministic power-reference: A6.
- 5.4 First-order damping family: A7.
- 5.5 Source-model route: A8.
- 5.6 Higher-order washout: A9.
- 5.7 Outcome-seeing headroom witness: A10 (Table 2, waterfall figure).
- Exit: negative evidence chain complete and internally consistent.

### S6 Discussion
- Job: mechanism synthesis (disturbance-only vs joint headroom; first-order
  selectivity boundary; projection saturation; model fidelity), what the
  negative evidence does and does not show, protocol value, future work.
- Claims: A7, A10-A11 (as bounded); A12.
- Exit: honest interpretation, no impossibility claim.

### S7 Related work
- Job: VSG coordination, MARL for power control, learning-readiness/headroom
  methodology; differentiate matched-permission + energy-feasibility + gate
  protocol.
- Claims: none positive; literature statements are advisory context.
- Exit: gap positioning.

### S8 Conclusion
- Job: restate bounded negative contribution, title boundary, future routes.
- Claims: A11.
- Exit: closed paper.

## W2 paragraph contracts (load-bearing paragraphs only)

- Methods-paragraph "port semantics": job = define actuator quantities;
  observation = quantities stay distinct (request/setpoint/achieved/energy);
  locator = CLM-1000 + CLM-1005; permitted inference = implementation contract
  validated on finite gate; qualifier = one plant, one-second gate, no
  disturbance.
- Results-paragraph "R382 interpretation": job = state the only quantitative
  positive in the whole chain (0.818x disturbance) and immediately bound it;
  permitted inference = disturbance-only authority; qualifier = outcome-seeing,
  nondeployable, finite family; next paragraph = why this does not pass joint
  gate.
- Discussion-paragraph "what stopped MARL": job = A11; permitted inference =
  the registered gates block training on this route; qualifier = not a
  MARL-class theorem.

Persistent paragraph bindings live here; reviewer precommitments go to
`tmp/paralleled_vsg_marl/` only.
