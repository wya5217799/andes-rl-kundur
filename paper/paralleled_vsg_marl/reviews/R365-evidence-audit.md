# R365 evidence and power-system domain audit

## Coverage and authority

- Scope: the fixed-title line navigation plus the proposed R365 statement that
  the registered V4 candidate passes the per-VSG object/action gate.
- Authority order: sealed `formal_analysis.json` and its bound
  `formal_execution.json`/manifest; R365 prospective plan and Q-0101; future
  claim/feed; `LINE.md` and `ROUTE.md` navigation; review output last.
- Inventory: the evidence inventory scanned `LINE.md` and `ROUTE.md`, found 33
  evidence-sensitive lines, and resolved the only current claim reference
  (`CLM-0970`) plus R338/R359/R363/R364.  No R365 performance prose existed.
- Independent recomputation read the raw eight records rather than importing
  the R365 classifier.  It reproduced the device identities, bus mapping,
  rank-eight action/readback map, observation error, repeat-run floors,
  per-agent off-target response, differential spread, and differential energy.
- Presentation, language, citation-style, venue, and manuscript-layout checks
  are not applicable at this pre-draft feed stage.

## Claim-evidence table

| ID | Proposed atomic claim | Type and scope | Canonical source and locator | Independent verification | Status | Evidence-matched wording |
|---|---|---|---|---|---|---|
| E-001 | The candidate exposes four separately addressable VSG objects. | mechanism/existence; one V4 modified-Kundur plant | `results/research_loop/r365_per_vsg_object_gate/formal_execution.json#/records/*/identity` | All eight arms report exactly `VSG_1..VSG_4` at buses `(12,16,14,15)` and 30/30 completed steps. | VERIFIED | On the registered V4 electromechanical proxy, four unique GENCLS-based VSG units are bound one-to-one to runtime actors. |
| E-002 | Each actor independently changes its declared M/D device channels without scalar aggregation. | intervention/interface; bounded decoder in the sealed bank | `formal_analysis.json#/checks/independent_action_mapping` and `formal_execution.json#/records/6/steps/0:8` | The independently reconstructed normalized-action matrix and physical readback matrix both have rank 8; readback matches the frozen decoder within `1e-9`. | VERIFIED | The eight actor-channel coordinates are independently addressable at the executed GENCLS M/D parameter seam under the registered bounds. |
| E-003 | Runtime observations are causal local-plus-neighbour observations without global/future fields. | information contract; zero delay/dropout, seven fields | `formal_analysis.json#/checks/same_instant_local_neighbour_information`; `formal_execution.json#/records/*/steps/*/observation` | Reconstructing all vectors from same-step local power/frequency/RoCoF and the declared two neighbours gives maximum absolute error `2.959168099447851e-08`; dimension is seven and augmentations are off. | QUALIFIED | The sealed no-delay implementation returns exactly the declared seven same-step local/ring-neighbour fields; source closure contains no additional observation field. This does not establish delayed/dropout behavior. |
| E-004 | The registered mismatch produces an above-noise differential oscillatory transient. | descriptive mechanism premise; one LS1 disturbance, one heterogeneous-D arm, six seconds | `formal_analysis.json#/differential_dynamics` | Physical-frequency spread is `0.20348587426928333 Hz`, differential energy is `0.008624438798992152 Hz^2 s` versus a `1.9999999999999998e-15 Hz^2 s` floor, with five direction reversals. | QUALIFIED | The combined heterogeneous-damping plus localized-load-step condition exhibits a measurable inter-device differential transient on this plant. Do not attribute it uniquely to damping heterogeneity. |
| E-005 | Every single-agent action has nonzero network-transmitted authority. | paired deterministic intervention; four single-agent arms versus repeated zero action | `formal_analysis.json#/action_authority` | Repeat drift is zero, frozen floors are `1e-7 Hz` and `1e-8 p.u.`; the four off-target frequency effects are `0.024731...` to `0.050853... Hz` and power effects are `0.165280...` to `0.320016... p.u.`. | VERIFIED | Each actor's registered combined M/D intervention changes at least one other VSG frequency or active-power trace above the repeated-run numerical floor. |

All transformations are identity reads except: action/readback rank is the
matrix rank of the first eight fingerprint decisions; differential energy is
`sum_t mean_i((f_i-mean_i f_i)^2) * 0.2 s`; authority is the maximum absolute
off-target paired difference from `zero_a`.  Physical frequency uses the
simulator's 60-Hz base.  Lower/higher directions are not performance claims.

## Findings

### D-001 | MAJOR | next deterministic-control and learning design | nominal-frequency contract

The plant reports a 60-Hz nominal base while the inherited observation
normalization uses the legacy 50-Hz contract.  R365 records both and computes
physical endpoints on 60 Hz, so the object/interface result remains usable;
however, any controller comparison or training must prospectively choose one
unit-valid normalization or explicitly prove the constant conversion is
permission-matched across every method.  No 50-Hz physical result may be
reported from this plant.

### D-002 | MAJOR | title and future method claims | actuator feasibility

The intervention changes GENCLS inertia and damping parameters.  The gate does
not model converter inner loops, storage state of charge, energy, current,
thermal limits, or an achieved hardware parameter update.  Therefore it proves
bounded parameter-seam authority, not energy-feasible storage control, safety,
deployment feasibility, or hardware VSG behavior.  These limits must remain in
the claim and must be addressed separately if future prose says storage or
safety.

### D-003 | MINOR | mechanism wording | mismatch attribution

The heterogeneous-D arm and localized disturbance occur together.  The trace
supports existence of a differential transient under the combined mismatch,
not a unique causal claim that damping heterogeneity created it.  A later
homogeneous/heterogeneous paired mechanism ablation is required for that
attribution.

### D-004 | MINOR | inference wording | population and uncertainty

This is a deterministic existence gate on one topology, disturbance, seed,
and short horizon.  Repeat runs establish numerical repeatability, not a
statistical population.  No robustness, probability, superiority,
generalization, stability, safety, or controller-performance language is
supported.

## Cross-section drift and repair

- `ROUTE.md` formerly said "safe direct M/D authority" after Phase 1.  The
  audit narrows it to "bounded direct M/D parameter authority" because R365
  has no energy/safety certificate.
- The fixed title remains prospective.  R365 supports the `Paralleled VSGs`
  object premise and a prerequisite for coordination; it does not yet support
  `Decoupling-Oriented`, `Coordination`, or `MARL` as achieved results.
- The direct-MARL navigation is a method decision, not evidence that learning
  is useful or trainable.

## Audit decisions

- Evidence audit: **CONDITIONAL PASS**.  E-001/E-002/E-005 are verified and
  E-003/E-004 are usable only with the supplied narrow wording.  No canonical
  conflict or missing formal record remains.
- Power-system domain verdict: **MAJOR REVISION before the next control or
  training gate**, due to the 50/60-Hz normalization contract and the gap
  between parameter modulation and energy-feasible storage actuation.  These
  findings do not reverse the narrowly scoped R365 object-gate PASS.
- Allowed claim: the sealed V4 proxy passed the registered four-object,
  independent M/D mapping, same-step local-neighbour information,
  differential-transient, and nonzero network-response prerequisite gate.
- Stay out: controller efficacy, decoupling improvement, message value,
  coordination gain, MARL value, convergence, stability, safety, robustness,
  topology generalization, storage-energy feasibility, hardware validity, and
  publication readiness.
