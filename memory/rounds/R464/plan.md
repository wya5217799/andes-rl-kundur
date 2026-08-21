---
round: R464
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-21'
closed: '2026-08-21'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R464 plan — U1 QY10 certificate-bearing finite-window phase I

**Opened**: 2026-08-21
**Driver**: Instantiate the requested 90-variable strictly causal differential Youla class on the complete R459 Object B model and either produce an independently checked witness/dual bound or stop at a named certificate failure.
**Parent**: CLM-1435/R459 shared Object B export; external U1 class/certificate specification is acceptance input, not evidence authority.

## TL;DR

Freeze one local Object B equilibrium, remove only its analytically unobservable unit-circle angle gauge, verify the remaining sampled realization is internally stable, use the stable-plant negative-feedback DCF, generate all 90 lifted columns over a 30-step orthonormal three-disturbance bank, and solve a conservative no-saturation SOCP phase I against the frozen K=3.5 bandpass reference. Export canonical cone data and unscaled primal/dual arrays for an independent checker.

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

### Classification and named class

- Work class: **evidence**; create-only root `results/research_loop/r464_u1_qy10_certificate`.
- Object: R459 Object B only. Object A and R452/R463 schedules are not pooled.
- Coordinates: `y_n=(f-60 Hz)/(1 Hz)` and normalized active-power command `u_n`; normalized command maps to system-pu power through the four frozen positive headrooms `0.072`.
- Let `T_d` be an explicitly exported orthonormal 3x4 basis for the zero-sum subspace. Freeze
  `Q(z)=sum_{h=1}^{10} T_d^T Qhat_h T_d z^{-h}`,
  `Qhat_h in R^(3x3)`, with 90 real variables and
  `sum_h ||Qhat_h||_F^2 <= 1`.
- `locality_claim=false`. Differential structure applies to Youla coefficients only; no ring-local final-controller claim is authorized.

### Gauge, baseline, and DCF

- Identify the unique sampled eigenvalue at one, export normalized left/right eigenvectors, and require eigen residuals `<=1e-10`, `||C v_g||<=1e-10`, and transfer residue norm `<=1e-10`. Remove it through an orthonormal basis whose first vector is `v_g`; require the 101-state complement spectral radius `<1-1e-6` and transfer-function agreement with the full realization away from `z=1` within `1e-10` relative error.
- The baseline for the DCF is the zero normalized controller on the stable gauge-removed plant. The K=3.5 bandpass is only the frozen performance reference.
- Under negative feedback `u=-K y`, factor the signed plant `-P_c` with stable factors `M=M~=I`, `N=N~=-P_c`, `U=U~=0`, `V=V~=I`. The frozen convention gives `K(Q)=(I-QP_c)^-1 Q`, `y=(I-P_c Q)P_w w`, and `u=-Q P_w w`.
- Verify the full block Bezout product coefficient-by-coefficient over the 30-step Markov horizon with relative residual `<=1e-10`; a sign/convention failure immediately yields `CERTIFICATE-INVALID` and stops before solving.

### Frozen finite bank and lifts

- Window: 30 samples at 0.2 s. Disturbance inputs are the exported three Object B PQ channels transformed into one normalized common direction and two orthonormal differential directions. Each basis impulse is a separate scenario; signs are redundant in this linear class and are verified by odd symmetry.
- Reference: an exact full-`D` reconstruction of the exported K=3.5 bandpass controller on the R459 sampled plant, solving its same-step algebraic loop explicitly and exporting frequency plus normalized command outputs. The older exported augmented array, which omits the sampled feedthrough in its assembly, is comparison-only and is not used as the certificate denominator. All reference denominators must be finite and above `1e-12`.
- Export affine lifts for differential output energy, cross response (differential output from common input plus common output from differential inputs), common IAE, all-unit peak/RoCoF, action RMS, boundary-aware TV, and every action sample.
- Independently compare every selected analytical column with symmetric direct-convolution finite differences at `1e-4` and `5e-5`; relative error must be `<=1e-7`, with absolute `1e-10` for near-zero columns.

### Conservative phase I

- Minimize dimensionless worst residual `t` across: both energy norms relative to `sqrt(0.95 E_ref)`; common IAE/peak/RoCoF relative to `1.03` reference; action RMS/TV relative to `1.10` reference; all normalized command samples relative to `0.69`, which is a conservative zero-saturation tube inside the frozen `0.70` clip; and the Q coefficient Frobenius bound.
- This is a pure SOCP/LP epigraph. No saturation-fraction cardinality constraint is represented.
- Run CVXPY 1.9.2 canonicalization and Clarabel 0.11.1 with equilibration disabled and declared tolerances. Export sparse cone `A,b,c`, cone ordering, variable maps, solver log/stats, original q/t, and canonical x/s/z.
- The independent checker recomputes primal equality/slack residual, cone membership, dual cone membership, stationarity, unscaled primal/dual objectives, relative gap, original constraints, lift identities, DCF identities, and 80-decimal dual bound.

### Prospective outcomes and stop rules

- `FEASIBLE-WITNESS-IN-QY10`: independently verified `t<=-1e-7`; run only this witness and symmetric coefficient perturbations in a separately sealed nonlinear successor before any nonlinear-transfer claim.
- `INFEASIBLE-QY10-WITH-VERIFIED-DUAL-BOUND`: `t>0`, canonical primal/dual checks meet tolerances, the positive unscaled dual bound exceeds ten times the numerical residual allowance, and 80-decimal reevaluation stays positive.
- `CERTIFICATE-INVALID`: solver status alone, DCF/lift/KKT/cone/gap failure, non-positive denominator, or insufficient positive-bound safety.
- `CERTIFICATE-NOT-IDENTIFIABLE`: gauge or model/reference data cannot identify the declared map without a new object definition.
- No result is extended to all FIR controllers, neural policies, nonlinear DAE behavior, robust stability, or deployment.

### Capacity and launch

- One process with four native BLAS threads, reusing R459's measured 1/4/8-thread ladder where four threads was fastest and oversubscription was rejected. GPU is not selected for sparse CPU conic canonicalization.
- Rehearsal executes gauge/DCF, a reduced column check, cone construction, strict output absence, and a short solver call without creating the formal root.
- WSL runtime: `/home/wya/andes_venv/bin/python`, with newly installed `cvxpy==1.9.2`, `clarabel==0.11.1`, and `scs==3.2.11` recorded by package version/hash.
- Commands: through `scripts/andes_scratch.py`, `scripts/run_r464_u1_qy10_certificate.py rehearse`, then `prepare`, then `run`.
- Retry policy: none; preserve terminal attempt and use a successor for any correction.

## Gate

Enter only one of the four prospective outcomes above. A positive class-infeasibility claim requires the verified dual-bound branch; solver text alone is never sufficient.

## 资产保护契约

Preserve R459, R461-R463, all parent models/results, and imported GPT material byte-for-byte. Add only R464 source/tests, prospective records, create-only certificate bundle, and later feed/claim/registrations.

## Cross-references

- CLM-1435 / R459: complete Object B arrays, headroom, units, controller and provenance.
- `paper/yang_md_decoupling_marl/working/gpt_pro_additional_data_request_20260821/`: U1 requested class and acceptance rules.
