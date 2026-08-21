# figures_source_manifest — decoupling-marl-model-first

Generated 2026-08-16. Every plotted value is read verbatim from the sealed
results JSONs below; the only transformations applied are the documented
ratios, log/percent scalings, and grouping listed per figure. Nothing was
re-simulated or invented. SHA-256 hashes are of the whole JSON files as
archived under `results/`.

## Revision log (review outcome)

- **fig6_family_gates.pdf → UNUSED**: the family results now live as
  in-text Table II and a figure would duplicate it (reviewer finding 5.1).
  The PDF is retained for reference and marked UNUSED below; do not include
  it in the submission.
- **fig5_oracle_headroom.pdf rewritten**: now renders per-scenario oracle
  improvements (`(base − nominal)/base` from `/oracle`) instead of only the
  two endpoint means, with the 2% floor line and the 1.7e-9 shortfall
  (mean 1.9999998%) annotated and a zoom inset; neighbour-local means
  remain as a prose note.
- **fig1_plant_contract.pdf**: added the caught-fidelity-defect callout
  (MF-01: legacy 60/50 Hz labelling repaired; the detected 60-Hz ANDES base
  is the only frequency base), sourced from `working/model_contract.md` and
  `reports/R306.md`.

| # | Figure file | Sealed source (repo-relative path) | Exact locator(s) | SHA-256 (source file) | Transformation | Caption (finding first; source pointer last) |
|---|---|---|---|---|---|---|
| 1 | `fig1_plant_contract.pdf` | `paper/decoupling_marl_model_first/working/implemented_control_and_topology.md` (sections 2, 4, 5, 6); fidelity-repair wording from `working/model_contract.md` (MF-01) and `reports/R306.md` | topology §2.4 (E_c, E_a, B_a), action basis §4, governors §5, controllers §6; MF-01 frequency-base defect | n/a (schematic; no measured values) | schematic drawing: four nodes, three graphs (G_e / G_c ring / G_a tree with B_a signs), request→command→achieved power layers; one caught-fidelity-defect callout (MF-01: legacy 60/50 Hz labelling repaired) | The storage-coordinated VSG plant separates the electrical graph, the communication ring and the three-edge differential action tree (B_a = [[1,0,0],[-1,1,0],[0,-1,1],[0,0,-1]]) and routes power through three distinct layers (request → projected command → achieved), so a controller can only set requests — with the caught 60/50 Hz labelling defect (MF-01) annotated on the plant; structural facts follow `implemented_control_and_topology.md` §2, §4, §5 and §6. |
| 2 | `fig2_gate_sequence.pdf` | `paper/decoupling_marl_model_first/working/manuscript_argument_contract_2026-08-14.md` (section 6) and line feeds R306–R363 | figure plan §6; gate stages and exit criteria per feed | n/a (schematic; stage labels only) | flowchart with per-stage PASS / FAIL(-closed) branches | Every protocol stage — fidelity contract, canaries, model gate, deterministic bridge, headroom oracle, information families, basis ablation — is a pre-registered fail-closed gate whose failure stops the route with a bounded verdict before any training compute; stage labels follow the argument contract §6 and the R306–R363 feeds. |
| 3 | `fig3_stage1_probes.pdf` | `results/r312_model_first_stage1/analysis.json` | `/pair_metrics` (per-pair `cross_gain`, `self_gain`); `/max_all_nonlinearity_ratio` | `75804e5fb3f704a3d0b878db20819f997c15aaa46ae6d6dcc886879eea361c02` | per-pair ratio `cross_gain/self_gain` expressed in % (12 pairs); observed range min/max annotated | Signed-probe cross/self L2 gain ratios stay at 1.11%–3.90% across all three operating points (1.11% at OP2/edge_2, 3.90% at OP1/common), so the plant is not hard-decoupled and the retained common/differential coordinates must keep the measured cross gains; ratios computed from `/pair_metrics` in `results/r312_model_first_stage1/analysis.json`. |
| 4 | `fig4_deterministic_bridge.pdf` | `results/r344_deterministic_bridge/formal_execution.json`; `results/r344_deterministic_bridge/formal_analysis.json` | `/records` (metrics `common_coordinate_iae`, `differential_coordinate_energy`, arms `zero_control`/`frozen_controller`); `/paired_mean_improvement_fraction`, `/guards` | `8a82763ce1b3f777c4e7a1429f92651eb88d94d0bc238ee0c06664be6676bbd1` (execution); `41c8e73deadbf30d0352dc5a20f82938ad3723ca7f2467a86f2d8f494996ad72` (analysis) | per-scenario paired fraction `(zero − controlled)/zero` for both endpoints (16 scenarios); sealed ratio-of-means reductions and guards reproduced verbatim; 5% no-harm limit marked at −0.05 | The frozen centralized deterministic bridge improves both endpoints in all 16 paired scenarios — mean common-coordinate IAE reduced by 0.9551 and differential-coordinate energy by 0.9933 — with no scenario worsening either endpoint by more than the 5% no-harm limit; per-scenario fractions from `formal_execution.json#/records`, sealed means and guards from `formal_analysis.json#/paired_mean_improvement_fraction` and `#/guards`. |
| 5 | `fig5_oracle_headroom.pdf` | `results/r350_smooth_convex_residual/analysis.json` | `/oracle` (16 per-case records: `base_endpoints`, `nominal_endpoints`, `scenario_id`); `/gates/oracle_nominal/endpoints` (sealed per-coordinate `mean_improvement_fraction`, `minimum_improvement_fraction`); `/gates/local_nominal/endpoints` (neighbour-local means, shown as prose note); `/classification` | `81801fd7e2d90b6aa231a887c13b4ded838e4392a0b112cff594a8278c418e32` | per-scenario improvement fraction `(base − nominal)/base` per coordinate (16 scenarios); mean-of-ratios reproduces the sealed `/gates/oracle_nominal` means exactly; 2% floor drawn from `minimum_improvement_fraction`; shortfall = floor − sealed mean = 1.74e-9 (annotated ~1.7e-9), zoom inset on panel (a) | The outcome-seeing oracle pins the common-coordinate improvement at the 2% constraint on all 16 scenarios — mean 1.9999998%, a 1.7e-9 shortfall below the 2% qualifying floor, so the nominal oracle gate fails — while only the PQ_Bus14 channel carries differential headroom (11–18%); per-scenario `(base − nominal)/base` from `/oracle` in `results/r350_smooth_convex_residual/analysis.json`, sealed means and floor from `/gates/oracle_nominal/endpoints`. |
| 6 | `fig6_family_gates.pdf` — **UNUSED** (superseded by in-text Table II, reviewer finding 5.1; file retained for reference, do not include in the submission) | `results/r359_neighbour_causal_residual/analysis.json`, `results/r360_flexible_neighbour_residual/analysis.json`, `results/r361_neighbour_message_residual/analysis.json`, `results/r362_shared_prediction_residual/analysis.json` | `/development/family_gates/*/nominal/endpoints` (r360–r362); `/development/gates/nominal/endpoints` (r359 affine-only); per-coordinate `paired_gate.mean_improvement_fraction` (panel a) and `paired_gate.mean_signed_relative_change` (panel b), `minimum_improvement_fraction` floor | `aa5b1d89d238a68f5b3c5506319a66450fdaa23b4f207894a3b7bd2fb4832f0f` (r359); `2a87258e37a52578d1bb339542054d6055c1e534378078e4b6afe53687e61ffc` (r360); `279f5aa53cfeccca658b4359441d735079da04712fd648430fa088edf320677f` (r361); `bcad59b38032ef8bb33293711897e06bc5a8e023f52763afcfcb640bfec14fc1` (r362) | grouped bars (variant × family); panel b on log scale; missing r359 cells left empty (absent by design, not zero) | UNUSED — the family results now live as in-text Table II and a figure would duplicate them; retained values: none of the 16 executed information-family gates reaches the 2% common-coordinate qualifying floor, and every family worsens the differential endpoint 0.9–673-fold (data from the four `/development/family_gates/*/nominal/endpoints` blocks; r359: `/development/gates/nominal/endpoints`). |
| 7 | `fig7_common_channel.pdf` | `results/r356_joint_endpoint_feasibility/analysis.json`, `results/r358_physical_joint_endpoint_qp/analysis.json`, `results/r363_common_channel_qp/analysis.json` | r356 `/development_results` (per-case `status`); r358 `/candidate_results`, `/inherited_relaxed_infeasible_scenario_ids`, `/accepted_physical_feasible_candidate_count`, `/inherited_relaxed_infeasible_count`; r363 `/common_channel_results` (per-case `accepted`), `/feasible_count`, `/r358_baseline_feasible_count`, `/newly_feasible_scenario_ids` | `9a4334c4575cd803114e52c4ed2279efe6defa979734b08e3bc28de0e37332b1` (r356); `c471aafc51a3019202777ca166e66b7c93739304fcd335bbe1511a5b3f4f26fb` (r358); `acc805c0cb2b4a90997f9a410f1af6187fe78bf254576326dc17c649f5d00238` (r363) | per-case feasible/infeasible boolean per gate (3 rows × 16 scenarios); counts and newly-feasible set read verbatim, asserted consistent (r363 newly feasible = r358 inherited = r356 primal-infeasible) | Adding the common channel to the residual basis restores feasibility on all 16 exposed development scenarios (16/16 vs 10/16 under the three-edge basis), and the six newly feasible scenarios are exactly those that were primal-infeasible even under the R356 cone relaxation, so the zero-common contract is the structural limiter; per-case statuses from `results/r356_joint_endpoint_feasibility/analysis.json#/development_results`, `results/r358_physical_joint_endpoint_qp/analysis.json#/candidate_results` and `results/r363_common_channel_qp/analysis.json#/common_channel_results`. |

