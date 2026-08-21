---
round: R466
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-21'
closed: '2026-08-21'
supersedes_rounds: []
superseded_by_round: R467
abort_reason: formal physical jobs completed in memory, but create-only raw JSON serialization
  failed because each segment embedded the outer row that subsequently embedded the segments,
  creating a cyclic object; preserve the 99 MB partial linear output and repair only in a successor
superseded_note: null
---
# R466 plan — U6 exact fractional command-delay margins

**Opened**: 2026-08-21
**Driver**: Replace R450's integer-delay endpoint bracket with an exact continuous-plant/ZOH fractional command-delay realization, all-pole nominal local tracking, and an independently labelled nonlinear finite-bank bisection.
**Parent**: CLM-1405/R450 integer-delay phase/endpoint result; CLM-1435/R459 complete Object B model; CLM-1455/R465 continuous/sampled audit; external U6 derivation is an acceptance input, not numerical evidence.

## TL;DR

Build the exact split `B0(delta),B1(delta)` for `tau=mTs+delta`, augment the gauge-removed Object B plant, K=3.5 digital bandpass state and a fixed ten-sample command memory, track every pole from 0 to 2 s, and localize the first simple unit-circle crossing when identifiable. Separately execute at most three adaptive fractional nonlinear points beginning at 0.1 s, retaining the sign-changing R450 0--0.2 s finite-bank bracket until width is at most 0.025 s. Report nominal local stability and empirical performance boundaries separately; no robust-margin claim.

## Snapshot at plan-time (oracle as of 2026-08-21)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] Does the finite-bank information-level margin program (shared action variables per non-anticipative info class, solution section 5.4) certify or refute INFORMATION-LIMITED for the 2% joint target under the exact R352/R353 observation histories?

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375 — Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0004 closed-negative @ R442, by CLM-1370 — AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?

## Methodology

### Classification and frozen objects

- Work class: **evidence**; create-only root `results/research_loop/r466_u6_fractional_delay`.
- Linear object: R459 Object B nominal continuous `A_c,B_c,C`, fixed R272 0.072 system-pu headroom, nominal physical gauge quotient, and the exact K=3.5 ring-bandpass digital realization. The three disturbance ports do not enter autonomous pole tracking.
- Delay seam is the controller's four-vector normalized output before headroom mapping, exactly matching R450/R440. Feedback is `u=-K y`; probe requests remain immediate and are not placed in the controller-delay queue.
- Nonlinear object: the unchanged R440/R450 nominal topology, seed 42, three arms, eight signed probes plus two disturbances, 50 outer samples and 0.2-s controller updates. Hashed R450 endpoints `r_d(0)=0.9389468<0.95` and `r_d(0.2)=0.9502788>0.95` are reused, not rerun.

### Exact fractional ZOH realization

- For `tau=mTs+delta`, `Ts=0.2 s`, use
  `x[k+1]=Ad x[k]+B1(delta)u[k-m-1]+B0(delta)u[k-m]`,
  `B0=int_0^(Ts-delta) exp(Ac t)Bc dt`, and `B1=Bd-B0`.
- Compute each integral by a block exponential, never Padé/Thiran. Require `delta=0` matrix identity with the integer-delay model to `1e-12` absolute and the `delta -> Ts` endpoint (evaluated at `Ts-1e-9`) to agree with the next-integer model to `1e-8`.
- Use a fixed ten-block command shift register for all `tau in [0,2.0] s`; unused memory modes remain explicit zero poles. This keeps the augmented dimension fixed at 149 and makes all branches comparable across integer boundaries.
- Export `B0,B1`, every augmented matrix hash, controller realization, memory index, and exact feedback-sign convention.

### Pole scan and crossing

- Scan 201 registered points `tau=0:0.01:2.0 s`. At each point compute all left/right eigenvectors, residuals, left-right overlap, inverse overlap condition, and modulus.
- Match consecutive spectra using a Hungarian cost combining normalized eigenvalue distance and `1-MAC`; repeated zero-memory clusters may use an invariant-subspace group ID, but no nonzero branch may be dropped.
- Require every eigen residual `<=1e-9 max(1,||Acl||_2)`. A branch with inverse overlap above `1e8` is near-defective and cannot receive a simple-eigenvalue crossing derivative.
- The first nonzero branch changing from `|lambda|<1` to `>=1` is refined by bisection to bracket width `<=1e-5 s`, preserving branch identity by eigenvalue distance plus MAC. Report centered transversality `d log|lambda|/d tau`; `|slope|>=1e-3 s^-1` and condition `<=1e8` are required for a simple crossing.
- Outcomes are `NOMINAL-LOCAL-CROSSING-VALID`, `NO-CROSSING-UP-TO-2S`, `NEAR-DEFECTIVE-CROSSING`, or `POLE-TRACKING-INVALID`. This is never called robust stability because no uncertainty set exists.

### Nonlinear fractional transport and bisection

