# GPT Pro math problem package

Generated: 2026-08-20T05:00:31
Tool: memory/tools/gpt_pro_pack.py (see manifest.json for sha256 provenance).

Self-contained package of math/theory problems for an external solver
(GPT Pro / theory audit). Hand the problem files + related data to the
solver; every number is repository-sealed or a design input, never invented.

## Problems in this package

### yang-relaxed-block-mechanism  [open]
- title: P1: mechanism of the relaxed-plant failure block (R415/R437)
- manuscript_line: yang_md_decoupling_marl
- note: paper-window candidate (ICEMS camera-ready 2026-09-07): small-signal sensitivity/margin analysis of the bandpass under M/D perturbation; channel detuning already REFUTED by R437
- files:
  - paper/yang_md_decoupling_marl/reports/R415.md
  - paper/yang_md_decoupling_marl/reports/R437.md
  - paper/yang_md_decoupling_marl/working/gpt_pro_failure_math_brief_2026-08-21.md
  - results/research_loop/r408_v2_solving_gate/formal_analysis.json
  - results/research_loop/r409_heldout_gate/formal_analysis.json
  - results/research_loop/r415_energy_port_extra_banks/a4_md_relaxed/records.json
  - results/research_loop/r415_energy_port_extra_banks/formal_analysis.json
  - results/research_loop/r437_relaxed_spectral/formal_analysis.json

### yang-delay-boundary-mechanism  [open]
- title: P2: controller-delay boundary of the constructive result (R440)
- manuscript_line: yang_md_decoupling_marl
- note: paper-window candidate: discrete-time ZOH phase-loss analysis; 0.2 s delay already pushes r_d over the 0.95 ceiling
- files:
  - paper/yang_md_decoupling_marl/reports/R440.md
  - paper/yang_md_decoupling_marl/working/gpt_pro_failure_math_brief_2026-08-21.md
  - results/research_loop/r408_v2_solving_gate/formal_analysis.json
  - results/research_loop/r440_robustness_expansion/delay/delay_1.json
  - results/research_loop/r440_robustness_expansion/delay/delay_1.json.sha256
  - results/research_loop/r440_robustness_expansion/delay/delay_2.json
  - results/research_loop/r440_robustness_expansion/delay/delay_2.json.sha256
  - results/research_loop/r440_robustness_expansion/formal_analysis.json

### yang-dae-first-order-authority  [open]
- title: P3: DAE first-order authority of multiplicative M/D feedback (Lemma 1 completion)
- manuscript_line: yang_md_decoupling_marl
- note: paper-window candidate: symbolics for the index-1 DAE Schur channel B_ur = f_u - f_y g_y^-1 g_u plus a finite-difference measurement recipe; converts a limitation paragraph into a contribution
- files:
  - paper/yang_md_decoupling_marl/manuscript/manuscript.md
  - paper/yang_md_decoupling_marl/reports/R399.md
  - paper/yang_md_decoupling_marl/working/gpt_pro_failure_math_brief_2026-08-21.md
  - paper/yang_md_decoupling_marl/working/theory_audit_bundle/IMPORT_NOTE.md
  - src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py
  - src/andes_rl_kundur/env/andes/base_env.py
  - src/andes_rl_kundur/env/andes/v4_config.py
  - src/andes_rl_kundur/evaluation/fast_md_authority.py

### yang-constrained-dual-saturation  [open]
- title: M1: sign-corrected constrained dual saturates at ceiling (R424-R427)
- manuscript_line: yang_md_decoupling_marl
- note: journal-extension mechanism science: projected dual ascent (step 0.05, ceiling 10.0) on nonconvex actor objective; all multipliers pinned at ceiling in 6/6 runs
- files:
  - paper/yang_md_decoupling_marl/reports/R424.md
  - paper/yang_md_decoupling_marl/reports/R425.md
  - paper/yang_md_decoupling_marl/reports/R427.md
  - paper/yang_md_decoupling_marl/working/gpt_pro_failure_math_brief_2026-08-21.md
  - results/research_loop/r425_guard_constraints_signfix/formal_analysis.json
  - results/research_loop/r427_critic_target_normalization/formal_analysis.json
  - src/andes_rl_kundur/agents/cd_matd3.py