## Missing-locator findings

None of the requested locators for figures 1–5 and 7 was missing. One
structural note for figure 6:

- `results/r359_neighbour_causal_residual/analysis.json` has **no**
  `/development/family_gates` key: R359 executed only the affine family and
  stores its gate at `/development/gates/{nominal,mismatch_bounded}/endpoints`
  (`/development/decision/classification` = `NO-NEIGHBOUR-CAUSAL-HEADROOM`).
  The R359 × {rbf_kernel_ridge, knn, quadratic_polynomial} cells in fig6 are
  therefore absent by design and are shown as empty slots; no value was
  substituted from memory or feed prose.

## Transformations applied (whitelist)

- fig3: `cross_gain / self_gain` from `/pair_metrics` (ratio, %); min/max
  range annotation is the min/max of those 12 ratios (1.1129% → 1.11%,
  3.8971% → 3.90%); `max_all_nonlinearity_ratio` shown as a ceiling note.
- fig4: per-scenario `(zero − controlled) / zero` from the two arms in
  `/records`; sealed `/paired_mean_improvement_fraction` reproduced exactly
  (verified equal to the ratio-of-means over the 16 scenarios).
- fig5 (revised after review): per-scenario oracle improvement
  `(base − nominal) / base` per coordinate from the 16 `/oracle` records;
  the mean-of-ratios reproduces the sealed `/gates/oracle_nominal` means
  exactly (common 0.019999998263348927, differential 0.05138182207868676);
  floor 0.02 from `minimum_improvement_fraction`; annotated shortfall
  `0.02 − mean = 1.7367e-9` (~1.7e-9); neighbour-local means shown only as
  a prose note (their per-scenario values are not derivable from
  `/neighbour_local`, which lacks a baseline endpoint).