- A controller is evaluated once per outer 0.2-s sample. For a fractional point `0<tau<0.2`, its previous output is held for the first `tau` seconds and its current output for the remainder; each segment advances real ANDES TDS with the matching segment duration. Zero/local/bandpass arms use identical jobs and initial conditions.
- Each row stores raw controller output, held segment outputs, requested/mapped/executed power, physical frequency, action/energy guards, TDS validity, and the ANDES discrete-mode hash. Any TDS failure, incomplete 50-step record, or within-new-point mode discontinuity blocks an empirical continuity statement.
- Start with `tau=0.1 s`. Preserve the sign-changing R450 endpoint whose sign opposes the midpoint, then bisect twice more. Stop early only on exact `r_d=0.95`, invalid execution, or mode discontinuity. Otherwise the final bracket width is `0.025 s` and contains at least one crossing only under continuity between the reused endpoints and newly executed interiors.
- The nonlinear classification is `FINITE-BANK-FRACTIONAL-BRACKET`, `OBSERVED-EXACT-THRESHOLD`, `MODE-BOUNDARY-NO-IVT`, or `NONLINEAR-FRACTIONAL-INVALID`. It is a performance boundary, never a pole crossing.

### Theory intake

- **Algebraic identity**: exact ZOH split and integer-endpoint continuity. Observables: block-exponential arrays and direct matrix identities.
- **Mechanism prediction P2-delay**: pure fractional controller delay generates a trackable first nominal local pole crossing. Observables: complete branches, residuals, matching, overlap condition and transversality. Verdict `SUPPORTED`, `REFUTED-UP-TO-2S`, or `UNDECIDABLE` follows only the pole outcome.
- **Performance prediction**: the R450 finite-bank 0.95 crossing remains bracketable under actual fractional transport. Observables: adaptive midpoint ratios, validity, guards, executed actions and mode hashes. A mode jump changes the result to `MODE-BOUNDARY-NO-IVT`, not a smooth crossing.
- The R450 5.38% linear/nonlinear seam is not propagated as an operator uncertainty and does not affect the pole result.

### Capacity and formal launch contract

- Pole construction/scan is one process with four native threads, reusing R459's measured 1/4/8 linear-algebra ladder. Nonlinear jobs use 15 workers plus one orchestrator, one native thread each, in up to six 15-job waves for at most 90 unique jobs; R460 measured this rung 50.96% faster than eight workers with >20% WSL memory headroom.
- GPU is not selected: eigenproblems are small dense CPU work and real ANDES TDS is CPU-bound; no measured GPU path exists.
- `capacity_evidence`: `memory/rounds/R466/capacity_evidence.json`; `host_process_budget=17`; `other_reserved_processes=0`.
- `formal_entry`: `scripts/run_r466_u6_fractional_delay.py` through `scripts/andes_scratch.py`.
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r466_u6_fractional_delay.py rehearse`.
- `rehearsal_scope`: source/parent/case/output checks, exact delay endpoints, 0/0.1/0.2-s augmented shapes and spectra, one representative fractional nonlinear job with two segment lengths, row schema, TDS completion and mode hash; no formal result root.
- `rehearsal_checks`: parent hashes, installed runtime/case, output absence, matrix endpoint identities, finite spectra/residuals, literal fractional segment times, one valid 50-step record, and current capacity/memory.
- Formal commands: `rehearse`, `prepare`, `run`; pole phase uses one process/four native threads, nonlinear phase uses 16 WSL Python processes/one native thread each. Retry policy none; any post-seal pre-output failure aborts R466.

## Gate

### Outcomes

- Enter exactly one pole outcome and one nonlinear outcome from the registered lists above.
- Publication entry requires valid hashes and residuals plus bounded wording; `POLE-TRACKING-INVALID` or `NONLINEAR-FRACTIONAL-INVALID` stays out except as a limitation.
- Stop after the registered 2-s scan and at most three nonlinear midpoint levels. No wider scan, threshold change, controller retune, endpoint rerun, interpolation substitution, or uncertainty invention in this round.

## 资产保护契约

Preserve R440, R450, R459, R465, all parent traces/models, paper-cited assets, and imported GPT material byte-for-byte. Add only R466 implementation/adapter, lifecycle records, create-only pole/nonlinear bundle, feed, claim, verdict, and registrations.

## Cross-references

- CLM-1405 / R450: integer-delay phase consistency and empirical 0--0.2-s endpoint bracket, not a stability margin.
- CLM-1435 / R459: continuous/sampled Object B arrays and controller/headroom contracts.
- CLM-1455 / R465: fixed-mode complete local model chain and conditioning.
- `paper/yang_md_decoupling_marl/working/gpt_pro_unresolved_math_solution_20260821/01_complete_solution.md#u6--分数延迟与局部稳定鲁棒裕度`.
- `paper/yang_md_decoupling_marl/working/gpt_pro_additional_data_request_20260821/` U6 schema and stop rules.
