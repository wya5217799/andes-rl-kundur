# RESEARCH_PROGRAM closed-priority archive

> Archived 2026-07-29: all 15 priority_question blocks (Q-0027..Q-0042) were
> closed through R281 and were removed from `memory/RESEARCH_PROGRAM.md` to
> keep the session-start file lean.  Verbatim content below; the live policy
> and any newly authorized questions stay in the main file.  Nothing here is
> parsed by tools.

```yaml
  - id: Q-0027
    rank: 10
    phase: P0_evidence_repair
    objective: >-
      Determine whether a pre-registered state-dependent droop residual gate
      can improve the learned-controller/droop Pareto frontier, using expanded
      physical endpoints and without interpreting legacy R201 as evidence for
      the corrected recurrent algorithm.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0027.md
      - memory/rounds/R261/verdict.md
      - memory/rounds/R262/verdict.md
      - docs/research/2026-07-24_rl_vsg_publication_landscape.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Probe frozen controllers before any new training.
      - Use real ANDES in WSL and preserve the V4 bit-identical contract.
      - Report geo and cum_rf as legacy diagnostics plus physical frequency endpoints.
      - Do not claim corrected recurrent performance from legacy checkpoints.
    stop_when:
      - Q-0027 has a recorded positive, negative, or partial verdict.
      - The round has a current claim with measured provenance.
      - The PI briefing and regenerated STATE.md identify the next programme question.
  - id: Q-0028
    rank: 20
    phase: P0_evidence_repair
    objective: >-
      Determine whether the R264 low-capacity mode-ratio gate improves paired
      physical frequency outcomes on a prospectively sealed random disturbance
      bank, without tuning on that bank and without using the paper-alignment
      composite as a primary endpoint.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0028.md
      - memory/rounds/R264/verdict.md
      - src/andes_rl_kundur/evaluation/paper_strict_eval.py
      - src/andes_rl_kundur/evaluation/physical_endpoints.py
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Freeze and hash the scenario bank before evaluating any controller.
      - Compare paired R201, droop k10, static alpha 0.25, and R264 gate alpha_cap 0.25 trajectories.
      - Use physical endpoints, normalized synchronization loss, failure rate, intervals, and tail outcomes.
      - Do not tune the gate threshold or capacity on the sealed bank.
      - Keep corrected recurrent retraining out of this replication round.
    stop_when:
      - Q-0028 has a positive, negative, or partial verdict from the sealed bank.
      - The result reports paired uncertainty, failures, and tail outcomes with measured provenance.
      - A next question explicitly chooses corrected residual training or a gate-mechanism pivot.
  - id: Q-0029
    rank: 30
    phase: P0_evidence_repair
    objective: >-
      Determine whether one prospectively fixed dynamic smoothing mechanism
      can retain the R265 gate's paired physical mean improvements while
      removing its action-variation failure on a new sealed disturbance bank.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0029.md
      - memory/rounds/R265/verdict.md
      - results/r265_sealed_gate_replication/sealed_gate_replication_summary.json
      - src/andes_rl_kundur/evaluation/hybrid.py
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Treat R264 and R265 as development evidence, not another confirmatory test.
      - Diagnose the action-variation mechanism before choosing a dynamic gate.
      - Freeze at most one smoothing law before generating new ANDES trajectories.
      - Keep ratio_full_scale 0.05 and alpha_cap 0.25; do not sweep them on R265.
      - Use a new sealed no-anchor bank and keep corrected recurrent training out of this pivot round.
    stop_when:
      - The action-variation source has a measured decomposition.
      - One pre-registered smooth gate has a positive, negative, or partial verdict on a new sealed bank.
      - The next question explicitly chooses corrected residual training or closes the hand-designed gate family.
  - id: Q-0030
    rank: 40
    phase: P0_evidence_repair
    objective: >-
      Determine whether a corrected, training/deployment-consistent bounded
      residual policy around a physical droop prior can show a reproducible
      physical mechanism benefit inside a prospectively defined
      reference-feasible disturbance envelope.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0030.md
      - memory/rounds/R261/verdict.md
      - memory/rounds/R267/verdict.md
      - src/andes_rl_kundur/agents/td3.py
      - src/andes_rl_kundur/agents/sac.py
      - src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py
      - scripts/train.py
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Treat this as a P0 correctness and feasibility pilot, not yet a P1 mechanism claim.
      - Reuse the corrected V4 and off-policy infrastructure before adding new machinery.
      - Start with a memoryless bounded residual; legacy recurrent checkpoints are mechanism evidence only.
      - Keep residual composition identical in training and evaluation.
      - Use a subtractive pilot kill gate before multi-seed training.
      - Define common baseline infeasibility separately from residual-specific failure.
      - Do not make topology, stability, cross-simulator, or manuscript claims in this question.
    stop_when:
      - Residual bounds, reset, checkpoint reload, and deterministic evaluation contracts are tested.
      - The pilot has a measured go or no-go verdict on predeclared physical and action guards.
      - A passed pilot has advanced to independent seeds and a sealed bank, or a failed pilot has closed the exact residual contract.
      - The round has a current claim, measured provenance, and a PI briefing.
  - id: Q-0031
    rank: 50
    phase: P0_evidence_repair
    objective: >-
      Determine whether a simple auditable residual-learning objective can
      align physical common-mode restoration, differential synchronization,
      and residual-specific effort/variation before authorizing a second
      controller training run.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0031.md
      - memory/rounds/R268/verdict.md
      - results/r268_residual_pilot_eval/pilot_summary.json
      - src/andes_rl_kundur/env/andes/base_env.py
      - src/andes_rl_kundur/env/andes/residual_adapter.py
      - src/andes_rl_kundur/evaluation/physical_endpoints.py
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Use existing R268 traces and synthetic tests before any new ANDES trajectory or training.
      - Keep physical common-mode, differential-mode, and residual-effort terms explicit and auditable.
      - Freeze one objective contract before a future training run; do not fit weights on its evaluation bank.
      - Do not sweep algorithms, seeds, horizons, hidden sizes, or residual scales in the objective-audit stage.
      - Keep topology, graph policy, stability, cross-simulator, and manuscript work out of this P0 question.
    stop_when:
      - The R268 reward/endpoint mismatch has a source-level and trace-level diagnosis.
      - One objective contract has passed or failed prospective unit, sign, and trajectory-ranking checks.
      - A positive audit authorizes one separate pilot, or a negative audit pivots away from learned residual control on this environment.
      - The round has a current claim, measured provenance, and a PI briefing.
  - id: Q-0032
    rank: 60
    phase: P0_evidence_repair
    objective: >-
      Determine whether the current bounded inertia/damping actuation admits a
      nontrivial controller-agnostic physical improvement margin above tuned
      droop on reference-feasible disturbances before any further learned
      controller work.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0032.md
      - memory/rounds/R268/verdict.md
      - memory/rounds/R269/verdict.md
      - results/r268_residual_pilot_eval/pilot_summary.json
      - src/andes_rl_kundur/evaluation/hybrid.py
      - src/andes_rl_kundur/evaluation/physical_endpoints.py
      - src/andes_rl_kundur/evaluation/paper_path.py
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Treat the disturbance-informed oracle as an attainability upper bound, never a deployable controller.
      - Freeze a low-dimensional physics-interpretable action schedule and strict evaluation budget before new trajectories.
      - Reuse the R268 feasible envelope, droop prior, physical endpoints, action bounds, and real-ANDES runner.
      - Do not train a neural network or sweep RL algorithms, seeds, hidden sizes, horizons, or rewards.
      - Keep topology, stability certification, cross-simulator, and manuscript work out of this P0 question.
    stop_when:
      - A prospective oracle budget and materiality threshold are frozen before new trajectories.
      - The attainable paired common/differential physical margin over droop is measured with safety and action guards.
      - A negative result closes learned inertia/damping control on this environment, or a positive result routes work to observability/credit assignment.
      - The round has a current claim, measured provenance, and a PI briefing.
  - id: Q-0033
    rank: 70
    phase: P0_evidence_repair
    objective: >-
      Determine whether material common-mode frequency restoration in the
      current modified Kundur model structurally requires an explicit
      active-power or secondary-frequency actuator beyond virtual inertia and
      damping.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0033.md
      - memory/rounds/R270/verdict.md
      - results/r270_attainable_oracle/attainable_oracle_summary.json
      - src/andes_rl_kundur/env/andes/base_env.py
      - src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py
      - docs/research/2026-07-24_rl_vsg_publication_landscape.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Start with source, equilibrium, and existing-trajectory evidence; no new ANDES or model change until the actuator hypothesis is explicit.
      - Separate transient RoCoF, differential damping, and sustained common-frequency restoration.
      - Specify physical power, energy, state, and timescale limits before proposing any new actuator.
      - Do not train a neural network or reopen algorithm, reward, seed, amplitude, or duration sweeps.
      - Keep topology, stability certification, cross-simulator, and manuscript work out of this P0 audit.
    stop_when:
      - The current M/D and power/governor paths have an equation-level equilibrium interpretation.
      - R268/R270 traces quantify early and terminal common/differential effects by actuator direction.
      - The result either freezes one physically bounded new-actuator contract or pivots to model/benchmark correction.
      - The round has a current claim, measured provenance, and a PI briefing.
  - id: Q-0034
    rank: 80
    phase: P0_evidence_repair
    objective: >-
      Under a prospectively frozen power, energy, SOC, headroom, ramp, lag,
      efficiency, and converter-capability contract, determine whether one
      independently controlled classical active-power actuator improves both
      full-horizon physical VSG-mean IAE and final-window common-frequency
      absolute mean by at least 2% over a matched zero-active-power-support
      baseline with identical storage DAE structure, without worsening
      completion, synchronization, peak, RoCoF, action, or energy guards.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0034.md
      - memory/rounds/R270/verdict.md
      - memory/rounds/R271/verdict.md
      - memory/claims/CLM-0555.md
      - memory/claims/CLM-0560.md
      - memory/claims/CLM-0565.md
      - docs/research/2026-07-25_energy_feasible_multitimescale_vsg_landscape.md
      - docs/research/2026-07-25_energy_feasible_multitimescale_vsg_execution_plan.md
      - docs/eng-notes/NOTES_ANDES.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every real-ANDES smoke and formal trajectory
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Treat GENCLS plus an independent ESD1 as a hybrid actuator-authority proxy, not a unified physical GFM-BESS.
      - Source, derive, freeze, and hash every physical parameter and per-unit conversion before any new ANDES trajectory.
      - Freeze the existing M/D settings and compare classical active-power control against an identical-DAE zero-support baseline.
      - Use development cases only to select one primary classical controller, then evaluate it once on a new no-anchor sealed bank.
      - Do not train a neural network or start GNN, topology, stability-certificate, cross-simulator, HIL, or manuscript work.
    stop_when:
      - One frozen active-power contract has an AUTHORITY-POSITIVE, AUTHORITY-PARTIAL, NO-MATERIAL-AUTHORITY, or INVALID verdict.
      - Both co-primary endpoints, paired uncertainty, failures, safety, action, and energy/capability guards have measured provenance.
      - A positive result alone may open Gate 2; every other result diagnoses or closes the exact Gate-1 contract.
      - The round has a current claim, question closure, validation, rendering, and a PI briefing.
  - id: Q-0035
    rank: 90
    phase: P0_evidence_repair
    objective: >-
      Using completion and solver diagnostics only, determine whether R272's
      matched zero-support TDS failures are caused by an infeasible
      disturbance envelope, by the added zero-command ESD1 DAE, or by both,
      before any further active-power controller comparison.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0035.md
      - memory/rounds/R272/plan.md
      - memory/rounds/R272/verdict.md
      - memory/claims/CLM-0570.md
      - results/r272_active_power_authority_v2/active_power_authority_summary.json
      - results/r272_active_power_authority_v2/provenance.json
      - docs/eng-notes/NOTES_ANDES.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every real-ANDES diagnostic trajectory
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Diagnose original V4 versus identical-DAE zero support only; do not run droop+PI or learning.
      - Keep M/D, storage contract, capacity, placement, solver configuration, timing, and environment seed frozen.
      - Retain every failure and use no candidate-performance endpoint to select a future envelope.
      - Do not open Gate 2, topology, stability-certificate, cross-simulator, HIL, or manuscript work.
    stop_when:
      - The registered shared failures and signed complete controls have matched V4 versus zero-support DAE evidence.
      - The cause is classified ENVELOPE-INFEASIBLE, STORAGE-DAE-CONFOUND, MIXED, or UNRESOLVED/INVALID.
      - Any future feasible envelope or model repair is explicit, prospective, and separate from an authority re-test.
      - The round has a current claim, measured provenance, question update, validation, rendering, and a PI briefing.
  - id: Q-0036
    rank: 100
    phase: P0_evidence_repair
    objective: >-
      Determine whether the frozen R272 active-power controller has valid
      bank-level common-frequency-restoration authority on a new signed,
      multi-location scenario bank whose zero-support feasibility,
      exclusions, and nontriviality are prospectively frozen before any
      controller trajectory.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0036.md
      - memory/rounds/R272/verdict.md
      - memory/rounds/R273/verdict.md
      - memory/claims/CLM-0570.md
      - memory/claims/CLM-0575.md
      - results/r273_storage_dae_feasibility/storage_dae_feasibility_summary.json
      - results/r273_storage_dae_feasibility/boundary_summary.json
      - src/andes_rl_kundur/evaluation/feasibility_screen.py
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every real-ANDES screening and controller trajectory
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Freeze zero-support feasibility and bank nontriviality before any controller trajectory; retain and stratify every exclusion.
      - Reuse the exact frozen R272 droop+PI, storage, M/D, solver, horizon, and physical endpoint contracts.
      - Do not inspect controller endpoints while generating or screening the bank, and do not tune after the formal seal.
      - Do not train learning, change the actuator, or open Gate 2, topology, stability-certificate, cross-simulator, HIL, or manuscript work.
    stop_when:
      - The prospective bank has an immutable feasibility/nontriviality contract and retained exclusion accounting.
      - One sealed comparison has an AUTHORITY-POSITIVE, AUTHORITY-PARTIAL, NO-MATERIAL-AUTHORITY, or INVALID verdict.
      - Completion, physical endpoints, paired uncertainty, tail risk, action, SOC, power, energy, ramp, and capability guards have measured provenance.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.
  - id: Q-0037
    rank: 110
    phase: P1_residual_mechanism
    objective: >-
      Determine whether one prospectively frozen, bounded fast M/D law adds
      independent physical transient value under the validated R274 slow
      droop+PI active-power controller, without weakening common-frequency
      restoration, completion, action, energy, or safety guards.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0037.md
      - memory/rounds/R270/verdict.md
      - memory/rounds/R271/verdict.md
      - memory/rounds/R274/verdict.md
      - memory/claims/CLM-0555.md
      - memory/claims/CLM-0565.md
      - memory/claims/CLM-0580.md
      - results/r274_prospective_active_power_authority/active_power_authority_summary.json
      - docs/research/2026-07-25_energy_feasible_multitimescale_vsg_execution_plan.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every real-ANDES formal trajectory
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Keep the R274 slow droop+PI, storage, bank, solver, horizon, and physical-frequency contracts identical in both arms.
      - Freeze one bounded fast M/D law and its amplitude, rate, and action budgets before formal trajectories.
      - Register physical RoCoF, peak, synchronization, and inter-area endpoints while guarding slow restoration, completion, SOC, power, energy, and constraints.
      - Do not train learning, change topology, alter the active-power actuator, or claim unified GFM-BESS, stability, EMT, HIL, or deployment evidence.
    stop_when:
      - One sealed comparison has a FAST-LAYER-POSITIVE, FAST-LAYER-PARTIAL, NO-INDEPENDENT-FAST-VALUE, or INVALID verdict.
      - Fast endpoints, paired uncertainty, tail risk, M/D action, completion, slow-restoration, and storage-contract guards have measured provenance.
      - A non-positive result explicitly removes or narrows the fast-layer research claim.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.
  - id: Q-0039
    rank: 111
    phase: P1_residual_mechanism
    objective: >-
      Determine whether the validated R275 fast/slow benefit contains a
      material non-additive interaction, by adding only the missing fast-only
      arm and reusing the immutable R274 zero/slow and R275 combined traces.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0039.md
      - memory/rounds/R274/verdict.md
      - memory/rounds/R275/verdict.md
      - memory/claims/CLM-0580.md
      - memory/claims/CLM-0585.md
      - results/r274_prospective_active_power_authority/provenance.json
      - results/r275_fast_md_authority/fast_md_authority_summary.json
      - results/r275_fast_md_authority/provenance.json
      - docs/research/2026-07-25_energy_feasible_multitimescale_vsg_execution_plan.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every real-ANDES formal trajectory
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Reuse the exact R274 formal bank, zero-support and slow-only traces, plus the exact R275 combined traces, by immutable hash.
      - Add exactly one fast-only arm with the frozen R275 common_M_pos law and zero requested BESS active power on the identical storage DAE.
      - Freeze absolute-scale factorial interactions, best-single comparisons, paired uncertainty, tail risk, action, completion, and storage guards before the first new trace.
      - Use three disjoint WSL shards; do not rerun existing arms, train learning, tune controllers, change topology/actuators, or claim non-additivity from combined-versus-slow evidence alone.
    stop_when:
      - One sealed four-arm comparison has a NONADDITIVE-POSITIVE, NONADDITIVE-PARTIAL, ADDITIVE-ONLY, or INVALID verdict.
      - The factorial interaction, best-single contrasts, completion, fast/slow endpoints, tail, action, storage, and provenance guards have measured evidence.
      - An additive-only result explicitly retains the two layers only as a classical benchmark and blocks learning novelty on their interaction.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.
  - id: Q-0040
    rank: 112
    phase: P1_residual_mechanism
    objective: >-
      Determine whether an explicitly optimistic outcome-seeing oracle over a
      frozen zero-sum inertia basis has a material, guarded differential-mode
      margin above the immutable R274+R275 additive classical reference before
      any parallel multi-seed residual training.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0040.md
      - memory/rounds/R270/verdict.md
      - memory/rounds/R275/verdict.md
      - memory/rounds/R276/verdict.md
      - memory/claims/CLM-0555.md
      - memory/claims/CLM-0585.md
      - memory/claims/CLM-0590.md
      - results/r275_fast_md_authority/fast_md_authority_summary.json
      - results/r276_fast_slow_factorial/fast_slow_factorial_summary.json
      - docs/research/2026-07-25_energy_feasible_multitimescale_vsg_execution_plan.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every real-ANDES candidate trajectory
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Reuse the exact R275 combined traces, R274 formal bank, plant, slow controller, common pulse, solver, horizon, physical endpoint, action, and storage contracts by immutable hash.
      - Add only six signed directions spanning the four-agent zero-sum inertia subspace, with one frozen amplitude and the same 15-step fast window.
      - Treat the result-seeing selector only as a development upper bound; it is not a deployable controller, confirmatory population evidence, or a paper result.
      - Use at most eight disjoint WSL ANDES shards after measured CPU/memory preflight; do not train learning, tune amplitude/duration, change topology/actuators, or inspect candidate endpoints before the library is complete.
    stop_when:
      - One sealed library-oracle audit has a LEARNING-GAP-PRESENT, LEARNING-GAP-PARTIAL, NO-RL-NEEDED, or INVALID verdict.
      - Both differential endpoints, paired uncertainty, common/restoration guards, tail risk, completion, exact zero-sum action, storage, and provenance have measured evidence.
      - A no-gap result closes or abandons Q-0038 without neural training; a positive result freezes exactly one learning gap before training.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.
  - id: Q-0038
    rank: 113
    phase: P1_residual_mechanism
    objective: >-
      Complete the minimum honest ICEMS evidence gate by training exactly one
      memoryless parameter-shared multi-agent policy whose only learned action
      is a bounded, slew-limited scalar on the two-area zero-sum inertia mode,
      and test whether it materially improves differential synchronization
      above the immutable R274+R275 classical reference on fresh unseen cases.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0038.md
      - memory/rounds/R261/verdict.md
      - memory/rounds/R274/verdict.md
      - memory/rounds/R275/verdict.md
      - memory/rounds/R276/verdict.md
      - memory/rounds/R277/verdict.md
      - memory/claims/CLM-0595.md
      - docs/research/2026-07-26_icems_2026_minimal_full_paper_experiment_plan.md
      - results/r277_learning_gap_oracle/learning_gap_oracle_summary.json
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every real-ANDES pilot and formal trajectory
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Keep the submitted title unchanged during the experiment and treat positive MARL evidence as a prerequisite for retaining its final phrase.
      - Freeze the R274 slow droop+PI storage controller and R275 common-inertia pulse; the learned action is only q times [1, 1, -1, -1], with D fixed at zero.
      - Use the viewed R274-R277 bank only for development and contract checks; generate and seal a fresh 24-case formal bank after all checkpoints are frozen.
      - Run one pilot seed first and continue to exactly three reported seeds only if the prospective pilot gate passes.
      - Use one memoryless algorithm and one frozen reward contract; no HAWE, ensemble, recurrent policy, algorithm sweep, best-seed headline, topology work, or navigation-layer expansion beyond baseline reproducibility fixes.
    stop_when:
      - The single-seed pilot fails either registered differential endpoint, any common/restoration/action/storage/completion guard, or the implementation contract.
      - Or three frozen seeds complete one fresh sealed 24-case comparison with a MARL-RESIDUAL-POSITIVE, NO-ADAPTIVE-MARL-VALUE, or INVALID verdict.
      - The result is propagated to the ICEMS manuscript without rescuing a negative outcome through new algorithms, seeds, rewards, weak baselines, or HAWE.
      - The round has a current claim, question update, validation, rendering, PI briefing, and committed code/provenance.
  - id: Q-0041
    rank: 114
    phase: P1_residual_mechanism
    objective: >-
      Determine whether one prospectively frozen causal inter-area feedback
      law or a size-matched centralized scalar TD3 explains the R278
      parameter-shared-policy signal, and quantify empirical common/differential
      leakage on fresh disturbances before any stronger decoupling or MARL claim.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0041.md
      - memory/rounds/R278/verdict.md
      - quality_reports/ars_icems2026_review/00_synthesis.md
      - src/andes_rl_kundur/agents/shared_area_td3.py
      - src/andes_rl_kundur/env/andes/icems_residual_env.py
      - results/r278_icems_residual_pilot_s49/icems_residual_pilot_summary.json
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every real-ANDES trajectory
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Treat this as a new reviewer-driven identifiability study; never reopen, overwrite, or reinterpret the stopped R278 gate.
      - Freeze at most one causal feedback family and one size-matched centralized actor contract before formal evaluation.
      - Match observations, scalar action, reward, training steps, predeclared seeds, and tuning budget between shared and centralized actors.
      - Freeze every controller before generating and screening a fresh signed, multi-location formal bank.
      - Do not use HAWE, recurrent policies, reward or algorithm sweeps, topology changes, EMT, HIL, deployment claims, or manuscript edits.
    stop_when:
      - One valid verdict classifies the signal as MARL-IDENTIFIABLE-POSITIVE, CAUSAL-EXPLANATION-SUFFICIENT, CENTRALIZED-EXPLANATION-SUFFICIENT, NO-REPRODUCIBLE-LEARNED-VALUE, or INVALID.
      - Algebraic inertia-budget preservation is separated explicitly from measured dynamic common/differential leakage.
      - All seeds, fresh-bank cases, paired or hierarchical uncertainty, failures, tail risk, action, storage, completion, and provenance guards are retained.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.
  - id: Q-0042
    rank: 120
    phase: P1_residual_mechanism
    objective: >-
      Determine whether static differential inertia allocation along the
      frozen two-area zero-sum mode produces a material, monotone mapping to
      the identified inter-area mode damping ratio in the linearized modified
      Kundur model, gating the SCI journal-extension mechanism section.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0042.md
      - memory/rounds/R280/verdict.md
      - memory/claims/CLM-0610.md
      - paper/sci_upgrade_survey/REPORT.md
      - docs/eng-notes/NOTES_ANDES.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every ANDES linearization
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Analysis-first: eigenvalue linearization plus existing traces; no new training, no new time-domain bank, no topology change.
      - Freeze the plant, R274 slow layer, R275 common pulse, operating point, action coordinate, sweep grid, and mode-identification rule before the first eigenvalue.
      - Sweep only static |q| <= 0.25 along [1, 1, -1, -1] plus one predeclared heterogeneity axis at development level.
      - Compare mapping shape to R280 gains only qualitatively; never fit parameters to force agreement.
      - Do not edit the manuscript or make topology, stability-certificate, cross-simulator, or HIL claims in this round.
    stop_when:
      - One sealed sweep has a MECHANISM-CONFIRMED, MECHANISM-PARTIAL, MECHANISM-ABSENT, or INVALID verdict.
      - The damping-ratio mapping, mode identification, materiality threshold, and provenance have measured evidence.
      - An absent result degrades the SCI plan to the pure-empirical track prospectively.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.
  # Archived 2026-07-29: Q-0043 closed-positive @ R283 by CLM-0630
  # (STRENGTH-GRADIENT-CONFIRMED).
  - id: Q-0043
    rank: 130
    phase: P1_residual_mechanism
    objective: >-
      Determine how differential-allocation damping sensitivity varies with
      prospectively frozen grid-strength axes — aggregate VSG inertia scaling
      and tie-line reactance scaling as the declared SCR proxy — on the
      frozen modified Kundur plant, providing the measured gradient for the
      SCI journal extension's weak-grid validation section.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0043.md
      - memory/rounds/R281/verdict.md
      - memory/claims/CLM-0615.md
      - paper/sci_upgrade_survey/LINE.md
      - docs/eng-notes/NOTES_ANDES.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every ANDES linearization
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Analysis first — eigenvalue linearization on the frozen R281 plant; no new training, no new time-domain bank, no topology change.
      - Freeze both grid-strength axes (inertia-scaling set, tie-line reactance-scaling set as the declared SCR proxy) and the q subset before the first eigenvalue.
      - Reuse the R281 conjugate-pair-merged per-machine participation mode-identification rule in-script; do not re-tune it on results.
      - Compare sensitivity across strength levels qualitatively against R281 only; never fit parameters to force a gradient.
      - Do not edit the manuscript or make topology, stability-certificate, cross-simulator, or HIL claims in this round.
    stop_when:
      - One sealed sweep has a STRENGTH-GRADIENT-CONFIRMED, STRENGTH-GRADIENT-PARTIAL, STRENGTH-GRADIENT-ABSENT, or INVALID verdict.
      - The sensitivity-vs-strength mapping, SCR-proxy contract, mode identification, and provenance have measured evidence.
      - An absent result narrows the C2 weak-grid section to the R281 development-probe statement prospectively.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.
  # Archived 2026-07-29: Q-0044 closed-positive @ R285 by CLM-0640
  # (ZONE-CHARTED).
  - id: Q-0044
    rank: 140
    phase: P1_residual_mechanism
    objective: >-
      Chart the inter-area / VSG-local mode hybridization zone on the frozen
      modified Kundur plant at low aggregate VSG inertia — map where the
      pre-registered branch-validity screen flags identification failure
      across a dense M0 x q grid and attribute which mode families mix, so
      the C2 weak-grid section can state precisely where the inertia-axis
      gradient is measurable.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0044.md
      - memory/rounds/R283/verdict.md
      - memory/rounds/R283/execution_amendment_20260729.md
      - memory/claims/CLM-0630.md
      - paper/sci_upgrade_survey/LINE.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every ANDES linearization
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Analysis first — eigenvalue linearization on the frozen R281 plant; no new training, no new time-domain bank, no topology change.
      - Freeze the M0 x q grid (M0 in {100,125,150,175} x q in {-0.25,-0.125,0,+0.125,+0.25}) before the first eigenvalue; R283 endpoint rows at M0 in {100,150} are reused read-only for the map, and the three flagged R283 cells may be re-computed solely to record the full merged-mode list for attribution — they must reproduce R283 identified values within |dzeta| < 1e-6, else INVALID.
      - Reuse the R282/R283 identification rule and branch-validity screen unchanged; no new mode-tracking rule this round.
      - Do not edit the manuscript or make topology, stability-certificate, cross-simulator, or HIL claims in this round.
    stop_when:
      - One sealed map has a ZONE-CHARTED, ZONE-PARTIAL, or INVALID verdict.
      - The valid/flag boundary and the mode-family attribution have measured evidence.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.
```

  # Archived 2026-07-29: Q-0045 closed-positive @ R286 by CLM-0645
  # (SURVIVES).
  - id: Q-0045
    rank: 150
    phase: P1_residual_mechanism
    objective: >-
      Test in time domain whether the frozen centralized differential-
      allocation gain (CLM-0610, sealed R279 bank) survives a weakened
      inter-area tie corridor — rerun frozen arms q0 + centralized
      s17/s53/s89 on the same 24 sealed scenarios with the 7<->8 triple-
      circuit corridor r/x scaled by k in {1.5, 2.0}, judge by the pre-
      registered tree SURVIVES / DEGRADED / COLLAPSES / INVALID, and group
      the same traces by disturbance location for a descriptive location-
      dependence read.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0045.md
      - memory/claims/CLM-0610.md
      - memory/rounds/R279/verdict.md
      - paper/sci_upgrade_survey/LINE.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every ANDES time-domain run
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Zero-training transfer evaluation only — frozen R279 controllers and checkpoints; no retraining, no new controller, no reward change.
      - Do not modify andes_vsg_env_v4.py, andes_vsg_storage_env.py, r279_controllers.py, or the sealed formal_bank.json — weak-tie variant lives in a new env subclass file; scenarios are referenced read-only with hash verification.
      - Tie scaling limited to TIE_IDX = Line_4/Line_5/Line_6 r and x multiplied by k in {1.5, 2.0}, applied after setup and before PFlow exactly as in probes/eig_alloc_common.py; no other plant parameter touched.
      - Arms frozen prospectively — q0 plus centralized s17/s53/s89 (4 arms); if wall-clock pressure forces cuts, drop k=1.5 first, then reduce to centralized s17 only; never cut q0 or the endpoint set.
      - Disturbance-location analysis is descriptive grouping of existing and new traces by the bank location field — no model fitting, no new scenarios.
      - Retraining under weakened tie is not this round — the tree may open it as a follow-up question, nothing more.
    stop_when:
      - One sealed weak-grid evaluation has a SURVIVES, DEGRADED, COLLAPSES, or INVALID verdict.
      - The per-location grouped endpoint read has measured evidence at every k level actually run.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.