- fig6 (UNUSED): `paired_gate.mean_improvement_fraction` (panel a) and
  `paired_gate.mean_signed_relative_change` (panel b, positive = worsening);
  log scale on panel b.
- fig7: per-case booleans; counts and ID sets verbatim, cross-consistency
  asserted in `scripts/audit_figures.py`.

## Style audit (figure-designer quality-control pass)

- Vector format: all 7 figure PDFs retained as vector (`pdf.fonttype 42`);
  **6 are active** — `fig6_family_gates.pdf` is kept but marked UNUSED
  (superseded by in-text Table II, reviewer finding 5.1) and must not be
  included in the submission.
- Font sizes: 6.5–9 pt at final (unscaled) size; data labels ≥6.5 pt,
  axis/labels ≥8 pt — dense schematic annotations are 6.5 pt, flag for
  confirmation at final column width (MINOR).
- Colour-blind-safe: Okabe-Ito palette only, always dual-encoded with
  hatches (fig3 edges, fig5 channels, fig7 infeasible) or markers/frames
  (fig4 points, fig7 orange frames for newly feasible).
- Self-contained captions: each states the finding first and the data
  source pointer last (see table above).
- Honest axes: fig4 y starts below 0 to show the −0.05 no-harm line;
  fig5 panel (a) carries a zoom inset on a 1e-9-scale axis to make the
  shortfall legible (no axis truncation in the main panels); fig6 panel b
  (retained file) uses a true log scale.
- No chartjunk: no 3D, no decorative elements; light gridlines only where
  they aid reading.
- Integrity gate: figure types match paradigms (schematic/flowchart for
  fig1–2; grouped bar / paired bar / feasibility grid for fig3–7); labels
  are real entity names (B_a, E_c, ESD1, Π_U, coordinates, gate names);
  every plotted value re-derived from the sealed JSONs by
  `scripts/audit_figures.py` (all checks pass); no CRITICAL violations.