### yang-critic-divergence-causality  [open]
- title: M2: critic divergence as causal driver of the common-frequency gap (R421/R432/R435)
- manuscript_line: yang_md_decoupling_marl
- note: journal-extension mechanism science: multiplier hypothesis REFUTED by R435; divergence remains the only surviving lead, never a measured cause
- files:
  - paper/yang_md_decoupling_marl/reports/R421.md
  - paper/yang_md_decoupling_marl/reports/R432.md
  - paper/yang_md_decoupling_marl/reports/R435.md
  - paper/yang_md_decoupling_marl/working/gpt_pro_failure_math_brief_2026-08-21.md
  - results/research_loop/r421_diagnostics/diagnostic_readout.json
  - results/research_loop/r421_diagnostics/formal_analysis.json
  - results/research_loop/r427_critic_target_normalization/formal_analysis.json
  - results/research_loop/r432_b3_diagnostics/train/cd_matd3_message/seed401/diagnostics_summary.json
  - results/research_loop/r432_b3_diagnostics/train/cd_matd3_message/seed402/diagnostics_summary.json
  - results/research_loop/r432_b3_diagnostics/train/cd_matd3_message/seed403/diagnostics_summary.json
  - results/research_loop/r432_b3_diagnostics/train/cd_matd3_no_message/seed401/diagnostics_summary.json
  - results/research_loop/r432_b3_diagnostics/train/cd_matd3_no_message/seed402/diagnostics_summary.json
  - results/research_loop/r432_b3_diagnostics/train/cd_matd3_no_message/seed403/diagnostics_summary.json
  - results/research_loop/r435_multiplier_floor/formal_analysis.json

### yang-message-contrast-sign  [open]
- title: M3: message-contrast sign puzzle (CD-MATD3 negative vs adapted-SAC positive)
- manuscript_line: yang_md_decoupling_marl
- note: journal-extension mechanism science: observation-channel attribution is OBS-leaning but BOUNDED-UNCLASSIFIED (R438); manuscript narrative must be re-familied
- files:
  - paper/yang_md_decoupling_marl/reports/R410.md
  - paper/yang_md_decoupling_marl/reports/R431.md
  - paper/yang_md_decoupling_marl/reports/R438.md
  - paper/yang_md_decoupling_marl/working/gpt_pro_failure_math_brief_2026-08-21.md
  - results/research_loop/r410_message_repair/endpoint_table.json
  - results/research_loop/r410_message_repair/formal_analysis.json
  - results/research_loop/r431_sac_slew/formal_analysis.json
  - results/research_loop/r438_sac_message_channels/formal_analysis.json

### yang-residual-identity-collapse  [open]
- title: M4: residual SAC on the energy-port anchor collapses to identity (R436)
- manuscript_line: yang_md_decoupling_marl
- note: journal-extension mechanism science: zero-residual = exact baseline seam; derive identity local-optimality from the all-non-positive penalty reward
- files:
  - paper/yang_md_decoupling_marl/reports/R436.md
  - paper/yang_md_decoupling_marl/working/gpt_pro_failure_math_brief_2026-08-21.md
  - results/research_loop/r436_energy_residual_sac/formal_analysis.json
  - results/research_loop/r436_energy_residual_sac/variants/nominal.json
  - results/research_loop/r436_energy_residual_sac/variants/nominal.json.sha256
  - results/research_loop/r436_energy_residual_sac/variants/out_Line_4.json
  - results/research_loop/r436_energy_residual_sac/variants/out_Line_4.json.sha256
  - results/research_loop/r436_energy_residual_sac/variants/out_Line_5.json
  - results/research_loop/r436_energy_residual_sac/variants/out_Line_5.json.sha256
  - results/research_loop/r436_energy_residual_sac/variants/out_Line_7.json
  - results/research_loop/r436_energy_residual_sac/variants/out_Line_7.json.sha256
  - results/research_loop/r436_energy_residual_sac/variants/out_Line_8.json
  - results/research_loop/r436_energy_residual_sac/variants/out_Line_8.json.sha256
  - results/research_loop/r436_energy_residual_sac/variants/x0p5_Line_4.json
  - results/research_loop/r436_energy_residual_sac/variants/x0p5_Line_4.json.sha256
  - results/research_loop/r436_energy_residual_sac/variants/x0p5_Line_7.json
  - results/research_loop/r436_energy_residual_sac/variants/x0p5_Line_7.json.sha256
  - results/research_loop/r436_energy_residual_sac/variants/x1p5_Line_4.json
  - results/research_loop/r436_energy_residual_sac/variants/x1p5_Line_4.json.sha256
  - results/research_loop/r436_energy_residual_sac/variants/x1p5_Line_7.json
  - results/research_loop/r436_energy_residual_sac/variants/x1p5_Line_7.json.sha256
  - results/research_loop/r436_energy_residual_sac/variants/x1p5_Line_7_12.json
  - results/research_loop/r436_energy_residual_sac/variants/x1p5_Line_7_12.json.sha256
  - src/andes_rl_kundur/agents/sac.py

