# Source map and provenance

The solution was derived only from the uploaded evidence package. No plant matrices, trajectories, uncertainty bounds, or R458 outcomes were back-filled.

## Core brief

- `tmp/yang_md_decoupling_marl/gpt_pro_unresolved_math_delta_20260821.md` — U1–U9 requirements and evidence boundaries.
- `tmp/yang_md_decoupling_marl/c1_youlas_sls_certificate.md` — procedural Youla/SLS construction and explicit list of missing certificate objects.
- `paper/yang_md_decoupling_marl/manuscript/manuscript.md` — common/differential coordinates and exact homogeneous proposition.

## Decision-bearing result files

- `results/research_loop/r405_homogenization_gate/linearization_matrices.json`
  - fields used: `profiles.*.{f_x,f_y,g_x,g_y,x0,y0,baseline_m0,baseline_d0}`.
  - limitation: no Object-B control/disturbance columns or output map.
- `results/research_loop/r405_homogenization_gate/formal_execution.json`
  - fields used: profile snapshot dimensions and `g_y_condition`.
- `results/research_loop/r446_md_authority_fd/formal_analysis.json`
  - fields used: `snapshot`, `h_grid`, `per_column`, `verdict`.
- `results/research_loop/r447_p1_complex_response/formal_analysis.json`
  - fields used: state/input/output dimensions, closed-loop dimensions, spectral-radius summaries, band energies and ratio.
- `results/research_loop/r449_p1_sensitivity/formal_analysis.json`
  - fields used: `delta`, `results.logM`, `results.logD`.
- `results/research_loop/r450_p2_delay_loop/formal_analysis.json`
  - fields used: nonlinear ratios, sample period, feedback sign, `band_rows`, predicted ratios, min return-difference singular values, zero-delay seam.
- `results/research_loop/r452_m5_all_candidate_pareto/formal_analysis.json`
  - fields used: candidate counts, fixed profile paths and guard-clean IDs.
- `results/research_loop/r452_m5_all_candidate_pareto/profiles/eval_{a,b,c,d}.json`
  - fields used: `static` reference metrics and record counts.
- `results/research_loop/r453_m5_aggregate_repair/formal_analysis.json`
  - fields used: corrected guard-clean candidate IDs and class scope.
- `results/research_loop/r456_m1_dual_saturation/formal_analysis.json`
  - fields used: RMS/TV gradient-conflict support counts and checkpoint scope.
- `results/research_loop/r457_m2_head_causality/formal_analysis.json`
  - used only to preserve the latest bounded disposition of the common-head hypothesis.

## Source and prospective plans

- `src/andes_rl_kundur/evaluation/cd_matd3_canary.py`
  - reward/constraint normalization, episode budget and multiplier update.
- `src/andes_rl_kundur/agents/cd_matd3.py`
  - slew projector, augmented observation, replay and target-action semantics.
- `src/andes_rl_kundur/evaluation/deterministic_headroom.py`
  - exact common IAE, TV and saturation definitions.
- `scripts/run_r452_m5_all_candidate_pareto.py`
  - thresholds and `candidate_guard` implementation.
- `memory/rounds/R451/algorithm_audit.json`
  - invalid placebo, late seeding, raw/executed mismatch and reward-access confounding.
- `memory/rounds/R458/plan.md`
  - prospective-only design and gate.
- `scripts/run_r458_dev_select_eval_validate.py`
  - exact selection sorting and classification code.

## Integrity

`machine_checks/verify_solution.py --verify-hashes` checked all 1,554 entries in the uploaded `SHA256SUMS`; no missing file or mismatch was found at solution time. The generated `derived_results.json` records this result and all recomputed numerical tables.
