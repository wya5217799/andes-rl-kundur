---
round: R323
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R323 plan - official-source platform and parameter-fidelity audit

**Opened**: 2026-08-03
**Driver**: determine whether R321/R322 can be attributed to the simulation
platform, a parameter/unit error, or an unresolved model-fidelity boundary
before Q-0078 constructs another deterministic controller.
**Parent**: CLM-0740; CLM-0770; CLM-0790; CLM-0815; CLM-0820; Q-0078.

## TL;DR

Audit official ANDES 2.0.0 documentation and installed source against the
registered model contract, sealed interface checks, reduced-model evidence,
and the model-only R321/R322 provenance. Make no new physical or controller
run. If platform causality is unsupported but parameter provenance or fast-
dynamics convergence remains unresolved, qualify the model scope and place one
minimal model-fidelity gate before Q-0078.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0078 [opened R322] Can one actuator-constrained finite-horizon output-feedback formulation be fixed directly from the reduced model, one-sample delay, and physical limits without using R321's examination or a weight grid?

## Recently Closed (last 3)

- Q-0077 closed-negative @ R322, by CLM-0820 — Which development-only mechanism dominates R321's near-continuous governor intervention and output-energy amplification - placed feedback gain, corrected-observer transients, governor projection, or their interaction - and can one analytic repair be fixed before any fresh holdout?
- Q-0076 closed-negative @ R321, by CLM-0815 — Can the exact R320 fixed pole-targeted observer feedback pass nominal poles, finite estimation, unchanged governed development, the untouched bipolar/mismatch examination, the absolute practical floor, and the matched retained-versus-deleted comparison without any target or gain search?
- Q-0075 closed-positive @ R320, by CLM-0810 — Which controller and observer eigenmodes caused R319's nominal pole rejection, are they controllable and observable under the exact delayed augmentation, and can one non-tuned pole-targeted repair be prospectively identified without loading the hidden examination?

## Methodology

### Bounded evidence set

- Use only official ANDES documentation, the installed WSL ANDES 2.0.0 source,
  the selected manuscript model contract, and current claims/feeds for R306,
  R312, R316, R321, and R322.
- Distinguish computational vectorization from the physical model domain.
  Distinguish parameter semantics and unit conversion from physical parameter
  provenance and calibration.
- Verify from registered provenance that R321/R322 did not execute ANDES, then
  prevent any direct-cause attribution to its integrator or lack of EMT detail.

### Fast local diagnostic

- Run the existing public-seam tests that would fail on system/device-base
  conversion, frequency, inertia/damping readback, signed storage power, SOC
  direction, or model-first contract drift.
- Inspect installed ESD1 charging bounds, paux system-base semantics, SOC
  scaling, and GENCLS M/D semantics without editing the installation.
- Record unresolved project-selected values separately: GENCLS proxy M/D,
  storage power/energy, ramp, fast active-current time constant, efficiencies,
  and SOC range.

### Inference and next-gate rule

- Treat existing unit/sign/readback checks as semantic evidence only. They do
  not validate physical realism of the selected values or prove a unified
  switching-level VSG-BESS model.
- Do not migrate to EMT or change the plant retrospectively. First require one
  prospective parameter-source table and a fixed small-signal time-step
  convergence check on the present plant. Any parameter or integration change
  makes a new plant version and requires reduced-model revalidation before
  downstream controller work.
- EVAL is `NOT-APPLICABLE-MODEL-FIDELITY-AUDIT`: this round creates no new
  closed-loop physical trajectory. A future claim-bearing closed-loop physical
  round must run EVAL only after its seal and formal scoring, as diagnostic
  evidence rather than a tuning oracle.

## Gate

- `INVALID-AUDIT`: any official-source, installed-version, parent-provenance,
  test, or manuscript-scope guard fails.
- `PLATFORM-CAUSE-IDENTIFIED`: official/local evidence identifies an actual
  platform or semantic defect that can produce the observed failures; block
  Q-0078 and open a scoped repair question.
- `MODEL-FIDELITY-QUALIFIED`: no direct platform or unit/sign cause is found,
  but parameter provenance or fast-dynamics convergence remains unresolved;
  keep R321/R322 as failures on the current declared proxy and place one
  prospective model-fidelity gate before Q-0078.
- `MODEL-FIDELITY-CLEARED`: direct platform causality is unsupported and every
  material parameter has defensible provenance plus converged fast-dynamics
  evidence; Q-0078 remains immediately eligible.

No outcome authorizes a new controller, physical closed loop, distributed
runtime, reward, agent, training, topology-generalization, EMT-equivalence, or
hardware claim.

## 资产保护契约

- Preserve every R306--R322 plan, seal, result, feed, claim, question, and
  verdict byte-for-byte. Do not change the plant, controller, solver, dataset,
  thresholds, conference title, or installed ANDES package.
- New durable assets are limited to this plan, one line-scoped technical feed,
  one decision claim, one verdict, one follow-up question if required, and the
  selected line navigation/manifest refresh.
- No ANDES simulation, controller execution, holdout access, EVAL score,
  distributed implementation, reward design, or training is permitted.

## Cross-references

- Interface semantics: CLM-0740 and CLM-0770.
- Reduced-model scope: CLM-0790.
- Model-only controller failures: CLM-0815 and CLM-0820.
- Deferred controller formulation: Q-0078.