### yang-timevarying-headroom-pareto  [open]
- title: M5: time-varying headroom structure and endpoint/action-stress trade-off (R416/R439/R441)
- manuscript_line: yang_md_decoupling_marl
- note: journal-extension mechanism science: all four winners collapse to constant (3,3); headroom is grid-extension not time-variation; action-stress violation measured by R441; lower-stress winner existence untested
- files:
  - paper/yang_md_decoupling_marl/reports/R416.md
  - paper/yang_md_decoupling_marl/reports/R439.md
  - paper/yang_md_decoupling_marl/reports/R441.md
  - paper/yang_md_decoupling_marl/working/gpt_pro_failure_math_brief_2026-08-21.md
  - results/research_loop/r416_headroom_expansion/formal_analysis.json
  - results/research_loop/r439_timevarying_oracle/formal_analysis.json
  - results/research_loop/r439_timevarying_oracle/formal_analysis.json.sha256
  - results/research_loop/r439_timevarying_oracle/profiles/eval_a.json
  - results/research_loop/r439_timevarying_oracle/profiles/eval_a.json.sha256
  - results/research_loop/r439_timevarying_oracle/profiles/eval_b.json
  - results/research_loop/r439_timevarying_oracle/profiles/eval_b.json.sha256
  - results/research_loop/r439_timevarying_oracle/profiles/eval_c.json
  - results/research_loop/r439_timevarying_oracle/profiles/eval_c.json.sha256
  - results/research_loop/r439_timevarying_oracle/profiles/eval_d.json
  - results/research_loop/r439_timevarying_oracle/profiles/eval_d.json.sha256
  - results/research_loop/r441_timevarying_guard/formal_analysis.json
  - results/research_loop/r441_timevarying_guard/formal_analysis.json.sha256
  - results/research_loop/r441_timevarying_guard/profiles/eval_a.json
  - results/research_loop/r441_timevarying_guard/profiles/eval_a.json.sha256
  - results/research_loop/r441_timevarying_guard/profiles/eval_b.json
  - results/research_loop/r441_timevarying_guard/profiles/eval_b.json.sha256
  - results/research_loop/r441_timevarying_guard/profiles/eval_c.json
  - results/research_loop/r441_timevarying_guard/profiles/eval_c.json.sha256
  - results/research_loop/r441_timevarying_guard/profiles/eval_d.json
  - results/research_loop/r441_timevarying_guard/profiles/eval_d.json.sha256

### yang-youlasls-certificate  [open]
- title: C1: controller-class certificate via FIR-Youla/SLS parameterization
- manuscript_line: yang_md_decoupling_marl
- note: paper-grade proposition for the journal extension: valid response parameterization + internal stability + dual/Farkas certificate for the controller-class no-headroom statement
- files:
  - paper/yang_md_decoupling_marl/manuscript/manuscript.md
  - paper/yang_md_decoupling_marl/working/gpt_pro_failure_math_brief_2026-08-21.md
  - paper/yang_md_decoupling_marl/working/theory_audit_bundle/IMPORT_NOTE.md
  - tmp/yang_md_decoupling_marl/external_vsg_decoupling_certificate.py
  - tmp/yang_md_decoupling_marl/vsg_v2_complete_resolution.md
  - tmp/yang_md_decoupling_marl/vsg_v2_fir_response_solver.py

## Intake contract

Answers are design aids, not authority. Route them through the project
external-theory intake (algebra / mechanism prediction / paper-grade
proposition) before any feed or manuscript use; see
skills/kundur-round/references/external-theory-intake.md.
