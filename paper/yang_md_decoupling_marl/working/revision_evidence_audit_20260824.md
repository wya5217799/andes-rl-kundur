# Review-driven revision evidence audit — 2026-08-24

## Coverage and authority

- Scope: material claims added or materially rewritten in both 2026-08-24
  review-driven revisions of `manuscript/main.tex`.
- Audited source SHA-256:
  `5eff32b5b430ec33197ac8dcacfd5ff6af3624d44a495e32714d9108ba285dc0`.
- Precedence: sealed/formal analysis and current executable contract, then
  validated claim/feed reports, then manuscript/review prose.
- The direct-$M/D$ and energy-port objects remain non-pooled.

## Claim-evidence table

| ID | Manuscript claim | Canonical source and locator | Verification | Status |
|---|---|---|---|---|
| E-001 | GENCLS swing equation, $M=2H$, and direct $M/D$ actuation (lines 173--195) | `src/andes_rl_kundur/env/andes/base_env.py`, `VSG_M0` contract and `_compute_omega_dot`; `paper/yang_md_decoupling_marl/reports/R446.md`, setup and observations | The repository equation is $M\dot\omega=P_m-P_e-D(\omega-1)$; the manuscript adds the standard ANDES angle equation and labels the plant as a swing-equation proxy. | VERIFIED |
| E-002 | Action interval, slew, asymmetric decoder, clamps, and learner-bank ranges (lines 182--195) | `src/andes_rl_kundur/evaluation/cd_matd3_canary.py`, `_PROFILE_ROWS` and `build_contract#/action_slew_limit,/decoder`; `src/andes_rl_kundur/env/andes/base_env.py`, `step` | Min/max across the eight learner profiles are $M^0=[140,260]$ and $D^0=[50,150]$; decoder and clamps match the executable contract exactly. | VERIFIED |
| E-003 | Odd response, probe vectors, and $J_{\mathrm{cross}},J_d$ definitions (lines 210--234) | `src/andes_rl_kundur/evaluation/md_decoupling_headroom.py`, `_signed_scenarios` and `summarize_profile`; `manuscript/supplement/frozen_profile_bank.csv` | The $1/2$ odd response, vector normalization, profile magnitudes/locations, $1/3$ differential-coordinate mean, and $\Delta t/\varepsilon_k^2$ normalization match the executable contract. | VERIFIED |
| E-004 | 103% output and 110% executed-command guards (lines 237--254) | `src/andes_rl_kundur/evaluation/md_decoupling_headroom.py`, `build_contract#/thresholds`, `_common_guard`, and oracle command guards | $1+0.03=1.03$ and $1+0.10=1.10$; wording is explicitly empirical and disclaims safety/stability certification. | VERIFIED |
| E-005 | Separate 2+4 deterministic and 4+4 learner profile banks (lines 275--284) | `src/andes_rl_kundur/evaluation/md_decoupling_headroom.py#_PROFILE_ROWS`; `src/andes_rl_kundur/evaluation/cd_matd3_canary.py#_PROFILE_ROWS`; `manuscript/supplement/frozen_profile_bank.csv` | Split counts and all numeric profile fields match both frozen contracts. | VERIFIED |
| E-006 | Synchronous ideal communication, training-only critic access, and no delay/loss/quantization (lines 296--300 and 575--577) | runner environment construction with `comm_fail_prob=0.0, comm_delay_steps=0`; `scripts/run_r475_u2_confirmatory.py#source_rows` | Source rows use the same-time joint observation; the critic is absent from evaluation action selection. No quantizer is present. | VERIFIED |
| E-007 | Confirmatory SAC reward weights, pre-clamp command penalty, and neighbour-term switch (lines 301--313) | `scripts/run_r451_m3_message_factorial.py#PHI_F,PHI_ABS,PHI_H,PHI_D`; `scripts/run_r438_sac_message_channels.py#channel_step_rewards`; `src/andes_rl_kundur/env/andes/base_env.py#step` | Coefficients and switch match; the implementation penalizes decoded increments before the lower clamp. | VERIFIED |
| E-008 | 48 cells, 16 audited carryovers, 32 fresh cells, and 16 evaluation jobs (lines 358--367) | `results/research_loop/r477_u2_confirmatory/formal_analysis.json`; `r476_shard_import.json`; supplement carryover and stability tables | Formal design/execution/integrity are VALID/COMPLETE/PASS; source/target paths and carryover allocation are exposed. | VERIFIED |
| E-009 | Exact $2^6$ sign flips, exact $6^6$ bootstrap, asymmetric sign sensitivity, half/final and curve-stability checks (lines 370--391) | `scripts/run_r475_u2_confirmatory.py`; R477 formal analysis; `r477_asymmetric_sensitivity.json`; `r477_training_stability.csv` | Primary procedure matches the code; the exact-binomial sensitivity is independently recomputed from the six sealed paired effects. | VERIFIED |
| E-010 | Marginal effects, intervals, p-values, half/final contraction, leave-one-out, and interaction reversals (lines 481--508) | R477 formal analysis; `r477_conditioned_effects.csv`; `r477_reward_conditioned_effects.csv` | All percentages and intervals reproduce from seed--profile endpoints; interactions are labelled descriptive. | VERIFIED |
| E-011 | Ten equilibrium-sound variants comprise nominal + four inter-area outages + five reactance scalings; two VSG-tie outages are excluded (lines 528--541) | `results/research_loop/r413_topology_robustness/formal_analysis.json`; `manuscript/supplement/r413_topology_variants.csv` | Formal keys contain exactly those ten passes and the two named failed VSG-tie outages. | VERIFIED |
| E-012 | Source-effect figure uses signed rather than improvement-only semantics | `manuscript/build_figures.py#pct,#build_source_effect`; `results/research_loop/r477_u2_confirmatory/formal_analysis.json#/primary_materiality_tests` | Axis is now “Signed source effect (geometric)”; plotted means and intervals are deterministic transforms of formal analysis. | VERIFIED |
| E-013 | Reproducibility supplement binds input banks, endpoints, contrasts, carryovers, stability, topology, and run flow (lines 365--368) | `manuscript/build_reproducibility_supplement.py`; `manuscript/supplement/supplement_manifest.json`; SHA-256-verified R477/R413 artifacts | The top-level manifest binds every generated file, upstream formal artifact, generator, and audited `main.tex` hash. | VERIFIED |
| E-014 | Carryover allocation is asymmetric and does not establish independent repeatability (lines 519--523) | `r477_carryover_manifest.csv`; `r477_run_flow.md`; `r476_shard_import.json` | All 16 carryovers are actor-source N; the manuscript now states the unexcluded batch-by-factor limitation. | VERIFIED |
| E-015 | Energy-port witness attains only its own distinct contract (lines 528--547 and 586--588) | R413 formal analysis and the non-pooled object boundary in the evidence map | Abstract, Results, and Conclusion no longer imply direct-$M/D$ attainability. | VERIFIED |

## Cross-section drift and findings

- No BLOCKER or MAJOR discrepancy remains within the audited revision scope.
- MINOR upstream inconsistency: `reports/R413.md` says “five inter-area
  outages” in two prose summaries, but its frozen-bank definition and the
  authoritative `formal_analysis.json` contain four sound inter-area outages,
  five reactance scalings, nominal, and two failed VSG-tie outages. The
  manuscript follows the formal artifact and the arithmetically consistent
  bank definition.
- The numerical 73.5% power sentence was removed because the main manuscript
  did not expose enough derivation to make the approximation reproducible.
- “Pre-registered” was replaced by “prospectively frozen” because no public
  registry locator is claimed.
- Exact Python, PyTorch, and NumPy versions were not recorded in the sealed
  R477 artifact. The supplement therefore reports this provenance limit rather
  than reconstructing an unverified execution environment.

## Decision

**PASS for the two review-driven revision scopes.** All added or materially
changed scientific claims are verified against current executable contracts or
formal analysis. This audit does not replace the existing whole-manuscript
evidence map or a venue-package audit.
