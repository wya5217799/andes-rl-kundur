# Owner decision: resume the line for the V2 non-learning solving mission (2026-08-15)

## Decision

The repository owner (user) directed: "继续执行长期任务，直到彻底完成全部为止"
(continue executing the long-term task until everything is fully complete),
following the owner's earlier instruction "持续解决问题" (keep solving the
problem).  This registers the owner manuscript-route decision that resumes the
yang-md-decoupling-marl line for the **V2 non-learning joint-headroom gate**
only.  It does not reopen the MARL learner route: R404 remains the terminal
successor decision for training; no training, no fresh bank, no algorithm
replacement is authorized by this decision.

## Scope of the resumed work

1. Execute the physical re-verification experiments demanded by the V2
   problem set (tmp/yang_md_decoupling_marl/gpt_pro_math_abstraction_v2.md)
   on the registered feasibility-native energy-port object (R379/R406/R407
   harness, buses 12/16/14/15, dev bank, seed 42, 0.2 s x 50 steps):
   - Stage A: K -> 0 anchor audit and small-gain grid for the frozen 0.4 Hz
     ring-edge bandpass (P6 discrimination), with per-step zero-sum telemetry;
   - Stage B: bandpass gain extension K in {2.25 .. 4.00} (P0'/P8 candidate);
   - Stage C: fixed parallel blend B1 (highpass alpha=0.85 + 0.70 * bandpass
     K=2, pre-clip mixing);
   - Stage D: time-varying A/B blend E1 (cosine cross-fade 3.6-4.0 s);
   - Stage F (only if needed): probe amplitude scan for the P7 divergence.
2. Register the outcome against Q = {r_d <= 0.95, r_cross <= 1.10} with the
   frozen thresholds and guards exactly as R406/R407.
3. Complete the round lifecycle: plan, preflight, capacity evidence,
   rehearsal, sealed execution, feed, claims, verdict, validate/render.

## Authority boundaries (unchanged)

- No training, no fresh unseen bank, no held-out access, no algorithm
  replacement; R404 values stay out of title-supporting results.
- The frozen thresholds (0.95/0.95, 1.03, 1.10, saturation 0) are not
  modifiable post-hoc; the threshold double-source (r_cross <= 1.10 in the
  core problem vs <= 0.95 in V2 section 2.1) is resolved toward 1.10 as the
  primary gate, matching R406/R407 execution, with 0.95 recorded as a
  secondary stricter gate for the found candidate.
- Physical execution enters evidence prospectively: round R408 on this line,
  preflight before any ANDES run.
- External solver outputs (tmp/yang_md_decoupling_marl/vsg_v2_*, registered
  in ARTIFACTS.json as v2-external-candidates) remain advisory context, not
  project evidence; their predictions are falsifiable claims to be tested
  here, not results.

## Records

- Decision doc: this file (working/route_owner_decision_v2_solving_2026-08-15.md)
- Round: memory/rounds/R408 (plan, capacity, rehearsal, seal)
- Results: results/research_loop/r408_v2_solving_gate/
- Feed: paper/yang_md_decoupling_marl/reports/R408.md
